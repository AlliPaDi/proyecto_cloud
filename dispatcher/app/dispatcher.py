import asyncio
import logging
import os

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

DRIVER_URL = os.getenv("DRIVER_URL", "http://driver:8088/driver/execute")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))
STUCK_TIMEOUT_MINUTES = int(os.getenv("STUCK_TIMEOUT_MINUTES", "10"))
KEEPALIVE_EVERY = 5  # run keep-alive check every N cycles


async def _fetch_and_lock_tasks(session: AsyncSession) -> list[dict]:
    """Atomically fetches PLACEMENT_READY tasks and marks them IN_PROGRESS."""
    result = await session.execute(text("""
        SELECT t.id, t.task_type, t.vm_id, t.worker_id, t.payload,
               w.ip_management AS worker_ip
        FROM tasks t
        JOIN workers w ON w.id = t.worker_id
        WHERE t.status = 'PLACEMENT_READY'
        LIMIT 10
        FOR UPDATE OF t SKIP LOCKED
    """))
    rows = result.mappings().all()
    if not rows:
        return []

    task_ids = [r["id"] for r in rows]
    id_list = ",".join(str(i) for i in task_ids)
    await session.execute(text(
        f"UPDATE tasks SET status = 'IN_PROGRESS', updated_at = NOW() WHERE id IN ({id_list})"
    ))
    await session.commit()
    return [dict(r) for r in rows]


async def _enrich_interfaces(session: AsyncSession, interfaces: list[dict]) -> list[dict]:
    """Adds subnet_cidr from the networks table to each interface that has a network_id."""
    enriched = []
    for iface in interfaces:
        iface = dict(iface)
        network_id = iface.get("network_id")
        if network_id:
            row = (await session.execute(
                text("SELECT subnet_cidr FROM networks WHERE id = :nid"),
                {"nid": network_id},
            )).first()
            if row and row[0]:
                iface["subnet_cidr"] = row[0]
        enriched.append(iface)
    return enriched


def _build_driver_request(task: dict, enriched_interfaces: list[dict]) -> dict:
    """Transforms a locked task row + enriched interfaces into a Driver API request."""
    p = task["payload"]
    return {
        "task_id": task["id"],
        "task_type": task["task_type"],
        "worker_ip": task["worker_ip"],
        "vm": {
            "id": task["vm_id"],
            "name": p["vm_name"],
            "base_image": p.get("base_image", ""),
            "base_path": p.get("base_path"),
            "ram": p.get("ram", 0),
            "vcpu": p.get("vcpu", 0),
            "instance_path": p["instance_path"],
            "process_id": p.get("process_id"),
        },
        "slice": {
            "id": p["slice_id"],
            "vlan_slice": p.get("vlan_slice", 0),
        },
        "interfaces": enriched_interfaces,
    }


async def _dispatch_task(task: dict, client: httpx.AsyncClient) -> dict:
    """Posts one task to the Driver. Returns a result summary dict."""
    async with AsyncSessionLocal() as session:
        enriched = await _enrich_interfaces(
            session, task["payload"].get("interfaces", [])
        )

    body = _build_driver_request(task, enriched)

    try:
        resp = await client.post(DRIVER_URL, json=body, timeout=120.0)
        result = resp.json()
        # Driver handles its own DB updates on both success (200) and failure (500).
        # We only intervene when we cannot reach the driver at all.
        status = result.get("status", "UNKNOWN")
        logger.info(f"Task {task['id']} → driver responded with status={status}")
        return {
            "task_id": task["id"],
            "vm_id": task["vm_id"],
            "worker_ip": task["worker_ip"],
            "status": status,
        }
    except httpx.RequestError as e:
        # Network-level failure: driver never received the request.
        # Mark task FAILED ourselves since no one else will.
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    UPDATE tasks
                    SET status = 'FAILED',
                        error_msg = :msg,
                        updated_at = NOW()
                    WHERE id = :tid
                """),
                {"tid": task["id"], "msg": f"Dispatcher: driver unreachable — {e}"},
            )
            await session.commit()
        logger.error(f"Task {task['id']} failed: driver unreachable: {e}")
        return {
            "task_id": task["id"],
            "vm_id": task["vm_id"],
            "worker_ip": task["worker_ip"],
            "status": "FAILED",
        }


async def _recover_stuck_tasks(session: AsyncSession) -> None:
    """Marks tasks stuck in IN_PROGRESS beyond STUCK_TIMEOUT_MINUTES as FAILED."""
    result = await session.execute(text(f"""
        UPDATE tasks
        SET status = 'FAILED',
            error_msg = 'Dispatcher timeout: task stuck in IN_PROGRESS',
            updated_at = NOW()
        WHERE status = 'IN_PROGRESS'
          AND updated_at < NOW() - INTERVAL '{STUCK_TIMEOUT_MINUTES} minutes'
        RETURNING id
    """))
    recovered = result.fetchall()
    if recovered:
        await session.commit()
        ids = [r[0] for r in recovered]
        logger.warning(f"Recovered {len(ids)} stuck tasks: {ids}")


async def run_dispatch_cycle() -> list[dict]:
    """One full poll → lock → dispatch cycle. Returns dispatched task summaries."""
    async with AsyncSessionLocal() as session:
        tasks = await _fetch_and_lock_tasks(session)

    if not tasks:
        return []

    async with httpx.AsyncClient() as client:
        raw = await asyncio.gather(
            *[_dispatch_task(t, client) for t in tasks],
            return_exceptions=True,
        )

    results = []
    for item in raw:
        if isinstance(item, Exception):
            logger.error(f"Unhandled exception during dispatch: {item}")
        else:
            results.append(item)
    return results


async def polling_loop() -> None:
    """Infinite background loop that polls and dispatches tasks periodically."""
    logger.info("Dispatcher polling loop started")
    cycle = 0
    while True:
        try:
            cycle += 1
            if cycle % KEEPALIVE_EVERY == 0:
                async with AsyncSessionLocal() as session:
                    await _recover_stuck_tasks(session)

            dispatched = await run_dispatch_cycle()
            if dispatched:
                logger.info(f"Dispatched {len(dispatched)} tasks: {dispatched}")
        except Exception as e:
            logger.error(f"Polling cycle error: {e}")

        await asyncio.sleep(POLL_INTERVAL)
