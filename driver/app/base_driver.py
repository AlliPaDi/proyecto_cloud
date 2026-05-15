from abc import ABC, abstractmethod
from typing import List


class BaseDriver(ABC):

    @abstractmethod
    async def create_vm(self, payload: dict) -> dict:
        """Crea la VM y retorna {process_id, vnc_port, commands_executed}"""
        ...

    @abstractmethod
    async def delete_vm(self, payload: dict) -> dict:
        """Termina proceso QEMU y limpia recursos. Retorna {rollback_actions}"""
        ...

    @abstractmethod
    async def setup_network(self, payload: dict) -> None:
        """Configura bridges OvS / redes Neutron según el cluster"""
        ...

    @abstractmethod
    async def rollback(self, payload: dict) -> List[str]:
        """Limpieza completa ante fallo. Retorna lista de acciones realizadas."""
        ...
