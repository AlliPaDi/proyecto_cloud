from pydantic import BaseModel
from typing import List


class DispatcherStatus(BaseModel):
    polling_active: bool
    tasks_in_progress: int
    tasks_completed_last_hour: int
    tasks_failed_last_hour: int


class TaskDispatchedInfo(BaseModel):
    task_id: int
    vm_id: int
    worker_ip: str
    status: str


class TriggerResponse(BaseModel):
    dispatched: List[TaskDispatchedInfo]
