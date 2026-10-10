
import os
import re
from contextlib import contextmanager

from dotenv import load_dotenv
from netmiko import ConnectHandler
from netmiko.exceptions import (
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Fixed device allowlist. The API cannot choose arbitrary hosts.
DEVICE_CONFIG = {
    "MP-SW01": {
        "host_env": "CISCO_MP_SW01_HOST",
        "username_env": "CISCO_MP_SW01_USERNAME",
        "password_env": "CISCO_MP_SW01_PASSWORD",
        "secret_env": "CISCO_MP_SW01_SECRET",
    }
}

CONNECT_TIMEOUT = int(os.getenv("NETPILOT_CONNECT_TIMEOUT", "5"))
COMMAND_TIMEOUT = int(os.getenv("NETPILOT_COMMAND_TIMEOUT", "20"))


class CiscoDeviceError(Exception):
    """Safe-to-display Cisco connection or collection error."""


@contextmanager
def connected_device(device_name: str):
    config = DEVICE_CONFIG.get(device_name)

    if config is None:
        raise CiscoDeviceError("Device is not in the approved allowlist.")

    host = os.getenv(config["host_env"], "").strip()
    username = os.getenv(config["username_env"], "").strip()
    password = os.getenv(config["password_env"], "")

    if not host or not username or not password:
        raise CiscoDeviceError(
            f"Connection settings are incomplete for {device_name}."
        )

    # Only the fixed inventory above can select a destination.
    params = {
        "device_type": "cisco_ios",
        "host": host,
        "username": username,
        "password": password,
        "conn_timeout": CONNECT_TIMEOUT,
        "auth_timeout": CONNECT_TIMEOUT,
        "banner_timeout": CONNECT_TIMEOUT,
        "fast_cli": False,
	"disabled_algorithms": {
    	"kex": [],
	},
    "session_log": "/tmp/netpilot-netmiko.log",
	"ssh_strict": True,
	"system_host_keys": True,
    }

    secret = os.getenv(config["secret_env"], "")
    if secret:
        params["secret"] = secret

    connection = None

    try:
        connection = ConnectHandler(**params)

        if secret:
            connection.enable()

        yield connection

    except NetmikoAuthenticationException as exc:
        raise CiscoDeviceError(
            "Cisco authentication failed. Check the account credentials."
        ) from exc
    except NetmikoTimeoutException as exc:
        raise CiscoDeviceError(
            "Cisco connection timed out. Check reachability and SSH access."
        ) from exc
    except CiscoDeviceError:
        raise
    except Exception as exc:
        # Do not return raw exception details, which may contain sensitive data.
        raise CiscoDeviceError(
            "Cisco collection failed. Check backend logs and device access."
        ) from exc
    finally:
        if connection is not None:
            try:
                connection.disconnect()
            except Exception:
                pass


def run_show(connection, command: str) -> str:
    """Run only commands defined by this application."""
    allowed_commands = {
        "show version",
        "show processes cpu",
        "show interfaces",
        "show vlan brief",
    }

    if command not in allowed_commands:
        raise CiscoDeviceError("Command is not approved.")

    return connection.send_command(
        command,
        read_timeout=COMMAND_TIMEOUT,
        strip_prompt=True,
        strip_command=True,
    )


def _extract_cpu(output: str):
    match = re.search(
        r"CPU utilization for five seconds:\s*(\d+)%/",
        output,
        re.IGNORECASE,
    )
    return int(match.group(1)) if match else None


def _extract_uptime(output: str):
    match = re.search(
        r"(\S.*?) uptime is (.+)",
        output,
        re.IGNORECASE,
    )
    return match.group(2).strip() if match else "Unknown"


def _parse_interfaces(output: str):
    interfaces = []

    # Cisco IOS interface output is generally organized into blocks
    # beginning with: Interface is ..., line protocol is ...
    blocks = re.split(r"(?m)^(?=\S+ is .+?, line protocol is )", output)

    for block in blocks:
        first_line = block.splitlines()[0] if block.strip() else ""

        match = re.match(
            r"(\S+) is (.+?), line protocol is (.+)",
            first_line,
            re.IGNORECASE,
        )
        if not match:
            continue

        name, physical_status, protocol_status = match.groups()

        input_errors = re.search(
            r"(\d+) input errors",
            block,
            re.IGNORECASE,
        )
        crc_errors = re.search(
            r"(\d+) CRC",
            block,
            re.IGNORECASE,
        )
        output_errors = re.search(
            r"(\d+) output errors",
            block,
            re.IGNORECASE,
        )

        input_count = int(input_errors.group(1)) if input_errors else 0
        crc_count = int(crc_errors.group(1)) if crc_errors else 0
        output_count = int(output_errors.group(1)) if output_errors else 0

        # CRC errors are typically included in input errors, so don't
        # double-count them.
        total_errors = max(input_count, crc_count) + output_count

        up = (
            physical_status.strip().lower() == "up"
            and protocol_status.strip().lower() == "up"
        )

        interfaces.append({
            "interface": name,
            "status": "connected" if up else "down",
            "errors": total_errors,
            "input_errors": input_count,
            "crc_errors": crc_count,
            "output_errors": output_count,
        })

    return interfaces


def get_device_status(device_name: str) -> dict:
    with connected_device(device_name) as connection:
        version = run_show(connection, "show version")
        cpu_output = run_show(connection, "show processes cpu")

    return {
        "device": device_name,
        "status": "online",
        "cpu": _extract_cpu(cpu_output),
        # Not every IOS platform exposes memory in the same format.
        # Do not report a fabricated value when it isn't collected.
        "memory": None,
        "uptime": _extract_uptime(version),
    }


def get_interface_status(device_name: str) -> dict:
    with connected_device(device_name) as connection:
        output = run_show(connection, "show interfaces")

    return {
        "device": device_name,
        "interfaces": _parse_interfaces(output),
    }


def get_vlan_info(device_name: str) -> dict:
    with connected_device(device_name) as connection:
        output = run_show(connection, "show vlan brief")

    vlans = []

    for line in output.splitlines():
        # Typical IOS format: VLAN ID, name, status, ports
        match = re.match(
            r"^\s*(\d+)\s+(\S+)\s+(active|act/unsup|suspend)\b",
            line,
            re.IGNORECASE,
        )
        if match:
            vlans.append({
                "id": int(match.group(1)),
                "name": match.group(2),
                "status": match.group(3),
            })

    return {
        "device": device_name,
        "vlans": vlans,
    }
