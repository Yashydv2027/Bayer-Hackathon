"""
DECIDE Phase - Root cause hypothesis generation.
"""
from typing import Dict, Any, List
import json

from ..models.investigation import InvestigationState


class DecisionMaker:
    """
    DECIDE phase of the reasoning loop.
    
    Responsibilities:
    - Analyze correlated data from all agents
    - Generate root cause hypothesis
    - Calculate confidence score
    """
    
    def __init__(self, llm_client=None):
        """Initialize with optional LLM client."""
        self.llm_client = llm_client
    
    async def decide(self, state: InvestigationState) -> InvestigationState:
        """
        Generate root cause hypothesis based on investigation results.
        
        Args:
            state: Current investigation state with agent results
            
        Returns:
            Updated state with root cause and confidence
        """
        if self.llm_client:
            root_cause, confidence = await self._llm_decide(state)
        else:
            root_cause, confidence = self._heuristic_decide(state)
        
        state.root_cause = root_cause
        state.root_cause_confidence = confidence
        
        return state
    
    async def _llm_decide(self, state: InvestigationState) -> tuple[str, float]:
        """Use LLM to generate root cause hypothesis."""
        prompt = self._build_decision_prompt(state)
        
        response = await self.llm_client.complete(
            prompt=prompt,
            system_prompt="You are an expert at root cause analysis. Analyze the evidence and determine the most likely root cause."
        )
        
        return self._parse_llm_response(response)
    
    def _heuristic_decide(self, state: InvestigationState) -> tuple[str, float]:
        """
        Heuristic root cause analysis (fallback when no LLM).
        
        Analyzes patterns in agent results to determine likely cause.
        """
        findings = []
        anomalies = state.get_all_anomalies()
        timeline = state.get_all_timeline_events()
        
        # Collect all findings
        for agent_name, result in state.agent_results.items():
            for finding in result.findings:
                findings.append({
                    "source": agent_name,
                    **finding
                })
        
        # Pattern matching for common root causes
        root_cause = self._analyze_patterns(findings, anomalies, timeline, state)
        confidence = self._calculate_confidence(state)
        
        return root_cause, confidence
    
    def _analyze_patterns(
        self, 
        findings: List[Dict], 
        anomalies: List[str], 
        timeline: List[Dict],
        state: InvestigationState
    ) -> str:
        """Analyze patterns to determine root cause."""
        
        # Check for deployment correlation
        deploy_result = state.agent_results.get("deploy")
        metrics_result = state.agent_results.get("metrics")
        logs_result = state.agent_results.get("logs")
        
        # Look for deployment + issue correlation
        if deploy_result and deploy_result.success:
            for finding in deploy_result.findings:
                if finding.get("type") == "config_change" or finding.get("type") == "deployment":
                    # Check if deployment time correlates with issue
                    deploy_time = finding.get("timestamp", "")
                    finding_desc = finding.get("description", "")
                    
                    # Check for DB connection issues in logs
                    if logs_result:
                        for log_finding in logs_result.findings:
                            if "db" in str(log_finding).lower() or "connection" in str(log_finding).lower() or "timeout" in str(log_finding).lower():
                                return f"Configuration deployment ({finding_desc}) caused database connection issues, leading to the observed {state.alert.issue}."
                    
                    # Check for latency correlation in metrics
                    if metrics_result:
                        for metric_finding in metrics_result.findings:
                            if metric_finding.get("type") == "latency_spike":
                                return f"Configuration deployment ({finding_desc}) at {deploy_time} caused performance degradation, leading to {state.alert.issue}."
        
        # Check for resource exhaustion pattern
        if metrics_result and metrics_result.success:
            for finding in metrics_result.findings:
                if finding.get("type") in ["memory_leak", "cpu_spike"]:
                    return f"Resource exhaustion detected: {finding.get('description', 'Unknown resource issue')} causing {state.alert.issue}."
        
        # Check for error patterns in logs
        if logs_result and logs_result.success:
            for finding in logs_result.findings:
                if finding.get("type") == "error_pattern":
                    return f"Application error pattern detected: {finding.get('description', 'Unknown error')}."
        
        # Default root cause based on anomalies
        if anomalies:
            return f"Multiple anomalies detected: {'; '.join(anomalies[:3])}. Further investigation needed."
        
        return "Unable to determine definitive root cause. Manual investigation recommended."
    
    def _calculate_confidence(self, state: InvestigationState) -> float:
        """Calculate confidence score based on evidence quality."""
        confidence = 0.0
        factors = []
        
        # Factor 1: Number of successful agent responses
        successful_agents = sum(1 for r in state.agent_results.values() if r.success)
        total_agents = len(state.agent_results)
        if total_agents > 0:
            agent_success_ratio = successful_agents / total_agents
            confidence += agent_success_ratio * 0.3
            factors.append(f"Agent success: {successful_agents}/{total_agents}")
        
        # Factor 2: Correlation count
        if state.correlations:
            correlation_bonus = min(len(state.correlations) * 0.1, 0.3)
            confidence += correlation_bonus
            factors.append(f"Correlations: {len(state.correlations)}")
        
        # Factor 3: Timeline completeness
        if state.timeline:
            timeline_bonus = min(len(state.timeline) * 0.05, 0.2)
            confidence += timeline_bonus
            factors.append(f"Timeline events: {len(state.timeline)}")
        
        # Factor 4: Anomaly detection
        anomalies = state.get_all_anomalies()
        if anomalies:
            anomaly_bonus = min(len(anomalies) * 0.05, 0.2)
            confidence += anomaly_bonus
        
        return min(confidence, 0.95)  # Cap at 95%
    
    def _build_decision_prompt(self, state: InvestigationState) -> str:
        """Build prompt for LLM decision making."""
        findings_str = ""
        for agent_name, result in state.agent_results.items():
            findings_str += f"\n{agent_name.upper()} Agent:\n"
            findings_str += f"  Findings: {result.findings}\n"
            findings_str += f"  Anomalies: {result.anomalies}\n"
        
        return f"""
Analyze this incident and determine the root cause:

ALERT: {state.alert.service} - {state.alert.issue} (Severity: {state.alert.severity})

INVESTIGATION FINDINGS:
{findings_str}

TIMELINE:
{state.get_all_timeline_events()}

Based on the evidence, provide:
1. The most likely root cause
2. A confidence score (0.0 to 1.0)

Return JSON: {{"root_cause": "...", "confidence": 0.X}}
"""
    
    def _parse_llm_response(self, response: str) -> tuple[str, float]:
        """Parse LLM response."""
        try:
            data = json.loads(response)
            return data.get("root_cause", "Unknown"), data.get("confidence", 0.5)
        except json.JSONDecodeError:
            return response, 0.5
