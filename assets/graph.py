import uuid

from langgraph.graph.state import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from assets.helper import ROUTER_SUPERVISOR_NAME, INPUT_CONSULTANT_NAME
from assets import *
from assets.nodes import *

class IncidentsGraph():
    def __init__(self):
        self.builder = StateGraph(AgentState)
        memory = MemorySaver()

        # Nodi
        self.builder.add_node(INPUT_CONSULTANT_NAME, input_consultant_node)
        self.builder.add_node(ROUTER_SUPERVISOR_NAME, router_supervisor_node)
        self.builder.add_node(ROOT_CAUSE_CONSULTANT_NAME, root_cause_consultant_node)
        self.builder.add_node(ENTITY_GRAPH_CONSULTANT_NAME, entity_graph_consultant_node)
        self.builder.add_node(TOOL_INVOCATION_SUPERVISOR_NAME, tool_invocation_supervisor_node)
        self.builder.set_entry_point(INPUT_CONSULTANT_NAME)
        self.graph = (
            self.builder
            .compile(checkpointer=memory)
            .with_config({
                "configurable": {"thread_id": str(uuid.uuid4())}
            })
        )
        topics = set(upload_topics())
        self.state = AgentState(
            topics=topics,
            incident=None,
            token=None,
            directives=[],
            nodes_logs={
                AgentRole.consultant.value: [],
                AgentRole.supervisor.value: [],
                AgentRole.worker.value: []
            }
        )

    def run(self, incident: Incident) -> AgentState:
        state_dict = self.state.model_dump()

        invoke_input = {
        **state_dict,
        "incident": incident
        }

        new_state_dict = self.graph.invoke(invoke_input)

        self.state = AgentState(**new_state_dict)

        return self.state

if __name__=="__main__":
    incidents = upload_json_incidents()
    for inc in incidents:
        state = AgentState(
            topics=set(),
            incident=Incident(**inc),
            token=None,
            nodes_logs=None
        )
        agent_graph = IncidentsGraph()
        response = agent_graph.run(inc)
        print(response)
        break