import streamlit as st
import pandas as pd
from notion import coletados, procura
from datetime import datetime

st.set_page_config(page_title="Saídas", page_icon="📈", layout="wide")

st.title("Saídas")
st.write("------------------------------------------------------------")

data = st.date_input(
        "Selecione o dia:",
        min_value="2026-07-01",
        max_value="today",
        value="today",
        format="DD/MM/YYYY"
    ).strftime("%d/%m/%Y")

saidas = coletados(data).json()['results']
resultados = {'Data de Coleta':[], 'Pedidos':[], 'Volumes':[], 'Vendedor':[], 'Equipe':[]}

for coleta in saidas:
    
    pedido = coleta['properties']['Nome']['title'][0]['text']['content']
    try:
        vendedor = coleta['properties']['VENDEDOR']['rich_text'][0]['text']['content']
        equipe = coleta['properties']['EQUIPE']['rich_text'][0]['text']['content']
    except:
        vendedor = 'VENDEDOR NÃO CADASTRADO'
        equipe = 'EQUIPE NÃO ENCONTRADA'
        
    volumes = coleta['properties']['VOLUMES']['number']
    # volumes = coleta
    data_coleta = coleta['properties']['DATA DE COLETA']['date']['start']
    data_coleta = datetime.strptime(data_coleta.split("T")[0], "%Y-%m-%d").date().isoformat()
    resultados['Pedidos'].append(pedido)
    resultados['Vendedor'].append(vendedor)
    resultados['Volumes'].append(volumes)
    resultados['Equipe'].append(equipe)
    resultados['Data de Coleta'].append(data_coleta)

df = pd.DataFrame(resultados)

#Caixa de pesquisa por numero do pedido
numero_pesquisa = st.sidebar.number_input(
    label="Digite o número do Pedido para buscar:", 
    min_value=0, 
    step=1, 
    format="%i",
)
st.sidebar.info("Digite um número acima para pesquisar.")

# Caixa de seleção das equipes
equipes = df["Equipe"].unique()
filtro_equipes = st.sidebar.multiselect(
    "Selecione a equipe:", 
    equipes,
    # default=equipes, # Vem com todas selecionadas por padrão
    placeholder='Escolha a equipe'
)

# Cria o filtro de equipe, base para o filtro de vendedores
if filtro_equipes:
    dados_filtrados = df[df['Equipe'].isin(filtro_equipes)]
else:
    dados_filtrados = df # Mostra todos se nada for selecionado

vendedores = dados_filtrados["Vendedor"].unique()

# Cria o filtro de vendedores
filtro_vendedor = st.sidebar.multiselect(
    "Selecione o vendedor:", 
    vendedores,
    # default=equipes, # Vem com todas selecionadas por padrão
    placeholder='Escolha o vendedor'
)

# 4. Filtrando o DataFrame com base na equipe, vendedores e data
if filtro_equipes or filtro_vendedor:
    if filtro_vendedor:
        dados_filtrados = df[df['Vendedor'].isin(filtro_vendedor)]
    if filtro_equipes:
        dados_filtrados = df[df['Equipe'].isin(filtro_equipes)]
    if filtro_equipes and filtro_vendedor:
        dados_filtrados = df[(df['Equipe'].isin(filtro_equipes)) & (df["Vendedor"].isin(filtro_vendedor))]
else:
    dados_filtrados = df # Mostra todos se nada for selecionado

st.dataframe(
    dados_filtrados,
    hide_index=True
)

if numero_pesquisa > 0:

    try: 
        pesquisa = procura(numero_pesquisa)
        print(pesquisa.json())
        pesq_data_coleta = datetime.fromisoformat(pesquisa.json()['results'][0]['properties']['DATA DE COLETA']['date']['start']).date().isoformat()
        pesq_pedido = pesquisa.json()['results'][0]['properties']['Nome']['title'][0]['text']['content']
        pesq_volume = pesquisa.json()['results'][0]['properties']['VOLUMES']['number']
        try:
            pesq_vendedor = pesquisa.json()['results'][0]['properties']['VENDEDOR']['rich_text'][0]['text']['content']
            pesq_equipe = pesquisa.json()['results'][0]['properties']['EQUIPE']['rich_text'][0]['text']['content']
        except:
            pesq_vendedor = "VENDEDOR NÃO CADASTRADO"
            pesq_equipe = "EQUIPE NÃO ENCONTRADA"
        dict_pesquisa = {'Data de Coleta':[pesq_data_coleta], 'Pedidos':[pesq_pedido], 'Volumes':[pesq_volume], 'Vendedor':[pesq_vendedor], 'Equipe':[pesq_equipe]}
        resultado = pd.DataFrame(dict_pesquisa)
        st.write(resultado)
    except:
        st.warning("Nenhum pedido encontrado com este número.")
