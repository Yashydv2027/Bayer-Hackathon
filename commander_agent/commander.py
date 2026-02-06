"""
Commander Agent - The Orchestrator.

Central coordinator for the multi-agent AI incident response system.
Implements the reasoning loop: DETECT -> PLAN -> INVESTIGATE -> DECIDE -> ACT -> REPORT
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from .models.alert import Alert
from .models.investigation import InvestigationState, InvestigationPhase
from .models.report import IncidentReport

from .reasoning.detector import Detector
from .reasoning.planner import Planner
from .reasoning.investigator import Investigator
from .reasoning.decision_maker import DecisionMaker
from .reasoning.action_recommender import ActionRecommender
from .reasoning.reporter import Reporter

from .correlation.correlation_engine import CorrelationEngine

from .agents.logs_agent import LogsAgent
from .agents.metrics_agent import MetricsAgent
from .agents.deploy_agent import DeployAgent


class CommanderAgent:
    """
    Commander Agent - The Orchestrator.
    
    Central coordinator that:
    1. Receives incident alerts
    2. Orchestrates investigation across specialized agents
    3. Correlates findings
    4. Generates root cause hypothesis
    5. Recommends actions
    6. Produces RCA report
    
    Reasoning Loop: DETECT -> PLAN -> INVESTIGATE -> DECIDE -> ACT -> REPORT
    """
    
    def __init__(self, llm_client=None, debug: bool = True):
        """
        Initialize Commander Agent with all components.
        
        Args:
            llm_client: Optional LLM client for reasoning (uses heuristics if None)
            debug: Enable debug logging
        """
        self.debug = debug
        self.llm_client = llm_client
        
        # Initialize reasoning components
        self.detector = Detector()
        self.planner = Planner(llm_client=llm_client)
        self.investigator = Investigator()
        self.correlation_engine = CorrelationEngine()
        self.decision_maker = DecisionMaker(llm_client=llm_client)
        self.action_recommender = ActionRecommender(llm_client=llm_client)
        self.reporter = Reporter()
        
        # Initialize and register sub-agents
        self._setup_agents()
        
        # Chain of thought log
        self.thought_log = []
    
    def _setup_agents(self):
        """Initialize and register all sub-agents."""
        logs_agent = LogsAgent()
        metrics_agent = MetricsAgent()
        deploy_agent = DeployAgent()
        
        self.investigator.register_agent("logs", logs_agent)
        self.investigator.register_agent("metrics", metrics_agent)
        self.investigator.register_agent("deploy", deploy_agent)
    
    def _log(self, phase: str, message: str):
        """Log a thought to the chain of thought."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {phase}: {message}"
        self.thought_log.append(entry)
        if self.debug:
            print(entry)
    
    async def investigate(self, alert_input: Dict[str, Any]) -> IncidentReport:
        """
        Main entry point - investigate an incident alert.
        
        Args:
            alert_input: Raw alert JSON/dict
            
        Returns:
            IncidentReport with full RCA
        """
        self.thought_log = []  # Reset for new investigation
        
        # ========== DETECT ==========
        self._log("DETECT", f"Received alert: {alert_input}")
        
        alert = self.detector.detect(alert_input)
        state = InvestigationState(alert=alert)
        state.advance_phase(InvestigationPhase.DETECT)
        
        self._log("DETECT", self.detector.get_detection_summary(alert))
        
        # ========== PLAN ==========
        self._log("PLAN", "Creating investigation plan...")
        state.advance_phase(InvestigationPhase.PLAN)
        
        state = await self.planner.create_plan(state)
        
        self._log("PLAN", f"Reasoning: {state.planning_reasoning}")
        self._log("PLAN", f"Plan: {[s.agent for s in sorted(state.investigation_plan, key=lambda x: x.priority)]}")
        
        # ========== INVESTIGATE ==========
        self._log("INVESTIGATE", "Executing investigation plan...")
        state.advance_phase(InvestigationPhase.INVESTIGATE)
        
        state = await self.investigator.investigate(state)
        
        for agent_name, result in state.agent_results.items():
            self._log("INVESTIGATE", f"{agent_name.upper()}: Found {len(result.findings)} findings, {len(result.anomalies)} anomalies")
        
        # ========== CORRELATE ==========
        self._log("CORRELATE", "Correlating findings across data sources...")
        
        state = self.correlation_engine.correlate(state)
        
        self._log("CORRELATE", f"Found {len(state.correlations)} correlations, built timeline with {len(state.timeline)} events")
        
        # ========== DECIDE ==========
        self._log("DECIDE", "Analyzing root cause...")
        state.advance_phase(InvestigationPhase.DECIDE)
        
        state = await self.decision_maker.decide(state)
        
        self._log("DECIDE", f"Root cause: {state.root_cause}")
        self._log("DECIDE", f"Confidence: {state.root_cause_confidence*100:.0f}%")
        
        # ========== ACT ==========
        self._log("ACT", "Generating recommended actions...")
        state.advance_phase(InvestigationPhase.ACT)
        
        state = await self.action_recommender.recommend(state)
        
        self._log("ACT", f"Primary action: {state.recommended_actions[0] if state.recommended_actions else 'None'}")
        
        # ========== REPORT ==========
        self._log("REPORT", "Generating final report...")
        state.advance_phase(InvestigationPhase.REPORT)
        state.completed_at = datetime.now()
        
        report = self.reporter.generate_report(state)
        
        self._log("REPORT", "Investigation complete!")
        
        return report
    
    def get_chain_of_thought(self) -> list:
        """Get the full chain of thought log."""
        return self.thought_log.copy()


# Callback type for external trigger
AlertCallback = callable  # async def callback(alert: dict) -> IncidentReport


class CommanderTrigger:
    """
    Trigger interface for activating Commander Agent.
    
    Can be used by external systems (error generators, monitoring, etc.)
    to trigger investigations.
    """
    
    def __init__(self, commander: CommanderAgent = None):
        """Initialize with optional commander instance."""
        self.commander = commander or CommanderAgent()
        self.is_monitoring = False
    
    async def trigger(self, alert: Dict[str, Any]) -> IncidentReport:
        """
        Trigger an investigation.
        
        Args:
            alert: Alert data to investigate
            
        Returns:
            IncidentReport with RCA
        """
        print("\n" + "="*60)
        print("[ALERT] ALERT TRIGGERED - Starting Investigation")
        print("="*60 + "\n")
        
        report = await self.commander.investigate(alert)
        
        print("\n" + "="*60)
        print("[DONE] INVESTIGATION COMPLETE")
        print("="*60 + "\n")
        
        return report
    
    def start_monitoring(self, check_interval: float = 1.0):
        """Start monitoring mode (for use with error generator)."""
        self.is_monitoring = True
        print(f"Commander Agent monitoring started (check interval: {check_interval}s)")
    
    def stop_monitoring(self):
        """Stop monitoring mode."""
        self.is_monitoring = False
        print("Commander Agent monitoring stopped")
