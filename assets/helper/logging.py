from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Any

from langchain_community.callbacks import OpenAICallbackHandler
from loguru import logger

from assets import AgentRole, AgentState, BaseLog, ConsultantLog, SupervisorLog


def add_log_to_state(
        agent_name:str,
        agent_role:str,
        state: AgentState,
        start_time: float,
        llm_count: bool,
        llm_callback: OpenAICallbackHandler|None,
        **role_specific_info:Any
) -> AgentState|None:
    logger.info(f"Adding {agent_name} log to state")
    log = BaseLog(
        node_name=agent_name,
        processing_time=round((time.perf_counter() - start_time) * 1000),
        token_usage=llm_callback.total_tokens if llm_callback else 0,
        total_cost=llm_callback.total_cost if llm_callback else 0,
        llm_count=llm_callback.successful_requests if llm_count else 0,
    )
    match agent_role:
        case AgentRole.consultant.value:
            consultant_log = ConsultantLog(
                **log.model_dump(),
                token_id=state.token.id,
                topic_extracted=state.token.topics.keys(),
                input_length=len(state.token.content)
            )
            state.nodes_logs[AgentRole.consultant.value].append(consultant_log)
            logger.info("log added successfully")
            return state
        case AgentRole.supervisor.value:
            supervisor_log = SupervisorLog(
                **log.model_dump(),
                actions=[directive.action for directive in state.directives],
                reasons=[directive.metadata['directive_reason'] for directive in state.directives],
                token_id=state.directives[0].source_token_id,
                directive_generated=len(state.directives),
                timestamp=datetime.now()
            )
            state.nodes_logs[AgentRole.supervisor.value].append(supervisor_log)
            logger.info("log added successfully")
            return state
        case _:
            pass

