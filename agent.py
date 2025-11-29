"""
Smart Personal Task Manager Agent
ADK-compatible version with Multi-agent System, Observability, and A2A Protocol
"""

import json
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import uuid
from dataclasses import dataclass

from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.runners import InMemoryRunner

# -------------------------------------------------------------------
# Enhanced Observability Setup
# -------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("task_manager_observability.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("SmartTaskManager")

class EventType(Enum):
    AGENT_CALL = "agent_call"
    TOOL_EXECUTION = "tool_execution"
    A2A_COMMUNICATION = "a2a_communication"
    ERROR = "error"
    SESSION_CREATED = "session_created"

@dataclass
class ObservabilityEvent:
    event_id: str
    event_type: EventType
    timestamp: str
    agent_name: str
    details: Dict[str, Any]
    duration_ms: float = 0.0

class ObservabilityTracker:
    def __init__(self):
        self.events: List[ObservabilityEvent] = []
    
    def log_event(self, event_type: EventType, agent_name: str, details: Dict[str, Any], duration_ms: float = 0.0):
        """Logs an event and maintains a maximum of 1000 events in memory."""
        event = ObservabilityEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            agent_name=agent_name,
            details=details,
            duration_ms=duration_ms
        )
        self.events.append(event)
        logger.info(f"{event_type.value} - {agent_name} - {details}")
        
        # Keep only last 1000 events
        if len(self.events) > 1000:
            self.events = self.events[-1000:]
    
    def get_events(self, agent_name: str = None, event_type: EventType = None):
        events = self.events
        if agent_name:
            events = [e for e in events if e.agent_name == agent_name]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events

# Global observability tracker
tracker = ObservabilityTracker()

# -------------------------------------------------------------------
# A2A Protocol Implementation
# -------------------------------------------------------------------

class A2AMessage:
    def __init__(self, from_agent: str, to_agent: str, message_type: str, content: Dict[str, Any], context: Dict[str, Any] = None):
        self.message_id = str(uuid.uuid4())
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.message_type = message_type
        self.content = content
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.delivered = False

class A2AProtocol:
    def __init__(self):
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.agent_handlers: Dict[str, Callable] = {}
        self._is_running = False
    
    def register_agent(self, agent_name: str, handler: Callable):
        """Registers an agent with its corresponding handler."""
        self.agent_handlers[agent_name] = handler
    
    async def send_message(self, message: A2AMessage):
        """Sends a message and logs the event."""
        await self.message_queue.put(message)
        tracker.log_event(
            EventType.A2A_COMMUNICATION,
            message.from_agent,
            {
                "action": "message_sent",
                "to_agent": message.to_agent,
                "message_type": message.message_type,
                "message_id": message.message_id
            }
        )
    
    async def start_message_processor(self):
        """Starts the message processing loop."""
        self._is_running = True
        while self._is_running:
            try:
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                await self._process_message(message)
            except asyncio.TimeoutError:
                continue
    
    async def _process_message(self, message: A2AMessage):
        if message.to_agent in self.agent_handlers:
            try:
                await self.agent_handlers[message.to_agent](message)
                message.delivered = True
                tracker.log_event(
                    EventType.A2A_COMMUNICATION,
                    message.to_agent,
                    {
                        "action": "message_processed",
                        "from_agent": message.from_agent,
                        "message_type": message.message_type,
                        "message_id": message.message_id
                    }
                )
            except Exception as e:
                tracker.log_event(
                    EventType.ERROR,
                    message.to_agent,
                    {
                        "action": "message_processing_error",
                        "error": str(e),
                        "message_id": message.message_id
                    }
                )
        else:
            tracker.log_event(
                EventType.ERROR,
                "A2AProtocol",
                {
                    "action": "agent_not_found",
                    "to_agent": message.to_agent,
                    "message_id": message.message_id
                }
            )
    
    def stop(self):
        self._is_running = False

# Global A2A protocol instance
a2a_protocol = A2AProtocol()

# -------------------------------------------------------------------
# Database helpers
# -------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), "tasks_db.json")

def _load_db() -> Dict[str, Any]:
    """Load tasks + goals from local JSON file."""
    if not os.path.exists(DB_PATH):
        return {"tasks": [], "goals": []}
    try:
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        tracker.log_event(EventType.ERROR, "Database", {"action": "load_failed", "error": str(e)})
        return {"tasks": [], "goals": []}

def _save_db(data: Dict[str, Any]) -> None:
    """Persist tasks and goals to a local JSON file."""
    try:
        with open(DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        tracker.log_event(EventType.ERROR, "Database", {"action": "save_failed", "error": str(e)})

def _next_task_id(tasks: List[Dict[str, Any]]) -> int:
    if not tasks:
        return 1
    return max(int(t.get("id", 0)) for t in tasks) + 1

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

# -------------------------------------------------------------------
# Tools (Enhanced with Observability)
# -------------------------------------------------------------------

def add_task(title: str, due_date: Optional[str] = None,
             priority: str = "medium", context: Optional[str] = None,
             reminder_time: Optional[str] = None) -> Dict[str, Any]:
    """Add a new task to the task manager.
    
    This function creates a new task with the specified title, due date,  priority,
    context, and reminder time. It first checks for duplicate  tasks to prevent
    adding the same task multiple times. If a duplicate  is found, it returns a
    status indicating the task already exists.  Otherwise, it generates a new task
    ID, adds the task to the database,  and logs the event for observability.
    
    Args:
        title (str): The title of the task.
        due_date (Optional[str]): The due date of the task.
        priority (str): The priority level of the task.
        context (Optional[str]): The context in which the task is set.
        reminder_time (Optional[str]): The time for a reminder about the task.
    """
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])

        # Prevent duplicates
        for t in tasks:
            if t["title"].lower() == title.lower() and t["due_date"] == due_date:
                return {
                    "status": "duplicate",
                    "task": t,
                    "message": f"task_exists:{t['id']}"
                }

        task_id = _next_task_id(tasks)
        task = {
            "id": task_id,
            "title": title,
            "due_date": due_date,
            "priority": priority,
            "context": context or "",
            "status": "pending",
            "created_at": _now_iso(),
            "updated_at": None,
            "reminder_time": reminder_time,
            "subtasks": [],
        }

        tasks.append(task)
        db["tasks"] = tasks
        _save_db(db)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        tracker.log_event(
            EventType.TOOL_EXECUTION,
            "TaskManager",
            {"action": "add_task", "task_id": task_id, "title": title, "priority": priority},
            duration_ms
        )
        
        return {"status": "success", "task": task, "message": f"task_created:{task_id}"}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "add_task_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def delete_previous_month_tasks() -> Dict[str, Any]:
    """Delete tasks that are due in the previous month.
    
    This function retrieves tasks from the database, checks their due dates,  and
    removes those that are due in the previous month. It handles date  parsing and
    logs the execution duration and any errors encountered.  Finally, it updates
    the database with the remaining tasks and returns  a summary of the operation,
    including the count of deleted tasks.
    """
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])
        now = datetime.utcnow()
        current_month = now.month
        current_year = now.year

        cleaned = []
        removed = []

        for t in tasks:
            d = t.get("due_date")
            try:
                due = datetime.fromisoformat(d)
            except:
                cleaned.append(t)
                continue

            if (due.year == current_year and due.month == current_month - 1) or \
               (current_month == 1 and due.year == current_year - 1 and due.month == 12):
                removed.append(t)
            else:
                cleaned.append(t)

        db["tasks"] = cleaned
        _save_db(db)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        tracker.log_event(
            EventType.TOOL_EXECUTION,
            "TaskManager",
            {"action": "delete_previous_month_tasks", "deleted_count": len(removed)},
            duration_ms
        )
        
        return {
            "status": "success",
            "deleted_count": len(removed),
            "deleted_tasks": removed
        }
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "delete_previous_month_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def list_high_priority_top_n(n: int = 5) -> Dict[str, Any]:
    """Retrieve the top N high-priority tasks.
    
    Args:
        n (int): The number of high-priority tasks to return. Defaults to 5.
    
    Returns:
        Dict[str, Any]: A dictionary containing the status and the list of tasks.
    """
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])
        high = [t for t in tasks if str(t.get("priority", "")).lower() == "high"]

        def _parse_due(d: Optional[str]):
            """Parse a due date from an ISO format string or return datetime.max."""
            if not d:
                return datetime.max
            try:
                return datetime.fromisoformat(d)
            except:
                return datetime.max

        high_sorted = sorted(high, key=lambda t: _parse_due(t.get("due_date")))
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        tracker.log_event(
            EventType.TOOL_EXECUTION,
            "TaskManager",
            {"action": "list_high_priority_top_n", "count": len(high_sorted[:n])},
            duration_ms
        )
        
        return {"status": "success", "tasks": high_sorted[:n]}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "list_high_priority_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def list_tasks(status: str = "all") -> Dict[str, Any]:
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])

        if status != "all":
            tasks = [t for t in tasks if t.get("status") == status]

        def _priority_rank(p: str) -> int:
            """Return the priority rank of a given string.
            
            Args:
                p (str): The priority level as a string.
            
            Returns:
                int: The corresponding rank of the priority level.
            """
            return {"high": 0, "medium": 1, "low": 2}.get(p, 3)

        def _parse_due(d: Optional[str]):
            """Parse a due date string into a datetime object or return datetime.max."""
            if not d:
                return datetime.max
            try:
                return datetime.fromisoformat(d)
            except Exception:
                try:
                    return datetime.fromisoformat(d + "T23:59:59")
                except Exception:
                    return datetime.max

        tasks_sorted = sorted(
            tasks,
            key=lambda t: (_parse_due(t.get("due_date")), _priority_rank(t.get("priority", "medium")), t.get("id")),
        )
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        tracker.log_event(
            EventType.TOOL_EXECUTION,
            "TaskManager",
            {"action": "list_tasks", "status_filter": status, "count": len(tasks_sorted)},
            duration_ms
        )
        
        return {"status": "success", "tasks": tasks_sorted}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "list_tasks_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def update_task(
    task_id: int,
    title: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    context: Optional[str] = None,
    reminder_time: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a task in the task manager.
    
    This function updates the details of a task identified by the given task_id.
    It modifies the task's title, due_date, priority, context, and reminder_time
    if the corresponding parameters are provided. The function also logs the
    execution time and any errors encountered during the update process, ensuring
    that the task manager's state remains consistent.
    
    Args:
        task_id (int): The ID of the task to be updated.
        title (Optional[str]): The new title for the task.
        due_date (Optional[str]): The new due date for the task.
        priority (Optional[str]): The new priority for the task.
        context (Optional[str]): The new context for the task.
        reminder_time (Optional[str]): The new reminder time for the task.
    """
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])

        for t in tasks:
            if t.get("id") == task_id:
                if title is not None:
                    t["title"] = title
                if due_date is not None:
                    t["due_date"] = due_date
                if priority is not None:
                    t["priority"] = priority
                if context is not None:
                    t["context"] = context
                if reminder_time is not None:
                    t["reminder_time"] = reminder_time
                t["updated_at"] = _now_iso()
                _save_db(db)
                
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                tracker.log_event(
                    EventType.TOOL_EXECUTION,
                    "TaskManager",
                    {"action": "update_task", "task_id": task_id, "updated_fields": {
                        "title": title is not None,
                        "due_date": due_date is not None,
                        "priority": priority is not None
                    }},
                    duration_ms
                )
                
                return {"status": "success", "task": t}

        return {"status": "error", "message": f"Task {task_id} not found."}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "update_task_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def update_task_status(task_id: int, status: str) -> Dict[str, Any]:
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])

        if status not in {"pending", "in_progress", "done"}:
            return {"status": "error", "message": f"Invalid status: {status}"}

        for t in tasks:
            if t.get("id") == task_id:
                t["status"] = status
                t["updated_at"] = _now_iso()
                _save_db(db)
                
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                tracker.log_event(
                    EventType.TOOL_EXECUTION,
                    "TaskManager",
                    {"action": "update_task_status", "task_id": task_id, "new_status": status},
                    duration_ms
                )
                
                return {"status": "success", "task": t}

        return {"status": "error", "message": f"Task {task_id} not found."}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "update_task_status_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def delete_task(task_id: int) -> Dict[str, Any]:
    """def delete_task(task_id: int) -> Dict[str, Any]:
    Delete a task by its ID.  This function attempts to delete a task identified by
    the given  task_id from the database. It first loads the current tasks,
    filters out the task with the specified ID, and checks if the  task was found.
    If the task is not found, it returns an error  message. If the task is
    successfully deleted, it saves the  updated task list back to the database and
    logs the event with  the duration of the operation.
    
    Args:
        task_id (int): The ID of the task to be deleted."""
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])

        new_tasks = [t for t in tasks if t.get("id") != task_id]
        if len(new_tasks) == len(tasks):
            return {"status": "error", "message": f"Task {task_id} not found."}

        db["tasks"] = new_tasks
        _save_db(db)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        tracker.log_event(
            EventType.TOOL_EXECUTION,
            "TaskManager",
            {"action": "delete_task", "task_id": task_id},
            duration_ms
        )
        
        return {"status": "success", "message": f"Task {task_id} deleted."}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "delete_task_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def add_subtasks(task_id: int, subtasks: List[str]) -> Dict[str, Any]:
    """def add_subtasks(task_id: int, subtasks: List[str]) -> Dict[str, Any]:
    Add subtasks to a specified task.  This function retrieves the task with the
    given task_id from the database,  appends the provided subtasks to its existing
    subtasks, and updates the task's  updated_at timestamp. It also logs the event
    duration and handles any exceptions  that may occur during the process,
    ensuring that appropriate error messages are returned.
    
    Args:
        task_id (int): The ID of the task to which subtasks will be added.
        subtasks (List[str]): A list of subtasks to be added to the task."""
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])

        for t in tasks:
            if t.get("id") == task_id:
                existing = t.get("subtasks", [])
                for s in subtasks:
                    existing.append({
                        "title": s,
                        "status": "pending",
                        "created_at": _now_iso(),
                        "completed_at": None,
                    })
                t["subtasks"] = existing
                t["updated_at"] = _now_iso()
                _save_db(db)
                
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                tracker.log_event(
                    EventType.TOOL_EXECUTION,
                    "TaskManager",
                    {"action": "add_subtasks", "task_id": task_id, "subtask_count": len(subtasks)},
                    duration_ms
                )
                
                return {"status": "success", "task": t}

        return {"status": "error", "message": f"Task {task_id} not found."}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "add_subtasks_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def mark_subtask_done(task_id: int, subtask_index: int) -> Dict[str, Any]:
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        tasks = db.get("tasks", [])

        for t in tasks:
            if t.get("id") == task_id:
                subs = t.get("subtasks", [])
                if not (0 <= subtask_index < len(subs)):
                    return {
                        "status": "error",
                        "message": f"Subtask index {subtask_index} out of range.",
                    }
                subs[subtask_index]["status"] = "done"
                subs[subtask_index]["completed_at"] = _now_iso()
                t["subtasks"] = subs
                t["updated_at"] = _now_iso()
                _save_db(db)
                
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                tracker.log_event(
                    EventType.TOOL_EXECUTION,
                    "TaskManager",
                    {"action": "mark_subtask_done", "task_id": task_id, "subtask_index": subtask_index},
                    duration_ms
                )
                
                return {"status": "success", "task": t}

        return {"status": "error", "message": f"Task {task_id} not found."}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "TaskManager", {"action": "mark_subtask_done_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def save_long_term_goal(goal: str, horizon_months: int = 6, category: Optional[str] = None) -> Dict[str, Any]:
    """Saves a long-term goal to the database."""
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        goals = db.get("goals", [])

        goal_obj = {
            "goal": goal,
            "horizon_months": horizon_months,
            "category": category or "",
            "created_at": _now_iso(),
        }
        goals.append(goal_obj)
        db["goals"] = goals
        _save_db(db)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        tracker.log_event(
            EventType.TOOL_EXECUTION,
            "GoalManager",
            {"action": "save_long_term_goal", "goal": goal, "horizon_months": horizon_months},
            duration_ms
        )
        
        return {"status": "success", "goal": goal_obj}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "GoalManager", {"action": "save_goal_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def list_long_term_goals() -> Dict[str, Any]:
    """Retrieve long-term goals from the database."""
    start_time = datetime.utcnow()
    try:
        db = _load_db()
        goals = db.get("goals", [])
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        tracker.log_event(
            EventType.TOOL_EXECUTION,
            "GoalManager",
            {"action": "list_long_term_goals", "count": len(goals)},
            duration_ms
        )
        
        return {"status": "success", "goals": goals}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "GoalManager", {"action": "list_goals_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

def get_current_time(timezone: str = "UTC") -> Dict[str, Any]:
    """Retrieve the current time in the specified timezone."""
    start_time = datetime.utcnow()
    try:
        now = _now_iso()
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        tracker.log_event(
            EventType.TOOL_EXECUTION,
            "System",
            {"action": "get_current_time", "timezone": timezone},
            duration_ms
        )
        
        return {"status": "success", "timezone": timezone, "time_utc": now}
    except Exception as e:
        tracker.log_event(EventType.ERROR, "System", {"action": "get_time_failed", "error": str(e)})
        return {"status": "error", "message": str(e)}

# -------------------------------------------------------------------
# Multi-Agent System
# -------------------------------------------------------------------

# Use the standard model instead of exp to avoid quota issues
GEMINI_MODEL_NAME = "gemini-2.0-flash"
gemini_llm = Gemini(model=GEMINI_MODEL_NAME)

generate_config = types.GenerateContentConfig(
    temperature=0.3,
    max_output_tokens=768,
)

# Main Task Manager Agent
task_manager_agent = LlmAgent(
    model=gemini_llm,
    name="task_manager_agent",
    description="Main agent for managing tasks, deadlines, and priorities",
    instruction="""
You are the main Task Manager agent. You handle:
- Creating, updating, deleting tasks
- Managing task priorities and due dates
- Breaking down complex tasks into subtasks
- Coordinating with other specialized agents

When you receive complex requests involving analysis or planning, delegate to the appropriate specialist agent via A2A protocol.

Always provide clear, structured responses to users.
""",
    tools=[
        add_task,
        list_tasks,
        update_task,
        update_task_status,
        delete_task,
        add_subtasks,
        mark_subtask_done,
        list_high_priority_top_n,
        delete_previous_month_tasks,
    ],
    generate_content_config=generate_config,
)

# Goal Planning Agent
goal_planning_agent = LlmAgent(
    model=gemini_llm,
    name="goal_planning_agent", 
    description="Specialized in long-term goal planning and strategy",
    instruction="""
You are the Goal Planning specialist. You handle:
- Setting and tracking long-term goals
- Breaking down goals into actionable tasks
- Providing strategic planning advice
- Analyzing goal progress and suggesting adjustments

Work with the Task Manager agent to convert goals into concrete tasks.
""",
    tools=[
        save_long_term_goal,
        list_long_term_goals,
        get_current_time,
    ],
    generate_content_config=generate_config,
)

# Analysis & Reporting Agent
analysis_agent = LlmAgent(
    model=gemini_llm,
    name="analysis_agent",
    description="Specialized in data analysis, reporting, and insights",
    instruction="""
You are the Analysis & Reporting specialist. You handle:
- Generating productivity reports
- Analyzing task completion trends
- Identifying patterns in task management
- Providing data-driven recommendations

Use the available tools to gather data and provide insightful analysis.
""",
    tools=[
        list_tasks,
        list_long_term_goals,
        get_current_time,
    ],
    generate_content_config=generate_config,
)

# -------------------------------------------------------------------
# Sequential/Loop Agent Orchestration
# -------------------------------------------------------------------

class SequentialAgentOrchestrator:
    def __init__(self):
        self.agents = {
            "task_manager_agent": task_manager_agent,
            "goal_planning_agent": goal_planning_agent, 
            "analysis_agent": analysis_agent,
        }
    
    async def execute_workflow(self, user_input: str, user_id: str = "default_user") -> str:
        """Execute a sequential workflow across multiple agents based on input type."""
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Route to appropriate agent based on input analysis
            primary_agent = self._route_to_agent(user_input)
            
            tracker.log_event(
                EventType.AGENT_CALL,
                "Orchestrator",
                {"action": "workflow_start", "input": user_input, "primary_agent": primary_agent.name}
            )
            
            # Step 2: Execute primary agent
            primary_response = await self._run_agent(primary_agent, user_input, user_id)
            
            # Step 3: Check if secondary agent involvement is needed
            secondary_agent = self._determine_secondary_agent(user_input, primary_response)
            if secondary_agent:
                secondary_response = await self._run_agent(secondary_agent, user_input, user_id)
                final_response = f"{primary_response}\n\n---\n\n{secondary_response}"
            else:
                final_response = primary_response
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            tracker.log_event(
                EventType.AGENT_CALL,
                "Orchestrator", 
                {"action": "workflow_complete", "duration_ms": duration_ms, "agents_involved": [
                    primary_agent.name,
                    secondary_agent.name if secondary_agent else "none"
                ]},
                duration_ms
            )
            
            return final_response
            
        except Exception as e:
            tracker.log_event(EventType.ERROR, "Orchestrator", {"action": "workflow_failed", "error": str(e)})
            return f"I encountered an error while processing your request: {str(e)}"
    
    def _route_to_agent(self, user_input: str) -> LlmAgent:
        """Route user input to the most appropriate agent.
        
        This function analyzes the provided user input and determines  the best agent
        to handle the request based on specific keywords.  It checks for keywords
        related to goal planning and analysis,  routing the input to the corresponding
        agent. If no relevant  keywords are found, it defaults to the task manager
        agent.
        
        Args:
            user_input (str): The input string from the user to be analyzed.
        """
        input_lower = user_input.lower()
        
        if any(keyword in input_lower for keyword in ["goal", "long-term", "strategy", "plan", "vision"]):
            return self.agents["goal_planning_agent"]
        elif any(keyword in input_lower for keyword in ["report", "analysis", "stats", "trend", "progress"]):
            return self.agents["analysis_agent"]
        else:
            return self.agents["task_manager_agent"]  # Default
    
    def _determine_secondary_agent(self, user_input: str, primary_response: str) -> Optional[LlmAgent]:
        """Determine if a secondary agent should be involved."""
        input_lower = user_input.lower()
        response_lower = primary_response.lower()
        
        # If primary was task manager but response suggests goals, involve goal agent
        if "goal" in input_lower and "task" in response_lower:
            return self.agents["goal_planning_agent"]
        # If any agent suggests analysis, involve analysis agent
        elif "report" in response_lower or "analysis" in response_lower:
            return self.agents["analysis_agent"]
        
        return None
    
    async def _run_agent(self, agent: LlmAgent, message: str, user_id: str) -> str:
        """Run a specific agent with its own runner."""
        start_time = datetime.utcnow()
        
        try:
            # Create dedicated runner for this agent
            runner = InMemoryRunner(agent=agent)
            session = await runner.session_service.create_session(
                app_name=f"agent_{agent.name}",
                user_id=user_id
            )
            
            content = types.Content(role="user", parts=[types.Part(text=message)])
            final_response = ""
            
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=content
            ):
                if hasattr(event, "is_final_response") and event.is_final_response():
                    final_response = str(event)
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            tracker.log_event(
                EventType.AGENT_CALL,
                agent.name,
                {"action": "agent_execution", "input_length": len(message)},
                duration_ms
            )
            
            return final_response or "No response generated."
            
        except Exception as e:
            tracker.log_event(EventType.ERROR, agent.name, {"action": "execution_failed", "error": str(e)})
            return f"Agent {agent.name} encountered an error: {str(e)}"

# -------------------------------------------------------------------
# A2A Message Handlers
# -------------------------------------------------------------------

async def handle_task_manager_message(message: A2AMessage):
    """Handle A2A messages for the task manager agent."""
    if message.message_type == "decompose_goal":
        # Goal agent asking to break down a goal into tasks
        goal = message.content.get("goal")
        horizon = message.content.get("horizon_months", 6)
        
        # Create main task for the goal
        task_result = add_task(
            title=f"Achieve: {goal}",
            due_date=(datetime.utcnow() + timedelta(days=horizon*30)).isoformat(),
            priority="high",
            context=f"Long-term goal: {goal}"
        )
        
        # Send response back
        response_msg = A2AMessage(
            from_agent="task_manager_agent",
            to_agent=message.from_agent,
            message_type="goal_decomposed",
            content={
                "original_goal": goal,
                "main_task_created": task_result["status"] == "success",
                "task_id": task_result.get("task", {}).get("id") if task_result["status"] == "success" else None
            }
        )
        await a2a_protocol.send_message(response_msg)

async def handle_goal_planning_message(message: A2AMessage):
    """Handle A2A messages for goal planning based on task patterns."""
    if message.message_type == "suggest_goals_from_tasks":
        # Analysis agent suggesting goals based on task patterns
        task_patterns = message.content.get("patterns", [])
        
        # Analyze patterns and create relevant goals
        for pattern in task_patterns[:2]:  # Limit to top 2 patterns
            if "meeting" in pattern.lower():
                goal_result = save_long_term_goal(
                    goal="Improve meeting efficiency and productivity",
                    horizon_months=3,
                    category="productivity"
                )
        
        response_msg = A2AMessage(
            from_agent="goal_planning_agent", 
            to_agent=message.from_agent,
            message_type="goals_created_from_patterns",
            content={"goals_created": 1}
        )
        await a2a_protocol.send_message(response_msg)

async def handle_analysis_message(message: A2AMessage):
    """async def handle_analysis_message(message: A2AMessage):
    Handle A2A messages for analysis agent.  This function processes messages of
    type "generate_productivity_report"  from the task manager. It retrieves the
    current tasks and long-term goals,  calculates the number of completed and
    pending tasks, and generates a  productivity report. The report includes the
    total number of tasks,  completion rate, and the number of active goals, which
    is then sent back  to the requesting agent.
    
    Args:
        message (A2AMessage): The incoming message containing the request type."""
    if message.message_type == "generate_productivity_report":
        # Task manager requesting a productivity report
        tasks_result = list_tasks()
        goals_result = list_long_term_goals()
        
        completed_tasks = [t for t in tasks_result.get("tasks", []) if t.get("status") == "done"]
        pending_tasks = [t for t in tasks_result.get("tasks", []) if t.get("status") == "pending"]
        
        analysis = {
            "total_tasks": len(tasks_result.get("tasks", [])),
            "completed_tasks": len(completed_tasks),
            "pending_tasks": len(pending_tasks),
            "completion_rate": len(completed_tasks) / max(len(tasks_result.get("tasks", [])), 1),
            "active_goals": len(goals_result.get("goals", [])),
            "report_generated_at": _now_iso()
        }
        
        response_msg = A2AMessage(
            from_agent="analysis_agent",
            to_agent=message.from_agent, 
            message_type="productivity_report",
            content=analysis
        )
        await a2a_protocol.send_message(response_msg)

# -------------------------------------------------------------------
# Root Agent (Orchestrator-based)
# -------------------------------------------------------------------

# Create orchestrator instance
orchestrator = SequentialAgentOrchestrator()

# Register A2A handlers
a2a_protocol.register_agent("task_manager_agent", handle_task_manager_message)
a2a_protocol.register_agent("goal_planning_agent", handle_goal_planning_message) 
a2a_protocol.register_agent("analysis_agent", handle_analysis_message)

# Root agent that uses the orchestrator
root_agent = LlmAgent(
    model=gemini_llm,
    name="smart_task_manager_orchestrator",
    description="Orchestrator agent that coordinates between specialized task management agents",
    instruction="""
You are the SmartTask Orchestrator. You coordinate between specialized agents:

Available Agents:
- Task Manager: Handles daily tasks, deadlines, priorities
- Goal Planning: Manages long-term goals and strategy  
- Analysis & Reporting: Provides insights and productivity reports

Your role:
1. Understand the user's request
2. Route to the appropriate specialist agent(s)
3. Combine responses when needed
4. Provide final coordinated response

Always be helpful, structured, and leverage the full multi-agent system.
""",
    tools=[],  # Orchestrator uses sequential execution rather than direct tools
    generate_content_config=generate_config,
)

# -------------------------------------------------------------------
# Web Support Functions (Enhanced)
# -------------------------------------------------------------------

_web_runner = None
_web_session_id = None

def _build_content(message: str):
    """Builds content from a user message."""
    return types.Content(
        role="user",
        parts=[types.Part(text=message)]
    )

async def _get_web_runner():
    """Get or create a runner for web usage."""
    global _web_runner, _web_session_id
    
    if _web_runner is None:
        _web_runner = InMemoryRunner(agent=root_agent)
        
        session = await _web_runner.session_service.create_session(
            app_name="smart_task_manager_web",
            user_id="web_user"
        )
        _web_session_id = session.id
        
        tracker.log_event(
            EventType.SESSION_CREATED,
            "WebRunner",
            {"action": "session_created", "session_id": _web_session_id, "user_id": "web_user"}
        )
    
    return _web_runner, _web_session_id

async def chat_once(message: str, user_id: str = "web_user") -> str:
    """Handles a single chat interaction using the multi-agent orchestrator."""
    try:
        # Use the orchestrator for sequential multi-agent execution
        response = await orchestrator.execute_workflow(message, user_id)
        return response
        
    except Exception as e:
        tracker.log_event(EventType.ERROR, "WebChat", {"action": "chat_failed", "error": str(e)})
        return "Hello! I'm SmartTask. How can I help you with your tasks today?"

# Simple command-based chat (unchanged from original)
def simple_chat_once(message: str) -> str:
    """Simple chat that uses direct function calls for common commands."""
    message_lower = message.lower().strip()
    
    try:
        greeting_responses = {
            'hi': "Hello! I'm SmartTask. How can I help with your tasks?",
            'hello': "Hi there! I'm here to help you manage tasks and goals.",
            'hey': "Hey! Ready to organize your tasks?",
            'hola': "¡Hola! I'm your task assistant.",
            'how are you': "I'm doing great! Ready to help you manage your tasks.",
        }
        
        if message_lower in greeting_responses:
            return greeting_responses[message_lower]
        
        # Add task command
        if message_lower.startswith("add "):
            parts = message[4:].strip()
            priority = "medium"
            due_date = None
            title = parts
            
            # Extract priority
            if " priority high" in parts.lower():
                priority = "high"
                parts = parts.replace(" priority high", "")
            elif " priority low" in parts.lower():
                priority = "low" 
                parts = parts.replace(" priority low", "")
            elif " priority medium" in parts.lower():
                parts = parts.replace(" priority medium", "")
            
            # Extract due date
            if " due " in parts.lower():
                due_idx = parts.lower().index(" due ")
                title = parts[:due_idx].strip()
                due_part = parts[due_idx + 5:].strip()
                # Simple date parsing - could be enhanced
                due_date = due_part.split()[0] if due_part else None
            else:
                title = parts
            
            if title and len(title) > 3:
                result = add_task(title, due_date, priority)
                if result["status"] == "success":
                    return f"✅ Task created! ID: {result['task']['id']}, Title: '{title}'" + (f", Due: {due_date}" if due_date else "") + f", Priority: {priority}"
                elif result["status"] == "duplicate":
                    return f"⚠️ Task already exists! ID: {result['task']['id']}"
                else:
                    return f"❌ {result.get('message', 'Failed to create task')}"
            else:
                return None
        
        # List tasks command
        elif message_lower in ["list tasks", "show tasks", "tasks"]:
            result = list_tasks()
            if result["status"] == "success" and result["tasks"]:
                tasks_str = "\n".join([
                    f"#{t['id']}: {t['title']} - {t['priority']} priority - {t['status']}" + 
                    (f" (due: {t['due_date']})" if t.get('due_date') else "")
                    for t in result["tasks"][:10]  # Limit to 10 tasks
                ])
                return f"📋 Your tasks:\n{tasks_str}"
            else:
                return "No tasks found. Add one with 'add [task description]'"
        
        # List goals command  
        elif message_lower in ["list goals", "show goals", "goals"]:
            result = list_long_term_goals()
            if result["status"] == "success" and result["goals"]:
                goals_str = "\n".join([
                    f"🎯 {g['goal']} ({g['horizon_months']} months)" + 
                    (f" - {g['category']}" if g.get('category') else "")
                    for g in result["goals"]
                ])
                return f"Your goals:\n{goals_str}"
            else:
                return "No goals found. Add one with 'I want to [goal] in [timeframe]'"
        
        # Show high priority tasks
        elif message_lower.startswith("show top"):
            parts = message_lower.split()
            n = 3  # default
            if len(parts) >= 3 and parts[2].isdigit():
                n = int(parts[2])
            result = list_high_priority_top_n(n)
            if result["status"] == "success" and result["tasks"]:
                tasks_str = "\n".join([
                    f"🚨 #{t['id']}: {t['title']}" + 
                    (f" (due: {t['due_date']})" if t.get('due_date') else "")
                    for t in result["tasks"]
                ])
                return f"🔝 Top {n} high priority tasks:\n{tasks_str}"
            else:
                return "No high priority tasks found."
        
        # Clean up old tasks
        elif message_lower == "delete previous month":
            result = delete_previous_month_tasks()
            if result["status"] == "success":
                return f"🧹 Cleaned up {result['deleted_count']} tasks from previous month"
            else:
                return f"❌ Cleanup failed: {result.get('message', 'Unknown error')}"
        
        else:
            return None
            
    except Exception as e:
        return f"Error executing command: {str(e)}"

# Hybrid approach for web
async def hybrid_chat_once(message: str) -> str:
    """Try simple commands first, then fall back to multi-agent orchestrator."""
    if any(keyword in message.lower() for keyword in 
           ["add ", "list tasks", "show top", "delete previous month", "list goals"]):
        result = simple_chat_once(message)
        if result is not None:
            return result
    
    try:
        return await chat_once(message)
    except Exception as e:
        return f"Hello! I can help you manage tasks. Try commands like:\n- 'add [task] due [date] priority [high/medium/low]'\n- 'list tasks'\n- 'show top 3 high priority'\n- 'list goals'"

# Direct function call for add task
def direct_add_task(title: str, due_date: str = None, priority: str = "medium") -> str:
    """Direct function to add task without using agents."""
    try:
        result = add_task(title, due_date, priority)
        if result["status"] == "success":
            return f"✅ Task created! ID: {result['task']['id']}, Title: {title}"
        else:
            return f"❌ {result.get('message', 'Failed to create task')}"
    except Exception as e:
        return f"Error: {str(e)}"

# -------------------------------------------------------------------
# Observability Endpoints
# -------------------------------------------------------------------

def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics for observability."""
    events = tracker.events
    
    agent_calls = len([e for e in events if e.event_type == EventType.AGENT_CALL])
    tool_executions = len([e for e in events if e.event_type == EventType.TOOL_EXECUTION])
    a2a_messages = len([e for e in events if e.event_type == EventType.A2A_COMMUNICATION])
    errors = len([e for e in events if e.event_type == EventType.ERROR])
    
    return {
        "total_events": len(events),
        "agent_calls": agent_calls,
        "tool_executions": tool_executions,
        "a2a_messages": a2a_messages,
        "errors": errors,
        "uptime": "since_first_event",  # Would need startup time tracking
        "recent_events": [
            {
                "event_type": e.event_type.value,
                "agent": e.agent_name,
                "timestamp": e.timestamp,
                "action": e.details.get("action", "unknown")
            }
            for e in events[-10:]  # Last 10 events
        ]
    }

# -------------------------------------------------------------------
# CLI Support with Enhanced Features
# -------------------------------------------------------------------

async def cli_chat_once(message: str, user_id: str = "cli_user") -> str:
    """Handles a single chat interaction via CLI."""
    try:
        return await orchestrator.execute_workflow(message, user_id)
    except Exception as e:
        return f"Error: {str(e)}"

async def start_a2a_processor():
    """Start the A2A message processor."""
    await a2a_protocol.start_message_processor()

if __name__ == "__main__":
    print("SmartTask – Enhanced Multi-Agent System")
    print("Features: Multi-agent, Observability, A2A Protocol, Sequential Execution")
    print("Type a message (or 'quit'):\n")
    
    async def main():
        # Start A2A message processor
        """Starts the main interactive chat loop for the CLI.
        
        This function initializes an A2A message processor and enters an infinite loop
        to handle user input. It processes user messages, checks for specific system
        commands like "metrics", and interacts with the `cli_chat_once` function to
        generate replies. The loop continues until the user decides to exit by typing
        "q", "quit", or "exit". Finally, it ensures proper cleanup by stopping the  A2A
        protocol and canceling the associated task.
        """
        a2a_task = asyncio.create_task(start_a2a_processor())
        
        try:
            while True:
                user_msg = input("you> ")
                if user_msg.lower().strip() in {"q", "quit", "exit"}:
                    break
                
                # Check for system commands
                if user_msg.lower() == "metrics":
                    metrics = get_system_metrics()
                    print("\nSystem Metrics:")
                    print(json.dumps(metrics, indent=2))
                    continue
                
                try:
                    reply = await cli_chat_once(user_msg, "cli_user")
                except Exception as e:
                    reply = f"[ERROR] {e}"
                print("\nagent>", reply, "\n")
        
        finally:
            a2a_protocol.stop()
            a2a_task.cancel()
    
    asyncio.run(main())