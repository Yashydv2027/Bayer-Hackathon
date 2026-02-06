"""
DETECT Phase - Alert parsing and classification.
"""
import re
from datetime import datetime
from typing import Dict, Any

from ..models.alert import Alert, IssueType, Severity


class Detector:
    """
    DETECT phase of the reasoning loop.
    
    Responsibilities:
    - Parse incoming alert JSON
    - Classify issue type
    - Extract structured context
    """
    
    # Keywords mapped to issue types
    ISSUE_KEYWORDS = {
        IssueType.LATENCY: ["latency", "slow", "delay", "response time", "p99", "p95"],
        IssueType.ERROR: ["error", "exception", "fail", "crash", "500", "503"],
        IssueType.TIMEOUT: ["timeout", "timed out", "connection timeout", "db timeout"],
        IssueType.MEMORY_LEAK: ["memory", "oom", "heap", "memory leak", "out of memory"],
        IssueType.CPU_SPIKE: ["cpu", "processor", "cpu spike", "high cpu"],
        IssueType.CONNECTION_FAILURE: ["connection", "refused", "unreachable", "network"],
    }
    
    def detect(self, raw_alert: Dict[str, Any]) -> Alert:
        """
        Parse and classify an incoming alert.
        
        Args:
            raw_alert: Raw JSON alert data
            
        Returns:
            Structured Alert object with classified issue type
        """
        # Create base alert
        alert = Alert.from_dict(raw_alert)
        
        # Classify issue type
        alert.issue_type = self._classify_issue(alert.issue)
        
        # Parse timestamp
        alert.parsed_timestamp = self._parse_timestamp(alert.timestamp)
        
        return alert
    
    def _classify_issue(self, issue_text: str) -> IssueType:
        """Classify the issue type based on keywords."""
        issue_lower = issue_text.lower()
        
        for issue_type, keywords in self.ISSUE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in issue_lower:
                    return issue_type
        
        return IssueType.UNKNOWN
    
    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse various timestamp formats."""
        formats = [
            "%H:%M",
            "%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        # Default to now if parsing fails
        return datetime.now()
    
    def get_detection_summary(self, alert: Alert) -> str:
        """Generate a human-readable detection summary."""
        return (
            f"Detected {alert.issue_type.value.upper()} issue in service '{alert.service}' "
            f"at {alert.timestamp}. Severity: {alert.severity.upper()}"
        )
