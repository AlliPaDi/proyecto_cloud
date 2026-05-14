import os
import asyncssh
import logging

logger = logging.getLogger(__name__)

SSH_ENABLED = os.getenv("SSH_ENABLED", "true").lower() == "true"
SSH_USER = os.getenv("SSH_USER", "ubuntu")
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "ubuntu")
BASE_IMAGE_PATH = os.getenv("BASE_IMAGE_PATH", "/mnt/storage/base/")
INSTANCE_PATH = os.getenv("INSTANCE_PATH", "/mnt/storage/instances/")


def _instance_path(vm_id: int) -> str:
    return f"{INSTANCE_PATH}vm_{vm_id}.qcow2"


def _vnc_display(vm_id: int) -> int:
    # Use vm_id mod 900 to stay in valid VNC display range (0-899)
    return vm_id % 900


async def _run(conn, cmd: str) -> str:
    result = await conn.run(cmd, check=True)
    return result.stdout.strip()


async def execute_create_vm(worker_ip: str, payload: dict) -> dict:
    """
    SSH into the worker and:
    1. Create a QCOW2 overlay from the base image
    2. Set up TAP interfaces and attach them to OvS bridges (one per VLAN)
    3. Launch QEMU/KVM daemonized
    4. Return process_id, vnc_port, instance_path
    """
    vm_id: int = payload["vm_id"]
    name: str = payload["name"]
    base_image: str = payload["base_image"]
    ram: int = payload["ram"]
    vcpu: int = payload["vcpu"]
    interfaces: list = payload.get("interfaces", [])

    instance = _instance_path(vm_id)
    display = _vnc_display(vm_id)
    vnc_port = 5900 + display

    if not SSH_ENABLED:
        logger.info(f"[MOCK] CREATE_VM vm_id={vm_id} on {worker_ip}")
        return {
            "process_id": 10000 + vm_id,
            "vnc_port": vnc_port,
            "instance_path": instance,
        }

    try:
        async with asyncssh.connect(
            worker_ip,
            username=SSH_USER,
            password=SSH_PASSWORD,
            known_hosts=None,
        ) as conn:
            # 1. Create overlay disk image
            base = f"{BASE_IMAGE_PATH}{base_image}"
            await _run(conn, f"qemu-img create -f qcow2 -b {base} -F qcow2 {instance}")

            # 2. Set up TAP interfaces and OvS bridges per interface
            for iface in interfaces:
                tap = iface["tap_name"]
                vlan_id = iface["vlan_id"]
                bridge = f"br-vlan-{vlan_id}"
                await _run(conn, f"ip tuntap add dev {tap} mode tap")
                await _run(conn, f"ip link set {tap} up")
                # Create OvS bridge if it doesn't exist yet
                await _run(conn, f"ovs-vsctl --may-exist add-br {bridge}")
                await _run(conn, f"ovs-vsctl add-port {bridge} {tap} tag={vlan_id}")

            # 3. Build QEMU netdev/device args for each interface
            net_args = []
            for idx, iface in enumerate(interfaces):
                tap = iface["tap_name"]
                mac = iface["mac_address"]
                net_args.append(
                    f"-netdev tap,id=net{idx},ifname={tap},script=no,downscript=no "
                    f"-device virtio-net-pci,netdev=net{idx},mac={mac}"
                )
            net_str = " ".join(net_args)

            # 4. Launch QEMU daemonized
            pid_file = f"/tmp/qemu-{vm_id}.pid"
            qemu_cmd = (
                f"qemu-system-x86_64 "
                f"-name {name} "
                f"-m {ram} "
                f"-smp {vcpu} "
                f"-drive file={instance},format=qcow2 "
                f"{net_str} "
                f"-vnc :{display} "
                f"-daemonize "
                f"-pidfile {pid_file} "
                f"-enable-kvm"
            )
            await _run(conn, qemu_cmd)

            # 5. Read back the PID
            pid_str = await _run(conn, f"cat {pid_file}")
            process_id = int(pid_str)

        return {
            "process_id": process_id,
            "vnc_port": vnc_port,
            "instance_path": instance,
        }

    except Exception as e:
        logger.error(f"CREATE_VM failed for vm_id={vm_id} on {worker_ip}: {e}")
        raise


async def execute_delete_vm(worker_ip: str, payload: dict) -> None:
    """
    SSH into the worker and:
    1. Kill the QEMU process
    2. Remove TAP interfaces from OvS bridges
    3. Delete the instance disk image
    """
    vm_id: int = payload["vm_id"]
    process_id: int | None = payload.get("process_id")
    instance: str | None = payload.get("instance_path") or _instance_path(vm_id)
    interfaces: list = payload.get("interfaces", [])

    if not SSH_ENABLED:
        logger.info(f"[MOCK] DELETE_VM vm_id={vm_id} on {worker_ip}")
        return

    try:
        async with asyncssh.connect(
            worker_ip,
            username=SSH_USER,
            password=SSH_PASSWORD,
            known_hosts=None,
        ) as conn:
            # 1. Kill QEMU process (ignore if already dead)
            if process_id:
                try:
                    await _run(conn, f"kill {process_id}")
                except Exception:
                    pass

            # 2. Clean up TAP interfaces
            for iface in interfaces:
                tap = iface.get("tap_name")
                if not tap:
                    continue
                try:
                    await _run(conn, f"ovs-vsctl del-port {tap}")
                except Exception:
                    pass
                try:
                    await _run(conn, f"ip link delete {tap}")
                except Exception:
                    pass

            # 3. Remove instance disk
            if instance:
                try:
                    await _run(conn, f"rm -f {instance}")
                except Exception:
                    pass

    except Exception as e:
        logger.error(f"DELETE_VM failed for vm_id={vm_id} on {worker_ip}: {e}")
        raise
