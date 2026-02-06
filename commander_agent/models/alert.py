"""
Alert model for incoming incident alerts.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum


class Severity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueType(Enum):
    """Types of issues that can be detected."""
    LATENCY = "latency"
    ERROR = "error"
    TIMEOUT = "timeout"
    MEMORY_LEAK = "memory_leak"
    CPU_SPIKE = "cpu_spike"
    CONNECTION_FAILURE = "connection_failure"
    UNKNOWN = "unknown"


@dataclass
class Alert:
    """
    Represents an incoming incident alert.
    
    This is the primary input to the Commander Agent.
    """
    service: str
    issue: str
    severity: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Derived fields (populated by detector)
    issue_type: Optional[IssueType] = None
    parsed_timestamp: Optional[datetime] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """Create Alert from dictionary input."""
        return cls(
            service=data.get("service", "unknown"),
            issue=data.get("issue", "unknown issue"),
            severity=data.get("severity", "medium"),
            timestamp=data.get("timestamp", datetime.now().strftime("%H:%M")),
            metadata=data.get("metadata", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service": self.service,
            "issue": self.issue,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "issue_type": self.issue_type.value if self.issue_type else None
        }
