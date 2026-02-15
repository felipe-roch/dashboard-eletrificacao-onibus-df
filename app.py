"""
DASHBOARD STREAMLIT - ELETRIFICAÇÃO DA FROTA DE ÔNIBUS DO DF
============================================================
Dashboard Interativo e Profissional
Versão 2.0 - Totalmente Dinâmico
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
from folium.plugins import HeatMap
import json
from pathlib import Path

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="Eletrificação Ônibus DF",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Customizado
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stMetric:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        transform: translateY(-2px);
        transition: all 0.3s ease;
    }
    h1 {
        color: #1f77b4;
        font-weight: 700;
    }
    .metric-row {
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# FUNÇÕES DE CARREGAMENTO DE DADOS
# ============================================================================

@st.cache_data
def carregar_dados():
    """Carrega todos os dados necessários"""
    DATA_DIR = Path("dashboard_data")
    
    try:
        with open(DATA_DIR / 'dados_dashboard_master.json', 'r', encoding='utf-8') as f:
            dados_master = json.load(f)
        
        with open(DATA_DIR / 'dados_kpis.json', 'r', encoding='utf-8') as f:
            kpis = json.load(f)
        
        with open(DATA_DIR / 'config_dashboard.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        df_paradas = pd.read_parquet(DATA_DIR / 'dados_paradas.parquet')
        
        return dados_master, kpis, config, df_paradas
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.info("Execute o NB6_Preparacao_Dashboard.ipynb primeiro!")
        st.stop()

def calcular_kpis_dinamicos(filtros, kpis_base, dados_master):
    """Recalcula KPIs baseado nos filtros (DINÂMICO!)"""
    
    # Fator de ajuste baseado nas operadoras selecionadas
    total_operadoras = 6  # Total de operadoras
    operadoras_sel = len(filtros['operadoras'])
    fator_operadora = operadoras_sel / total_operadoras if operadoras_sel > 0 else 1.0
    
    # Fator de ajuste baseado no modelo de ônibus
    if filtros['modelo_onibus'] == "D9W":
        fator_modelo = kpis_base['frota_d9w'] / kpis_base['frota_total']
    elif filtros['modelo_onibus'] == "D11B":
        fator_modelo = kpis_base['frota_d11b'] / kpis_base['frota_total']
    else:
        fator_modelo = 1.0
    
    # Fator de ajuste baseado no período
    fator_periodo = filtros['periodo_anos'] / 15.0
    
    # Fator combinado
    fator_total = fator_operadora * fator_modelo
    
    # KPIs ajustados
    kpis_dinamicos = {
        'km_anual': kpis_base['km_anual'] * fator_total,
        'passageiros_ano': kpis_base['passageiros_ano'] * fator_total,
        'emissoes_evitadas_ton': kpis_base['emissoes_evitadas_ton'] * fator_total,
        'capex_total': kpis_base['capex_total'] * fator_total,
        'opex_diesel_anual': kpis_base['opex_diesel_anual'] * fator_total,
        'opex_eletrico_anual': kpis_base['opex_eletrico_anual'] * fator_total,
        'economia_opex_anual': kpis_base['economia_opex_anual'] * fator_total,
        'economia_opex_pct': kpis_base['economia_opex_pct'],
        'frota_total': int(kpis_base['frota_total'] * fator_total),
    }
    
    # Busca VPL e Payback do cenário selecionado
    aumento = filtros['aumento_tarifa']
    cenario_sel = next((c for c in dados_master['cenarios_financeiros'] 
                       if c['aumento_pct'] == aumento), None)
    
    if cenario_sel:
        kpis_dinamicos['vpl'] = cenario_sel['vpl'] * fator_total
        kpis_dinamicos['payback'] = cenario_sel['payback_simples']
        kpis_dinamicos['tir'] = cenario_sel.get('tir', 0)
    else:
        kpis_dinamicos['vpl'] = 0
        kpis_dinamicos['payback'] = 999
        kpis_dinamicos['tir'] = 0
    
    return kpis_dinamicos

# ============================================================================
# FUNÇÕES DE VISUALIZAÇÃO - MAPA
# ============================================================================

def criar_mapa_completo(df_paradas, garagens, terminais, config, filtros, mostrar_heatmap=False):
    """Cria mapa ESPETACULAR com tudo interativo"""
    
    centro = config['centro_mapa']
    
    # Mapa base com tile bonito
    m = folium.Map(
        location=[centro['lat'], centro['lon']],
        zoom_start=config['zoom_inicial'],
        tiles='CartoDB positron',
        prefer_canvas=True
    )
    
    # Filtra garagens por operadora selecionada
    cores_op = config['cores_operadoras']
    
    for garagem in garagens:
        if garagem['operadora'] in filtros['operadoras']:
            cor = cores_op.get(garagem['operadora'], 'gray')
            
            folium.Marker(
                location=[garagem['lat'], garagem['lon']],
                popup=folium.Popup(f"""
                    <div style='font-family: Arial; width: 200px;'>
                        <h4 style='margin: 0; color: #1f77b4;'>{garagem['garagem']}</h4>
                        <hr style='margin: 5px 0;'>
                        <b>Operadora:</b> {garagem['operadora']}<br>
                        <b>Frota:</b> {garagem['frota']} ônibus<br>
                        <b>Carregadores:</b> {garagem['carregadores']}<br>
                        <b>Potência:</b> {garagem['potencia_mva']:.2f} MVA<br>
                        <b>Custo:</b> R$ {garagem['custo_total']/1e6:.2f}M
                    </div>
                """, max_width=250),
                icon=folium.Icon(color='blue', icon='home', prefix='fa'),
                tooltip=f"🏠 {garagem['garagem']}"
            ).add_to(m)
    
    # Terminais
    for terminal in terminais:
        folium.Marker(
            location=[terminal['lat'], terminal['lon']],
            popup=folium.Popup(f"""
                <div style='font-family: Arial; width: 200px;'>
                    <h4 style='margin: 0; color: #2ca02c;'>{terminal['terminal']}</h4>
                    <hr style='margin: 5px 0;'>
                    <b>Linhas:</b> {terminal['linhas_termino']}<br>
                    <b>Carregadores:</b> {terminal['carregadores']}<br>
                    <b>Potência:</b> {terminal['potencia_mva']:.2f} MVA
                </div>
            """, max_width=250),
            icon=folium.Icon(color='green', icon='bolt', prefix='fa'),
            tooltip=f"⚡ {terminal['terminal']}"
        ).add_to(m)
    
    # Paradas (amostra inteligente)
    if mostrar_heatmap:
        heat_data = [[row['lat'], row['lon']] for _, row in df_paradas.iterrows()]
        HeatMap(heat_data, radius=15, blur=20, max_zoom=13).add_to(m)
    else:
        # Amostra de paradas
        if len(df_paradas) > 300:
            df_paradas_plot = df_paradas.sample(300, random_state=42)
        else:
            df_paradas_plot = df_paradas
        
        for _, parada in df_paradas_plot.iterrows():
            folium.CircleMarker(
                location=[parada['lat'], parada['lon']],
                radius=3,
                popup=parada['stop_name'],
                color='#ff7f0e',
                fill=True,
                fillColor='#ff7f0e',
                fillOpacity=0.6,
                weight=1
            ).add_to(m)
    
    # Adiciona controle de camadas
    folium.LayerControl().add_to(m)
    
    return m

# ============================================================================
# SIDEBAR - FILTROS
# ============================================================================

def criar_sidebar(dados_master, config):
    """Cria sidebar com filtros"""
    
    st.sidebar.image("https://via.placeholder.com/300x80/1f77b4/ffffff?text=Eletrificação+DF", 
                     use_container_width=True)
    
    st.sidebar.markdown("## 🔧 Filtros")
    st.sidebar.markdown("---")
    
    # Operacionais
    st.sidebar.markdown("### 🚌 Operacionais")
    
    operadoras = list(config['cores_operadoras'].keys())
    operadoras_sel = st.sidebar.multiselect(
        "Operadoras",
        options=operadoras,
        default=operadoras,
        help="Selecione as operadoras para análise"
    )
    
    modelo_onibus = st.sidebar.selectbox(
        "Modelo de Ônibus",
        options=["Ambos", "D9W", "D11B"],
        help="D9W: 9m | D11B: 11m"
    )
    
    periodo_anos = st.sidebar.slider(
        "Período de Análise",
        min_value=1,
        max_value=15,
        value=15,
        step=1,
        help="Anos para análise financeira"
    )
    
    st.sidebar.markdown("---")
    
    # Financeiros
    st.sidebar.markdown("### 💰 Cenários Financeiros")
    
    aumento_tarifa = st.sidebar.slider(
        "Aumento Tarifário (%)",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
        help="Percentual de aumento sobre tarifa atual"
    )
    
    tarifa_energia = st.sidebar.slider(
        "Tarifa Energia (R$/kWh)",
        min_value=0.50,
        max_value=1.50,
        value=0.829,
        step=0.05,
        format="R$ %.3f"
    )
    
    preco_diesel = st.sidebar.slider(
        "Preço Diesel (R$/L)",
        min_value=4.0,
        max_value=10.0,
        value=5.96,
        step=0.10,
        format="R$ %.2f"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Dica:** Ajuste os filtros para ver os indicadores mudarem em tempo real!")
    
    return {
        'operadoras': operadoras_sel,
        'modelo_onibus': modelo_onibus,
        'periodo_anos': periodo_anos,
        'aumento_tarifa': aumento_tarifa,
        'tarifa_energia': tarifa_energia,
        'preco_diesel': preco_diesel
    }

# ============================================================================
# PÁGINA: HOME
# ============================================================================

def pagina_home(kpis, filtros, dados_master):
    """Página HOME com KPIs dinâmicos e compactos"""
    
    st.title("🚌 Eletrificação da Frota de Ônibus do DF")
    st.markdown("Dashboard Interativo de Análise de Viabilidade")
    st.markdown("---")
    
    # KPIs PRINCIPAIS (4 colunas)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📏 KM Percorridos/Ano",
            value=f"{kpis['km_anual']/1e6:.1f}M",
            delta=f"{(len(filtros['operadoras'])/6)*100:.0f}% da frota",
            help="Quilometragem anual da frota selecionada"
        )
    
    with col2:
        st.metric(
            label="👥 Passageiros/Ano",
            value=f"{kpis['passageiros_ano']/1e6:.1f}M",
            delta=f"+{kpis['passageiros_ano']/1e3:.0f}k/dia",
            help="Passageiros transportados anualmente"
        )
    
    with col3:
        st.metric(
            label="🌱 Emissões Evitadas",
            value=f"{kpis['emissoes_evitadas_ton']/1000:.1f}k ton",
            delta="CO₂/ano",
            help="Emissões de CO₂ evitadas vs diesel"
        )
    
    with col4:
        st.metric(
            label="💰 Economia OPEX",
            value=f"{kpis['economia_opex_pct']:.1f}%",
            delta=f"R$ {kpis['economia_opex_anual']/1e6:.1f}M/ano",
            help="Economia operacional vs diesel"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # KPIs FINANCEIROS (3 colunas)
    col5, col6, col7 = st.columns(3)
    
    with col5:
        vpl_bi = kpis['vpl'] / 1e9
        delta_vpl = "✅ Viável" if vpl_bi > 0 else "⚠️ Inviável"
        st.metric(
            label=f"📊 VPL (Aumento {filtros['aumento_tarifa']}%)",
            value=f"R$ {vpl_bi:.2f}bi",
            delta=delta_vpl,
            delta_color="normal" if vpl_bi > 0 else "inverse",
            help="Valor Presente Líquido (TMA 8% a.a., 15 anos)"
        )
    
    with col6:
        pb_ok = kpis['payback'] <= 15
        delta_pb = "✅ OK" if pb_ok else "⚠️ Longo"
        st.metric(
            label="⏱️ Payback Simples",
            value=f"{kpis['payback']:.1f} anos",
            delta=delta_pb,
            delta_color="normal" if pb_ok else "inverse",
            help="Tempo para retorno do investimento"
        )
    
    with col7:
        tir_val = kpis.get('tir', 0)
        if tir_val and tir_val > 0:
            tir_ok = tir_val > 8.0
            delta_tir = "✅ > TMA" if tir_ok else "⚠️ < TMA"
            st.metric(
                label="📈 TIR",
                value=f"{tir_val:.1f}%",
                delta=delta_tir,
                delta_color="normal" if tir_ok else "inverse",
                help="Taxa Interna de Retorno (TMA: 8%)"
            )
        else:
            st.metric(
                label="📈 TIR",
                value="N/A",
                help="Taxa Interna de Retorno não calculada"
            )
    
    st.markdown("---")
    
    # Alerta baseado na viabilidade
    if vpl_bi > 0 and pb_ok:
        st.success(f"✅ **Projeto VIÁVEL** no cenário selecionado (Aumento {filtros['aumento_tarifa']}%)")
    elif vpl_bi > 0:
        st.warning(f"⚠️ **Projeto MARGINALMENTE viável** - Payback longo ({kpis['payback']:.1f} anos)")
    else:
        st.error(f"❌ **Projeto NÃO VIÁVEL** no cenário selecionado - Considere aumentar o percentual tarifário")

# ============================================================================
# PÁGINA: MAPA
# ============================================================================

def pagina_mapa(df_paradas, dados_master, config, filtros):
    """Página do MAPA - Protagonista do Dashboard"""
    
    st.title("🗺️ Mapa Interativo - Infraestrutura de Recarga")
    
    # Controles do mapa
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown("### Explore garagens, terminais e paradas no mapa abaixo")
    
    with col2:
        mostrar_heatmap = st.checkbox("🔥 Heatmap", value=False, 
                                      help="Mostra densidade de paradas")
    
    with col3:
        st.metric("📍 Paradas", len(df_paradas), help="Total de paradas no sistema")
    
    st.markdown("---")
    
    # Mapa
    mapa = criar_mapa_completo(
        df_paradas,
        dados_master['garagens'],
        dados_master['terminais'],
        config,
        filtros,
        mostrar_heatmap
    )
    
    st_folium(mapa, width=1400, height=700, returned_objects=[])
    
    # Legenda
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("🏠 **Garagens** - Recarga noturna")
    with col2:
        st.markdown("⚡ **Terminais** - Recarga diurna")
    with col3:
        st.markdown("🚏 **Paradas** - Pontos de ônibus")

# ============================================================================
# PÁGINA: VIABILIDADE ECONÔMICA
# ============================================================================

def pagina_viabilidade(dados_master, filtros):
    """Página de Viabilidade Econômica"""
    
    st.title("💰 Análise de Viabilidade Econômica")
    st.markdown("---")
    
    df_cenarios = pd.DataFrame(dados_master['cenarios_financeiros'])
    
    # GRÁFICO 1: VPL por Cenário
    st.markdown("### 📊 Valor Presente Líquido (VPL) por Cenário")
    
    fig_vpl = go.Figure()
    
    cores = ['#d32f2f' if v < 0 else '#388e3c' for v in df_cenarios['vpl']]
    
    fig_vpl.add_trace(go.Bar(
        x=df_cenarios['aumento_pct'],
        y=df_cenarios['vpl'] / 1e9,
        marker_color=cores,
        text=[f"R$ {v/1e9:.2f}bi" for v in df_cenarios['vpl']],
        textposition='outside',
        hovertemplate='<b>Aumento: %{x}%</b><br>VPL: R$ %{y:.2f}bi<extra></extra>'
    ))
    
    fig_vpl.add_hline(y=0, line_dash="dash", line_color="black", 
                      annotation_text="Break-even")
    
    # Destaca cenário selecionado
    idx_sel = df_cenarios[df_cenarios['aumento_pct'] == filtros['aumento_tarifa']].index
    if len(idx_sel) > 0:
        fig_vpl.add_vline(x=filtros['aumento_tarifa'], line_dash="dot", 
                         line_color="blue", annotation_text="Cenário Atual")
    
    fig_vpl.update_layout(
        xaxis_title="Aumento Tarifário (%)",
        yaxis_title="VPL (R$ bilhões)",
        height=400,
        showlegend=False,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_vpl, use_container_width=True)
    
    # GRÁFICO 2 e 3: Payback e TIR
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ⏱️ Payback por Cenário")
        
        fig_pb = go.Figure()
        
        df_pb = df_cenarios[df_cenarios['payback_simples'] < 30]
        
        fig_pb.add_trace(go.Scatter(
            x=df_pb['aumento_pct'],
            y=df_pb['payback_simples'],
            mode='lines+markers',
            name='Simples',
            line=dict(color='#1f77b4', width=3)
        ))
        
        fig_pb.add_hline(y=15, line_dash="dash", line_color="red",
                        annotation_text="Vida útil (15a)")
        
        fig_pb.update_layout(
            xaxis_title="Aumento (%)",
            yaxis_title="Payback (anos)",
            height=350,
            showlegend=True
        )
        
        st.plotly_chart(fig_pb, use_container_width=True)
    
    with col2:
        st.markdown("### 📈 TIR por Cenário")
        
        df_tir = df_cenarios[df_cenarios['tir'].notna()].copy()
        
        if len(df_tir) > 0:
            fig_tir = go.Figure()
            
            fig_tir.add_trace(go.Scatter(
                x=df_tir['aumento_pct'],
                y=df_tir['tir'],
                mode='lines+markers',
                name='TIR',
                line=dict(color='#2ca02c', width=3),
                fill='tozeroy',
                fillcolor='rgba(44, 160, 44, 0.2)'
            ))
            
            fig_tir.add_hline(y=8, line_dash="dash", line_color="orange",
                            annotation_text="TMA (8%)")
            
            fig_tir.update_layout(
                xaxis_title="Aumento (%)",
                yaxis_title="TIR (%)",
                height=350
            )
            
            st.plotly_chart(fig_tir, use_container_width=True)
        else:
            st.info("TIR não calculada para os cenários")

# ============================================================================
# PÁGINA: SIMULADOR
# ============================================================================

def pagina_simulador(dados_master, kpis_base):
    """Simulador Interativo"""
    
    st.title("🎮 Simulador de Viabilidade")
    st.markdown("Ajuste os parâmetros e veja os resultados em tempo real!")
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 🎛️ Parâmetros")
        
        sim_tarifa = st.slider("Aumento Tarifário (%)", 0, 100, 50, 5)
        sim_diesel = st.slider("Preço Diesel (R$/L)", 4.0, 10.0, 5.96, 0.1)
        sim_energia = st.slider("Tarifa Energia (R$/kWh)", 0.5, 1.5, 0.829, 0.05)
        sim_credito = st.slider("Crédito Carbono (US$/ton)", 0, 150, 86, 5)
    
    with col2:
        st.markdown("### 📊 Resultados Instantâneos")
        
        # Cálculo simplificado (baseado em fórmulas aproximadas)
        # CAPEX fixo
        capex = kpis_base['capex_total']
        
        # OPEX ajustado
        km_ano = kpis_base['km_anual']
        consumo_diesel_lkm = 0.35
        consumo_elet_kwh = 1.6
        
        opex_diesel = km_ano * consumo_diesel_lkm * sim_diesel + km_ano * 0.80
        opex_elet = km_ano * consumo_elet_kwh * sim_energia + km_ano * 0.30
        economia_opex = opex_diesel - opex_elet
        
        # Receita créditos
        receita_cred = kpis_base['emissoes_evitadas_ton'] * sim_credito * 5.40
        
        # Receita tarifa
        receita_base = kpis_base['passageiros_ano'] * 4.39
        receita_tarifa = receita_base * (sim_tarifa / 100)
        
        # Benefício total
        beneficio = economia_opex + receita_cred + receita_tarifa
        
        # Payback
        if beneficio > 0:
            payback_sim = capex / beneficio
        else:
            payback_sim = 999
        
        # VPL aproximado
        tma = 0.08
        vpl_sim = sum([beneficio / ((1 + tma) ** ano) for ano in range(1, 16)]) - capex
        
        # Mostra resultados
        st.metric("💰 VPL Estimado", f"R$ {vpl_sim/1e9:.2f}bi",
                 "✅ Viável" if vpl_sim > 0 else "❌ Inviável")
        
        st.metric("⏱️ Payback", f"{payback_sim:.1f} anos",
                 "✅ OK" if payback_sim <= 15 else "⚠️ Longo")
        
        st.metric("📈 Benefício Anual", f"R$ {beneficio/1e9:.2f}bi")
        
        # Gráfico de composição
        st.markdown("---")
        st.markdown("#### Composição dos Benefícios")
        
        fig_comp = go.Figure(data=[go.Pie(
            labels=['Economia OPEX', 'Créditos Carbono', 'Receita Tarifa'],
            values=[economia_opex, receita_cred, receita_tarifa],
            hole=.3
        )])
        
        fig_comp.update_layout(height=300, showlegend=True)
        st.plotly_chart(fig_comp, use_container_width=True)

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal"""
    
    # Carrega dados
    dados_master, kpis_base, config, df_paradas = carregar_dados()
    
    # Cria sidebar com filtros
    filtros = criar_sidebar(dados_master, config)
    
    # Recalcula KPIs com filtros
    kpis = calcular_kpis_dinamicos(filtros, kpis_base, dados_master)
    
    # Menu de navegação
    st.sidebar.markdown("---")
    pagina = st.sidebar.radio(
        "📍 Navegação",
        options=["🏠 Home", "🗺️ Mapa Interativo", "💰 Viabilidade Econômica", "🎮 Simulador"],
        label_visibility="collapsed"
    )
    
    # Renderiza página selecionada
    if pagina == "🏠 Home":
        pagina_home(kpis, filtros, dados_master)
    
    elif pagina == "🗺️ Mapa Interativo":
        pagina_mapa(df_paradas, dados_master, config, filtros)
    
    elif pagina == "💰 Viabilidade Econômica":
        pagina_viabilidade(dados_master, filtros)
    
    elif pagina == "🎮 Simulador":
        pagina_simulador(dados_master, kpis_base)

if __name__ == "__main__":
    main()
