import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
# from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions

# Carrega segredos


load_dotenv('credentials.env')
data_source_id = os.getenv('SOURCE')
token = os.getenv('TOKEN')
base = os.getenv('BASE')
mercus_user = os.getenv("MERCUS_USER")
mercus_password = os.getenv("MERCUS_PASSWORD")

equipe_elano = ['Alexandre', 'Bernardo', 'Claudiano', 'Elisângela Damasceno Silva', 'Elton Reury', 'Gabriel Mota Façanha', 'Kelly Nobre', 'Nara (Elano)', 'Rita de Cássia', 'Wiler Bastos']
equipe_junior = ['Carlos Eduardo', 'Catarina Rocha', 'Erica Alencar', 'Léo Rodrigues', 'Marcelo Gomes', 'Marcos Morais', 'Nara Alexandre (Júnior)', 'Reinaldo', 'Venda Interna (Catarina)', 'Venda Interna Marcelo']
equipe_raphael = ['Claudinei Ferreira', 'Débora Picinin (SP)', 'Henrique dos Santos', 'Juliana Estrela', 'Marcia Andreia']

chrome_options = Options()

# Add the experimental "detach" option
chrome_options.add_experimental_option("detach", True)
# chrome_options.add_argument("--headless=new")
# Initialize the WebDriver with the specified options
driver = webdriver.Chrome(options=chrome_options)

base_url = 'https://app.mercos.com/384882/'
url_faturados = 'relatorios/pedidos_faturados/'
url_pesquisa = base_url+url_faturados

mes = datetime.today().month
data_inicial = datetime(2026, mes, 1)
periodo_incial = datetime.strftime(data_inicial, "%d/%m/%Y")
periodo_final = "31/07/2026"

params = {'ajax':1, 'ordem':'asc', 'periodo_final':f'{periodo_final}', 'periodo_inicial':f'{periodo_incial}', 'status_pedido':'2', 'tipo_de_pedido':'-1', 'valor_ordenacao':'data_emissao'}
url = f"{url_pesquisa}?{urlencode(params)}"
driver.get(url)

def login_mercus(login, senha):
    elem = driver.find_element(By.NAME, "usuario")
    elem.send_keys(login)
    elem = driver.find_element(By.NAME, "senha")
    elem.send_keys(senha)
    elem.submit()
    
login_mercus(mercus_user, mercus_password)
nomes = {}
def busca_pedidos():
    WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.ID, 'componente-de-tabela-2'))
)
    linhas = driver.find_elements(By.XPATH, '//*[@id="componente-de-tabela-2"]/table/tbody/tr')
    # print(linhas)
    for linha in linhas:
        # print(linha.text)
        pedido = linha.find_element(By.TAG_NAME, "a")
        vendedor = linha.find_elements(By.TAG_NAME, "td")[4].text
        item = pedido.text.replace("#","")
        par = {item:vendedor}
        # print(item, ' - ', vendedor)
        nomes.update(par)
    return nomes
coisas = busca_pedidos()
print(coisas)
driver.close()

# if vendedor in equipe_elano:
#     equipe = "ELANO"
# if vendedor in equipe_junior:
#     equipe = "JUNIOR"
# if vendedor in equipe_raphael:
#     equipe = "RAPHAEL"

# print(equipe)



# response = requests.patch(url, json=payload, headers=headers)

# atualiza = response.json()
# print(atualiza)