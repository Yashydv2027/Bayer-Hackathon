"""
PLAN Phase - LLM-driven investigation planning.
"""
from typing import List, Dict, Any
import json

from ..models.alert import Alert, IssueType
from ..models.investigation import InvestigationStep, InvestigationState


class Planner:
    """
    PLAN phase of the reasoning loop.
    
    Responsibilities:
    - Analyze the alert context
    - Generate dynamic investigation plan using LLM reasoning
    - Order agent calls based on issue type
    
    NOT hardcoded logic trees - uses reasoning to decide.
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize planner with optional LLM client.
        
        Args:
            llm_client: LLM client for reasoning (uses mock if None)
        """
        self.llm_client = llm_client
    
    async def create_plan(self, state: InvestigationState) -> InvestigationState:
        """
        Create a dynamic investigation plan based on the alert.
        
        Args:
            state: Current investigation state with detected alert
            
        Returns:
            Updated state with investigation plan
        """
        alert = state.alert
        
        # Generate investigation plan using reasoning
        if self.llm_client:
            plan, reasoning = await self._llm_plan(alert)
        else:
            plan, reasoning = self._heuristic_plan(alert)
        
        state.investigation_plan = plan
        state.planning_reasoning = reasoning
        
        return state
    
    async def _llm_plan(self, alert: Alert) -> tuple[List[InvestigationStep], str]:
        """Generate plan using LLM reasoning."""
        prompt = self._build_planning_prompt(alert)
        
        response = await self.llm_client.complete(
            prompt=prompt,
            system_prompt=self._get_system_prompt()
        )
        
        return self._parse_llm_response(response)
    
    def _heuristic_plan(self, alert: Alert) -> tuple[List[InvestigationStep], str]:
        """
        Generate plan using heuristic reasoning (fallback when no LLM).
        
        This simulates what the LLM would do - dynamic ordering based on issue type.
        """
        steps = []
        reasoning_parts = []
        
        issue_type = alert.issue_type or IssueType.UNKNOWN
        
        # Dynamic ordering based on issue type
        if issue_type == IssueType.LATENCY:
            # Latency issues: Check metrics first, then logs, then deployments
            reasoning_parts.append("Latency issue detected - metrics are most likely to show the cause")
            steps = [
                InvestigationStep(
                    agent="metrics",
                    reason="Check for latency spikes, p99 percentiles, and resource saturation",
                    priority=1
                ),
                InvestigationStep(
                    agent="logs", 
                    reason="Look for timeout errors or slow query logs that correlate with latency",
                    priority=2
                ),
                InvestigationStep(
                    agent="deploy",
                    reason="Check if recent deployments or config changes caused the latency",
                    priority=3
                )
            ]
            
        elif issue_type in [IssueType.ERROR, IssueType.TIMEOUT, IssueType.CONNECTION_FAILURE]:
            # Error-based issues: Check logs first for stack traces
            reasoning_parts.append("Error/timeout detected - logs will have stack traces and error details")
            steps = [
                InvestigationStep(
                    agent="logs",
                    reason="Find error stack traces and exception patterns",
                    priority=1
                ),
                InvestigationStep(
                    agent="metrics",
                    reason="Check for correlated metric anomalies around error time",
                    priority=2
                ),
                InvestigationStep(
                    agent="deploy",
                    reason="Identify if deployment caused the errors",
                    priority=3
                )
            ]
            
        elif issue_type in [IssueType.MEMORY_LEAK, IssueType.CPU_SPIKE]:
            # Resource issues: Metrics first
            reasoning_parts.append("Resource issue detected - metrics are the primary data source")
            steps = [
                InvestigationStep(
                    agent="metrics",
                    reason="Analyze memory/CPU patterns and identify the spike timeline",
                    priority=1
                ),
                InvestigationStep(
                    agent="deploy",
                    reason="Check for code changes that could cause resource issues",
                    priority=2
                ),
                InvestigationStep(
                    agent="logs",
                    reason="Look for OOM errors or related application logs",
                    priority=3
                )
            ]
            
        else:
            # Unknown: Check all agents in balanced order
            reasoning_parts.append("Unknown issue type - gathering data from all sources")
            steps = [
                InvestigationStep(agent="logs", reason="Scan for any errors or anomalies", priority=1),
                InvestigationStep(agent="metrics", reason="Check all metric patterns", priority=1),
                InvestigationStep(agent="deploy", reason="Review recent changes", priority=2)
            ]
        
        reasoning_parts.append(f"Plan: {' → '.join(s.agent.upper() for s in sorted(steps, key=lambda x: x.priority))}")
        reasoning = ". ".join(reasoning_parts)
        
        return steps, reasoning
    
    def _build_planning_prompt(self, alert: Alert) -> str:
        """Build prompt for LLM planning."""
        return f"""
You are an expert incident investigator. Analyze this alert and create an investigation plan.

ALERT:
- Service: {alert.service}
- Issue: {alert.issue}
- Severity: {alert.severity}
- Timestamp: {alert.timestamp}
- Classified as: {alert.issue_type.value if alert.issue_type else 'unknown'}

AVAILABLE AGENTS:
1. logs - Deep-scans application logs for stack traces and error patterns
2. metrics - Analyzes CPU, memory, latency, and other performance metrics
3. deploy - Checks CI/CD deployment history and config changes

Create an ordered investigation plan. Return JSON:
{{
    "reasoning": "Your thought process",
    "steps": [
        {{"agent": "agent_name", "reason": "why calling this agent", "priority": 1}}
    ]
}}
"""
    
    def _get_system_prompt(self) -> str:
        """System prompt for the planner."""
        return """You are an AI incident commander. Your job is to create optimal investigation plans.
        
Key principles:
- For latency issues: Check metrics first (shows the spike), then logs, then deployments
- For errors: Check logs first (shows stack traces), then metrics, then deployments  
- For resource issues (CPU/memory): Check metrics first, then deployments, then logs
- Always check deployments when looking for root cause of sudden issues

Prioritize agents that are most likely to reveal the root cause quickly."""

    def _parse_llm_response(self, response: str) -> tuple[List[InvestigationStep], str]:
        """Parse LLM response into steps."""
        try:
            data = json.loads(response)
            steps = [
                InvestigationStep(
                    agent=s["agent"],
                    reason=s["reason"],
                    priority=s["priority"]
                )
                for s in data.get("steps", [])
            ]
            reasoning = data.get("reasoning", "")
            return steps, reasoning
        except (json.JSONDecodeError, KeyError):
            # Fallback if LLM response is malformed
            return self._heuristic_plan(Alert(service="unknown", issue="unknown", severity="medium", timestamp=""))
