from statistics import median

from counter_history import get_recent_cpu_history


def detect_cpu_anomalies(device: str, limit: int = 100) -> dict:
    """
    Analyze stored CPU readings and return rule-based anomalies.
    History is expected to be ordered newest first.
    This function does not make network configuration changes.
    """
    records = get_recent_cpu_history(device, limit=limit)

    readings = []
    for record in records:
        try:
            value = float(record["cpu_percent"])
            if 0 <= value <= 100:
                readings.append({
                    "cpu_percent": value,
                    "captured_at": record.get("captured_at"),
                })
        except (KeyError, TypeError, ValueError):
            continue

    if not readings:
        return {
            "device": device,
            "status": "insufficient_data",
            "message": (
                "No valid CPU history is available yet. "
                "Start the NetPilot monitor and try again."
            ),
            "latest_cpu_percent": None,
            "baseline_cpu_percent": None,
            "anomalies": [],
            "readings_analyzed": 0,
        }

    latest = readings[0]
    current_cpu = latest["cpu_percent"]
    anomalies = []

    def add_anomaly(severity, code, title, description):
        anomalies.append({
            "severity": severity,
            "code": code,
            "title": title,
            "description": description,
            "device": device,
            "observed_at": latest["captured_at"],
            "observed_cpu_percent": round(current_cpu, 1),
        })

    # Absolute CPU thresholds
    if current_cpu >= 90:
        add_anomaly(
            "critical",
            "CPU_CRITICAL",
            "Critical CPU utilization",
            (
                f"CPU is at {current_cpu:.1f}%. "
                "Investigate processes, traffic levels, and recent changes."
            ),
        )
    elif current_cpu >= 85:
        add_anomaly(
            "high",
            "CPU_HIGH",
            "High CPU utilization",
            (
                f"CPU is at {current_cpu:.1f}%, above the 85% threshold. "
                "Check device load and CPU-intensive processes."
            ),
        )

    # Compare with the previous recorded reading
    if len(readings) >= 2:
        previous_cpu = readings[1]["cpu_percent"]
        increase = current_cpu - previous_cpu

        if increase >= 25:
            add_anomaly(
                "high",
                "CPU_SPIKE",
                "Sudden CPU spike",
                (
                    f"CPU increased by {increase:.1f} percentage points "
                    f"from {previous_cpu:.1f}% to {current_cpu:.1f}%."
                ),
            )

    # Compare with older readings, excluding the latest reading
    older_readings = [
        item["cpu_percent"] for item in readings[1:11]
    ]
    baseline = median(older_readings) if older_readings else None

    if baseline is not None and current_cpu >= 60:
        difference = current_cpu - baseline

        if difference >= 20:
            add_anomaly(
                "medium",
                "CPU_ABOVE_BASELINE",
                "CPU above recent baseline",
                (
                    f"CPU is {difference:.1f} percentage points above "
                    f"the recent median of {baseline:.1f}%."
                ),
            )

    # Check the latest three readings for sustained high CPU
    if len(readings) >= 3:
        last_three = [item["cpu_percent"] for item in readings[:3]]

        if all(value >= 75 for value in last_three):
            add_anomaly(
                "high",
                "CPU_SUSTAINED_HIGH",
                "Sustained high CPU",
                (
                    "The three most recent readings are all at least 75%. "
                    "Check whether elevated utilization is continuing."
                ),
            )

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    anomalies.sort(
        key=lambda item: severity_order.get(item["severity"], 99)
    )

    if any(item["severity"] == "critical" for item in anomalies):
        status = "critical"
    elif any(item["severity"] == "high" for item in anomalies):
        status = "warning"
    elif anomalies:
        status = "attention"
    else:
        status = "normal"

    return {
        "device": device,
        "status": status,
        "latest_cpu_percent": round(current_cpu, 1),
        "latest_captured_at": latest["captured_at"],
        "baseline_cpu_percent": (
            round(baseline, 1) if baseline is not None else None
        ),
        "readings_analyzed": len(readings),
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "note": (
            "Rule-based findings are indicators for investigation, "
            "not proof of a device fault."
        ),
    }
