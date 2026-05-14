from pydantic import BaseModel
from typing import Optional, Any

class TaskResponse(BaseModel):
    id: int
    slice_id: int
    vm_id: int
    task_type: str
    status: str
    payload: Any
    worker_id: Optional[int] = None
    error_msg: Optional[str] = None

    class Config:
        from_attributes = True

class HealthResponse(BaseModel):
    status: str
