🧠 Smart Personal Task Manager Agent
A Multi-Agent, ADK-Compatible Productivity System with A2A Protocol, Observability & Orchestration
📌 Overview

Smart Personal Task Manager Agent is an AI-powered multi-agent productivity system built using the Google Agent Development Kit (ADK).

This system helps users:

Create, update, and organize daily tasks

Set and manage long-term goals

Generate productivity reports

View trends and analytics

Interact intuitively via conversation

The architecture includes four major agents:

Task Manager Agent

Goal Planning Agent

Analysis Agent

Orchestrator Agent (routes and coordinates)

Agents communicate using a fully implemented A2A Protocol, enabling multi-step reasoning and cooperative workflows.

This project is built as a comprehensive submission for the Google × Kaggle Agents Intensive Capstone Project (2025).

🖼️ Screenshots & UI Previews
💬 Chat Interface
<img width="1910" src="https://github.com/user-attachments/assets/86b6125d-b4af-443a-830d-bf89ffd52188" />
📋 Task List View
<img width="788" src="https://github.com/user-attachments/assets/110b5c43-f171-4859-be42-8774694b09b9" />
📊 System Metrics / Observability

(Add your image here when ready — recommended.)

🏗️ Architecture Diagram

(Optional: Insert exported architecture image here.)

🎯 Problem the System Solves

Modern life requires continuous task management and long-term planning.
However, most tools fall short because:

They only act as checklists

They do not break goals into actionable steps

They lack intelligent prioritization

They produce no insights or progress analysis

They cannot collaborate on complex requests

This system solves all of these with agent-driven automation + multi-step reasoning.

🤖 Why Agents?
🟦 Multi-Agent Collaboration

Each agent has a clear expertise:

Task Manager → tasks, deadlines, subtasks

Goal Planner → long-term goals & breakdown

Analysis Agent → insights, summaries, reports

Orchestrator → routing + multi-step pipelines

This mimics real-world delegation.

🟩 A2A Protocol (Agent-to-Agent Communication)

Agents coordinate through structured messages:

Goals → converted into tasks

Patterns → transformed into goals

Reports → auto-generated and shared

Long-term goals → broken into timelines

Enables autonomous cooperation.

🟦 Observability + Metrics

Every event is tracked:

Agent calls

Tool execution

A2A messages

Errors

System events

Session creation

Metrics and last 1000 events can be viewed anytime.

🟩 Sequential & Hybrid Orchestration

The Orchestrator determines:

Which agent should respond

When a secondary agent must join

How to combine outputs

Multi-step workflow execution

🏗️ Architecture Diagram
flowchart TD

    User[[User Input]] --> ORCH[Orchestrator Agent]

    ORCH -->|Routes Request| TM[Task Manager Agent]
    ORCH -->|Routes Request| GP[Goal Planning Agent]
    ORCH -->|Routes Request| AN[Analysis Agent]

    TM <-->|A2A Messages| GP
    TM <-->|A2A Messages| AN
    GP <-->|A2A Messages| AN

    TM --> DB[(tasks_db.json)]
    GP --> DB
    AN --> DB

    TM --> LOG[(Observability Logs)]
    GP --> LOG
    AN --> LOG
    ORCH --> LOG

⚙️ Features
✔ Multi-Agent System
✔ Full A2A Protocol
✔ FastAPI Web App
✔ CLI Interface
✔ Observability (logs + metrics)
✔ Task Manager Tools (10+)
✔ Goal Management
✔ Reporting & Analytics
✔ Sequential Orchestration
✔ InMemory Sessions
🚀 Installation & Setup
1️⃣ Clone the Repository
git clone https://github.com/yourusername/smart-task-manager-agent.git
cd smart-task-manager-agent

2️⃣ Install Dependencies
pip install -r requirements.txt

3️⃣ Create the .env File
cp .env.example .env


Insert your Gemini API key inside .env.

4️⃣ Run the CLI Version
python agent.py

5️⃣ Run the Web Version
uvicorn web_app:app --reload


Visit the UI at:
👉 http://127.0.0.1:8000

💬 Command List
🔹 Task Management
add Buy groceries due tomorrow priority high
add Complete project report due Friday
add Call dentist priority medium
list tasks
show tasks

🔹 Priority & Filtering
show top 3 high priority
show top 5
list high priority tasks

🔹 Task Status Updates
update task 1 status done
update task 2 status in_progress

🔹 Cleanup
delete previous month tasks
clean old tasks

🎯 Advanced Features
🔹 Goal Setting
set a goal to learn Python in 3 months
I want to run a marathon in 6 months
save goal: improve fitness in 2 months
list goals

🔹 Subtasks / Breakdown
break down "Complete project" into subtasks
add subtasks to task 3: research, outline, write, review
mark subtask 0 done for task 3

🔹 Reporting & Analytics
generate productivity report
show progress report
generate weekly summary
get task statistics

🎪 Demo Script (Perfect for Video Submission)
Phase 1: Basic Task Management
add Buy groceries due tomorrow priority high
add Complete project proposal due Friday priority high
add Schedule team meeting priority medium
add Read book priority low
list tasks

Phase 2: Priority & Status
show top 3 high priority
update task 1 status done
update task 2 status in_progress
list tasks

Phase 3: Goal Setting
set a goal to learn Python in 3 months
I want to improve fitness in 2 months
list goals

Phase 4: Subtasks
break down 'Complete project proposal' into subtasks
add subtasks to task 2: research, outline, write, review, submit
mark subtask 0 done for task 2

Phase 5: Reporting
generate productivity report
show progress report
clean old tasks

Phase 6: UI Quick Actions

🚨 High Priority

📊 Report

🧹 Clean Old

💡 Extra Demo Scenarios
Scenario A — Busy Professional
add Prepare client presentation due Wednesday priority high
add Review quarterly reports due Friday
add Team lunch meeting priority low
add Follow up with sales team priority medium
show top 2 high priority
generate productivity report

Scenario B — Student
add Complete math homework due tomorrow priority high
add Study for exams in 2 weeks
add Join coding workshop priority medium
set a goal to improve grades this semester
break down 'Study for exams' into subtasks

Scenario C — Project Manager
add Project kickoff meeting Monday priority high
add Create project timeline due Wednesday
add Assign team tasks priority medium
set a goal to deliver project on time
generate weekly summary

🛠 System & Technical Commands
System / Observability
show system status
get metrics
view agent health
check system events

Error Testing
add very very long task title that might test the system limits
update task 999 status done
delete task 999

📁 Project Structure
schedule_agent/
│
├── agent.py
├── web_app.py
├── tasks_db.json
├── requirements.txt
├── .env.example
└── __init__.py

🧩 ADK Compatibility Notes

This project uses:

LlmAgent

InMemoryRunner

GenerateContentConfig

Gemini 2.0 Flash

ADK-style tools and orchestration

Full A2A Protocol

Compatible with:

✔ Vertex Agent Engine
✔ Cloud Run
✔ MCP + future extensions

🏆 Competition Checklist

This project includes:

✔ Multi-agent system
✔ Sequential + hybrid orchestration
✔ Tools (10+)
✔ Sessions & memory
✔ A2A Protocol
✔ Observability
✔ Web App
✔ CLI
✔ Full Documentation
