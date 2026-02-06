"""
Action Executor - Actually performs remediation actions.

This module can:
1. Rollback deployments (reset service config)
2. Restart services
3. Scale resources
"""
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ActionResult:
    """Result of executing an action."""
    action: str
    success: bool
    message: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class ActionExecutor:
    """
    Executes remediation actions on real services.
    """
    
    def __init__(self, service_url: str = "http://localhost:8000"):
        self.service_url = service_url
        self.executed_actions = []
    
    def rollback(self) -> ActionResult:
        """
        Rollback the service to a healthy state.
        
        This actually calls the reset endpoint on the service.
        """
        try:
            response = requests.post(f"{self.service_url}/admin/reset", timeout=10)
            
            if response.status_code == 200:
                result = ActionResult(
                    action="ROLLBACK",
                    success=True,
                    message="Service configuration rolled back to healthy state",
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    details=response.json()
                )
            else:
                result = ActionResult(
                    action="ROLLBACK",
                    success=False,
                    message=f"Rollback failed with status {response.status_code}",
                    timestamp=datetime.now().strftime("%H:%M:%S")
                )
        except Exception as e:
            result = ActionResult(
                action="ROLLBACK",
                success=False,
                message=f"Rollback failed: {str(e)}",
                timestamp=datetime.now().strftime("%H:%M:%S")
            )
        
        self.executed_actions.append(result)
        return result
    
    def verify_health(self) -> ActionResult:
        """
        Verify that the service is healthy after remediation.
        """
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            data = response.json()
            
            is_healthy = data.get("status") == "healthy"
            
            result = ActionResult(
                action="VERIFY_HEALTH",
                success=is_healthy,
                message="Service is healthy" if is_healthy else "Service is still unhealthy",
                timestamp=datetime.now().strftime("%H:%M:%S"),
                details=data
            )
        except Exception as e:
            result = ActionResult(
                action="VERIFY_HEALTH",
                success=False,
                message=f"Health check failed: {str(e)}",
                timestamp=datetime.now().strftime("%H:%M:%S")
            )
        
        self.executed_actions.append(result)
        return result
    
    def test_checkout(self) -> ActionResult:
        """
        Test that checkout works after fix.
        """
        try:
            response = requests.post(
                f"{self.service_url}/checkout",
                json={"product_id": 1, "quantity": 1},
                timeout=10
            )
            
            if response.status_code == 200:
                result = ActionResult(
                    action="TEST_CHECKOUT",
                    success=True,
                    message="Checkout test successful - service is working",
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    details=response.json()
                )
            else:
                result = ActionResult(
                    action="TEST_CHECKOUT",
                    success=False,
                    message=f"Checkout still failing: {response.text}",
                    timestamp=datetime.now().strftime("%H:%M:%S")
                )
        except Exception as e:
            result = ActionResult(
                action="TEST_CHECKOUT",
                success=False,
                message=f"Checkout test failed: {str(e)}",
                timestamp=datetime.now().strftime("%H:%M:%S")
            )
        
        self.executed_actions.append(result)
        return result
    
    def execute_remediation(self, action_type: str) -> ActionResult:
        """
        Execute a remediation action based on type.
        """
        if action_type.lower() in ["rollback", "revert", "reset"]:
            return self.rollback()
        elif action_type.lower() in ["verify", "health", "check"]:
            return self.verify_health()
        elif action_type.lower() in ["test", "checkout"]:
            return self.test_checkout()
        else:
            return ActionResult(
                action=action_type,
                success=False,
                message=f"Unknown action type: {action_type}",
                timestamp=datetime.now().strftime("%H:%M:%S")
            )
    
    def get_action_summary(self) -> str:
        """Get a summary of all executed actions."""
        if not self.executed_actions:
            return "No actions executed"
        
        lines = ["## Actions Executed\n"]
        for action in self.executed_actions:
            status = "✅" if action.success else "❌"
            lines.append(f"- [{action.timestamp}] {status} **{action.action}**: {action.message}")
        
        return "\n".join(lines)
