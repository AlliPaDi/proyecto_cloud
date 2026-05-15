from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.models import ExecuteRequest, ExecuteResponse
from app.factory import get_driver
import app.dependencies as cfg

app = FastAPI(title="Cloud Orchestrator - Driver Service")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ssh_enabled": cfg.SSH_ENABLED,
        "cluster_type": cfg.CLUSTER_TYPE,
    }


@app.post("/driver/execute", response_model=ExecuteResponse)
async def execute(req: ExecuteRequest):
    driver = get_driver(cfg.CLUSTER_TYPE)
    payload = req.model_dump()

    try:
        if req.task_type == "CREATE_VM":
            result = await driver.create_vm(payload)
            return ExecuteResponse(
                task_id=req.task_id,
                status="READY",
                process_id=result["process_id"],
                vnc_port=result["vnc_port"],
                commands_executed=result["commands_executed"],
            )

        if req.task_type == "DELETE_VM":
            result = await driver.delete_vm(payload)
            return ExecuteResponse(
                task_id=req.task_id,
                status="DELETED",
                rollback_actions=result.get("rollback_actions", []),
            )

        return JSONResponse(
            status_code=400,
            content={"detail": f"Unknown task_type: {req.task_type!r}"},
        )

    except Exception as e:
        rollback_actions: list[str] = []
        if req.task_type == "CREATE_VM":
            try:
                rollback_actions = await driver.rollback(payload)
            except Exception:
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
