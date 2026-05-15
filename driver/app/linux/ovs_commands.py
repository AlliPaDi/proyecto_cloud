def ensure_br_wk() -> list[str]:
    return [
        "ovs-vsctl --may-exist add-br br-wk",
        "ovs-vsctl --may-exist add-port br-wk ens4",
    ]


def ensure_br_slice(slice_id: int) -> list[str]:
    return [f"ovs-vsctl --may-exist add-br br-sl-{slice_id}"]


def add_tap_port(bridge: str, tap_name: str, vlan_inner: int) -> list[str]:
    cmds = [
        f"ip tuntap add dev {tap_name} mode tap",
        f"ip link set {tap_name} up",
    ]
    if vlan_inner == 0:
        cmds.append(f"ovs-vsctl add-port {bridge} {tap_name}")
    else:
        cmds.append(f"ovs-vsctl add-port {bridge} {tap_name} tag={vlan_inner}")
    return cmds


def add_patch_ports(slice_id: int, vlan_slice: int) -> list[str]:
    # Bidirectional patch between br-sl-{id} and br-wk; br-wk side tagged with vlan_slice
    return [
        (
            f"ovs-vsctl add-port br-sl-{slice_id} patch-to-wk-{slice_id}"
            f" -- set interface patch-to-wk-{slice_id} type=patch"
            f" options:peer=patch-to-sl-{slice_id}"
        ),
        (
            f"ovs-vsctl add-port br-wk patch-to-sl-{slice_id} tag={vlan_slice}"
            f" -- set interface patch-to-sl-{slice_id} type=patch"
            f" options:peer=patch-to-wk-{slice_id}"
        ),
    ]


def del_tap_port(bridge: str, tap_name: str) -> list[str]:
    return [
        f"ovs-vsctl del-port {bridge} {tap_name} 2>/dev/null || true",
        f"ip link del {tap_name} 2>/dev/null || true",
    ]


def del_patch_ports(slice_id: int) -> list[str]:
    return [
        f"ovs-vsctl del-port br-sl-{slice_id} patch-to-wk-{slice_id} 2>/dev/null || true",
        f"ovs-vsctl del-port br-wk patch-to-sl-{slice_id} 2>/dev/null || true",
    ]


def del_br_slice(slice_id: int) -> str:
    return f"ovs-vsctl del-br br-sl-{slice_id}"


def list_ports(bridge: str) -> str:
    return f"ovs-vsctl list-ports {bridge}"
