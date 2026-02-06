"""
Report model - the final RCA output.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List
from datetime import datetime


@dataclass
class IncidentReport:
    """
    Final incident report - Root Cause Analysis output.
    
    This is the primary output of the Commander Agent.
    """
    incident_summary: str
    timeline_analysis: str
    findings: List[str]
    root_cause: str
    recommended_action: str
    confidence_score: float
    
    # Additional metadata
    service: str = ""
    severity: str = ""
    investigation_duration: float = 0.0
    agents_consulted: List[str] = field(default_factory=list)
    chain_of_thought: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "incident_summary": self.incident_summary,
            "timeline_analysis": self.timeline_analysis,
            "findings": self.findings,
            "root_cause": self.root_cause,
            "recommended_action": self.recommended_action,
            "confidence_score": self.confidence_score,
            "metadata": {
                "service": self.service,
                "severity": self.severity,
                "investigation_duration_seconds": self.investigation_duration,
                "agents_consulted": self.agents_consulted
            }
        }
    
    def to_markdown(self) -> str:
        """Generate RCA Markdown artifact."""
        md = f"""# Incident Report - Root Cause Analysis

## Summary
{self.incident_summary}

## Service Information
- **Service**: {self.service}
- **Severity**: {self.severity}
- **Investigation Duration**: {self.investigation_duration:.2f} seconds

## Timeline Analysis
{self.timeline_analysis}

## Findings
"""
        for i, finding in enumerate(self.findings, 1):
            md += f"{i}. {finding}\n"
        
        md += f"""
## Root Cause
**{self.root_cause}**

**Confidence Score**: {self.confidence_score * 100:.1f}%

## Recommended Action
{self.recommended_action}

## Chain of Thought
"""
        for i, thought in enumerate(self.chain_of_thought, 1):
            md += f"{i}. {thought}\n"
        
        md += f"""
---
*Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Agents consulted: {', '.join(self.agents_consulted)}*
"""
        return md
