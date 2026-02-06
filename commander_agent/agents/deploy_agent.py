"""
Deploy Agent - Checks REAL configuration changes.

This agent reads the actual service_config.json and compares:
- Current vs default configuration
- Deployment timestamps
- Config change history
"""
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import json

from .base_agent import BaseAgent


class DeployAgent(BaseAgent):
    """
    Historian - Tracks real deployment and config changes.
    """
    
    def __init__(self, config_file: str = None):
        super().__init__(
            name="deploy",
            description="Deployment intelligence - tracks config changes"
        )
        self.config_file = Path(config_file) if config_file else Path(__file__).parent.parent.parent / "service_config.json"
        self.default_config = {
            "db_pool_max_connections": 100,
            "db_timeout_seconds": 10,
            "is_healthy": True,
            "version": "2.3.0"
        }
    
    async def investigate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check for configuration changes.
        """
        findings = []
        anomalies = []
        timeline_events = []
        
        if not self.config_file.exists():
            return self._create_result(
                success=False,
                findings=[{"type": "info", "description": "No config file found", "severity": "low"}],
                anomalies=[],
                timeline_events=[],
                confidence=0.5
            )
        
        # Read current config
        try:
            with open(self.config_file) as f:
                current_config = json.load(f)
        except Exception as e:
            return self._create_result(
                success=False,
                findings=[{"type": "error", "description": f"Failed to read config: {e}", "severity": "medium"}],
                anomalies=["Config file unreadable"],
                timeline_events=[],
                confidence=0.0
            )
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Compare with defaults
        changes_found = []
        
        # Check DB pool size
        current_pool = current_config.get("db_pool_max_connections", 100)
        default_pool = self.default_config["db_pool_max_connections"]
        if current_pool != default_pool:
            change_desc = f"DB pool max_connections changed: {default_pool} → {current_pool}"
            changes_found.append(change_desc)
            findings.append({
                "type": "config_change",
                "description": change_desc,
                "timestamp": timestamp,
                "severity": "high" if current_pool < default_pool else "medium"
            })
            anomalies.append(f"DB pool reduced by {((default_pool - current_pool) / default_pool * 100):.0f}%")
        
        # Check timeout
        current_timeout = current_config.get("db_timeout_seconds", 10)
        default_timeout = self.default_config["db_timeout_seconds"]
        if current_timeout != default_timeout:
            change_desc = f"DB timeout changed: {default_timeout}s → {current_timeout}s"
            changes_found.append(change_desc)
            findings.append({
                "type": "config_change",
                "description": change_desc,
                "timestamp": timestamp,
                "severity": "medium"
            })
            anomalies.append(f"DB timeout reduced from {default_timeout}s to {current_timeout}s")
        
        # Check version
        current_version = current_config.get("version", "2.3.0")
        default_version = self.default_config["version"]
        if current_version != default_version:
            findings.append({
                "type": "deployment",
                "description": f"Version changed: {default_version} → {current_version}",
                "timestamp": timestamp,
                "severity": "medium"
            })
        
        # Check deployment timestamp
        last_deployment = current_config.get("last_deployment")
        if last_deployment:
            findings.append({
                "type": "deployment",
                "description": f"Last deployment at {last_deployment}",
                "timestamp": last_deployment,
                "severity": "medium"
            })
            timeline_events.append({
                "timestamp": last_deployment,
                "description": "Configuration deployment",
                "type": "deploy"
            })
            anomalies.append(f"Recent deployment detected at {last_deployment}")
        
        # Check health flag
        if not current_config.get("is_healthy", True):
            findings.append({
                "type": "config_flag",
                "description": "Service marked as unhealthy in config",
                "timestamp": timestamp,
                "severity": "critical"
            })
            anomalies.append("Config has is_healthy=False")
        
        # Add timeline events for changes
        if changes_found:
            timeline_events.append({
                "timestamp": timestamp,
                "description": f"Config changes detected: {len(changes_found)} modifications",
                "type": "deploy"
            })
        
        # Calculate confidence
        confidence = min(0.95, 0.3 + (len(changes_found) * 0.2) + (0.2 if last_deployment else 0))
        
        return self._create_result(
            success=True,
            findings=findings,
            anomalies=anomalies,
            timeline_events=timeline_events,
            confidence=confidence
        )
