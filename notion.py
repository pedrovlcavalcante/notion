import os
import requests

from dotenv import load_dotenv
from datetime import datetime, timedelta

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Carrega segredos
load_dotenv('credentials.env')
data_source_id = os.getenv('SOURCE')
token = os.getenv('TOKEN')
mercos_user = os.getenv('MERCUS_USER')
mercos_password = os.getenv('MERCUS_PASSWORD')

nomes = {}
def equipe(vendedor):
    equipe_elano = ['Alexandre Lima', 'Bernardo', 'Claudiano Ferreira', 'Diana Jaqueline', 
                    'Elano Dias', 'Elisângela Damasceno Silva', 'Gabriel Mota Façanha', 'Kelly Nobre', 'Nara Alexandre', 'Rita de Cássia', 'Wesley Ribeiro', 'Wiler Bastos']
    equipe_junior = ['Catarina Rocha', 'Erica Alencar', 'Junior Salu', 'Léo Rodrigues', 'Marcelo Gomes', 'Marcos Morais', 'Reinaldo', 'Thays Barbosa', 'Venda Interna (Catarina)', 'Venda Interna Marcelo']
    equipe_raphael = ['Claudinei Ferreira', 'Claysson (MARCIA)', 'Débora Picinin (SP)', 'Diego Carlos', 'Henrique dos Santos', 'Juliana Estrela', 'Marcia Andreia', 'Raphael Vasconcelos' ]
    if vendedor in equipe_elano:
        return "ELANO"
    elif vendedor in equipe_junior:
        return "JUNIOR"
    elif vendedor in equipe_raphael:
        return "RAPHAEL"
    elif vendedor == "Renatta Oliveira":
        return "PAULO"
    else:
        return "SEM EQUIPE"

def transportadoras(transportadora):
    match transportadora:
        case 'SEM FRETE'|'AEROPRESS'|'BOMFIM'|'BRASPRESS'|'CB EXPRESS'|'CORREIOS'|'ENTREGA'|'RETIRADA'|'EXPRESS FORTALEZA'|'J&T EXPRESS'|'LATAM'|'NOVO AMANHECER'|'P/ SÃO PAULO'|'RCA'|'TODO BRASIL'|'TRANSCEARA'|'TRANSPOTYGUAR'|'EXCURSÃO'|'JADLOG':
            return transportadora
        case 'REDESPACHO DE SP':
            return 'P/ SÃO PAULO'
        case _:
            if 'EXCURSÃO' in transportadora:
                return 'EXCURSÃO'
            else:
                return 'A DECIDIR'

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

def login_mercus(driver, login=mercos_user, senha=mercos_password):
    elem = driver.find_element(By.NAME, "usuario")
    elem.send_keys(login)
    elem = driver.find_element(By.NAME, "senha")
    elem.send_keys(senha)
    elem.submit()

def consulta_titles(data, proximo, source=data_source_id):
    url = f"https://api.notion.com/v1/data_sources/{source}/query?"
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
        "filter":
            {
                "timestamp":"created_time",
                "created_time":{"on_or_after":data}
            },
        "start_cursor":proximo
    }
    if not proximo:
        payload.pop("start_cursor")
    titles = requests.post(url, headers=headers, json=payload)
    return titles

def consulta_boletos(source=data_source_id):
    url = f"https://api.notion.com/v1/data_sources/{source}/query"
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }
    payload = {
    "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
    "filter": { "and": [
            {
                "property":"BOLETO",
                "type":"select",
                "select":{"equals":"BOLETO"}
            },
            {
                "property":"PROGRESSO",
                "type":"status",
                "status":{"does_not_equal":"AGUARDANDO COLETA"}
            },
            {
                "property":"PROGRESSO",
                "type":"status",
                "status":{"does_not_equal":"COLETADO"}
            },
            {
                "property":"PROGRESSO",
                "type":"status",
                "status":{"does_not_equal":"CANCELADO"}
            },
            {
                "property":"PROGRESSO",
                "type":"status",
                "status":{"does_not_equal":"CONCLUÍDO"}
            },
      ] },
    'page_size':500
    }
    boletos = requests.post(url, headers=headers, json=payload)
    return boletos

def consulta_em_analise(source=data_source_id):
    url = f"https://api.notion.com/v1/data_sources/{source}/query"
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }
    payload = {
    "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
    "filter": { "or": [
            {
                "property":"PROGRESSO",
                "type":"status",
                "status":{"equals":"EM ANÁLISE"}
            }
      ] },
    'page_size':500
    }
    em_analise = requests.post(url, headers=headers, json=payload)
    return em_analise

def procura(pedido):
    url = 'https://api.notion.com/v1/search'
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }
    payload = {
    "query": f"{pedido}",
    'page_size':500
    }
    pesquisa = requests.post(url, headers=headers, json=payload)

    return pesquisa

def cria_pedido(pedido, itens, quantidade, boleto, transportadora, cliente, vendedor, link_mercos, data_pedido, nome_excursao, equipe, valor, progresso, source=data_source_id):
    url = 'https://api.notion.com/v1/pages'
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "parent":{
            "data_source_id": source,
            "type":"data_source_id"
        },
        "properties": {
            "Nome": {
                    "title": [
                { "text": { "content": f"{pedido}" } }
                ]
            },
            "PROGRESSO": {
                "status":{"name": progresso}
            },
            "ITENS NO PEDIDO": {
                "id": "MiZy",
                "type":"number",
                "number": int(itens)
            },
            "QUANTIDADE TOTAL DE ITENS": {
                "id": "wTpu",
                "type":"number",
                "number": int(quantidade),
            },
            "BOLETO":{
                "type": "select",
                "select": {"id": "2d27d6c8-e9e8-48f7-818c-5055cb418929"},
            },
            "TRANSPORTADORA":{
                "type":"select",
                "select":{
                    "name":transportadora
                }
            },
            "CLIENTE":{
                "type":"rich_text",
                "rich_text":[{
                    "text":{"content":cliente}
                }]
            },
            "EXCURSÃO":{
                "type":"rich_text",
                "rich_text":[{
                    "text":{"content":nome_excursao}
                }]
            },
            "VENDEDOR":{
                "type":"rich_text",
                "rich_text":[{
                    "text":{"content":vendedor}
                }]
            },
            "LINK":{
                "type":"url",
                "url":link_mercos
            },
            "DATA DO PEDIDO":{
                "date":{
                    "start":data_pedido
                }
            },
            "EQUIPE":{
                "type":"rich_text",
                "rich_text":[{
                    "text":{"content":equipe}
                }]
            },
            "VALOR":{
                "type":"number",
                "number":valor
                }      
            }
        }
    if not boleto:
        payload["properties"].pop("BOLETO")
    if not nome_excursao:
        payload["properties"].pop("EXCURSÃO")
    novo_pedido = requests.post(url, headers=headers, json=payload)
    if novo_pedido.status_code == 400:
        print("Erro ao criar pedido")
        print(novo_pedido.json())
        return novo_pedido
    else:
        print(f"Pedido {pedido} criado com sucesso")
        return novo_pedido

def cria_bloco(page_id, linhas):
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }

    children = []
    if len(linhas) > 100:
        children = [{"bulleted_list_item":{"rich_text":[{"text":{"content":"+100 ITENS: VER NO PEDIDO"}}]}}]
    else:
        for linha in linhas: 
            children.append({"bulleted_list_item":{"rich_text":[{"text":{"content":linha}}]}})

    payload = {
    "children":children,
    "position":{
        "type":"start"
    }
    }
    conteudo = requests.patch(url, headers=headers, json=payload)
    if conteudo.status_code == 400:
        print("Erro ao criar pedido")
        print(conteudo.json())
        return conteudo
    else:
        print(f"Conteudo criado com sucesso")
        # print(conteudo.json())
        return conteudo

def coletados(data, source=data_source_id):
    dia = datetime.strptime(data, "%d/%m/%Y")
    dia_seguinte = dia + timedelta(days=1)

    url = f"https://api.notion.com/v1/data_sources/{source}/query?filter_properties[]=title&filter_properties[]=DATA DE COLETA&filter_properties[]=VENDEDOR&filter_properties[]=VOLUMES&filter_properties[]=EQUIPE"
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
        "filter":{ "and":[
            {
                "property":"DATA DE COLETA",
                "date":{"on_or_after":dia.isoformat()},
                "type":"date",
            },
            {
                "property":"DATA DE COLETA",
                "date":{"before":dia_seguinte.isoformat()},
                "type":"date",
            }
        ]
                
            }     
        }
    titles = requests.post(url, headers=headers, json=payload)
    return titles

def equipe(vendedor):
    equipe_elano = ['Alexandre', 'Bernardo', 'Claudiano', 'Elisângela Damasceno Silva', 'Elton Reury', 'Gabriel Mota Façanha', 'Kelly Nobre', 'Nara Alexandre', 'Rita de Cássia', 'Wiler Bastos']
    equipe_junior = ['Thays Barbosa','Carlos Eduardo', 'Catarina Rocha', 'Erica Alencar', 'Léo Rodrigues', 'Marcelo Gomes', 'Marcos Morais', 'Reinaldo', 'Venda Interna (Catarina)', 'Venda Interna Marcelo']
    equipe_raphael = ['Claudinei Ferreira', 'Débora Picinin (SP)', 'Henrique dos Santos', 'Juliana Estrela', 'Marcia Andreia']
    if vendedor in equipe_elano:
        return "ELANO"
    elif vendedor in equipe_junior:
        return "JUNIOR"
    elif vendedor in equipe_raphael:
        return "RAPHAEL"
    elif vendedor == "Renatta Oliveira":
        return "PAULO"
    else:
        return "SEM EQUIPE"

def atualiza_pedidos(num_pedido, id, equipe, vendedor, cliente, itens, qtd_total, valor, link):
    print(f"Atualizando Pedido {num_pedido} - Vendedor: {vendedor} - Equipe: {equipe} - Cliente: {cliente}")
    url = f"https://api.notion.com/v1/pages/{id}"

    payload = {
        "properties":{
            "EQUIPE":{"rich_text":[{"text":{"content":equipe}}]},
            "VENDEDOR":{"rich_text":[{"text":{"content":vendedor}}]},
            "CLIENTE":{"rich_text":[{"text":{"content":cliente}}]},
            "ITENS NO PEDIDO":{"number":{itens}},
            "QUANTIDADE TOTA DE ITENS":{"number":{qtd_total}},
            "VALOR":{"number":{valor}},
            "LINK":{"url":{link}}
        }
    }

    headers = {
            "Notion-Version": "2026-03-11",
            "Authorization": f"Bearer {token}",
        }
    
    atualizados = requests.patch(url, headers=headers, json=payload)
    if atualizados.status_code == 200:
        print(f"Pedido {num_pedido} atualizado com sucesso")
    else:
        print(f"Não foi possível atualizar o Pedido {num_pedido}")
        print(atualizados.json())
    return atualizados

def rodar_atualização():
    # chrome_options = Options()

    # # Add the experimental "detach" option
    # chrome_options.add_experimental_option("detach", True)
    # # chrome_options.add_argument("--headless=new")
    # # Initialize the WebDriver with the specified options
    # driver = webdriver.Chrome(options=chrome_options)

    # base_url = 'https://app.mercos.com/384882/'
    # url_faturados = 'relatorios/pedidos_faturados/'
    # url_pesquisa = base_url+url_faturados

    # mes = datetime.today().month
    # data_inicial = datetime(2026, mes, 1)
    # periodo_incial = datetime.strftime(data_inicial, "%d/%m/%Y")
    # periodo_final = "31/07/2026"

    # params = {'ajax':1, 'ordem':'asc', 'periodo_final':f'{periodo_final}', 'periodo_inicial':f'{periodo_incial}', 'status_pedido':'2', 'tipo_de_pedido':'-1', 'valor_ordenacao':'data_emissao'}
    # url = f"{url_pesquisa}?{urlencode(params)}"
    # driver.get(url)

    # login_mercus(driver, mercos_user, mercos_password)

    # pedidos_mercos = busca_pedidos()
    # print(pedidos_mercos)
    import pandas as pd

    itens = {}
    merc = pd.read_excel("ATUALIZA.xls")
    for pedido_mercos in merc.values:
        # print(pedido)
        itens[str(pedido_mercos[0])] = {"Cliente":pedido_mercos[1], "Vendedor":pedido_mercos[2], "Itens":pedido_mercos[3], "Quantidade":pedido_mercos[4], "Valor":pedido_mercos[5], "Link":pedido_mercos[6]}
    print(itens)
    
    proximo = False
    data = datetime(2026,7,1).date().isoformat()

    # titulos = consulta_titles(data_source_id, data, proximo).json()
    # print(len(titulos['results']))

    tem_mais = True
    # if tem_mais:
    #     proximo = titulos['next_cursor']
    i=1

    while tem_mais:
        titulos = consulta_titles(data, proximo).json()
        # print(titulos)
        for titulo in titulos['results']:
            try:
                pedido = titulo['properties']['Nome']['title'][0]['text']['content']
                pedido_id = titulo['id']
                vendedor = itens[pedido]["Vendedor"]
                cliente = itens[pedido]["Cliente"]
                q_itens = itens[pedido]["Itens"]
                quantidade = itens[pedido]["Quantidade"]
                valor = itens[pedido]["Valor"]
                link = itens[pedido]["Link"]
                grupo = equipe(vendedor)
                atualiza_pedidos(pedido, pedido_id, grupo, vendedor, cliente, q_itens, quantidade, valor, link)
                # print(pedido, ' - id:', pedido_id)
                # print(prx_pagina['results']['properties']['Nome']['title'][0]['text']['content'], ' - id:', titulo['id'])
            except:
                continue
        proximo = titulos['next_cursor']
        tem_mais = titulos['has_more']
        print(len(titulos['results']))
        print(f"pagina {i}")
        i += 1

def seleciona_pedidos(data_atual, data_futura, source=data_source_id, pagina=None):
    url = f"https://api.notion.com/v1/data_sources/{source}/query"
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }
    payload = {
    "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
    "filter": { "and": [
            {
                "property":"1º CONFERENTE",
                "type":"select",
                "select":{"is_not_empty":True}
            },
            {
                "timestamp":"created_time",
                "created_time":{"on_or_after":data_atual}
            },
            {
                "timestamp":"created_time",
                "created_time":{"before":data_futura}
            }
      ] },
    'start_cursor': pagina,
    'page_size':500
    }
    if pagina == None:
        payload.pop('start_cursor')
    conferente = requests.post(url, headers=headers, json=payload)
    return conferente

def seta_nf(id, nf):
    url = f"https://api.notion.com/v1/pages/{id}"

    payload = {
        "properties":{
            "NF":{"rich_text":[{"text":{"content":nf}}]},
        }
    }

    headers = {
            "Notion-Version": "2026-03-11",
            "Authorization": f'Bearer {token}',
        }
    
    atualizados = requests.patch(url, headers=headers, json=payload)
    if atualizados.status_code == 200:
        print(f"Pedido atualizado com sucesso")
    else:
        print(f"Não foi possível atualizar o Pedido")
        print(atualizados.json())
    return atualizados

def atualiza_dados_faturamento(id, dados_atualizados):
    url = f"https://api.notion.com/v1/pages/{id}"
    qtd_itens, qtd_total, valor_pedido, link_mercos, vendedor, time = dados_atualizados
    payload = {
        "properties":{
            "ITENS NO PEDIDO": {
                "id": "MiZy",
                "type":"number",
                "number": int(qtd_itens),
            },
            "QUANTIDADE TOTAL DE ITENS": {
                "id": "wTpu",
                "type":"number",
                "number": int(qtd_total),
            },
            "VALOR":{
                "type":"number",
                "number": valor_pedido
            },
            "LINK":{
                "type":"url",
                "url": link_mercos
            },
            "VENDEDOR":{
                "type":"rich_text",
                "rich_text":[{
                    "text":{"content":vendedor}
                }]
            },
            "EQUIPE":{
                "type":"rich_text",
                "rich_text":[{
                    "text":{"content":time}
                }]
            }
        }
    }
    headers = {
            "Notion-Version": "2026-03-11",
            "Authorization": f'Bearer {token}',
        }
    
    atualizados = requests.patch(url, headers=headers, json=payload)
    if atualizados.status_code == 200:
        print(f"Pedido atualizado com sucesso")
    else:
        print(f"Não foi possível atualizar o Pedido")
        print(atualizados.json())
    return atualizados

def id_pedido_notion(pedido):
    url = 'https://api.notion.com/v1/search'
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f'Bearer {token}',
    }
    payload = {
    # "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
    "query": f"{pedido}",
    'page_size':500
    }

    id_pedido = requests.post(url, headers=headers, json=payload).json()['results'][0]['id']
    transportadora = requests.post(url, headers=headers, json=payload).json()['results'][0]['properties']['TRANSPORTADORA']['select']['name']
    return (id_pedido, transportadora)

if __name__=="__main__":
    # rodar_atualização()
    pass