from typing import List, Dict
from assets.custom_obj import BaseLog
from assets.run import process_input
from assets.helper import log_processing, print_summary

logs: List[Dict[str, Dict[str, List[BaseLog]]]] = []
# Struttura dell'oggetto di log
# Analisi dall'esterno verso l'interno
# List[Dict[.....]] -> ogni dizionario della lista ha chiave IncX e raccoglie tutte le info per l'incident
# ...Dict[str, Dict[str, .... -> Ogni dizionario con chiave IncX ha al suo interno 3 dizionari, con chiavi Supervisor, Consultant, worker
# ...Dict[str,List[BaseLog]]... -> Ogni chiave relativa al ruolo contiene una lista di log specifici del ruolo, tutti estensioni di BaseLog

def main():
    print_summary(log_processing(process_input()), style="table")


if __name__=="__main__":
    main()
