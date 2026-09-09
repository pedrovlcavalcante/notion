import psutil


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

class Pedido():
    def __init__(self, numero, cliente, vendedor, data, pagamento, tabela, porcentagem, envio, frete, estado, cidade):
        self.numero = numero
        self.cliente = cliente
        self.vendedor = vendedor
        self.data = data
        self.pagamento = pagamento
        self.tabela = tabela
        self.porcentagem = porcentagem
        self.envio = envio
        self.frete = frete
        self.estado = estado
        self.cidade = cidade

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
