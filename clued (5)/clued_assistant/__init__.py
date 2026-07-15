"""
Clued -- a multi-source AI research assistant.

    from clued_assistant import ClueEngine
    engine = ClueEngine()
    result = engine.research("What is quantum computing?")
"""

from .core import ClueEngine

__all__ = ["ClueEngine"]
__version__ = "1.0.0"
