import requests
import json
from typing import Dict, Any, List
import os
from dotenv import load_dotenv

load_dotenv()

class MCPClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv('MCP_SERVER_URL', 'http://localhost:3002')
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available MCP tools"""
        try:
            response = requests.get(f"{self.base_url}/tools")
            response.raise_for_status()
            return response.json().get('tools', [])
        except requests.RequestException as e:
            raise Exception(f"Failed to get tools: {e}")
    
    def call_tool(self, tool_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Call an MCP tool with parameters"""
        try:
            url = f"{self.base_url}/tools/{tool_name}"
            response = requests.post(url, json=parameters or {})
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to call tool {tool_name}: {e}")
    
    def list_tasks(self) -> Dict[str, Any]:
        """List all tasks"""
        return self.call_tool('list_tasks')
    
    def create_task(self, title: str, description: str = "", priority: str = "medium") -> Dict[str, Any]:
        """Create a new task"""
        return self.call_tool('create_task', {
            'title': title,
            'description': description,
            'priority': priority
        })
    
    def update_task(self, task_id: str, **kwargs) -> Dict[str, Any]:
        """Update an existing task"""
        params = {'id': task_id}
        params.update(kwargs)
        return self.call_tool('update_task', params)
    
    def delete_task(self, task_id: str) -> Dict[str, Any]:
        """Delete a task"""
        return self.call_tool('delete_task', {'id': task_id})
    
    def get_task_stats(self) -> Dict[str, Any]:
        """Get task statistics"""
        return self.call_tool('get_task_stats')
    
    def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.status_code == 200
        except:
            return False