"""
DASHBOARD PROFISSIONAL - ELETRIFICAÇÃO FROTA ÔNIBUS DF
=======================================================
Versão Final Corrigida - Com Análise Tarifária Funcionando
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
# CONFIG
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
    .main {padding-top: 0.5rem;}
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem;
        border-radius: 10px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stMetric label, .stMetric [data-testid="stMetricValue"], 
    .stMetric [data-testid="stMetricDelta"] {
        color: white !important;
    }
    h1 {color: #1f77b4; font-weight: 700;}
    .alerta-ocupacao {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-weight: bold;
    }
    .alerta-ok {background: #d4edda; color: #155724;}
    .alerta-aviso {background: #fff3cd; color: #856404;}
    .alerta-perigo {background: #f8d7da; color: #721c24;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CARREGAMENTO
# ============================================================================

@st.cache_data
def carregar_dados():
    """Carrega dados REAIS processados"""
    DATA_DIR = Path("dashboard_data")
    
    try:
        with open(DATA_DIR / 'dashboard_data_REAL.json', 'r', encoding='utf-8') as f:
            dados = json.load(f)
        
        with open(DATA_DIR / 'kpis_base.json', 'r', encoding='utf-8') as f:
            kpis = json.load(f)
        
        with open(DATA_DIR / 'config_dashboard.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        df_paradas = pd.read_parquet(DATA_DIR / 'dados_paradas.parquet')
        
        return dados, kpis, config, df_paradas
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {e}")
        st.info("Execute o NB6_REAL_COMPLETO_CORRIGIDO.ipynb primeiro!")
        st.stop()

# ============================================================================
# CÁLCULOS
# ============================================================================

def calcular_metricas_filtradas(filtros, kpis_base, dados):
    """Recalcula métricas com filtros"""
    
    total_ops = len(dados['operadoras'])
    ops_sel = len(filtros['operadoras'])
    
    fator = ops_sel / total_ops if ops_sel > 0 else 1.0
    
    metricas = {
        'frota': int(kpis_base['total_onibus'] * fator),
        'linhas': int(kpis_base['total_linhas'] * fator),
        'paradas': int(kpis_base['total_paradas'] * fator),
        'km_anual': kpis_base['km_anual'] * fator,
        'passageiros_ano': kpis_base['passageiros_ano'] * fator,
        'co2': kpis_base['emissoes_evitadas_ton'] * fator,
        'taxa_ocupacao': kpis_base['taxa_ocupacao_atual'],
        'capacidade_ano': kpis_base['capacidade_total_ano'] * fator,
    }
    
    # Projeção de demanda
    novos_usuarios = filtros.get('novos_usuarios', 0)
    passes_dia = novos_usuarios * 3
    novos_passes_ano = passes_dia * 365
    
    metricas['passageiros_projetados'] = metricas['passageiros_ano'] + novos_passes_ano
    metricas['taxa_projetada'] = (metricas['passageiros_projetados'] / metricas['capacidade_ano']) * 100
    
    # Cenário financeiro
    if 'aumento_tarifa' in filtros and len(dados.get('cenarios_financeiros', [])) > 0:
        cenario = next((c for c in dados['cenarios_financeiros'] 
                       if c['aumento_pct'] == filtros['aumento_tarifa']), None)
        if cenario:
            metricas['vpl'] = cenario['vpl'] * fator
            metricas['payback'] = cenario['payback_simples']
            metricas['tir'] = cenario.get('tir', 0)
        else:
            metricas['vpl'] = 0
            metricas['payback'] = 999
            metricas['tir'] = 0
    else:
        metricas['vpl'] = 0
        metricas['payback'] = 999
        metricas['tir'] = 0
    
    return metricas

# ============================================================================
# MAPA
# ============================================================================

def criar_mapa_profissional(df_paradas, garagens, terminais, config, filtros, heatmap=False):
    """Mapa com rotas, garagens, terminais e paradas"""
    
    centro = config['centro_mapa']
    
    m = folium.Map(
        location=[centro['lat'], centro['lon']],
        zoom_start=config['zoom_inicial'],
        tiles='CartoDB positron',
        prefer_canvas=True
    )
    
    # Garagens
    for g in garagens:
        folium.Marker(
            [g['lat'], g['lon']],
            popup=f"<b>🏠 {g['garagem']}</b><br>{g.get('operadora', 'N/A')}<br>Frota: {g.get('frota', 0)}",
            icon=folium.Icon(color='blue', icon='home', prefix='fa'),
            tooltip=g['garagem']
        ).add_to(m)
    
    # Terminais
    for t in terminais:
        folium.Marker(
            [t['lat'], t['lon']],
            popup=f"<b>⚡ {t['terminal']}</b><br>Carregadores: {t.get('carregadores', 0)}",
            icon=folium.Icon(color='green', icon='bolt', prefix='fa'),
            tooltip=t['terminal']
        ).add_to(m)
    
    # Paradas ou Heatmap
    if heatmap:
        heat_data = [[r['lat'], r['lon']] for _, r in df_paradas.iterrows()]
        HeatMap(heat_data, radius=15, blur=20).add_to(m)
    else:
        amostra = df_paradas.sample(min(400, len(df_paradas)), random_state=42)
        for _, p in amostra.iterrows():
            folium.CircleMarker(
                [p['lat'], p['lon']],
                radius=2,
                popup=p['stop_name'],
                color='#ff7f0e',
                fill=True,
                fillOpacity=0.6,
                weight=1
            ).add_to(m)
    
    folium.LayerControl().add_to(m)
    
    return m

# ============================================================================
# SIDEBAR
# ============================================================================

def criar_sidebar(dados):
    """Sidebar com filtros"""
    
    st.sidebar.markdown("## 🔧 Filtros")
    
    # Operadoras (TODAS as 16!)
    todas_ops = dados['operadoras']
    ops_sel = st.sidebar.multiselect(
        "Operadoras",
        todas_ops,
        todas_ops,
        help=f"{len(todas_ops)} operadoras disponíveis"
    )
    
    st.sidebar.markdown("---")
    
    # Projeção de demanda
    st.sidebar.markdown("### 📈 Projeção de Demanda")
    
    novos_usuarios = st.sidebar.slider(
        "+Novos Usuários (mil)",
        0, 200, 100, 10,
        help="Absorção do transporte pirata"
    ) * 1000
    
    st.sidebar.markdown("---")
    
    # Cenário financeiro
    st.sidebar.markdown("### 💰 Cenário Tarifário")
    
    aumento_tarifa = st.sidebar.slider(
        "Aumento (%)",
        10, 100, 50, 10
    )
    
    return {
        'operadoras': ops_sel,
        'novos_usuarios': novos_usuarios,
        'aumento_tarifa': aumento_tarifa
    }

# ============================================================================
# HOME
# ============================================================================

def pagina_home(metricas, filtros, dados, df_paradas, config, kpis_base):
    """Home com KPIs + Análise Tarifária + Ocupação + Mapa"""
    
    st.title("🚌 Eletrificação da Frota de Ônibus do DF")
    st.markdown("Dashboard com Análise de Demanda e Viabilidade Econômica")
    
    # ========================================================================
    # KPIs PRINCIPAIS
    # ========================================================================
    
    c1, c2, c3, c4, c5 = st.columns(5)
    
    c1.metric("🚌 Frota", f"{metricas['frota']:,}", help="Total de ônibus")
    c2.metric("📍 Linhas", f"{metricas['linhas']:,}", help="Linhas ativas")
    c3.metric("🚏 Paradas", f"{metricas['paradas']:,}", help="Pontos de ônibus")
    c4.metric("🌱 CO₂", f"{metricas['co2']/1000:.0f}k ton", help="Emissões evitadas/ano")
    c5.metric("📏 KM", f"{metricas['km_anual']/1e6:.0f}M/ano", help="Quilometragem anual")
    
    st.markdown("---")
    
    # ========================================================================
    # ANÁLISE TARIFÁRIA
    # ========================================================================
    
    st.markdown("### 💵 Impacto Tarifário no Projeto")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Tarifa base (usa dados reais do kpis_base)
    TARIFA_ATUAL = kpis_base.get('tarifa_media_atual', 4.39)
    aumento_pct = filtros['aumento_tarifa']
    tarifa_nova = TARIFA_ATUAL * (1 + aumento_pct/100)
    
    with col1:
        st.metric(
            "Tarifa Atual",
            f"R$ {TARIFA_ATUAL:.2f}",
            help="Média ponderada real (dados API)"
        )
    
    with col2:
        st.metric(
            "Tarifa Premium",
            f"R$ {tarifa_nova:.2f}",
            f"+{aumento_pct}%",
            delta_color="normal",
            help="Tarifa necessária para viabilidade"
        )
    
    with col3:
        receita_base = metricas['passageiros_ano'] * TARIFA_ATUAL
        receita_nova = metricas['passageiros_ano'] * tarifa_nova
        receita_adicional = receita_nova - receita_base
        
        st.metric(
            "Receita Adicional",
            f"R$ {receita_adicional/1e9:.2f}bi/ano",
            help="Incremento de receita com tarifa premium"
        )
    
    with col4:
        if metricas['vpl'] > 0:
            st.metric("Status", "✅ VIÁVEL", f"VPL R$ {metricas['vpl']/1e9:.2f}bi")
        else:
            st.metric("Status", "❌ INVIÁVEL", f"VPL R$ {metricas['vpl']/1e9:.2f}bi")
    
    # Gráfico de composição da receita
    st.markdown("#### 📊 Composição da Receita (Cenário Selecionado)")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        labels = ['Receita Base (Atual)', 'Receita Adicional (Premium)']
        values = [receita_base, receita_adicional]
        colors = ['#1f77b4', '#2ca02c']
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=.4,
            marker_colors=colors,
            textinfo='label+percent',
            textposition='auto',
        )])
        
        fig.update_layout(
            title=f"Receita Total: R$ {receita_nova/1e9:.2f} bilhões/ano",
            height=300,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**💡 Análise:**")
        
        media_nacional = 4.76
        
        if tarifa_nova < media_nacional:
            st.success(
                f"✅ Tarifa premium (R$ {tarifa_nova:.2f}) ainda está "
                f"**abaixo** da média nacional (R$ {media_nacional:.2f})"
            )
        elif tarifa_nova < media_nacional * 1.15:
            st.warning(
                f"⚠️ Tarifa premium (R$ {tarifa_nova:.2f}) está "
                f"**próxima** da média nacional (R$ {media_nacional:.2f})"
            )
        else:
            st.error(
                f"🚨 Tarifa premium (R$ {tarifa_nova:.2f}) está "
                f"**acima** da média nacional (R$ {media_nacional:.2f})"
            )
        
        aumento_mensal = (tarifa_nova - TARIFA_ATUAL) * 40
        st.info(
            f"📌 **Impacto:** Passageiro que usa 40 passes/mês "
            f"pagará **R$ {aumento_mensal:.2f}** a mais"
        )
    
    st.markdown("---")
    
    # ========================================================================
    # ANÁLISE DE OCUPAÇÃO
    # ========================================================================
    
    st.markdown("### 📊 Análise de Taxa de Ocupação")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['Atual'],
            y=[metricas['taxa_ocupacao']],
            name='Atual',
            marker_color='#1f77b4',
            text=f"{metricas['taxa_ocupacao']:.1f}%",
            textposition='outside'
        ))
        
        cor_proj = '#d32f2f' if metricas['taxa_projetada'] > 78 else '#2ca02c'
        fig.add_trace(go.Bar(
            x=['Projetada'],
            y=[metricas['taxa_projetada']],
            name=f"+{filtros['novos_usuarios']/1000:.0f}k usuários",
            marker_color=cor_proj,
            text=f"{metricas['taxa_projetada']:.1f}%",
            textposition='outside'
        ))
        
        fig.add_hline(
            y=78,
            line_dash="dash",
            line_color="red",
            annotation_text="Limite Seguro (78%)",
            annotation_position="right"
        )
        
        fig.update_layout(
            title="Taxa de Ocupação: Atual vs Projetada",
            yaxis_title="Taxa de Ocupação (%)",
            height=350,
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        taxa_proj = metricas['taxa_projetada']
        
        if taxa_proj < 70:
            classe = "alerta-ok"
            icone = "✅"
            titulo = "Sistema Confortável"
            msg = f"Taxa de {taxa_proj:.1f}% permite crescimento."
        elif taxa_proj < 78:
            classe = "alerta-aviso"
            icone = "⚠️"
            titulo = "Sistema Sob Pressão"
            msg = f"Taxa de {taxa_proj:.1f}% próxima do limite."
        else:
            classe = "alerta-perigo"
            icone = "🚨"
            titulo = "Sistema Saturado!"
            msg = f"Taxa de {taxa_proj:.1f}% ACIMA do limite seguro!"
        
        st.markdown(f"""
        <div class="alerta-ocupacao {classe}">
            <h3>{icone} {titulo}</h3>
            <p>{msg}</p>
            <hr>
            <small>
            • Passageiros atuais: {metricas['passageiros_ano']/1e6:.1f}M/ano<br>
            • Projetados: {metricas['passageiros_projetados']/1e6:.1f}M/ano<br>
            • Capacidade: {metricas['capacidade_ano']/1e6:.1f}M/ano
            </small>
        </div>
        """, unsafe_allow_html=True)
        
        taxa_atual = metricas['taxa_ocupacao']
        capacidade_restante = 78 - taxa_atual
        
        if capacidade_restante > 0:
            usuarios_limite = (capacidade_restante / 100) * kpis_base['capacidade_total_ano'] / (3 * 365)
            st.info(f"💡 Sistema aguenta mais **{usuarios_limite/1000:.0f}mil usuários** até 78%")
    
    st.markdown("---")
    
    # ========================================================================
    # MAPA
    # ========================================================================
    
    st.markdown("### 🗺️ Infraestrutura de Recarga")
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        st.info(f"📍 {len(filtros['operadoras'])} operadoras | {len(df_paradas):,} paradas")
    
    with col2:
        heatmap = st.checkbox("🔥 Heatmap")
    
    mapa = criar_mapa_profissional(
        df_paradas, dados['garagens'], dados['terminais'], 
        config, filtros, heatmap
    )
    
    st_folium(mapa, width=1400, height=500, returned_objects=[])

# ============================================================================
# VIABILIDADE
# ============================================================================

def pagina_viabilidade(dados, metricas, filtros):
    """Análise financeira"""
    
    st.title("💰 Viabilidade Econômica")
    
    if len(dados.get('cenarios_financeiros', [])) == 0:
        st.warning("Dados financeiros não disponíveis. Execute o NB5 primeiro.")
        return
    
    df_cen = pd.DataFrame(dados['cenarios_financeiros'])
    
    # Card do cenário selecionado
    st.info(
        f"📌 **Cenário Selecionado:** Aumento de {filtros['aumento_tarifa']}% | "
        f"VPL R$ {metricas['vpl']/1e9:.2f}bi | "
        f"Payback {metricas['payback']:.1f} anos"
    )
    
    st.markdown("---")
    
    # VPL
    st.markdown("### 📊 Valor Presente Líquido")
    
    cores = ['#d32f2f' if v < 0 else '#388e3c' for v in df_cen['vpl']]
    
    fig = go.Figure(go.Bar(
        x=df_cen['aumento_pct'],
        y=df_cen['vpl']/1e9,
        marker_color=cores,
        text=[f"R$ {v/1e9:.2f}bi" for v in df_cen['vpl']],
        textposition='outside'
    ))
    
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(
        xaxis_title="Aumento Tarifário (%)",
        yaxis_title="VPL (R$ bilhões)",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Payback e TIR
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### ⏱️ Payback")
        df_pb = df_cen[df_cen['payback_simples'] < 30]
        
        fig = go.Figure(go.Scatter(
            x=df_pb['aumento_pct'],
            y=df_pb['payback_simples'],
            mode='lines+markers',
            line=dict(width=3, color='#1f77b4')
        ))
        
        fig.add_hline(y=15, line_dash="dash", annotation_text="Vida útil (15a)")
        fig.update_layout(height=300)
        
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown("### 📈 TIR")
        df_tir = df_cen[df_cen['tir'].notna()]
        
        if len(df_tir) > 0:
            fig = go.Figure(go.Scatter(
                x=df_tir['aumento_pct'],
                y=df_tir['tir'],
                mode='lines+markers',
                fill='tozeroy',
                line=dict(width=3, color='#2ca02c')
            ))
            
            fig.add_hline(y=8, line_dash="dash", annotation_text="TMA (8%)")
            fig.update_layout(height=300)
            
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# MAIN
# ============================================================================

def main():
    
    # Carrega dados
    dados, kpis_base, config, df_paradas = carregar_dados()
    
    # Sidebar
    filtros = criar_sidebar(dados)
    
    # Calcula métricas
    metricas = calcular_metricas_filtradas(filtros, kpis_base, dados)
    
    # TABS
    tab1, tab2, tab3 = st.tabs([
        "🏠 Home & Mapa",
        "💰 Viabilidade Econômica",
        "📊 Análise Operacional"
    ])
    
    with tab1:
        pagina_home(metricas, filtros, dados, df_paradas, config, kpis_base)
    
    with tab2:
        pagina_viabilidade(dados, metricas, filtros)
    
    with tab3:
        st.info("🚧 Em desenvolvimento - Rankings operacionais")

if __name__ == "__main__":
    main()
