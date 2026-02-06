"""
Logs Agent - Reads REAL log files from the service.

This agent reads the actual service.log file and extracts:
- Error patterns
- Critical exceptions
- Timeline of events
"""
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import re

from .base_agent import BaseAgent


class LogsAgent(BaseAgent):
    """
    Forensic Expert - Analyzes real log files.
    """
    
    def __init__(self, log_file: str = None):
        super().__init__(
            name="logs",
            description="Forensic log analysis - reads real service logs"
        )
        self.log_file = Path(log_file) if log_file else Path(__file__).parent.parent.parent / "service.log"
    
    async def investigate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read real logs and extract errors.
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
        with open(self.log_file, encoding='utf-8', errors='ignore') as f:
            logs = f.readlines()
        
        # Parse logs
        error_count = 0
        critical_count = 0
        
        for log in logs[-100:]:  # Last 100 lines
            log = log.strip()
            if not log:
                continue
            
            # Extract timestamp
            timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} )?(\d{2}:\d{2}:\d{2})', log)
            time_only = timestamp_match.group(2) if timestamp_match else datetime.now().strftime("%H:%M:%S")
            
            if "CRITICAL" in log:
                critical_count += 1
                message = log.split(" - ")[-1] if " - " in log else log
                findings.append({
                    "type": "critical_error",
                    "description": message,
                    "timestamp": time_only,
                    "severity": "critical"
                })
                timeline_events.append({
                    "timestamp": time_only,
                    "description": message[:100],
                    "type": "logs"
                })
                
            elif "ERROR" in log:
                error_count += 1
                message = log.split(" - ")[-1] if " - " in log else log
                findings.append({
                    "type": "error",
                    "description": message,
                    "timestamp": time_only,
                    "severity": "high"
                })
                timeline_events.append({
                    "timestamp": time_only,
                    "description": message[:100],
                    "type": "logs"
                })
        
        # Analyze patterns
        full_log_text = "".join(logs[-50:])
        
        if "ConnectionTimeoutException" in full_log_text:
            anomalies.append("ConnectionTimeoutException detected - database connection issues")
        if "pool exhausted" in full_log_text.lower():
            anomalies.append("Connection pool exhaustion - all connections in use")
        if "Checkout FAILED" in full_log_text:
            anomalies.append("Checkout transactions failing")
        
        if critical_count > 0:
            anomalies.append(f"Found {critical_count} CRITICAL errors")
        if error_count > 0:
            anomalies.append(f"Found {error_count} ERROR entries")
        
        confidence = min(0.95, 0.3 + (error_count * 0.1) + (critical_count * 0.2))
        
        return self._create_result(
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=confidence
        )
