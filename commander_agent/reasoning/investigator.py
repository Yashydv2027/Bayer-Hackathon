"""
INVESTIGATE Phase - Orchestrate sub-agent execution.
"""
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.investigation import InvestigationState, InvestigationStep, AgentResult


class Investigator:
    """
    INVESTIGATE phase of the reasoning loop.
    
    Responsibilities:
    - Execute investigation plan by calling sub-agents
    - Collect and store results
    - Handle timeouts and retries
    """
    
    def __init__(self, agents: Dict[str, Any] = None):
        """
        Initialize with available agents.
        
        Args:
            agents: Dictionary mapping agent names to agent instances
        """
        self.agents = agents or {}
    
    def register_agent(self, name: str, agent: Any):
        """Register a sub-agent."""
        self.agents[name] = agent
    
    async def investigate(self, state: InvestigationState) -> InvestigationState:
        """
        Execute the investigation plan.
        
        Args:
            state: Current investigation state with plan
            
        Returns:
            Updated state with agent results
        """
        # Sort steps by priority
        sorted_steps = sorted(state.investigation_plan, key=lambda x: x.priority)
        
        # Group steps by priority for parallel execution
        priority_groups = self._group_by_priority(sorted_steps)
        
        for priority, steps in priority_groups.items():
            # Execute same-priority steps in parallel
            await self._execute_parallel(steps, state)
        
        return state
    
    def _group_by_priority(self, steps: List[InvestigationStep]) -> Dict[int, List[InvestigationStep]]:
        """Group steps by priority level."""
        groups = {}
        for step in steps:
            if step.priority not in groups:
                groups[step.priority] = []
            groups[step.priority].append(step)
        return dict(sorted(groups.items()))
    
    async def _execute_parallel(self, steps: List[InvestigationStep], state: InvestigationState):
        """Execute steps in parallel."""
        tasks = []
        for step in steps:
            task = asyncio.create_task(self._execute_step(step, state))
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_step(self, step: InvestigationStep, state: InvestigationState):
        """Execute a single investigation step."""
        step.status = "running"
        start_time = datetime.now()
        
        try:
            agent = self.agents.get(step.agent)
            if not agent:
                # Create mock result if agent not found
                result = AgentResult(
                    agent_name=step.agent,
                    success=False,
                    findings=[],
                    anomalies=[],
                    timeline_events=[],
                    confidence=0.0,
                    error=f"Agent '{step.agent}' not registered"
                )
            else:
                # Call the agent
                result = await agent.investigate(state)
            
            # Record execution time
            result.execution_time = (datetime.now() - start_time).total_seconds()
            
            # Store result
            state.add_agent_result(result)
            step.status = "completed"
            
        except Exception as e:
            step.status = "failed"
            result = AgentResult(
                agent_name=step.agent,
                success=False,
                findings=[],
                anomalies=[],
                timeline_events=[],
                confidence=0.0,
                error=str(e),
                execution_time=(datetime.now() - start_time).total_seconds()
            )
            state.add_agent_result(result)
