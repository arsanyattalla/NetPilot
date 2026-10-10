
import os

from network import get_device_status, get_interface_status
from counter_history import get_interface_trends

DATA_SOURCE = os.getenv("NETPILOT_MODE", "mock").strip().lower()


def analyze_device(device_name: str) -> dict:
    """Analyze device health without changing monitoring history."""

    findings = []
    recommendations = []

    try:
        device = get_device_status(device_name)
        interface_data = get_interface_status(device_name)
    except Exception:
        # Avoid exposing credentials or internal connection details.
        return {
            "device": device_name,
            "data_source": DATA_SOURCE,
            "status": "diagnostics_unavailable",
            "health_score": 0,
            "health": "unknown",
            "findings_count": 1,
            "findings": [{
                "severity": "critical",
                "issue": "Device diagnostics unavailable",
                "evidence": (
                    "Could not collect current device diagnostics. "
                    "The cause has not been confirmed."
                ),
            }],
            "recommendations": [
                "Verify device reachability, management connectivity, "
                "and monitoring service status."
            ],
        }

    if device.get("status") != "online":
        findings.append({
            "severity": "critical",
            "issue": "Device is not reporting online status",
            "evidence": f"Status: {device.get('status')}",
        })
        recommendations.append(
            "Verify device reachability and management connectivity."
        )

    cpu = device.get("cpu")
    if isinstance(cpu, (int, float)):
        if cpu >= 90:
            findings.append({
                "severity": "critical",
                "issue": "Very high CPU utilization",
                "evidence": f"CPU usage: {cpu}%",
            })
            recommendations.append(
                "Read current CPU process statistics and compare "
                "against recent device baselines."
            )
        elif cpu >= 80:
            findings.append({
                "severity": "warning",
                "issue": "High CPU utilization",
                "evidence": f"CPU usage: {cpu}%",
            })
            recommendations.append(
                "Monitor CPU utilization and investigate sustained load."
            )

    memory = device.get("memory")
    if isinstance(memory, (int, float)):
        if memory >= 90:
            findings.append({
                "severity": "critical",
                "issue": "Very high memory utilization",
                "evidence": f"Memory usage: {memory}%",
            })
            recommendations.append(
                "Inspect memory statistics and compare against "
                "the device baseline."
            )
        elif memory >= 80:
            findings.append({
                "severity": "warning",
                "issue": "High memory utilization",
                "evidence": f"Memory usage: {memory}%",
            })
            recommendations.append(
                "Monitor memory utilization for continued increases."
            )

    # Use only snapshots created by the monitoring process.
    for item in get_interface_trends(device_name):
        name = item["interface"]
        status = item["status"]
        deltas = item["new_errors_since_previous_poll"]

        if status == "baseline":
            continue

        if status == "counter_reset_or_decrease":
            findings.append({
                "severity": "info",
                "issue": f"Interface counter reset or decrease on {name}",
                "evidence": (
                    "Counters decreased between stored snapshots. "
                    "A reset or reboot is possible; verify device uptime."
                ),
            })
            continue

        if status != "increasing" or not deltas:
            continue

        new_errors = sum(deltas.values())
        findings.append({
            "severity": "critical" if new_errors >= 100 else "warning",
            "issue": f"New interface errors detected on {name}",
            "evidence": (
                f"Between monitoring snapshots: "
                f"{deltas['input_errors']} input, "
                f"{deltas['crc_errors']} CRC, and "
                f"{deltas['output_errors']} output errors."
            ),
        })
        recommendations.append(
            f"Investigate {name}: compare further readings and check "
            "cabling, connectors, transceiver condition, speed/duplex, "
            "and the connected device."
        )

    score = 100
    for finding in findings:
        if finding["severity"] == "critical":
            score -= 25
        elif finding["severity"] == "warning":
            score -= 10

    score = max(0, score)

    if score >= 90:
        health = "healthy"
    elif score >= 70:
        health = "warning"
    else:
        health = "critical"

    return {
        "device": device_name,
        "status": device.get("status", "unknown"),
        "data_source": DATA_SOURCE,
        "health_score": score,
        "health": health,
        "findings_count": len(findings),
        "findings": findings,
        "recommendations": list(dict.fromkeys(recommendations)),
    }
