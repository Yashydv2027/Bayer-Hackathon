"""
ACT Phase - Action recommendation.
"""
from typing import List, Dict, Any

from ..models.investigation import InvestigationState
from ..models.alert import IssueType


class ActionRecommender:
    """
    ACT phase of the reasoning loop.
    
    Responsibilities:
    - Recommend remediation actions based on root cause
    - Prioritize actions by impact and urgency
    """
    
    # Action templates by root cause pattern
    ACTION_TEMPLATES = {
        "deployment": [
            "IMMEDIATE: Rollback the recent deployment",
            "Verify service health after rollback",
            "Review deployment changes before redeployment"
        ],
        "config": [
            "IMMEDIATE: Revert configuration change",
            "Validate configuration values",
            "Implement config change validation in CI/CD"
        ],
        "database": [
            "IMMEDIATE: Check database connection pool settings",
            "Restart affected service instances",
            "Monitor DB connection metrics"
        ],
        "memory": [
            "IMMEDIATE: Restart affected pods/instances",
            "Increase memory limits if appropriate",
            "Investigate memory leak in application code"
        ],
        "cpu": [
            "IMMEDIATE: Scale out affected service",
            "Identify CPU-intensive operations",
            "Optimize or throttle heavy operations"
        ],
        "default": [
            "IMMEDIATE: Escalate to on-call engineer",
            "Gather additional diagnostic data",
            "Monitor for issue recurrence"
        ]
    }
    
    def __init__(self, llm_client=None):
        """Initialize with optional LLM client."""
        self.llm_client = llm_client
    
    async def recommend(self, state: InvestigationState) -> InvestigationState:
        """
        Generate recommended actions based on root cause.
        
        Args:
            state: Current investigation state with root cause
            
        Returns:
            Updated state with recommended actions
        """
        if self.llm_client:
            actions = await self._llm_recommend(state)
        else:
            actions = self._heuristic_recommend(state)
        
        state.recommended_actions = actions
        
        return state
    
    async def _llm_recommend(self, state: InvestigationState) -> List[str]:
        """Use LLM to generate recommendations."""
        prompt = f"""
Based on this root cause: {state.root_cause}

And investigation findings for service: {state.alert.service}

Recommend specific remediation actions. Prioritize by urgency.
Return a JSON list of action strings.
"""
        response = await self.llm_client.complete(
            prompt=prompt,
            system_prompt="You are an SRE expert. Recommend practical, specific remediation actions."
        )
        
        try:
            import json
            return json.loads(response)
        except:
            return [response]
    
    def _heuristic_recommend(self, state: InvestigationState) -> List[str]:
        """Heuristic action recommendation."""
        root_cause_lower = state.root_cause.lower()
        
        # Match root cause to action template
        if "deployment" in root_cause_lower or "deploy" in root_cause_lower:
            actions = self.ACTION_TEMPLATES["deployment"].copy()
        elif "config" in root_cause_lower:
            actions = self.ACTION_TEMPLATES["config"].copy()
        elif "database" in root_cause_lower or "db" in root_cause_lower or "connection" in root_cause_lower:
            actions = self.ACTION_TEMPLATES["database"].copy()
        elif "memory" in root_cause_lower or "oom" in root_cause_lower:
            actions = self.ACTION_TEMPLATES["memory"].copy()
        elif "cpu" in root_cause_lower:
            actions = self.ACTION_TEMPLATES["cpu"].copy()
        else:
            actions = self.ACTION_TEMPLATES["default"].copy()
        
        # Add service-specific context
        actions = [a.replace("affected service", state.alert.service) for a in actions]
        
        # Add severity-based urgency
        if state.alert.severity.lower() == "critical":
            actions.insert(0, "CRITICAL: Page on-call team immediately")
        elif state.alert.severity.lower() == "high":
            actions.insert(0, "HIGH PRIORITY: Engage incident response team")
        
        return actions
