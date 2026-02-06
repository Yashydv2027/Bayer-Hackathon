# Autonomous Incident Commander - Architecture Documentation
## Bayer AI Hackathon 2026

---

## Executive Summary

The **Autonomous Incident Commander** is a multi-agent AI system that automatically detects, investigates, and fixes production incidents. It uses a reasoning loop inspired by how human SRE (Site Reliability Engineering) teams handle incidents:

```
DETECT → INVESTIGATE → CORRELATE → DECIDE → ACT → REPORT
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         STREAMLIT UI (app.py)                       │
│                    User Interface & Demo Controls                   │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      COMMANDER AGENT (Orchestrator)                 │
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │ LogsAgent   │    │MetricsAgent │    │ DeployAgent │             │
│  │ (Forensic)  │    │ (Telemetry) │    │ (Historian) │             │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘             │
│         │                  │                  │                     │
│         └──────────────────┼──────────────────┘                     │
│                            ▼                                        │
│                   ┌─────────────────┐                               │
│                   │ CorrelationEngine│                              │
│                   │ (Links Findings) │                              │
│                   └────────┬────────┘                               │
│                            ▼                                        │
│                   ┌─────────────────┐                               │
│                   │ ActionExecutor  │                               │
│                   │ (Fixes Service) │                               │
│                   └─────────────────┘                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CHECKOUT SERVICE (FastAPI)                       │
│                  Real Service with SQLite Database                  │
│                                                                     │
│  Endpoints:                                                         │
│  - POST /checkout (can fail when config is broken)                  │
│  - GET  /metrics  (latency, error rate, pool utilization)           │
│  - GET  /health   (service status)                                  │
│  - POST /admin/inject-error (breaks the service)                    │
│  - POST /admin/reset (fixes the service)                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
Bayer Hackathon/
│
├── app.py                          # Streamlit UI - One-click demo
├── checkout_service.py             # FastAPI service with SQLite
├── service.log                     # Real log file (generated)
├── service_config.json             # Service configuration (modified by inject/reset)
│
└── commander_agent/
    │
    ├── agents/                     # Sub-agents that investigate
    │   ├── base_agent.py           # Interface all agents implement
    │   ├── logs_agent.py           # Reads service.log for errors
    │   ├── metrics_agent.py        # Calls /metrics endpoint
    │   └── deploy_agent.py         # Checks service_config.json
    │
    ├── reasoning/                  # Reasoning loop components
    │   ├── detector.py             # DETECT: Parse alerts
    │   ├── planner.py              # PLAN: Decide which agents to call
    │   ├── investigator.py         # INVESTIGATE: Run agents
    │   ├── decision_maker.py       # DECIDE: Determine root cause
    │   ├── action_recommender.py   # ACT: Recommend fix
    │   ├── action_executor.py      # ACT: Execute the fix
    │   └── reporter.py             # REPORT: Generate RCA
    │
    ├── correlation/
    │   └── correlation_engine.py   # Links findings across agents
    │
    └── models/                     # Data models
        ├── alert.py                # Alert structure
        ├── investigation.py        # Investigation state
        └── report.py               # RCA report structure
```

---

## How the Demo Works (Step by Step)

### Step 1: User Clicks "INJECT ERROR & AUTO-FIX"

The button triggers two actions:
1. **Inject Error**: Calls `POST /admin/inject-error` which modifies `service_config.json`:
   - `db_pool_max_connections`: 100 → 50
   - `db_timeout_seconds`: 10 → 2

2. **Trigger Failure**: Makes a checkout request that will fail because the connection pool is now too small

### Step 2: LogsAgent Investigates

**File**: `commander_agent/agents/logs_agent.py`

```python
# Reads the actual service.log file
with open(self.log_file) as f:
    logs = f.readlines()

# Looks for ERROR and CRITICAL entries
for log in logs[-100:]:
    if "CRITICAL" in log:
        findings.append({
            "type": "critical_error",
            "description": "ConnectionTimeoutException...",
            ...
        })
```

**What it finds**:
- ConnectionTimeoutException in logs
- Pool exhaustion errors
- Failed checkout transactions

### Step 3: MetricsAgent Investigates

**File**: `commander_agent/agents/metrics_agent.py`

```python
# Calls the real /metrics endpoint
response = requests.get(f"{self.service_url}/metrics")
metrics = response.json()

# Analyzes for anomalies
if latency > 500:  # Baseline is 150ms
    findings.append({
        "type": "latency_spike",
        "description": f"P99 latency at {latency}ms"
    })
```

**What it finds**:
- Latency spike (2000ms vs 150ms baseline)
- Error rate spike (15% vs 0.1% baseline)
- DB pool at 100% utilization

### Step 4: DeployAgent Investigates

**File**: `commander_agent/agents/deploy_agent.py`

```python
# Reads the actual config file
with open(self.config_file) as f:
    current_config = json.load(f)

# Compares with defaults
if current_pool != default_pool:
    findings.append({
        "type": "config_change",
        "description": f"DB pool changed: {default_pool} → {current_pool}"
    })
```

**What it finds**:
- DB pool reduced by 50%
- DB timeout reduced
- Recent deployment timestamp

### Step 5: Correlation Engine

**File**: Inline in `app.py` (`correlate_findings` function)

```python
# Checks for patterns
has_config_change = any("config" in str(f).lower() for f in all_findings)
has_connection_error = any("connection" in str(a).lower() for a in all_anomalies)

if has_config_change and has_connection_error:
    root_cause = "Configuration change caused database connection pool exhaustion"
    confidence = 0.95
```

**Result**: Determines that config change + connection errors = deployment caused the issue

### Step 6: Action Executor

**File**: `commander_agent/reasoning/action_executor.py`

```python
def rollback(self):
    # Actually calls the service to reset
    response = requests.post(f"{self.service_url}/admin/reset")
    
    return ActionResult(
        action="ROLLBACK",
        success=True,
        message="Service configuration rolled back"
    )
```

**Actions taken**:
1. **ROLLBACK**: Calls `/admin/reset` to restore healthy config
2. **VERIFY**: Checks `/health` to confirm service is healthy
3. **TEST**: Makes a checkout request to verify functionality

### Step 7: Report Generation

A Markdown report is generated with:
- Summary of the incident
- All agents consulted and their findings
- Root cause determination
- Actions taken
- Timeline of events

---

## Key Technical Decisions

### 1. Real Data, Not Mocks
Every agent works with **real data**:
- LogsAgent reads actual `service.log`
- MetricsAgent calls actual `/metrics` endpoint
- DeployAgent checks actual `service_config.json`

### 2. Async Agent Architecture
Agents are designed to run asynchronously for parallel investigation:
```python
async def investigate(self, context: Dict[str, Any]) -> Dict[str, Any]:
```

### 3. Standardized Result Format
All agents return the same structure:
```python
{
    "agent_name": str,
    "success": bool,
    "findings": [...],      # What was found
    "anomalies": [...],     # What's abnormal
    "timeline_events": [...], # For building incident timeline
    "confidence": float     # 0.0 to 1.0
}
```

### 4. Separation of Concerns
- **Agents**: Only gather data, don't decide
- **Correlation Engine**: Links findings, doesn't fix
- **Action Executor**: Only executes approved actions
- **Commander**: Orchestrates everything

---

## Demo Scenario (Hackathon)

**Trigger**: Checkout Service latency spikes to 2000ms

**Investigation Finds**:
1. LogsAgent: ConnectionTimeoutException, pool exhausted errors
2. MetricsAgent: Latency 2000ms (13x baseline), Error rate 15%
3. DeployAgent: Config changed - pool reduced from 100→50

**Root Cause**: Configuration deployment reduced database connection pool, causing exhaustion under normal load

**Fix Applied**: Rollback configuration to healthy state

**Result**: Service restored, checkout working, 95% confidence

---

## Technologies Used

| Component | Technology |
|-----------|------------|
| UI | Streamlit |
| Backend Service | FastAPI + SQLite |
| Agents | Python async/await |
| Logging | Python logging module |
| Configuration | JSON files |

---

## Running the Demo

```bash
# Terminal 1: Start the service
uvicorn checkout_service:app --reload --port 8000

# Terminal 2: Start the UI
streamlit run app.py
```

Then click **"INJECT ERROR & AUTO-FIX"** to see the full flow.

---

*Bayer AI Hackathon 2026 - Autonomous Incident Commander*
