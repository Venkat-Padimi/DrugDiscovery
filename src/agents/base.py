import time
import abc
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.domain.enums import WorkflowStage
from src.domain.state import ResearchGraphState, WorkflowError
from src.domain.models import AgentTraceEvent


class BaseAgent(abc.ABC):
    """
    Abstract base class for all specialized research agents.
    Enforces standardized tracing, execution timing, and error handling.
    """

    def __init__(self, agent_name: str, stage: WorkflowStage):
        self.agent_name = agent_name
        self.stage = stage

    @abc.abstractmethod
    def run(self, state: ResearchGraphState) -> ResearchGraphState:
        """Executes the agent's domain logic on the shared workflow state."""
        pass

    def record_trace(
        self,
        state: ResearchGraphState,
        input_summary: str,
        output_summary: str,
        tool_calls: Optional[List[str]] = None,
        duration_ms: float = 0.0,
        status: str = "success",
        notes: Optional[str] = None,
    ) -> None:
        """Appends a strongly typed trace event to state['audit_trace']."""
        trace = AgentTraceEvent(
            agent_name=self.agent_name,
            stage=self.stage,
            input_summary=input_summary,
            output_summary=output_summary,
            tool_calls=tool_calls or [],
            duration_ms=round(duration_ms, 2),
            status=status,
            notes=notes,
        )
        if "audit_trace" not in state:
            state["audit_trace"] = []
        state["audit_trace"].append(trace.model_dump())

    def record_error(
        self,
        state: ResearchGraphState,
        error_type: str,
        message: str,
        is_fatal: bool = False,
        degradation_applied: bool = False,
    ) -> None:
        """Appends a structured error event to state['errors']."""
        err = WorkflowError(
            stage=self.stage,
            agent_name=self.agent_name,
            error_type=error_type,
            message=message,
            is_fatal=is_fatal,
            degradation_applied=degradation_applied,
        )
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(err.model_dump())
