"""
Main entry point for Commander Agent demo.

Usage:
    python -m commander_agent.main
"""
import asyncio
import json
import sys
import io
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from commander_agent.commander import CommanderAgent
from commander_agent.llm.client import create_llm_client
from commander_agent.config import config


async def main():
    """
    Demo: Run Commander Agent with the hackathon scenario.
    
    Scenario:
    - Trigger: Checkout Service latency spikes to 2000ms
    - Investigation: Find DB Connection timeouts correlated with config deployment
    - Outcome: Recommend immediate rollback
    """
    
    print("\n" + "="*70)
    print("[COMMANDER] BAYER AI HACKATHON 2026 - AUTONOMOUS INCIDENT COMMANDER")
    print("="*70)
    print()
    
    # Create LLM client (will use mock if no API key)
    llm_client = create_llm_client(
        provider=config.llm.provider,
        api_key=config.llm.get_api_key(),
        model=config.llm.model
    )
    
    # Create Commander Agent with LLM
    commander = CommanderAgent(llm_client=llm_client, debug=True)
    
    # Demo alert matching hackathon scenario
    alert = {
        "service": "checkout-api",
        "issue": "latency spike to 2000ms",
        "severity": "high",
        "timestamp": "10:15",
        "metadata": {
            "error_rate": "15%",
            "affected_users": 1250
        }
    }
    
    print("[ALERT] INCOMING ALERT:")
    print(json.dumps(alert, indent=2))
    print()
    
    # Run investigation
    report = await commander.investigate(alert)
    
    # Print results
    print("\n" + "="*70)
    print("[REPORT] FINAL REPORT (JSON)")
    print("="*70)
    print(json.dumps(report.to_dict(), indent=2))
    
    print("\n" + "="*70)
    print("[REPORT] FINAL REPORT (MARKDOWN)")  
    print("="*70)
    print(report.to_markdown())
    
    # Print chain of thought
    print("\n" + "="*70)
    print("[THOUGHT] CHAIN OF THOUGHT")
    print("="*70)
    for thought in commander.get_chain_of_thought():
        print(thought)
    
    # Save report to file
    output_file = f"rca_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report.to_markdown())
    print(f"\n[SAVED] Report saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
