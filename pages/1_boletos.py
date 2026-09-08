import streamlit as st
import pandas as pd
from notion import consulta_boletos, procura
from datetime import datetime

st.set_page_config(page_title="Boletos", page_icon="🧾", layout="wide")

@st.dialog("LEMBRETE PARA A KARINE")
def abrir_popup():
    st.write("FAZER A SUBSTITUIÇÃO DO PEDIDO 15669, A NOTA JA FOI CANCELADA!")
    if st.button("Fechar"):
        st.rerun()

st.title("Boletos")
st.write("------------------------------------------------------------")


# 2. Botão para disparar o popup
if datetime.today().strftime(format="%Y-%m-%d") == "2026-09-04" and datetime.today().hour < 10:
    if st.button("Clique: LEMBRETE PARA A KARINE"):
        abrir_popup()

def ordem_importancia(df):
    ordem = {
        'EM ANÁLISE'.upper():0,
        'Não aprovado'.upper():1,
        'Aprovado'.upper():2,
        'Impresso'.upper():3,
        '3ª ANDAR'.upper():4,
        '2ª ANDAR'.upper():5,
        '1ª ANDAR'.upper():6,
        'SEPARAÇÃO LOJA'.upper():7,
        'SEPARAÇÃO JACARECANGA':8,
        'Fila Conferência'.upper():9,
        'Conferência'.upper():10,
        '2ª CONFERENCIA'.upper():11,
        'PENDÊNCIA PRODUTOS'.upper():12,
        'PENDÊNCIA GALPÃO'.upper():12.1,
        'PENDÊNCIA JACARECANGA'.upper():12.2,
        'PENDÊNCIA LOJA'.upper():12.3,
        'Itens da Fábrica'.upper():13,
        'AGD COMPLEMENTO'.upper():13.1,
        'AGUARDANDO CONTÊINER MILI'.upper():13.2,
        'Retorno Representante'.upper():14,
        'FECHAR'.upper():15,
        'Cotação'.upper():16,
        'Fila Faturamento'.upper():17,
        'Aguardando Coleta'.upper():18,
        'Coletado'.upper():19,
        'Pendente'.upper():20,
        'Faturados Abertos'.upper():21
    }

    df["peso"] = df["PROGRESSO"].map(ordem)
    df_ordenado = df.sort_values("peso").drop(columns=["peso"])
    return df_ordenado

def color_rows(row):
    # Default style if condition isn't met
    style = [''] * len(row)

    cores = {
        'EM ANÁLISE':'#858C99',
        'Não aprovado'.upper():'#FF1F23',
        'Aprovado'.upper():'#2BF346',
        'Impresso'.upper():'#E5C238',
        '3ª ANDAR'.upper():'#EAAD34',
        '2ª ANDAR'.upper():'#EAAD34',
        '1ª ANDAR'.upper():'#EAAD34',
        'SEPARAÇÃO LOJA':'#F8FF1F',
        'SEPARAÇÃO JACARECANGA':'#F8FF1F',
        'Fila Conferência'.upper():'#DFAAD4',
        'Conferência'.upper():'#F395E8',
        '2ª CONFERENCIA':'#F395E8',
        'PENDÊNCIA PRODUTOS':'#FDAE54',
        'PENDÊNCIA GALPÃO':"#DAB995",
        'PENDÊNCIA JACARECANGA':"#DFC999",
        'PENDÊNCIA LOJA':"#9E8348",
        'Fita Fracionada'.upper():'#FDAE54',
        'Itens da Fábrica'.upper():'#E56C82',
        'Retorno Representante'.upper():'#96C3F3',
        'FECHAR':'#5C87FF',
        'Cotação'.upper():'#CBF8C4',
        'Fila Faturamento'.upper():'#9EEC92',
        'Aguardando Coleta'.upper():'#7FE66B',
        'AGD COMPLEMENTO'.upper():'#7FE66B',
        'AGUARDANDO CONTÊINER MILI'.upper():"#CD9BEE",
        'Coletado'.upper():'#35AC20',
        'Pendente'.upper():'#BA1212',
        'Faturados Abertos'.upper():'#7FE66B'
    }
    if row['PROGRESSO'] in cores.keys():
        progresso = row['PROGRESSO']
        style = [f'background-color: {cores[progresso]}; color: #000000'] * len(row)
    else:
        style = [''] * len(row)
    return style

boletos = consulta_boletos().json()['results']
# st.write(boletos)
resultados = {'DATA':[], 'PEDIDO':[], 'CLIENTE':[], 'REPRESENTANTE':[], 'VALOR':[], 'PROGRESSO':[]}

for boleto in boletos:
    
    pedido = boleto['properties']['Nome']['title'][0]['text']['content']
    progresso = boleto['properties']['PROGRESSO']['status']['name']
    valor = boleto['properties']['VALOR']['number']
    try:
        vendedor = boleto['properties']['VENDEDOR']['rich_text'][0]['text']['content']
        cliente = boleto['properties']['CLIENTE']['rich_text'][0]['text']['content']
        
    except:
        cliente = 'CLIENTE NÃO CADASTRADO'
        vendedor = 'VENDEDOR NÃO CADASTRADO'
        equipe = 'EQUIPE NÃO ENCONTRADA'
        
    volumes = boleto['properties']['VOLUMES']['number']
    
    data_pedido = boleto['properties']['Criado em']['created_time']
    data_pedido = datetime.strptime(data_pedido.split("T")[0], "%Y-%m-%d").date().isoformat()
    
    resultados['PEDIDO'].append(pedido)
    resultados['REPRESENTANTE'].append(vendedor)
    resultados['CLIENTE'].append(cliente)
    resultados['VALOR'].append(valor)
    resultados['PROGRESSO'].append(progresso)
    resultados['DATA'].append(data_pedido)

df_pre_order = pd.DataFrame(resultados)
grupos = df_pre_order["PROGRESSO"].value_counts()

cols = st.columns(len(grupos), vertical_alignment='bottom')
g = grupos.index
for col, grupo, numero in zip(cols,g, grupos) :
    with col:
        st.markdown(
            f'<span style="font-size: 10px; color: white; text-align: center;">{grupo}</span>', 
            unsafe_allow_html=True
        )
        st.markdown(
            f'<span style="font-size: 15px; color: white; text-align: center;">{numero}</span>', 
            unsafe_allow_html=True
        )
st.space(10)

df = ordem_importancia(df_pre_order)
styled_df = df.style.apply(color_rows, axis=1)

st.dataframe(
    styled_df,
    column_config={
        "DATA": st.column_config.Column("DATA", width="small"),
        "PEDIDO": st.column_config.Column("PEDIDO", width="small"),
        "CLIENTE": st.column_config.Column("CLIENTE", width="medium"),
        "PROGRESSO": st.column_config.Column("PROGRESSO", width="large"),
        "VALOR": st.column_config.NumberColumn("VALOR", format="R$ %.2f")
    },
    # use_container_width=True,
    width='stretch',
    hide_index=True,
)

#Caixa de pesquisa por numero do pedido
numero_pesquisa = st.sidebar.number_input(
    label="Digite o número do Pedido para buscar:", 
    min_value=0, 
    step=1, 
    format="%i",
)
st.sidebar.info("Digite um número acima para pesquisar.")

# # Filtragem em tempo real da pesquisa por pedido
if numero_pesquisa > 0:
    try: 
        pesquisa = procura(numero_pesquisa)
        print(pesquisa.json())
        data_pesquisa = pesquisa.json()['results'][0]['created_time']
        data_pesquisa = datetime.strptime(data_pedido.split("T")[0], "%Y-%m-%d").date().isoformat()
        pesq_pedido = pesquisa.json()['results'][0]['properties']['Nome']['title'][0]['text']['content']
        pesq_valor = pesquisa.json()['results'][0]['properties']['VALOR']['number']
        pesq_progresso = pesquisa.json()['results'][0]['properties']['PROGRESSO']['status']['name']
        try:
            pesq_vendedor = pesquisa.json()['results'][0]['properties']['VENDEDOR']['rich_text'][0]['text']['content']
            pesq_cliente = pesquisa.json()['results'][0]['properties']['CLIENTE']['rich_text'][0]['text']['content']
        except:
            pesq_vendedor = "VENDEDOR NÃO CADASTRADO"
            pesq_cliente = "CLIENTE NÃO ENCONTRADA"
        dict_pesquisa = {'DATA':[data_pesquisa], 'PEDIDO':[pesq_pedido], 'CLIENTE':[pesq_cliente], 'REPRESENTANTE':[pesq_vendedor], 'VALOR':[pesq_valor], 'PROGRESSO':[pesq_progresso]}
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
    except:
        st.warning("Nenhum pedido encontrado com este número.")   