import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database import get_db
from models import Task, VirtualMachine
from schemas import TaskResponse, HealthResponse
from auth import require_admin
from task_processor import run_task_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop_task = asyncio.create_task(run_task_loop())
    yield
    loop_task.cancel()


app = FastAPI(title="Linux Cluster Driver", version="1.0", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


@app.get("/driver/tasks", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, IN_PROGRESS, DONE, FAILED"),
    slice_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_admin),
):
    q = select(Task)
    if status:
        q = q.where(Task.status == status)
    if slice_id:
        q = q.where(Task.slice_id == slice_id)
    result = await db.execute(q.order_by(Task.id))
    return result.scalars().all()


@app.get("/driver/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_admin),
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/driver/tasks/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_admin),
):
    """Reset a FAILED task back to PENDING so the processor picks it up again."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "FAILED":
        raise HTTPException(status_code=400, detail="Only FAILED tasks can be retried")

    task.status = "PENDING"
    task.error_msg = None
    await db.commit()
    await db.refresh(task)
    return task


@app.get("/driver/vms/{vm_id}")
async def get_vm(
    vm_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(require_admin),
):
    vm = await db.get(VirtualMachine, vm_id)
    if not vm:
        raise HTTPException(status_code=404, detail="VM not found")
    return {
        "id": vm.id,
        "name": vm.name,
        "status": vm.status,
        "worker_id": vm.worker_id,
        "process_id": vm.process_id,
        "vnc_port": vm.vnc_port,
        "instance_path": vm.instance_path,
    }
