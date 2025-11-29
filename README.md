🧠 Smart Personal Task Manager Agent
A Multi-Agent, ADK-Compatible Productivity System with A2A Protocol, Observability & Orchestration
📌 Overview

Smart Personal Task Manager Agent is an AI-powered multi-agent productivity system built using the Google Agent Development Kit (ADK).
It helps users organize tasks, set long-term goals, generate productivity reports, and maintain a healthy workflow — all through a conversational interface.

The system uses a multi-agent architecture consisting of specialized agents (Task Manager, Goal Planner, and Analysis Agent) coordinated by an intelligent Orchestrator Agent.
Agents collaborate via a full Agent-to-Agent (A2A) Protocol, enabling advanced workflows and modular reasoning.

Designed as a complete submission for the Google × Kaggle Agents Intensive Capstone Project (2025).

<img width="1910" height="941" alt="image" src="https://github.com/user-attachments/assets/86b6125d-b4af-443a-830d-bf89ffd52188" />


Chat Interface
<img width="788" height="752" alt="image" src="https://github.com/user-attachments/assets/110b5c43-f171-4859-be42-8774694b09b9" />

Task List View

System Metrics / Observability

Architecture Diagram

🎯 Problem the System Solves

Most people struggle with:

Prioritizing tasks

Breaking big goals into actionable steps

Tracking long-term aspirations

Maintaining consistency

Understanding productivity trends

Existing tools lack reasoning, automation, and multi-step workflows.

This system solves all of these with intelligent agent-driven automation.

🤖 Why Agents?
🟦 Multi-Agent Collaboration

Each agent specializes in a domain:

Task Manager → tasks, subtasks, priorities

Goal Planner → long-term vision & strategy

Analysis Agent → reports, insights, summaries

Orchestrator → routes messages & coordinates workflows

🟩 A2A Protocol Communication

Agents communicate using structured messages:

Convert goals → tasks

Detect productivity patterns → create goals

Generate reports → share insights

🟦 Observability

Tracks:

Agent calls

Tool executions

Errors

A2A messages

Sessions

Metrics endpoint available.

🟩 Sequential & Hybrid Orchestration

The orchestrator detects:

Primary agent

Secondary agent

Multi-step workflows

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
✔ A2A Protocol (Custom Message Types)
✔ Tools (10+ ADK-compatible tools)
✔ Observability + Logging
✔ Sequential Orchestration
✔ FastAPI-based Web UI
✔ CLI Interface
✔ InMemory Sessions
🚀 Setup Instructions
1️⃣ Clone Repo
git clone https://github.com/yourusername/smart-task-manager-agent.git
cd smart-task-manager-agent

2️⃣ Install Dependencies
pip install -r requirements.txt

3️⃣ Create .env File
cp .env.example .env


Add your Gemini API keys.

4️⃣ Run CLI Version
python agent.py

5️⃣ Run Web Version
uvicorn web_app:app --reload


Visit:
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

🔹 Task Status
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

🎪 Demo Script (Use in Video or Presentation)
Phase 1: Basic Task Management
1. add Buy groceries due tomorrow priority high
2. add Complete project proposal due Friday priority high  
3. add Schedule team meeting priority medium
4. add Read book priority low
5. list tasks

Phase 2: Priorities & Updates
6. show top 3 high priority
7. update task 1 status done
8. update task 2 status in_progress
9. list tasks

Phase 3: Goal Setting
10. set a goal to learn Python in 3 months
11. I want to improve fitness in 2 months
12. list goals

Phase 4: Subtask Management
13. break down 'Complete project proposal' into subtasks
14. add subtasks to task 2: research, outline, write, review, submit
15. mark subtask 0 done for task 2

Phase 5: Reporting
16. generate productivity report
17. show progress report
18. clean old tasks

Phase 6: UI Quick Actions

Click “🚨 High Priority”

Click “📊 Report”

Click “🧹 Clean Old”

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

🛠 Technical Commands
System & Observability
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

Built using:

LlmAgent

InMemoryRunner

GenerateContentConfig

Gemini 2.0 Flash

ADK-compatible tools, sessions, orchestration, A2A messaging

Fully compatible with:
✔ Vertex Agent Engine
✔ Cloud Run deployment
✔ Future tool extensions

🏆 Competition Checklist

This project includes:

✔ Multi-agent architecture
✔ Sequential + hybrid orchestration
✔ Tools (custom + system-level)
✔ Sessions & memory
✔ Observability
✔ A2A protocol
✔ Web UI
✔ CLI
✔ Strong documentation

Compliant with ALL Capstone scoring requirements.

📜 License

MIT License.
