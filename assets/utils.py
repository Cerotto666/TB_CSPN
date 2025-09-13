import csv
import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Union, Dict, List, Tuple

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.output_parsers import StrOutputParser

from decouple import config
from langchain_core.runnables import RunnableSerializable

from assets.custom_obj import AgentState

from langgraph.types import Command
from loguru import logger

AgentLike = Union[AgentExecutor, RunnableSerializable[dict, Any]]
def create_agent(llm: BaseChatModel, tools: list, system_prompt: str) -> AgentExecutor:
    """
    Crea un agente con tools
    :param llm:
    :param tools:
    :param system_prompt:
    :return: AgentExecutor
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),  # richiesto dal tools agent
    ])
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools)  # type: ignore
    return agent_executor

def create_chain(llm: BaseChatModel, system_prompt: str) -> RunnableSerializable[dict, Any]:
    return ChatPromptTemplate.from_template(system_prompt) | llm | StrOutputParser()

def agent_node(state: AgentState, agent: AgentLike, name: str, field_to_update: str, go_to: str):
    result = agent.invoke(state)
    if isinstance(agent, RunnableSerializable):
        return Command(
            update={
                field_to_update: result['field_to_update']
            },
            goto=result['go_to']
        )


def set_environment_variables(project_name: str = "") -> None:
    """
    Funzione di caricamento delle variabili d'ambiente da .env
    :param project_name: il nome del progetto per il logging su langsmith
    :return:
    """
    if not project_name:
        project_name = f"Test_{date.today()}"

    os.environ["OPENAI_API_KEY"] = str(config("OPENAI_API_KEY"))

    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = str(config("LANGCHAIN_API_KEY"))
    os.environ["LANGCHAIN_PROJECT"] = project_name


def upload_json_incidents() -> List[Dict]|None:
    """
    Funzione di caricamento di una lista di json
    :return: La lista di dizionari corrispondenti ai json del file
    """
    PROJECT_ROOT = Path(__file__).resolve().parent
    path = PROJECT_ROOT.parent / "data" / "incidents.json"
    try:
        logger.info(f"loading file: {path.name}")
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logger.error(f"Errore nel caricamento del file json:{path.name}")
        return None

def upload_topics(strip: bool = True, drop_empty: bool = True)-> List[str]|None:
    """
    funzione di caricamento di una lista di stinghe
    Il file deve avere stringhe separate da virgola
    :return: La lista di stringhe
    """
    PROJECT_ROOT = Path(__file__).resolve().parent
    path = PROJECT_ROOT.parent / "data" / "topics.txt"
    items: List[str] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=",")
        for row in reader:            # row è una lista di celle su quella riga
            for cell in row:
                s = cell.strip() if strip else cell
                if drop_empty and s == "":
                    continue
                items.append(s)
    return items if items else []

def save_topics(topics: Dict[str,float])-> None:
    PROJECT_ROOT = Path(__file__).resolve().parent
    path = PROJECT_ROOT.parent / "data" / "topics.txt"
    new_topics = set(topics.keys())
    saved_topics = set(upload_topics())
    all_topics = new_topics | saved_topics
    logger.info("Saving new topics to file")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(all_topics)
    pass

def group_scores(topics: Dict[str, float]) -> tuple[float, float, str, str]:
    ROOT_CAUSE_TOPICS = {
        "availability", "latency", "auth", "database", "network", "config", "capacity", "diagnostics"
    }
    ENTITY_GRAPH_TOPICS = {
        "dependency", "deployment", "incident_management","restart_candidate","notification_required"
    }
    tnorm = {str(k).lower().strip(): float(v) for k, v in (topics or {}).items()}
    rc = {k: v for k, v in tnorm.items() if k in ROOT_CAUSE_TOPICS}
    eg = {k: v for k, v in tnorm.items() if k in ENTITY_GRAPH_TOPICS}
    rc_score = max(rc.values()) if rc else 0.0
    eg_score = max(eg.values()) if eg else 0.0
    rc_top = max(rc, key=rc.get) if rc else ""
    eg_top = max(eg, key=eg.get) if eg else ""
    return rc_score, eg_score, rc_top, eg_top

def merge_topic_scores(old: Dict[str, float], new: Dict[str, float]) -> Dict[str, float]:
    """Unisce i topic mantenendo per ogni chiave lo score massimo (con clamp [0,1])."""
    out = dict(old or {})
    for k, v in (new or {}).items():
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if not (0.0 <= v <= 1.0):
            v = max(0.0, min(1.0, v))
        kk = str(k).lower().strip()
        out[kk] = max(v, out.get(kk, 0.0))
    return out

def choose_worker_tool(topics: Dict[str, float], incident: Dict) -> Tuple[str, float, str]:
    """
    Ritorna (tool_name, confidence, reason).
    """
    t = {str(k).lower().strip(): float(v) for k, v in (topics or {}).items()}
    impact = incident.get("impact")  # 1,2,3
    state  = (incident.get("state") or "").lower()

    # 1) Restart se forte candidato e il ticket non è chiuso
    if t.get("restart_candidate", 0.0) >= 0.70 and state not in {"resolved", "closed"}:
        return "restart_worker", t["restart_candidate"], "restart_candidate strong and ticket open"

    # 2) Notifica se richiesta esplicita o impatto alto + availability molto alto
    if t.get("notification_required", 0.0) >= 0.70:
        return "notify_team_worker", t["notification_required"], "notification_required strong"
    if impact == 1 and t.get("availability", 0.0) >= 0.85:
        return "notify_team_worker", t["availability"], "high impact + availability signal"

    # 3) Diagnostica se richiesto/utile
    if t.get("diagnostics", 0.0) >= 0.60:
        return "diagnostics_worker", t["diagnostics"], "diagnostics indicated"

    # 4) Fallback: log work note
    conf = max(t.get("incident_management", 0.0), 0.50)
    return "log_work_note_worker", conf, "fallback to work note"

if __name__=="__main__":
    save_topics({"a":1,"b":2})