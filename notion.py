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
cotacao_id = os.getenv('COTACAO')
clientes = os.getenv('CLIENTES')
token = os.getenv('TOKEN')
mercos_user = os.getenv('MERCUS_USER')
mercos_password = os.getenv('MERCUS_PASSWORD')

nomes = {}

def consulta_volatil(tipo, source):
    pass

def consulta_clientes_incompletos(source=clientes):
    url = f"https://api.notion.com/v1/data_sources/{source}/query"

    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "filter":{
            "property":"CODIGO OMIE",
            "number":{"is_empty":True}
        }
    }
    clientes_incompletos = requests.post(url, headers=headers, json=payload)
    cnpj_lista = []
    for cliente in clientes_incompletos.json()['results']:
        cnpj = cliente['properties']['CNPJ/CPF']['title'][0]['text']['content']
        cnpj_lista.append(cnpj)
    return cnpj_lista

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

def login_mercus(driver, login=mercos_user, senha=mercos_password):
    elem = driver.find_element(By.NAME, "usuario")
    elem.send_keys(login)
    elem = driver.find_element(By.NAME, "senha")
    elem.send_keys(senha)
    elem.submit()

def busca_cliente(cnpj, finalidade='properties', source=clientes):
    url = f"https://api.notion.com/v1/data_sources/{source}/query?"
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
        "filter":
            {
                "property":"CNPJ/CPF",
                "rich_text":{"equals":cnpj}
            },
    }

    cliente = requests.post(url, headers=headers, json=payload)
    if finalidade == 'id':
        try:
            return cliente.json()['results'][0]['id']
        except Exception as e:
            return False
    else:
        return cliente.json()

def propriedade_cliente(page_id, property_id):
    url = f"https://api.notion.com/v1/pages/{page_id}/properties/{property_id}"

    headers = {
            "Notion-Version": "2026-03-11",
            "Authorization": f'Bearer {token}',
        }
    
    propriedades = requests.get(url, headers=headers)
    if propriedades.status_code == 200:
        print(f"Cliente encontrado com sucesso")
    else:
        print(f"Não foi possível encontrar o cliente")
        print(propriedades.json())
    return propriedades
    
def cadastra_cliente(cnpj, fantasia, source=clientes):
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
        "properties":{
            "CNPJ/CPF":{
                    "title":[
                        {"text":{"content":f"{cnpj}"}}
                    ]
            },
            "NOME FANTASIA":{
                "type":"rich_text",
                "rich_text":[{
                    "text":{"content":fantasia}
                }]
            }
        }
    }
    novo_cliente = requests.post(url, headers=headers, json=payload)
    return novo_cliente

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

def procura(pedido, titulo="Nome", source=data_source_id):
    url = f'https://api.notion.com/v1/data_sources/{source}/query'
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f"Bearer {token}",
    }

    payload = {
        "filter":{
            "title":{"equals":f"{pedido}"},
            "property":titulo
        }
    }
    pesquisa = requests.post(url, headers=headers, json=payload)

    return pesquisa

def cria_pedido(pedido, itens, quantidade, boleto, transportadora, cliente, vendedor, link_mercos, data_pedido, nome_excursao, equipe, valor, progresso, id_cliente, frete_tabelado, source=data_source_id):
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
            "CLIENTES":{
                "relation":[
                    {"id":f"{id_cliente}"}
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
            "FRETE TABELADO": {
                "type":"number",
                "number": frete_tabelado,
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

def cria_cotacao(pedido, id_pedido, frete_tabelado, source=cotacao_id):
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
            "COTACAO": {
                    "title": [
                { "text": { "content": f"{pedido}" } }
                ]
            },
            "PEDIDO":{
                "relation":[
                    {"id":f"{id_pedido}"}
                ]
            },
            "FRETE TABELADO": {
                "type":"number",
                "number": frete_tabelado,
            },
        }
    }

    nova_cotacao = requests.post(url, headers=headers, json=payload)
    if nova_cotacao.status_code == 400:
        print("Erro ao criar cotação")
        print(nova_cotacao.json())
        return nova_cotacao
    else:
        print(f"Cotação do pedido {pedido} criada com sucesso.")
        return nova_cotacao

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

def atualiza_clientes_notion(id, codigo_omie):
    url = f"https://api.notion.com/v1/pages/{id}"

    payload = {
        "properties":{
            "CODIGO OMIE":{"number":codigo_omie},
        }
    }

    headers = {
            "Notion-Version": "2026-03-11",
            "Authorization": f"Bearer {token}",
        }
    
    atualizados = requests.patch(url, headers=headers, json=payload)
    if atualizados.status_code == 200:
        print(f"Cliente atualizado com sucesso")
    else:
        print(f"Não foi possível atualizar o cliente")
        print(atualizados.json())
    return atualizados


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

def atualiza_cotacao(id, data_cotacao=0, valor_cotacao=0, prazo=0, pre_nota=False, nota_cheia=False):
    url = f"https://api.notion.com/v1/pages/{id}"

    if not pre_nota:
        payload = {
            "properties":{
                "DATA COTAÇÃO BRASPRESS":{"date":{"start":f"{data_cotacao}"}},
                "COTAÇÃO BRASPRESS":{"number":valor_cotacao},
                "PRAZO BRASPRESS":{"number":prazo},
            }
        }
    else:
        payload = {
            "properties":{
                "FRETE TOTAL":{"number":valor_cotacao},
                "NOTA CHEIA":{"checkbox":nota_cheia}
            }
        }
    headers = {
            "Notion-Version": "2026-03-11",
            "Authorization": f'Bearer {token}',
        }
    
    atualizados = requests.patch(url, headers=headers, json=payload)
    if atualizados.status_code == 200:
        print(f"Cotação atualizada com sucesso")
    else:
        print(f"Não foi possível atualizar a cotação")
        print(atualizados.json())
    return atualizados

def atualiza_dados_faturamento(id, dados_atualizados, volumes):
    url = f"https://api.notion.com/v1/pages/{id}"
    qtd_itens, qtd_total, valor_pedido, link_mercos, vendedor, time, transportadora, excursao = dados_atualizados
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
            "VOLUMES": {
                "type":"number",
                "number": int(volumes),
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
            },
            "TRANSPORTADORA":{
                "select":{"name":transportadora}
            },
            "EXCURSÃO":{
                "type":"rich_text",
                "rich_text":[{"text":{"content":excursao}}]
            }
        }
    }
    headers = {
            "Notion-Version": "2026-03-11",
            "Authorization": f'Bearer {token}',
        }
    if not excursao:
        payload["properties"].pop("EXCURSÃO")
    atualizados = requests.patch(url, headers=headers, json=payload)
    if atualizados.status_code == 200:
        print(f"Pedido atualizado com sucesso")
    else:
        print(f"Não foi possível atualizar o Pedido")
        print(atualizados.json())
    return atualizados

def id_pedido_notion(pedido, source=data_source_id):
    url = f'https://api.notion.com/v1/data_sources/{source}/query'
    headers = {
        "Notion-Version": "2026-03-11",
        "Authorization": f'Bearer {token}',
    }
    payload = {
    # "sorts": [{ "timestamp": "created_time", "direction":"descending" }],
        "filter":{
            "title":{"equals":pedido},
            "property":"Nome"
        }
    }

    requisicao = requests.post(url, headers=headers, json=payload).json()['results'][0]
    id_pedido = requisicao['id']
    transportadora = requisicao['properties']['TRANSPORTADORA']['select']['name']
    return (id_pedido, transportadora)

if __name__=="__main__":
    # rodar_atualização()
    pass