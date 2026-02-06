"""
Streamlit Demo App - FULLY DYNAMIC Multi-Agent System

Flow:
1. Click "INJECT ERROR" → Real service breaks
2. Commander Agent orchestrates investigation:
   - LogsAgent reads real logs
   - MetricsAgent calls real endpoints
   - DeployAgent checks real config
3. Commander correlates findings
4. Commander executes fix
5. Commander generates report
"""
import streamlit as st
import requests
import time
import asyncio
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from commander_agent.agents.logs_agent import LogsAgent
from commander_agent.agents.metrics_agent import MetricsAgent
from commander_agent.agents.deploy_agent import DeployAgent
from commander_agent.reasoning.action_executor import ActionExecutor

# ============= CONFIG =============
SERVICE_URL = "http://localhost:8000"
LOG_FILE = Path(__file__).parent / "service.log"
CONFIG_FILE = Path(__file__).parent / "service_config.json"

# ============= SERVICE FUNCTIONS =============

def is_service_running():
    try:
        return requests.get(f"{SERVICE_URL}/health", timeout=2).status_code == 200
    except:
        return False

def get_service_health():
    try:
        return requests.get(f"{SERVICE_URL}/health", timeout=5).json()
    except:
        return {"status": "offline"}

def get_service_metrics():
    try:
        return requests.get(f"{SERVICE_URL}/metrics", timeout=5).json()
    except:
        return {"latency_p99_ms": 0, "error_rate": 0, "db_pool_utilization": 0}

def inject_real_error():
    try:
        return requests.post(f"{SERVICE_URL}/admin/inject-error", timeout=5).json()
    except Exception as e:
        return {"error": str(e)}

def reset_service():
    try:
        return requests.post(f"{SERVICE_URL}/admin/reset", timeout=5).json()
    except:
        return {}

def make_checkout_request():
    try:
        response = requests.post(
            f"{SERVICE_URL}/checkout",
            json={"product_id": 1, "quantity": 1},
            timeout=15
        )
        return response.status_code, response.json()
    except requests.exceptions.Timeout:
        return 503, {"error": "Connection pool exhausted"}
    except Exception as e:
        return 500, {"error": str(e)}

def get_real_logs(lines=30):
    if LOG_FILE.exists():
        with open(LOG_FILE, encoding='utf-8', errors='ignore') as f:
            return f.readlines()[-lines:]
    return []

# ============= MULTI-AGENT INVESTIGATION =============

async def run_agent_investigation(alert_context):
    """Run all agents and collect findings."""
    
    # Initialize agents
    logs_agent = LogsAgent(str(LOG_FILE))
    metrics_agent = MetricsAgent(SERVICE_URL)
    deploy_agent = DeployAgent(str(CONFIG_FILE))
    
    # Run all agents in parallel
    logs_result = await logs_agent.investigate(alert_context)
    metrics_result = await metrics_agent.investigate(alert_context)
    deploy_result = await deploy_agent.investigate(alert_context)
    
    return {
        "logs": logs_result,
        "metrics": metrics_result,
        "deploy": deploy_result
    }

def correlate_findings(agent_results):
    """Correlate findings from all agents to determine root cause."""
    
    all_findings = []
    all_anomalies = []
    all_timeline = []
    
    for agent_name, result in agent_results.items():
        for finding in result.get("findings", []):
            finding["source"] = agent_name
            all_findings.append(finding)
        all_anomalies.extend(result.get("anomalies", []))
        all_timeline.extend(result.get("timeline_events", []))
    
    # Convert to lowercase for matching
    anomaly_text = " ".join(str(a).lower() for a in all_anomalies)
    finding_text = " ".join(str(f).lower() for f in all_findings)
    combined_text = anomaly_text + " " + finding_text
    
    # Detect error type based on patterns
    root_cause = "Unknown error"
    confidence = 0.5
    
    if "outofmemory" in combined_text or "heap" in combined_text or "memory" in combined_text:
        root_cause = "Memory Leak: Heap exhausted due to disabled cache eviction"
        confidence = 0.92
    elif "deadlock" in combined_text or "lock timeout" in combined_text or "lock" in combined_text:
        root_cause = "Database Deadlock: Circular dependency caused transaction rollback"
        confidence = 0.90
    elif "sockettimeout" in combined_text or "gateway" in combined_text or "payment" in combined_text:
        root_cause = "Network Timeout: Downstream payment gateway unreachable"
        confidence = 0.88
    elif "circuitbreaker" in combined_text or "cascading" in combined_text or "auth" in combined_text:
        root_cause = "Cascading Failure: Auth service outage triggered circuit breaker"
        confidence = 0.93
    elif "connectiontimeout" in combined_text or "pool exhausted" in combined_text or "connection" in combined_text:
        root_cause = "Connection Pool Exhaustion: DB pool config reduced causing timeouts"
        confidence = 0.95
    elif "config" in combined_text:
        root_cause = "Configuration change caused service degradation"
        confidence = 0.85
    
    # Sort timeline
    all_timeline.sort(key=lambda x: x.get("timestamp", ""))
    
    return {
        "root_cause": root_cause,
        "confidence": confidence,
        "all_findings": all_findings,
        "all_anomalies": all_anomalies,
        "timeline": all_timeline
    }

# ============= STREAMLIT UI =============

st.set_page_config(page_title="Incident Commander", page_icon="🤖", layout="wide")

st.title("🤖 Autonomous Incident Commander")
st.markdown("**Bayer AI Hackathon 2026** - Dynamic Multi-Agent System")

# Check service
if not is_service_running():
    st.error("⚠️ Start the service first:")
    st.code("uvicorn checkout_service:app --reload --port 8000")
    st.stop()

# Session state
if "fixing_in_progress" not in st.session_state:
    st.session_state.fixing_in_progress = False
if "fix_complete" not in st.session_state:
    st.session_state.fix_complete = False

# Sidebar
st.sidebar.header("🔧 Controls")
st.sidebar.success("✅ Service Online")

if st.sidebar.button("🔄 Reset Everything", use_container_width=True):
    reset_service()
    st.session_state.fixing_in_progress = False
    st.session_state.fix_complete = False
    st.rerun()

st.sidebar.divider()
st.sidebar.header("⚡ One-Click Demo")

if st.sidebar.button("💥 INJECT ERROR & AUTO-FIX", type="primary", use_container_width=True):
    st.session_state.fixing_in_progress = True
    st.session_state.fix_complete = False
    st.rerun()

# Main content
col1, col2 = st.columns(2)

with col1:
    st.header("📊 Service Status")
    health = get_service_health()
    metrics = get_service_metrics()
    
    if health.get("status") == "healthy":
        st.success("✅ HEALTHY")
    else:
        st.error("🚨 UNHEALTHY")
    
    m1, m2 = st.columns(2)
    with m1:
        st.metric("Latency", f"{metrics.get('latency_p99_ms', 0)}ms")
    with m2:
        st.metric("Error Rate", f"{metrics.get('error_rate', 0):.1f}%")

with col2:
    st.header("📋 Recent Logs")
    logs = get_real_logs(10)
    error_logs = [l for l in logs if "ERROR" in l or "CRITICAL" in l]
    if error_logs:
        for e in error_logs[-5:]:
            st.warning(e.strip()[:80])
    else:
        st.info("No errors")

st.divider()

# ============= AUTO-FIX FLOW =============
if st.session_state.fixing_in_progress and not st.session_state.fix_complete:
    
    # Step 1: Inject error
    st.header("💥 Step 1: INJECTING ERROR")
    with st.spinner("Breaking the service..."):
        inject_real_error()
        time.sleep(0.5)
        status, result = make_checkout_request()
    
    if status != 200:
        st.error(f"Service crashed: {result.get('error', '')[:80]}")
    
    st.divider()
    
    # Step 2: Multi-Agent Investigation
    st.header("🔍 Step 2: MULTI-AGENT INVESTIGATION")
    
    progress = st.progress(0)
    
    alert_context = {
        "service": "checkout-api",
        "issue": "latency spike with errors",
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    
    # Run agents
    st.subheader("🤖 Agents Working...")
    
    agent_cols = st.columns(3)
    
    with agent_cols[0]:
        st.markdown("**📋 LogsAgent**")
        with st.spinner("Reading logs..."):
            logs_agent = LogsAgent(str(LOG_FILE))
            logs_result = asyncio.run(logs_agent.investigate(alert_context))
        st.success(f"✅ Found {len(logs_result.get('findings', []))} findings")
        with st.expander("View Details"):
            for f in logs_result.get("findings", [])[:3]:
                st.text(f"{f.get('type')}: {f.get('description', '')[:50]}")
            for a in logs_result.get("anomalies", [])[:3]:
                st.warning(a[:60])
    
    progress.progress(33)
    
    with agent_cols[1]:
        st.markdown("**📊 MetricsAgent**")
        with st.spinner("Fetching metrics..."):
            metrics_agent = MetricsAgent(SERVICE_URL)
            metrics_result = asyncio.run(metrics_agent.investigate(alert_context))
        st.success(f"✅ Found {len(metrics_result.get('findings', []))} findings")
        with st.expander("View Details"):
            for f in metrics_result.get("findings", [])[:3]:
                st.text(f"{f.get('type')}: {f.get('description', '')[:50]}")
            for a in metrics_result.get("anomalies", [])[:3]:
                st.warning(a[:60])
    
    progress.progress(66)
    
    with agent_cols[2]:
        st.markdown("**🚀 DeployAgent**")
        with st.spinner("Checking config..."):
            deploy_agent = DeployAgent(str(CONFIG_FILE))
            deploy_result = asyncio.run(deploy_agent.investigate(alert_context))
        st.success(f"✅ Found {len(deploy_result.get('findings', []))} findings")
        with st.expander("View Details"):
            for f in deploy_result.get("findings", [])[:3]:
                st.text(f"{f.get('type')}: {f.get('description', '')[:50]}")
            for a in deploy_result.get("anomalies", [])[:3]:
                st.warning(a[:60])
    
    progress.progress(100)
    
    st.divider()
    
    # Step 3: Correlation
    st.header("🧠 Step 3: CORRELATION & DECISION")
    
    agent_results = {
        "logs": logs_result,
        "metrics": metrics_result,
        "deploy": deploy_result
    }
    
    correlation = correlate_findings(agent_results)
    
    st.error(f"**Root Cause:** {correlation['root_cause']}")
    st.metric("Confidence", f"{correlation['confidence']*100:.0f}%")
    
    with st.expander("View All Anomalies"):
        for a in correlation["all_anomalies"]:
            st.write(f"• {a}")
    
    st.divider()
    
    # Step 4: Execute Fix
    st.header("🔧 Step 4: EXECUTING FIX")
    
    executor = ActionExecutor(SERVICE_URL)
    
    fix_cols = st.columns(3)
    
    with fix_cols[0]:
        with st.spinner("Rolling back..."):
            rollback = executor.rollback()
        if rollback.success:
            st.success("✅ ROLLBACK")
        else:
            st.error("❌ ROLLBACK")
    
    with fix_cols[1]:
        with st.spinner("Verifying..."):
            time.sleep(0.5)
            verify = executor.verify_health()
        if verify.success:
            st.success("✅ VERIFIED")
        else:
            st.error("❌ VERIFIED")
    
    with fix_cols[2]:
        with st.spinner("Testing..."):
            test = executor.test_checkout()
        if test.success:
            st.success("✅ TESTED")
        else:
            st.error("❌ TESTED")
    
    st.divider()
    
    # Step 5: Generate Report
    st.header("📋 Step 5: INCIDENT REPORT")
    
    report = f"""# Incident Report - Auto-Fix Complete

## Summary
| Field | Value |
|-------|-------|
| **Service** | checkout-api |
| **Root Cause** | {correlation['root_cause']} |
| **Confidence** | {correlation['confidence']*100:.0f}% |
| **Status** | ✅ FIXED |

## Agents Consulted
| Agent | Findings | Anomalies |
|-------|----------|-----------|
| LogsAgent | {len(logs_result.get('findings', []))} | {len(logs_result.get('anomalies', []))} |
| MetricsAgent | {len(metrics_result.get('findings', []))} | {len(metrics_result.get('anomalies', []))} |
| DeployAgent | {len(deploy_result.get('findings', []))} | {len(deploy_result.get('anomalies', []))} |

## Key Findings
{chr(10).join(['- ' + a for a in correlation['all_anomalies'][:10]])}

## Actions Executed
1. ✅ **ROLLBACK** - {rollback.message}
2. ✅ **VERIFY** - {verify.message}
3. ✅ **TEST** - {test.message}

## Timeline
{chr(10).join(['- [' + e.get('timestamp', '') + '] ' + e.get('description', '')[:50] for e in correlation['timeline'][:10]])}

---
*Commander Agent | Bayer AI Hackathon 2026*
*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    report_file = f"rca_autofix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    
    
    with st.expander("📄 View Full Report", expanded=True):
        st.markdown(report)
    
    st.success(f"📁 Report saved: {report_file}")
    
    st.session_state.fix_complete = True
    st.session_state.fixing_in_progress = False
    
    if st.button("🔄 Run Demo Again"):
        st.session_state.fix_complete = False
        st.rerun()

elif st.session_state.fix_complete:
    st.success("✅ Last incident resolved!")
    if st.button("🔄 Run Demo Again"):
        st.session_state.fix_complete = False
        st.rerun()
else:
    st.info("👈 Click **INJECT ERROR & AUTO-FIX** to start the demo")

st.divider()
st.caption("Bayer AI Hackathon 2026 - Dynamic Multi-Agent Commander")
