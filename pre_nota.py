import requests
from datetime import datetime
import json
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import psutil
import time
from notion import login_mercus
from dotenv import load_dotenv
import os

load_dotenv("credentials.env")
app_key = os.getenv("APP_KEY")
app_secret = os.getenv("APP_SECRET")

grupo_zigg = ["ZIGG-ZAGG DISTRIBUIDORA - FILIAL", "ZIGG-ZAGG DISTRIBUIDORA", "BELA BIJU"]
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

def inclui_parcela(parcela):
    url = 'https://app.omie.com.br/api/v1/geral/parcelas/'

    headers = {
            'Content-type': 'application/json',
        }

    json_data = {
        'call': 'IncluirParcela',
        'param': [
            {
                 "cParcela": f"{parcela}"
            }
        ],
        'app_key': app_key,
        'app_secret': app_secret,
    }

    nova_parcela = requests.post(url, headers=headers, json=json_data)
    codigo_nova_parcela = nova_parcela.json()["cCodParcela"]
    status = nova_parcela.json()["cCodStatus"]
    desc_status = nova_parcela.json()["cDesStatus"]
    # print(parcelas.json())
    return (codigo_nova_parcela, status, desc_status)

def preco_tabelado(tabela_mercos: str, estado, valor_pedido):
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
            return preco

    return 0  
        
def pega_cfop(cod_cliente):
    url = 'https://app.omie.com.br/api/v1/geral/clientes/'
    
    headers = {
            'Content-type': 'application/json',
        }
    json_data = {
        'call': 'ConsultarCliente',
        'param': [{
            "codigo_cliente_omie": cod_cliente,
            "codigo_cliente_integracao": ""
        }],
        'app_key': app_key,
        'app_secret': app_secret,
    }
    while True:
        try:
            consulta = requests.post(url, headers=headers, json=json_data)
            break
        except requests.exceptions.ConnectionError:
            print("Erro de conexão na busca do estado do cliente, tentando novamente...")
            time.sleep(61)
            continue
            # print(consulta.json())
    estado = consulta.json()["estado"]
    if estado == "CE":
        cfop = "5.405"
    else:
        cfop = "6.102"
    return (cfop, estado)

def deleta_prenota(cod_integracao):
    url = 'https://app.omie.com.br/api/v1/produtos/pedido/'
    
    headers = {
            'Content-type': 'application/json',
        }
    json_data = {
        'call': 'ExcluirPedido',
        'param': [{
            "codigo_pedido": 0,
            "codigo_pedido_integracao": f"{cod_integracao}"
        }],
        'app_key': app_key,
        'app_secret': app_secret,
    }
    consulta = requests.post(url, headers=headers, json=json_data)
    print(consulta.json())
    if consulta.status_code == 200:
        print('Pre nota excluida')
        return True
    elif consulta.json()['faultstring']=="ERROR: Este pedido de vendas já foi faturado, não é possível prosseguir com a exclusão!":
        print("Erro na exclusão da pre nota")
        return False
    else:
        return True

def salva_html(pedido):
    while selenium_esta_rodando():
        time.sleep(1)
        for i in range(4):
            pontos = "." * i
            time.sleep(0.2)
            print(f"\rAguardando vez para acessar a pagina{pontos:<3}", end="", flush=True)
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

        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            html = driver.page_source
            with open(f"pedidos\\{pedido}.html", "w", encoding="utf-8") as file:
                file.write(html)
        except Exception as e:
            print("Não foi possivel salvar o html", e)
    # driver.close()

def busca_codigos_produtos(codigos):
    info_produtos = []
    lista_codigos = []
    codigos_para_atualizar = []
    #Verificar se tem algum subtituto
    with open("substituto.json", "rb") as file:
        substitutos = json.load(file)
        for codigo in codigos:
            if codigo in substitutos.keys():
                lista_codigos.append(substitutos[codigo])
                print(f"Codigo {codigo} substituido por {substitutos[codigo]}")
            else:
                lista_codigos.append(codigo)
    with open("produtos.json", "rb") as file:
        produtos = json.load(file)
    for codigo in lista_codigos:
        try:
            info_produtos.append(produtos[codigo]['codigo_omie'])
        except KeyError as e:
            print(f"Código não encontrado: {codigo}")
            codigos_para_atualizar.append(codigo)
            continue
    if len(codigos_para_atualizar) > 0:
        return codigos_para_atualizar
        
    return info_produtos

def busca_codigo_cliente(cnpj_cpf):
    with open("clientes.json", "rb") as file:
        clientes = json.load(file)
    try:
        codigo_cliente = clientes[cnpj_cpf]['codigo']
    except KeyError as e:
        print("Cliente não encontrado, insira o codigo manualmente...")
        codigo_cliente = input("Código cliente: ")
    return codigo_cliente

def busca_codigo_transportadora(transportadora):
    with open("transportadoras.json", "rb") as file:
        transportadoras = json.load(file)
    try:
        codigo_transportadora = transportadoras[transportadora]['codigo']
    except KeyError:
        codigo_transportadora = False
    return codigo_transportadora

def busca_codigo_parcela(parcela):
    if parcela == "Pix":
        return "000"
    with open("parcelas.json", "rb") as file:
        parcelas = json.load(file)
    try:
        codigo_parcela = parcelas[parcela]['codigo']
    except KeyError:
        print(f"Parcela não cadastrada, efetuando cadastro de parcela: {parcela}")
        try:
            codigo_nova_parcela, status, descricao = inclui_parcela(parcela)
            if status == "0":
                print("Parcela cadastrada com sucesso")
                return codigo_nova_parcela
            else:
                print(f"Erro no cadastro da parcela. ERRO: {descricao}")
        except Exception as e:
            print(f"Não foi possível cadastrar a parcela, cadastre manualmente. Erro: {e}")
    return codigo_parcela

def gera_produtos(cod_produtos, cfop):
    det = []
    for cod_prod, qtd, valor in cod_produtos:
        det.append(
            {
            "ide": {
                "codigo_item_integracao": f"{cod_prod}"
            },
            "produto": {
                "cfop": f"{cfop}",
                "codigo_produto": f"{cod_prod}",
                "quantidade": qtd,
                "valor_unitario": valor
            }
            }
        )
    return det

def cria_pedido(parametros):
    cod_integracao, cod_cliente, cod_parcela, cod_produtos, cfop, cod_transportadora, mod_frete, volumes, valor_frete, num_pedido_mercos, sucesso = parametros
    tentativa = 1
    if not sucesso:
        cod_integracao = f"pedido{num_pedido_mercos}t{tentativa}"
    url = 'https://app.omie.com.br/api/v1/produtos/pedido/'

    headers = {
            'Content-type': 'application/json',
        }
    
    json_data = {
        'call': 'IncluirPedido',
        'param': [
            {
                "cabecalho": {
                    "codigo_pedido_integracao": f"{cod_integracao}",
                    "codigo_cliente": cod_cliente,
                    "data_previsao": datetime.today().date().strftime(format="%d/%m/%Y"),
                    "etapa": "50",
                    "codigo_parcela": f"{cod_parcela}",
                    "codigo_cenario_impostos":9553371106
                },
                "det": gera_produtos(cod_produtos, cfop),

                "frete": {
                    "codigo_transportadora":cod_transportadora,
                    "modalidade": f"{mod_frete}",
                    "quantidade_volumes":volumes,
                    "valor_frete":valor_frete
                },
                "informacoes_adicionais": {
                    "codigo_categoria": "1.01.03",
                    "codigo_conta_corrente": 9520897830,
                    "numero_pedido_cliente":f"{num_pedido_mercos}",
                    "consumidor_final": "S",
                    "enviar_email": "N"
                },
            }
        ],
        'app_key': app_key,
        'app_secret': app_secret,
    }
    if not cod_transportadora:
        json_data["param"][0]["frete"].pop("codigo_transportadora")
    try:
        pedido = requests.post(url, headers=headers, json=json_data, timeout=(5, 10))
        pedido.raise_for_status()
        # print(pedido.status_code)
        print(pedido.json()['descricao_status'])
    except requests.exceptions.ReadTimeout:
        print("Envio concluído, mas sem resposta do servidor")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro no envio do pedido: {e}")
        while pedido.status_code != 200:
            time.sleep(61)
            try:
                tentativa += 1
                cod_integracao = f"pedido{num_pedido_mercos}t{tentativa}"
                json_data["param"][0]["cabecalho"]["codigo_pedido_integracao"] = cod_integracao
                pedido = requests.post(url, headers=headers, json=json_data, timeout=(5, 10))
                pedido.raise_for_status()
                # print(pedido.status_code)
                print(pedido.json()['descricao_status'])
            except requests.exceptions.ReadTimeout as e:
                print("Envio concluído, mas sem resposta do servidor")
                return True
        return True

def menu_inicial():
    while True:
        try:
            volumes = input('Digite a quantidade de volumes: ')
            if volumes == "":
                    volumes = 1
            volumes = int(volumes)
            break
        except Exception as e:
            print("Valor inválido")

    mod_frete = input('Digite a modalidade de frete: 0 - CIF, 1 - FOB, 9 - Sem Frete: ')
    while mod_frete not in ["0", "1", "9"]:
        print("Opção inválida")
        mod_frete = input('Digite a modalidade de frete: 0 - CIF, 1 - FOB, 9 - Sem Frete: ')
        if mod_frete == "":
            mod_frete = "9"

    valor_frete = input('Digite o valor da cotação: ')
    if valor_frete == "":
        valor_frete = 0
    try:
        valor_frete = float(valor_frete.replace(",", "."))
    except Exception as e:
        print("Frete inválido")
        valor_frete = 0
    return (mod_frete, volumes, valor_frete)

def info_pedido(pedido, valor_pedido):
    try:
        with open(f"pedidos\\{pedido}.html", "rb") as html_content:
            soup = BeautifulSoup(html_content, "lxml")
    except Exception as e:
        print("Pedido não encontrado nos downloads")
    cod_integracao = soup.select_one("#js-div-global > div.overlay > section > div.container-fluid > div.box.bordered.padded > div.padded.acoes_pedido.barra-acao > script").text.strip().split()[2]
    lista_cliente = soup.select_one("#selecionado_autocomplete_id_codigo_cliente > span > div > div:nth-child(1) > div:nth-child(1) > h5 > a").get_text(strip=True, separator="|").split("|")
    lista_cnpj_cpf = soup.select_one("#selecionado_autocomplete_id_codigo_cliente > span > div > div:nth-child(1) > div:nth-child(1) > h5 > small:nth-child(3)").get_text(strip=True, separator=" ").split(" ")
    destino = soup.select_one('#selecionado_autocomplete_id_codigo_cliente > span > div > div:nth-child(3) > div > span').text
    # print(lista_cnpj_cpf)
    if len(lista_cnpj_cpf) > 1:
        cnpj_cpf = lista_cnpj_cpf[1]
    else:
        cnpj_cpf = lista_cnpj_cpf[0]
    if len(lista_cliente) > 1:
        cliente = lista_cliente[1]
    else:
        cliente = lista_cliente[0]
    num_pedido_mercos = soup.select_one("#informacoes_complementares > div > div > div:nth-child(1) > div:nth-child(1) > div > div.col-sm-8.label-valor").text

    parcela =  soup.select_one("#informacoes_complementares > div > div > div:nth-child(2) > div:nth-child(1) > div > div.js-condicao-pagamento.col-sm-8.label-valor").text
    transportadora = soup.select_one("#informacoes_complementares > div > div > div:nth-child(3) > div:nth-child(2) > div > div.col-sm-8.label-valor").text
    porcentagem = soup.select_one("#informacoes_complementares > div > div > div:nth-child(2)")
    info_adicionais = soup.select_one("#informacoes_complementares > div > div > div.flex.col-sm-12.tpadded20 > div.label-valor").text
    vendedor = soup.select_one('#informacoes_complementares > div > div > div:nth-child(1) > div:nth-child(4) > div > div.col-sm-8.label-valor').text
    for child in porcentagem.find_all():
        texto_limpo = child.get_text(strip=True)
        if texto_limpo == "* TABELA DE ENVIO DE MERCADORIA":
            # .find_next_sibling() pega o elemento irmão que vem logo depois dele
            proximo_elemento = child.find_next_sibling()
            if proximo_elemento:
                pct = proximo_elemento.get_text(strip=True)
                break

    for child in porcentagem.find_all():
        texto_limpo = child.get_text(strip=True)
        if texto_limpo == "* TABELA USADA NO PEDIDO":
            # .find_next_sibling() pega o elemento irmão que vem logo depois dele
            texto_tabela = child.find_next_sibling()
            if texto_tabela:
                tabela = texto_tabela.get_text(strip=True)
                
                break

    for child in porcentagem.find_all():
        texto_limpo = child.get_text(strip=True)
        if texto_limpo == "* Observação Interna":
            # .find_next_sibling() pega o elemento irmão que vem logo depois dele
            texto_observacao = child.find_next_sibling()
            if texto_observacao:
                observacao = texto_observacao.get_text(strip=True)
                
                break
    texto_completo = f"INFORMAÇÕES PEDIDO: {pedido}"            
    pedido_formatado = f"R$ {valor_pedido:,.2f}"
    print("=" * 50)
    print(f"{texto_completo:^50}")
    print("=" * 50)
    print(f" {'Cliente:':<18} {cliente}")
    print(f" {'CNPJ/CPF:':<18} {cnpj_cpf}")
    print(f" {'Destino:':<18} {destino}")
    print(f" {'Pagamento:':<18} {parcela}")
    print(f" {'Transportadora:':<18} {transportadora}")
    print(f" {'Valor do Pedido:':<18} {pedido_formatado}")
    print(f" {'Tabela:':<18} {tabela}")
    print(f" {'Porcentagem:':<18} {pct}")
    print("=" * 50)
    print(f" {'Vendedor:' :<18} {vendedor}")
    print(f" {'Observação Interna:' :<18} {observacao}")
    print(f" {'Informações Adicionais:' :<18} {info_adicionais}")            
    print("=" * 50)

    return (cod_integracao, cliente, cnpj_cpf, num_pedido_mercos, parcela, transportadora, pct, tabela, destino, vendedor)
    
def painel_informativo(pedido, cliente, parcela, transportadora, frete_tabelado, valor_pedido, valor_nf, porcentagem, tabela,  mod_frete, volumes, valor_cotacao, frete_nota, destino, vendedor):
    # Formatação de valores e porcentagem
    porcentagem_formatada = f"{porcentagem * 100:.1f}%"
    pedido_formatado = f"R$ {valor_pedido:,.2f}"
    cotacao_formatada = f"R$ {valor_cotacao:,.2f}"
    nf_formatado = f"R$ {valor_nf:,.2f}"
    frete_nf_formatado = f"R$ {frete_nota:,.2f}"
    frete_formatado = f"R$ {frete_tabelado:,.2f}" if isinstance(frete_tabelado, (int, float)) else frete_tabelado
    match mod_frete:
        case "0":
            mod_frete_formatado = "CIF"
        case "1":
            mod_frete_formatado = "FOB"
        case "9":
            mod_frete_formatado = "SEM FRETE"
    texto_completo = f"INFORMAÇÕES AJUSTADAS PEDIDO: {pedido}"
    # Criação do painel
    print("=" * 50)
    print(f"{texto_completo:^50}")
    print("=" * 50)
    print(f" {'Cliente:':<18} {cliente}")
    print(f" {'Destino:':<18} {destino}")
    print(f" {'Vendedor:':<18} {vendedor}")
    print(f" {'Pagamento:':<18} {parcela}")
    print(f" {'Transportadora:':<18} {transportadora}")
    print(f" {'Tabela:':<18} {tabela}")
    print("-" * 50)
    print(f" {'Modalidade Frete:':<18} {mod_frete_formatado}")
    print(f" {'Volumes:':<18} {volumes}")
    print(f" {'Frete Tabelado:':<18} {frete_formatado}")
    print(f" {'Cotação:':<18} {cotacao_formatada}")
    print(f" {'Frete NOTA:':<18} {frete_nf_formatado}")
    print(f" {'Valor Pedido:':<18} {pedido_formatado}")
    print(f" {'Valor NF:':<18} {nf_formatado}")
    print(f" {'Porcentagem:':<18} {porcentagem_formatada}")
    print("=" * 50)

def preco_zerado(preco):
    if preco < 0.01:
        return 0.01
    else:
        return preco

def configuracoes():
    pedido = input('Digite o numero do pedido ou Digite 0 para encerrar: ')
    if pedido == "0":
        return False

    salva_html(pedido)
    file_path = f"pedidos\\{pedido}.html"

    while True:
        if os.path.exists(file_path):
            df = pd.read_html(
                file_path, attrs={"id": "tabela_itens_pedido"}
            )[0].drop(columns=["Foto", "Desc. Acrés.", "Preço Tab."]).drop_duplicates(keep=False)
            break
        else:
            foi = input("O arquivo foi gerado/baixado? Digite 1 para tentar novamente ou outro valor para sair: ")
            if foi == "1":
                continue
            else:
                print("Monitoramento encerrado pelo usuário.")
                break

    df = df[~df['Código'].str.startswith('Observações:', na=False)]
    df.dropna(how='all', inplace=True)
    df.dropna(how='all', inplace=True, axis=1)
    df.reset_index(inplace=True, drop=True)
        
    preco_liq = df['Preço Líq.'].apply(lambda x: x.split()[1].replace(",",".")).astype(float)
    subtotal = df['Subtotal'].apply(lambda x: x.split()[1].replace(".","").replace(",",".")).astype(float)
    qtde = df['Qtde.'].apply(lambda x: x.split()[0].replace(".","")).astype(int)
    df["Preço Líq."] = preco_liq
    df["Qtde."] = qtde
    try:
        df['codigos_omie'] = busca_codigos_produtos(df["Código"])
    except Exception as e:
        codigos_para_atualizar = busca_codigos_produtos(df["Código"])
        print(codigos_para_atualizar)
        codigos_novos = {}
        for cod in codigos_para_atualizar:
            substituto = input(f"Digite o substituto para o codigo {cod}: ")
            codigos_novos[cod] = substituto.replace("\t", "").strip()
        with open("substituto.json", "rb") as file:
            subs = json.load(file)
            subs.update(codigos_novos)
        with open("substituto.json", "w", encoding="utf-8") as file:
                json.dump(subs, file, indent=4)
        df['codigos_omie'] = busca_codigos_produtos(df["Código"])

    valor_pedido = subtotal.sum()
    

    cod_integracao, cliente, cnpj_cpf, num_pedido_mercos, parcela, transportadora, porcentagem, tabela, destino, vendedor = info_pedido(pedido, valor_pedido)
    
    cod_cliente = busca_codigo_cliente(cnpj_cpf)
    cod_parcela = busca_codigo_parcela(parcela)
    cod_transportadora = busca_codigo_transportadora(transportadora)

    cfop, estado = pega_cfop(cod_cliente)

    try:
        if cliente in grupo_zigg:
            pct = 0.12
        else:
            pct = int(porcentagem)/100
    except Exception as e:
        pct = 0.2

    p = input("Porcentagem diferente: ")
    if p == "":
        pass
    else:
        try:
            pct = int(p)/100
        except:
            print("Valor inválido")

    parc = input("Parcelamento diferente: ")
    if parc == "":
        pass
    else:
        try:
            parcela = parc
            cod_parcela = busca_codigo_parcela(parcela)
        except:
            print("Valor inválido")
    
    df['valor'] = df['Preço Líq.']*pct
    df['valor'] = df['valor'].apply(preco_zerado)
    valor_nf = valor_pedido*pct

    frete_tabelado = preco_tabelado(tabela, estado, valor_pedido)

    mod_frete, volumes, valor_cotacao = menu_inicial()

    if mod_frete == "9":
        cod_transportadora = False
        valor_cotacao = 0

    if porcentagem == "100":
        frete_nota = valor_cotacao
    else:
        
        if (valor_cotacao < frete_tabelado) or valor_pedido < 2000:
            frete_nota = valor_cotacao
        else:
            frete_nota = frete_tabelado

    if mod_frete == "0" and transportadora == "P/ SÃO PAULO":
        cod_transportadora = 10021638182
    
    sucesso = deleta_prenota(cod_integracao)
    painel_informativo(pedido, cliente, parcela, transportadora, frete_tabelado, valor_pedido, valor_nf, pct, tabela, mod_frete, volumes, valor_cotacao, frete_nota, destino, vendedor)
    print("Ajustando pré nota...")
    codigo_omie = (zip(df['codigos_omie'], df['Qtde.'], df['valor']))
    return (cod_integracao, cod_cliente, cod_parcela, codigo_omie, cfop, cod_transportadora, mod_frete, volumes, frete_nota, num_pedido_mercos, sucesso)

def executa():
    parametros = True
    while parametros:
        parametros = configuracoes()
        if not parametros:
            break
        cria_pedido(parametros)
    print("Encerrando execução")

if __name__=="__main__":

    executa()
