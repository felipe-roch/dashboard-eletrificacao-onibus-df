"""
DASHBOARD FINAL - ELETRIFICAÇÃO FROTA ÔNIBUS DF
================================================
Versão Completa com:
- 9.287 paradas (TODAS!)
- Distribuição de tarifas detalhada
- Análise operacional com rankings
- Filtros globais funcionando
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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
    .stMetric [data-testid="stMetricDelta"] {color: white !important;}
    h1 {color: #1f77b4; font-weight: 700;}
    .alerta-ocupacao {
        padding: 1rem; border-radius: 8px; margin: 1rem 0; font-weight: bold;
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
        st.error(f"❌ Erro: {e}")
        st.info("Execute o NB6 primeiro!")
        st.stop()

# ============================================================================
# CÁLCULOS
# ============================================================================

def calcular_metricas_filtradas(filtros, kpis_base, dados):
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
    
    novos_usuarios = filtros.get('novos_usuarios', 0)
    novos_passes_ano = novos_usuarios * 3 * 365
    
    metricas['passageiros_projetados'] = metricas['passageiros_ano'] + novos_passes_ano
    metricas['taxa_projetada'] = (metricas['passageiros_projetados'] / metricas['capacidade_ano']) * 100
    
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
    centro = config['centro_mapa']
    
    m = folium.Map(
        location=[centro['lat'], centro['lon']],
        zoom_start=config['zoom_inicial'],
        tiles='CartoDB positron',
        prefer_canvas=True
    )
    
    # Garagens
    for g in garagens:
    # Monta popup rico com todas as informações
        popup_html = f"""
        <div style='font-family: Arial; width: 250px;'>
            <h4 style='margin: 0; color: #1f77b4;'>🏠 {g.get('garagem', 'N/A')}</h4>
            <hr style='margin: 5px 0;'>
            <b>Operadora:</b> {g.get('operadora', 'N/A')}<br>
            <b>Frota:</b> {g.get('frota', 0)} ônibus<br>
            <b>Carregadores:</b> {g.get('carregadores', 0)}<br>
            <b>Potência:</b> {g.get('potencia_mva', 0):.2f} MVA<br>
            <b>Custo Total:</b> R$ {g.get('custo_total', 0)/1e6:.2f} milhões
        </div>
        """
        
        folium.Marker(
            [g['lat'], g['lon']],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color='blue', icon='home', prefix='fa'),
            tooltip=f"🏠 {g.get('garagem', 'Garagem')}"
        ).add_to(m)
    
    # Terminais
    for t in terminais:
        folium.Marker(
            [t['lat'], t['lon']],
            popup=f"<b>⚡ {t['terminal']}</b><br>Carregadores: {t.get('carregadores', 0)}",
            icon=folium.Icon(color='green', icon='bolt', prefix='fa'),
            tooltip=t['terminal']
        ).add_to(m)
    
    # TODAS AS PARADAS! (9.287)
    if heatmap:
        heat_data = [[r['lat'], r['lon']] for _, r in df_paradas.iterrows()]
        HeatMap(heat_data, radius=15, blur=20).add_to(m)
    else:
        # USA TODAS AS 9.287 PARADAS!
        for _, p in df_paradas.iterrows():
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
# ============================================================================
# SIDEBAR
# ============================================================================

def criar_sidebar(dados):
    st.sidebar.markdown("## 🔧 Filtros")
    
    todas_ops = dados['operadoras']
    ops_sel = st.sidebar.multiselect(
        "Operadoras",
        todas_ops,
        todas_ops,
        help=f"{len(todas_ops)} operadoras disponíveis"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Projeção de Demanda")
    
    novos_usuarios = st.sidebar.slider(
        "+Novos Usuários (mil)",
        0, 200, 100, 10,
        help="Absorção do transporte pirata"
    ) * 1000
    
    st.sidebar.markdown("---")
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
    st.title("🚌 Eletrificação da Frota de Ônibus do DF")
    st.markdown("Dashboard com Análise de Demanda e Viabilidade Econômica")
    
    # KPIs PRINCIPAIS
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🚌 Frota", f"{metricas['frota']:,}")
    c2.metric("📍 Linhas", f"{metricas['linhas']:,}")
    c3.metric("🚏 Paradas", f"{len(df_paradas):,}")  # Total real!
    c4.metric("🌱 CO₂", f"{metricas['co2']/1000:.0f}k ton")
    c5.metric("📏 KM", f"{metricas['km_anual']/1e6:.0f}M/ano")
    
    st.markdown("---")
    
    # ANÁLISE TARIFÁRIA COM DISTRIBUIÇÃO
    st.markdown("### 💵 Impacto Tarifário no Projeto")
    
    TARIFA_ATUAL = kpis_base.get('tarifa_media_atual', 4.39)
    aumento_pct = filtros['aumento_tarifa']
    tarifa_nova = TARIFA_ATUAL * (1 + aumento_pct/100)
    
    # Cards de tarifas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Tarifa Atual", f"R$ {TARIFA_ATUAL:.2f}",
                 help="Média ponderada (dados API)")
    
    with col2:
        st.metric("Tarifa Premium", f"R$ {tarifa_nova:.2f}",
                 f"+{aumento_pct}%", delta_color="normal")
    
    with col3:
        receita_base = metricas['passageiros_ano'] * TARIFA_ATUAL
        receita_nova = metricas['passageiros_ano'] * tarifa_nova
        receita_adicional = receita_nova - receita_base
        st.metric("Receita Adicional", f"R$ {receita_adicional/1e9:.2f}bi/ano")
    
    with col4:
        if metricas['vpl'] > 0:
            st.metric("Status", "✅ VIÁVEL", f"VPL R$ {metricas['vpl']/1e9:.2f}bi")
        else:
            st.metric("Status", "❌ INVIÁVEL", f"VPL R$ {metricas['vpl']/1e9:.2f}bi")
    
    # DISTRIBUIÇÃO DE TARIFAS (NOVA SEÇÃO!)
    st.markdown("#### 📊 Distribuição Atual de Tarifas")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Gráfico de distribuição
        if 'distribuicao_tarifas' in kpis_base:
            dist = kpis_base['distribuicao_tarifas']
            
            tarifas = []
            percentuais = []
            linhas_qtd = []
            descricoes = []
            
            for tarifa, info in sorted(dist.items(), key=lambda x: float(x[0])):
                tarifas.append(f"R$ {float(tarifa):.2f}")
                percentuais.append(info['pct'] * 100)
                linhas_qtd.append(info['linhas'])
                descricoes.append(info['descricao'])
            
            fig = go.Figure(data=[go.Bar(
                x=tarifas,
                y=percentuais,
                text=[f"{p:.1f}%<br>({q} linhas)" for p, q in zip(percentuais, linhas_qtd)],
                textposition='outside',
                marker_color=['#3498db', '#2ecc71', '#e74c3c']
            )])
            
            fig.update_layout(
                title="Distribuição das Tarifas por Quantidade de Linhas",
                xaxis_title="Tarifa",
                yaxis_title="Percentual (%)",
                height=350
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("**💡 Com o aumento:**")
        
        if 'distribuicao_tarifas' in kpis_base:
            for tarifa, info in sorted(dist.items(), key=lambda x: float(x[0])):
                tarifa_val = float(tarifa)
                nova_tarifa = tarifa_val * (1 + aumento_pct/100)
                st.info(
                    f"**{info['descricao']}**<br>"
                    f"R$ {tarifa_val:.2f} → R$ {nova_tarifa:.2f}",
                    icon="💵"
                )
    
    st.markdown("---")
    
    # ANÁLISE DE OCUPAÇÃO
    st.markdown("### 📊 Análise de Taxa de Ocupação")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=['Atual'], y=[metricas['taxa_ocupacao']], name='Atual',
            marker_color='#1f77b4', text=f"{metricas['taxa_ocupacao']:.1f}%",
            textposition='outside'
        ))
        
        cor_proj = '#d32f2f' if metricas['taxa_projetada'] > 78 else '#2ca02c'
        fig.add_trace(go.Bar(
            x=['Projetada'], y=[metricas['taxa_projetada']],
            name=f"+{filtros['novos_usuarios']/1000:.0f}k usuários",
            marker_color=cor_proj, text=f"{metricas['taxa_projetada']:.1f}%",
            textposition='outside'
        ))
        
        fig.add_hline(y=78, line_dash="dash", line_color="red",
                      annotation_text="Limite Seguro (78%)")
        
        fig.update_layout(title="Taxa de Ocupação: Atual vs Projetada",
                         yaxis_title="Taxa (%)", height=350)
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        taxa_proj = metricas['taxa_projetada']
        
        if taxa_proj < 70:
            classe, icone, titulo = "alerta-ok", "✅", "Sistema Confortável"
            msg = f"Taxa de {taxa_proj:.1f}% permite crescimento."
        elif taxa_proj < 78:
            classe, icone, titulo = "alerta-aviso", "⚠️", "Sistema Sob Pressão"
            msg = f"Taxa de {taxa_proj:.1f}% próxima do limite."
        else:
            classe, icone, titulo = "alerta-perigo", "🚨", "Sistema Saturado!"
            msg = f"Taxa de {taxa_proj:.1f}% ACIMA do limite!"
        
        st.markdown(f"""
        <div class="alerta-ocupacao {classe}">
            <h3>{icone} {titulo}</h3>
            <p>{msg}</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # MAPA COM TODAS AS PARADAS
    st.markdown("### 🗺️ Infraestrutura de Recarga")
    st.info(f"📍 {len(filtros['operadoras'])} operadoras | **{len(df_paradas):,} paradas** no sistema")
    
    heatmap = st.checkbox("🔥 Heatmap")
    
    # Aviso de carregamento
    with st.spinner(f'⏳ Carregando {len(df_paradas):,} paradas no mapa... Pode levar até 30 segundos.'):
        mapa = criar_mapa_profissional(df_paradas, dados['garagens'], 
                                        dados['terminais'], config, filtros, heatmap)
    
    st.success(f"✅ Mapa carregado com {len(df_paradas):,} paradas!")
    st_folium(mapa, width=1400, height=500, returned_objects=[])

# ============================================================================
# VIABILIDADE
# ============================================================================

def pagina_viabilidade(dados, metricas, filtros):
    st.title("💰 Viabilidade Econômica")
    
    if len(dados.get('cenarios_financeiros', [])) == 0:
        st.warning("Dados financeiros indisponíveis.")
        return
    
    df_cen = pd.DataFrame(dados['cenarios_financeiros'])
    
    st.info(f"📌 Cenário: Aumento {filtros['aumento_tarifa']}% | VPL R$ {metricas['vpl']/1e9:.2f}bi")
    st.markdown("---")
    
    st.markdown("### 📊 Valor Presente Líquido")
    
    cores = ['#d32f2f' if v < 0 else '#388e3c' for v in df_cen['vpl']]
    
    fig = go.Figure(go.Bar(
        x=df_cen['aumento_pct'], y=df_cen['vpl']/1e9, marker_color=cores,
        text=[f"R$ {v/1e9:.2f}bi" for v in df_cen['vpl']], textposition='outside'
    ))
    
    fig.add_hline(y=0, line_dash="dash")
    fig.update_layout(xaxis_title="Aumento (%)", yaxis_title="VPL (R$ bi)", height=400)
    
    st.plotly_chart(fig, use_container_width=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("### ⏱️ Payback")
        df_pb = df_cen[df_cen['payback_simples'] < 30]
        
        fig = go.Figure(go.Scatter(x=df_pb['aumento_pct'], y=df_pb['payback_simples'],
                                   mode='lines+markers', line=dict(width=3)))
        fig.add_hline(y=15, line_dash="dash", annotation_text="Vida útil")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.markdown("### 📈 TIR")
        df_tir = df_cen[df_cen['tir'].notna()]
        
        if len(df_tir) > 0:
            fig = go.Figure(go.Scatter(x=df_tir['aumento_pct'], y=df_tir['tir'],
                                       mode='lines+markers', fill='tozeroy'))
            fig.add_hline(y=8, line_dash="dash", annotation_text="TMA")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# ANÁLISE OPERACIONAL (NOVA!)
# ============================================================================

def pagina_analise_operacional(metricas, kpis_base):
    """Análise Operacional com Rankings REAIS"""
    
    st.title("📊 Análise Operacional")
    
    # KPIs
    st.markdown("### 📈 Indicadores Operacionais")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Passageiros/Dia", f"{metricas['passageiros_ano']/365/1e6:.2f}M")
    col2.metric("KM/Dia", f"{metricas['km_anual']/365/1e6:.2f}M")
    col3.metric("Ônibus Ativos", f"{metricas['frota']:,}")
    
    st.markdown("---")
    
    # ========================================================================
    # RANKINGS COM DADOS REAIS
    # ========================================================================
    
    DIR_BASE = Path(r"C:\Users\Felipe\Documents\Trabalho_de_Logistica")
    
    # TOP 10 LINHAS MAIS LONGAS
    st.markdown("### 🚌 TOP 10 Linhas Mais Longas")
    
    # ... seu código anterior ...

    try:
        df_consolidado = pd.read_excel(DIR_BASE / 'data_processed' / 'NB1' / 'dados_consolidados.xlsx')

        # ... (após ler o df_consolidado)

        # Filtro para excluir a linha 206.1 da Marechal
        # Usamos o operador ~ para "negar" a condição (trazer tudo que NÃO seja isso)
        df_consolidado = df_consolidado[~((df_consolidado['linha_nome'].astype(str) == '206.1') & 
                                        (df_consolidado['operadora'] == 'MARECHAL'))]

               
        # Calcula distância total
        df_consolidado['km_total'] = df_consolidado['km_ida_circular'] + df_consolidado['km_volta']
        
        # 1. Pegamos o Top 10 e garantimos que a coluna 'linha_nome' seja STRING (Texto)
        # Isso evita que o Plotly trate o eixo Y como uma escala numérica
        top_longas = df_consolidado.nlargest(10, 'km_total')[['linha_nome', 'operadora', 'km_total']].copy()
        top_longas['linha_nome'] = top_longas['linha_nome'].astype(str)
        
        # 2. Ordenamos para que a maior fique no topo no gráfico de barras horizontais
        # O Plotly renderiza de baixo para cima, então ordenamos de forma crescente para o maior aparecer em cima
        top_longas = top_longas.sort_values(by='km_total', ascending=True)

        fig = px.bar(
            top_longas,
            x='km_total',
            y='linha_nome',
            orientation='h',
            color='operadora',
            title="TOP 10 Linhas Mais Longas (KM Total)",
            labels={'km_total': 'Distância (km)', 'linha_nome': 'Linha'},
            # Força o eixo Y a tratar os dados como categorias (nomes)
            category_orders={"linha_nome": top_longas['linha_nome'].tolist()}
        )
        
        # 3. Ajuste adicional para garantir que todos os nomes apareçam
        fig.update_yaxes(type='category')
        
        fig.update_layout(height=500) # Aumentei um pouco para não cortar os nomes
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar dados: {e}")
        
        st.markdown("---")
    
    # TOP 10 LINHAS COM MAIOR DEMANDA
    st.markdown("### 📈 TOP 10 Linhas com Maior Demanda")

    try:
        # 1. Carregar as duas bases
        df_horarios = pd.read_csv(DIR_BASE / 'data_processed' / 'NB2' / 'horarios_expandidos.csv')
        df_consolidado = pd.read_excel(DIR_BASE / 'data_processed' / 'NB1' / 'dados_consolidados.xlsx')

        # 2. Preparar as colunas para o merge (garantir que ambas sejam string)
        df_horarios['linha_nome'] = df_horarios['linha_nome'].astype(str)
        df_consolidado['linha_nome'] = df_consolidado['linha_nome'].astype(str)

        # 3. Mesclar as bases para trazer 'operadora' e 'cor_companhia_x' para os horários
        # Usamos 'left' para manter todos os horários, mesmo que a linha não esteja no consolidado
        df_merged = pd.merge(
            df_horarios, 
            df_consolidado[['linha_nome', 'operadora', 'cor_companhia_x']], 
            on='linha_nome', 
            how='left'
        )

        # 4. FILTRO: Desconsiderar a linha 0.808 da URBI
        # Usamos o ~ para manter tudo que NÃO atenda a essa condição específica
        df_merged = df_merged[~((df_merged['linha_nome'] == '0.808') & 
                                (df_merged['operadora'] == 'URBI'))]

        # 5. Agora sim, agrupar incluindo as informações da operadora
        demanda = df_merged.groupby(['linha_nome', 'operadora', 'cor_companhia_x']).size().reset_index(name='horarios_semana')
        
        # 6. Pegar o Top 10 e ordenar
        top_demanda = demanda.nlargest(10, 'horarios_semana').copy()
        top_demanda = top_demanda.sort_values(by='horarios_semana', ascending=True)

        # 7. Criar um mapa de cores para o Plotly usar as cores oficiais 'cor_companhia_x'
        cores_map = dict(zip(top_demanda['operadora'], top_demanda['cor_companhia_x']))

        fig = px.bar(
            top_demanda,
            x='horarios_semana',
            y='linha_nome',
            orientation='h',
            color='operadora',
            color_discrete_map=cores_map, # Usa as cores vindas da sua base!
            title="TOP 10 Linhas com Maior Demanda (Horários/Semana)",
            labels={'horarios_semana': 'Viagens por Semana', 'linha_nome': 'Linha'}
        )

        fig.update_yaxes(type='category')
        fig.update_layout(height=450, showlegend=True)
        
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ Erro ao processar demanda: {e}")
    
    # TOP 10 OPERADORAS POR FROTA
    st.markdown("### 🚌 TOP 10 Operadoras por Frota Elétrica")
    
    try:
        df_frota = pd.read_excel(
            DIR_BASE / 'data_processed' / 'NB2' / 'analise_frota_completa.xlsx',
            sheet_name='Investimento'
        )
        
        # Soma frota por operadora
        frota_op = df_frota.groupby('operadora')['frota_total'].sum().reset_index()
        top_frota = frota_op.nlargest(10, 'frota_total')
        
        fig = px.bar(
            top_frota,
            x='frota_total',
            y='operadora',
            orientation='h',
            title="TOP 10 Operadoras por Frota Elétrica",
            labels={'frota_total': 'Frota Elétrica', 'operadora': 'Operadora'},
            color='frota_total',
            color_continuous_scale='Blues'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, width='stretch')
        
    except Exception as e:
        st.warning(f"⚠️ Não foi possível carregar dados: {e}")

# ============================================================================
# MAIN
# ============================================================================

def main():
    dados, kpis_base, config, df_paradas = carregar_dados()
    filtros = criar_sidebar(dados)
    metricas = calcular_metricas_filtradas(filtros, kpis_base, dados)
    
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
        pagina_analise_operacional(metricas, kpis_base)

if __name__ == "__main__":
    main()
