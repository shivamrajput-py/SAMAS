"""
LangGraph agents for SAMAS.

Each agent is a LangGraph StateGraph â€” a state machine where:
- Nodes are functions that process data
- Edges define the flow between nodes
- State is a shared dictionary that nodes read from and write to

Currently implemented:
- profile_builder.py â†’ The Profile Builder agent (Phase 1)

Coming soon:
- interview_agent.py â†’ The HITL Interview agent (Phase 2)
"""
