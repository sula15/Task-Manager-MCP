# 🚀 CLI Task Management Client

A powerful command-line interface for the MCP Task Management System. This CLI client provides lightning-fast task management capabilities with beautiful terminal output, working seamlessly with your Gemini-powered web interface and other MCP clients.

## ✨ Features

- 🎨 **Rich Terminal UI** - Beautiful colored output with tables and progress bars
- ⚡ **Lightning Fast** - Instant task operations from the command line
- 🔍 **Smart Search** - Find tasks by keywords with advanced filtering
- 📊 **Real-time Statistics** - Comprehensive task analytics and insights
- 🔄 **Multi-Client Sync** - Works with Streamlit web app and Claude Desktop
- 🛡️ **Error Handling** - Graceful error messages and connection management
- 📱 **Interactive Mode** - Smart prompts when arguments are missing

## 🏗️ Architecture

```
CLI Client → MCP Server → Task API → MongoDB
     ↕              ↕           ↕
Gemini Web App ←→ Same Data ←→ Claude Desktop
```

## 📋 Available Commands

### **Core Commands**

| Command | Description | Usage |
|---------|-------------|-------|
| `list` | List all tasks | `python cli_client.py list` |
| `create` | Create new task | `python cli_client.py create "Task title" --priority high` |
| `search` | Search tasks | `python cli_client.py search "keyword" --limit 10` |
| `stats` | Show statistics | `python cli_client.py stats` |
| `health` | Check server health | `python cli_client.py health` |

### **Global Options**

| Option | Description | Default |
|--------|-------------|---------|
| `--server` | MCP server URL | `http://localhost:3002` |
| `--help` | Show help message | - |

## 🚀 Quick Start

### Prerequisites
- Python 3.6+
- MCP Server running on port 3002
- Task API running on port 3001
- MongoDB running on port 27017

### Setup
```bash
# Navigate to CLI client directory
cd cli-client

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

# Verify installation
python cli_client.py --help
```

### First Commands
```bash
# Check if everything is working
python cli_client.py health

# List existing tasks
python cli_client.py list

# Create your first task
python cli_client.py create "My first CLI task" --priority high

# View statistics
python cli_client.py stats
```

## 📖 Command Reference

### **📋 list - List All Tasks**
Display all tasks in a beautiful table format.

```bash
# Basic usage
python cli_client.py list

# With custom server
python cli_client.py --server http://localhost:3002 list
```

**Output:**
```
                                📋 All Tasks                                
┏━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Status   ┃ Priority ┃ Title          ┃ Description    ┃ ID           ┃
┡━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ ⏳ Pending │ HIGH     │ Deploy app     │ Production...  │ 507f1f77...  │
│ ✅ Done    │ MEDIUM   │ Fix bug        │ Login issue    │ 507f1f78...  │
└──────────┴──────────┴────────────────┴────────────────┴──────────────┘

💡 Found 2 tasks
```

### **➕ create - Create New Task**
Create new tasks with various options.

```bash
# Full command
python cli_client.py create "Task title" --priority high --description "Detailed description"

# Quick creation (medium priority by default)
python cli_client.py create "Quick task"

# Interactive mode (prompts for missing info)
python cli_client.py create

# Priority options: low, medium, high
python cli_client.py create "Important task" --priority high
```

**Arguments:**
- `title` - Task title (required, or prompted)
- `--priority` - Task priority: `low`, `medium`, `high` (default: `medium`)
- `--description` - Task description (optional)

**Interactive Example:**
```bash
$ python cli_client.py create
📝 Enter task title: Deploy new feature
💬 Add a description? (y/N): y
📄 Enter description: Deploy the new authentication feature to production

✅ Task created successfully!
   📋 Title: Deploy new feature
   🔥 Priority: MEDIUM
   🆔 ID: 507f1f77bcf86cd799439011
```

### **🔍 search - Search Tasks**
Find tasks by keywords in title or description.

```bash
# Basic search
python cli_client.py search "deployment"

# Search with limit
python cli_client.py search "bug" --limit 5

# Interactive search
python cli_client.py search
```

**Arguments:**
- `query` - Search keyword (required, or prompted)
- `--limit` - Maximum results (default: 10)

**Example:**
```bash
$ python cli_client.py search "api" --limit 3

🔍 Search Results for 'api'
┏━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Status   ┃ Priority ┃ Title          ┃ Description    ┃ ID           ┃
┡━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│ ⏳ Pending │ HIGH     │ Fix API bug    │ Auth endpoint  │ 507f1f77...  │
│ ✅ Done    │ MEDIUM   │ API docs       │ Update docs    │ 507f1f78...  │
└──────────┴──────────┴────────────────┴────────────────┴──────────────┘

💡 Found 2 task(s) matching "api"
```

### **📊 stats - Show Statistics**
Display comprehensive task statistics and insights.

```bash
# Show statistics dashboard
python cli_client.py stats
```

**Output:**
```
                              📈 Dashboard                              
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│ 📊 Task Statistics                                                  │
│ ├── Total Tasks: 15                                                 │
│ ├── Completed: 8                                                    │
│ ├── Pending: 7                                                      │
│ ├── High Priority: 3                                                │
│ ├── Medium Priority: 8                                              │
│ └── Low Priority: 4                                                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### **🏥 health - Check Server Health**
Verify that the MCP server and related services are running.

```bash
# Check system health
python cli_client.py health
```

**Healthy System:**
```
✅ MCP Server is healthy
   Version: 2.0.0
   Clients: Streamlit Web App, CLI Tool, Claude Desktop
```

**Unhealthy System:**
```
❌ MCP Server is not responding
```

## 🎯 Usage Scenarios

### **🌅 Morning Routine**
```bash
# Quick status check
python cli_client.py stats

# Review pending tasks
python cli_client.py list

# Check for urgent items
python cli_client.py search "urgent" --limit 5
```

### **🚀 Development Workflow**
```bash
# Create tasks for bugs
python cli_client.py create "Fix login validation" --priority high --description "Users can't login with special characters"

# Create feature tasks
python cli_client.py create "Add dark mode" --priority medium --description "Implement dark/light theme toggle"

# Track progress
python cli_client.py stats
```

### **🔍 Project Management**
```bash
# Find all tasks for a specific feature
python cli_client.py search "authentication" --limit 20

# Check sprint progress
python cli_client.py search "sprint-3" --limit 10

# Review high priority items
python cli_client.py search "priority:high" --limit 5
```

### **📈 Reporting**
```bash
# Generate daily report
echo "📊 Daily Task Report - $(date)"
python cli_client.py stats
python cli_client.py search "today" --limit 10
```

## 🔄 Multi-Client Workflow

The CLI client works seamlessly with other interfaces:

### **CLI + Gemini Web App**
1. **Create via CLI**: `python cli_client.py create "Deploy feature" --priority high`
2. **View in Web**: Open Streamlit app, ask Gemini "Show me high priority tasks"
3. **Search via CLI**: `python cli_client.py search "deploy"`
4. **Update via Web**: Use Gemini to mark tasks as completed

### **CLI + Claude Desktop**
1. **Bulk create via CLI**: Multiple quick task creation
2. **Smart queries via Claude**: "What are the most urgent tasks this week?"
3. **Status via CLI**: `python cli_client.py stats`

## 🛠️ Troubleshooting

### **Connection Issues**

**Problem**: `❌ Cannot connect to MCP server`
```bash
# Check if MCP server is running
curl http://localhost:3002/health

# Start MCP server
cd ../mcp-server
npm start
```

**Problem**: `❌ Request timed out`
```bash
# Check server status
python cli_client.py health

# Try with different server URL
python cli_client.py --server http://localhost:3002 health
```

### **Virtual Environment Issues**

**Problem**: `ModuleNotFoundError: No module named 'rich'`
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

**Problem**: `Command not found: python`
```bash
# Try with python3
python3 cli_client.py health

# Or check Python installation
which python
which python3
```

### **Permission Issues**

**Problem**: Permission denied
```bash
# Make script executable (Linux/Mac)
chmod +x cli_client.py

# Run with explicit python
python cli_client.py health
```

## 🚀 Advanced Usage

### **Custom Server URL**
```bash
# Connect to different MCP server
python cli_client.py --server http://localhost:3003 health
python cli_client.py --server http://remote-server:3002 list
```

### **Scripting and Automation**
```bash
#!/bin/bash
# Daily task automation script

# Activate CLI environment
cd /path/to/cli-client
source venv/bin/activate

# Create daily standup report
echo "📊 Daily Standup Report - $(date)" > daily_report.txt
echo "================================" >> daily_report.txt
python cli_client.py stats >> daily_report.txt
echo "" >> daily_report.txt
echo "🔍 High Priority Tasks:" >> daily_report.txt
python cli_client.py search "priority:high" --limit 5 >> daily_report.txt

# Email or slack the report
# mail -s "Daily Tasks" team@company.com < daily_report.txt
```

### **Shell Aliases**
```bash
# Add to ~/.bashrc or ~/.zshrc
alias task='cd /path/to/cli-client && source venv/bin/activate && python cli_client.py'
alias tlist='task list'
alias tstats='task stats'
alias tsearch='task search'

# Usage after sourcing
tlist
tstats
tsearch "bug"
```

## 🔧 Configuration

### **Environment Variables**
```bash
# Set default MCP server URL
export MCP_SERVER_URL="http://localhost:3002"

# Use in CLI
python cli_client.py --server $MCP_SERVER_URL health
```

### **Requirements**
The CLI client requires these Python packages:
```
requests==2.31.0
rich==13.7.0
```

## 📚 Integration Examples

### **With Git Hooks**
```bash
#!/bin/bash
# .git/hooks/pre-commit
# Create task for each commit

cd /path/to/cli-client
source venv/bin/activate

COMMIT_MSG=$(git log -1 --pretty=%B)
python cli_client.py create "Review: $COMMIT_MSG" --priority medium --description "Code review needed for latest commit"
```

### **With CI/CD**
```bash
# In your CI pipeline
- name: Create deployment task
  run: |
    cd cli-client
    source venv/bin/activate
    python cli_client.py create "Deploy to staging" --priority high --description "Deploy commit ${{ github.sha }}"
```

## 🤝 Contributing

### **Adding New Commands**
1. Add command parser to `main()` function
2. Create command handler method (`cmd_<command_name>`)
3. Add to `command_methods` dictionary
4. Update help text and README

### **Extending Functionality**
- Add new MCP tools support
- Implement advanced filtering options
- Add export/import capabilities
- Create custom output formats

## 📄 License

This CLI client is part of the MCP Task Management System.

## 🔗 Related

- [Main Project README](../README.md)
- [MCP Server Documentation](../mcp-server/README.md)
- [Streamlit Web App](../streamlit-app/README.md)
- [Task API Documentation](../task-api/README.md)

---

**Happy task managing!** 🚀

For issues or questions, check the troubleshooting section above or refer to the main project documentation.