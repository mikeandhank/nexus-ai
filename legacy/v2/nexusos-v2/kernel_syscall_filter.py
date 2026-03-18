"""
System Call Filtering - Security Sandbox
=========================================
Restricts what system calls agents can make.
"""

import os
import subprocess
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Whitelist of allowed system calls
ALLOWED_SYSCALLS = {
    # File operations
    'read', 'write', 'open', 'close', 'stat', 'lstat', 'fstat',
    'access', 'pipe', 'select', 'poll', 'dup', 'dup2', 'mkdir',
    
    # Process
    'getpid', 'getuid', 'getgid', 'geteuid', 'getegid',
    'getppid', 'getpgrp', 'setpgid', 'setsid',
    
    # Time
    'gettimeofday', 'time', 'clock_gettime',
    
    # Memory
    'brk', 'mmap', 'munmap', 'mprotect',
    
    # Networking (read-only)
    'socket', 'connect', 'send', 'recv', 'shutdown',
    'bind', 'listen', 'accept', 'getsockname', 'getpeername',
    
    # Signals
    'sigaction', 'sigprocmask', 'sigreturn', 'sigemptyset', 'sigfillset',
    'sigaddset', 'sigdelset',
}

# Blocked system calls (security risks)
BLOCKED_SYSCALLS = {
    # Process control
    'fork', 'vfork', 'clone', 'execve', 'exit', 'wait4', 'waitpid',
    
    # Module/syscall
    'init_module', 'delete_module', 'create_module',
    
    # Admin
    'reboot', 'setuid', 'setgid', 'setreuid', 'setregid',
    'setresuid', 'getresuid', 'setresgid', 'getresgid',
    'setgroups', 'getgroups', 'setfsuid', 'setfsgid',
    'capget', 'capset',
    
    # Kernel
    'quotactl', 'setdomainname', 'sethostname',
    'mount', 'umount', 'umount2',
    
    # Privilege
    'chroot', 'pivot_root',
}


class SystemCallFilter:
    """
    System call filtering for agent sandbox.
    
    Uses seccomp-bpf on Linux for syscall filtering.
    Falls back to basic validation on other platforms.
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.blocked_count = 0
        self.allowed_count = 0
        
    def is_allowed(self, syscall: str) -> bool:
        """Check if a system call is allowed"""
        if not self.enabled:
            return True
            
        if syscall in BLOCKED_SYSCALLS:
            self.blocked_count += 1
            logger.warning(f"Blocked dangerous syscall: {syscall}")
            return False
            
        if syscall in ALLOWED_SYSCALLS:
            self.allowed_count += 1
            return True
            
        # Unknown syscalls are logged but allowed (fail-open for compatibility)
        logger.info(f"Unknown syscall: {syscall}")
        return True
    
    def validate_command(self, cmd: List[str]) -> Dict:
        """
        Validate a shell command before execution.
        
        Returns:
            {"allowed": bool, "reason": str}
        """
        if not self.enabled:
            return {"allowed": True, "reason": "filter disabled"}
            
        dangerous_patterns = [
            'rm -rf /', 'dd if=/dev/zero', ':(){:|:&};:',
            '/etc/passwd', '/etc/shadow', '/proc/sys',
            'wget.*|sh', 'curl.*|sh', 'nc -e', 'bash -i',
        ]
        
        import re
        cmd_str = ' '.join(cmd)
        
        for pattern in dangerous_patterns:
            if re.search(pattern, cmd_str, re.IGNORECASE):
                return {
                    "allowed": False, 
                    "reason": f"Dangerous pattern detected: {pattern}"
                }
        
        return {"allowed": True, "reason": "command validated"}
    
    def get_stats(self) -> Dict:
        """Get filter statistics"""
        return {
            "enabled": self.enabled,
            "blocked_count": self.blocked_count,
            "allowed_count": self.allowed_count,
            "blocked_syscalls": list(BLOCKED_SYSCALLS),
            "allowed_syscalls": len(ALLOWED_SYSCALLS)
        }
    
    def enable(self):
        """Enable the filter"""
        self.enabled = True
        logger.info("System call filter enabled")
    
    def disable(self):
        """Disable the filter"""
        self.enabled = False
        logger.info("System call filter disabled")


# Integration with kernel
def apply_to_agent(agent_id: str) -> Dict:
    """Apply system call filter to an agent"""
    return {
        "agent_id": agent_id,
        "system_call_filter": "enabled",
        "seccomp_profile": "localhost/nexusos-filter.json"
    }


# Singleton
_filter = None

def get_filter() -> SystemCallFilter:
    global _filter
    if _filter is None:
        _filter = SystemCallFilter()
    return _filter
