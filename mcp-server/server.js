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

class EnhancedTaskMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: 'enhanced-task-management-server',
        version: '2.0.0',
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
        apiUrl: API_BASE_URL,
        version: '2.0.0',
        clients: ['Streamlit Web App', 'CLI Tool', 'Claude Desktop']
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
      console.log(`🌐 Enhanced MCP HTTP Server running on http://localhost:${MCP_HTTP_PORT}`);
      console.log(`📡 Health check: http://localhost:${MCP_HTTP_PORT}/health`);
      console.log(`🔧 Tools: http://localhost:${MCP_HTTP_PORT}/tools`);
    });
  }

  async getTools() {
    return {
      tools: [
        // Original tools
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
        
        // NEW ENHANCED TOOLS
        {
          name: 'search_tasks',
          description: 'Search tasks by keyword in title or description',
          parameters: {
            query: { type: 'string', description: 'Search query', required: true },
            limit: { type: 'number', description: 'Maximum number of results (default: 10)' },
          },
        },
        {
          name: 'get_tasks_by_priority',
          description: 'Get tasks filtered by priority level',
          parameters: {
            priority: { type: 'string', description: 'Priority level to filter by', enum: ['low', 'medium', 'high'], required: true },
          },
        },
        {
          name: 'get_tasks_by_status',
          description: 'Get tasks filtered by completion status',
          parameters: {
            completed: { type: 'boolean', description: 'Completion status to filter by', required: true },
          },
        },
        {
          name: 'bulk_update_tasks',
          description: 'Update multiple tasks at once',
          parameters: {
            task_ids: { type: 'array', description: 'Array of task IDs to update', required: true },
            updates: { type: 'object', description: 'Updates to apply to all tasks', required: true },
          },
        },
        {
          name: 'get_recent_tasks',
          description: 'Get recently created or updated tasks',
          parameters: {
            limit: { type: 'number', description: 'Number of tasks to return (default: 5)' },
            days: { type: 'number', description: 'Number of days to look back (default: 7)' },
          },
        },
        {
          name: 'archive_completed_tasks',
          description: 'Archive all completed tasks (marks them as archived)',
          parameters: {},
        },
        {
          name: 'get_task_summary',
          description: 'Get a comprehensive summary of all tasks with insights',
          parameters: {},
        },
      ],
    };
  }

  async callTool(toolName, args) {
    console.log(`Executing tool: ${toolName}`);
    
    try {
      switch (toolName) {
        // Original tools
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
        
        // NEW ENHANCED TOOLS
        case 'search_tasks':
          return await this.searchTasks(args);
        case 'get_tasks_by_priority':
          return await this.getTasksByPriority(args);
        case 'get_tasks_by_status':
          return await this.getTasksByStatus(args);
        case 'bulk_update_tasks':
          return await this.bulkUpdateTasks(args);
        case 'get_recent_tasks':
          return await this.getRecentTasks(args);
        case 'archive_completed_tasks':
          return await this.archiveCompletedTasks();
        case 'get_task_summary':
          return await this.getTaskSummary();
        
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

  // ORIGINAL TOOL IMPLEMENTATIONS
  async listTasks() {
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }
      const tasks = await response.json();
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
    try {
      const response = await fetch(`${API_BASE_URL}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(args),
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        let error;
        try {
          error = JSON.parse(errorText);
        } catch {
          error = { error: errorText };
        }
        throw new Error(error.error || `HTTP ${response.status}`);
      }
      
      const task = await response.json();
      return { task, message: 'Task created successfully!' };
    } catch (error) {
      console.error('Error in createTask:', error);
      throw error;
    }
  }

  async updateTask(args) {
    try {
      const { id, ...updateData } = args;
      const response = await fetch(`${API_BASE_URL}/tasks/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
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
    try {
      const response = await fetch(`${API_BASE_URL}/tasks/stats`);
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }
      const stats = await response.json();
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

  // NEW ENHANCED TOOL IMPLEMENTATIONS
  async searchTasks(args) {
    try {
      const { query, limit = 10 } = args;
      
      // First get all tasks, then filter (in a real app, you'd do this in the database)
      const response = await fetch(`${API_BASE_URL}/tasks`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const allTasks = await response.json();
      const searchQuery = query.toLowerCase();
      
      const matchingTasks = allTasks
        .filter(task => 
          task.title.toLowerCase().includes(searchQuery) || 
          (task.description && task.description.toLowerCase().includes(searchQuery))
        )
        .slice(0, limit);
      
      return {
        tasks: matchingTasks,
        message: `Found ${matchingTasks.length} task(s) matching "${query}"`,
        query: query
      };
    } catch (error) {
      console.error('Error in searchTasks:', error);
      throw error;
    }
  }

  async getTasksByPriority(args) {
    try {
      const { priority } = args;
      
      const response = await fetch(`${API_BASE_URL}/tasks`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const allTasks = await response.json();
      const filteredTasks = allTasks.filter(task => task.priority === priority);
      
      return {
        tasks: filteredTasks,
        message: `Found ${filteredTasks.length} task(s) with ${priority} priority`,
        priority: priority
      };
    } catch (error) {
      console.error('Error in getTasksByPriority:', error);
      throw error;
    }
  }

  async getTasksByStatus(args) {
    try {
      const { completed } = args;
      
      const response = await fetch(`${API_BASE_URL}/tasks`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const allTasks = await response.json();
      const filteredTasks = allTasks.filter(task => task.completed === completed);
      
      return {
        tasks: filteredTasks,
        message: `Found ${filteredTasks.length} ${completed ? 'completed' : 'pending'} task(s)`,
        completed: completed
      };
    } catch (error) {
      console.error('Error in getTasksByStatus:', error);
      throw error;
    }
  }

  async bulkUpdateTasks(args) {
    try {
      const { task_ids, updates } = args;
      const results = [];
      let successCount = 0;
      let errorCount = 0;
      
      for (const taskId of task_ids) {
        try {
          const response = await fetch(`${API_BASE_URL}/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
          });
          
          if (response.ok) {
            const updatedTask = await response.json();
            results.push({ id: taskId, success: true, task: updatedTask });
            successCount++;
          } else {
            results.push({ id: taskId, success: false, error: `HTTP ${response.status}` });
            errorCount++;
          }
        } catch (error) {
          results.push({ id: taskId, success: false, error: error.message });
          errorCount++;
        }
      }
      
      return {
        results: results,
        summary: {
          total: task_ids.length,
          successful: successCount,
          failed: errorCount
        },
        message: `Bulk update completed: ${successCount} successful, ${errorCount} failed`
      };
    } catch (error) {
      console.error('Error in bulkUpdateTasks:', error);
      throw error;
    }
  }

  async getRecentTasks(args) {
    try {
      const { limit = 5, days = 7 } = args;
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - days);
      
      const response = await fetch(`${API_BASE_URL}/tasks`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const allTasks = await response.json();
      const recentTasks = allTasks
        .filter(task => {
          const taskDate = new Date(task.createdAt || task.updatedAt);
          return taskDate >= cutoffDate;
        })
        .sort((a, b) => new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt))
        .slice(0, limit);
      
      return {
        tasks: recentTasks,
        message: `Found ${recentTasks.length} task(s) from the last ${days} days`,
        period: `${days} days`,
        cutoff_date: cutoffDate.toISOString()
      };
    } catch (error) {
      console.error('Error in getRecentTasks:', error);
      throw error;
    }
  }

  async archiveCompletedTasks() {
    try {
      // Get all completed tasks
      const response = await fetch(`${API_BASE_URL}/tasks`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const allTasks = await response.json();
      const completedTasks = allTasks.filter(task => task.completed);
      
      // Update each completed task to add archived flag
      let archivedCount = 0;
      for (const task of completedTasks) {
        try {
          const updateResponse = await fetch(`${API_BASE_URL}/tasks/${task.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ archived: true }),
          });
          
          if (updateResponse.ok) {
            archivedCount++;
          }
        } catch (error) {
          console.error(`Failed to archive task ${task.id}:`, error);
        }
      }
      
      return {
        message: `Archived ${archivedCount} completed task(s)`,
        archived_count: archivedCount,
        total_completed: completedTasks.length
      };
    } catch (error) {
      console.error('Error in archiveCompletedTasks:', error);
      throw error;
    }
  }

  async getTaskSummary() {
    try {
      const [tasksResponse, statsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/tasks`),
        fetch(`${API_BASE_URL}/tasks/stats`)
      ]);
      
      if (!tasksResponse.ok || !statsResponse.ok) {
        throw new Error('Failed to fetch data');
      }
      
      const tasks = await tasksResponse.json();
      const stats = await statsResponse.json();
      
      // Calculate additional insights
      const recentTasks = tasks.filter(task => {
        const taskDate = new Date(task.createdAt);
        const daysDiff = (new Date() - taskDate) / (1000 * 60 * 60 * 24);
        return daysDiff <= 7;
      });
      
      const urgentTasks = tasks.filter(task => 
        task.priority === 'high' && !task.completed
      );
      
      return {
        overview: stats,
        insights: {
          recent_tasks_count: recentTasks.length,
          urgent_pending_tasks: urgentTasks.length,
          completion_rate: stats.total > 0 ? Math.round((stats.completed / stats.total) * 100) : 0,
          most_common_priority: stats.highPriority >= stats.mediumPriority && stats.highPriority >= stats.lowPriority ? 'high' :
                                stats.mediumPriority >= stats.lowPriority ? 'medium' : 'low'
        },
        urgent_tasks: urgentTasks.slice(0, 3), // Top 3 urgent tasks
        recent_activity: recentTasks.slice(0, 5), // 5 most recent tasks
        message: 'Comprehensive task summary generated successfully'
      };
    } catch (error) {
      console.error('Error in getTaskSummary:', error);
      throw error;
    }
  }

  setupErrorHandling() {
    this.server.onerror = (error) => {
      console.error('[MCP Error]', error);
    };

    process.on('SIGINT', async () => {
      console.log('\n🛑 Shutting down Enhanced MCP server...');
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
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('🚀 Enhanced Task Management MCP server running on stdio');
    console.error('✅ Ready to receive commands from Claude and HTTP clients');
    console.error('🆕 New tools available: search, filter, bulk operations, and more!');
  }
}

const server = new EnhancedTaskMCPServer();
server.run().catch(console.error);