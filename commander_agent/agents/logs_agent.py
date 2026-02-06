"""
Logs Agent - The Forensic Expert.

Deep-scans distributed application logs to find specific stack traces and error correlations.

THIS IS A MOCK IMPLEMENTATION for demonstration.
Replace with actual log analysis logic for production.
"""
import json
from typing import Dict, Any, List
from pathlib import Path

from .base_agent import BaseAgent
from ..models.investigation import InvestigationState, AgentResult


class LogsAgent(BaseAgent):
    """
    Logs Agent - The Forensic Expert.
    
    Capabilities:
    - Deep-scan application logs
    - Find stack traces and error patterns
    - Identify error correlations
    - Extract error timelines
    """
    
    def __init__(self, mock_data_path: str = None):
        """
        Initialize Logs Agent.
        
        Args:
            mock_data_path: Path to mock log data JSON (optional)
        """
        super().__init__("logs")
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
        Investigate logs for the given alert context.
        
        For production: Connect to actual log aggregation systems (ELK, Splunk, etc.)
        """
        context = self.get_context_for_query(state)
        
        # Use mock data or generate sample findings
        if self.mock_data:
            return self._analyze_mock_data(context)
        else:
            return self._generate_demo_findings(context)
    
    def _generate_demo_findings(self, context: Dict[str, Any]) -> AgentResult:
        """Generate demo findings matching the hackathon scenario."""
        service = context.get("service", "unknown")
        timestamp = context.get("timestamp", "10:15")
        issue = context.get("issue", "")
        
        # Demo: DB connection timeout pattern matching hackathon scenario
        findings = [
            {
                "type": "error_pattern",
                "description": f"Multiple DB connection timeout errors in {service}",
                "timestamp": timestamp,
                "severity": "high",
                "count": 47,
                "raw_data": {
                    "error_type": "ConnectionTimeoutException",
                    "message": "Connection pool exhausted - unable to acquire connection within 5000ms"
                }
            },
            {
                "type": "timeout",
                "description": "Database query timeout - checkout transaction failed",
                "timestamp": timestamp,
                "severity": "critical",
                "raw_data": {
                    "query": "SELECT * FROM inventory WHERE product_id = ?",
                    "timeout_ms": 5000
                }
            },
            {
                "type": "error",
                "description": "Stack trace showing DB pool exhaustion in checkout service",
                "timestamp": timestamp,
                "severity": "high",
                "raw_data": {
                    "stack_trace": [
                        "com.bayer.checkout.CheckoutService.processOrder()",
                        "com.bayer.db.ConnectionPool.getConnection()",
                        "TIMEOUT: Pool exhausted after 5000ms"
                    ]
                }
            }
        ]
        
        anomalies = [
            "Sudden spike in DB connection errors (47 in 5 minutes)",
            "Connection pool reaching 100% utilization",
            "Increased error rate from 0.1% to 15%"
        ]
        
        timeline_events = [
            {
                "timestamp": "10:00",
                "description": "Normal operation - no errors",
                "type": "normal"
            },
            {
                "timestamp": "10:12",
                "description": "First DB connection timeout detected",
                "type": "error"
            },
            {
                "timestamp": "10:15",
                "description": "Connection pool exhaustion - cascade failures",
                "type": "critical"
            }
        ]
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=0.85,
            raw_data={
                "log_lines_scanned": 15420,
                "time_range": "10:00 - 10:20",
                "sources": [f"{service}-pod-1", f"{service}-pod-2", f"{service}-pod-3"]
            }
        )
    
    def _analyze_mock_data(self, context: Dict[str, Any]) -> AgentResult:
        """Analyze provided mock data."""
        logs = self.mock_data.get("logs", [])
        
        findings = []
        anomalies = []
        timeline_events = []
        
        # Analyze logs
        error_count = 0
        for log in logs:
            if log.get("level") in ["ERROR", "CRITICAL"]:
                error_count += 1
                findings.append({
                    "type": "error",
                    "description": log.get("message", "Unknown error"),
                    "timestamp": log.get("timestamp", ""),
                    "severity": "high" if log.get("level") == "ERROR" else "critical",
                    "raw_data": log
                })
                timeline_events.append({
                    "timestamp": log.get("timestamp", ""),
                    "description": log.get("message", "")[:100],
                    "type": "error"
                })
        
        if error_count > 5:
            anomalies.append(f"High error count detected: {error_count} errors")
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=0.8 if findings else 0.3,
            raw_data={"total_logs": len(logs), "error_count": error_count}
        )
