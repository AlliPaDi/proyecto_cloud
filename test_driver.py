import httpx
import asyncio
import json

# URL del Driver dentro de tu local
BASE_URL = "http://localhost:8088/driver/execute"

# Datos de prueba siguiendo tus modelos (models.py)
test_payload = {
    "task_id": 1,
    "task_type": "CREATE_VM",
    "worker_ip": "192.168.1.10",
    "vm": {
        "id": 101,
        "name": "vm-pucp-test",
        "base_image": "ubuntu-22.04.qcow2",
        "ram": 2048,
        "vcpu": 2,
        "instance_path": "/mnt/storage/instances/vm-pucp-test.qcow2"
    },
    "slice": {
        "id": 500,
        "vlan_slice": 100
    },
    "interfaces": [
        {
            "tap_name": "tap-vm101",
            "vlan_inner": 10,
            "mac_address": "52:54:00:11:22:33",
            "is_remote": True
        }
    ]
}

async def run_test():
    async with httpx.AsyncClient() as client:
        print("--- Enviando solicitud de CREATE_VM ---")
        try:
            response = await client.post(BASE_URL, json=test_payload, timeout=10.0)
            print(f"Código de Estado: {response.status_code}")
            print("Respuesta del Driver:")
            print(json.dumps(response.json(), indent=4))
        except Exception as e:
            print(f"Error de conexión: {e}")

if __name__ == "__main__":
    asyncio.run(run_test())