"""
Real Logs Agent - Reads ACTUAL log files from the service.

This agent reads real log files instead of using mock data.
"""
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import re

from .base_agent import BaseAgent


class RealLogsAgent(BaseAgent):
    """
    Agent that reads real log files and extracts error information.
    """
    
    def __init__(self, log_file: str = None):
        super().__init__(
            name="logs",
            description="Reads real service logs and extracts error patterns"
        )
        self.log_file = Path(log_file) if log_file else Path(__file__).parent.parent.parent / "service.log"
    
    async def investigate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read real logs and extract errors.
        
        Args:
            context: Investigation context with alert info
            
        Returns:
            AgentResult with real log findings
        """
        findings = []
        anomalies = []
        timeline_events = []
        
        if not self.log_file.exists():
            return self._create_result(
                success=False,
                findings=[{"type": "error", "description": "Log file not found", "severity": "low"}],
                anomalies=["Log file does not exist"],
                timeline_events=[],
                confidence=0.0
            )
        
        # Read actual log file
        with open(self.log_file) as f:
            logs = f.readlines()
        
        # Parse logs for errors
        error_count = 0
        critical_count = 0
        warning_count = 0
        
        for log in logs[-100:]:  # Last 100 lines
            log = log.strip()
            
            # Extract timestamp
            timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', log)
            timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime("%H:%M")
            time_only = timestamp.split()[-1][:5] if timestamp_match else "00:00"
            
            if "CRITICAL" in log:
                critical_count += 1
                findings.append({
                    "type": "critical_error",
                    "description": log.split(" - ")[-1] if " - " in log else log,
                    "timestamp": time_only,
                    "severity": "critical",
                    "source": "real_logs"
                })
                timeline_events.append({
                    "timestamp": time_only,
                    "description": log.split(" - ")[-1] if " - " in log else log,
                    "type": "critical"
                })
                
            elif "ERROR" in log:
                error_count += 1
                findings.append({
                    "type": "error",
                    "description": log.split(" - ")[-1] if " - " in log else log,
                    "timestamp": time_only,
                    "severity": "high",
                    "source": "real_logs"
                })
                timeline_events.append({
                    "timestamp": time_only,
                    "description": log.split(" - ")[-1] if " - " in log else log,
                    "type": "error"
                })
                
            elif "WARNING" in log and "CONFIGURATION" in log:
                warning_count += 1
                findings.append({
                    "type": "config_change",
                    "description": log.split(" - ")[-1] if " - " in log else log,
                    "timestamp": time_only,
                    "severity": "medium",
                    "source": "real_logs"
                })
                timeline_events.append({
                    "timestamp": time_only,
                    "description": "Configuration changed",
                    "type": "deploy"
                })
        
        # Create anomalies
        if critical_count > 0:
            anomalies.append(f"Found {critical_count} CRITICAL errors in logs")
        if error_count > 0:
            anomalies.append(f"Found {error_count} ERROR entries in logs")
        if warning_count > 0:
            anomalies.append(f"Found {warning_count} configuration changes")
        
        # Check for specific patterns
        full_log_text = "".join(logs[-50:])
        if "ConnectionTimeoutException" in full_log_text:
            anomalies.append("Database connection timeout exception detected")
        if "pool exhausted" in full_log_text.lower():
            anomalies.append("Connection pool exhaustion detected")
        if "max_connections" in full_log_text:
            anomalies.append("Connection pool configuration was modified")
        
        confidence = min(0.95, 0.5 + (error_count * 0.1) + (critical_count * 0.2))
        
        return self._create_result(
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=confidence
        )
