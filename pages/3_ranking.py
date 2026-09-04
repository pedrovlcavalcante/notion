import streamlit as st

import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from notion import seleciona_pedidos

st.set_page_config(page_title="Ranking", page_icon="🏅", layout="wide")

st.title("Ranking")
st.write("------------------------------------------------------------")


# data = st.date_input(
#         "Selecione o dia:",
#         min_value="2026-07-01",
#         max_value="today",
#         value="today",
#         format="DD/MM/YYYY"
#     ).strftime("%d/%m/%Y")
dia = 1
mes = datetime.today().month
ano = datetime.today().year

meses = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]

periodo = meses[0:mes]
option_map = {i: month for i, month in enumerate(periodo)}

selection = st.pills(
    "Mês",
    options=option_map.keys(),
    format_func=lambda option: option_map[option],
    selection_mode="single",
)
if selection == None:
    selecao = mes
else:
    selecao = selection+1

data_atual = datetime(ano, selecao, dia).date()
data_futura = data_atual + relativedelta(months=1)

str_data_atual = data_atual.isoformat()
str_data_futura = data_futura.isoformat()
# print(str_data_atual)
# print(str_data_futura)
consulta = seleciona_pedidos(data_atual=str_data_atual, data_futura=str_data_futura).json()
# print(consulta)
pedidos = consulta['results']
tem_mais = consulta['has_more']
prox_pagina = consulta['next_cursor']
# resultados = {'1ª CONFERENTE':[], '2ª CONFERENTE':[], 'DATA':[], 'PEDIDO':[], 'VALOR':[], 'PROGRESSO':[]}
resultados = {'1ª CONFERENTE':[], 'DATA':[], 'PEDIDO':[], 'ITENS':[], 'QUANTIDADE':[]}
lista_pedidos = []
lista_pedidos.append(pedidos)

while tem_mais:
    consulta = seleciona_pedidos(data_atual=str_data_atual, data_futura=str_data_futura, pagina=prox_pagina).json()
    prox_pagina = consulta['next_cursor']
    pedidos = consulta['results']
    tem_mais = consulta['has_more']
    lista_pedidos.append(pedidos)

for resultado in lista_pedidos:
    for pedido in resultado:
        try:
            num_pedido = pedido['properties']['Nome']['title'][0]['text']['content']
        except:
            num_pedido = "00000"
        # progresso = pedido['properties']['PROGRESSO']['status']['name']
        # valor = pedido['properties']['VALOR']['number']
        itens = pedido['properties']['ITENS NO PEDIDO']['number']
        qtd_total = pedido['properties']['QUANTIDADE TOTAL DE ITENS']['number']
        conferente_1 = pedido['properties']['1º CONFERENTE']['select']['name']
        # conferente_2 = pedido['properties']['2º CONFERENTE']['select'] tem muito pedido sem segunda conferente
        
        
        data_pedido = pedido['properties']['Criado em']['created_time']
        data_pedido = datetime.strptime(data_pedido.split("T")[0], "%Y-%m-%d").date().isoformat()

        resultados['1ª CONFERENTE'].append(conferente_1)
        # resultados['2ª CONFERENTE'].append(conferente_2)
        resultados['PEDIDO'].append(num_pedido)
        resultados['ITENS'].append(itens)
        resultados['QUANTIDADE'].append(qtd_total)
        resultados['DATA'].append(data_pedido)


df = pd.DataFrame(resultados)
num_pedidos_conferidos = df["1ª CONFERENTE"].value_counts()
media_itens = df['ITENS'].mean()
std_itens = df['ITENS'].std()
media_quantidade = df['QUANTIDADE'].mean()
std_quantidade = df['QUANTIDADE'].std()
df['ITENS (Z)'] = df['ITENS'].apply(lambda x: (x - df['ITENS'].min())/(df['ITENS'].max() - df['ITENS'].min()))
df['QUANTIDADE (Z)'] = df['QUANTIDADE'].apply(lambda x: (x - df['QUANTIDADE'].min())/(df['QUANTIDADE'].max() - df['QUANTIDADE'].min()))
df['NOTA DIF'] = df['ITENS (Z)'].apply(lambda x: x*0.5) + df['QUANTIDADE (Z)'].apply(lambda x: x*0.5)
df['PROD'] = df['NOTA DIF']*df['QUANTIDADE']

# print(nota_z_itens)
# print("media ", media_itens)
# st.write(df)

resultado = (
    df.groupby("1ª CONFERENTE")
    .agg(
        NUM_PEDIDOS_CONFERIDOS=("1ª CONFERENTE", "value_counts"),
        ITENS=("ITENS", "sum"),
        QUANTIDADE=("QUANTIDADE", "sum"),
        MEDIA_ITENS=("ITENS", "mean"),
        MEDIA_QUANTIDADE=("QUANTIDADE", "mean"),
        STD_ITENS=("ITENS", "std"),
        STD_QUANTIDADE=("QUANTIDADE", "std"),
        NOTA=("NOTA DIF", "sum"),
        PONTUAÇÃO=("PROD", "sum")
    )
).reset_index()
resultado['IPP'] = resultado['PONTUAÇÃO']/df['QUANTIDADE'].sum()
resultado.sort_values(by=['IPP', 'PONTUAÇÃO'], ascending=False, inplace=True)
resultado.reset_index(inplace=True, drop=True)

# podium = pd.DataFrame(resultado)
# df = pd.DataFrame(conferente)
# st.write(df.loc["1ª CONFERENTE"]["QUANTIDADE"].mean())
# st.write(itens_conferidos)
# st.write(resultado)

# 1. Config columns with bottom-alignment to mimic the ground floor
col_2nd, col_1st, col_3rd = st.columns([1, 1, 1], border=True, vertical_alignment='bottom')

# 2. Configure the 2nd Place Container (Medium height)
with col_2nd:
    st.markdown("<h3 style='text-align: center;'>🥈 2º Lugar</h3>", unsafe_allow_html=True)
    with st.container(height='content'):
        st.markdown(f"<h4 style='text-align: center;'>{resultado["1ª CONFERENTE"][1]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Pedidos Conferidos: {resultado['NUM_PEDIDOS_CONFERIDOS'][1]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Itens Conferidos: {resultado['ITENS'][1]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Quantidade total: {resultado['QUANTIDADE'][1]}</h4>", unsafe_allow_html=True)
        st.space(180)
        # st.link_button("View Profile", "https://github.com")

# 3. Configure the 1st Place Container (Tallest height)
with col_1st:
    # st.space('small')
    st.markdown("<h3 style='text-align: center;'>🥇 1º Lugar</h3>", unsafe_allow_html=True)
    with st.container(height='content'):
        st.markdown(f"<h4 style='text-align: center;'>{resultado["1ª CONFERENTE"][0]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Pedidos Conferidos: {resultado['NUM_PEDIDOS_CONFERIDOS'][0]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Itens Conferidos: {resultado['ITENS'][0]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Quantidade total: {resultado['QUANTIDADE'][0]}</h4>", unsafe_allow_html=True)
        st.space(300)
        # st.link_button("View Profile", "https://github.com")

# 4. Configure the 3rd Place Container (Shortest height)
with col_3rd:
    st.markdown("<h3 style='text-align: center;'>🥉 3º Lugar</h3>", unsafe_allow_html=True)
    with st.container(height='content'):
        st.markdown(f"<h4 style='text-align: center;'>{resultado["1ª CONFERENTE"][2]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Pedidos Conferidos: {resultado['NUM_PEDIDOS_CONFERIDOS'][2]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Itens Conferidos: {resultado['ITENS'][2]}</h4>", unsafe_allow_html=True)
        st.write(f"<h4 style='text-align: center;'>Quantidade total: {resultado['QUANTIDADE'][2]}</h4>", unsafe_allow_html=True)
        st.space(70)
    #     st.link_button("View Profile", "https://github.com")