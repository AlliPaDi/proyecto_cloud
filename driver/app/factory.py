# app/factory.py
from app.linux.linux_driver import LinuxDriver
from app.openstack.openstack_driver import OpenStackDriver

def get_driver(cluster_type: str):
    if cluster_type == "linux":
        return LinuxDriver()
    elif cluster_type == "openstack":
        return OpenStackDriver()
    else:
        raise ValueError(f"Cluster type desconocido: {cluster_type}")