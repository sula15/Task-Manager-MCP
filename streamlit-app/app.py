import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
import plotly.express as px
from mcp_client import MCPClient
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

# Initialize clients
@st.cache_resource
def init_clients():
    # Configure Gemini
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-1.5-flash'))
    
    # Initialize MCP client
    mcp_client = MCPClient()
    
    return model, mcp_client

def get_tool_schema():
    return """
Available Task Management Tools:

1. list_tasks
   - Purpose: Get all tasks from database
   - Parameters: none
   - Example: "Show me all tasks"

2. create_task  
   - Purpose: Create a new task
   - Required: title (string)
   - Optional: description (string), priority ("low"|"medium"|"high")
   - Example: Create task with title="Deploy app", priority="high"

3. update_task
   - Purpose: Update existing task
   - Required: id (string)
   - Optional: title, description, completed (boolean), priority
   - Example: Update task id="123" with completed=true

4. delete_task
   - Purpose: Delete a task
   - Required: id (string)
   - Example: Delete task with id="123"

5. get_task_stats
   - Purpose: Get task statistics
   - Parameters: none
   - Example: "Show task statistics"
"""

def process_gemini_request(user_input: str, model, mcp_client: MCPClient):
    """Process user input with Gemini and execute tool calls if needed"""
    
    tool_schema = get_tool_schema()
    
    # First, let Gemini analyze what the user wants
    analysis_prompt = f"""
You are a task management assistant. Analyze this user request and determine the appropriate action.

{tool_schema}

User request: "{user_input}"

IMPORTANT RULES:
1. For create_task: ALWAYS include a "title" field (this is REQUIRED)
2. For create_task: Only use "title", "description", and "priority" fields
3. For update_task: ALWAYS include "id" field
4. Priority must be one of: "low", "medium", "high"
5. Do NOT use fields like "status" or "name" - they don't exist
6. RESPOND WITH PURE JSON ONLY - NO MARKDOWN CODE BLOCKS OR FORMATTING

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

Examples:
- "Create a task to deploy the app" → {{"action": "tool_call", "tool": "create_task", "parameters": {{"title": "Deploy the app"}}}}
- "Create high priority task to review code" → {{"action": "tool_call", "tool": "create_task", "parameters": {{"title": "Review code", "priority": "high"}}}}

IMPORTANT: Return ONLY the JSON object, no extra text or formatting.
"""
    
    try:
        response = model.generate_content(analysis_prompt)
        analysis = response.text.strip()
        
        # Debug: Show what Gemini generated
        st.write("🔍 **Debug - Gemini Analysis:**")
        st.code(analysis, language="json")
        
        # Clean up the response - remove markdown code blocks if present
        cleaned_analysis = analysis.strip()
        
        # Remove markdown code block formatting
        if cleaned_analysis.startswith('```json'):
            # Find the start and end of the JSON content
            start_idx = cleaned_analysis.find('{')
            end_idx = cleaned_analysis.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                cleaned_analysis = cleaned_analysis[start_idx:end_idx]
        elif cleaned_analysis.startswith('```'):
            # Remove any code block markers
            lines = cleaned_analysis.split('\n')
            # Remove first and last lines if they contain ```
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines[-1].strip() == '```':
                lines = lines[:-1]
            cleaned_analysis = '\n'.join(lines)
        
        st.write("🧹 **Cleaned Analysis:**")
        st.code(cleaned_analysis, language="json")
        
        # Try to parse as JSON
        try:
            parsed = json.loads(cleaned_analysis)
        except json.JSONDecodeError as e:
            st.error(f"❌ JSON Parse Error: {e}")
            st.write("Raw response:", analysis)
            st.write("Cleaned response:", cleaned_analysis)
            return {"action": "error", "response": f"Failed to parse Gemini response: {analysis}"}
        
        if parsed.get("action") == "tool_call":
            # Validate parameters
            tool_name = parsed.get("tool")
            parameters = parsed.get("parameters", {})
            
            st.write(f"🔧 **Calling Tool:** `{tool_name}`")
            st.write(f"📋 **Parameters:** `{parameters}`")
            
            # Execute the tool call
            try:
                tool_result = mcp_client.call_tool(tool_name, parameters)
                st.write("✅ **Tool Result:**")
                st.json(tool_result)
                
                # Generate user-friendly response
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
                    "tool_result": tool_result
                }
                
            except Exception as e:
                st.error(f"❌ Tool execution error: {e}")
                return {"action": "error", "response": f"Failed to execute tool: {e}"}
        
        else:
            return parsed
            
    except Exception as e:
        st.error(f"❌ Gemini request error: {e}")
        return {"action": "error", "response": f"Error processing request: {e}"}

def main():
    st.title("📋 Task Management Assistant")
    st.markdown("*Powered by Gemini AI + MCP Server + MongoDB*")
    
    # Initialize clients
    try:
        model, mcp_client = init_clients()
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
            import requests
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
            result = mcp_client.call_tool('list_tasks')
            if "tasks" in result:
                task_count = len(result["tasks"])
                st.success(f"✅ MongoDB ({task_count} tasks)")
            else:
                st.warning("⚠️ MongoDB Issues")
        except:
            st.error("🚨 MongoDB Disconnected")
    
    # Sidebar with quick actions
    st.sidebar.header("🚀 Quick Actions")
    
    if st.sidebar.button("📋 Show All Tasks"):
        try:
            result = mcp_client.list_tasks()
            st.sidebar.success("✅ Fetched tasks")
            st.json(result)
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
    
    if st.sidebar.button("📊 Show Statistics"):
        try:
            result = mcp_client.get_task_stats()
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
            {"role": "assistant", "content": "Hello! I'm your Task Management Assistant. I can help you create, update, delete, and view your tasks. Try saying: 'Create a high priority task to test the system'"}
        ]
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about your tasks..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = process_gemini_request(prompt, model, mcp_client)
                
                response = result.get("response", "I'm not sure how to help with that.")
                st.markdown(response)
                
                # Show tool result data if available
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
        st.session_state.messages.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    main()