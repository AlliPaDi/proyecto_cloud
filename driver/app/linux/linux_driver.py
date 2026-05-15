import asyncio
import asyncssh
from typing import List

from app.base_driver import BaseDriver
from app.linux import ovs_commands as ovs
from app.linux import qemu_commands as qemu
import app.dependencies as cfg


class LinuxDriver(BaseDriver):

    async def create_vm(self, payload: dict) -> dict:
        worker_ip = payload["worker_ip"]
        vm = payload["vm"]
        slice_info = payload["slice"]
        interfaces = payload["interfaces"]

        slice_id = slice_info["id"]
        vlan_slice = slice_info["vlan_slice"]
        vm_id = vm["id"]
        vm_name = vm["name"]
        ram = vm["ram"]
        vcpu = vm["vcpu"]
        instance_path = vm["instance_path"]
        base_image = vm.get("base_image", "")
        bridge_name = f"br-sl-{slice_id}"
        vnc_display = vm_id  # VNC port = 5900 + vm_id

        if vm.get("base_path"):
            base_path = vm["base_path"]
        else:
            base_dir = cfg.settings.BASE_IMAGE_PATH.rstrip("/")
            base_path = f"{base_dir}/{base_image}"

        has_remote = any(iface["is_remote"] for iface in interfaces)

        # Secuencia completa de comandos
        commands: list[str] = []
        commands.append(qemu.create_disk(base_path, instance_path))

        if has_remote:
            commands.extend(ovs.ensure_br_wk())

        commands.extend(ovs.ensure_br_slice(slice_id))

        for iface in interfaces:
            commands.extend(ovs.add_tap_port(bridge_name, iface["tap_name"], iface["vlan_inner"]))

        if has_remote:
            commands.extend(ovs.add_patch_ports(slice_id, vlan_slice))

        # Seed ISO de cloud-init para configurar IPs en el guest OS
        commands.append(qemu.create_seed_iso(vm_name))

        launch_cmd = qemu.launch_vm(vm_name, ram, vcpu, instance_path, interfaces, vnc_display)
        commands.append(launch_cmd)

        if not cfg.settings.SSH_ENABLED:
            return {
                "process_id": 99999,
                "vnc_port": 5900 + vnc_display,
                "commands_executed": commands,
            }

        setup_cmds = commands[:-1]
        executed, process_id = await self._run_create_ssh(
            worker_ip, setup_cmds, launch_cmd, vm_name, interfaces
        )
        return {
            "process_id": process_id,
            "vnc_port": 5900 + vnc_display,
            "commands_executed": executed,
        }

    async def _run_create_ssh(
        self,
        host: str,
        setup_cmds: list[str],
        launch_cmd: str,
        vm_name: str,
        interfaces: list,
    ) -> tuple[list[str], int]:
        executed: list[str] = []
        try:
            async with asyncssh.connect(
                host, username=cfg.settings.SSH_USER, known_hosts=None, **self._connect_kwargs()
            ) as conn:
                # Escribir archivos cloud-init via SFTP antes de ejecutar cloud-localds
                await self._write_cloud_init_files(conn, vm_name, interfaces)

                for cmd in setup_cmds:
                    result = await conn.run(cmd, check=False)
                    if result.exit_status != 0:
                        raise RuntimeError(
                            f"Command failed (exit {result.exit_status}): {cmd!r}\n{result.stderr}"
                        )
                    executed.append(cmd)

                result = await conn.run(launch_cmd, check=False)
                if result.exit_status != 0:
                    raise RuntimeError(
                        f"QEMU launch failed: {launch_cmd!r}\n{result.stderr}"
                    )
                executed.append(launch_cmd)

                # Dar tiempo a QEMU para escribir el .pid
                await asyncio.sleep(1)

                pid_cmd = qemu.read_pid(vm_name)
                pid_result = await conn.run(pid_cmd, check=False)
                if pid_result.exit_status != 0 or not pid_result.stdout.strip():
                    raise RuntimeError(f"Could not read PID file for VM {vm_name!r}")

                return executed, int(pid_result.stdout.strip())

        except (asyncssh.Error, OSError) as e:
            raise RuntimeError(f"SSH connection to {host} failed: {e}")

    async def _write_cloud_init_files(self, conn, vm_name: str, interfaces: list) -> None:
        """Escribe meta-data, user-data y network-config via SFTP para el seed ISO."""
        meta_data = f"instance-id: {vm_name}\nlocal-hostname: {vm_name}\n"
        user_data = "#cloud-config\n{}\n"
        network_config = self._build_network_config(interfaces)

        async with conn.start_sftp_client() as sftp:
            for filename, content in [
                (f"/tmp/meta-{vm_name}.yaml", meta_data),
                (f"/tmp/user-{vm_name}.yaml", user_data),
                (f"/tmp/net-{vm_name}.yaml", network_config),
            ]:
                async with sftp.open(filename, "w") as f:
                    await f.write(content)

    @staticmethod
    def _build_network_config(interfaces: list) -> str:
        """Genera YAML cloud-init network v2 con las IPs de cada interfaz del guest."""
        lines = ["network:", "  version: 2", "  ethernets:"]
        for iface in interfaces:
            name = iface.get("interface_name", "")
            ip = iface.get("ip_address", "")
            mac = iface.get("mac_address", "")
            subnet_cidr = iface.get("subnet_cidr")
            if not name:
                continue
            prefix = subnet_cidr.split("/")[1] if subnet_cidr else "24"
            lines += [f"    {name}:", "      dhcp4: false"]
            if ip:
                lines += ["      addresses:", f"        - {ip}/{prefix}"]
            if mac:
                lines += [
                    "      match:",
                    f"        macaddress: {mac}",
                    f"      set-name: {name}",
                ]
        return "\n".join(lines) + "\n"

    async def delete_vm(self, payload: dict) -> dict:
        worker_ip = payload["worker_ip"]
        vm = payload["vm"]
        slice_info = payload["slice"]
        interfaces = payload["interfaces"]

        slice_id = slice_info["id"]
        vm_name = vm["name"]
        instance_path = vm["instance_path"]
        process_id = vm.get("process_id")
        bridge_name = f"br-sl-{slice_id}"
        has_remote = any(iface["is_remote"] for iface in interfaces)

        rollback_actions: list[str] = []

        if not cfg.settings.SSH_ENABLED:
            if process_id:
                rollback_actions.append(f"Killed QEMU process {process_id}")
            rollback_actions.append(f"Deleted disk {instance_path}")
            for iface in interfaces:
                rollback_actions.append(f"Deleted TAP {iface['tap_name']} from {bridge_name}")
            if has_remote:
                rollback_actions.append(f"Deleted patch-ports for slice {slice_id}")
            rollback_actions.append(f"Deleted cloud-init seed files for {vm_name}")
            return {"rollback_actions": rollback_actions}

        try:
            async with asyncssh.connect(
                worker_ip, username=cfg.settings.SSH_USER, known_hosts=None, **self._connect_kwargs()
            ) as conn:
                if process_id:
                    await conn.run(qemu.kill_process(process_id), check=False)
                    await asyncio.sleep(2)
                    await conn.run(qemu.kill_process_force(process_id), check=False)
                    rollback_actions.append(f"Killed QEMU process {process_id}")

                await conn.run(qemu.delete_disk(instance_path), check=False)
                await conn.run(qemu.delete_pid_file(vm_name), check=False)
                rollback_actions.append(f"Deleted disk {instance_path}")

                for iface in interfaces:
                    for cmd in ovs.del_tap_port(bridge_name, iface["tap_name"]):
                        await conn.run(cmd, check=False)
                    rollback_actions.append(f"Deleted TAP {iface['tap_name']} from {bridge_name}")

                if has_remote:
                    for cmd in ovs.del_patch_ports(slice_id):
                        await conn.run(cmd, check=False)
                    rollback_actions.append(f"Deleted patch-ports for slice {slice_id}")

                # Eliminar archivos temporales del seed cloud-init
                await conn.run(qemu.delete_seed_files(vm_name), check=False)
                rollback_actions.append(f"Deleted cloud-init seed files for {vm_name}")

                # Borrar br-slice si ya no tiene puertos activos
                list_result = await conn.run(ovs.list_ports(bridge_name), check=False)
                remaining = [p for p in list_result.stdout.strip().splitlines() if p.strip()]
                if not remaining:
                    await conn.run(ovs.del_br_slice(slice_id), check=False)
                    rollback_actions.append(f"Deleted bridge {bridge_name}")

        except (asyncssh.Error, OSError) as e:
            raise RuntimeError(f"SSH connection to {worker_ip} failed: {e}")

        return {"rollback_actions": rollback_actions}

    async def setup_network(self, payload: dict) -> None:
        # La configuración de red está embebida en create_vm
        pass

    async def rollback(self, payload: dict) -> List[str]:
        """Limpieza best-effort tras un create_vm fallido."""
        worker_ip = payload["worker_ip"]
        vm = payload["vm"]
        slice_info = payload["slice"]
        interfaces = payload["interfaces"]

        slice_id = slice_info["id"]
        vm_name = vm["name"]
        instance_path = vm["instance_path"]
        bridge_name = f"br-sl-{slice_id}"
        has_remote = any(iface["is_remote"] for iface in interfaces)

        rollback_actions: list[str] = []
        cmds: list[str] = []

        for iface in interfaces:
            cmds.extend(ovs.del_tap_port(bridge_name, iface["tap_name"]))
            rollback_actions.append(f"Deleted TAP {iface['tap_name']} from {bridge_name}")

        if has_remote:
            cmds.extend(ovs.del_patch_ports(slice_id))
            rollback_actions.append(f"Deleted patch-ports for slice {slice_id}")

        cmds.append(qemu.delete_disk(instance_path))
        cmds.append(qemu.delete_pid_file(vm_name))
        cmds.append(qemu.delete_seed_files(vm_name))
        rollback_actions.append(f"Deleted disk {instance_path}")
        rollback_actions.append(f"Deleted cloud-init seed files for {vm_name}")

        if not cfg.settings.SSH_ENABLED:
            return rollback_actions

        try:
            async with asyncssh.connect(
                worker_ip, username=cfg.settings.SSH_USER, known_hosts=None, **self._connect_kwargs()
            ) as conn:
                for cmd in cmds:
                    await conn.run(cmd, check=False)
        except Exception:
            pass  # best-effort: no re-raise

        return rollback_actions

    def _connect_kwargs(self) -> dict:
        if cfg.settings.SSH_PASSWORD:
            return {"password": cfg.settings.SSH_PASSWORD}
        return {"client_keys": [cfg.settings.SSH_KEY_PATH]}
