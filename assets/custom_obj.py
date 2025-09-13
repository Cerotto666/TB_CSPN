import time
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Optional, List, Dict, Any, Set
from typing import Annotated, Sequence, TypedDict
import operator

from pydantic import BaseModel


class Incident(BaseModel):
    id: str
    created_at: datetime
    short_description: str = ""
    description: str = ""
    service: Optional[str] = None
    impact: Optional[int] = None  # 1=alto, 2=medio, 3=basso
    state: Optional[str] = None   # "new", "in progress", "resolved", "closed"

class Token(BaseModel):
    id: str
    layer: str
    topics: Dict[str, float]
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]


class Directive(BaseModel):
    """Directive issued by Supervisor agents"""
    id: str
    action: str
    confidence: float
    source_token_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = None

class BaseLog(BaseModel):
    node_name: str
    token_usage: int
    processing_time: int  # ms
    total_cost: float
    llm_count: int

class ConsultantLog(BaseLog):
    input_length: int
    token_id: str
    topic_extracted: List[str]

class SupervisorLog(BaseLog):
    actions: List[str]
    reasons: List[str]
    token_id: str
    directive_generated: int
    timestamp: datetime

class WorkerLog(BaseLog):
    directive_id: str
    action: str
    success: bool
    timestamp: datetime


class AgentRole(StrEnum):
    unknown = "unknown"
    consultant = "consultant"
    supervisor = "supervisor"
    worker = "worker"

class AgentState(BaseModel):
    topics: Annotated[set[str], operator.or_]
    incident: Optional[Incident] = None
    token: Optional[Token] = None
    directives: Optional[List[Directive]] = None
    nodes_logs: Optional[Dict[str, List[Any]]]

if __name__=="__main__":
    print(time.time())










