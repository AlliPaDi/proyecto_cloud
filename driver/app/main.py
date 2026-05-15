from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models import ExecuteRequest, ExecuteResponse
from app.factory import get_driver
import app.dependencies as cfg

app = FastAPI(title="Cloud Orchestrator - Driver Service")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ssh_enabled": cfg.settings.SSH_ENABLED,
        "cluster_type": cfg.settings.CLUSTER_TYPE,
    }

@app.post("/driver/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest, db: AsyncSession = Depends(cfg.get_db)):
    """
    Punto de entrada principal para ejecutar tareas de infraestructura.
    Gestiona la creación/eliminación y persiste los resultados en la BD.
    """
    driver = get_driver(cfg.settings.CLUSTER_TYPE)
    payload = req.model_dump()

    try:
        if req.task_type == "CREATE_VM":
            # 1. Ejecución técnica en el Worker
            result = await driver.create_vm(payload)
            
            # 2. Persistencia: Actualizar la VM con el PID real y puerto VNC
            query_vm = text("""
                UPDATE virtual_machines 
                SET process_id = :pid, vnc_port = :vnc, status = 'READY'
                WHERE id = :vm_id
            """)
            await db.execute(query_vm, {
                "pid": result["process_id"],
                "vnc": result["vnc_port"],
                "vm_id": req.vm.id
            })

            # 3. Persistencia: Marcar la tarea como completada
            query_task = text("UPDATE tasks SET status = 'READY' WHERE id = :task_id")
            await db.execute(query_task, {"task_id": req.task_id})
            
            await db.commit()

            return ExecuteResponse(
                task_id=req.task_id,
                status="READY",
                process_id=result["process_id"],
                vnc_port=result["vnc_port"],
                commands_executed=result["commands_executed"],
            )

        if req.task_type == "DELETE_VM":
            # 1. Ejecución técnica de limpieza
            result = await driver.delete_vm(payload)
            
            # 2. Persistencia: Actualizar estado de la VM y la Tarea
            await db.execute(
                text("UPDATE virtual_machines SET status = 'DELETED', process_id = NULL WHERE id = :vm_id"),
                {"vm_id": req.vm.id}
            )
            await db.execute(
                text("UPDATE tasks SET status = 'READY' WHERE id = :task_id"),
                {"task_id": req.task_id}
            )
            
            await db.commit()

            return ExecuteResponse(
                task_id=req.task_id,
                status="DELETED",
                rollback_actions=result.get("rollback_actions", []),
            )

        raise HTTPException(status_code=400, detail=f"Tipo de tarea no soportado: {req.task_type}")

    except Exception as e:
        await db.rollback()
        rollback_actions: list[str] = []
        
        if req.task_type == "CREATE_VM":
            try:
                # Intentar limpiar lo que se haya alcanzado a crear
                rollback_actions = await driver.rollback(payload)
            except Exception as rollback_err:
                rollback_actions = [f"Error durante rollback: {str(rollback_err)}"]

        # Actualizar la tarea a fallida en la BD
        try:
            await db.execute(
                text("UPDATE tasks SET status = 'FAILED' WHERE id = :task_id"),
                {"task_id": req.task_id}
            )
            await db.commit()
        except:
            pass

        return JSONResponse(
            status_code=500,
            content=ExecuteResponse(
                task_id=req.task_id,
                status="FAILED",
                error_msg=str(e),
                rollback_actions=rollback_actions,
            ).model_dump(),
        )