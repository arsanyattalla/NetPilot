# NetPilot — AI-Powered Network Operations Assistant

NetPilot is a Python-based network operations assistant designed to simplify network monitoring, troubleshooting, and incident investigation. It combines network device integration, automated diagnostics, historical performance tracking, and AI-assisted analysis in a centralized dashboard.

The project explores how AI and automation can help network engineers identify anomalies, investigate connectivity issues, correlate incidents, and accelerate troubleshooting.

## Features

- **Network Device Integration** — Connect to supported Cisco devices using Python and Netmiko.
- **Device Diagnostics** — Retrieve device information, interface status, and VLAN information.
- **Network Monitoring** — Track device performance and maintain historical monitoring data.
- **Anomaly Detection** — Identify unusual network performance patterns.
- **Incident Investigation** — Collect diagnostic information to help investigate network issues.
- **Root Cause Analysis** — Analyze available device and monitoring data to help identify potential causes of incidents.
- **Incident Correlation** — Connect related alerts and symptoms to support troubleshooting.
- **Alert Management** — Retrieve and investigate network alerts.
- **AI Assistant** — Use a language model to assist with network troubleshooting and technical questions.
- **Web Dashboard** — Access network information and troubleshooting tools through a browser-based interface.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend logic and automation |
| FastAPI | REST API and application backend |
| Uvicorn | ASGI application server |
| Netmiko | Network device access and automation |
| SQLite | Historical monitoring and application data |
| Ollama | Local language-model integration |
| HTML, CSS, JavaScript | Web dashboard |
| Git and GitHub | Version control and project hosting |

## Architecture

```text
                Network Engineer
                       |
                       v
               Web Dashboard
              HTML / CSS / JS
                       |
                       v
                 FastAPI API
                       |
          +------------+-------------+
          |            |             |
          v            v             v
    Cisco Devices   Monitoring    AI Assistant
      Netmiko       & Diagnostics  Ollama
          |            |
          +------------+
                       |
                       v
                 SQLite History
```

## Project Structure

```text
NetPilot/
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── cisco.py
│   ├── network.py
│   ├── devices.py
│   ├── diagnostics.py
│   ├── monitor.py
│   ├── database.py
│   ├── counter_history.py
│   ├── anomaly_detector.py
│   ├── alerts.py
│   └── incident_engine.py
├── frontend/
│   └── index.html
├── .gitignore
└── README.md
```

*The exact files and optional modules may vary by version.*

## Getting Started

### Requirements

- Python 3.10 or newer
- pip
- Git
- Ollama and a supported local model, if using the local AI integration
- Authorized network device access, if using live network monitoring

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/NetPilot.git
cd NetPilot
```

Replace `YOUR-USERNAME` with your GitHub username and adjust the repository name if necessary.

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r backend/requirements.txt
```

### 4. Configure the AI model

If your installation uses Ollama, install and start Ollama, then download the configured model:

```bash
ollama pull llama3.2:3b
```

Make sure Ollama is running and that the model name matches the configuration in `backend/agent.py`.

### 5. Start the backend

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000
```

Open the dashboard:

**http://127.0.0.1:8000**

Explore the interactive API documentation:

**http://127.0.0.1:8000/docs**

### 6. Start network monitoring

If live monitoring is configured, open a second terminal:

```bash
cd ~/Desktop/NetPilot/backend
source ../venv/bin/activate
python monitor.py
```

Configure device access and monitoring settings before starting the monitor. Do not run live monitoring against devices without authorization.

## API Overview

The FastAPI backend exposes endpoints for network operations, diagnostics, monitoring, and incident investigation.

| Endpoint | Description |
|---|---|
| `GET /health` | Check application health |
| `GET /devices/{device_name}` | Retrieve device information |
| `GET /devices/{device_name}/interfaces` | Retrieve interface information |
| `GET /devices/{device_name}/vlans` | Retrieve VLAN information |
| `GET /devices/{device_name}/diagnostics` | Run or retrieve device diagnostics |
| `POST /ask` | Submit a question to the AI assistant |
| `GET /monitoring/{device_name}/history` | Retrieve monitoring history |
| `GET /monitoring/{device_name}/cpu-history` | Retrieve CPU history |
| `GET /anomalies/{device_name}` | Retrieve detected anomalies |
| `GET /alerts/{device_name}` | Retrieve network alerts |
| `GET /correlate-incidents/{device_name}` | Correlate incident information |
| `GET /root-cause/{device_name}` | Analyze potential root causes |

For request parameters, response schemas, and interactive testing, start the application and visit `/docs`.

## Security Considerations

NetPilot is intended for authorized network administration and lab environments.

- Never commit credentials, API keys, private keys, or `.env` files.
- Do not publish internal IP addresses, real device inventories, configuration backups, or sensitive monitoring data.
- Use a sanitized configuration and simulated data for public demonstrations.
- Protect network-management endpoints with authentication and appropriate access controls before deployment.
- Restrict device access to authorized management networks.
- Do not expose the development API directly to the public internet.
- Review dependencies and application settings before deploying to a production environment.

## Future Improvements

- Role-based authentication and access control.
- Real-time dashboard updates and alert notifications.
- Expanded network vendor support.
- Improved anomaly detection and incident correlation.
- AI-assisted troubleshooting recommendations with supporting diagnostic evidence.
- Containerized deployment and automated testing.
- CI/CD integration and automated deployment.
- A public demo mode with simulated network devices.

## Project Goals

This project demonstrates practical skills in:

- Network engineering and troubleshooting
- Python network automation
- REST API development
- Network monitoring and observability
- Incident investigation and root-cause analysis
- AI-assisted operations
- Linux application deployment
- Git-based version control

## Disclaimer

NetPilot is an independent learning and portfolio project. Diagnostic results and AI-generated recommendations should be verified by a qualified network engineer before changes are made to production infrastructure.

---

**Built with Python, FastAPI, Netmiko, and AI.**
