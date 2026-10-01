import streamlit as st
import pandas as pd
import requests, os, base64
from dotenv import load_dotenv
from notion import procura, propriedade_cliente, atualiza_cotacao
from datetime import datetime

load_dotenv('credentials.env')
cnpj_rementente = os.getenv("CNPJ_REMETENTE")
usuario = os.getenv("BRASPRESS_USUARIO")
senha = os.getenv("BRASPRESS_SENHA")
cep_origem = os.getenv("CEP")
id_cnpj = os.getenv("ID_CNPJ")
id_cep = os.getenv("ID_CEP")

# Junta os valores no formato 'usuario:senha'
credenciais = f"{usuario}:{senha}"

# Codifica para Base64 (requer transformar a string em bytes primeiro)
credenciais_bytes = credenciais.encode("utf-8")
base64_bytes = base64.b64encode(credenciais_bytes)
base64_string = base64_bytes.decode("utf-8")

def formatar_cnpj(cnpj):
    # Converte para string e garante que tenha 14 dígitos preenchendo com zeros à esquerda
    cnpj_limpo = str(cnpj).strip().zfill(14)
    # Aplica a máscara: 00.000.000/0000-00
    return f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"

def formatar_cep(cep):
    # Converte para string e garante que tenha 8 dígitos preenchendo com zeros à esquerda
    cep_limpo = str(cep).strip().zfill(8)
    # Aplica a máscara: 00000-000
    return f"{cep_limpo[:5]}-{cep_limpo[5:]}"

st.set_page_config(page_title="Calculadora de Cotação", layout="wide")
st.title("Sistema de Cotação de Volumes")

#Caixa de pesquisa por numero do pedido
numero_pesquisa = st.sidebar.number_input(
    label="Digite o número do Pedido para buscar:", 
    min_value=0, 
    step=1, 
    format="%i",
)
st.sidebar.info("Digite um número acima para pesquisar.")
# pesquisa = procura(numero_pesquisa)
# id_cliente = pesquisa.json()
# st.write(id_cliente)
# # Filtragem em tempo real da pesquisa por pedido
if numero_pesquisa > 0:
    try: 
        pesquisa = procura(numero_pesquisa)
        # print(pesquisa.json())
        id_cliente = pesquisa.json()['results'][0]['properties']['CLIENTES']['relation'][0]['id']
        id_cotacao = pesquisa.json()['results'][0]['properties']['COTAÇÕES']['relation'][0]['id']
        st.write(id_cliente)

        cnpj_destinatario_bruto = propriedade_cliente(id_cliente, id_cnpj)
        cep_destinatario_bruto = propriedade_cliente(id_cliente, id_cep)
        #.replace('.','').replace('/','').replace('-','')
        #[0]['title']['text']['content']
        #[0]['title']['text']['content']
        cnpj_destinatario = cnpj_destinatario_bruto.json()['results'][0]['title']['text']['content'].replace('.','').replace('/','').replace('-','')
        cep_destinatario = cep_destinatario_bruto.json()['results'][0]['rich_text']['text']['content'].replace('-','')
        url = pesquisa.json()['results'][0]['properties']['LINK']['url']

        st.write(cnpj_destinatario)
        st.write(cep_destinatario)
        st.write(url)
        
        data_pedido = pesquisa.json()['results'][0]['properties']['DATA DO PEDIDO']['date']['start']
        pesq_pedido = pesquisa.json()['results'][0]['properties']['Nome']['title'][0]['text']['content']
        input_valor_pedido = pesquisa.json()['results'][0]['properties']['VALOR']['number']
        pesq_progresso = pesquisa.json()['results'][0]['properties']['PROGRESSO']['status']['name']
        try:
            pesq_vendedor = pesquisa.json()['results'][0]['properties']['VENDEDOR']['rich_text'][0]['text']['content']
            pesq_cliente = pesquisa.json()['results'][0]['properties']['CLIENTE']['rich_text'][0]['text']['content']
        except:
            pesq_vendedor = "VENDEDOR NÃO CADASTRADO"
            pesq_cliente = "CLIENTE NÃO ENCONTRADA"
        dict_pesquisa = {'DATA':[data_pedido], 'PEDIDO':[pesq_pedido], 'CLIENTE':[pesq_cliente], 'REPRESENTANTE':[pesq_vendedor], 'VALOR':[input_valor_pedido], 'PROGRESSO':[pesq_progresso]}
        resultado = pd.DataFrame(dict_pesquisa)
        st.dataframe(
            resultado,
            column_config={
                "DATA": st.column_config.Column("DATA", width="small"),
                "PEDIDO": st.column_config.Column("PEDIDO", width="small"),
                "CLIENTE": st.column_config.Column("CLIENTE", width="medium"),
                "PROGRESSO": st.column_config.Column("PROGRESSO", width="large"),
                "VALOR": st.column_config.NumberColumn("VALOR", format="R$ %.2f")
            },
            use_container_width=True,
            hide_index=True,
        )
        valor_pedido_alternativo = st.text_input("Valor pedido:")
        modal = st.selectbox("Modal", ['Rodoviário', 'Aéreo'])
        avulso = False
    except Exception as e:
        avulso = True
        st.warning("Nenhum pedido encontrado com este número.")
        cnpj_destinatario = st.text_input("CNPJ DESTINATÁRIO:")
        cep_destinatario = st.text_input("CEP DESTINATÁRIO:")
        input_valor_pedido = st.text_input("Valor do Pedido:")
        modal = st.selectbox("Modal", ['Rodoviário', 'Aéreo'])

API_URL = "https://api.braspress.com/v1/cotacao/calcular/json"

# --- INICIALIZAÇÃO DO ESTADO (SESSION STATE) ---
if "volumes_list" not in st.session_state:
    st.session_state.volumes_list = []

if "cotacao_gerada" not in st.session_state:
    st.session_state.cotacao_gerada = False

if "payload_cotacao" not in st.session_state:
    st.session_state.payload_cotacao = None

def parse_valor_pedido(valor_pedido):
    if not valor_pedido or not str(valor_pedido).strip():
        return 0.0

    clean_str = str(valor_pedido).replace("R$", "").strip().replace(",", ".")
    return float(clean_str)

def parse_input_value(value_str):

    """
    Converte a string digitada para float.
    Se digitar '10' -> 0.10. Se digitar '0,10' -> 0.10.
    """
    if not value_str or not str(value_str).strip():
        return 0.0

    clean_str = str(value_str).replace("R$", "").strip().replace(",", ".")

    try:
        if "." not in clean_str:
            return float(clean_str) / 100.0
        else:
            return float(clean_str)
    except ValueError:
        return 0.0
try:
    if not valor_pedido_alternativo:
        
            valor_pedido = parse_valor_pedido(input_valor_pedido)

    else:
        valor_pedido = parse_valor_pedido(valor_pedido_alternativo)
except:
    valor_pedido = 0
st.write("Pesquise o pedido para cotação")
# --- FORMULÁRIO PRINCIPAL ---
col1, col2, col3 = st.columns(3)

with col3:
    pct_input = st.text_input(
        "Porcentagem da Nota",
        placeholder="20%",
        key="nota",
        value=20
    )

pct_nota = parse_input_value(pct_input)

with col1:
    peso_input = st.text_input(
        "Peso Total (kg) (*)",
        placeholder="0,00",
        key="peso_str"
    )

with col2:
    if not valor_pedido:
        valor_input = st.text_input(
            "Valor da Nota Fiscal (R$) (*)",
            placeholder=f"{valor_pedido}",
            key="valor_str"
        )
    else:
        valor_input = valor_pedido*pct_nota
        st.text("Valor Nota Fiscal Calculada")
        st.text(f"{valor_input}")

# with col2:
#     valor_input = valor_pedido*parse_input_value(pct_nota)


st.divider()
st.subheader("Adicionar Dimensões do Volume")

# Campos de entrada com Placeholder limpo
c1, c2, c3, c4 = st.columns(4)

with c1:
    comp_input = st.text_input("Comprimento (m)", placeholder="0,00", key="comp_str")

with c2:
    larg_input = st.text_input("Largura (m)", placeholder="0,00", key="larg_str")

with c3:
    alt_input = st.text_input("Altura (m)", placeholder="0,00", key="alt_str")

with c4:
    qtd_input = st.number_input("Nº de Volumes", min_value=1, value=1, step=1, key="qtd_num")

# Botão para adicionar à lista
if st.button("➕ Adicionar Volume à Tabela"):
    comp = parse_input_value(comp_input)
    larg = parse_input_value(larg_input)
    alt = parse_input_value(alt_input)
    qtd = int(qtd_input)

    if comp > 0 and larg > 0 and alt > 0:
        volumetria = comp * larg * alt * qtd
        st.session_state.volumes_list.append({
            "Comprimento (m)": comp,
            "Largura (m)": larg,
            "Altura (m)": alt,
            "Qtd Volumes": qtd,
            "Volumetria (m³)": round(volumetria, 4)
        })
        # Reseta o estado da cotação caso adicione um novo volume
        st.session_state.cotacao_gerada = False
        st.success("Volume adicionado!")
    else:
        st.warning("Preencha as dimensões do volume antes de adicionar.")

st.divider()

# --- TABELA INTERATIVA COM RECÁLCULO AUTOMÁTICO DE VOLUMETRIA ---
if st.session_state.volumes_list:
    st.subheader("Volumes Registrados")
    st.caption("💡 Caso edite algum valor na tabela ou exclua linhas, a volumetria total será recalculada automaticamente.")

    df_volumes = pd.DataFrame(st.session_state.volumes_list)

    # Exibe a tabela interativa sem a coluna de volumetria pré-calculada para edição livre
    cols_editaveis = ["Comprimento (m)", "Largura (m)", "Altura (m)", "Qtd Volumes"]
    
    df_editado = st.data_editor(
        df_volumes[cols_editaveis],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Comprimento (m)": st.column_config.NumberColumn(format="%.2f", min_value=0.0),
            "Largura (m)": st.column_config.NumberColumn(format="%.2f", min_value=0.0),
            "Altura (m)": st.column_config.NumberColumn(format="%.2f", min_value=0.0),
            "Qtd Volumes": st.column_config.NumberColumn(step=1, min_value=1),
        },
        key="editor_volumes"
    )

    # Recalcula a volumetria dinamicamente para cada linha editada
    if not df_editado.empty:
        df_editado["Volumetria (m³)"] = (
            df_editado["Comprimento (m)"] * 
            df_editado["Largura (m)"] * 
            df_editado["Altura (m)"] * 
            df_editado["Qtd Volumes"]
        ).round(4)

        # Atualiza o Session State com a tabela recalculada
        st.session_state.volumes_list = df_editado.to_dict(orient="records")

    if st.button("🗑️ Limpar Toda a Tabela"):
        st.session_state.volumes_list = []
        st.session_state.cotacao_gerada = False
        st.rerun()

st.divider()

# --- BOTÃO FINAL DE GERAR COTAÇÃO ---
if st.button("🚀 Gerar Cotação", type="primary"):
    peso_final = parse_input_value(peso_input)
    valor_final = parse_input_value(valor_input)

    if not st.session_state.volumes_list:
        st.warning("Adicione pelo menos um volume antes de gerar a cotação.")
        st.session_state.cotacao_gerada = False
    else:
        # Prepara o payload e salva no estado
        volumes_payload = [
            {
                "comprimento": float(item["Comprimento (m)"]),
                "largura": float(item["Largura (m)"]),
                "altura": float(item["Altura (m)"]),
                "volumes": int(item["Qtd Volumes"])
            }
            for item in st.session_state.volumes_list
        ]
        total_vols = sum(item["volumes"] for item in volumes_payload)
        if modal == "Rodoviário":
            m = "R"
        else:
            m = "A"
        st.session_state.payload_cotacao = {
            "cnpjRemetente": cnpj_rementente,
            "cnpjDestinatario": cnpj_destinatario,
            "modal": m,
            "tipoFrete": 1,
            "cepOrigem": cep_origem,
            "cepDestino": cep_destinatario,
            "vlrMercadoria": valor_final,
            "peso": peso_final,
            "volumes": total_vols,
            "cubagem": volumes_payload
        }

        st.session_state.cotacao_gerada = True
        st.success("Cotação processada com sucesso!")
    
# --- EXIBIÇÃO E ENVIO DA COTAÇÃO (INDEPENDENTE DO CLIQUE RECENTE DO BOTÃO) ---
if st.session_state.cotacao_gerada and st.session_state.payload_cotacao:
    payload = st.session_state.payload_cotacao
    total_vols = payload["volumes"]

    m1, m2, m3 = st.columns(3)
    m1.metric("Peso Total", f"{payload['peso']:.2f} kg")
    m2.metric("Valor da Mercadoria", f"R$ {payload['vlrMercadoria']:.2f}")
    m3.metric("Total de Volumes", total_vols)

    # st.subheader("Payload de Envio:")
    # st.json(payload)

    # Botão de Envio posicionado de forma persistente
    if st.button("📤 Enviar para a Transportadora", type="secondary"):
        headers = {
            "Authorization": f"Basic {base64_string}",
            "Content-Type": "application/json",
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'
        }
        
        try:
            with st.spinner("Enviando cotação para a API..."):
                response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
                if response.status_code == 200:
                    st.success("Cotação enviada com sucesso!")
                    res1, res2, res3, res4, res5 = st.columns(5)
                    with res1:
                        protocolo = response.json()['id']
                        st.metric("Protocolo", protocolo)
                    with res2:
                        prazo = response.json()['prazo']
                        st.metric("Dias úteis / Horas", prazo)
                    with res3:
                        valor_frete = response.json()['totalFrete']
                        st.metric("Valor total frete", valor_frete)
                    with res4:
                        data_cotacao = datetime.today().date()
                        st.metric("Data da Simulação", data_cotacao.strftime('%d/%m/%Y'))
                    with res5:
                        st.metric("Modal", modal)
                    if not avulso:
                        atualiza_cotacao(id_cotacao, data_cotacao.isoformat(), valor_frete, prazo)
                    else:
                        pass
                else:
                    st.error(f"Erro na API ({response.status_code}): {response.text}")
        except Exception as e:
            st.error(f"Falha ao conectar na API: {e}")

    if 'volumes_payload' in locals() and volumes_payload:
        blocos_caixas = []
        for item in volumes_payload:
            c = int(item["comprimento"] * 100)
            l = int(item["largura"] * 100)
            a = int(item["altura"] * 100)
            qtd = item["volumes"]
        
            bloco = (
                f"{qtd} CX\n"
                f"C: {c}\n"
                f"L: {l}\n"
                f"A: {a}")
            blocos_caixas.append(bloco)

        texto_caixas = "\n\n".join(blocos_caixas)

        cnpj_formatado_remetente = formatar_cnpj(cnpj_rementente)
        cep_formatado_remetente = formatar_cep(cep_origem)
        cnpj_formatado_destinatario = formatar_cnpj(cnpj_destinatario)
        cep_formatado_destinatario = formatar_cep(cep_destinatario)

        texto_ajustado = (
        f"CNPJ pagador: {cnpj_formatado_remetente}\n"
        f"CEP pagador : {cep_formatado_remetente}\n\n"
        f"CNPJ destinatário: {cnpj_formatado_destinatario}\n"
        f"CEP destinatário: {cep_formatado_destinatario}\n\n"
        f"{texto_caixas}\n\n"
        f"{total_vols} VOLUMES\n\n"
        f"PESO TOTAL: {peso_final} KG\n"
        f"NF: R$ {valor_final:.2f}\n"
        f"PEDIDO {numero_pesquisa}"
        )   


    # 1. Cria a caixa que esconde/mostra o conteúdo ao clicar
        with st.expander("Texto para WhatsApp"):
            
            # 2. Exibe o texto com fonte monoespaçada e o botão de copiar automático
            st.code(texto_ajustado, language="text")