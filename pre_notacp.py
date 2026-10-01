from datetime import datetime
import json
import os
from pathlib import Path
import time
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Dependências e integrações externas
from dependencias import selenium_esta_rodando, Pedido
from notion import atualiza_cotacao, cria_cotacao, login_mercus, procura

load_dotenv("credentials.env")

class PreNota(Pedido):
    """Subclasse de Pedido responsável pela preparação, cálculo de impostos/fretes

    e faturamento do pedido no ERP Omie e sincronização no Notion.
    """

    APP_KEY = os.getenv("APP_KEY")
    APP_SECRET = os.getenv("APP_SECRET")
    COTACAO_ID = os.getenv("COTACAO")
    GRUPO_ZIGG = [
        "ZIGG-ZAGG DISTRIBUIDORA - FILIAL",
        "ZIGG-ZAGG DISTRIBUIDORA",
        "BELA BIJU",
    ]

    def __init__(self, numero, link=None):
        # Inicializa todos os atributos da classe pai (Pedido)
        super().__init__(numero, link)

        # Atributos específicos do faturamento / Omie
        self.cnpj_cpf = None
        self.cod_cliente = None
        self.cod_parcela = None
        self.cod_transportadora = None
        self.cfop = None
        self.file_path = Path("pedidos") / f"{numero}.html"

        # Atributos ajustados de faturamento
        self.pct_faturamento = 0.20
        self.valor_nf = 0.0
        self.mod_frete = "9"  # 0-CIF, 1-FOB, 9-Sem Frete
        self.volumes = 1
        self.valor_cotacao = 0.0
        self.frete_nota = 0.0
        self.peso_bruto = 0.0
        self.codigos_omie_produtos = []

        # Carrega dados adicionais da página se não capturados pelo pai
        self._extrai_dados_adicionais_html()

    # -------------------------------------------------------------------------
    # Métodos de Extração e Selenium
    # -------------------------------------------------------------------------

    @classmethod
    def baixar_html_mercus(cls, numero_pedido):
        """Baixa o HTML do pedido via Selenium se ainda não existir localmente."""
        while selenium_esta_rodando():
            time.sleep(1)

        chrome_options = Options()
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument("--headless=new")

        with webdriver.Chrome(options=chrome_options) as driver:
            driver.get("https://app.mercos.com/384882/pedidos/")
            login_mercus(driver)

            try:
                caixa = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//*[@id="id_texto"]')
                    )
                )
                caixa.send_keys(numero_pedido, Keys.ENTER)
            except Exception as e:
                print(f"Erro ao pesquisar pedido {numero_pedido}: {e}")
                return False

            try:
                pagina = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "numero-pedido"))
                )
                pagina.click()
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState")
                    == "complete"
                )

                path = Path("pedidos") / f"{numero_pedido}.html"
                path.parent.mkdir(exist_ok=True)
                with open(path, "w", encoding="utf-8") as file:
                    file.write(driver.page_source)
                return True
            except Exception as e:
                print(f"Erro ao salvar HTML do pedido {numero_pedido}: {e}")
                return False

    def _extrai_dados_adicionais_html(self):
        """Extrai CNPJ/CPF do cliente a partir do HTML salvo se não disponível."""
        if not self.file_path.exists():
            return

        with open(self.file_path, "rb") as file:
            soup = BeautifulSoup(file, "lxml")

        elem_cnpj = soup.select_one(
            "#selecionado_autocomplete_id_codigo_cliente > span > div > div:nth-child(1) > div:nth-child(1) > h5 > small:nth-child(3)"
        )
        if elem_cnpj:
            lista_cnpj = elem_cnpj.get_text(
                strip=True, separator=" "
            ).split(" ")
            self.cnpj_cpf = lista_cnpj[1] if len(lista_cnpj) > 1 else lista_cnpj[0]
        # porcentagem = soup.select_one("#informacoes_complementares > div > div > div:nth-child(2)")
        # info_adicionais = soup.select_one("#informacoes_complementares > div > div > div.flex.col-sm-12.tpadded20 > div.label-valor").text
        # vendedor = soup.select_one('#informacoes_complementares > div > div > div:nth-child(1) > div:nth-child(4) > div > div.col-sm-8.label-valor').text
        # for child in porcentagem.find_all():
        #     texto_limpo = child.get_text(strip=True)
        #     if texto_limpo == "* TABELA DE ENVIO DE MERCADORIA":
        #         # .find_next_sibling() pega o elemento irmão que vem logo depois dele
        #         proximo_elemento = child.find_next_sibling()
        #         if proximo_elemento:
        #             pct = proximo_elemento.get_text(strip=True)
        #     if texto_limpo == "* TABELA USADA NO PEDIDO":
        #         # .find_next_sibling() pega o elemento irmão que vem logo depois dele
        #         texto_tabela = child.find_next_sibling()
        #         if texto_tabela:
        #             tabela = texto_tabela.get_text(strip=True)
        #     if texto_limpo == "* Observação Interna":
        #         # .find_next_sibling() pega o elemento irmão que vem logo depois dele
        #         texto_observacao = child.find_next_sibling()
        #         if texto_observacao:
        #             observacao = texto_observacao.get_text(strip=True)

    # -------------------------------------------------------------------------
    # Mapeamentos de Códigos (JSONs Locais)
    # -------------------------------------------------------------------------

    def mapear_codigos_locais(self):
        """Busca códigos do Cliente, Parcela, Transportadora e Produtos em arquivos JSON."""
        # 1. Cliente
        if self.cnpj_cpf:
            with open("clientes.json", "rb") as f:
                clientes = json.load(f)
            if self.cnpj_cpf in clientes:
                self.cod_cliente = clientes[self.cnpj_cpf]["codigo"]
            else:
                print(f"Cliente {self.cnpj_cpf} não encontrado em clientes.json.")
                self.cod_cliente = input("Digite o código do cliente no Omie: ")

        # 2. Consultar CFOP, Estado e Cidade atualizados no Omie
        if self.cod_cliente:
            self._consultar_cfop_omie()

        # 3. Parcela
        self.cod_parcela = self._buscar_ou_criar_parcela(self.condicao_pagamento)

        # 4. Transportadora
        with open("transportadoras.json", "rb") as f:
            transportadoras = json.load(f)
        if self.transportadora in transportadoras:
            self.cod_transportadora = transportadoras[self.transportadora]["codigo"]
        else:
            self.cod_transportadora = False

        # 5. Mapear Códigos Omie dos Produtos
        self._mapear_produtos_omie()

    def _buscar_ou_criar_parcela(self, parcela_nome):
        if parcela_nome == "Pix":
            return "000"

        with open("parcelas.json", "rb") as f:
            parcelas = json.load(f)

        if parcela_nome in parcelas:
            return parcelas[parcela_nome]["codigo"]

        print(f"Parcela '{parcela_nome}' não encontrada. Cadastrando na Omie...")
        return self._incluir_parcela_omie(parcela_nome)

    def _mapear_produtos_omie(self):
        if self.produtos is None or self.produtos.empty:
            return

        with open("substituto.json", "rb") as f:
            substitutos = json.load(f)
        with open("produtos.json", "rb") as f:
            produtos_db = json.load(f)

        codigos_mapeados = []
        codigos_faltantes = []

        for codigo in self.produtos["Código"]:
            cod_final = substitutos.get(codigo, codigo)
            if cod_final in produtos_db:
                codigos_mapeados.append(produtos_db[cod_final]["codigo_omie"])
            else:
                codigos_faltantes.append(codigo)

        if codigos_faltantes:
            print(f"Códigos não encontrados no banco: {codigos_faltantes}")
            novos_substitutos = {}
            for cod in codigos_faltantes:
                sub = input(f"Digite o código substituto para '{cod}': ").strip()
                novos_substitutos[cod] = sub
            
            substitutos.update(novos_substitutos)
            with open("substituto.json", "w", encoding="utf-8") as f:
                json.dump(substitutos, f, indent=4)
            
            # Recalcula recursivamente após atualizar a tabela de substitutos
            self._mapear_produtos_omie()
            return

        self.produtos["codigo_omie"] = codigos_mapeados

    # -------------------------------------------------------------------------
    # Integrações com API Omie
    # -------------------------------------------------------------------------

    def _consultar_cfop_omie(self):
        url = "https://app.omie.com.br/api/v1/geral/clientes/"
        payload = {
            "call": "ConsultarCliente",
            "param": [{"codigo_cliente_omie": self.cod_cliente, "codigo_cliente_integracao": ""}],
            "app_key": self.APP_KEY,
            "app_secret": self.APP_SECRET,
        }

        while True:
            try:
                res = requests.post(url, json=payload, timeout=10)
                res_json = res.json()
                estado = res_json.get("estado")
                self.cfop = "5.405" if estado == "CE" else "6.102"
                break
            except requests.exceptions.RequestException:
                print("Erro de conexão com Omie na consulta de cliente. Repetindo em 60s...")
                time.sleep(60)

    def _incluir_parcela_omie(self, parcela_nome):
        url = "https://app.omie.com.br/api/v1/geral/parcelas/"
        payload = {
            "call": "IncluirParcela",
            "param": [{"cParcela": str(parcela_nome)}],
            "app_key": self.APP_KEY,
            "app_secret": self.APP_SECRET,
        }
        try:
            res = requests.post(url, json=payload, timeout=10).json()
            if res.get("cCodStatus") == "0":
                print("Parcela cadastrada com sucesso!")
                return res.get("cCodParcela")
            print(f"Erro ao cadastrar parcela: {res.get('cDesStatus')}")
        except Exception as e:
            print(f"Exceção ao cadastrar parcela na Omie: {e}")
        return None

    def deletar_prenota_omie(self):
        """Exclui a pré-nota existente na Omie antes de enviar a atualizada."""
        url = "https://app.omie.com.br/api/v1/produtos/pedido/"
        payload = {
            "call": "ExcluirPedido",
            "param": [{"codigo_pedido": 0, "codigo_pedido_integracao": str(self.codigo_integração)}],
            "app_key": self.APP_KEY,
            "app_secret": self.APP_SECRET,
        }
        res = requests.post(url, json=payload).json()
        if "faultstring" in res and "já foi faturado" in res["faultstring"]:
            print("Erro: Pedido já faturado, não é possível excluir a pré-nota.")
            return False
        print("Pré-nota anterior excluída com sucesso (ou inexistente).")
        return True

    def enviar_prenota_omie(self, tentativa=1):
        """Gera o payload e inclui/atualiza a pré-nota de venda na Omie."""
        cod_int = self.codigo_integração if tentativa == 1 else f"pedido{self.numero}t{tentativa}"
        
        # Prepara a lista de itens
        det = []
        for _, row in self.produtos.iterrows():
            valor_item = max(row["Preço Líq."] * self.pct_faturamento, 0.01)
            det.append({
                "ide": {"codigo_item_integracao": str(row["codigo_omie"])},
                "produto": {
                    "cfop": str(self.cfop),
                    "codigo_produto": str(row["codigo_omie"]),
                    "quantidade": int(row["Qtde."]),
                    "valor_unitario": valor_item,
                },
            })

        payload = {
            "call": "IncluirPedido",
            "param": [{
                "cabecalho": {
                    "codigo_pedido_integracao": cod_int,
                    "codigo_cliente": self.cod_cliente,
                    "data_previsao": datetime.today().strftime("%d/%m/%Y"),
                    "etapa": "50",
                    "codigo_parcela": str(self.cod_parcela),
                    "codigo_cenario_impostos": 9553371106,
                },
                "det": det,
                "frete": {
                    "modalidade": str(self.mod_frete),
                    "quantidade_volumes": self.volumes,
                    "valor_frete": self.frete_nota,
                    "peso_bruto": self.peso_bruto,
                },
                "informacoes_adicionais": {
                    "codigo_categoria": "1.01.03",
                    "codigo_conta_corrente": 9520897830,
                    "numero_pedido_cliente": str(self.numero),
                    "consumidor_final": "S",
                    "enviar_email": "N",
                },
            }],
            "app_key": self.APP_KEY,
            "app_secret": self.APP_SECRET,
        }

        if self.cod_transportadora:
            payload["param"][0]["frete"]["codigo_transportadora"] = self.cod_transportadora

        try:
            res = requests.post("https://app.omie.com.br/api/v1/produtos/pedido/", json=payload, timeout=(5, 10))
            res.raise_for_status()
            print(f"Envio Omie: {res.json().get('descricao_status', 'Sucesso')}")
            return True
        except requests.exceptions.ReadTimeout:
            print("Envio concluído (timeout na resposta do servidor).")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Erro no envio (Tentativa {tentativa}): {e}. Tentando novamente...")
            time.sleep(60)
            return self.enviar_prenota_omie(tentativa=tentativa + 1)

    # -------------------------------------------------------------------------
    # Regras de Negócio e Cálculos de Frete
    # -------------------------------------------------------------------------

    def calcular_ajustes_faturamento(self, pct_input="", mod_frete="9", volumes=1, valor_cotacao=0.0, peso_bruto=0.0):
        """Aplica percentuais de nota, modalidade de frete e regras específicas de transportadora."""
        # 1. Definição do Percentual
        if self.cliente.nome in self.GRUPO_ZIGG:
            self.pct_faturamento = 0.12
        elif pct_input != "":
            try:
                self.pct_faturamento = float(pct_input) / 100.0
            except ValueError:
                self.pct_faturamento = 0.20
        else:
            try:
                self.pct_faturamento = float(self.porcentagem) / 100.0 if self.porcentagem else 0.20
            except ValueError:
                self.pct_faturamento = 0.20

        self.valor_nf = self.valor_pedido * self.pct_faturamento
        self.mod_frete = str(mod_frete)
        self.volumes = int(volumes)
        self.peso_bruto = float(peso_bruto)

        # 2. Regras de Frete Especiais por Transportadora
        if self.transportadora in ["CB EXPRESS", "EXPRESS FORTALEZA", "TRANSCEARA"]:
            valor_cotacao = self._calcular_frete_especial()

        self.valor_cotacao = float(valor_cotacao)

        # 3. Determinação do Frete na NF
        if self.mod_frete in ["9", 9]:
            self.cod_transportadora = False
            self.valor_cotacao = 0.0
            self.frete_nota = 0.0
        elif self.pct_faturamento == 1.0:
            self.frete_nota = self.valor_cotacao
        else:
            self.frete_nota = self.valor_cotacao if (self.valor_cotacao < self.frete_tabelado or self.valor_pedido < 2000) else self.frete_tabelado

        if self.mod_frete == "0" and self.transportadora == "P/ SÃO PAULO":
            self.cod_transportadora = 10021638182

    def _calcular_frete_especial(self):
        cidade = self.cliente.cidade.upper() if self.cliente.cidade else ""
        estado = self.cliente.estado

        if self.transportadora == "CB EXPRESS":
            return max(0.045 * self.valor_nf, 50.0)
        elif self.transportadora == "EXPRESS FORTALEZA":
            return max(0.045 * self.valor_nf, 33.0)
        elif self.transportadora == "TRANSCEARA":
            if estado == "PI":
                return max(0.10 * self.valor_nf, 115.70) if cidade == "TERESINA" else max(0.12 * self.valor_nf, 130.0)
            elif estado == "MA":
                return max(0.13 * self.valor_nf, 141.0) if cidade in ["SÃO LUIS", "SAO LUIS"] else max(0.15 * self.valor_nf, 163.44)
            elif estado == "PA":
                return max(0.16 * self.valor_nf, 184.62)
            elif estado == "PE":
                return max(0.12 * self.valor_nf, 130.43)
        return 0.0

    # -------------------------------------------------------------------------
    # Notion e Exibição
    # -------------------------------------------------------------------------

    def sincronizar_notion(self):
        """Procura ou cria a cotação no Notion e atualiza com os valores calculados."""
        res_cotacao = procura(self.numero, titulo="COTACAO", source=self.COTACAO_ID)
        try:
            id_cotacao = res_cotacao.json()["results"][0]["id"]
        except Exception:
            print(f"Cotação do pedido {self.numero} não encontrada no Notion. Criando...")
            try:
                res_pedido = procura(self.numero)
                id_pedido = res_pedido.json()["results"][0]["id"]
                nova_cot = cria_cotacao(self.numero, id_pedido, self.frete_tabelado)
                id_cotacao = nova_cot.json()["id"]
            except Exception as e:
                print(f"Erro ao vincular pedido no Notion: {e}")
                return False

        atualiza_cotacao(
            id=id_cotacao,
            valor_cotacao=self.valor_cotacao,
            pre_nota=True,
            nota_cheia=(self.pct_faturamento == 1.0),
        )
        return True

    def exibir_painel_informativo(self):
        """Exibe o painel formatado no console."""
        mod_map = {"0": "CIF", "1": "FOB", "9": "SEM FRETE"}
        mod_desc = mod_map.get(str(self.mod_frete), "N/A")

        print("=" * 50)
        print(f"{f'INFORMAÇÕES AJUSTADAS PEDIDO: {self.numero}':^50}")
        print("=" * 50)
        print(f" {'Cliente:':<18} {self.cliente.nome}")
        print(f" {'Vendedor:':<18} {self.vendedor}")
        print(f" {'Pagamento:':<18} {self.condicao_pagamento}")
        print(f" {'Transportadora:':<18} {self.transportadora}")
        print(f" {'Tabela:':<18} {self.tabela_mercos}")
        print("-" * 50)
        print(f" {'Modalidade Frete:':<18} {mod_desc}")
        print(f" {'Volumes:':<18} {self.volumes}")
        print(f" {'Frete Tabelado:':<18} R$ {self.frete_tabelado:,.2f}")
        print(f" {'Cotação:':<18} R$ {self.valor_cotacao:,.2f}")
        print(f" {'Frete NOTA:':<18} R$ {self.frete_nota:,.2f}")
        print(f" {'Valor Pedido:':<18} R$ {self.valor_pedido:,.2f}")
        print(f" {'Valor NF:':<18} R$ {self.valor_nf:,.2f}")
        print(f" {'Porcentagem:':<18} {self.pct_faturamento * 100:.1f}%")
        print("=" * 50)

# if __name__=='__main__':
#     prenota = PreNota(16377)
#     prenota.extrai_produtos()
#     prenota.calcula_frete_tabelado()
#     prenota.itens_fabrica()
#     prenota.exibir_painel_informativo()
#     prenota.deletar_prenota_omie()
#     prenota.calcular_ajustes_faturamento()