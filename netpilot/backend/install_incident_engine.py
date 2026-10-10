from pathlib import Path
from datetime import datetime
import py_compile
import shutil

root = Path(__file__).resolve().parent
main_file = root / "main.py"
engine_file = root / "incident_engine.py"

if not main_file.exists():
    raise SystemExit("ERROR: main.py was not found.")

source = main_file.read_text()

if '@app.get("/correlate-incidents/{device_name}")' in source:
    raise SystemExit(
        "The correlation endpoint already exists. "
        "No files were changed."
    )

if "def device_diagnostics(" not in source:
    raise SystemExit("Could not find device_diagnostics() in main.py.")

if "def device_alerts(" not in source:
    raise SystemExit("Could not find device_alerts() in main.py.")

engine_code = r'''
from collections.abc import Mapping


def _walk(obj, path=""):
    """Yield paths and values from nested dictionaries and lists."""
    if isinstance(obj, Mapping):
        for key, value in obj.items():
            child = f"{path}.{key}" if path else str(key)
            yield child, str(key).lower(), value
            yield from _walk(value, child)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from _walk(value, f"{path}[{index}]")


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def correlate_incident(device, cpu, diagnostics, alerts):
    """
    Produce explainable incident findings from existing monitoring data.
    Findings are indicators, not proof of root cause.
    """
    findings = []
    evidence_sources = []

    def add(severity, code, title, detail, source):
        findings.append({
            "severity": severity,
            "code": code,
            "title": title,
            "detail": detail,
            "source": source,
        })

    # CPU findings come from the existing rule-based detector.
    if isinstance(cpu, dict):
        for anomaly in cpu.get("anomalies", []):
            if not isinstance(anomaly, dict):
                continue
            add(
                anomaly.get("severity", "medium"),
                anomaly.get("code", "CPU_ANOMALY"),
                anomaly.get("title", "CPU anomaly"),
                anomaly.get("description", "CPU anomaly detected."),
                "cpu_anomaly_detector",
            )
        evidence_sources.append("CPU history and anomaly detector")

    # Look for explicit interface error counters and link-state warnings.
    # Positive counters are evidence of recorded events, not proof that
    # the events are current or responsible for a problem.
    if diagnostics is not None:
        interface_terms = (
            "crc", "input_errors", "output_errors", "errors",
            "discards", "drops", "flaps",
        )
        state_terms = ("link_status", "interface_status", "oper_status")

        for path, key, value in _walk(diagnostics):
            number = _number(value)

            if (
                any(term in key for term in interface_terms)
                and number is not None
                and number > 0
            ):
                add(
                    "medium",
                    "INTERFACE_COUNTER",
                    f"Nonzero interface counter: {key}",
                    f"{path} has value {value}. Check whether the counter "
                    "is increasing and when it was last cleared.",
                    "device_diagnostics",
                )

            if any(term in key for term in state_terms):
                state = str(value).strip().lower()
                if state in ("down", "false", "notconnect", "not connected"):
                    add(
                        "high",
                        "INTERFACE_DOWN",
                        f"Interface state indicates down: {key}",
                        f"{path} reports {value}. Verify whether this "
                        "interface is expected to be operational.",
                        "device_diagnostics",
                    )

        evidence_sources.append("Device diagnostics")

    # Include active alert records when the endpoint supplies them.
    alert_items = alerts
    if isinstance(alerts, dict):
        alert_items = alerts.get(
            "alerts",
            alerts.get("items", alerts.get("data", []))
        )

    if isinstance(alert_items, list):
        for item in alert_items:
            if not isinstance(item, dict):
                continue

            status = str(
                item.get("status", item.get("state", "active"))
            ).lower()
            if status in ("resolved", "cleared", "closed", "inactive"):
                continue

            severity = str(item.get("severity", "medium")).lower()
            if severity not in ("critical", "high", "medium", "low"):
                severity = "medium"

            title = item.get(
                "title", item.get("name", item.get("type", "Active alert"))
            )
            detail = item.get(
                "description", item.get("message", item.get("details", ""))
            )

            add(
                severity,
                str(item.get("code", "ACTIVE_ALERT")),
                str(title),
                str(detail or "An active alert was returned."),
                "alert_store",
            )

        evidence_sources.append("Alert endpoint")

    priority = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(
        key=lambda item: priority.get(item["severity"], 99)
    )

    if any(f["severity"] == "critical" for f in findings):
        severity = "critical"
    elif any(f["severity"] == "high" for f in findings):
        severity = "high"
    elif findings:
        severity = "medium"
    else:
        severity = "normal"

    # Report cross-signal overlap without asserting causality.
    codes = {item["code"] for item in findings}
    cpu_present = any(code.startswith("CPU_") for code in codes)
    interface_present = any(
        code.startswith("INTERFACE_") for code in codes
    )
    alert_present = any(
        item["source"] == "alert_store" for item in findings
    )

    correlations = []
    if cpu_present and interface_present:
        correlations.append({
            "title": "CPU and interface evidence coexist",
            "detail": (
                "CPU anomalies and interface indicators were observed "
                "in the available data. Compare their timestamps and "
                "counter changes before concluding they are related."
            ),
        })
    if alert_present and (cpu_present or interface_present):
        correlations.append({
            "title": "Alerts coexist with telemetry findings",
            "detail": (
                "An active alert and telemetry findings are present. "
                "Compare timestamps and affected interfaces to determine "
                "whether they describe the same event."
            ),
        })

    return {
        "device": device,
        "severity": severity,
        "finding_count": len(findings),
        "findings": findings,
        "correlations": correlations,
        "evidence_sources": evidence_sources,
        "cpu_status": (
            cpu.get("status") if isinstance(cpu, dict) else None
        ),
        "limitations": [
            "Co-occurrence does not establish causation.",
            "Cumulative interface counters may predate the incident.",
            "Missing telemetry is not proof that a subsystem is healthy.",
        ],
        "read_only": True,
    }
'''

engine_file.write_text(engine_code.strip() + "\n")
py_compile.compile(str(engine_file), doraise=True)

backup = root / (
    "main.py.before_correlation_"
    + datetime.now().strftime("%Y%m%d_%H%M%S")
    + ".bak"
)
shutil.copy2(main_file, backup)

endpoint = r'''

@app.get("/correlate-incidents/{device_name}")
def correlate_network_incidents(device_name: str):
    """Correlate existing CPU, diagnostics, and alert evidence."""
    import json
    from fastapi import HTTPException
    from anomaly_detector import detect_cpu_anomalies
    from incident_engine import correlate_incident

    # Keep the endpoint restricted to the currently supported lab device.
    if device_name != "MP-SW01":
        raise HTTPException(
            status_code=404,
            detail="Device is not in the NetPilot demo allowlist."
        )

    def as_data(value):
        # Support FastAPI JSONResponse values as well as plain dictionaries.
        if hasattr(value, "body"):
            try:
                return json.loads(value.body.decode("utf-8"))
            except Exception:
                return {"response": str(value.body)}
        return value

    cpu_data = detect_cpu_anomalies(device_name)

    diagnostics_data = None
    diagnostics_error = None
    try:
        diagnostics_data = as_data(device_diagnostics(device_name))
    except Exception as exc:
        diagnostics_error = str(exc)

    alerts_data = None
    alerts_error = None
    try:
        alerts_data = as_data(device_alerts(device_name, limit=50))
    except Exception as exc:
        alerts_error = str(exc)

    result = correlate_incident(
        device=device_name,
        cpu=cpu_data,
        diagnostics=diagnostics_data,
        alerts=alerts_data,
    )

    result["data_quality"] = {
        "diagnostics_available": diagnostics_error is None,
        "alerts_available": alerts_error is None,
        "diagnostics_error": diagnostics_error,
        "alerts_error": alerts_error,
    }
    return result
'''

main_file.write_text(source.rstrip() + "\n" + endpoint + "\n")

try:
    py_compile.compile(str(main_file), doraise=True)
except Exception:
    shutil.copy2(backup, main_file)
    raise

print("SUCCESS: incident_engine.py created.")
print("SUCCESS: correlation endpoint added to main.py.")
print(f"Backup saved at: {backup}")
print("Endpoint: GET /correlate-incidents/MP-SW01")
