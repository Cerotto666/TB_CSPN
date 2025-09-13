from langchain.tools import tool
from loguru import logger


@tool("restart_worker")
def restart_worker_tool(directive: str, directive_id: str) -> str:
    """
    Restart a failing component/service according to the directive.

    Args:
        directive: The plain-text instruction for the worker (e.g., "service=orders restart-now").
        directive_id: A unique identifier to correlate logs and actions across nodes.

    Returns:
        "ok" if the action was accepted.
    """
    logger.info(f"[restart_worker] id={directive_id} directive={directive}")

    return "ok"


@tool("diagnostics_worker")
def diagnostics_worker_tool(directive: str, directive_id: str) -> str:
    """
    Run diagnostics as requested by the directive.

    Args:
        directive: The diagnostic instruction (e.g., "collect=cpu,mem duration=120s").
        directive_id: A unique identifier to correlate logs and actions across nodes.

    Returns:
        "ok" if the action was accepted.
    """
    logger.info(f"[diagnostics_worker] id={directive_id} directive={directive}")
    return "ok"


@tool("notify_team_worker")
def notify_team_worker_tool(directive: str, directive_id: str) -> str:
    """
    Notify the on-call team according to the directive.

    Args:
        directive: The message/routing info (e.g., "channel=sev1 text='DB down'").
        directive_id: A unique identifier to correlate logs and actions across nodes.

    Returns:
        "ok" if the action was accepted.
    """
    logger.info(f"[notify_team_worker] id={directive_id} directive={directive}")
    return "ok"


@tool("log_work_note_worker")
def log_work_note_worker_tool(directive: str, directive_id: str) -> str:
    """
    Append a work note in the incident record.

    Args:
        directive: The work note content or template reference.
        directive_id: A unique identifier to correlate logs and actions across nodes.

    Returns:
        "ok" if the action was accepted.
    """
    logger.info(f"[log_work_note_worker] id={directive_id} directive={directive}")
    return "ok"
