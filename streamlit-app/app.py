import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
import time
import requests
import random
from functools import wraps
from typing import Dict, List, Optional
from mcp_client import MCPClient  # Keep your existing client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Task Management Assistant",
    page_icon="📋",
    layout="wide"
)

# Add retry decorator for Gemini requests
def with_retry(max_retries=3, backoff_factor=1.5):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Check if it's a rate limit error
                    if '429' in error_str or 'quota exceeded' in error_str or 'rate_limit' in error_str:
                        if attempt < max_retries - 1:
                            # Calculate backoff time with jitter
                            backoff_time = (backoff_factor ** attempt) + random.uniform(0, 1)
                            st.warning(f"⏳ Rate limit hit. Retrying in {backoff_time:.1f} seconds... (Attempt {attempt + 1}/{max_retries})")
                            time.sleep(backoff_time)
                            continue
                        else:
                            st.error("🚨 Rate limit exceeded. Please wait a few minutes before trying again.")
                            return {"action": "rate_limited", "response": "Rate limit exceeded. Try again later."}
                    else:
                        # For non-rate-limit errors, re-raise immediately
                        raise e
            return None
        return wrapper
    return decorator

@with_retry(max_retries=3)
def call_gemini_with_retry(model, prompt):
    """Call Gemini with automatic retry logic"""
    response = model.generate_content(prompt)
    return response.text.strip()

def process_fallback_request(user_input: str, mcp_client):
    """Simple pattern matching for when Gemini is unavailable"""
    user_input_lower = user_input.lower()
    
    # Simple pattern matching
    if any(word in user_input_lower for word in ['list', 'show', 'display', 'all']) and 'task' in user_input_lower:
        try:
            result = mcp_client.call_tool('list_tasks', {})
            return {
                "action": "tool_result",
                "response": f"📋 Here are your tasks (fallback mode):",
                "tool_result": result
            }
        except Exception as e:
            return {"action": "error", "response": f"Error listing tasks: {e}"}
    
    elif any(word in user_input_lower for word in ['create', 'add', 'new']) and 'task' in user_input_lower:
        # Extract title (simple approach)
        title = user_input.replace('create task', '').replace('add task', '').replace('new task', '').strip()
        if not title:
            return {
                "action": "chat",
                "response": "Please specify a task title. Example: 'create task: Deploy new feature'"
            }
        
        try:
            result = mcp_client.call_tool('create_task', {'title': title, 'priority': 'medium'})
            return {
                "action": "tool_result", 
                "response": f"✅ Task created: {title} (fallback mode)",
                "tool_result": result
            }
        except Exception as e:
            return {"action": "error", "response": f"Error creating task: {e}"}
    
    elif any(word in user_input_lower for word in ['stats', 'statistics', 'summary']):
        try:
            result = mcp_client.call_tool('get_task_stats', {})
            return {
                "action": "tool_result",
                "response": "📊 Task statistics (fallback mode):",
                "tool_result": result
            }
        except Exception as e:
            return {"action": "error", "response": f"Error getting stats: {e}"}
    
    else:
        return {
            "action": "chat",
            "response": """🤖 I'm in fallback mode due to API limits. You can:
            
• Say "list tasks" to see all tasks
• Say "create task: [your task title]" to add a task  
• Say "stats" to see statistics
• Use the sidebar form for full task creation

Or wait a few minutes for AI features to resume."""
        }

class EnhancedMCPClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.getenv('MCP_SERVER_URL', 'http://localhost:3002')
        self._tools_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 300  # 5 minutes cache

    def health_check(self) -> bool:
        """Check if MCP server is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def call_tool(self, tool_name: str, parameters: Dict[str, any] = None) -> Dict[str, any]:
        """Call an MCP tool via HTTP"""
        try:
            url = f"{self.base_url}/tools/{tool_name}"
            response = requests.post(url, json=parameters or {}, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise Exception(f"Failed to call tool {tool_name}: {e}")

    def list_tasks(self) -> Dict[str, any]:
        """List all tasks"""
        return self.call_tool('list_tasks')

    def get_task_stats(self) -> Dict[str, any]:
        """Get task statistics"""
        return self.call_tool('get_task_stats')

    def create_task(self, title: str, description: str = "", priority: str = "medium") -> Dict[str, any]:
        """Create a new task"""
        return self.call_tool('create_task', {
            'title': title,
            'description': description,
            'priority': priority
        })

    def get_dynamic_tools(self, force_refresh: bool = False) -> Optional[Dict]:
        """Fetch tools dynamically from MCP server with caching"""
        now = time.time()
        
        # Check cache first (unless force refresh)
        if not force_refresh and self._tools_cache and (now - self._cache_timestamp < self._cache_ttl):
            return self._tools_cache
        
        try:
            with st.spinner("🔍 Discovering available tools..."):
                response = requests.get(f"{self.base_url}/tools", timeout=10)
                response.raise_for_status()
                
                tools_data = response.json()
                
                # Update cache
                self._tools_cache = tools_data
                self._cache_timestamp = now
                
                return tools_data
                
        except requests.exceptions.ConnectionError:
            st.error("❌ Cannot connect to MCP server for tool discovery")
            return None
        except requests.exceptions.Timeout:
            st.error("❌ Tool discovery timed out")
            return None
        except requests.RequestException as e:
            st.error(f"❌ Error fetching tools: {e}")
            return None

    def convert_mcp_tools_to_schema(self, tools_data: Dict) -> str:
        """Convert MCP tools format to Gemini-friendly schema"""
        if not tools_data or 'tools' not in tools_data:
            return "No tools available"
        
        schema = "Available Task Management Tools (Dynamically Discovered):\n\n"
        
        for tool in tools_data['tools']:
            name = tool.get('name', 'unknown')
            description = tool.get('description', 'No description')
            parameters = tool.get('parameters', {})
            
            schema += f"🔧 **{name}**\n"
            schema += f"   - Purpose: {description}\n"
            
            # Process parameters
            if parameters:
                required_params = []
                optional_params = []
                
                for param_name, param_info in parameters.items():
                    if isinstance(param_info, dict):
                        param_type = param_info.get('type', 'string')
                        param_desc = param_info.get('description', '')
                        is_required = param_info.get('required', False)
                        enum_values = param_info.get('enum', [])
                        
                        param_str = f"{param_name} ({param_type})"
                        if enum_values:
                            param_str += f" - options: {', '.join(enum_values)}"
                        if param_desc:
                            param_str += f" - {param_desc}"
                        
                        if is_required:
                            required_params.append(param_str)
                        else:
                            optional_params.append(param_str)
                
                if required_params:
                    schema += f"   - Required: {', '.join(required_params)}\n"
                if optional_params:
                    schema += f"   - Optional: {', '.join(optional_params)}\n"
            else:
                schema += "   - Parameters: none\n"
            
            # Add example usage
            schema += f"   - Example: \"{self._generate_example_usage(name, parameters)}\"\n"
            schema += "\n"
        
        return schema

    def _generate_example_usage(self, tool_name: str, parameters: Dict) -> str:
        """Generate example usage text for each tool"""
        examples = {
            'list_tasks': 'Show me all my tasks',
            'create_task': 'Create a high priority task to deploy the authentication feature',
            'update_task': 'Mark the deployment task as completed',
            'delete_task': 'Delete the completed testing task',
            'get_task_stats': 'Show me task statistics',
            'search_tasks': 'Find all tasks related to authentication',
            'get_tasks_by_priority': 'Show me all high priority tasks',
            'get_tasks_by_status': 'Show me all pending tasks',
            'get_recent_tasks': 'Show me recent tasks from last 3 days',
            'bulk_update_tasks': 'Mark these 3 tasks as completed',
            'archive_completed_tasks': 'Archive all my completed tasks',
            'get_task_summary': 'Give me a comprehensive task summary'
        }
        
        return examples.get(tool_name, f'Use the {tool_name} tool')

    def get_tools_info(self) -> Dict:
        """Get detailed information about tools and cache status"""
        tools_data = self.get_dynamic_tools()
        
        if not tools_data:
            return {
                'available': False,
                'count': 0,
                'tools': [],
                'cache_status': 'failed',
                'last_updated': None
            }
        
        cache_age = time.time() - self._cache_timestamp
        cache_status = 'fresh' if cache_age < 60 else 'cached' if cache_age < 300 else 'stale'
        
        return {
            'available': True,
            'count': len(tools_data.get('tools', [])),
            'tools': [tool.get('name') for tool in tools_data.get('tools', [])],
            'cache_status': cache_status,
            'cache_age_seconds': int(cache_age),
            'last_updated': time.strftime('%H:%M:%S', time.localtime(self._cache_timestamp))
        }

def show_tool_discovery_settings(mcp_client: EnhancedMCPClient):
    """Tool discovery settings panel"""
    
    st.sidebar.header("🔧 Tool Discovery Settings")
    
    # Main toggle
    use_dynamic = st.sidebar.checkbox(
        "🔍 Dynamic Tool Discovery",
        value=st.session_state.get('use_dynamic_tools', False),
        help="Fetch tools from MCP server vs. using hardcoded schema"
    )
    st.session_state['use_dynamic_tools'] = use_dynamic
    
    # Show current mode
    mode = "Dynamic" if use_dynamic else "Static"
    mode_color = "🟢" if use_dynamic else "🔵"
    st.sidebar.write(f"**Current Mode:** {mode_color} {mode}")
    
    # Dynamic mode controls
    if use_dynamic:
        st.sidebar.subheader("🔍 Dynamic Discovery")
        
        # Get tools info
        tools_info = mcp_client.get_tools_info()
        
        if tools_info['available']:
            st.sidebar.success(f"✅ {tools_info['count']} tools discovered")
            
            # Cache status
            cache_status = tools_info['cache_status']
            cache_icons = {'fresh': '🟢', 'cached': '🟡', 'stale': '🔴', 'failed': '❌'}
            cache_icon = cache_icons.get(cache_status, '❓')
            
            st.sidebar.write(f"**Cache:** {cache_icon} {cache_status.title()}")
            if tools_info['last_updated']:
                st.sidebar.write(f"**Last Updated:** {tools_info['last_updated']}")
                st.sidebar.write(f"**Age:** {tools_info['cache_age_seconds']}s")
            
            # Refresh button
            col1, col2 = st.sidebar.columns(2)
            with col1:
                if st.button("🔄 Refresh Tools"):
                    tools_info = mcp_client.get_dynamic_tools(force_refresh=True)
                    if tools_info:
                        st.sidebar.success("✅ Tools refreshed!")
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Refresh failed")
            
            with col2:
                if st.button("📋 Show Tools"):
                    st.session_state['show_tools_details'] = True
            
            # Show discovered tools
            if st.session_state.get('show_tools_details', False):
                st.sidebar.subheader("📋 Discovered Tools")
                for tool_name in tools_info['tools']:
                    st.sidebar.code(tool_name)
                
                if st.sidebar.button("❌ Hide Tools"):
                    st.session_state['show_tools_details'] = False
                    st.rerun()
        
        else:
            st.sidebar.error("❌ Tool discovery failed")
            st.sidebar.write("**Fallback:** Using static schema")
            
            if st.sidebar.button("🔄 Retry Discovery"):
                tools_info = mcp_client.get_dynamic_tools(force_refresh=True)
                st.rerun()
    
    else:
        st.sidebar.subheader("📝 Static Schema")
        st.sidebar.info("Using hardcoded tool definitions")
        st.sidebar.write("**Benefits:** Fast, reliable, optimized prompts")
        
        if st.sidebar.button("📋 Show Static Tools"):
            st.session_state['show_static_tools'] = True
        
        if st.session_state.get('show_static_tools', False):
            static_tools = [
                'list_tasks', 'create_task', 'update_task', 'delete_task',
                'get_task_stats', 'search_tasks', 'get_tasks_by_priority',
                'get_tasks_by_status', 'get_recent_tasks', 'bulk_update_tasks',
                'archive_completed_tasks', 'get_task_summary'
            ]
            
            for tool in static_tools:
                st.sidebar.code(tool)
            
            if st.sidebar.button("❌ Hide Static Tools"):
                st.session_state['show_static_tools'] = False
                st.rerun()
    
    # Debug options
    st.sidebar.subheader("🐛 Debug Options")
    
    show_debug = st.sidebar.checkbox(
        "Show AI Analysis",
        value=st.session_state.get('show_debug', False),
        help="Show raw Gemini responses"
    )
    st.session_state['show_debug'] = show_debug

# Enhanced schema functions
def get_static_tool_schema():
    """Original hardcoded schema - fast and reliable"""
    return """
Available Task Management Tools (Static Schema):

🔧 **list_tasks**
   - Purpose: Get all tasks from database
   - Parameters: none
   - Example: "Show me all tasks"

🔧 **create_task**  
   - Purpose: Create a new task
   - Required: title (string)
   - Optional: description (string), priority ("low"|"medium"|"high")
   - Example: "Create a high priority task called 'Deploy app'"

🔧 **update_task**
   - Purpose: Update existing task
   - Required: id (string)
   - Optional: title, description, completed (boolean), priority
   - Example: "Mark task xyz as completed"

🔧 **delete_task**
   - Purpose: Delete a task
   - Required: id (string)
   - Example: "Delete task with ID xyz"

🔧 **get_task_stats**
   - Purpose: Get task statistics
   - Parameters: none
   - Example: "Show me task statistics"

🔧 **search_tasks**
   - Purpose: Search tasks by keywords
   - Required: query (string)
   - Optional: limit (number)
   - Example: "Find all tasks containing 'authentication'"

🔧 **get_tasks_by_priority**
   - Purpose: Get tasks filtered by priority level
   - Required: priority ("low"|"medium"|"high")
   - Example: "Show me all high priority tasks"

🔧 **get_tasks_by_status**
   - Purpose: Get tasks filtered by completion status  
   - Required: completed (boolean)
   - Example: "List all pending tasks"

🔧 **get_recent_tasks**
   - Purpose: Get recently created or updated tasks
   - Optional: limit (number), days (number)
   - Example: "Show tasks from the last 3 days"

🔧 **bulk_update_tasks**
   - Purpose: Update multiple tasks at once
   - Required: task_ids (array), updates (object)
   - Example: "Mark tasks A, B, C as completed"

🔧 **archive_completed_tasks**  
   - Purpose: Archive all completed tasks
   - Parameters: none
   - Example: "Archive all my completed tasks"

🔧 **get_task_summary**
   - Purpose: Get comprehensive summary with insights
   - Parameters: none
   - Example: "Give me a detailed task summary"
"""

def get_tool_schema(use_dynamic: bool = False, mcp_client: Optional[EnhancedMCPClient] = None) -> str:
    """Get tool schema - either static or dynamic based on user preference"""
    
    if not use_dynamic:
        return get_static_tool_schema()
    
    if not mcp_client:
        st.warning("⚠️ Dynamic mode selected but no MCP client available. Using static schema.")
        return get_static_tool_schema()
    
    # Try dynamic discovery
    tools_data = mcp_client.get_dynamic_tools()
    
    if tools_data:
        dynamic_schema = mcp_client.convert_mcp_tools_to_schema(tools_data)
        return dynamic_schema
    else:
        st.warning("⚠️ Dynamic tool discovery failed. Falling back to static schema.")
        return get_static_tool_schema()

# Enhanced process function with dynamic support
def process_gemini_request_enhanced(user_input: str, model, mcp_client: EnhancedMCPClient, use_dynamic_tools: bool = False):
    """Enhanced Gemini processing with dynamic tool discovery support"""
    
    # Check if we should use fallback mode
    if st.session_state.get('use_fallback_mode', False):
        return process_fallback_request(user_input, mcp_client)
    
    # Get appropriate tool schema
    tool_schema = get_tool_schema(use_dynamic=use_dynamic_tools, mcp_client=mcp_client)
    
    # Show which mode we're using
    mode = "Dynamic" if use_dynamic_tools else "Static"
    st.info(f"🔧 Using {mode} tool discovery")
    
    analysis_prompt = f"""
You are a task management assistant. Analyze this user request and determine the appropriate action.

{tool_schema}

User request: "{user_input}"

IMPORTANT RULES:
1. For create_task: ALWAYS include a "title" field (this is REQUIRED)
2. For create_task: Only use "title", "description", and "priority" fields
3. RESPOND WITH PURE JSON ONLY - NO MARKDOWN CODE BLOCKS OR FORMATTING

If this is a task operation, respond with JSON in this EXACT format (NO ``` markers):
{{
    "action": "tool_call",
    "tool": "tool_name_here",
    "parameters": {{
        "title": "extracted title here",
        "priority": "high|medium|low",
        "description": "optional description"
    }},
    "explanation": "Brief explanation of what you're doing"
}}

If it's just conversation, respond with (NO ``` markers):
{{
    "action": "chat", 
    "response": "Your response here"
}}

IMPORTANT: Return ONLY the JSON object, no extra text or formatting.
"""
    
    try:
        # Add dynamic discovery indicator
        discovery_msg = "🤖 Analyzing request with Gemini (Dynamic Tools)" if use_dynamic_tools else "🤖 Analyzing request with Gemini (Static Tools)"
        
        with st.spinner(discovery_msg):
            analysis = call_gemini_with_retry(model, analysis_prompt)
        
        # Rest of your existing parsing logic...
        cleaned_analysis = analysis.strip()
        
        # JSON cleanup logic (same as before)
        if cleaned_analysis.startswith('```json'):
            start_idx = cleaned_analysis.find('{')
            end_idx = cleaned_analysis.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                cleaned_analysis = cleaned_analysis[start_idx:end_idx]
        elif cleaned_analysis.startswith('```'):
            lines = cleaned_analysis.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned_analysis = '\n'.join(lines)
        
        # Debug output with mode indicator
        if st.session_state.get('show_debug', False):
            st.write(f"🔍 **Debug - Gemini Analysis ({mode} Mode):**")
            st.code(cleaned_analysis, language="json")
        
        try:
            parsed = json.loads(cleaned_analysis)
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON Parse Error: {e}")
            return {"action": "error", "response": f"Failed to parse AI response"}
        
        if parsed.get("action") == "tool_call":
            tool_name = parsed.get("tool")
            parameters = parsed.get("parameters", {})
            
            # Validate tool exists if using dynamic mode
            if use_dynamic_tools:
                tools_info = mcp_client.get_tools_info()
                available_tools = tools_info.get('tools', [])
                
                if tool_name not in available_tools:
                    st.error(f"❌ Tool '{tool_name}' not found in available tools: {available_tools}")
                    return {"action": "error", "response": f"Tool '{tool_name}' not available"}
            
            st.success(f"🔧 Calling tool: `{tool_name}` ({mode} mode)")
            
            try:
                tool_result = mcp_client.call_tool(tool_name, parameters)
                
                if "error" in tool_result:
                    response_text = f"❌ Error: {tool_result['error']}"
                elif tool_result.get("message"):
                    response_text = f"✅ {tool_result['message']}"
                    if "task" in tool_result:
                        task = tool_result["task"]
                        response_text += f"\n\n📋 **Task Details:**\n- Title: {task.get('title')}\n- Priority: {task.get('priority')}\n- Completed: {task.get('completed')}"
                else:
                    response_text = "✅ Operation completed successfully!"
                
                return {
                    "action": "tool_result",
                    "response": response_text,
                    "tool_result": tool_result,
                    "mode": mode
                }
                
            except Exception as e:
                st.error(f"❌ Tool execution error: {e}")
                return {"action": "error", "response": f"Failed to execute tool: {e}"}
        
        else:
            return parsed
            
    except Exception as e:
        st.error(f"❌ Gemini request error: {e}")
        return {"action": "error", "response": f"Error processing request: {e}"}

# Initialize clients
@st.cache_resource
def init_clients():
    # Configure Gemini
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-2.0-flash'))
    
    # Initialize MCP clients
    legacy_mcp_client = MCPClient()
    enhanced_mcp_client = EnhancedMCPClient()  
    
    return model, legacy_mcp_client, enhanced_mcp_client

def main():
    st.title("📋 Task Management Assistant")
    st.markdown("*Powered by Gemini AI + MCP Server + MongoDB*")
    
    # Initialize clients with enhanced version
    try:
        model, legacy_client, enhanced_client = init_clients()
        
        # Use enhanced client as primary, legacy as fallback
        mcp_client = enhanced_client
        
    except Exception as e:
        st.error(f"Failed to initialize: {e}")
        st.stop()
    
    # Check MCP server health
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if mcp_client.health_check():
            st.success("✅ MCP Server Connected")
        else:
            st.error("🚨 MCP Server Disconnected")
    
    with col2:
        # Test API health
        try:
            response = requests.get("http://localhost:3001/health")
            if response.status_code == 200:
                st.success("✅ API Server Connected")
            else:
                st.error("🚨 API Server Issues")
        except:
            st.error("🚨 API Server Disconnected")
    
    with col3:
        # Test MongoDB by getting task count
        try:
            result = mcp_client.call_tool('list_tasks', {})
            if "tasks" in result:
                task_count = len(result["tasks"])
                st.success(f"✅ MongoDB ({task_count} tasks)")
            else:
                st.warning("⚠️ MongoDB Issues")
        except:
            st.error("🚨 MongoDB Disconnected")

    # Tool discovery settings panel
    show_tool_discovery_settings(mcp_client)

    # Show current mode indicator
    use_dynamic = st.session_state.get('use_dynamic_tools', False)
    mode = "Dynamic" if use_dynamic else "Static" 
    mode_icon = "🔍" if use_dynamic else "📋"

    st.info(f"{mode_icon} **Tool Discovery Mode:** {mode}")

    if use_dynamic:
        tools_info = mcp_client.get_tools_info()
        if tools_info['available']:
            st.success(f"✅ Discovered {tools_info['count']} tools | Cache: {tools_info['cache_status']}")
        else:
            st.warning("⚠️ Dynamic discovery failed - using static fallback")
    
    # Sidebar with quick actions
    st.sidebar.header("🚀 Quick Actions")
    
    if st.sidebar.button("📋 Show All Tasks"):
        try:
            result = mcp_client.call_tool('list_tasks', {})
            st.sidebar.success("✅ Fetched tasks")
            st.json(result)
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
    
    if st.sidebar.button("📊 Show Statistics"):
        try:
            result = mcp_client.call_tool('get_task_stats', {})
            st.sidebar.success("✅ Fetched stats")
            st.json(result)
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
    
    # Direct tool testing
    st.sidebar.subheader("🧪 Direct Tool Testing")
    if st.sidebar.button("Test Create Task"):
        try:
            result = mcp_client.create_task(
                title="Test Task from Sidebar",
                description="This is a test task",
                priority="medium"
            )
            st.sidebar.success("✅ Created test task")
            st.json(result)
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
    
    # Task creation form
    st.sidebar.subheader("📝 Manual Task Creation")
    with st.sidebar.form("quick_task"):
        task_title = st.text_input("Task Title")
        task_priority = st.selectbox("Priority", ["low", "medium", "high"])
        task_description = st.text_area("Description (optional)")
        
        if st.form_submit_button("Create Task"):
            if task_title:
                try:
                    result = mcp_client.create_task(
                        title=task_title,
                        description=task_description,
                        priority=task_priority
                    )
                    st.sidebar.success("✅ Task created!")
                    st.json(result)
                except Exception as e:
                    st.sidebar.error(f"❌ Error: {e}")
            else:
                st.sidebar.error("Please enter a task title")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant", 
                "content": f"Hello! I'm your Task Management Assistant running in **{mode} Tool Discovery** mode. I can help you create, update, delete, and view your tasks. Try saying: 'Create a high priority task to test the system'"
            }
        ]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Enhanced chat input processing
    if prompt := st.chat_input(f"Ask me about your tasks... (Using {mode} mode)"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response with dynamic tool support
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                use_dynamic = st.session_state.get('use_dynamic_tools', False)
                
                # Use enhanced processing function
                result = process_gemini_request_enhanced(
                    prompt, 
                    model, 
                    mcp_client, 
                    use_dynamic_tools=use_dynamic
                )
                
                response = result.get("response", "I'm not sure how to help with that.")
                
                # Show mode used in response
                response_mode = result.get("mode", mode)
                mode_badge = f"*[{response_mode} Mode]*"
                
                st.markdown(f"{response} {mode_badge}")
                
                # Tool result handling
                if result.get("tool_result") and result["action"] == "tool_result":
                    tool_result = result["tool_result"]
                    
                    # Special handling for different types of results
                    if "tasks" in tool_result:
                        tasks = tool_result["tasks"]
                        if tasks:
                            st.subheader("📋 Tasks")
                            df = pd.DataFrame(tasks)
                            st.dataframe(df, use_container_width=True)
                        else:
                            st.info("No tasks found.")
                    
                    elif "stats" in tool_result:
                        stats = tool_result["stats"]
                        st.subheader("📊 Task Statistics")
                        
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Tasks", stats.get("total", 0))
                        with col2:
                            st.metric("Completed", stats.get("completed", 0))
                        with col3:
                            st.metric("Pending", stats.get("pending", 0))
                        with col4:
                            st.metric("High Priority", stats.get("highPriority", 0))
                        
                        # Priority distribution chart
                        if stats.get("total", 0) > 0:
                            priority_data = {
                                "Priority": ["High", "Medium", "Low"],
                                "Count": [stats.get("highPriority", 0), stats.get("mediumPriority", 0), stats.get("lowPriority", 0)]
                            }
                            fig = px.pie(priority_data, values="Count", names="Priority", title="Tasks by Priority")
                            st.plotly_chart(fig, use_container_width=True)
        
        # Add assistant response to chat history
        response_with_mode = f"{response} {mode_badge}"
        st.session_state.messages.append({"role": "assistant", "content": response_with_mode})

if __name__ == "__main__":
    main()