import json
from datetime import date
from typing import List, Dict

from loguru import logger

from assets import set_environment_variables, upload_json_incidents, AgentState, Incident, BaseLog
from assets.graph import IncidentsGraph

logs: List[Dict[str,Dict[str,List[BaseLog]]]] = []

def main():
    set_environment_variables(f"incidents_analyzer_{date.today()}")
    incidents = upload_json_incidents()
    for i,inc in enumerate(incidents):
        agent_graph = IncidentsGraph()
        response = agent_graph.run(inc)
        logger.info(response)
        logs.append({f"Inc{i}" : response.nodes_logs})
        if i == 5:
            break
    logger.info(logs)

    final_cost = 0
    total_llm_calls = 0
    total_time = 0
    total_time_in_minutes = 0
    total_success_rate = 0
    total_items = 0
    for i, log in enumerate(logs):
        log_value = log[f'Inc{i}']
        logger.info(f"i:{i}")
        # logger.info(log_value)
        consultant_logs = log_value['consultant']
        supervisor_logs = log_value['supervisor']
        worker_logs = log_value['worker']
        total_items += 1
        for cl in consultant_logs:
            final_cost += cl.total_cost
            total_llm_calls += cl.llm_count
            total_time += cl.processing_time
            total_time_in_minutes += int(total_time/60000)
        for sl in supervisor_logs:
            final_cost += sl.total_cost
            total_llm_calls += sl.llm_count
            total_time += sl.processing_time
            total_time_in_minutes += int(total_time/60000)
    logger.info(f"Final cost: {final_cost}")
    logger.info(f"Total llm calls: {total_llm_calls}")
    logger.info(f"Total Executionn time in ms: {total_time}")
    logger.info(f"Total processed items {total_items}")





if __name__=="__main__":
    main()