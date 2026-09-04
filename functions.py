from dotenv import load_dotenv
import os
import requests
import win32print
import win32ui
import pdfplumber
from PIL import ImageWin

import xml.etree.ElementTree as ET

local_filename = 'C:\\Users\\Lomil Etiquetas\\Desktop\\NFS\\nota_fiscal_saida_00012166.pdf'

def print_pdf_to_default_printer(pdf_path):
    """Renders PDF pages and sends them directly to the Windows printer."""
    print("Sending document to default printer...")

    # Get the default system printer name
    printer_name = win32print.GetDefaultPrinter()

    # Open the printer and start a print job
    h_printer = win32print.OpenPrinter(printer_name)
    try:
        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer_name)

        # Open the PDF file
        with pdfplumber.open(pdf_path) as pdf:
            # Start the print job container
            hdc.StartDoc("Python PDF Print Job")

            for page_num, page in enumerate(pdf.pages):
                hdc.StartPage()

                # Convert PDF page to a high-res PIL Image object
                pil_image = page.to_image(resolution=200).original

                # Calculate scale mapping to match printer dimensions
                printer_width = hdc.GetDeviceCaps(110)  # PHYSICALWIDTH
                printer_height = hdc.GetDeviceCaps(111)  # PHYSICALHEIGHT

                # Maintain aspect ratio
                img_width, img_height = pil_image.size
                ratio = min(printer_width / img_width, printer_height / img_height)
                new_width = int(img_width * ratio)
                new_height = int(img_height * ratio)

                # Draw the image onto the printer device context
                dib = ImageWin.Dib(pil_image)
                dib.draw(hdc.GetHandleDC(), (0, 0, new_width, new_height))

                hdc.EndPage()

            hdc.EndDoc()
            print(f"Successfully sent to: {printer_name}")

    finally:
        win32print.ClosePrinter(h_printer)



def imprime_nf(file):
    os.startfile(file, "print")

load_dotenv('credentials.env')
data_source_id = os.getenv('SOURCE')
token = os.getenv('TOKEN')
base = os.getenv('BASE')

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

def cria_pedido(pedido, valor, source=data_source_id):
    url = 'https://api.notion.com/v1/pages'
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": token,
    }
    payload = {
        "parent":{
            "data_source_id": source,
            "type":"data_source_id"
        },
        "properties":{
            "Nome": {
                    "title": [
                { "text": { "content": f"{pedido}" } }
                ]
            },
            "PROGRESSO": {
                "status":{"name": "EM ANÁLISE"}
            },
            "VALOR":{
                    "type":"number",
                    "number":valor
            }
        }
    }
    
    novo_pedido = requests.post(url, headers=headers, json=payload)
    if novo_pedido.status_code == 400:
        print("Erro ao criar pedido")
        print(novo_pedido.json())
        return novo_pedido
    else:
        print(f"Pedido criado com sucesso")
        return novo_pedido

def pega_pedido_xml():
    url_xml = 'https://cdn.omie.com.br/repository/897035c99c49512b4b40dbcb0d23ed10/d9ece551c0ccca3a1b7ec200e5cdc2bd/23260731161476000138550010000121441651542055-procNFe.xml?response-content-type=application%2Foctet-stream&AWSAccessKeyId=AKIA4INFFOTW64RNC5N7&Expires=1784817399&Signature=mdNP%2Fr1uFTnXfTBWRIr6l%2Fgpfco%3D'

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
