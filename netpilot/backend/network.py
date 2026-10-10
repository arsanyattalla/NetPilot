
import os
import random
from datetime import datetime

from cisco import (
    CiscoDeviceError,
    get_device_status as get_real_device_status,
    get_interface_status as get_real_interface_status,
    get_vlan_info as get_real_vlan_info,
)

MODE = os.getenv("NETPILOT_MODE", "mock").strip().lower()

if MODE not in {"mock", "real"}:
    raise ValueError("NETPILOT_MODE must be 'mock' or 'real'.")


def get_device_status(device_name):
    if MODE == "real":
        return get_real_device_status(device_name)

    return {
        "device": device_name,
        "status": "online",
        "cpu": random.randint(10, 45),
        "memory": random.randint(20, 60),
        "uptime": "42 days, 7 hours",
        "checked_at": datetime.now().isoformat(),
    }


def get_interface_status(device_name):
    if MODE == "real":
        return get_real_interface_status(device_name)

    return {
        "device": device_name,
        "interfaces": [
            {"interface": "Gi1/0/1", "status": "connected", "errors": 0},
            {"interface": "Gi1/0/2", "status": "connected", "errors": 0},
            {"interface": "Gi1/0/24", "status": "connected", "errors": 143},
        ],
    }


def get_vlan_info(device_name):
    if MODE == "real":
        return get_real_vlan_info(device_name)

    return {
        "device": device_name,
        "vlans": [
            {"id": 10, "name": "DATA"},
            {"id": 20, "name": "VOICE"},
            {"id": 30, "name": "POS"},
            {"id": 40, "name": "GUEST"},
        ],
    }
