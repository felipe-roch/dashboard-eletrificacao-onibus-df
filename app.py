"""
DASHBOARD STREAMLIT - ELETRIFICAÇÃO DA FROTA DE ÔNIBUS DO DF
============================================================

Estrutura Modular do Dashboard

Para facilitar a manutenção, este arquivo está organizado em seções.
Copie TODO este código para um arquivo chamado 'app.py'
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import json
from pathlib import Path

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Dashboard - Eletrificação Ônibus DF",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# FUNÇÕES DE CARREGAMENTO DE DADOS
# ============================================================================

@st.cache_data
def carregar_dados():
    """Carrega todos os dados necessários"""
    
    # Define diretório de dados
    # AJUSTE ESTE CAMINHO conforme necessário
    DATA_DIR = Path("dashboard_data")
    
    # Carrega arquivos JSON
    with open(DATA_DIR / 'dados_dashboard_master.json', 'r', encoding='utf-8') as f:
        dados_master = json.load(f)
    
    with open(DATA_DIR / 'dados_kpis.json', 'r', encoding='utf-8') as f:
        kpis = json.load(f)
    
    with open(DATA_DIR / 'config_dashboard.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Carrega paradas
    df_paradas = pd.read_parquet(DATA_DIR / 'dados_paradas.parquet')
    
    return dados_master, kpis, config, df_paradas

@st.cache_data
def calcular_kpis_filtrados(filtros, dados_master):
    """Recalcula KPIs baseado nos filtros aplicados"""
    # Esta função será expandida para filtrar dados
    # Por enquanto retorna os KPIs base
    pass

# ============================================================================
# FUNÇÕES DE VISUALIZAÇÃO
# ============================================================================

def criar_card_kpi(titulo, valor, unidade="", delta=None, delta_label=""):
    """Cria um card de KPI estilizado"""
    
    # Formata valor
    if isinstance(valor, (int, float)):
        if valor >= 1_000_000_000:
            valor_fmt = f"{valor/1_000_000_000:.2f}"
            unidade = "bilhões " + unidade
        elif valor >= 1_000_000:
            valor_fmt = f"{valor/1_000_000:.1f}"
            unidade = "milhões " + unidade
        elif valor >= 1_000:
            valor_fmt = f"{valor:,.0f}".replace(",", ".")
        else:
            valor_fmt = f"{valor:.1f}"
    else:
        valor_fmt = str(valor)
    
    # HTML do card
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
    ">
        <h4 style="margin: 0; font-size: 14px; opacity: 0.9;">{titulo}</h4>
        <h2 style="margin: 10px 0; font-size: 32px; font-weight: bold;">{valor_fmt}</h2>
        <p style="margin: 0; font-size: 12px; opacity: 0.8;">{unidade}</p>
    </div>
    """
    
    return card_html

def criar_mapa_rotas(df_paradas, garagens, terminais, config, mostrar_heatmap=False):
    """Cria mapa interativo com rotas, garagens, terminais e paradas"""
    
    # Centro do mapa
    centro = config['centro_mapa']
    
    # Cria mapa base
    m = folium.Map(
        location=[centro['lat'], centro['lon']],
        zoom_start=config['zoom_inicial'],
        tiles='OpenStreetMap'
    )
    
    # Adiciona garagens
    for garagem in garagens:
        folium.Marker(
            location=[garagem['lat'], garagem['lon']],
            popup=f"""
                <b>{garagem['garagem']}</b><br>
                Operadora: {garagem['operadora']}<br>
                Frota: {garagem['frota']} ônibus<br>
                Carregadores: {garagem['carregadores']}<br>
                Custo: R$ {garagem['custo_total']:,.0f}
            """,
            icon=folium.Icon(color='blue', icon='home', prefix='fa'),
            tooltip=garagem['garagem']
        ).add_to(m)
    
    # Adiciona terminais
    for terminal in terminais:
        folium.Marker(
            location=[terminal['lat'], terminal['lon']],
            popup=f"""
                <b>{terminal['terminal']}</b><br>
                Linhas: {terminal['linhas_termino']}<br>
                Carregadores: {terminal['carregadores']}<br>
                Potência: {terminal['potencia_mva']:.2f} MVA
            """,
            icon=folium.Icon(color='green', icon='bolt', prefix='fa'),
            tooltip=terminal['terminal']
        ).add_to(m)
    
    # Adiciona paradas (amostra se muitas)
    if len(df_paradas) > 500:
        df_paradas_plot = df_paradas.sample(500)
    else:
        df_paradas_plot = df_paradas
    
    for _, parada in df_paradas_plot.iterrows():
        folium.CircleMarker(
            location=[parada['lat'], parada['lon']],
            radius=3,
            popup=parada['stop_name'],
            color='red',
            fill=True,
            fillColor='red',
            fillOpacity=0.6
        ).add_to(m)
    
    # Heatmap (se solicitado)
    if mostrar_heatmap:
        from folium.plugins import HeatMap
        heat_data = [[row['lat'], row['lon']] for _, row in df_paradas.iterrows()]
        HeatMap(heat_data).add_to(m)
    
    return m

# ============================================================================
# SIDEBAR - FILTROS
# ============================================================================

def criar_sidebar(dados_master, config):
    """Cria sidebar com todos os filtros"""
    
    st.sidebar.title("🔧 Filtros")
    
    # Seção: Filtros Operacionais
    st.sidebar.markdown("### 🚌 Operacionais")
    
    # Operadora
    operadoras = list(config['cores_operadoras'].keys())
    operadoras_sel = st.sidebar.multiselect(
        "Operadora",
        options=operadoras,
        default=operadoras
    )
    
    # Modelo de ônibus
    modelo_onibus = st.sidebar.selectbox(
        "Modelo de Ônibus",
        options=["Ambos", "D9W", "D11B"]
    )
    
    # Tipo de linha
    tipo_linha = st.sidebar.multiselect(
        "Tipo de Linha",
        options=["Normal", "BRT", "Executivo"],
        default=["Normal", "BRT", "Executivo"]
    )
    
    # Período de análise
    periodo_anos = st.sidebar.slider(
        "Período de Análise (anos)",
        min_value=1,
        max_value=15,
        value=15,
        step=1
    )
    
    # Seção: Filtros Financeiros
    st.sidebar.markdown("### 💰 Financeiros")
    
    # Cenário tarifário
    aumento_tarifa = st.sidebar.slider(
        "Aumento Tarifário (%)",
        min_value=0,
        max_value=100,
        value=50,
        step=10
    )
    
    # Sensibilidade Energia
    tarifa_energia = st.sidebar.slider(
        "Tarifa Energia (R$/kWh)",
        min_value=0.50,
        max_value=1.50,
        value=0.829,
        step=0.05
    )
    
    # Sensibilidade Diesel
    preco_diesel = st.sidebar.slider(
        "Preço Diesel (R$/L)",
        min_value=4.0,
        max_value=10.0,
        value=5.96,
        step=0.10
    )
    
    # Retorna filtros
    return {
        'operadoras': operadoras_sel,
        'modelo_onibus': modelo_onibus,
        'tipo_linha': tipo_linha,
        'periodo_anos': periodo_anos,
        'aumento_tarifa': aumento_tarifa,
        'tarifa_energia': tarifa_energia,
        'preco_diesel': preco_diesel
    }

# ============================================================================
# PÁGINA: HOME (KPIs)
# ============================================================================

def pagina_home(kpis, filtros, dados_master):
    """Página principal com KPIs"""
    
    st.title("🏠 Dashboard - Eletrificação da Frota de Ônibus do DF")
    st.markdown("---")
    
    # KPIs em 3 linhas de 2 colunas
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(criar_card_kpi(
            "KM Percorridos/Ano",
            kpis['km_anual'],
            "km"
        ), unsafe_allow_html=True)
    
    with col2:
        st.markdown(criar_card_kpi(
            "Passageiros/Ano",
            kpis['passageiros_ano'],
            "passageiros"
        ), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown(criar_card_kpi(
            "Emissões Evitadas",
            kpis['emissoes_evitadas_ton'],
            "tCO₂"
        ), unsafe_allow_html=True)
    
    with col4:
        st.markdown(criar_card_kpi(
            "Economia OPEX",
            kpis['economia_opex_pct'],
            "%"
        ), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col5, col6 = st.columns(2)
    
    # Busca VPL e Payback do cenário selecionado
    cenario_sel = None
    for cenario in dados_master['cenarios_financeiros']:
        if cenario['aumento_pct'] == filtros['aumento_tarifa']:
            cenario_sel = cenario
            break
    
    if cenario_sel:
        with col5:
            st.markdown(criar_card_kpi(
                f"VPL (Aumento {filtros['aumento_tarifa']}%)",
                cenario_sel['vpl'],
                "R$"
            ), unsafe_allow_html=True)
        
        with col6:
            st.markdown(criar_card_kpi(
                "Payback Simples",
                cenario_sel['payback_simples'],
                "anos"
            ), unsafe_allow_html=True)

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal"""
    
    # Carrega dados
    try:
        dados_master, kpis, config, df_paradas = carregar_dados()
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.info("Execute o NB6_Preparacao_Dashboard.ipynb primeiro!")
        return
    
    # Cria sidebar com filtros
    filtros = criar_sidebar(dados_master, config)
    
    # Menu de navegação
    pagina = st.sidebar.radio(
        "📍 Navegação",
        options=["🏠 Home", "🗺️ Mapa & Rotas", "📊 Análise Operacional", 
                 "💰 Viabilidade Econômica", "🎮 Simulador"]
    )
    
    # Renderiza página selecionada
    if pagina == "🏠 Home":
        pagina_home(kpis, filtros, dados_master)
    
    elif pagina == "🗺️ Mapa & Rotas":
        st.title("🗺️ Mapa Interativo - Rotas, Garagens e Terminais")
        
        # Toggle heatmap
        mostrar_heatmap = st.checkbox("Mostrar Heatmap de Densidade", value=False)
        
        # Cria mapa
        mapa = criar_mapa_rotas(
            df_paradas,
            dados_master['garagens'],
            dados_master['terminais'],
            config,
            mostrar_heatmap
        )
        
        # Exibe mapa
        st_folium(mapa, width=1400, height=600)
    
    # TODO: Implementar outras páginas
    elif pagina == "📊 Análise Operacional":
        st.title("📊 Análise Operacional")
        st.info("Em desenvolvimento...")
    
    elif pagina == "💰 Viabilidade Econômica":
        st.title("💰 Análise de Viabilidade Econômica")
        st.info("Em desenvolvimento...")
    
    elif pagina == "🎮 Simulador":
        st.title("🎮 Simulador Interativo")
        st.info("Em desenvolvimento...")

# ============================================================================
# EXECUÇÃO
# ============================================================================

if __name__ == "__main__":
    main()
