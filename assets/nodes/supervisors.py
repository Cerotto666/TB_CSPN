import json
import time
import uuid
from datetime import datetime

from assets.utils import create_agent, choose_worker_tool, parse_worker_log
from assets.custom_obj import AgentState, AgentRole, Directive, WorkerLog
from assets.helper import add_log_to_state, ROUTER_SUPERVISOR_NAME
from langchain_openai import ChatOpenAI
from langgraph.types import Command
from loguru import logger
from langchain_community.callbacks import get_openai_callback

from assets.utils import group_scores
from assets.nodes.workers import restart_worker_tool, diagnostics_worker_tool, notify_team_worker_tool, \
    log_work_note_worker_tool
from assets.prompts import TOOL_SUPERVISOR_PROMPT

LLM = ChatOpenAI(model="gpt-4o-mini")

TOOL_REGISTRY = {
    "restart_worker": restart_worker_tool,
    "diagnostics_worker": diagnostics_worker_tool,
    "notify_team_worker": notify_team_worker_tool,
    "log_work_note_worker": log_work_note_worker_tool,
}

def router_supervisor_node(state: AgentState) -> Command:
    #@TODO rivedere il sistema di soglie rispetto ai topic, introdurre elementi di dinamismo
    #@TODO meccanismo di validazione di nuovi topic -> esportare i dati su file per la gestione dinamica
    #@TODO aggiungere versione con llm

    ROUTE_MIN = 0.50  # conf. minima per considerare “forte” un segnale
    MARGIN = 0.10  # margine per discriminare tra i due punteggi
    logger.info("Entering the router supervisor node")
    start_time = time.perf_counter()

    topics = state.token.topics

    rc_score, eg_score, rc_top, eg_top = group_scores(topics or {})

    # Decision policy
    if rc_score < ROUTE_MIN and eg_score < ROUTE_MIN:
        route = "entity_graph_consultant"  # raccolta contesto prima
        reason = f"weak signals (rc={rc_score:.2f}, eg={eg_score:.2f})"
    else:
        if rc_score > eg_score + MARGIN:
            route = "root_cause_consultant"
            reason = f"root-cause dominance: {rc_top}={rc_score:.2f}"
        elif eg_score > rc_score + MARGIN:
            route = "entity_graph_consultant"
            reason = f"entity-graph dominance: {eg_top}={eg_score:.2f}"
        else:
            # tie-break: preferisci costruire contesto
            route = "entity_graph_consultant"
            reason = f"tie (rc={rc_score:.2f}, eg={eg_score:.2f}) → prefer entity"

    directive_text = f"Routing to route: {route}"
    directive = Directive(
        id=str(uuid.uuid4()),
        action=directive_text,
        confidence=rc_score if route == "root_cause_consultant" else eg_score,
        source_token_id=state.token.id,
        timestamp=datetime.now(),
        metadata={
            "directive_text": directive_text,
            "directive_reason": reason,
            "processing_time": time.time() - start_time
        }
    )
    logger.info(f"Directive created with ID: {directive.id}")
    state.directives = [directive]
    # print(state)

    state = add_log_to_state(
        agent_name=ROUTER_SUPERVISOR_NAME,
        agent_role=AgentRole.supervisor.value,
        start_time=start_time,
        llm_count=False,
        llm_callback=None,
        state=state
    )
    return Command(
        update={
            "nodes_logs": state.nodes_logs,
            "directives": state.directives
        },
        goto=route
    )

def tool_invocation_supervisor_node(state: AgentState) -> Command:
    logger.info("Entering the tool_invocation_supervisor node")
    start_time = time.perf_counter()

    # 1) Scegli il tool
    topics = state.token.topics
    incident = state.incident
    inc_dict = incident.model_dump(
        mode="python",
        exclude_none=True,
        by_alias=True
    )
    tool_name, confidence, reason = choose_worker_tool(topics, inc_dict)


    directive_text = f"[Directive] Execute tool '{tool_name}' for incident {incident.id}. "

    directive = Directive(
        id=str(uuid.uuid4()),
        action=directive_text,
        confidence=confidence,
        source_token_id=getattr(state.token, "id", None),
        timestamp=datetime.now(),
        metadata={
            "selected_tool": tool_name,
            "directive_text": directive_text,
            "directive_reason": reason if reason else "Reason not detected",
            "processing_time": time.perf_counter() - start_time,
        },
    )
    logger.info(f"Directive created with ID: {directive.id} → tool={tool_name}")
    logger.info(f"Reason: {directive.metadata['directive_reason']}")

    tool_obj = TOOL_REGISTRY[tool_name]
    agent = create_agent(
        llm=LLM,
        tools=[tool_obj],
        system_prompt=TOOL_SUPERVISOR_PROMPT,
    )

    with get_openai_callback() as cb:
        result = agent.invoke({
            # molti agent executor richiedono 'input'
            "input": directive_text,
            # variabili usate dal prompt
            "directive": directive_text,
            "directive_id": directive.id,
            "incident_json": inc_dict,
            "topics": topics,
            "tool_name": tool_name
        })

    logger.debug(f"tool_invocation_supervisor agent result: {result}")
    state.directives = [directive]

    logger.debug("------------------------------------------")
    logger.debug(f"Creating worker log from supervisor node")
    worker_log = parse_worker_log(result.get("output"))
    if isinstance(worker_log, WorkerLog):
        state.nodes_logs.setdefault("worker", []).append(worker_log)
    else:
        logger.warning(f"Worker log non valido, salvato come raw: {worker_log}")
    logger.debug("------------------------------------------")

    state = add_log_to_state(
        agent_name="tool_invocation_supervisor",
        agent_role=AgentRole.supervisor.value,
        start_time=start_time,
        llm_count=True,
        llm_callback=cb,
        state=state,
    )

    update = {
        "nodes_logs": state.nodes_logs,
        "directives": state.directives,
        "last_executed_tool": tool_name,
        "last_tool_result": result.get("output", result),
    }
    return Command(update=update, goto="__end__")
