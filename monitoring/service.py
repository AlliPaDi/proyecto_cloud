import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
import datetime
from typing import Dict, List, Optional

from models import Worker, User, Slice, VirtualMachine
from ssh_client import get_worker_metrics, SSH_ENABLED

async def update_all_workers_metrics(session: AsyncSession):
    # Ambos clusters (linux y openstack) exponen sus nodos vía SSH
    result = await session.execute(select(Worker))
    workers = result.scalars().all()

    for worker in workers:
        if not SSH_ENABLED:
            continue
            
        metrics = await get_worker_metrics(worker.ip_management)
        
        if metrics:
            if "total_ram" in metrics and worker.total_ram == 0:
                worker.total_ram = metrics["total_ram"]
            if "total_cpu" in metrics and worker.total_cpu == 0:
                worker.total_cpu = metrics["total_cpu"]
            
            if "current_cpu_load" in metrics:
                worker.current_cpu_load = metrics["current_cpu_load"]
            if "current_ram_available" in metrics:
                worker.current_ram_available = metrics["current_ram_available"]
            
            worker.status = metrics.get("status", "DOWN")
            worker.updated_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            
    await session.commit()

async def get_workers_for_user(session: AsyncSession, user_role: str, user_id: Optional[int] = None) -> List[Worker]:
    if user_role == "SYSTEM_ADMIN":
        result = await session.execute(select(Worker).order_by(Worker.id))
        return list(result.scalars().all())
        
    if not user_id:
        # Si no hay ID pero el rol requiere filtrar, devolvemos vacio temporalmente o lanzamos error.
        # Asumimos que gateway siempre inyecta X-User-Id si esta autenticado.
        return []

    if user_role == "SLICE_ADMIN":
        # SLICE_ADMIN ve workers de las VMs de sus alumnos (User.admin_id == user_id)
        query = select(Worker).distinct().join(VirtualMachine, VirtualMachine.worker_id == Worker.id)\
            .join(Slice, VirtualMachine.slice_id == Slice.id)\
            .join(User, Slice.user_id == User.id)\
            .where(User.admin_id == user_id).order_by(Worker.id)
        result = await session.execute(query)
        return list(result.scalars().all())

    if user_role == "STUDENT":
        # STUDENT ve workers de sus propias VMs (Slice.user_id == user_id)
        query = select(Worker).distinct().join(VirtualMachine, VirtualMachine.worker_id == Worker.id)\
            .join(Slice, VirtualMachine.slice_id == Slice.id)\
            .where(Slice.user_id == user_id).order_by(Worker.id)
        result = await session.execute(query)
        return list(result.scalars().all())

    return []

async def get_worker_by_id_for_user(session: AsyncSession, worker_id: int, user_role: str, user_id: Optional[int] = None) -> Optional[Worker]:
    workers = await get_workers_for_user(session, user_role, user_id)
    for w in workers:
        if w.id == worker_id:
            return w
    return None

async def get_metrics_for_user(session: AsyncSession, user_role: str, user_id: Optional[int] = None) -> List[dict]:
    workers = await get_workers_for_user(session, user_role, user_id)
    if not workers:
        return []

    worker_ids = [w.id for w in workers]
    result = await session.execute(
        select(
            VirtualMachine.worker_id,
            func.coalesce(func.sum(VirtualMachine.vcpu), 0),
            func.coalesce(func.sum(VirtualMachine.ram), 0),
        )
        .where(VirtualMachine.worker_id.in_(worker_ids), VirtualMachine.status != "FAILED")
        .group_by(VirtualMachine.worker_id)
    )
    assigned_map = {row[0]: (int(row[1]), int(row[2])) for row in result.all()}

    clusters: Dict[str, list] = {}
    for w in sorted(workers, key=lambda w: w.id):
        assigned_cores, assigned_ram_mb = assigned_map.get(w.id, (0, 0))
        used_cores = w.total_cpu * (float(w.current_cpu_load or 0) / 100.0)
        used_ram_mb = max(w.total_ram - w.current_ram_available, 0)

        node = {
            "node_name": w.hostname,
            "status": w.status,
            "hardware_total": {
                "cores": w.total_cpu,
                "ram_gb": round(w.total_ram / 1024, 2),
            },
            "resources_assigned": {
                "cores": assigned_cores,
                "ram_gb": round(assigned_ram_mb / 1024, 2),
            },
            "resources_utilized": {
                "cores": round(used_cores, 2),
                "ram_gb": round(used_ram_mb / 1024, 2),
            },
        }
        clusters.setdefault(w.cluster_type, []).append(node)

    return [{"cluster_type": ct, "nodes": nodes} for ct, nodes in clusters.items()]
