"""
REPORT Phase - Generate RCA report.
"""
from datetime import datetime
from typing import List

from ..models.investigation import InvestigationState
from ..models.report import IncidentReport


class Reporter:
    """
    REPORT phase of the reasoning loop.
    
    Responsibilities:
    - Generate structured incident report
    - Create RCA Markdown artifact
    - Document chain of thought
    """
    
    def generate_report(self, state: InvestigationState) -> IncidentReport:
        """
        Generate the final incident report.
        
        Args:
            state: Completed investigation state
            
        Returns:
            IncidentReport with full RCA
        """
        # Build timeline analysis
        timeline_analysis = self._build_timeline_analysis(state)
        
        # Compile findings
        findings = self._compile_findings(state)
        
        # Build chain of thought
        chain_of_thought = self._build_chain_of_thought(state)
        
        # Calculate investigation duration
        duration = 0.0
        if state.completed_at and state.started_at:
            duration = (state.completed_at - state.started_at).total_seconds()
        
        report = IncidentReport(
            incident_summary=self._build_summary(state),
            timeline_analysis=timeline_analysis,
            findings=findings,
            root_cause=state.root_cause,
            recommended_action=self._format_actions(state.recommended_actions),
            confidence_score=state.root_cause_confidence,
            service=state.alert.service,
            severity=state.alert.severity,
            investigation_duration=duration,
            agents_consulted=list(state.agent_results.keys()),
            chain_of_thought=chain_of_thought
        )
        
        return report
    
    def _build_summary(self, state: InvestigationState) -> str:
        """Build incident summary."""
        return (
            f"Incident detected in {state.alert.service} at {state.alert.timestamp}. "
            f"Issue: {state.alert.issue}. Severity: {state.alert.severity.upper()}. "
            f"Investigation involved {len(state.agent_results)} agents and identified "
            f"root cause with {state.root_cause_confidence*100:.0f}% confidence."
        )
    
    def _build_timeline_analysis(self, state: InvestigationState) -> str:
        """Build timeline analysis from events."""
        events = state.get_all_timeline_events()
        
        if not events:
            return "No timeline events captured during investigation."
        
        lines = ["Timeline of events:"]
        for event in events:
            time = event.get("timestamp", "Unknown time")
            desc = event.get("description", "Unknown event")
            source = event.get("source", "Unknown")
            lines.append(f"- [{time}] ({source}) {desc}")
        
        return "\n".join(lines)
    
    def _compile_findings(self, state: InvestigationState) -> List[str]:
        """Compile findings from all agents."""
        findings = []
        
        for agent_name, result in state.agent_results.items():
            if result.success:
                for finding in result.findings:
                    desc = finding.get("description", str(finding))
                    findings.append(f"[{agent_name.upper()}] {desc}")
                
                for anomaly in result.anomalies:
                    findings.append(f"[{agent_name.upper()} ANOMALY] {anomaly}")
        
        return findings if findings else ["No significant findings recorded."]
    
    def _build_chain_of_thought(self, state: InvestigationState) -> List[str]:
        """Build chain of thought showing reasoning process."""
        chain = []
        
        # Phase 1: Detection
        chain.append(f"DETECT: Received alert for {state.alert.service} - {state.alert.issue}")
        chain.append(f"DETECT: Classified issue as {state.alert.issue_type.value if state.alert.issue_type else 'unknown'}")
        
        # Phase 2: Planning
        chain.append(f"PLAN: {state.planning_reasoning}")
        
        # Phase 3: Investigation
        for step in state.investigation_plan:
            chain.append(f"INVESTIGATE: Called {step.agent.upper()} agent - {step.reason}")
        
        # Phase 4: Decision
        chain.append(f"DECIDE: Root cause identified - {state.root_cause[:100]}...")
        chain.append(f"DECIDE: Confidence score: {state.root_cause_confidence*100:.0f}%")
        
        # Phase 5: Action
        if state.recommended_actions:
            chain.append(f"ACT: Primary recommendation - {state.recommended_actions[0]}")
        
        return chain
    
    def _format_actions(self, actions: List[str]) -> str:
        """Format actions as readable text."""
        if not actions:
            return "No specific actions recommended."
        
        # Return primary action with count of additional actions
        primary = actions[0]
        if len(actions) > 1:
            return f"{primary}\n\nAdditional actions ({len(actions)-1} more):\n" + "\n".join(f"- {a}" for a in actions[1:])
        return primary
