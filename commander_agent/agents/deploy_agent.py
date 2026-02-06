"""
Deploy Intelligence Agent - The Historian.

Maps real-time errors against the timeline of CI/CD deployments and service configuration changes.

THIS IS A MOCK IMPLEMENTATION for demonstration.
Replace with actual deployment tracking logic for production.
"""
import json
from typing import Dict, Any, List

from .base_agent import BaseAgent
from ..models.investigation import InvestigationState, AgentResult


class DeployAgent(BaseAgent):
    """
    Deploy Intelligence Agent - The Historian.
    
    Capabilities:
    - Track CI/CD deployment history
    - Monitor configuration changes
    - Map errors against deployment timeline
    - Identify recent changes as potential causes
    """
    
    def __init__(self, mock_data_path: str = None):
        """
        Initialize Deploy Intelligence Agent.
        
        Args:
            mock_data_path: Path to mock deployment data JSON (optional)
        """
        super().__init__("deploy")
        self.mock_data_path = mock_data_path
        self.mock_data = None
    
    def load_mock_data(self, data: Dict[str, Any] = None):
        """Load mock data for demonstration."""
        if data:
            self.mock_data = data
        elif self.mock_data_path:
            with open(self.mock_data_path, 'r') as f:
                self.mock_data = json.load(f)
    
    async def investigate(self, state: InvestigationState) -> AgentResult:
        """
        Investigate deployments for the given alert context.
        
        For production: Connect to actual CI/CD systems (Jenkins, GitLab, ArgoCD, etc.)
        """
        context = self.get_context_for_query(state)
        
        if self.mock_data:
            return self._analyze_mock_data(context)
        else:
            return self._generate_demo_findings(context)
    
    def _generate_demo_findings(self, context: Dict[str, Any]) -> AgentResult:
        """Generate demo findings matching the hackathon scenario."""
        service = context.get("service", "unknown")
        timestamp = context.get("timestamp", "10:15")
        
        # Demo: Config deployment 15 minutes before incident (hackathon scenario)
        findings = [
            {
                "type": "config_change",
                "description": "Database connection pool configuration updated - max_connections reduced from 100 to 50",
                "timestamp": "10:00",
                "severity": "high",
                "raw_data": {
                    "change_type": "configuration",
                    "component": "database",
                    "changed_by": "config-automation",
                    "commit_id": "a1b2c3d4",
                    "changes": {
                        "db.pool.max_connections": {"old": 100, "new": 50},
                        "db.pool.timeout_ms": {"old": 10000, "new": 5000}
                    }
                }
            },
            {
                "type": "deployment",
                "description": f"Deployment of {service} v2.3.1 with config changes",
                "timestamp": "09:58",
                "severity": "medium",
                "raw_data": {
                    "version": "2.3.1",
                    "previous_version": "2.3.0",
                    "deploy_type": "config_update",
                    "deployed_by": "ci-pipeline",
                    "rollback_available": True
                }
            }
        ]
        
        anomalies = [
            "Configuration change detected 15 minutes before incident",
            "DB pool max_connections reduced by 50% (100 → 50)",
            "Connection timeout reduced from 10s to 5s"
        ]
        
        timeline_events = [
            {
                "timestamp": "09:58",
                "description": f"Deployment started: {service} v2.3.1",
                "type": "deployment"
            },
            {
                "timestamp": "10:00",
                "description": "Configuration applied: DB pool settings changed",
                "type": "config_change"
            },
            {
                "timestamp": "10:00",
                "description": "Deployment completed successfully",
                "type": "deployment"
            }
        ]
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=0.9,
            raw_data={
                "deployments_in_window": 1,
                "config_changes_in_window": 1,
                "time_window": "last 30 minutes",
                "rollback_command": f"kubectl rollout undo deployment/{service}"
            }
        )
    
    def _analyze_mock_data(self, context: Dict[str, Any]) -> AgentResult:
        """Analyze provided mock deployment data."""
        deployments = self.mock_data.get("deployments", [])
        config_changes = self.mock_data.get("config_changes", [])
        
        findings = []
        anomalies = []
        timeline_events = []
        
        # Analyze deployments
        for deploy in deployments:
            findings.append({
                "type": "deployment",
                "description": deploy.get("description", "Deployment detected"),
                "timestamp": deploy.get("timestamp", ""),
                "severity": "medium",
                "raw_data": deploy
            })
            timeline_events.append({
                "timestamp": deploy.get("timestamp", ""),
                "description": deploy.get("description", ""),
                "type": "deployment"
            })
        
        # Analyze config changes
        for change in config_changes:
            findings.append({
                "type": "config_change",
                "description": change.get("description", "Config change detected"),
                "timestamp": change.get("timestamp", ""),
                "severity": "high",
                "raw_data": change
            })
            anomalies.append(f"Config change: {change.get('description', '')}")
        
        return AgentResult(
            agent_name=self.name,
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=0.85 if findings else 0.3,
            raw_data={
                "total_deployments": len(deployments),
                "total_config_changes": len(config_changes)
            }
        )
