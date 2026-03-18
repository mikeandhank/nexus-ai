"""
Plugin SDK Module
================
Marketplace and plugin system for extending NexusOS
"""
import os
import json
import importlib
import inspect
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PluginManifest:
    """Plugin manifest definition"""
    id: str
    name: str
    version: str
    description: str
    author: str
    permissions: List[str]
    dependencies: List[str]


class Plugin:
    """Base plugin class"""
    
    manifest: PluginManifest
    hooks: Dict[str, Callable] = {}
    
    def __init__(self):
        self.enabled = False
        self.config = {}
    
    def on_load(self):
        """Called when plugin is loaded"""
        pass
    
    def on_unload(self):
        """Called when plugin is unloaded"""
        pass
    
    def get_routes(self) -> List[Dict]:
        """Return Flask routes"""
        return []
    
    def get_tools(self) -> List[Dict]:
        """Return agent tools"""
        return []


class PluginRegistry:
    """
    Registry for NexusOS plugins
    """
    
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
        self.hooks: Dict[str, List[Callable]] = {}
    
    def register(self, plugin: Plugin):
        """Register a plugin"""
        self.plugins[plugin.manifest.id] = plugin
        plugin.on_load()
    
    def unregister(self, plugin_id: str):
        """Unregister a plugin"""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].on_unload()
            del self.plugins[plugin_id]
    
    def get_plugin(self, plugin_id: str) -> Plugin:
        """Get plugin by ID"""
        return self.plugins.get(plugin_id)
    
    def list_plugins(self) -> List[Dict]:
        """List all plugins"""
        return [
            {
                "id": p.manifest.id,
                "name": p.manifest.name,
                "version": p.manifest.version,
                "enabled": p.enabled
            }
            for p in self.plugins.values()
        ]
    
    def register_hook(self, hook_name: str, callback: Callable):
        """Register a hook callback"""
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []
        self.hooks[hook_name].append(callback)
    
    def trigger_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """Trigger all callbacks for a hook"""
        results = []
        if hook_name in self.hooks:
            for callback in self.hooks[hook_name]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
        return results


class PluginLoader:
    """
    Load plugins from directory or package
    """
    
    def __init__(self, plugins_dir: str = None):
        self.plugins_dir = plugins_dir or os.environ.get(
            'PLUGINS_DIR', 
            '/app/plugins'
        )
        self.registry = PluginRegistry()
    
    def discover_plugins(self) -> List[str]:
        """Discover available plugins"""
        plugins = []
        
        if not os.path.exists(self.plugins_dir):
            return plugins
        
        for item in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, item)
            
            if os.path.isdir(plugin_path) and os.path.exists(
                os.path.join(plugin_path, 'plugin.py')
            ):
                plugins.append(item)
        
        return plugins
    
    def load_plugin(self, plugin_name: str) -> Plugin:
        """Load a specific plugin"""
        try:
            # Dynamic import
            module = importlib.import_module(f"plugins.{plugin_name}.plugin")
            
            # Find Plugin class
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, Plugin) and 
                    obj != Plugin):
                    
                    plugin = obj()
                    self.registry.register(plugin)
                    return plugin
            
            raise ValueError(f"No Plugin class found in {plugin_name}")
            
        except Exception as e:
            raise ValueError(f"Failed to load plugin {plugin_name}: {e}")
    
    def load_all(self):
        """Load all discovered plugins"""
        for plugin_name in self.discover_plugins():
            try:
                self.load_plugin(plugin_name)
            except Exception as e:
                print(f"Failed to load {plugin_name}: {e}")


# Built-in hooks
class NexusOSHooks:
    """Core NexusOS hooks for plugins"""
    
    # Chat hooks
    PRE_CHAT = "pre_chat"
    POST_CHAT = "post_chat"
    
    # Agent hooks
    PRE_AGENT_RUN = "pre_agent_run"
    POST_AGENT_RUN = "post_agent_run"
    
    # Auth hooks
    PRE_LOGIN = "pre_login"
    POST_LOGIN = "post_login"
    
    # Tool hooks
    PRE_TOOL_EXEC = "pre_tool_exec"
    POST_TOOL_EXEC = "post_tool_exec"


# Example plugin template
EXAMPLE_PLUGIN = '''
"""Example NexusOS Plugin"""
from nexusos_v2.plugin_sdk import Plugin, PluginManifest

class MyPlugin(Plugin):
    manifest = PluginManifest(
        id="my-plugin",
        name="My Plugin",
        version="1.0.0",
        description="A sample plugin",
        author="Your Name",
        permissions=["read", "write"],
        dependencies=[]
    )
    
    def on_load(self):
        print("My plugin loaded!")
    
    def get_tools(self):
        return [
            {
                "name": "my_tool",
                "description": "A custom tool",
                "function": self.my_function
            }
        ]
    
    def my_function(self, arg):
        return f"Result: {arg}"
'''

# Singleton
_plugin_registry = None

def get_plugin_registry() -> PluginRegistry:
    global _plugin_registry
    if _plugin_registry is None:
        _plugin_registry = PluginRegistry()
    return _plugin_registry