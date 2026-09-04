import requests
import html
import json
import time
import unicodedata
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv("credentials.env")
app_key = os.getenv("APP_KEY")
app_secret = os.getenv("APP_SECRET")

def atualiza_clientes():
    pagina = 1
    clientes = requisita_clientes(pagina)
    # print(clientes.status_code)
    total_paginas = clientes.json()['total_de_paginas']
    base_clientes = {}
    while pagina <= total_paginas:
        pct = (pagina/total_paginas)*100
        print(f"\rAtualizando clientes | Página: {pagina} de {total_paginas}| {pct:.2f}%", end="", flush=True)
        if pagina == 1:
            time.sleep(61)
        clientes = requisita_clientes(pagina)
        for cliente in clientes.json()['clientes_cadastro']:
            codigo = cliente['codigo_cliente_omie']
            razao_social = html.unescape(cliente['razao_social'])
            fantasia = html.unescape(cliente['nome_fantasia']).upper()
            cnpj_cpf = html.unescape(cliente['cnpj_cpf'])
            try:
                email = cliente['email']
            except:
                email = 'na'
            base_clientes[cnpj_cpf]={"codigo":codigo, "razao_social":razao_social, "email":email, "fantasia":fantasia}
        pagina+=1
            # print(codigo, ' - ', razao_social , ' - ', fantasia, ' - ', email)
    with open("clientes.json", "w", encoding="utf-8") as file:
        json.dump(base_clientes, file, ensure_ascii=False, indent=4)
    return 'Base atualizada'

def atualiza_produtos():
    pagina = 1
    produtos = requisita_produtos(pagina)
    # print(produtos.status_code)
    total_paginas = produtos.json()['total_de_paginas']
    base_produtos = {}
    i = 1
    while pagina <= total_paginas:
        pct = (pagina/total_paginas)*100
        print(f"\rAtualizando produtos | Página: {pagina} de {total_paginas}| {pct:.2f}%", end="", flush=True)
        if pagina == 1:
            time.sleep(61)
        try:
            produtos = requisita_produtos(pagina)
            for produto in produtos.json()['produto_servico_resumido']:
                codigo_mercos = produto['codigo'].replace("\t", "")
                codigo_omie = produto['codigo_produto']
                descricao = produto['descricao']
                base_produtos[codigo_mercos]={"codigo_omie":codigo_omie, "descricao":descricao}
                i+=1
            pagina+=1
        except:
            print(f"Erro na pagina: {pagina}")
            time.sleep(61)
            continue
            # print(codigo, ' - ', razao_social , ' - ', fantasia, ' - ', email)
    with open("produtos.json", "w", encoding="utf-8") as file:
        json.dump(base_produtos, file, indent=4)
    return "Base produtos atualizada"

def atualiza_parcelas():
    pagina = 1
    parcelas = consulta_parcela(pagina)
    # print(parcelas.status_code)
    total_paginas = parcelas.json()['total_de_paginas']
    base_parcelas = {}
    i = 1
    while pagina <= total_paginas:
        pct = (pagina/total_paginas)*100
        print(f"\rAtualizando parcelas | Página: {pagina} de {total_paginas}| {pct:.2f}%", end="", flush=True)
        if pagina == 1:
            time.sleep(61)
        try:
            parcelas = consulta_parcela(pagina)
            for parcela in parcelas.json()['cadastros']:
                descricao = parcela['cDescricao']
                codigo = parcela['nCodigo']
                num_parcelas = parcela['nParcelas']
                base_parcelas[descricao]={"codigo":codigo, "num_parcelas":num_parcelas}
                i+=1
            pagina+=1
        except:
            print(f"Erro na pagina: {pagina}")
            time.sleep(61)
            continue
            # print(codigo, ' - ', razao_social , ' - ', fantasia, ' - ', email)
    with open("parcelas.json", "w", encoding="utf-8") as file:
        json.dump(base_parcelas, file, indent=4)
    return "Base parcelas atualizada"

def requisita_clientes(pagina):
    url = 'https://app.omie.com.br/api/v1/geral/clientes/'

    headers = {
        'Content-type': 'application/json',
    }

    json_data = {
        'call': 'ListarClientes',
        'param': [
            {
                'pagina': pagina,
                'registros_por_pagina': 100,
                'apenas_importado_api': 'N',
            },
        ],
        'app_key': app_key,
        'app_secret': app_secret,
    }

    clientes = requests.post(url, headers=headers, json=json_data)
    return clientes

def requisita_produtos(pagina):
    url = 'https://app.omie.com.br/api/v1/geral/produtos/'

    headers = {
        'Content-type': 'application/json',
    }

    json_data = {
        'call': 'ListarProdutosResumido',
        'param': [
            {
                'pagina': pagina,
                'registros_por_pagina': 100,
                'apenas_importado_api': 'N',
                'filtrar_apenas_omiepdv': "N"
            },
        ],
        'app_key': app_key,
        'app_secret': app_secret,
    }
    produtos = requests.post(url, headers=headers, json=json_data)
    return produtos

def consulta_parcela(pagina):
    url = 'https://app.omie.com.br/api/v1/geral/parcelas/'

    headers = {
            'Content-type': 'application/json',
        }
    
    json_data = {
        'call': 'ListarParcelas',
        'param': [
            {
                "pagina": pagina,
                "registros_por_pagina": 100
            }
        ],
        'app_key': app_key,
        'app_secret': app_secret,
    }

    parcelas = requests.post(url, headers=headers, json=json_data)
    # print(parcelas.json())
    return parcelas

def cadastra_clientes():
    df = pd.read_excel("clientes_mercos.xls")
    not_found = []
    keys = []
    with open("clientes.json", "r", encoding="utf-8") as file:
        base = json.load(file)
        
    for k in base.keys():
        texto_normalizado = unicodedata.normalize("NFD", k.lower().strip())
        texto_sem_acento = "".join(
            c for c in texto_normalizado if unicodedata.category(c) != "Mn"
        )
        keys.append(texto_sem_acento)

    for cliente in df["Nome fantasia"]:
        texto_normalizado = unicodedata.normalize("NFD", cliente.lower().strip())
        texto_sem_acento = "".join(
            c for c in texto_normalizado if unicodedata.category(c) != "Mn"
        )
        if texto_sem_acento not in keys:
            not_found.append(texto_sem_acento)
    print(not_found)
    print(len(not_found))
    # with open("cadastrar.txt", "w") as file:
    #     for i in not_found:
    #         file.write(f"{i}\n")


    print(df.head())
    pass

if __name__=='__main__':
    pass
    atualiza_produtos()
    atualiza_parcelas()
    atualiza_clientes()
    # cadastra_clientes()


