"""
Error Generator Script

Simulates normal logs, then randomly generates an error that triggers the Commander Agent.
This demonstrates the full incident response workflow.

Usage:
    python error_generator.py
"""
import asyncio
import random
import time
from datetime import datetime
from typing import Callable, Optional

from commander_agent.commander import CommanderAgent, CommanderTrigger


class ErrorGenerator:
    """
    Simulates a service generating logs.
    
    Generates normal logs for a while, then randomly generates an error
    that triggers the Commander Agent.
    """
    
    def __init__(
        self,
        service_name: str = "checkout-api",
        error_probability: float = 0.1,  # 10% chance after threshold
        normal_logs_before_error: int = 10,
        on_error_callback: Optional[Callable] = None
    ):
        """
        Initialize the error generator.
        
        Args:
            service_name: Name of the simulated service
            error_probability: Probability of error after threshold logs
            normal_logs_before_error: Minimum normal logs before errors can occur
            on_error_callback: Async callback when error is generated
        """
        self.service_name = service_name
        self.error_probability = error_probability
        self.normal_logs_before_error = normal_logs_before_error
        self.on_error_callback = on_error_callback
        
        self.log_count = 0
        self.error_triggered = False
        
        # Sample log messages
        self.normal_messages = [
            "Request processed successfully",
            "User authentication completed",
            "Cart updated for user",
            "Payment validation passed",
            "Inventory check completed",
            "Order submitted to queue",
            "Cache hit for product data",
            "Session refreshed",
            "API response sent in 45ms",
            "Database query completed",
        ]
        
        # Error scenarios matching hackathon demo
        self.error_scenarios = [
            {
                "service": "checkout-api",
                "issue": "latency spike to 2000ms",
                "severity": "high",
                "error_type": "LATENCY"
            },
            {
                "service": "checkout-api",
                "issue": "database connection timeout",
                "severity": "critical",
                "error_type": "TIMEOUT"
            },
            {
                "service": "checkout-api",
                "issue": "high error rate detected",
                "severity": "high",
                "error_type": "ERROR"
            }
        ]
    
    def generate_normal_log(self) -> str:
        """Generate a normal log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = random.choice(self.normal_messages)
        return f"[{timestamp}] INFO  [{self.service_name}] {message}"
    
    def generate_error_log(self) -> dict:
        """Generate an error log and return the alert data."""
        timestamp = datetime.now().strftime("%H:%M")
        scenario = random.choice(self.error_scenarios)
        
        return {
            "service": scenario["service"],
            "issue": scenario["issue"],
            "severity": scenario["severity"],
            "timestamp": timestamp,
            "metadata": {
                "error_type": scenario["error_type"],
                "log_count_before_error": self.log_count
            }
        }
    
    def should_generate_error(self) -> bool:
        """Determine if an error should be generated."""
        if self.error_triggered:
            return False
        
        if self.log_count < self.normal_logs_before_error:
            return False
        
        return random.random() < self.error_probability
    
    async def run(self, max_logs: int = 20, delay: float = 0.5):
        """
        Run the error generator.
        
        Args:
            max_logs: Maximum number of logs to generate
            delay: Delay between logs in seconds
        """
        print("\n" + "="*60)
        print(f"🔄 Starting Error Generator for {self.service_name}")
        print(f"   - Normal logs before potential error: {self.normal_logs_before_error}")
        print(f"   - Error probability after threshold: {self.error_probability*100:.0f}%")
        print("="*60 + "\n")
        
        for i in range(max_logs):
            self.log_count += 1
            
            # Check if we should generate an error
            if self.should_generate_error():
                self.error_triggered = True
                
                print(f"\n{'!'*60}")
                print(f"🚨 ERROR DETECTED ON LOG #{self.log_count}")
                print(f"{'!'*60}\n")
                
                # Generate error alert
                alert = self.generate_error_log()
                
                print(f"[{alert['timestamp']}] ERROR [{self.service_name}] {alert['issue']}")
                print(f"\nAlert generated: {alert}\n")
                
                # Trigger callback (Commander Agent)
                if self.on_error_callback:
                    await self.on_error_callback(alert)
                
                break
            else:
                # Generate normal log
                log = self.generate_normal_log()
                print(f"  #{self.log_count:02d} {log}")
            
            await asyncio.sleep(delay)
        
        if not self.error_triggered:
            print(f"\n✅ Completed {max_logs} logs without errors")


async def main():
    """Main entry point - run error generator with Commander Agent."""
    
    # Initialize Commander Agent
    commander = CommanderAgent(debug=True)
    trigger = CommanderTrigger(commander)
    
    # Define callback for when error is detected
    async def on_error(alert: dict):
        """Handler when error is generated - triggers Commander Agent."""
        report = await trigger.trigger(alert)
        
        # Print the report
        print("\n" + "="*60)
        print("📋 INCIDENT REPORT")
        print("="*60)
        print(report.to_markdown())
        
        # Also save to file
        output_file = f"rca_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(output_file, 'w') as f:
            f.write(report.to_markdown())
        print(f"\n📁 Report saved to: {output_file}")
    
    # Create error generator
    generator = ErrorGenerator(
        service_name="checkout-api",
        error_probability=0.3,  # 30% chance after 10 normal logs
        normal_logs_before_error=10,
        on_error_callback=on_error
    )
    
    # Run the simulation
    await generator.run(max_logs=25, delay=0.3)


if __name__ == "__main__":
    asyncio.run(main())
