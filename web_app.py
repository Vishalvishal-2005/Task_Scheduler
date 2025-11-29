from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import traceback
import asyncio
import json
from datetime import datetime

# Import from your agent.py file - use direct function calls instead of agents
from agent import (
    add_task,
    list_tasks, 
    list_long_term_goals,
    update_task_status,
    delete_task,
    save_long_term_goal,
    list_high_priority_top_n,
    delete_previous_month_tasks,
    simple_chat_once,
    tracker
)

app = FastAPI(
    title="SmartTask Manager API",
    description="Task Management System",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str
    success: bool = True

class TaskCreateRequest(BaseModel):
    title: str
    due_date: Optional[str] = None
    priority: str = "medium"

class TaskUpdateRequest(BaseModel):
    status: Optional[str] = None

class GoalCreateRequest(BaseModel):
    goal: str
    horizon_months: int = 6

# API Routes
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """Chat with the SmartTask system using simple commands"""
    try:
        if not req.message.strip():
            return ChatResponse(reply="Please enter a message.", success=False)
        
        # Use simple_chat_once which doesn't have session issues
        reply = simple_chat_once(req.message)
        
        if reply is None:
            # If simple commands don't work, provide helpful response
            reply = "I can help you with:\n\n• Add tasks: 'add [task] due [date] priority [high/medium/low]'\n• List tasks: 'list tasks' or 'show tasks'\n• Set goals: 'I want to [goal] in [time]'\n• Show high priority: 'show top 5'\n• Clean old tasks: 'delete previous month'\n\nTry one of these commands!"
        
        return ChatResponse(reply=reply)
        
    except Exception as e:
        print(f"Chat error: {str(e)}")
        return ChatResponse(reply=f"Hello! I can help you manage tasks. Try 'add Buy groceries' or 'list tasks'", success=False)

@app.get("/api/tasks")
async def get_tasks_endpoint(status: Optional[str] = "all"):
    """Get all tasks"""
    try:
        result = list_tasks(status)
        if result["status"] == "success":
            return result["tasks"]
        else:
            return []
    except Exception as e:
        return []

@app.post("/api/tasks", response_model=ChatResponse)
async def create_task_endpoint(req: TaskCreateRequest):
    """Create a new task"""
    try:
        result = add_task(req.title, req.due_date, req.priority)
        if result["status"] == "success":
            return ChatResponse(reply=f"✅ Task created! ID: {result['task']['id']}, Title: {req.title}")
        elif result["status"] == "duplicate":
            return ChatResponse(reply=f"⚠️ Task already exists! ID: {result['task']['id']}")
        else:
            return ChatResponse(reply=f"❌ {result.get('message', 'Failed to create task')}", success=False)
    except Exception as e:
        return ChatResponse(reply=f"Error: {str(e)}", success=False)

@app.put("/api/tasks/{task_id}", response_model=ChatResponse)
async def update_task_endpoint(task_id: int, req: TaskUpdateRequest):
    """Update a task status"""
    try:
        if req.status:
            result = update_task_status(task_id, req.status)
            if result["status"] == "success":
                return ChatResponse(reply=f"Task #{task_id} status updated to {req.status}")
            else:
                return ChatResponse(reply=result.get("message", "Task not found"), success=False)
        else:
            return ChatResponse(reply="No status provided", success=False)
    except Exception as e:
        return ChatResponse(reply=f"Error: {str(e)}", success=False)

@app.delete("/api/tasks/{task_id}", response_model=ChatResponse)
async def delete_task_endpoint(task_id: int):
    """Delete a task"""
    try:
        result = delete_task(task_id)
        if result["status"] == "success":
            return ChatResponse(reply=result["message"])
        else:
            return ChatResponse(reply=result.get("message", "Task not found"), success=False)
    except Exception as e:
        return ChatResponse(reply=f"Error: {str(e)}", success=False)

@app.get("/api/goals")
async def get_goals_endpoint():
    """Get all long-term goals"""
    try:
        result = list_long_term_goals()
        if result["status"] == "success":
            return result["goals"]
        else:
            return []
    except Exception as e:
        return []

@app.post("/api/goals", response_model=ChatResponse)
async def create_goal_endpoint(req: GoalCreateRequest):
    """Create a new long-term goal"""
    try:
        result = save_long_term_goal(req.goal, req.horizon_months)
        if result["status"] == "success":
            return ChatResponse(reply=f"🎯 Goal created: {req.goal}")
        else:
            return ChatResponse(reply=result.get("message", "Failed to create goal"), success=False)
    except Exception as e:
        return ChatResponse(reply=f"Error: {str(e)}", success=False)

@app.get("/api/metrics")
async def get_metrics_endpoint():
    """Get system metrics"""
    try:
        events = tracker.events
        agent_calls = len([e for e in events if e.event_type.value == "agent_call"])
        tool_executions = len([e for e in events if e.event_type.value == "tool_execution"])
        errors = len([e for e in events if e.event_type.value == "error"])
        
        return {
            "total_events": len(events),
            "agent_calls": agent_calls,
            "tool_executions": tool_executions,
            "errors": errors,
            "uptime": "active"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/quick-actions/{action}")
async def quick_actions_endpoint(action: str):
    """Execute quick actions using direct function calls"""
    try:
        if action == "high-priority":
            result = list_high_priority_top_n(5)
            if result["status"] == "success" and result["tasks"]:
                tasks_str = "\n".join([
                    f"🚨 #{t['id']}: {t['title']}" + 
                    (f" (due: {t['due_date']})" if t.get('due_date') else "")
                    for t in result["tasks"]
                ])
                return ChatResponse(reply=f"🔝 Top 5 high priority tasks:\n{tasks_str}")
            else:
                return ChatResponse(reply="No high priority tasks found.")
                
        elif action == "clean-old":
            result = delete_previous_month_tasks()
            if result["status"] == "success":
                return ChatResponse(reply=f"🧹 Cleaned up {result['deleted_count']} tasks from previous month")
            else:
                return ChatResponse(reply=f"❌ Cleanup failed: {result.get('message', 'Unknown error')}")
                
        elif action == "productivity-report":
            tasks_result = list_tasks()
            if tasks_result["status"] == "success":
                tasks = tasks_result["tasks"]
                total_tasks = len(tasks)
                completed = len([t for t in tasks if t.get("status") == "done"])
                pending = len([t for t in tasks if t.get("status") == "pending"])
                completion_rate = (completed / total_tasks * 100) if total_tasks > 0 else 0
                
                report = f"📊 Productivity Report:\n\n"
                report += f"• Total Tasks: {total_tasks}\n"
                report += f"• Completed: {completed}\n"
                report += f"• Pending: {pending}\n"
                report += f"• Completion Rate: {completion_rate:.1f}%\n"
                report += f"• High Priority: {len([t for t in tasks if t.get('priority') == 'high'])}\n"
                
                return ChatResponse(reply=report)
            else:
                return ChatResponse(reply="Could not generate report")
                
        else:
            return ChatResponse(reply="Action not found", success=False)
    except Exception as e:
        return ChatResponse(reply=f"Error: {str(e)}", success=False)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "SmartTask Manager API",
        "timestamp": datetime.utcnow().isoformat()
    }

# Serve the main web interface
@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the web interface"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SmartTask Manager</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container { 
                max-width: 1200px; 
                margin: 0 auto; 
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }
            @media (max-width: 768px) {
                .container {
                    grid-template-columns: 1fr;
                }
            }
            .card { 
                background: white; 
                border-radius: 12px; 
                padding: 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            }
            h1 { 
                margin-top: 0; 
                color: white;
                text-align: center;
                margin-bottom: 20px;
                font-size: 2.2rem;
            }
            h2 {
                color: #4a5568;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 8px;
                margin-bottom: 16px;
            }
            #chat-log { 
                height: 300px; 
                overflow-y: auto; 
                border: 1px solid #e2e8f0;
                padding: 16px; 
                border-radius: 8px; 
                background: #f8fafc; 
                font-size: 14px; 
                margin-bottom: 16px;
            }
            .msg-user { 
                background: #4299e1; 
                color: white; 
                padding: 8px 12px;
                border-radius: 12px 12px 4px 12px;
                margin-bottom: 8px;
                max-width: 80%;
                margin-left: auto;
                word-wrap: break-word;
            }
            .msg-agent { 
                background: #edf2f7; 
                color: #2d3748; 
                padding: 8px 12px;
                border-radius: 12px 12px 12px 4px;
                margin-bottom: 8px;
                max-width: 80%;
                word-wrap: break-word;
                border: 1px solid #e2e8f0;
                white-space: pre-line;
            }
            .chat-input-container {
                display: flex;
                gap: 12px;
            }
            input { 
                flex: 1;
                padding: 12px; 
                border-radius: 8px;
                border: 2px solid #e2e8f0; 
                font-family: inherit;
                font-size: 14px;
            }
            input:focus {
                outline: none;
                border-color: #4299e1;
            }
            button { 
                padding: 12px 24px; 
                border-radius: 8px; 
                border: none;
                background: #667eea;
                color: white; 
                cursor: pointer; 
                font-weight: 600;
                font-size: 14px;
            }
            button:hover { 
                background: #5a6fd8;
            }
            .tasks-container { 
                font-size: 14px; 
                max-height: 400px;
                overflow-y: auto;
            }
            .task-item { 
                padding: 12px; 
                border-bottom: 1px solid #e2e8f0; 
                border-radius: 6px;
                margin-bottom: 8px;
                background: #f8fafc;
            }
            .badge { 
                display: inline-block; 
                padding: 4px 8px; 
                border-radius: 999px;
                font-size: 11px; 
                margin-left: 8px;
                font-weight: 600;
            }
            .badge-high { background: #fed7d7; color: #c53030; }
            .badge-medium { background: #feebc8; color: #d69e2e; }
            .badge-low { background: #c6f6d5; color: #276749; }
            .badge-pending { background: #fed7d7; color: #c53030; }
            .badge-done { background: #c6f6d5; color: #276749; }
            .task-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 4px;
            }
            .task-title {
                font-weight: 600;
                color: #2d3748;
            }
            .task-meta {
                font-size: 12px;
                color: #718096;
            }
            .task-actions {
                display: flex;
                gap: 4px;
                margin-top: 8px;
            }
            .task-actions button {
                padding: 4px 8px;
                font-size: 12px;
            }
            .quick-actions {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 8px;
                margin-bottom: 16px;
            }
            .quick-actions button {
                padding: 8px 12px;
                font-size: 12px;
            }
            .loading {
                text-align: center;
                color: #718096;
                padding: 20px;
            }
            .error {
                background: #fed7d7;
                color: #c53030;
                padding: 8px;
                border-radius: 6px;
                margin-bottom: 8px;
                font-size: 12px;
            }
            .examples {
                background: #f0fff4;
                border: 1px solid #9ae6b4;
                border-radius: 8px;
                padding: 8px;
                margin-bottom: 12px;
                font-size: 11px;
            }
            .examples-title {
                font-weight: 600;
                margin-bottom: 6px;
                color: #2d3748;
                font-size: 12px;
            }
            .example-items {
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
            }
            .example-item {
                background: white;
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid #c6f6d5;
                cursor: pointer;
                white-space: nowrap;
                font-size: 10px;
            }
            .example-item:hover {
                background: #c6f6d5;
            }
        </style>
    </head>
    <body>
        <h1>🤖 SmartTask Manager</h1>
        
        <div class="container">
            <div class="card">
                <h2>💬 Task Assistant</h2>
                
                <div class="examples">
                    <div class="examples-title">Try these commands:</div>
                    <div class="example-items">
                        <div class="example-item" onclick="setExample('hi')">Hello</div>
                        <div class="example-item" onclick="setExample('add Buy groceries')">Add task</div>
                        <div class="example-item" onclick="setExample('list tasks')">List tasks</div>
                        <div class="example-item" onclick="setExample('set a goal')">Set goal</div>
                        <div class="example-item" onclick="setExample('show top 5')">High priority</div>
                    </div>
                </div>
                
                <div class="quick-actions">
                    <button onclick="executeQuickAction('high-priority')">🚨 High Priority</button>
                    <button onclick="executeQuickAction('clean-old')">🧹 Clean Old</button>
                    <button onclick="executeQuickAction('productivity-report')">📊 Report</button>
                </div>
                
                <div id="chat-log"></div>
                
                <div class="chat-input-container">
                    <input type="text" id="message" placeholder="Type your command here..." />
                    <button onclick="sendMessage()">Send</button>
                </div>
            </div>

            <div class="card">
                <h2>📋 Tasks 
                    <button style="float: right; padding: 4px 8px; font-size: 12px;" onclick="fetchTasks()">Refresh</button>
                </h2>
                <div class="tasks-container" id="tasks">
                    <div class="loading">Loading tasks...</div>
                </div>
            </div>
        </div>

        <script>
            // Global state
            let currentTasks = [];

            // Utility functions
            function setExample(text) {
                document.getElementById('message').value = text;
                document.getElementById('message').focus();
            }

            async function fetchWithErrorHandling(url, options = {}) {
                try {
                    const response = await fetch(url, options);
                    if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                    }
                    return await response.json();
                } catch (error) {
                    console.error('Fetch error:', error);
                    showError(error.message);
                    throw error;
                }
            }

            function showError(message) {
                const chatLog = document.getElementById('chat-log');
                chatLog.innerHTML += `<div class="error"><strong>Error:</strong> ${message}</div>`;
                chatLog.scrollTop = chatLog.scrollHeight;
            }

            function showLoading(containerId) {
                document.getElementById(containerId).innerHTML = '<div class="loading">Loading...</div>';
            }

            // Task management
            async function fetchTasks() {
                showLoading('tasks');
                try {
                    const tasks = await fetchWithErrorHandling('/api/tasks');
                    currentTasks = tasks;
                    renderTasks(tasks);
                } catch (error) {
                    document.getElementById('tasks').innerHTML = '<div class="error">Failed to load tasks</div>';
                }
            }

            function renderTasks(tasks) {
                const container = document.getElementById('tasks');
                
                if (!tasks.length) {
                    container.innerHTML = '<div class="loading"><i>No tasks yet. Add one using the examples above!</i></div>';
                    return;
                }
                
                let html = '';
                for (const task of tasks) {
                    const priorityClass = `badge-${task.priority}`;
                    const statusClass = `badge-${task.status}`;
                    
                    html += `<div class="task-item">
                                <div class="task-header">
                                    <span class="task-title">#${task.id} ${task.title}</span>
                                    <div>
                                        <span class="badge ${priorityClass}">${task.priority}</span>
                                        <span class="badge ${statusClass}">${task.status}</span>
                                    </div>
                                </div>
                                ${task.due_date ? `<div class="task-meta">📅 Due: ${new Date(task.due_date).toLocaleDateString()}</div>` : ''}
                                <div class="task-actions">
                                    ${task.status !== 'done' ? 
                                        `<button onclick="updateTaskStatus(${task.id}, 'done')">✅ Done</button>` : 
                                        `<button onclick="updateTaskStatus(${task.id}, 'pending')">↩️ Reopen</button>`
                                    }
                                    <button onclick="deleteTask(${task.id})">🗑️ Delete</button>
                                </div>
                            </div>`;
                }
                container.innerHTML = html;
            }

            async function updateTaskStatus(taskId, status) {
                try {
                    const response = await fetchWithErrorHandling(`/api/tasks/${taskId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ status })
                    });
                    addChatMessage('assistant', response.reply);
                    await fetchTasks();
                } catch (error) {
                    showError(`Failed to update task: ${error.message}`);
                }
            }

            async function deleteTask(taskId) {
                if (!confirm('Are you sure you want to delete this task?')) return;
                
                try {
                    const response = await fetchWithErrorHandling(`/api/tasks/${taskId}`, {
                        method: 'DELETE'
                    });
                    addChatMessage('assistant', response.reply);
                    await fetchTasks();
                } catch (error) {
                    showError(`Failed to delete task: ${error.message}`);
                }
            }

            // Chat functionality
            function addChatMessage(role, content) {
                const chatLog = document.getElementById('chat-log');
                const messageClass = role === 'user' ? 'msg-user' : 'msg-agent';
                const prefix = role === 'user' ? 'You' : 'Assistant';
                
                chatLog.innerHTML += `<div class="${messageClass}"><strong>${prefix}:</strong> ${content}</div>`;
                chatLog.scrollTop = chatLog.scrollHeight;
            }

            async function sendMessage() {
                const input = document.getElementById('message');
                const text = input.value.trim();
                if (!text) return;
                
                addChatMessage('user', text);
                input.value = '';

                try {
                    const response = await fetchWithErrorHandling('/api/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: text })
                    });
                    
                    if (response.success) {
                        addChatMessage('assistant', response.reply);
                    } else {
                        showError(response.reply);
                    }
                } catch (error) {
                    showError(`Network error: ${error.message}`);
                }
                
                // Refresh tasks
                await fetchTasks();
            }

            async function executeQuickAction(action) {
                try {
                    const response = await fetchWithErrorHandling(`/api/quick-actions/${action}`);
                    addChatMessage('assistant', response.reply);
                    await fetchTasks();
                } catch (error) {
                    showError(`Failed to execute action: ${error.message}`);
                }
            }

            // Event listeners
            document.getElementById('message').addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    sendMessage();
                }
            });

            // Initialization
            async function initialize() {
                await fetchTasks();
                document.getElementById('message').focus();
                
                // Show welcome message
                addChatMessage('assistant', 
                    'Hello! I\\'m SmartTask Assistant. I can help you manage tasks and goals.\\n\\n' +
                    'Try the example commands above or type your own request!'
                );
            }

            // Start the application
            initialize();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)



    