import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import DispatcherStatus, TaskDispatchedInfo, TriggerResponse
from app.dispatcher import polling_loop, run_dispatch_cycle

logging.basicConfig(level=logging.INFO)

_polling_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _polling_task
    _polling_task = asyncio.create_task(polling_loop())
    yield
    if _polling_task and not _polling_task.done():
        _polling_task.cancel()


app = FastAPI(title="Cloud Orchestrator - Dispatcher Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "polling_active": _polling_task is not None and not _polling_task.done(),
    }


@app.get("/dispatcher/status", response_model=DispatcherStatus)
async def dispatcher_status(db: AsyncSession = Depends(get_db)):
    in_progress = (await db.execute(
        text("SELECT COUNT(*) FROM tasks WHERE status = 'IN_PROGRESS'")
    )).scalar() or 0

    completed = (await db.execute(
        text("""
            SELECT COUNT(*) FROM tasks
            WHERE status = 'READY'
              AND updated_at > NOW() - INTERVAL '1 hour'
        """)
    )).scalar() or 0

    failed = (await db.execute(
        text("""
            SELECT COUNT(*) FROM tasks
            WHERE status = 'FAILED'
              AND updated_at > NOW() - INTERVAL '1 hour'
        """)
    )).scalar() or 0

    return DispatcherStatus(
        polling_active=_polling_task is not None and not _polling_task.done(),
        tasks_in_progress=in_progress,
        tasks_completed_last_hour=completed,
        tasks_failed_last_hour=failed,
    )


@app.post("/dispatcher/trigger", response_model=TriggerResponse)
async def trigger():
    """Force one immediate dispatch cycle."""
    dispatched = await run_dispatch_cycle()
    return TriggerResponse(
        dispatched=[
            TaskDispatchedInfo(
                task_id=d["task_id"],
                vm_id=d["vm_id"],
                worker_ip=d["worker_ip"],
                status=d["status"],
            )
            for d in dispatched
        ]
    )
