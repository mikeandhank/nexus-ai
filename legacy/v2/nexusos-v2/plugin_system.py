"""
NexusOS Plugin System
Allow community tool extensions.
"""

import os
import importlib.util
import inspect
from typing import Dict, List, Callable

PLUGIN_DIR = os.environ.get('NEXUSOS_PLUGINS', '/opt/nexusos-data/plugins')

class PluginManager:
    """Manage NexusOS plugins"""
    
    def __init__(self):
        self.plugins: Dict[str, Dict] = {}
        self.tools: Dict[str, Callable] = {}
        
    def load_plugins(self):
        """Load all plugins from plugin directory"""
        if not os.path.exists(PLUGIN_DIR):
            os.makedirs(PLUGIN_DIR, exist_ok=True)
            self._create_sample_plugin()
            return
            
        for filename in os.listdir(PLUGIN_DIR):
            if filename.endswith('.py') and not filename.startswith('_'):
                self._load_plugin(filename)
    
    def _create_sample_plugin():
        """Create a sample plugin for reference"""
        sample = '''"""
Sample NexusOS Plugin
Copy this to create your own tools.
"""
from typing import Dict, Any

def setup(plugin_api):
    """Register your plugin tools"""
    plugin_api.register_tool(
        name="echo",
        description="Echo back the input",
        func=echo_tool
    )
    plugin_api.register_tool(
        name="calculate", 
        description="Simple calculator",
        func=calc_tool
    )

def echo_tool(text: str) -> str:
    """Echo tool implementation"""
    return f"Echo: {text}"

def calc_tool(expression: str) -> str:
    """Calculate math expression"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"
'''
        with open(f'{PLUGIN_DIR}/sample.py', 'w') as f:
            f.write(sample)
    
    def _load_plugin(self, filename: str):
        """Load a single plugin"""
        path = os.path.join(PLUGIN_DIR, filename)
        name = filename[:-3]
        
        try:
            spec = importlib.util.spec_from_file_location(name, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for setup function
            if hasattr(module, 'setup'):
                plugin_api = PluginAPI(self)
                module.setup(plugin_api)
                self.plugins[name] = {
                    'path': path,
                    'tools': list(plugin_api._tools.keys())
                }
                print(f"[NexusOS] Loaded plugin: {name} ({len(plugin_api._tools)} tools)")
        except Exception as e:
            print(f"[NexusOS] Failed to load {filename}: {e}")
    
    def get_tool(self, name: str) -> Callable:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict]:
        """List all available tools"""
        return [
            {'name': name, 'plugin': plugin}
            for plugin, tools in self.plugins.items()
            for name in tools['tools']
        ]


class PluginAPI:
    """API available to plugins"""
    
    def __init__(self, manager: PluginManager):
        self._manager = manager
        self._tools = {}
    
    def register_tool(self, name: str, description: str, func: Callable):
        """Register a tool"""
        self._tools[name] = {
            'description': description,
            'func': func,
            'signature': inspect.signature(func)
        }
        self._manager.tools[name] = func
    
    def get_config(self, key: str, default=None):
        """Get config value"""
        return os.environ.get(f'NEXUSOS_{key.upper()}', default)


# Global plugin manager
_plugin_manager = None

def get_plugin_manager() -> PluginManager:
    """Get global plugin manager"""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
        _plugin_manager.load_plugins()
    return _plugin_manager


def setup_plugin_routes(app):
    """Add plugin routes to Flask app"""
    pm = get_plugin_manager()
    
    @app.route('/api/plugins', methods=['GET'])
    def list_plugins():
        """List loaded plugins"""
        return jsonify({'plugins': list(pm.plugins.keys())})
    
    @app.route('/api/plugins/tools', methods=['GET'])
    def list_plugin_tools():
        """List all plugin tools"""
        return jsonify({'tools': pm.list_tools()})
    
    @app.route('/api/plugins/<name>/reload', methods=['POST'])
    def reload_plugin(name):
        """Reload a specific plugin"""
        if name in pm.plugins:
            del pm.plugins[name]
            for tool in pm.plugins.get(name, {}).get('tools', []):
                pm.tools.pop(tool, None)
        
        path = os.path.join(PLUGIN_DIR, f'{name}.py')
        if os.path.exists(path):
            pm._load_plugin(f'{name}.py')
            return jsonify({'status': 'success'})
        
        return jsonify({'error': 'Plugin not found'}), 404


# Import jsonify for the routes
from flask import jsonify
