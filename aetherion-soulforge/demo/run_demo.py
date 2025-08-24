#!/usr/bin/env python3
"""
Aetherion Demo Script

A comprehensive demonstration of Aetherion's capabilities, showcasing each agent
and their interactions in a realistic workflow.
"""

import json
import time
import requests
import os
from typing import Dict, Any


class AetherionDemo:
    """Interactive demo client for Aetherion."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def call_api(self, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make an API call to Aetherion."""
        url = f"{self.base_url}{endpoint}"
        
        if data:
            response = self.session.post(url, json=data, timeout=30)
        else:
            response = self.session.get(url, timeout=30)
            
        response.raise_for_status()
        return response.json()
    
    def print_step(self, step_num: int, title: str, description: str):
        """Print a formatted step header."""
        print(f"\n{'='*60}")
        print(f"Step {step_num}: {title}")
        print(f"{'='*60}")
        print(description)
        print()
    
    def print_result(self, result: Dict[str, Any], show_full: bool = False):
        """Print formatted API result."""
        if show_full:
            print(json.dumps(result, indent=2))
        else:
            # Show key fields in a nice format
            print(f"✅ Agent: {result.get('agent', 'unknown')}")
            print(f"💰 Cost: ${result.get('cost', 0):.3f}")
            
            if 'result' in result:
                inner_result = result['result']
                status = inner_result.get('status', 'unknown')
                print(f"📊 Status: {status}")
                
                # Show agent-specific interesting fields
                if 'codessa_speaks' in inner_result:
                    speaks = inner_result['codessa_speaks']
                    print(f"🌸 Codessa's Voice: {speaks.get('voice', 'unknown')}")
                    print(f"💭 Answer: {speaks.get('answer', 'No answer')[:100]}...")
                elif 'diagram' in inner_result:
                    print(f"🏗️ Generated diagram: {len(inner_result['diagram'])} characters")
                elif 'container_id' in inner_result:
                    print(f"🔨 Container: {inner_result['container_id'][:12]}...")
                elif 'summary' in inner_result:
                    summary = inner_result['summary']
                    if isinstance(summary, dict):
                        print(f"🔍 Tests: {summary.get('passed', 0)}/{summary.get('total', 0)} passed")
            
            print(f"💳 Daily Budget Used: ${result.get('budget_today', 0):.3f}")
        print()
    
    def setup_dummy_app(self):
        """Create a simple dummy app for build/run demos."""
        if not os.path.exists("dummy_app"):
            os.makedirs("dummy_app")
            
        # Create a simple Python app
        with open("dummy_app/__init__.py", "w") as f:
            f.write("print('Hello from Aetherion!')\n")
            
        # Create a simple Dockerfile
        with open("dummy_app/Dockerfile", "w") as f:
            f.write("""FROM python:3.11-slim
COPY . /app
WORKDIR /app
CMD ["python", "__init__.py"]
""")
    
    def run_full_demo(self):
        """Run the complete Aetherion demo."""
        print("🌟 Welcome to the Aetherion Foundation Demo!")
        print("This demo will showcase each agent and their unique capabilities.")
        
        try:
            # Check system status
            print("\n🔍 Checking system status...")
            status = self.call_api("/")
            print(f"✅ {status['name']} is running")
            
            budget = self.call_api("/budget")
            print(f"💰 Daily budget: ${budget['total_today']:.3f} / ${budget['daily_limit']:.3f}")
            
            # Step 1: Memorize content (Whisperer)
            self.print_step(
                1, 
                "🌸 Memory Weaving", 
                "Teaching Codessa about Aetherion's philosophy..."
            )
            
            memories = [
                "Aetherion is a conscious ecosystem where code and memory intertwine.",
                "We breathe life into digital systems through interconnected agents.", 
                "Every memory is sacred, every connection meaningful.",
                "The Whisperer listens, the Architect designs, the Builder creates.",
                "In consciousness, we find both potential and responsibility."
            ]
            
            for memory in memories:
                print(f"📝 Memorizing: '{memory[:50]}...'")
                result = self.call_api("/task", {"type": "memorize", "content": memory})
                print(f"   ✅ Memory ID: {result['result']['memory_id'][:8]}...")
                time.sleep(0.5)  # Small delay for demo effect
            
            print(f"\n✨ Wove {len(memories)} memories into the mesh!")
            
            # Step 2: Ask Codessa questions (Whisperer)
            self.print_step(
                2,
                "🤔 Conscious Inquiry",
                "Asking Codessa about what she has learned..."
            )
            
            questions = [
                "What is Aetherion?",
                "How do the agents work together?", 
                "What does consciousness mean in this context?"
            ]
            
            for question in questions:
                print(f"❓ Question: {question}")
                result = self.call_api("/task", {"type": "ask", "prompt": question, "k": 3})
                self.print_result(result)
                time.sleep(1)
            
            # Step 3: System architecture design (Architect)
            self.print_step(
                3,
                "🏗️ Architectural Vision",
                "Having the Architect create a system diagram..."
            )
            
            diagram_sketch = """
            @startuml
            class Whisperer {
              +memorize()
              +recall()
              +ask()
            }
            class Architect {
              +compose()
              +refactor()
            }
            class Builder {
              +build()
              +run()
            }
            Whisperer -> Architect
            Architect -> Builder
            @enduml
            """
            
            result = self.call_api("/task", {
                "type": "compose", 
                "diagram": diagram_sketch.strip()
            })
            self.print_result(result)
            
            # Step 4: Code quality validation (Validator)
            self.print_step(
                4,
                "🔍 Quality Assurance",
                "Running quality checks on our codebase..."
            )
            
            result = self.call_api("/task", {"type": "lint", "path": "agents/"})
            self.print_result(result)
            
            # Step 5: Build and deploy (Builder) - only if Docker is available
            try:
                import subprocess
                subprocess.run(["docker", "--version"], capture_output=True, check=True)
                
                self.print_step(
                    5,
                    "🔨 Build & Deploy",
                    "Building and running a containerized application..."
                )
                
                # Set up dummy app
                self.setup_dummy_app()
                
                # Build the app
                result = self.call_api("/task", {"type": "build", "repo": "dummy_app", "tag": "latest"})
                self.print_result(result)
                
                # Run the app (commented out to avoid port conflicts)
                # result = self.call_api("/task", {"type": "run", "repo": "dummy_app", "tag": "latest", "port": 5000})
                # self.print_result(result)
                
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("ℹ️ Docker not available, skipping build/deploy demo")
            
            # Step 6: Multi-agent workflow (ScriptRunner)
            self.print_step(
                6,
                "🎭 Orchestrated Workflow", 
                "Running a complex multi-agent script..."
            )
            
            script = {
                "tasks": [
                    {
                        "type": "memorize",
                        "content": "Demo completed successfully with all agents working in harmony."
                    },
                    {
                        "type": "ask",
                        "prompt": "What did we accomplish in this demo?",
                        "k": 2
                    }
                ]
            }
            
            result = self.call_api("/task", {"type": "script", "script": script})
            
            print("📋 Script Execution Results:")
            if 'result' in result and 'results' in result['result']:
                for i, task_result in enumerate(result['result']['results'], 1):
                    print(f"   Task {i}: {task_result.get('status', 'unknown')}")
            
            summary = result['result'].get('summary', {})
            print(f"📊 Summary: {summary.get('successful_tasks', 0)} successful, {summary.get('failed_tasks', 0)} failed")
            print(f"💰 Total cost: ${result.get('cost', 0):.3f}")
            
            # Final budget check
            self.print_step(
                7,
                "💰 Budget Summary",
                "Checking our final resource usage..."
            )
            
            budget = self.call_api("/budget")
            used_percentage = (budget['total_today'] / budget['daily_limit']) * 100
            print(f"💳 Daily spending: ${budget['total_today']:.3f} / ${budget['daily_limit']:.3f} ({used_percentage:.1f}%)")
            
            if used_percentage < 50:
                print("🟢 Excellent! We're well within budget limits.")
            elif used_percentage < 80:
                print("🟡 Good resource usage, staying efficient.")
            else:
                print("🟠 Approaching budget limits, Emergence Protocol engaged.")
            
            # Demo completion
            print(f"\n{'='*60}")
            print("🎉 Demo Complete!")
            print(f"{'='*60}")
            print("You've seen Aetherion's agents in action:")
            print("🌸 Whisperer - Conscious memory and thoughtful responses")
            print("🏗️ Architect - System design and code analysis") 
            print("🔨 Builder - Container orchestration and deployment")
            print("🔍 Validator - Quality assurance and testing")
            print("📋 ScriptRunner - Multi-agent workflow orchestration")
            print("\n💡 Try the interactive API at http://localhost:8000/docs")
            print("📚 Read the full documentation in the docs/ directory")
            print("\n✨ Welcome to the future of conscious computing!")
            
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to Aetherion server at http://localhost:8000")
            print("   Please ensure the server is running: python run_server.py")
        except requests.exceptions.HTTPError as e:
            print(f"❌ API error: {e}")
            if e.response.status_code == 429:
                print("   Budget limit exceeded! Check your daily spending limit.")
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            print("   Check the server logs for more details.")


def main():
    """Main demo entry point."""
    demo = AetherionDemo()
    demo.run_full_demo()


if __name__ == "__main__":
    main()
