from pydantic import BaseModel
from typing import List, Optional


class InterfacePayload(BaseModel):
    interface_name: str = ""
    tap_name: str
    vlan_inner: int = 0
    ip_address: str = ""
    mac_address: str = ""
    bridge_name: str = ""
    is_remote: bool = False
    subnet_cidr: Optional[str] = None  # ej. "192.168.2.0/24"; si None se asume /24


class VMPayload(BaseModel):
    id: int
    name: str
    base_image: str = ""
    base_path: Optional[str] = None
    ram: int = 0
    vcpu: int = 0
    instance_path: str
    process_id: Optional[int] = None


class SlicePayload(BaseModel):
    id: int
    vlan_slice: int


class ExecuteRequest(BaseModel):
    task_id: int
    task_type: str  # CREATE_VM | DELETE_VM
    worker_ip: str
    vm: VMPayload
    slice: SlicePayload
    interfaces: List[InterfacePayload]


class ExecuteResponse(BaseModel):
    task_id: int
    status: str
    process_id: Optional[int] = None
    vnc_port: Optional[int] = None
    commands_executed: Optional[List[str]] = None
    error_msg: Optional[str] = None
    rollback_actions: Optional[List[str]] = None
