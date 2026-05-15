import os
from typing import Optional

SSH_ENABLED: bool = os.getenv("SSH_ENABLED", "true").lower() == "true"
SSH_USER: str = os.getenv("SSH_USER", "root")
SSH_PASSWORD: Optional[str] = os.getenv("SSH_PASSWORD")
SSH_KEY_PATH: str = os.getenv("SSH_KEY_PATH", "/root/.ssh/id_rsa")
BASE_IMAGE_PATH: str = os.getenv("BASE_IMAGE_PATH", "/mnt/storage/base/")
CLUSTER_TYPE: str = os.getenv("CLUSTER_TYPE", "linux")
