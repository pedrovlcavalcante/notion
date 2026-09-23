from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from bs4 import BeautifulSoup
from datetime import datetime
import time
from decimal import Decimal
import tkinter as tk
from tkinter import messagebox
from notion import procura, cria_pedido, cria_bloco, login_mercus, transportadoras, equipe
from dependencias import selenium_esta_rodando, Pedido, Cliente
import logging
import pandas as pd

tipos_boleto = ['Para 30 dias', 'Para 45 dias']
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

def busca_pedidos(driver):
    WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.ID, 'componente-de-tabela-2'))
)
    linhas = driver.find_elements(By.XPATH, '//*[@id="componente-de-tabela-2"]/table/tbody/tr')
    for linha in linhas:
        pedido_mercos = linha.find_element(By.TAG_NAME, "a")
        numero_pedido_mercos = pedido_mercos.text.replace("#","")
        pesquisa = procura(numero_pedido_mercos)
        link_mercos = driver.current_url
        if len(pesquisa.json()['results']) == 0:
            print(f"Criando Pedido {numero_pedido_mercos} no Notion")
            driver.execute_script("arguments[0].scrollIntoView(true);", pedido_mercos)
            pedido_mercos.click()

            wait = WebDriverWait(driver, 10)

            original_window_handle = driver.current_window_handle
            wait.until(EC.number_of_windows_to_be(2))

            new_window_handle = (set(driver.window_handles) - {original_window_handle}).pop()
            driver.switch_to.window(new_window_handle)
            assert driver.current_window_handle == new_window_handle
            link_mercos = driver.current_url

            # salva html do pedido
            html = driver.page_source
            file_path = f"novos_pedidos\\{numero_pedido_mercos}.html"
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(html)

            pedido = Pedido(numero_pedido_mercos, link_mercos)
            pedido.extrai_produtos()
            pedido.calcula_frete_tabelado()
            pedido.itens_fabrica()
            pedido.cria_pedido_notion()

            print(f"Pedido {pedido.numero} | Quantidade de itens: {pedido.itens} | Quantidade Total: {pedido.quantidade} | Valor: {pedido.valor_pedido} | Pagamento: {pedido.condicao_pagamento} | Cliente: {pedido.cliente.nome} | Vendedor: {pedido.vendedor} | Data: {pedido.data_pedido}" )
            print(pedido.link)
            driver.close()
            driver.switch_to.window(original_window_handle)
        else:
            print(f"Pedido {numero_pedido_mercos} já está nos pedidos")

while selenium_esta_rodando():
    for i in range(4):
        pontos = "." * i
        time.sleep(0.2)
        print(f"\rAguardando vez para acessar a pagina{pontos:<3}", end="", flush=True)

diferenca = verifica_dia()

periodo_final = datetime.strftime(datetime.today().date(), "%d/%m/%Y")
data_inicial = datetime.today().date() - diferenca
periodo_incial = datetime.strftime(data_inicial, "%d/%m/%Y")

#Abre chrome e acessa mercos
chrome_options = Options()

# Add the experimental "detach" option
chrome_options.add_experimental_option("detach", True)
chrome_options.add_argument("--headless=new")

# Initialize the WebDriver with the specified options
driver = webdriver.Chrome(options=chrome_options)

print(f"Período: {periodo_incial} - {periodo_final}")
base_url = 'https://app.mercos.com/384882/'
url_faturados = 'relatorios/pedidos_faturados/'
url_pesquisa = base_url+url_faturados

params = {'ajax':1, 'ordem':'asc', 'periodo_final':f'{periodo_final}', 'periodo_inicial':f'{periodo_incial}', 'status_faturamento':'0', 'status_pedido':'2', 'tipo_de_pedido':'-1', 'valor_ordenacao':'data_emissao'}

url = f"{url_pesquisa}?{urlencode(params)}"

driver.get(url)
login_mercus(driver)
driver.get(url)
    
log()

nao_faturados = busca_pedidos(driver)
driver.close()

root = tk.Tk()
root.withdraw()
root.attributes('-topmost', 1) 

# Display the popup window
messagebox.showinfo("Notion", "Pedidos adicionados", parent=root)
root.destroy()