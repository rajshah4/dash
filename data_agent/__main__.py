"""
Data Agent CLI Entry Point
==========================

Run the data agent:
    python -m data_agent
"""

from data_agent.agent import data_agent

if __name__ == "__main__":
    data_agent.cli_app(stream=True)
