# Task Management MCP Server

A Model Context Protocol (MCP) server that connects Claude to a MongoDB-backed task management system.

## Features

- ✅ Create, read, update, delete tasks
- 📊 Task statistics and analytics
- 🗄️ MongoDB persistence
- 🔄 Real-time data access
- 🛡️ Type-safe API calls

## Quick Start

1. **Start MongoDB** (ensure it's running on localhost:27017)
2. **Start API**: `cd task-api && npm install && npm start`
3. **Start MCP Server**: `cd mcp-server && npm install && npm start`
4. **Configure Claude** with MCP server path
5. **Test with Claude**: "Show me all my tasks"

## Project Structure

- `task-api/` - Express.js REST API with MongoDB
- `mcp-server/` - MCP protocol server
- MongoDB database: `task_management`
- Collection: `tasks`

## Example Commands for Claude

- "List all my tasks"
- "Create a high priority task called 'Deploy to production'"
- "Mark task [id] as completed"
- "Show me task statistics"
- "Delete task [id]"