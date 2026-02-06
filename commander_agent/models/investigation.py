"""
Investigation state model - tracks the entire investigation workflow.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from .alert import Alert


class InvestigationPhase(Enum):
    """Current phase in the reasoning loop."""
    DETECT = "detect"
    PLAN = "plan"
    INVESTIGATE = "investigate"
    DECIDE = "decide"
    ACT = "act"
    REPORT = "report"
    COMPLETED = "completed"


@dataclass
class InvestigationStep:
    """A single step in the investigation plan."""
    agent: str  # Which agent to call
    reason: str  # Why this agent is being called
    priority: int  # Order of execution (lower = first)
    status: str = "pending"  # pending, running, completed, failed
    

@dataclass
class AgentResult:
    """
    Standardized result from any sub-agent.
    
    THIS IS WHAT COMMANDER EXPECTS FROM ALL SUB-AGENTS.
    """
    agent_name: str
    success: bool
    findings: List[Dict[str, Any]]  # List of findings
    anomalies: List[str]  # Detected anomalies
    timeline_events: List[Dict[str, Any]]  # Events with timestamps
    confidence: float  # 0.0 to 1.0
    raw_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class InvestigationState:
    """
    Maintains the complete state of an investigation.
    
    This is the central state object passed through all phases.
    """
    # Input
    alert: Alert
    
    # Current phase
    current_phase: InvestigationPhase = InvestigationPhase.DETECT
    
    # Planning output
    investigation_plan: List[InvestigationStep] = field(default_factory=list)
    planning_reasoning: str = ""
    
    # Investigation results
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)
    
    # Correlation output
    timeline: List[Dict[str, Any]] = field(default_factory=list)
    correlations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Decision output
    root_cause: str = ""
    root_cause_confidence: float = 0.0
    
    # Action output  
    recommended_actions: List[str] = field(default_factory=list)
    
    # Metadata
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def add_agent_result(self, result: AgentResult):
        """Add result from a sub-agent."""
        self.agent_results[result.agent_name] = result
    
    def advance_phase(self, next_phase: InvestigationPhase):
        """Move to the next phase."""
        self.current_phase = next_phase
        
    def get_all_anomalies(self) -> List[str]:
        """Get all anomalies from all agents."""
        anomalies = []
        for result in self.agent_results.values():
            anomalies.extend(result.anomalies)
        return anomalies
    
    def get_all_timeline_events(self) -> List[Dict[str, Any]]:
        """Get all timeline events sorted by time."""
        events = []
        for result in self.agent_results.values():
            events.extend(result.timeline_events)
        # Sort by timestamp
        return sorted(events, key=lambda x: x.get("timestamp", ""))
