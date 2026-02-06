"""
Base Agent - Abstract interface for all sub-agents.

ALL SUB-AGENTS MUST IMPLEMENT THIS INTERFACE.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

from ..models.investigation import InvestigationState, AgentResult


class BaseAgent(ABC):
    """
    Abstract base class for all sub-agents.
    
    INTERFACE CONTRACT:
    - All agents must implement the `investigate` method
    - All agents must return an `AgentResult` object
    - All agents receive the full `InvestigationState` for context
    
    REQUIRED OUTPUT FORMAT (AgentResult):
    {
        "agent_name": str,           # Name of this agent
        "success": bool,             # Whether investigation succeeded
        "findings": [                # List of findings
            {
                "type": str,         # Finding type (error, anomaly, etc.)
                "description": str,  # Human-readable description
                "timestamp": str,    # When it occurred
                "severity": str,     # low/medium/high/critical
                "raw_data": {}       # Original data
            }
        ],
        "anomalies": [str],          # List of detected anomalies
        "timeline_events": [         # Events for timeline
            {
                "timestamp": str,
                "description": str,
                "type": str
            }
        ],
        "confidence": float,         # 0.0 to 1.0
        "raw_data": {},              # Any additional raw data
        "error": str | None          # Error message if failed
    }
    """
    
    def __init__(self, name: str, description: str = ""):
        """Initialize agent with name and description."""
        self.name = name
        self.description = description
    
    def _create_result(self, success: bool, findings: list, anomalies: list, 
                       timeline_events: list, confidence: float, error: str = None) -> Dict[str, Any]:
        """Helper to create standardized result."""
        return {
            "agent_name": self.name,
            "success": success,
            "findings": findings,
            "anomalies": anomalies,
            "timeline_events": timeline_events,
            "confidence": confidence,
            "error": error
        }
    
    @abstractmethod
    async def investigate(self, state: InvestigationState) -> AgentResult:
        """
        Perform investigation based on current state.
        
        Args:
            state: Current investigation state with alert context
            
        Returns:
            AgentResult with findings, anomalies, and timeline events
        """
        pass
    
    def get_context_for_query(self, state: InvestigationState) -> Dict[str, Any]:
        """Extract relevant context for this agent's query."""
        return {
            "service": state.alert.service,
            "issue": state.alert.issue,
            "timestamp": state.alert.timestamp,
            "severity": state.alert.severity,
            "issue_type": state.alert.issue_type.value if state.alert.issue_type else "unknown"
        }
