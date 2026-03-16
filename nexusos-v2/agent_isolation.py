"""
Agent Container Isolation Module
Provides sandboxed execution for AI agents with resource limits
"""
import docker
import uuid
import time
import subprocess
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class AgentResources:
    """Resource limits for an agent"""
    max_memory_mb: int = 512
    max_cpu_percent: int = 50
    max_network_mbps: int = 10
    max_files: int = 100
    timeout_seconds: int = 300


class AgentSandbox:
    """Manages isolated container execution for agents"""
    
    def __init__(self, base_image: str = "python:3.11-slim"):
        self.client = docker.from_env()
        self.base_image = base_image
        self._ensure_base_image()
    
    def _ensure_base_image(self):
        """Pull base image if needed"""
        try:
            self.client.images.get(self.base_image)
        except:
            print(f"Pulling {self.base_image}...")
            self.client.images.pull(self.base_image)
    
    def create_agent_container(
        self, 
        agent_id: str,
        resources: AgentResources = None,
        environment: Dict[str, str] = None
    ) -> str:
        """
        Create an isolated container for an agent
        
        Returns container_id
        """
        if resources is None:
            resources = AgentResources()
        
        container_name = f"nexus-agent-{agent_id}"
        
        # Remove existing if any
        try:
            existing = self.client.containers.get(container_name)
            existing.remove(force=True)
        except:
            pass
        
        # Create container with resource limits
        container = self.client.containers.run(
            self.base_image,
            name=container_name,
            detach=True,
            mem_limit=f"{resources.max_memory_mb}m",
            cpu_period=100000,
            cpu_quota=int(resources.max_cpu_percent * 1000),
            network_mode="nexusos-agent-net",  # Isolated network
            mem_reservation=f"{resources.max_memory_mb // 2}m",
            environment=environment or {},
            command="sleep infinity",  # Placeholder - will exec commands
            labels={
                "nexusos.agent": agent_id,
                "nexusos.type": "agent-sandbox"
            }
        )
        
        return container.id
    
    def execute_in_agent(
        self,
        agent_id: str,
        command: List[str],
        timeout: int = 30
    ) -> Dict[str, any]:
        """
        Execute a command inside an agent's container
        
        Returns: {"success": bool, "output": str, "error": str, "exit_code": int}
        """
        container_name = f"nexus-agent-{agent_id}"
        
        try:
            container = self.client.containers.get(container_name)
            
            # Execute with timeout
            result = container.exec_run(
                command,
                stream=False,
                demux=False
            )
            
            return {
                "success": result.exit_code == 0,
                "output": result.output.decode('utf-8', errors='ignore'),
                "error": "",
                "exit_code": result.exit_code
            }
            
        except docker.errors.NotFound:
            return {
                "success": False,
                "output": "",
                "error": f"Agent container {agent_id} not found",
                "exit_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1
            }
    
    def stop_agent(self, agent_id: str) -> bool:
        """Stop and remove an agent's container"""
        container_name = f"nexus-agent-{agent_id}"
        
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=10)
            container.remove()
            return True
        except:
            return False
    
    def get_agent_stats(self, agent_id: str) -> Optional[Dict]:
        """Get resource usage for an agent"""
        container_name = f"nexus-agent-{agent_id}"
        
        try:
            container = self.client.containers.get(container_name)
            stats = container.stats(stream=False)
            
            return {
                "cpu_percent": self._calc_cpu_percent(stats),
                "memory_usage_mb": stats['memory_stats'].get('usage', 0) / 1024 / 1024,
                "memory_limit_mb": stats['memory_stats'].get('limit', 0) / 1024 / 1024,
                "network_rx": stats['networks'].get('eth0', {}).get('rx_bytes', 0) if stats.get('networks') else 0,
                "network_tx": stats['networks'].get('eth0', {}).get('tx_bytes', 0) if stats.get('networks') else 0,
            }
        except:
            return None
    
    def _calc_cpu_percent(self, stats: dict) -> float:
        """Calculate CPU percentage from stats"""
        try:
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            
            if system_delta > 0:
                num_cpus = len(stats['cpu_stats'].get('cpu_usage', {}).get('percpu_usage', [0]))
                return (cpu_delta / system_delta) * num_cpus * 100
        except:
            pass
        return 0.0
    
    def kill_agent(self, agent_id: str) -> bool:
        """Emergency kill - force stop an agent"""
        return self.stop_agent(agent_id)


# Global sandbox manager
_sandbox = None

def get_sandbox() -> AgentSandbox:
    """Get global sandbox instance"""
    global _sandbox
    if _sandbox is None:
        _sandbox = AgentSandbox()
    return _sandbox


def create_isolated_agent(agent_id: str, **env) -> str:
    """Convenience function to create an isolated agent"""
    sandbox = get_sandbox()
    return sandbox.create_agent_container(agent_id, environment=env)


def execute_in_agent(agent_id: str, command: List[str], timeout: int = 30) -> Dict:
    """Convenience function to execute in agent"""
    sandbox = get_sandbox()
    return sandbox.execute_in_agent(agent_id, command, timeout)


def kill_agent(agent_id: str) -> bool:
    """Convenience function to kill an agent"""
    sandbox = get_sandbox()
    return sandbox.kill_agent(agent_id)
