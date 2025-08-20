import streamlit as st
import requests 
import pandas as pd
import plotly.express as px
import logging as log

# Ajusta a página por padrão
st.set_page_config(layout='wide')

# Função que ajusta as unidades de medida de acordo com o valor
def formata_numero(valor, prefixo= ''):
    for unidade in ['', 'mil']:
        if valor < 1000:
            return f'{prefixo}{valor:.2f} {unidade}'
        valor /= 1000
    return f'{prefixo}{valor:.2f} milhões'
    
# Titulo 
st.title('DASHBOARD DE VENDAS :shopping_trolley:')



# # --- PASSO DE DEBUG: TESTE MÍNIMO E ISOLADO ---
# # Vamos criar um DataFrame de teste, 100% controlado por nós, para verificar se o Plotly funciona.
# # Se este gráfico aparecer corretamente, o problema está nos dados que vêm da URL.
# # Se este gráfico também falhar, o problema está na sua instalação/ambiente (conflito de versões).
# st.header("--- INÍCIO DO TESTE DE AMBIENTE ---")
# st.info("Esta seção é um teste para diagnosticar o problema. Se o gráfico abaixo aparecer corretamente, seu ambiente está OK.")
# teste_df = pd.DataFrame({
#     'Categoria': ['Eletrônicos', 'Móveis', 'Livros'],
#     'Valor': [150000, 250000, 85000]
# })
# st.write("DataFrame de Teste Criado Manualmente:")
# st.dataframe(teste_df)
# try:
#     fig_teste = px.bar(teste_df, x='Categoria', y='Valor', title="GRÁFICO DE TESTE MÍNIMO", text_auto=True)
#     st.plotly_chart(fig_teste)
#     st.success("Diagnóstico: O ambiente de plotagem parece estar funcionando corretamente.")
# except Exception as e:
#     st.error(f"Diagnóstico: Ocorreu um erro ao plotar o gráfico de teste: {e}")
# st.header("--- FIM DO TESTE DE AMBIENTE ---")
# st.markdown("---") # Linha divisória
# # ----------------------------------------------------




# URL do endpoint
url = 'https://labdados.com/produtos'

regioes = ['Brasil', 'Centro-Oeste', 'Nordeste', 'Norte', 'Sudeste', 'Sul']

st.sidebar.title('Filtros')
regiao = st.sidebar.selectbox('Região', regioes)

if regiao == 'Brasil':
    regiao = ''

todos_anos = st.sidebar.checkbox('Dados de todo o periodo', value=True)
if todos_anos:
    ano = ''
else:
    ano = st.sidebar.slider('Ano', 2020, 2023)

# Adiciona os parâmetros à URL
query_string = {'regiao':regiao.lower(), 'ano':ano}

# Requisição GET para obter os dados
response = requests.get(url, params=query_string)

# Verifica se a requisição foi bem sucedida
if response.status_code == 200:
    try:
        # Tranformar em JSON
        dados = pd.DataFrame.from_dict(response.json())
        dados['Data da Compra'] = pd.to_datetime(dados['Data da Compra'], format='%d/%m/%Y')


        filtro_vendedores = st.sidebar.multiselect('Vendedores', options=dados['Vendedor'].unique())
        if filtro_vendedores:
            dados = dados[dados['Vendedor'].isin(filtro_vendedores)]
        ## Tabela que contém a receita por estado

        # Agrupando os dados por estado e somando os preços. Obs.: Note que o novo index é o 'Local da compra'
        receita_estados = dados.groupby('Local da compra')[['Preço']].sum()
        # Adicionando as coordenadas geográficas (latitude e longitude) para cada estado
        locais_unicos = dados.drop_duplicates(subset='Local da compra')[['Local da compra', 'lat', 'lon']]
        
        receita_final = pd.merge(receita_estados, locais_unicos, on='Local da compra', how='left').sort_values('Preço', ascending=False)
        receita_final = receita_final.reset_index()

        ## Tabela que contém a receita mensal e por categoria de produto
        # Valor de receita mensal 
        receita_mensal = dados.set_index('Data da Compra').groupby(pd.Grouper(freq ='M'))['Preço'].sum()
        receita_mensal = receita_mensal.reset_index()
        receita_mensal['Ano'] = receita_mensal['Data da Compra'].dt.year
        receita_mensal['Mês'] = receita_mensal['Data da Compra'].dt.month_name()

        # Receita por categoria de produto
        receita_categorias = dados.groupby('Categoria do Produto')[['Preço']].sum().sort_values('Preço', ascending=False)
        receita_categorias = receita_categorias.reset_index()

        # Quantidade de vendas por estado
        quantidade_estados = dados.groupby('Local da compra')[['Preço']].count()
        quantidade_estados = quantidade_estados.sort_values('Preço', ascending=False).reset_index()
        quantidade_estados = pd.merge(quantidade_estados, locais_unicos, on='Local da compra', how='left')

        # Tabela de vendedores
        vendedores = pd.DataFrame(dados.groupby('Vendedor')['Preço'].agg(['sum', 'count']))

        ## Construção dos gráficos
        # Gráficos da receita
        fig_mapa_receita = px.scatter_geo(receita_final,
                                        lat = 'lat',
                                        lon = 'lon',
                                        scope = 'south america',
                                        size = 'Preço',
                                        template = 'seaborn',
                                        hover_name = 'Local da compra',
                                        hover_data = {'lat':False, 'lon':False},
                                        title = 'Receita por Estado')       
            
        fig_receita_mensal = px.line(receita_mensal,
                                    x='Mês',
                                    y='Preço',
                                    markers=True,
                                    range_y=(0, receita_mensal.max()),
                                    color='Ano',
                                    line_dash='Ano',
                                    title='Receita Mensal')

        fig_receita_mensal.update_layout(yaxis_title='Receita')

        fig_receita_estados = px.bar(receita_final.head(),
                                     x = 'Local da compra',
                                     y = 'Preço',
                                     text_auto = True,
                                     title = 'Top Estados (receita)')
        
        fig_receita_estados.update_layout(yaxis_title='Receita')

        fig_receita_categorias = px.bar(receita_categorias,
                                        x = 'Categoria do Produto',
                                        y = 'Preço',
                                        text_auto=True,
                                        title='Receita por Categoria',)
        
        fig_receita_categorias.update_layout(yaxis_title='Receita')                                

        # Gráficos da quantidade de vendas
        fig_quantidade_vendas_estados = px.bar(quantidade_estados,
                                        x = 'Local da compra',
                                        y = 'Preço',
                                        text_auto=True,
                                        title='Quantidade de Vendas por Estado')

        ## Visualização no Streamlit
        # Adicionando métricas
        # Construindo abas
        aba1, aba2, aba3 = st.tabs(['Receita', 'Quantidade de vendas', 'Vendedores'])

        with aba1:
            # Adicionando métricas
            coluna1, coluna2 = st.columns(2)
            with coluna1:
                st.plotly_chart(fig_mapa_receita, use_container_width=True)
                st.plotly_chart(fig_receita_estados, use_container_width=True)
            with coluna2:
                st.plotly_chart(fig_receita_mensal, use_container_width=True)
                st.plotly_chart(fig_receita_categorias, use_container_width=True)

        # Aba com as métricas
        with aba2:
            coluna1, coluna2 = st.columns(2)
            with coluna1:
                st.metric('Receita', formata_numero(dados['Preço'].sum(), 'R$'), help='Total de receita gerada')
            with coluna2:
                st.metric('Quantidade de vendas', formata_numero(dados.shape[0]), help='Total de vendas realizadas')
            st.plotly_chart(fig_quantidade_vendas_estados)

        with aba3:
            qtd_vendedores = st.number_input('Quantidade de vendedores', min_value=1, max_value=100, value=10, step=1)
            coluna1, coluna2 = st.columns(2)
            with coluna1:
                st.metric('Receita', formata_numero(dados['Preço'].sum(), 'R$'), help='Total de receita gerada')
                fig_receita_vendedores = px.bar(vendedores[['sum']].sort_values('sum', ascending=False).head(qtd_vendedores),
                                                x = 'sum',
                                                y = vendedores[['sum']].sort_values('sum', ascending=False).head(qtd_vendedores).index,
                                                text_auto=True,
                                                title=f'Top {qtd_vendedores} vendedores (receita)')
                st.plotly_chart(fig_receita_vendedores, use_container_width=True)
            with coluna2:
                st.metric('Quantidade de vendas', formata_numero(dados.shape[0]), help='Total de vendas realizadas')
                fig_vendas_vendedores = px.bar(vendedores[['count']].sort_values('count', ascending=False).head(qtd_vendedores),
                                                x = 'count',
                                                y = vendedores[['count']].sort_values('count', ascending=False).head(qtd_vendedores).index,
                                                text_auto=True,
                                                title=f'Top {qtd_vendedores} vendedores (quantidade de vendas)')
                st.plotly_chart(fig_vendas_vendedores, use_container_width=True)
        # Exibir os dados em uma tabela
            # st.dataframe(receita_categorias)
        
    except requests.exceptions.JSONDecodeError:
        st.error("Erro: A resposta recebida não é um JSON válido.")
        st.text("Conteúdo da resposta:")
        st.text(response.text)
else:
    st.error(f"Erro ao fazer a requisição. Status code: {response.status_code}")
    st.text("Conteúdo da resposta:")
    st.text(response.text)

