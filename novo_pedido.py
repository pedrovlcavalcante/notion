from urllib.parse import urlencode
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
import time
from decimal import Decimal
import tkinter as tk
from tkinter import messagebox
from notion import procura, cria_pedido, cria_bloco, login_mercus, transportadoras, equipe
from dependencias import selenium_esta_rodando
import logging
import pandas as pd

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

while selenium_esta_rodando():
    for i in range(4):
        pontos = "." * i
        time.sleep(0.2)
        print(f"\rAguardando vez para acessar a pagina{pontos:<3}", end="", flush=True)

chrome_options = Options()

# Add the experimental "detach" option
chrome_options.add_experimental_option("detach", True)
chrome_options.add_argument("--headless=new")

# Initialize the WebDriver with the specified options
driver = webdriver.Chrome(options=chrome_options)

diferenca = verifica_dia()

periodo_final = datetime.strftime(datetime.today().date(), "%d/%m/%Y")
data_inicial = datetime.today().date() - diferenca
periodo_incial = datetime.strftime(data_inicial, "%d/%m/%Y")

log()

print(periodo_final, periodo_incial)
base_url = 'https://app.mercos.com/384882/'
url_faturados = 'relatorios/pedidos_faturados/'
url_pesquisa = base_url+url_faturados

params = {'ajax':1, 'ordem':'asc', 'periodo_final':f'{periodo_final}', 'periodo_inicial':f'{periodo_incial}', 'status_faturamento':'0', 'status_pedido':'2', 'tipo_de_pedido':'-1', 'valor_ordenacao':'data_emissao'}
url = f"{url_pesquisa}?{urlencode(params)}"
driver.get(url)

login_mercus(driver)

driver.get(url)

tipos_boleto = ['Para 30 dias', 'Para 45 dias']
    
def busca_pedidos():
    WebDriverWait(driver, 30).until(
    EC.presence_of_element_located((By.ID, 'componente-de-tabela-2'))
)
    linhas = driver.find_elements(By.XPATH, '//*[@id="componente-de-tabela-2"]/table/tbody/tr')
    for linha in linhas:
        pedido = linha.find_element(By.TAG_NAME, "a")
        item = pedido.text.replace("#","")
        pesquisa = procura(item)
        link_mercos = driver.current_url
        if len(pesquisa.json()['results']) == 0:
            print(f"Criando Pedido {item} no Notion")
            driver.execute_script("arguments[0].scrollIntoView(true);", pedido)
            pedido.click()

            wait = WebDriverWait(driver, 10)

            original_window_handle = driver.current_window_handle
            wait.until(EC.number_of_windows_to_be(2))

            new_window_handle = (set(driver.window_handles) - {original_window_handle}).pop()
            driver.switch_to.window(new_window_handle)
            assert driver.current_window_handle == new_window_handle
            link_mercos = driver.current_url
            
            qtd_itens = driver.find_element(By.XPATH, '//*[@id="rodape_itens_pedido_js"]/div[1]/div[1]/div[2]/strong').text.replace('.','')
            qtd_total = driver.find_element(By.XPATH, '//*[@id="rodape_itens_pedido_js"]/div[1]/div[2]/div[2]/strong').text.replace('.','')
            valor_pedido = driver.find_element(By.CLASS_NAME, 'rodape-valor-total').text
            cond_pagamento = driver.find_element(By.XPATH, '//*[@id="informacoes_complementares"]/div/div/div[2]/div[1]/div/div[2]').text
            transportadora_mercos = driver.find_element(By.XPATH, '//*[@id="informacoes_complementares"]/div/div/div[3]/div[2]/div/div[2]').text

            fantasia = driver.find_element(By.XPATH, '//*[@id="selecionado_autocomplete_id_codigo_cliente"]/span/div/div[1]/div[1]/h5/a').text
            vendedor = driver.find_element(By.XPATH, '//*[@id="informacoes_complementares"]/div/div/div[1]/div[4]/div/div[2]').text
            extrai_data = driver.find_element(By.XPATH, '//*[@id="informacoes_complementares"]/div/div/div[1]/div[2]/div/div[2]').text
            data_pedido = datetime.strptime(extrai_data, "%d/%m/%Y").date().isoformat()
            boleto = False
            transportadora = transportadoras(transportadora_mercos)

            html = driver.page_source
            with open(f"novos_pedidos\\{item}.html", "w", encoding="utf-8") as file:
                file.write(html)
            file_path = f"novos_pedidos\\{item}.html"
            df = pd.read_html(
                file_path, attrs={"id": "tabela_itens_pedido"}
            )[0].drop(columns=["Foto", "Desc. Acrés.", "Preço Tab."]).drop_duplicates(keep=False)

            df = df[df['Código'].str.startswith('ZLM', na=False)][['Código', 'Descrição', 'Qtde.']].sort_values(by="Código")
            # print(df)

            if not df.empty:
                linhas = []
                for i in df.itertuples():
                    linhas.append(f"{i[1]} - {i[2]} - {i[3]}")
                progresso = "FITAS DA FÁBRICA"
            else:
                print("Sem itens da fábrica")
                progresso = "EM ANÁLISE"

            time = equipe(vendedor)
            if ('/' in cond_pagamento) or (cond_pagamento in tipos_boleto):
                boleto = True
            if ':' in  transportadora_mercos:
                nome_excursao = transportadora_mercos
            else:
                nome_excursao = False
            valor_separado = valor_pedido.split()[1].replace('.','').replace(',','.')
            decimal = Decimal(valor_separado)
            valor_ajustado = float(decimal)
            resposta = cria_pedido(item, qtd_itens, qtd_total, boleto, transportadora, fantasia, vendedor, link_mercos, data_pedido, nome_excursao, time, valor_ajustado, progresso)
            if not df.empty:
                # print(resposta.json())
                page_id = resposta.json()["id"]
                cria_bloco(page_id, linhas)
            print(f"Pedido {item} | Quantidade de itens: {qtd_itens} | Quantidade Total: {qtd_total} | Valor: {valor_pedido} | Pagamento: {cond_pagamento} | Cliente: {fantasia} | Vendedor: {vendedor} | Data: {data_pedido}" )
            print(link_mercos)
            driver.close()
            driver.switch_to.window(original_window_handle)
        else:
            print(f"Pedido {item} já está nos pedidos")

print('Não Faturados - Primeira Busca')
nao_faturados = busca_pedidos()
driver.close()

root = tk.Tk()
root.withdraw()
root.attributes('-topmost', 1) 

# Display the popup window
messagebox.showinfo("Notion", "Pedidos adicionados", parent=root)
root.destroy()