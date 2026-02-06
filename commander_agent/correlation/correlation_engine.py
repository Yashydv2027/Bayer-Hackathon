"""
Correlation Engine - Links data across all sources.
"""
from typing import List, Dict, Any
from datetime import datetime, timedelta

from ..models.investigation import InvestigationState


class CorrelationEngine:
    """
    Cross-source correlation analysis.
    
    Responsibilities:
    - Link log errors to metric spikes
    - Map errors against deployment timeline
    - Build unified timeline
    - Identify cause-effect relationships
    """
    
    def __init__(self, time_window_minutes: int = 30):
        """
        Initialize correlation engine.
        
        Args:
            time_window_minutes: Time window for correlation matching
        """
        self.time_window = timedelta(minutes=time_window_minutes)
    
    def correlate(self, state: InvestigationState) -> InvestigationState:
        """
        Perform correlation analysis across all agent results.
        
        Args:
            state: Investigation state with agent results
            
        Returns:
            Updated state with correlations and timeline
        """
        # Build unified timeline
        state.timeline = self._build_timeline(state)
        
        # Find correlations
        state.correlations = self._find_correlations(state)
        
        return state
    
    def _build_timeline(self, state: InvestigationState) -> List[Dict[str, Any]]:
        """Build unified timeline from all sources."""
        timeline = []
        
        # Add alert as first event
        timeline.append({
            "timestamp": state.alert.timestamp,
            "source": "alert",
            "type": "incident",
            "description": f"Alert triggered: {state.alert.issue}",
            "severity": state.alert.severity
        })
        
        # Add events from all agents
        for agent_name, result in state.agent_results.items():
            for event in result.timeline_events:
                event["source"] = agent_name
                timeline.append(event)
        
        # Sort by timestamp
        timeline.sort(key=lambda x: x.get("timestamp", ""))
        
        return timeline
    
    def _find_correlations(self, state: InvestigationState) -> List[Dict[str, Any]]:
        """Find correlations between different data sources."""
        correlations = []
        
        # Get results by type
        logs_result = state.agent_results.get("logs")
        metrics_result = state.agent_results.get("metrics")
        deploy_result = state.agent_results.get("deploy")
        
        # Correlation 1: Deployment → Errors
        if deploy_result and logs_result:
            deploy_correlations = self._correlate_deploy_to_errors(
                deploy_result.findings,
                logs_result.findings
            )
            correlations.extend(deploy_correlations)
        
        # Correlation 2: Deployment → Metrics
        if deploy_result and metrics_result:
            deploy_metrics_correlations = self._correlate_deploy_to_metrics(
                deploy_result.findings,
                metrics_result.findings
            )
            correlations.extend(deploy_metrics_correlations)
        
        # Correlation 3: Errors → Latency
        if logs_result and metrics_result:
            error_latency_correlations = self._correlate_errors_to_latency(
                logs_result.findings,
                metrics_result.findings
            )
            correlations.extend(error_latency_correlations)
        
        return correlations
    
    def _correlate_deploy_to_errors(
        self, 
        deploy_findings: List[Dict], 
        log_findings: List[Dict]
    ) -> List[Dict]:
        """Correlate deployments to error patterns."""
        correlations = []
        
        for deploy in deploy_findings:
            if deploy.get("type") in ["deployment", "config_change"]:
                deploy_time = deploy.get("timestamp", "")
                
                for log_finding in log_findings:
                    if log_finding.get("type") in ["error", "error_pattern", "timeout"]:
                        log_time = log_finding.get("timestamp", "")
                        
                        # Check if error occurred after deployment
                        if self._is_after(log_time, deploy_time):
                            correlations.append({
                                "type": "deployment_to_error",
                                "cause": deploy,
                                "effect": log_finding,
                                "confidence": 0.8,
                                "description": f"Deployment at {deploy_time} likely caused errors at {log_time}"
                            })
        
        return correlations
    
    def _correlate_deploy_to_metrics(
        self,
        deploy_findings: List[Dict],
        metric_findings: List[Dict]
    ) -> List[Dict]:
        """Correlate deployments to metric anomalies."""
        correlations = []
        
        for deploy in deploy_findings:
            if deploy.get("type") in ["deployment", "config_change"]:
                deploy_time = deploy.get("timestamp", "")
                
                for metric in metric_findings:
                    if metric.get("type") in ["latency_spike", "cpu_spike", "memory_spike"]:
                        metric_time = metric.get("timestamp", "")
                        
                        if self._is_after(metric_time, deploy_time):
                            correlations.append({
                                "type": "deployment_to_metric",
                                "cause": deploy,
                                "effect": metric,
                                "confidence": 0.85,
                                "description": f"Deployment at {deploy_time} caused {metric.get('type')} at {metric_time}"
                            })
        
        return correlations
    
    def _correlate_errors_to_latency(
        self,
        log_findings: List[Dict],
        metric_findings: List[Dict]
    ) -> List[Dict]:
        """Correlate error patterns to latency spikes."""
        correlations = []
        
        for log_finding in log_findings:
            if log_finding.get("type") in ["timeout", "connection_error"]:
                log_time = log_finding.get("timestamp", "")
                
                for metric in metric_findings:
                    if metric.get("type") == "latency_spike":
                        metric_time = metric.get("timestamp", "")
                        
                        # Check if times are close
                        if self._times_within_window(log_time, metric_time):
                            correlations.append({
                                "type": "error_to_latency",
                                "cause": log_finding,
                                "effect": metric,
                                "confidence": 0.7,
                                "description": f"{log_finding.get('type')} correlates with latency spike"
                            })
        
        return correlations
    
    def _is_after(self, time1: str, time2: str) -> bool:
        """Check if time1 is after time2."""
        try:
            # Simple string comparison works for HH:MM format
            return time1 >= time2
        except:
            return False
    
    def _times_within_window(self, time1: str, time2: str, window_minutes: int = 15) -> bool:
        """Check if two times are within a window."""
        try:
            # Parse HH:MM format
            t1 = datetime.strptime(time1, "%H:%M")
            t2 = datetime.strptime(time2, "%H:%M")
            diff = abs((t1 - t2).total_seconds())
            return diff <= window_minutes * 60
        except:
            return True  # Assume correlated if can't parse
