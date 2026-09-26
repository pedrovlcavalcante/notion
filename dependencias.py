import psutil, json
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from notion import busca_cliente, cria_pedido, cria_cotacao, cria_bloco, equipe
from datetime import datetime
import requests
import os
import base64

estados_brasil = {
    "Acre": "AC",
    "Alagoas": "AL",
    "Amapá": "AP",
    "Amazonas": "AM",
    "Bahia": "BA",
    "Ceará": "CE",
    "Distrito Federal": "DF",
    "Espírito Santo": "ES",
    "Goiás": "GO",
    "Maranhão": "MA",
    "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG",
    "Pará": "PA",
    "Paraíba": "PB",
    "Paraná": "PR",
    "Pernambuco": "PE",
    "Piauí": "PI",
    "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS",
    "Rondônia": "RO",
    "Roraima": "RR",
    "Santa Catarina": "SC",
    "São Paulo": "SP",
    "Sergipe": "SE",
    "Tocantins": "TO"
}

regras_preco = {
    "CE": {
        (0, 2999.99): 50,
        (3000, float("inf")): 0,
    },
    "nordeste": {
        "10": {(2000, 2999.99): 180, (3000, 3999.99): 150, (4000, 4999.99): 120, (5000, float("inf")): 0},
        "40": {(2000, 2999.99): 120, (3000, 3499.99): 90, (3500, float("inf")): 0}
    },
    "norte": {
        "10": {(3000, 3999.99): 260, (4000, 4999.99): 240, (5000, 5999.99): 220, (6000, 6999.99): 200, (7000, 7999.99): 170, (8000, 8999.99): 150, (9000, float("inf")): 0},
        "40": {(2000, 2999.99): 250, (3000, 3999.99): 200, (4000, 4999.99): 180, (5000, 5999.99): 150, (6000, 7499.99): 120, (7500, float("inf")): 0},
    },
    "outras": {
        "10": {(2000, 2999.99): 200, (3000, 3999.99): 170, (4000, 4999.99): 150, (5000, 5999.99): 120, (6000, 6999.99): 110, (7000, float("inf")): 0},
        "40": {(2000, 2999.99): 150, (3000, 3999.99): 120, (4000, 4999.99): 100, (5000, 5499.99): 80, (5500, float("inf")): 0},
    },
}

tipos_boleto = ['Para 30 dias', 'Para 45 dias']

cidades_rm = ['AQUIRAZ', 'CASCAVEL', 'CAUCAIA', 'EUSÉBIO', 'EUSEBIO', 'FORTALEZA', 'HORIZONTE', 'ITAITINGA', 'MARACANAÚ', 'MARACANAU', 'MARANGUAPE', 'PACAJÚS', 'PACAJUS', 'PACATUBA', 'PINDORETAMA']

def selenium_esta_rodando(): 
    # Nomes dos executáveis comuns de WebDrivers
    drivers_selenium = ["chromedriver", "geckodriver", "msedgedriver"]


    for proc in psutil.process_iter(['name']):
        try:
            # Converte o nome para minúsculo para evitar problemas no Windows/Linux
            nome_processo = proc.info['name'].lower()
            
            # Se encontrar o driver na lista de processos ativos
            if any(driver in nome_processo for driver in drivers_selenium):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return False

class Cliente():
    def __init__(self, numero_pedido_mercos):
        self.numero_pedido_mercos = numero_pedido_mercos
        self.fiscal = self.extrai_cnpj()
        notion = busca_cliente(self.fiscal)
        # print(notion)
        busca = notion['results'][0]
        self.codigo_integracao_cliente = busca['properties']['CODIGO OMIE']['number']
        self.cep = busca['properties']['CEP']['rich_text'][0]['text']['content']
        self.nome = busca['properties']['NOME FANTASIA']['rich_text'][0]['text']['content']
        self.razao_social = busca['properties']['RAZAO SOCIAL']['rich_text'][0]['text']['content']
        self.cidade = busca['properties']['CIDADE']['rich_text'][0]['text']['content']
        self.estado = busca['properties']['ESTADO']['rich_text'][0]['text']['content']
        self.id_notion = busca['id']

    def extrai_cnpj(self):
        file_path = f"novos_pedidos\\{self.numero_pedido_mercos}.html"
        with open(file_path, "rb") as html_content:
            soup = BeautifulSoup(html_content, "lxml")
        lista_cnpj_cpf = soup.select_one("#selecionado_autocomplete_id_codigo_cliente > span > div > div:nth-child(1) > div:nth-child(1) > h5 > small:nth-child(3)").get_text(strip=True, separator=" ").split(" ")

        if len(lista_cnpj_cpf) > 1:
            cnpj_cpf = lista_cnpj_cpf[1]
        else:
            cnpj_cpf = lista_cnpj_cpf[0]
        return cnpj_cpf

class Pedido():
    # a ideia aqui é essa ser a classe base para criar a pagina do pedido no Notion e criar a pre-nota também
    def __init__(self, numero, link):
        self.numero = numero
        file_path = f"novos_pedidos\\{self.numero}.html"

        with open(file_path, "rb") as html_content:
            soup = BeautifulSoup(html_content, "lxml")

        codigo_integracao_pedido = soup.select_one("#js-div-global > div.overlay > section > div.container-fluid > div.box.bordered.padded > div.padded.acoes_pedido.barra-acao > script").text.strip().split()[2]
            
        # Informações extraídas da parte inferior da página
        # 1ª coluna
        vendedor = soup.select_one('#informacoes_complementares > div > div > div:nth-child(1) > div:nth-child(4) > div > div.col-sm-8.label-valor').text
        data_emissao = soup.select_one('#informacoes_complementares > div > div > div:nth-child(1) > div:nth-child(2) > div > div.col-sm-8.label-valor').text
        data_pedido = datetime.strptime(data_emissao, "%d/%m/%Y").date().isoformat()
        # 2ª coluna
        condicao_pagamento = soup.select_one("#informacoes_complementares > div > div > div:nth-child(2) > div:nth-child(1) > div > div.js-condicao-pagamento.col-sm-8.label-valor").text
        outros_campos = soup.select_one("#informacoes_complementares > div > div > div:nth-child(2)")
    
        #3ª coluna
        transportadora = soup.select_one("#informacoes_complementares > div > div > div:nth-child(3) > div:nth-child(2) > div > div.col-sm-8.label-valor").text
        if ':' in  transportadora:
            excursao = transportadora
        else:
            excursao = False
    
        # essa variável se encontra no fim dessa div, quase no rodapé
        info_adicionais = soup.select_one("#informacoes_complementares > div > div > div.flex.col-sm-12.tpadded20 > div.label-valor").text
    
        # loop para encontrar a porcentagem da nota
        for child in outros_campos.find_all():
            texto_limpo = child.get_text(strip=True)
            if texto_limpo == "* TABELA DE ENVIO DE MERCADORIA":
                # .find_next_sibling() pega o elemento irmão que vem logo depois dele
                proximo_elemento = child.find_next_sibling()
                if proximo_elemento:
                    porcentagem = proximo_elemento.get_text(strip=True)
                    break
    
        # loop para encontar a tabela de preço           
        for child in outros_campos.find_all():
            texto_limpo = child.get_text(strip=True)
            if texto_limpo == "* TABELA USADA NO PEDIDO":
                # .find_next_sibling() pega o elemento irmão que vem logo depois dele
                texto_tabela = child.find_next_sibling()
                if texto_tabela:
                    tabela_mercos = texto_tabela.get_text(strip=True)
                    break
    
        # loop para encontrar a observação interna
        for child in outros_campos.find_all():
            texto_limpo = child.get_text(strip=True)
            if texto_limpo == "* Observação Interna":
                # .find_next_sibling() pega o elemento irmão que vem logo depois dele
                texto_observacao = child.find_next_sibling()
                if texto_observacao:
                    observacao = texto_observacao.get_text(strip=True)
                    break

        boleto = False
        if ('/' in condicao_pagamento) or (condicao_pagamento in tipos_boleto):
            boleto = True

        self.cliente = Cliente(self.numero)
        self.vendedor = vendedor
        self.time = equipe(self.vendedor)
        self.data_pedido = data_pedido
        self.condicao_pagamento = condicao_pagamento
        self.boleto = boleto
        self.tabela_mercos = tabela_mercos
        self.observacao_interna = observacao
        self.informacoes_adicionais = info_adicionais
        self.porcentagem = porcentagem
        self.link = link

        self.produtos = None
        self.itens_da_fabrica = None
        self.itens = None
        self.quantidade = None
        self.valor_pedido = None

        self.codigo_integração = codigo_integracao_pedido
        self.volumes = None
        self.frete_tabelado = None
        self.transportadora = transportadora
        self.excursao = excursao

        self.page_id = None

    def extrai_produtos(self):
        file_path = f"novos_pedidos\\{self.numero}.html"
        df = pd.read_html(
                file_path, attrs={"id": "tabela_itens_pedido"}
            )[0].drop(columns=["Foto", "Desc. Acrés.", "Preço Tab."]).drop_duplicates(keep=False)
        
        df = df[~df['Código'].str.startswith('Observações:', na=False)]
        df.dropna(how='all', inplace=True)
        df.dropna(how='all', inplace=True, axis=1)
        df.reset_index(inplace=True, drop=True)

        preco_liq = df['Preço Líq.'].apply(lambda x: x.split()[1].replace(",",".")).astype(float)
        subtotal = df['Subtotal'].apply(lambda x: x.split()[1].replace(".","").replace(",",".")).astype(float)
        qtde = df['Qtde.'].apply(lambda x: x.split()[0].replace(".","")).astype(int)
        df["Preço Líq."] = preco_liq
        df["Qtde."] = qtde

        self.produtos = df
        self.itens = df['Código'].value_counts().sum()
        self.quantidade = df['Qtde.'].sum()
        self.valor_pedido = subtotal.sum()

    def calcula_frete_tabelado(self):
        estado = self.cliente.estado
        cidade = self.cliente.cidade
        if cidade.upper() in cidades_rm:
            if self.transportadora == 'EXPRESS FORTALEZA':
                if self.valor_pedido < 1200:
                    self.frete_tabelado = 33
                    return 0
                else:
                    self.frete_tabelado = 0
                    return 0
            else:
                self.frete_tabelado = 0
                return 0
        else:    
            tabela_mercos = self.tabela_mercos
            valor_pedido = self.valor_pedido
            # Agrupamentos de estados
            nordeste = ["AL", "BA", "MA", "PB", "PE", "PI", "RN", "SE"]
            norte = ["AC", "AP", "AM", "PA", "RO", "RR", "TO"]

            # Identifica o grupo da tabela ("10" ou "40")
            tabela1 = ["10", "20", "30"]
            tabela2 = ["40", "50"]
            tabela = tabela_mercos.split(',')
            if len(tabela)>1:
                for t in tabela:
                    if t in tabela2:
                        tabela = "40"

            if tabela[0] in tabela1:
                grupo_tabela = "10"
            elif tabela[0] in tabela2:
                grupo_tabela = "40"
            else:
                grupo_tabela = None

            # Identifica a região correta no dicionário
            if estado == "CE":
                regra_regiao = "CE"
                faixas = regras_preco.get(regra_regiao, {})
                for (minimo, maximo), preco in faixas.items():
                    if minimo <= valor_pedido <= maximo:
                        return preco
                # grupo_tabela = "todas"  # CE ignora o tipo de tabela nas suas regras
            elif estado in nordeste:
                regra_regiao = "nordeste"
            elif estado in norte:
                regra_regiao = "norte"
            else:
                regra_regiao = "outras"

            # Busca as faixas de valores baseadas na região e tabela detectadas
            faixas = regras_preco.get(regra_regiao, {}).get(grupo_tabela, {})

            # Varre as faixas para encontrar o preço correspondente
            for (minimo, maximo), preco in faixas.items():
                if minimo <= valor_pedido <= maximo:
                    # return preco
                    self.frete_tabelado = preco
            return 0

    def itens_fabrica(self):
        df = self.produtos
        df = df[df['Código'].str.startswith('ZLM', na=False)][['Código', 'Descrição', 'Qtde.']].sort_values(by="Código")
        if not df.empty:
            linhas = []
            for i in df.itertuples():
                linhas.append(f"{i[1]} - {i[2]} - {i[3]}")
            self.itens_da_fabrica = linhas
        else:
            print("Sem itens da fábrica")
            self.itens_da_fabrica = False

    def cria_pedido_notion(self):
        pagina = cria_pedido(self.numero, self.itens, self.quantidade, self.boleto, self.transportadora, self.cliente.nome, self.vendedor, self.link, self.data_pedido, self.excursao, self.time, self.valor_pedido, "EM ANÁLISE", self.cliente.id_notion, self.frete_tabelado)
        self.page_id = pagina.json()["id"]
        cria_cotacao(self.numero, self.page_id, self.frete_tabelado)
        if self.itens_da_fabrica:
            cria_bloco(self.page_id, self.itens_da_fabrica)

class Cotacao():
    load_dotenv('credentials.env')
    cnpj_rementente = os.getenv("CNPJ_REMETENTE")
    usuario = os.getenv("BRASPRESS_USUARIO")
    senha = os.getenv("BRASPRESS_SENHA")
    cep_origem = os.getenv("CEP")
    # Junta os valores no formato 'usuario:senha'
    credenciais = f"{usuario}:{senha}"

    # Codifica para Base64 (requer transformar a string em bytes primeiro)
    credenciais_bytes = credenciais.encode("utf-8")
    base64_bytes = base64.b64encode(credenciais_bytes)
    base64_string = base64_bytes.decode("utf-8")

    def __init__(self, pedido:Pedido):
        self.pedido = pedido
        self.cnpj_destinatario = pedido.cliente.fiscal
        self.cep_destino = pedido.cliente.cep
        pass

    # URL do endpoint
    url = "https://api.braspress.com/v1/cotacao/calcular/json"
    headers = {}
    # Cabeçalhos (Headers) com a autenticação Basic
    headers = {
        "Authorization": f"Basic {base64_string}",
        "Content-Type": "application/json",
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
    }

    def dados():
        data = {
            "cnpjRemetente": cnpj_rementente,
            "cnpjDestinatario": cnpj_destinatario,
            "modal": modal,
            "tipoFrete": tipo_frete,
            "cepOrigem": cep_origem,
            "cepDestino": cep_destino,
            "vlrMercadoria": valor_nota,
            "peso": peso,
            "volumes": volumes,
            "cubagem": [
                {
                    "altura": 0.39,
                    "largura": 0.47,
                    "comprimento": 0.5,
                    "volumes": 2
                },
            ]
        }
    def requisicao(url, headers, data):
        # Fazendo a requisição POST
        response = requests.post(url, headers=headers, json=data)
        return response

if __name__=="__main__":
    pass
    # cliente = Cliente(15187)
    # print(cliente.fiscal)
    # print(cliente.nome)
    # print(cliente.cidade)
    # print(cliente.estado)
    # print(cliente.codigo_integracao)

    # pedido = Pedido(15187, "nada")
    # pedido.extrai_produtos()
    # pedido.calcula_frete_tabelado()
    
    # print(pedido.itens)
    # c = Cotacao(15187)