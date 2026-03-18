"""
Tool Execution Tasks - Background tool processing
"""
from tasks.celery_app import app

@app.task(bind=True)
def run_tool_async(self, tool_name, params, user_id):
    """Run tool in background"""
    from tool_engine import get_tool_engine
    
    engine = get_tool_engine()
    result = engine.execute(tool_name, params, user_id)
    
    return {
        'tool': tool_name,
        'result': result,
        'status': 'completed'
    }

@app.task
def batch_run_tools(tool_calls):
    """Run multiple tools in sequence"""
    from tool_engine import get_tool_engine
    
    engine = get_tool_engine()
    results = []
    
    for call in tool_calls:
        result = engine.execute(call['tool'], call['params'], call.get('user_id'))
        results.append({'tool': call['tool'], 'result': result})
    
    return results
