# app/base_driver.py
from abc import ABC, abstractmethod

class BaseDriver(ABC):

    @abstractmethod
    async def create_vm(self, payload: dict) -> dict:
        """Crea la VM y retorna {process_id, vnc_port, instance_path}"""
        ...

    @abstractmethod
    async def delete_vm(self, payload: dict) -> None:
        """Termina proceso QEMU y limpia recursos"""
        ...

    @abstractmethod
    async def setup_network(self, payload: dict) -> None:
        """Configura bridges OvS / redes Neutron según el cluster"""
        ...

    @abstractmethod
    async def rollback(self, payload: dict) -> None:
        """Limpieza completa ante fallo"""
        ...