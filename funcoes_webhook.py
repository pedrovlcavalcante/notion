import pyautogui
import xml.etree.ElementTree as ET
import requests
import os
import time
import queue
from decimal import Decimal

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from notion import login_mercus, seta_nf, id_pedido_notion, atualiza_dados_faturamento, equipe
from dependencias import selenium_esta_rodando

fila_tarefas = queue.Queue()


def dados_atualizados_pedido(driver):
    qtd_itens = driver.find_element(By.XPATH, '//*[@id="rodape_itens_pedido_js"]/div[1]/div[1]/div[2]/strong').text.replace('.','')
    qtd_total = driver.find_element(By.XPATH, '//*[@id="rodape_itens_pedido_js"]/div[1]/div[2]/div[2]/strong').text.replace('.','')
    valor_pedido = driver.find_element(By.CLASS_NAME, 'rodape-valor-total').text
    link_mercos = driver.current_url
    vendedor = driver.find_element(By.XPATH, '//*[@id="informacoes_complementares"]/div/div/div[1]/div[4]/div/div[2]').text
    time = equipe(vendedor)
    valor_separado = valor_pedido.split()[1].replace('.','').replace(',','.')
    decimal = Decimal(valor_separado)
    valor_ajustado = float(decimal)
    return (qtd_itens, qtd_total, valor_ajustado, link_mercos, vendedor, time)

def download_danfe(danfe_url, numero_nf, pedido):
    url = danfe_url

    output_filename = f"nota_fiscal_saida_{numero_nf}_pedido_{pedido}.pdf" #nota_fiscal_saida_{numero_nf}_pedido_{pedido}.pdf
    output_dir = "C:\\Users\\Lomil Etiquetas\\Desktop\\NFS"
    file_path = os.path.join(output_dir, output_filename)
    # 1. Send an HTTP GET request to the URL
    response = requests.get(url, allow_redirects=True)

    # 2. Check if the request was successful
    if response.status_code == 200:
        # 3. Open a local file in 'wb' (write binary) mode and save the content
        with open(file_path, "wb") as pdf_file:
            pdf_file.write(response.content)
        print("Download complete!")
    else:
        print(f"Failed to download. Status code: {response.status_code}")
    return file_path

def download_xml(xml_url, numero_nf, pedido):
    url = xml_url

    output_filename = f"xml_{numero_nf}_pedido_{pedido}.xml"
    output_dir = "C:\\Users\\Lomil Etiquetas\\Desktop/XML"
    file_path = os.path.join(output_dir, output_filename)
    # 1. Send an HTTP GET request to the URL
    response = requests.get(url, allow_redirects=True)

    # 2. Check if the request was successful
    if response.status_code == 200:
        # 3. Open a local file in 'wb' (write binary) mode and save the content
        with open(file_path, "wb") as xml_file:
            xml_file.write(response.content)
        print("Download complete!")
    else:
        print(f"Failed to download. Status code: {response.status_code}")

def pega_pedido_xml(url_xml):
    # url_xml = 'https://cdn.omie.com.br/repository/897035c99c49512b4b40dbcb0d23ed10/d9ece551c0ccca3a1b7ec200e5cdc2bd/23260731161476000138550010000121441651542055-procNFe.xml?response-content-type=application%2Foctet-stream&AWSAccessKeyId=AKIA4INFFOTW64RNC5N7&Expires=1784817399&Signature=mdNP%2Fr1uFTnXfTBWRIr6l%2Fgpfco%3D'

    xml = requests.get(url_xml).text
    # 1. Parse the XML file
    root = ET.fromstring(xml)
    # root = tree.getroot()
    info = root[0][0]
    ide = info.find("{http://www.portalfiscal.inf.br/nfe}ide")
    nat_op = ide.find("{http://www.portalfiscal.inf.br/nfe}natOp").text
    if nat_op == "Remessa em Bonificacao, Doacao ou Brinde":
        return nat_op
    else:
        compra = info.find("{http://www.portalfiscal.inf.br/nfe}compra")
        pedido_nf = compra.find("{http://www.portalfiscal.inf.br/nfe}xPed").text
        transp = info.find("{http://www.portalfiscal.inf.br/nfe}transp")
        mod_frete = transp.find("{http://www.portalfiscal.inf.br/nfe}modFrete").text
        return (pedido_nf, mod_frete)

def upload_danfe(dados):
    numero_nf = dados['event']['numero_nf']
    xml = dados['event']['nfe_xml']
    info_pedido = pega_pedido_xml(xml)
    if type(info_pedido) == str:
        return
    pedido = info_pedido[0]
    output_filename = f"nota_fiscal_saida_{numero_nf}_pedido_{pedido}.pdf"
    output_dir = "C:\\Users\\Lomil Etiquetas\\Desktop\\NFS"
    file = os.path.join(output_dir, output_filename)

    chrome_options = Options()
    
    # Add the experimental "detach" option
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--headless=new")
    with webdriver.Chrome(options=chrome_options) as driver:
    
        driver.get("https://app.mercos.com/384882/pedidos/")
        login_mercus(driver)

        # Pesquisa o pedido
        try:
            caixa = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="id_texto"]'))
            )
            caixa.send_keys(pedido, Keys.ENTER)
            print(f"Pesquisando pedido {pedido}")
        except Exception as e:
            print("Não foi possivel localizar o pedido", e)


        try:
            pagina_pedido = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'numero-pedido'))
            )
            pagina_pedido.click()
            print(f"Pagina do pedido {pedido} clicada")
        except Exception as e:
            print(f"Pagina do pedido não pode ser clicada", e)


        # 1. Caminho absoluto do arquivo
        file_path = os.path.abspath(file)
        try:
            btn_drop = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="outras_opcoes"]/a'))
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", btn_drop)
            btn_drop.click()
            print("Botão drop localizado e clicado")
        except Exception as e:
            print("Não foi possivel localizar ou clicar no botão drop", e)

        try:
            btn_anexar = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "btn_anexar"))
            )
            btn_anexar.click()
            print("Botão anexar localixado e clicado")
        except Exception as e:
            print("Botão anexar nao localizado ou não clicado", e)

        try:
            # 3. CORREÇÃO: Busca por By.ID para bater com o id criado no JavaScript
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.NAME, "arquivo"))
            )
            print("Input localizado")

            # 4. Força o pai (a DIV oculta) a ficar visível para o Selenium não travar
            div_pai = file_input.find_element(By.XPATH, "..")
            driver.execute_script(
                "arguments[0].style.visibility = 'visible'; arguments[0].style.opacity = '1';", 
                div_pai
            )
            print("DIV pai tornada visivel")
        except Exception as e:
            print("Falhou aqui", e)

        try:
            # 5. Envia o arquivo
            file_input.send_keys(file_path)
            time.sleep(3)
            pyautogui.press('escape') 
            # driver.quit()
            print(f"Upload da nf do pedido {pedido} completa")
        except Exception as e:
            print("Excessão do upload", e)

        try:
            dados_atualizados = dados_atualizados_pedido(driver)
            print("Dados atualizados do pedido capturadas", dados_atualizados)
            id_pedido = id_pedido_notion(pedido)[0]
            atualiza_dados_faturamento(id_pedido, dados_atualizados)
            driver.quit()
        except Exception as e:
            print("Erro na atualização dos dados do pedido ", e)

def imprime_nf(file):
    os.startfile(file, "print")

def trabalhador_fila(fila_tarefas=fila_tarefas):
    while True:
        # Fica bloqueado aqui até que surja algo na fila
        dados = fila_tarefas.get()
        
        try:            
            # Executa o upload (se precisar ser sequencial também)
            while selenium_esta_rodando():
                for i in range(4):
                    pontos = "." * i
                    time.sleep(0.2)
                    print(f"\rAguardando vez para acessar a pagina{pontos:<3}", end="", flush=True)
            upload_danfe(dados)
        except Exception as e:
            print(f"Erro ao processar dados: {e}")
        
        finally:
            # Sinaliza que a tarefa atual terminou, liberando para a próxima
            fila_tarefas.task_done()
            
def processar_dados_webhook(dados):
    try:
        danfe = dados['event']['nfe_danfe']
        xml = dados['event']['nfe_xml']
        numero_nf = dados['event']['numero_nf']
        
        info_pedido = pega_pedido_xml(xml)
        if info_pedido == "Remessa em Bonificacao, Doacao ou Brinde":
            file_path = download_danfe(danfe, numero_nf, pedido="bonificação")
            download_xml(xml, numero_nf, pedido="bonificação")
            imprime_nf(file_path)
            return
        pedido = info_pedido[0]
        mod_frete = info_pedido[1]

        file_path = download_danfe(danfe, numero_nf, pedido)
        download_xml(xml, numero_nf, pedido)
        
        
        id_pedido, transportadora = id_pedido_notion(pedido)
        seta_nf(id_pedido, numero_nf)
        
        print("Caminho: ", file_path)
        print("Modalidade: ", mod_frete)
        print("Pedido: ", pedido, " - NF: ", numero_nf)
        
        if mod_frete == '0' or transportadora == 'EXCURSÃO':
            imprime_nf(file_path)
            print(f"Processo de impresssão do pedido {pedido}!")
            
        # O upload via Selenium que consome tempo roda isolado aqui
        # upload_danfe(file=file_path, pedido=pedido)
        # print(f"Processamento concluído com sucesso para o pedido {pedido}!")
        
    except Exception as e:
        print(f"Erro ao processar o webhook em segundo plano: {e}")