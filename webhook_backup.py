from flask import Flask, request, jsonify
from dotenv import load_dotenv
import pyautogui
import xml.etree.ElementTree as ET
import requests
import os
import time
import threading

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from notion import login_mercus

load_dotenv('credentials.env')
data_source_id = os.getenv('SOURCE')
token = os.getenv('TOKEN')

def download_danfe(danfe_url, numero_nf):
    url = danfe_url

    output_filename = f"nota_fiscal_saida_{numero_nf}.pdf"
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

def download_xml(xml_url, numero_nf):
    url = xml_url

    output_filename = f"xml_{numero_nf}.xml"
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
    compra = info.find("{http://www.portalfiscal.inf.br/nfe}compra")
    pedido_nf = compra.find("{http://www.portalfiscal.inf.br/nfe}xPed").text
    transp = info.find("{http://www.portalfiscal.inf.br/nfe}transp")
    mod_frete = transp.find("{http://www.portalfiscal.inf.br/nfe}modFrete").text
    return (pedido_nf, mod_frete)

def id_pedido_notion(pedido, token):
    url = 'https://api.notion.com/v1/search'
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": token,
    }
    payload = {
    # "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
    "query": f"{pedido}",
    'page_size':500
    }

    id_pedido = requests.post(url, headers=headers, json=payload).json()['results'][0]['id']
    return id_pedido

def seta_nf(id, nf, token):
    url = f"https://api.notion.com/v1/pages/{id}"

    payload = {
        "properties":{
            "NF":{"rich_text":[{"text":{"content":nf}}]},
        }
    }

    headers = {
            "Notion-Version": "2026-03-11",
            "Authorization": token,
        }
    
    atualizados = requests.patch(url, headers=headers, json=payload)
    if atualizados.status_code == 200:
        print(f"Pedido atualizado com sucesso")
    else:
        print(f"Não foi possível atualizar o Pedido")
        print(atualizados.json())
    return atualizados

def upload_danfe(file, pedido):
    chrome_options = Options()
    
    # Add the experimental "detach" option
    chrome_options.add_experimental_option("detach", True)
    chrome_options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=chrome_options)
    
    driver.get("https://app.mercos.com/384882/pedidos/")
    login_mercus(driver)

    # Pesquisa o pedido
    caixa = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="id_texto"]'))
    )
    caixa.send_keys(pedido, Keys.ENTER)

    pagina_pedido = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="js-div-global"]/div[1]/section/div[3]/div[1]/div[4]/div[2]/div[1]/div[1]/p/a'))
    )
    pagina_pedido.click()

    # 1. Caminho absoluto do arquivo
    file_path = os.path.abspath(file)

    btn_drop = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, '//*[@id="outras_opcoes"]/a'))
    )
    btn_drop.click()

    btn_anexar = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "btn_anexar"))
    )
    btn_anexar.click()

    # 3. CORREÇÃO: Busca por By.ID para bater com o id criado no JavaScript
    file_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "arquivo"))
    )
    time.sleep(1)
    pyautogui.press('escape') 
    # 4. Força o pai (a DIV oculta) a ficar visível para o Selenium não travar
    div_pai = file_input.find_element(By.XPATH, "..")
    driver.execute_script(
        "arguments[0].style.visibility = 'visible'; arguments[0].style.opacity = '1';", 
        div_pai
    )

    # 5. Envia o arquivo
    file_input.send_keys(file_path)
    driver.quit()

def imprime_nf(file):
    os.startfile(file, "print")


app = Flask(__name__)


def receber_webhook():
    # Pega os dados enviados pelo serviço externo
    dados = request.json
    
    # Exibe os dados no terminal para você visualizar
    print("Dados recebidos:")
    print(dados)

    danfe = dados['event']['nfe_danfe']
    xml = dados['event']['nfe_xml']
    numero_nf = dados['event']['numero_nf'] 
    file_path = download_danfe(danfe, numero_nf)
    download_xml(xml, numero_nf)
    info_pedido = pega_pedido_xml(xml)
    pedido = info_pedido[0]
    mod_frete = info_pedido[1]
    id_pedido = id_pedido_notion(pedido, token)
    seta_nf(id_pedido, numero_nf, token)
    print("Caminho: ", file_path)
    print("Modalidade: ", mod_frete)
    print("Pedido: ", pedido, " - NF: ", numero_nf)
    if mod_frete=='0':
        imprime_nf(file_path)
    if mod_frete=='1':
        pass
    # Retorna uma resposta confirmando o recebimento (status 200)
    upload_danfe(file=file_path, pedido=pedido)
    return jsonify({"status": "sucesso", "mensagem": "Webhook recebido!"}), 200

@app.route('/', methods=['POST'])
def receber_webhook():
    dados = request.json
    print("Webhook recebido no terminal. Respondendo ao servidor externo...")

    # Dispara a função pesada em uma linha de execução paralela (Thread)
    thread = threading.Thread(target=processar_dados_webhook, args=(dados,))
    thread.start()

    # Retorna IMEDIATAMENTE o status 200. O servidor externo para de reenviar!
    return jsonify({"status": "sucesso", "mensagem": "Webhook recebido e em processamento!"}), 200

if __name__ == '__main__':
    # Roda o servidor localmente na porta 5000
    app.run(port=5000, debug=True)
    