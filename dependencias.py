import psutil, json
from bs4 import BeautifulSoup


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

def instancia_cliente(pedido):
    with open(f"pedidos\\{pedido}.html", "rb") as html_content:
        soup = BeautifulSoup(html_content, "lxml")
    lista_cliente = soup.select_one("#selecionado_autocomplete_id_codigo_cliente > span > div > div:nth-child(1) > div:nth-child(1) > h5 > a").get_text(strip=True, separator="|").split("|")
    lista_cnpj_cpf = soup.select_one("#selecionado_autocomplete_id_codigo_cliente > span > div > div:nth-child(1) > div:nth-child(1) > h5 > small:nth-child(3)").get_text(strip=True, separator=" ").split(" ")
    destino = soup.select_one('#selecionado_autocomplete_id_codigo_cliente > span > div > div:nth-child(3) > div > span').text

    # extrai cnpj ou cpf
    if len(lista_cnpj_cpf) > 1:
        fiscal = lista_cnpj_cpf[1]
    else:
        fiscal = lista_cnpj_cpf[0]
    if len(lista_cliente) > 1:
        nome_cliente = lista_cliente[1]
    else:
        nome_cliente = lista_cliente[0]
    destino = destino.split(",")
    cidade = destino[0].strip()
    estado = destino[1].strip()
    return Cliente(nome_cliente, estado, cidade, fiscal)

def instancia_pedido(pedido, cliente):
    # esse método coleta as informações do pedido continas na Mercos
    with open(f"pedidos\\{pedido}.html", "rb") as html_content:
        soup = BeautifulSoup(html_content, "lxml")
    cod_integracao = soup.select_one("#js-div-global > div.overlay > section > div.container-fluid > div.box.bordered.padded > div.padded.acoes_pedido.barra-acao > script").text.strip().split()[2]
    
    # Informações extraídas da parte inferior da página
    # 1ª coluna
    num_pedido_mercos = soup.select_one("#informacoes_complementares > div > div > div:nth-child(1) > div:nth-child(1) > div > div.col-sm-8.label-valor").text
    vendedor = soup.select_one('#informacoes_complementares > div > div > div:nth-child(1) > div:nth-child(4) > div > div.col-sm-8.label-valor').text
    data_emissao = None

    # 2ª coluna
    parcela =  soup.select_one("#informacoes_complementares > div > div > div:nth-child(2) > div:nth-child(1) > div > div.js-condicao-pagamento.col-sm-8.label-valor").text
    outros_campos = soup.select_one("#informacoes_complementares > div > div > div:nth-child(2)")

    #3ª coluna
    transportadora = soup.select_one("#informacoes_complementares > div > div > div:nth-child(3) > div:nth-child(2) > div > div.col-sm-8.label-valor").text


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
                tabela = texto_tabela.get_text(strip=True)
                
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
    return Pedido(num_pedido_mercos, tabela, porcentagem, cliente, None)

class Cliente():
    def __init__(self, nome, estado, cidade, fiscal):
        self.nome = nome
        self.estado = estado
        self.cidade = cidade
        self.fiscal = fiscal
        self.uf = estados_brasil.get(estado)
        self.codigo_integracao = self.pega_codigo_integracao()

    def pega_codigo_integracao(self):
        with open("clientes.json", "rb") as file:
            clientes = json.load(file)
        try:
            codigo_cliente = clientes[self.fiscal]['codigo']
        except KeyError as e:
            print("Cliente não encontrado, insira o codigo manualmente...")
            codigo_cliente = input("Código cliente: ")
        return codigo_cliente

class Pedido():
    def __init__(self, numero, tabela_mercos, porcentagem, cliente:Cliente, produtos):
        self.numero = numero
        self.itens = None
        self.quantidade = None
        self.tabela_mercos = tabela_mercos
        self.porcentagem = porcentagem
        self.produtos = produtos
        self.valor_pedido = None
        self.cliente = cliente
        self.frete_tabelado = self.calcula_frete_tabelado()
        self.codigo_integração = None

    def calcula_frete_tabelado(self):
        estado = self.cliente.estado
        tabela_mercos = self.tabela_mercos
        valor_pedido = self.valor_pedido
        #apagar esse if depois, apenas para testes
        if valor_pedido == None:
            valor_pedido = 2000
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

    def imprime_informações(self):
        # Tenho q puxar a tabela e calcular o valor do pedido aqui valor_pedido
        texto_completo = f"INFORMAÇÕES PEDIDO: {self.numero}"            
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


if __name__=="__main__":

    cliente = instancia_cliente(14886)
    print(cliente.nome)
    print(cliente.cidade)
    print(cliente.estado)
    print(cliente.uf)
    print(cliente.fiscal)
    print(cliente.codigo_integracao)

    pedido = instancia_pedido(14886, cliente)
    print(pedido.valor_pedido)
    print(pedido.tabela_mercos)
    print(pedido.frete_tabelado)