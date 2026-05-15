from typing import List
from app.base_driver import BaseDriver


class OpenStackDriver(BaseDriver):

    async def create_vm(self, payload: dict) -> dict:
        raise NotImplementedError("OpenStack driver not implemented")

    async def delete_vm(self, payload: dict) -> dict:
        raise NotImplementedError("OpenStack driver not implemented")

    async def setup_network(self, payload: dict) -> None:
        raise NotImplementedError("OpenStack driver not implemented")

    async def rollback(self, payload: dict) -> List[str]:
        raise NotImplementedError("OpenStack driver not implemented")
