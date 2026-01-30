"""
Data Agent
==========

A self-learning data agent inspired by OpenAI's internal data agent.

Features:
- 6 layers of context for grounded reasoning
- LearningMachine for continuous improvement
- Knowledge-based SQL generation
- Provides insights, not just data

Usage:
    python -m data_agent

See README.md for documentation.
"""

from data_agent.agent import data_agent

__all__ = ["data_agent"]
