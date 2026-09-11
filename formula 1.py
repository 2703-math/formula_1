import streamlit as st
import fastf1
import fastf1.plotting
from fastf1 import utils
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

# ============================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================
st.set_page_config(
    page_title="F1 Telemetry Dashboard",
    page_icon="🏎️",
    layout="wide"
)

# ============================================
# CONFIGURAÇÃO DE CACHE DO FASTF1
# ============================================
cache_dir = './f1_cache'
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)
fastf1.plotting.setup_mpl(misc_mpl_mods=False) 

# ============================================
# CSS PROFISSIONAL - ESTILO SAAS / DASHBOARD
# ============================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {background-color: #f8fafc;}
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .main-title {font-size: 2.2rem; font-weight: 800; color: #0f172a; text-align: center; margin-bottom: 0.2rem; letter-spacing: -0.5px;}
    .subtitle {font-size: 1.05rem; color: #64748b; text-align: center; margin-bottom: 2rem; font-weight: 400;}
    .dashboard-card {background: #ffffff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02); margin-bottom: 1.2rem;}
    .card-header {font-size: 1.05rem; font-weight: 700; color: #1e293b; margin-bottom: 1.0rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.6rem;}
</style>
""", unsafe_allow_html=True)

# ============================================
# FUNÇÕES DE CARREGAMENTO BLINDADAS
# ============================================
@st.cache_data(ttl=86400)
def carregar_eventos(ano):
    try:
        schedule = fastf1.get_event_schedule(ano)
        eventos = schedule[schedule['EventFormat'] != 'testing']['EventName'].tolist()
        return eventos
    except Exception:
        return []

@st.cache_resource
def carregar_sessao(ano, corrida, sessao_tipo):
    try:
        session = fastf1.get_session(ano, corrida, sessao_tipo)
        # Força o carregamento completo de telemetria, voltas e meteorologia
        session.load(telemetry=True, laps=True, weather=True)
        
        # Validação de segurança: se as voltas vierem vazias, força um recarregamento manual
        if session.laps is None or len(session.laps) == 0:
            session.load_laps(with_telemetry=True)
            
        return session, None
    except Exception as e:
        return None, str(e)

# ============================================
# INTERFACE PRINCIPAL
# ============================================
st.markdown('<div class="main-title">🏎️ Central de Telemetria F1</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Análise de Dados Avançada e Comparação de Pilotos (Estilo MoTeC)</div>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">⚙️ Configuração do Grand Prix</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
    with col1:
        ano = st.selectbox("Ano", list(range(2026, 2017, -1)))
    with col2:
        eventos_disponiveis = carregar_eventos(ano)
        if not eventos_disponiveis:
            st.error("Erro ao carregar o calendário deste ano. Tente outro ano.")
            st.stop()
        corrida = st.selectbox("Corrida", eventos_disponiveis)
    with col3:
        sessao_tipo = st.selectbox("Sessão", ["FP1", "FP2", "FP3", "Q", "S", "SQ", "R"], 
                                   format_func=lambda x: {"FP1":"Treino Livre 1", "FP2":"Treino Livre 2", "FP3":"Treino Livre 3", 
                                                          "Q":"Classificação", "S":"Sprint", "SQ":"Sprint Shootout", "R":"Corrida"}[x])
    with col4:
        st.write("")
        st.write("")
        carregar_btn = st.button("Carregar Dados", use_container_width=True, type="primary")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Gerenciamento de Estado da Sessão
if carregar_btn or 'session' in st.session_state:
    if carregar_btn:
        with st.spinner('Conectando aos servidores da F1 e baixando pacotes de dados...'):
            session, erro = carregar_sessao(ano, corrida, sessao_tipo)
            if erro:
                st.error(f"Falha crítica ao carregar a sessão: {erro}")
                st.stop()
            else:
                st.session_state['session'] = session
    else:
        session = st.session_state['session']

    tab1, tab2, tab3 = st.tabs(["  📊 Resultados Gerais  ", "  📈 Telemetria MoTeC  ", "  💡 Sugestões de Análise  "])

    # ABA 1: RESULTADOS GERAIS
    with tab1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header">Classificação Oficial - {corrida} ({ano})</div>', unsafe_allow_html=True)
        
        try:
            if hasattr(session, 'results') and not session.results.empty:
                df_results = session.results[['Position', 'DriverNumber', 'BroadcastName', 'Abbreviation', 'TeamName', 'Time', 'Status', 'Points']].copy()
                df_results.columns = ['Pos', 'Nº', 'Piloto', 'Sigla', 'Equipe', 'Tempo/Delta', 'Status', 'Pontos']
                st.dataframe(df_results, use_container_width=True, hide_index=True)
            else:
                st.warning("Os dados de resultados oficiais ainda não foram publicados para esta sessão.")
        except Exception as e:
            st.error(f"Erro ao exibir tabela de resultados: {e}")
            
        st.markdown('</div>', unsafe_allow_html=True)

    # ABA 2: TELEMETRIA MoTeC
    with tab2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Comparação de Canais de Telemetria (Volta Mais Rápida)</div>', unsafe_allow_html=True)
        
        try:
            pilotos_disponiveis = session.results['Abbreviation'].dropna().tolist()
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                piloto_a = st.selectbox("Piloto de Referência (A)", pilotos_disponiveis, index=0)
            with col_p2:
                piloto_b = st.selectbox("Piloto Comparado (B)", pilotos_disponiveis, index=1 if len(pilotos_disponiveis)>1 else 0)

            if st.button("Gerar Gráfico MoTeC", key="btn_motec"):
                with st.spinner('Processando canais de alta frequência...'):
                    lap_a = session.laps.pick_driver(piloto_a).pick_fastest()
                    lap_b = session.laps.pick_driver(piloto_b).pick_fastest()
                    
                    tel_a = lap_a.get_telemetry()
                    tel_b = lap_b.get_telemetry()
                    
                    delta_time, ref_tel, comp_tel = utils.delta_time(lap_a, lap_b)
                    
                    cor_a = fastf1.plotting.get_team_color(lap_a['TeamName'], session=session)
                    cor_b = fastf1.plotting.get_team_color(lap_b['TeamName'], session=session)
                    
                    if cor_a == cor_b:
                        cor_b = "#ffffff"
                        
                    fig = make_subplots(
                        rows=5, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03,
                        subplot_titles=(
                            f"Velocidade (km/h) - {lap_a['LapTime'].total_seconds():.3f}s vs {lap_b['LapTime'].total_seconds():.3f}s", 
                            "Delta Time (s) - A(Zero) vs B", 
                            "Acelerador (%)", 
                            "Freio (Brake)", 
                            "Marcha (Gear)"
                        )
                    )
                    
                    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Speed'], name=f"{piloto_a}", line=dict(color=cor_a, width=2)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Speed'], name=f"{piloto_b}", line=dict(color=cor_b, width=2)), row=1, col=1)
                    
                    fig.add_trace(go.Scatter(x=ref_tel['Distance'], y=delta_time, name="Delta", line=dict(color="#f1c40f", width=2)), row=2, col=1)
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
                    
                    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Throttle'], name=f"{piloto_a} Thr", line=dict(color=cor_a, width=2)), row=3, col=1)
                    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Throttle'], name=f"{piloto_b} Thr", line=dict(color=cor_b, width=2)), row=3, col=1)
                    
                    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Brake'], name=f"{piloto_a} Brk", line=dict(color=cor_a, width=2, shape='hv')), row=4, col=1)
                    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Brake'], name=f"{piloto_b} Brk", line=dict(color=cor_b, width=2, shape='hv')), row=4, col=1)
                    
                    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['nGear'], name=f"{piloto_a} Gear", line=dict(color=cor_a, width=2, shape='hv')), row=5, col=1)
                    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['nGear'], name=f"{piloto_b} Gear", line=dict(color=cor_b, width=2, shape='hv')), row=5, col=1)
                    
                    fig.update_layout(
                        height=850,
                        plot_bgcolor='#111111',
                        paper_bgcolor='#ffffff',
                        font=dict(color='#333333'),
                        hovermode="x unified",
                        showlegend=False,
                        margin=dict(l=10, r=10, t=40, b=10)
                    )
                    
                    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333333', title_text="Distância (m)", row=5, col=1)
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333333')
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
        except Exception as e:
            st.info("Selecione os pilotos e clique em 'Gerar Gráfico MoTeC' para carregar a comparação.")
            
        st.markdown('</div>', unsafe_allow_html=True)

    # ABA 3: SUGESTÕES
    with tab3:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">🚀 Próximos Passos recomendados</div>', unsafe_allow_html=True)
        st.markdown("""
        * **Análise de Minissetores (Track Dominance):** Mapear quais equipes dominam trechos de alta vs baixa velocidade.
        * **Distribuição de Ritmo de Corrida:** Avaliar a consistência dos compostos de pneus ao longo dos stints.
        """)
        st.markdown('</div>', unsafe_allow_html=True)

# Rodapé
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; font-size: 0.85rem; padding: 1rem;">
    🏎️ <b>F1 Telemetry Dashboard SaaS</b> — Desenvolvido com Streamlit e FastF1
</div>
""", unsafe_allow_html=True)
