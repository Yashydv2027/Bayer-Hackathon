"""
Metrics Agent - The Telemetry Analyst.

Monitors performance counters (CPU, p99 Latency, Memory Leak patterns) to spot anomalies.

THIS IS A MOCK IMPLEMENTATION for demonstration.
Replace with actual metrics analysis logic for production.
"""
import json
from typing import Dict, Any, List

from .base_agent import BaseAgent
from ..models.investigation import InvestigationState, AgentResult


class MetricsAgent(BaseAgent):
    """
    Metrics Agent - The Telemetry Analyst.
    
    Capabilities:
    - Monitor CPU, memory, latency metrics
    - Detect p99 latency spikes
    - Identify memory leak patterns
    - Analyze resource utilization
    """
    
    def __init__(self, mock_data_path: str = None):
        """
        Initialize Metrics Agent.
        
        Args:
            mock_data_path: Path to mock metrics data JSON (optional)
        """
        super().__init__("metrics")
        self.mock_data_path = mock_data_path
        self.mock_data = None
    
    def load_mock_data(self, data: Dict[str, Any] = None):
        """Load mock data for demonstration."""
        if data:
            self.mock_data = data
        elif self.mock_data_path:
            with open(self.mock_data_path, 'r') as f:
                self.mock_data = json.load(f)
    
    async def investigate(self, state: InvestigationState) -> AgentResult:
        """
        Investigate metrics for the given alert context.
        
        For production: Connect to actual metrics systems (Prometheus, Datadog, etc.)
        """
        context = self.get_context_for_query(state)
        
        if self.mock_data:
            return self._analyze_mock_data(context)
        else:
            return self._generate_demo_findings(context)
    
    def _generate_demo_findings(self, context: Dict[str, Any]) -> AgentResult:
        """Generate demo findings matching the hackathon scenario."""
        service = context.get("service", "unknown")
        timestamp = context.get("timestamp", "10:15")
        
        # Demo: Latency spike to 2000ms matching hackathon scenario
        findings = [
            {
                "type": "latency_spike",
                "description": f"P99 latency spiked to 2000ms (baseline: 150ms)",
                "timestamp": "10:12",
                "severity": "critical",
                "raw_data": {
                    "metric": "p99_latency_ms",
                    "current_value": 2000,
                    "baseline_value": 150,
                    "increase_percentage": 1233
                }
            },
            {
                "type": "throughput_drop",
                "description": "Request throughput dropped 60% during incident",
                "timestamp": "10:12",
                "severity": "high",
                "raw_data": {
                    "metric": "requests_per_second",
                    "before": 450,
                    "during": 180
                }
            },
            {
                "type": "error_rate_spike",
                "description": "Error rate increased from 0.1% to 15%",
                "timestamp": "10:12",
                "severity": "high",
                "raw_data": {
                    "metric": "error_rate",
                    "before": 0.001,
                    "during": 0.15
                }
            },
            {
                "type": "connection_pool",
                "description": "DB connection pool utilization at 100%",
                "timestamp": "10:10",
                "severity": "critical",
                "raw_data": {
                    "metric": "db_pool_utilization",
                    "value": 1.0,
                    "max_connections": 50,
                    "active_connections": 50,
                    "waiting_threads": 127
                }
            }
        ]
        
        anomalies = [
            "P99 latency deviation: 13x above baseline",
            "Request throughput drop: -60%",
            "Error rate spike: 150x increase",
            "DB connection pool saturation at 100%"
        ]
        
        timeline_events = [
            {
                "timestamp": "10:00",
                "description": "Baseline metrics - P99: 150ms, Error rate: 0.1%",
                "type": "baseline"
            },
            {
                "timestamp": "10:10",
                "description": "DB connection pool utilization spike to 100%",
                "type": "warning"
            },
            {
                "timestamp": "10:12",
                "description": "P99 latency spike to 2000ms detected",
                "type": "critical"
            },
            {
                "timestamp": "10:12",
                "description": "Error rate spike to 15%",
                "type": "critical"
            }
        ]
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=0.9,
            raw_data={
                "metrics_analyzed": ["p99_latency", "error_rate", "throughput", "cpu", "memory", "db_pool"],
                "time_range": "10:00 - 10:20",
                "data_points": 120
            }
        )
    
    def _analyze_mock_data(self, context: Dict[str, Any]) -> AgentResult:
        """Analyze provided mock metrics data."""
        metrics = self.mock_data.get("metrics", {})
        
        findings = []
        anomalies = []
        timeline_events = []
        
        # Check latency
        if "latency" in metrics:
            latency_data = metrics["latency"]
            if latency_data.get("current", 0) > latency_data.get("baseline", 100) * 2:
                findings.append({
                    "type": "latency_spike",
                    "description": f"Latency spike: {latency_data.get('current')}ms",
                    "timestamp": latency_data.get("timestamp", ""),
                    "severity": "high",
                    "raw_data": latency_data
                })
                anomalies.append(f"Latency {latency_data.get('current')}ms exceeds baseline")
        
        # Check CPU
        if "cpu" in metrics:
            cpu_data = metrics["cpu"]
            if cpu_data.get("utilization", 0) > 80:
                findings.append({
                    "type": "cpu_spike",
                    "description": f"High CPU: {cpu_data.get('utilization')}%",
                    "timestamp": cpu_data.get("timestamp", ""),
                    "severity": "medium",
                    "raw_data": cpu_data
                })
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=0.8 if findings else 0.3,
            raw_data={"metrics_checked": list(metrics.keys())}
        )
