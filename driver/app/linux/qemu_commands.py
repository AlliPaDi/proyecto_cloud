from typing import List


def create_disk(base_path: str, instance_path: str) -> str:
    return f"sudo qemu-img create -f qcow2 -b {base_path} -F qcow2 {instance_path}"


def create_seed_iso(vm_name: str) -> str:
    return (
        f"sudo cloud-localds --network-config /tmp/net-{vm_name}.yaml"
        f" /tmp/seed-{vm_name}.iso"
        f" /tmp/user-{vm_name}.yaml /tmp/meta-{vm_name}.yaml"
    )


def delete_seed_files(vm_name: str) -> str:
    return (
        f"rm -f /tmp/seed-{vm_name}.iso /tmp/net-{vm_name}.yaml"
        f" /tmp/user-{vm_name}.yaml /tmp/meta-{vm_name}.yaml"
    )


def launch_vm(
    vm_name: str,
    ram: int,
    vcpu: int,
    instance_path: str,
    interfaces: List[dict],
    vnc_display: int,
) -> str:
    parts = [
        "sudo qemu-system-x86_64",
        f"-m {ram}",
        f"-smp {vcpu}",
        f"-drive file={instance_path},format=qcow2",
        f"-drive file=/tmp/seed-{vm_name}.iso,media=cdrom",  # cloud-init NoCloud seed
    ]
    for i, iface in enumerate(interfaces):
        parts += [
            f"-netdev tap,id=net{i},ifname={iface['tap_name']},script=no,downscript=no",
            f"-device virtio-net-pci,netdev=net{i},mac={iface['mac_address']}",
        ]
    parts += [
        f"-pidfile /tmp/{vm_name}.pid",
        f"-vnc :{vnc_display}",
        "-daemonize",
    ]
    return " ".join(parts)


def read_pid(vm_name: str) -> str:
    return f"sudo cat /tmp/{vm_name}.pid"


def kill_process(process_id: int) -> str:
    return f"kill -SIGTERM {process_id} 2>/dev/null || true"


def kill_process_force(process_id: int) -> str:
    return f"kill -SIGKILL {process_id} 2>/dev/null || true"


def delete_disk(instance_path: str) -> str:
    return f"rm -f {instance_path}"


def delete_pid_file(vm_name: str) -> str:
    return f"rm -f /tmp/{vm_name}.pid"
