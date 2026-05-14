import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from database import AsyncSessionLocal
from models import Task, VirtualMachine, Slice, Worker, Config
from ssh_driver import execute_create_vm, execute_delete_vm

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(__import__("os").getenv("POLL_INTERVAL", "10"))


# ---------------------------------------------------------------------------
# Worker placement (Round Robin via config table)
# ---------------------------------------------------------------------------

async def _pick_worker(db: AsyncSession) -> Worker | None:
    result = await db.execute(select(Worker).where(Worker.status == "ALIVE"))
    workers = result.scalars().all()
    if not workers:
        return None

    cfg = await db.execute(select(Config).where(Config.key == "last_worker_id"))
    config_row = cfg.scalars().first()
    last_id = int(config_row.value) if config_row else 0

    # Find the next worker in round-robin order by id
    candidates = sorted(workers, key=lambda w: w.id)
    next_worker = next((w for w in candidates if w.id > last_id), candidates[0])

    # Persist the new pointer
    if config_row:
        config_row.value = str(next_worker.id)
    else:
        db.add(Config(key="last_worker_id", value=str(next_worker.id)))

    return next_worker


# ---------------------------------------------------------------------------
# Slice status helpers
# ---------------------------------------------------------------------------

async def _try_activate_slice(db: AsyncSession, slice_id: int) -> None:
    """Set slice ACTIVE if every VM in it is ACTIVE."""
    result = await db.execute(
        select(func.count()).select_from(VirtualMachine)
        .where(VirtualMachine.slice_id == slice_id)
        .where(VirtualMachine.status != "ACTIVE")
    )
    remaining = result.scalar()
    if remaining == 0:
        await db.execute(
            update(Slice).where(Slice.id == slice_id).values(status="ACTIVE")
        )


async def _try_terminate_slice(db: AsyncSession, slice_id: int) -> None:
    """Set slice TERMINATED if every VM in it is DELETED."""
    result = await db.execute(
        select(func.count()).select_from(VirtualMachine)
        .where(VirtualMachine.slice_id == slice_id)
        .where(VirtualMachine.status != "DELETED")
    )
    remaining = result.scalar()
    if remaining == 0:
        await db.execute(
            update(Slice).where(Slice.id == slice_id).values(status="TERMINATED")
        )


# ---------------------------------------------------------------------------
# Task handlers
# ---------------------------------------------------------------------------

async def _handle_create_vm(db: AsyncSession, task: Task) -> None:
    payload = task.payload

    # Placement: use task.worker_id if already set, otherwise round-robin
    if task.worker_id:
        worker_res = await db.execute(select(Worker).where(Worker.id == task.worker_id))
        worker = worker_res.scalars().first()
    else:
        worker = await _pick_worker(db)

    if not worker:
        raise RuntimeError("No ALIVE workers available for placement")

    # Bind task and VM to the chosen worker
    task.worker_id = worker.id
    await db.execute(
        update(VirtualMachine)
        .where(VirtualMachine.id == task.vm_id)
        .values(worker_id=worker.id, status="PROVISIONING")
    )
    await db.commit()

    result = await execute_create_vm(worker.ip_management, payload)

    await db.execute(
        update(VirtualMachine)
        .where(VirtualMachine.id == task.vm_id)
        .values(
            process_id=result["process_id"],
            vnc_port=result["vnc_port"],
            instance_path=result["instance_path"],
            status="ACTIVE",
        )
    )
    task.status = "DONE"
    await db.commit()
    await _try_activate_slice(db, task.slice_id)
    await db.commit()


async def _handle_delete_vm(db: AsyncSession, task: Task) -> None:
    payload = task.payload
    worker_id = payload.get("worker_id") or task.worker_id

    worker = None
    if worker_id:
        worker_res = await db.execute(select(Worker).where(Worker.id == worker_id))
        worker = worker_res.scalars().first()

    if worker:
        await execute_delete_vm(worker.ip_management, payload)
    else:
        # Worker unknown or gone — still mark VM deleted so slice can be cleaned up
        logger.warning(f"DELETE_VM task {task.id}: no valid worker found, skipping SSH cleanup")

    await db.execute(
        update(VirtualMachine)
        .where(VirtualMachine.id == task.vm_id)
        .values(status="DELETED")
    )
    task.status = "DONE"
    await db.commit()
    await _try_terminate_slice(db, task.slice_id)
    await db.commit()


# ---------------------------------------------------------------------------
# Main polling loop
# ---------------------------------------------------------------------------

async def _process_one(db: AsyncSession, task: Task) -> None:
    """Claim and execute a single task. Errors are caught and stored."""
    task.status = "IN_PROGRESS"
    await db.commit()

    try:
        if task.task_type == "CREATE_VM":
            await _handle_create_vm(db, task)
        elif task.task_type == "DELETE_VM":
            await _handle_delete_vm(db, task)
        else:
            raise ValueError(f"Unknown task_type: {task.task_type}")
    except Exception as exc:
        logger.error(f"Task {task.id} ({task.task_type}) failed: {exc}")
        task.status = "FAILED"
        task.error_msg = str(exc)
        await db.commit()


async def run_task_loop() -> None:
    """Background coroutine: poll for PENDING tasks and process them."""
    logger.info("Task processor started")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Use SKIP LOCKED so concurrent instances don't race
                result = await db.execute(
                    select(Task)
                    .where(Task.status == "PENDING")
                    .order_by(Task.id)
                    .limit(5)
                    .with_for_update(skip_locked=True)
                )
                tasks = result.scalars().all()

            for task in tasks:
                # Each task gets its own session to isolate failures
                async with AsyncSessionLocal() as db:
                    task_fresh = await db.get(Task, task.id)
                    if task_fresh and task_fresh.status == "PENDING":
                        await _process_one(db, task_fresh)

        except Exception as exc:
            logger.error(f"Error in task polling loop: {exc}")

        await asyncio.sleep(POLL_INTERVAL)
