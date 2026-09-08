import logging
from datetime import datetime, timedelta

# Configura o log para gravar apenas a data e hora no arquivo 'datas.log'
def log():
    logging.basicConfig(
        filename='datas.log', 
        level=logging.INFO, 
        format='%(asctime)s', 
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Grava o registro atual
    logging.info('')

def verifica_dia():
    with open("datas.log", "r") as file:
        ultima = file.readlines()[-1].replace("\n", "")
    ultima_data = datetime.strptime(ultima, "%Y-%m-%d %H:%M:%S").date()
    hoje = datetime.today().date()
    diferenca = hoje - ultima_data
    return diferenca

log()