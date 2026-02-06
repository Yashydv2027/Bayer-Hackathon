"""
Metrics Agent - Calls REAL metrics endpoint.

This agent calls the actual /metrics endpoint and analyzes:
- Latency spikes
- Error rate changes
- Resource utilization
"""
from typing import Dict, Any
from datetime import datetime
import requests

from .base_agent import BaseAgent


class MetricsAgent(BaseAgent):
    """
    Telemetry Analyst - Fetches real metrics from service.
    """
    
    def __init__(self, service_url: str = "http://localhost:8000"):
        super().__init__(
            name="metrics",
            description="Real-time metrics analysis from service endpoints"
        )
        self.service_url = service_url
        self.baseline = {
            "latency_p99_ms": 150,
            "error_rate": 0.1,
            "db_pool_utilization": 0.3
        }
    
    async def investigate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch real metrics and analyze anomalies.
        """
        findings = []
        anomalies = []
        timeline_events = []
        
        try:
            # Fetch real metrics
            response = requests.get(f"{self.service_url}/metrics", timeout=5)
            metrics = response.json()
            
            # Fetch health
            health_response = requests.get(f"{self.service_url}/health", timeout=5)
            health = health_response.json()
            
        except Exception as e:
            return self._create_result(
                success=False,
                findings=[{"type": "error", "description": f"Failed to fetch metrics: {e}", "severity": "high"}],
                anomalies=["Metrics endpoint unreachable"],
                timeline_events=[],
                confidence=0.0
            )
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Analyze latency
        latency = metrics.get("latency_p99_ms", 0)
        if latency > 500:
            severity = "critical" if latency > 1500 else "high"
            findings.append({
                "type": "latency_spike",
                "description": f"P99 latency at {latency}ms (baseline: {self.baseline['latency_p99_ms']}ms)",
                "timestamp": timestamp,
                "severity": severity
            })
            anomalies.append(f"Latency spike: {latency}ms ({latency/self.baseline['latency_p99_ms']:.1f}x above baseline)")
            timeline_events.append({
                "timestamp": timestamp,
                "description": f"Latency spike to {latency}ms",
                "type": "metrics"
            })
        
        # Analyze error rate
        error_rate = metrics.get("error_rate", 0)
        if error_rate > 1:
            findings.append({
                "type": "error_rate_spike",
                "description": f"Error rate at {error_rate}% (baseline: {self.baseline['error_rate']}%)",
                "timestamp": timestamp,
                "severity": "high"
            })
            anomalies.append(f"Error rate spike: {error_rate}% ({error_rate/self.baseline['error_rate']:.0f}x increase)")
            timeline_events.append({
                "timestamp": timestamp,
                "description": f"Error rate spike to {error_rate}%",
                "type": "metrics"
            })
        
        # Analyze DB pool
        pool_util = metrics.get("db_pool_utilization", 0)
        if pool_util > 0.8:
            findings.append({
                "type": "resource_saturation",
                "description": f"DB connection pool at {pool_util*100:.0f}% utilization",
                "timestamp": timestamp,
                "severity": "critical" if pool_util >= 1.0 else "high"
            })
            anomalies.append(f"DB pool saturation: {pool_util*100:.0f}%")
            timeline_events.append({
                "timestamp": timestamp,
                "description": f"DB pool at {pool_util*100:.0f}%",
                "type": "metrics"
            })
        
        # Check service health status
        if health.get("status") != "healthy":
            findings.append({
                "type": "service_unhealthy",
                "description": f"Service health status: {health.get('status')}",
                "timestamp": timestamp,
                "severity": "critical"
            })
            anomalies.append("Service reporting unhealthy status")
        
        # Calculate confidence based on findings
        confidence = min(0.95, 0.2 + (len(findings) * 0.15) + (len(anomalies) * 0.1))
        
        return self._create_result(
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=confidence
        )
