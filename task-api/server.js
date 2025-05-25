// Load environment variables
require('dotenv').config();

const express = require('express');
const cors = require('cors');
const { MongoClient, ObjectId } = require('mongodb');

const app = express();
const port = process.env.PORT || 3001;

// Middleware
app.use(express.json());
app.use(cors());

// MongoDB connection
const url = process.env.MONGODB_URL || 'mongodb://localhost:27017';
const dbName = process.env.DB_NAME || 'task_management';
let db;

// Connect to MongoDB
MongoClient.connect(url)
  .then(client => {
    console.log('✅ Connected to MongoDB');
    db = client.db(dbName);
    
    // Create indexes for better performance
    db.collection('tasks').createIndex({ "createdAt": -1 });
    db.collection('tasks').createIndex({ "priority": 1 });
    db.collection('tasks').createIndex({ "completed": 1 });
    console.log('✅ Database indexes created');
  })
  .catch(error => {
    console.error('❌ MongoDB connection error:', error);
    process.exit(1);
  });

// Helper function to get tasks collection
const getTasksCollection = () => db.collection('tasks');

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    timestamp: new Date().toISOString(),
    database: db ? 'Connected' : 'Disconnected'
  });
});

// ✅ IMPORTANT: Put /tasks/stats BEFORE /tasks/:id
app.get('/tasks/stats', async (req, res) => {
  try {
    console.log('📊 Getting task statistics...');
    
    const stats = await getTasksCollection().aggregate([
      {
        $group: {
          _id: null,
          total: { $sum: 1 },
          completed: { $sum: { $cond: ["$completed", 1, 0] } },
          highPriority: { $sum: { $cond: [{ $eq: ["$priority", "high"] }, 1, 0] } },
          mediumPriority: { $sum: { $cond: [{ $eq: ["$priority", "medium"] }, 1, 0] } },
          lowPriority: { $sum: { $cond: [{ $eq: ["$priority", "low"] }, 1, 0] } }
        }
      }
    ]).toArray();
    
    const result = stats[0] || {
      total: 0,
      completed: 0,
      highPriority: 0,
      mediumPriority: 0,
      lowPriority: 0
    };
    
    delete result._id;
    result.pending = result.total - result.completed;
    
    console.log('📊 Stats calculated:', result);
    res.json(result);
  } catch (error) {
    console.error('Error fetching stats:', error);
    res.status(500).json({ error: 'Failed to fetch stats' });
  }
});

// GET /tasks - List all tasks
app.get('/tasks', async (req, res) => {
  try {
    const tasks = await getTasksCollection()
      .find({})
      .sort({ createdAt: -1 })
      .toArray();
    
    // Convert ObjectId to string for frontend compatibility
    const formattedTasks = tasks.map(task => ({
      ...task,
      id: task._id.toString(),
      _id: undefined
    }));
    
    res.json(formattedTasks);
  } catch (error) {
    console.error('Error fetching tasks:', error);
    res.status(500).json({ error: 'Failed to fetch tasks' });
  }
});

// GET /tasks/:id - Get specific task (AFTER /tasks/stats!)
app.get('/tasks/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    // Validate ObjectId format
    if (!ObjectId.isValid(id)) {
      return res.status(400).json({ error: 'Invalid task ID format' });
    }
    
    const task = await getTasksCollection().findOne({ _id: new ObjectId(id) });
    
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    // Format response
    const formattedTask = {
      ...task,
      id: task._id.toString(),
      _id: undefined
    };
    
    res.json(formattedTask);
  } catch (error) {
    console.error('Error fetching task:', error);
    res.status(500).json({ error: 'Failed to fetch task' });
  }
});

// POST /tasks - Create new task
app.post('/tasks', async (req, res) => {
  try {
    const { title, priority = 'medium', description = '' } = req.body;
    
    if (!title || title.trim() === '') {
      return res.status(400).json({ error: 'Title is required' });
    }
    
    const newTask = {
      title: title.trim(),
      description: description.trim(),
      completed: false,
      priority,
      createdAt: new Date(),
      updatedAt: new Date()
    };
    
    const result = await getTasksCollection().insertOne(newTask);
    
    // Return the created task
    const createdTask = {
      ...newTask,
      id: result.insertedId.toString(),
      _id: undefined
    };
    
    console.log('✅ Task created:', createdTask.title);
    res.status(201).json(createdTask);
  } catch (error) {
    console.error('Error creating task:', error);
    res.status(500).json({ error: 'Failed to create task' });
  }
});

// PUT /tasks/:id - Update task
app.put('/tasks/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const updates = req.body;
    
    // Validate ObjectId format
    if (!ObjectId.isValid(id)) {
      return res.status(400).json({ error: 'Invalid task ID format' });
    }
    
    // Clean up updates object
    delete updates.id;
    delete updates._id;
    delete updates.createdAt; // Don't allow updating creation time
    updates.updatedAt = new Date();
    
    // Trim string fields
    if (updates.title) updates.title = updates.title.trim();
    if (updates.description) updates.description = updates.description.trim();
    
    const result = await getTasksCollection().findOneAndUpdate(
      { _id: new ObjectId(id) },
      { $set: updates },
      { returnDocument: 'after' }
    );
    
    if (!result.value) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    // Format response
    const formattedTask = {
      ...result.value,
      id: result.value._id.toString(),
      _id: undefined
    };
    
    console.log('✅ Task updated:', formattedTask.title);
    res.json(formattedTask);
  } catch (error) {
    console.error('Error updating task:', error);
    res.status(500).json({ error: 'Failed to update task' });
  }
});

// DELETE /tasks/:id - Delete task
app.delete('/tasks/:id', async (req, res) => {
  try {
    const { id } = req.params;
    
    // Validate ObjectId format
    if (!ObjectId.isValid(id)) {
      return res.status(400).json({ error: 'Invalid task ID format' });
    }
    
    const result = await getTasksCollection().deleteOne({ _id: new ObjectId(id) });
    
    if (result.deletedCount === 0) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    console.log('🗑️ Task deleted:', id);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting task:', error);
    res.status(500).json({ error: 'Failed to delete task' });
  }
});

// Start server
app.listen(port, () => {
  console.log(`🚀 Task API with MongoDB running on http://localhost:${port}`);
  console.log(`📊 Health check: http://localhost:${port}/health`);
  console.log(`📊 Stats endpoint: http://localhost:${port}/tasks/stats`);
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down server...');
  process.exit(0);
});