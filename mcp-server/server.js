import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import express from 'express';
import cors from 'cors';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const API_BASE_URL = 'http://localhost:3001';
const MCP_HTTP_PORT = 3002;

class TaskMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'task-management-mongodb-server',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.setupErrorHandling();
    this.setupHttpServer();
  }

  setupHttpServer() {
    // Create Express server for HTTP access
    this.httpApp = express();
    this.httpApp.use(cors());
    this.httpApp.use(express.json());

    // Add request logging
    this.httpApp.use((req, res, next) => {
      console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
      console.log('Body:', req.body);
      next();
    });

    // Health check
    this.httpApp.get('/health', (req, res) => {
      res.json({ 
        status: 'OK', 
        timestamp: new Date().toISOString(),
        apiUrl: API_BASE_URL 
      });
    });

    // List tools endpoint
    this.httpApp.get('/tools', async (req, res) => {
      try {
        const tools = await this.getTools();
        res.json(tools);
      } catch (error) {
        console.error('Error in /tools:', error);
        res.status(500).json({ error: error.message, stack: error.stack });
      }
    });

    // Call tool endpoint
    this.httpApp.post('/tools/:toolName', async (req, res) => {
      try {
        const { toolName } = req.params;
        const args = req.body;
        
        console.log(`Calling tool: ${toolName} with args:`, args);
        
        const result = await this.callTool(toolName, args);
        console.log(`Tool ${toolName} result:`, result);
        
        res.json(result);
      } catch (error) {
        console.error(`Error in tool ${req.params.toolName}:`, error);
        res.status(500).json({ 
          error: error.message, 
          stack: error.stack,
          tool: req.params.toolName,
          args: req.body
        });
      }
    });

    // Error handling middleware
    this.httpApp.use((error, req, res, next) => {
      console.error('Express error:', error);
      res.status(500).json({ 
        error: 'Internal server error', 
        message: error.message 
      });
    });

    this.httpApp.listen(MCP_HTTP_PORT, () => {
      console.log(`🌐 MCP HTTP Server running on http://localhost:${MCP_HTTP_PORT}`);
      console.log(`📡 Health check: http://localhost:${MCP_HTTP_PORT}/health`);
      console.log(`🔧 Tools: http://localhost:${MCP_HTTP_PORT}/tools`);
    });
  }

  async getTools() {
    return {
      tools: [
        {
          name: 'list_tasks',
          description: 'Get all tasks from MongoDB with sorting by creation date',
          parameters: {},
        },
        {
          name: 'get_task',
          description: 'Get a specific task by ID',
          parameters: {
            id: { type: 'string', description: 'Task ID (MongoDB ObjectId)', required: true },
          },
        },
        {
          name: 'create_task',
          description: 'Create a new task in MongoDB',
          parameters: {
            title: { type: 'string', description: 'Task title', required: true },
            description: { type: 'string', description: 'Task description' },
            priority: { type: 'string', description: 'Priority: low, medium, high', enum: ['low', 'medium', 'high'] },
          },
        },
        {
          name: 'update_task',
          description: 'Update an existing task in MongoDB',
          parameters: {
            id: { type: 'string', description: 'Task ID', required: true },
            title: { type: 'string', description: 'New title' },
            description: { type: 'string', description: 'New description' },
            completed: { type: 'boolean', description: 'Completion status' },
            priority: { type: 'string', description: 'Priority level', enum: ['low', 'medium', 'high'] },
          },
        },
        {
          name: 'delete_task',
          description: 'Delete a task from MongoDB',
          parameters: {
            id: { type: 'string', description: 'Task ID to delete', required: true },
          },
        },
        {
          name: 'get_task_stats',
          description: 'Get comprehensive task statistics from MongoDB',
          parameters: {},
        },
      ],
    };
  }

  async callTool(toolName, args) {
    console.log(`Executing tool: ${toolName}`);
    
    try {
      switch (toolName) {
        case 'list_tasks':
          return await this.listTasks();
        case 'get_task':
          return await this.getTask(args);
        case 'create_task':
          return await this.createTask(args);
        case 'update_task':
          return await this.updateTask(args);
        case 'delete_task':
          return await this.deleteTask(args);
        case 'get_task_stats':
          return await this.getTaskStats();
        default:
          throw new Error(`Unknown tool: ${toolName}`);
      }
    } catch (error) {
      console.error(`Error in callTool(${toolName}):`, error);
      throw error;
    }
  }

  setupToolHandlers() {
    // Keep existing stdio handlers for Claude Desktop compatibility
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return await this.getTools();
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;
      try {
        const result = await this.callTool(name, args);
        return {
          content: [
            {
              type: 'text',
              text: typeof result === 'string' ? result : JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`,
            },
          ],
        };
      }
    });
  }

  async listTasks() {
    console.log('Fetching tasks from API...');
    
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`);
      console.log('API response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API error response:', errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }
      
      const tasks = await response.json();
      console.log('Tasks fetched:', tasks.length);
      
      return { 
        tasks, 
        message: `Found ${tasks.length} task${tasks.length === 1 ? '' : 's'}` 
      };
    } catch (error) {
      console.error('Error in listTasks:', error);
      throw error;
    }
  }

  async getTask(args) {
    console.log('Getting task:', args.id);
    
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${args.id}`);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(error.error || `HTTP ${response.status}`);
      }
      
      const task = await response.json();
      return { task, message: 'Task retrieved successfully' };
    } catch (error) {
      console.error('Error in getTask:', error);
      throw error;
    }
  }

  async createTask(args) {
    console.log('Creating task:', args);
    
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(args),
      });
      
      console.log('Create task response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Create task error:', errorText);
        
        let error;
        try {
          error = JSON.parse(errorText);
        } catch {
          error = { error: errorText };
        }
        
        throw new Error(error.error || `HTTP ${response.status}`);
      }
      
      const task = await response.json();
      console.log('Task created successfully:', task);
      
      return { task, message: 'Task created successfully!' };
    } catch (error) {
      console.error('Error in createTask:', error);
      throw error;
    }
  }

  async updateTask(args) {
    console.log('Updating task:', args);
    
    try {
      const { id, ...updateData } = args;
      const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(error.error || `HTTP ${response.status}`);
      }
      
      const task = await response.json();
      return { task, message: 'Task updated successfully!' };
    } catch (error) {
      console.error('Error in updateTask:', error);
      throw error;
    }
  }

  async deleteTask(args) {
    console.log('Deleting task:', args.id);
    
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/${args.id}`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(error.error || `HTTP ${response.status}`);
      }
      
      return { message: `Task ${args.id} deleted successfully` };
    } catch (error) {
      console.error('Error in deleteTask:', error);
      throw error;
    }
  }

  async getTaskStats() {
    console.log('Fetching task statistics...');
    
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/stats`);
      console.log('Stats API response status:', response.status);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Stats API error:', errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }
      
      const stats = await response.json();
      console.log('Stats fetched successfully:', stats);
      
      return { 
        stats, 
        message: 'Statistics retrieved successfully',
        summary: `Total: ${stats.total}, Completed: ${stats.completed}, Pending: ${stats.pending}`
      };
    } catch (error) {
      console.error('Error in getTaskStats:', error);
      throw error;
    }
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error('[MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      console.log('\n🛑 Shutting down MCP server...');
      await this.server.close();
      process.exit(0);
    });

    process.on('uncaughtException', (error) => {
      console.error('Uncaught Exception:', error);
    });

    process.on('unhandledRejection', (reason, promise) => {
      console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    });
  }

  async run() {
    // Start stdio server for Claude Desktop
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('🚀 Task Management MCP server running on stdio');
    console.error('✅ Ready to receive commands from Claude and HTTP clients');
  }
}

const server = new TaskMCPServer();
server.run().catch(console.error);