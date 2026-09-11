import streamlit as st
import fastf1
import fastf1.plotting
from fastf1 import utils
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os

# ============================================
# CONFIGURAÇÃO GERAL E CACHE
# ============================================
st.set_page_config(page_title="F1 Telemetry Dashboard", page_icon="🏎️", layout="wide")

# Criar pasta de cache se não existir e habilitar
os.makedirs("f1_cache", exist_ok=True)
fastf1.Cache.enable_cache("f1_cache")

# Desabilitar avisos internos do fastf1 no terminal
fastf1.plotting.setup_mpl(misc_mpl_mods=False) 

# ============================================
# CSS PROFISSIONAL - SAAS
# ============================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp {background-color: #f8fafc;}
    .main-title {font-size: 2.2rem; font-weight: 800; color: #0f172a; text-align: center; margin-bottom: 0.2rem;}
    .subtitle {font-size: 1.05rem; color: #64748b; text-align: center; margin-bottom: 2rem;}
    .dashboard-card {background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.02); margin-bottom: 1.2rem;}
    .card-header {font-size: 1.1rem; font-weight: 700; color: #1e293b; margin-bottom: 1rem; border-bottom: 1px solid #f1f5f9; padding-bottom: 0.5rem;}
</style>
""", unsafe_allow_html=True)

# ============================================
# FUNÇÕES DE CARREGAMENTO DE DADOS (CACHEADAS)
# ============================================
@st.cache_data(ttl=86400) # Cache expira em 1 dia
def carregar_eventos(ano):
    schedule = fastf1.get_event_schedule(ano)
    # Filtra apenas eventos que não são testes de pré-temporada
    eventos = schedule[schedule['EventFormat'] != 'testing']['EventName'].tolist()
    return eventos
    
@st.cache_resource   # <--- MUDE APENAS ESTA LINHA
def carregar_sessao(ano, corrida, sessao_tipo):
    session = fastf1.get_session(ano, corrida, sessao_tipo)
    session.load(telemetry=True, laps=True, weather=False)
    return session

# ============================================
# INTERFACE DO USUÁRIO
# ============================================
st.markdown('<div class="main-title">🏎️ Central de Telemetria F1</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Análise de Dados Avançada e Comparação de Pilotos (Estilo MoTeC)</div>', unsafe_allow_html=True)

# Barra Superior de Controles
with st.container():
    st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">⚙️ Configuração do Grand Prix</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
    with col1:
        ano = st.selectbox("Ano", list(range(2026, 2017, -1)))
    with col2:
        eventos_disponiveis = carregar_eventos(ano)
        corrida = st.selectbox("Corrida", eventos_disponiveis)
    with col3:
        sessao_tipo = st.selectbox("Sessão", ["FP1", "FP2", "FP3", "Q", "S", "SQ", "R"], 
                                   format_func=lambda x: {"FP1":"Treino Livre 1", "FP2":"Treino Livre 2", "FP3":"Treino Livre 3", 
                                                          "Q":"Classificação", "S":"Sprint", "SQ":"Sprint Shootout", "R":"Corrida"}[x])
    with col4:
        st.write("") # Espaçamento
        st.write("")
        carregar_btn = st.button("Carregar Dados", use_container_width=True, type="primary")
    
    st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# LÓGICA PRINCIPAL APÓS CARREGAMENTO
# ============================================
if carregar_btn or 'session' in st.session_state:
    if carregar_btn:
        with st.spinner('Conectando aos servidores da FIA e processando telemetria...'):
            try:
                session = carregar_sessao(ano, corrida, sessao_tipo)
                st.session_state['session'] = session
            except Exception as e:
                st.error(f"Não foi possível carregar esta sessão. Verifique se ela já aconteceu. Erro: {e}")
                st.stop()
    else:
        session = st.session_state['session']

    # Criando as Abas
    tab1, tab2, tab3 = st.tabs(["📊 Resultados Gerais", "📈 Telemetria MoTeC", "💡 Ideias p/ Evolução"])

    # ABA 1: RESULTADOS GERAIS
    with tab1:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="card-header">Classificação Final - {corrida} ({ano})</div>', unsafe_allow_html=True)
        
        # Formatando o DataFrame de resultados
        df_results = session.results[['Position', 'DriverNumber', 'BroadcastName', 'Abbreviation', 'TeamName', 'Time', 'Status', 'Points']].copy()
        df_results.columns = ['Pos', 'Nº', 'Piloto', 'Sigla', 'Equipe', 'Tempo/Delta', 'Status', 'Pontos']
        
        st.dataframe(df_results, use_container_width=True, hide_index=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ABA 2: TELEMETRIA MoTeC
    with tab2:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Comparação de Telemetria (Volta mais rápida)</div>', unsafe_allow_html=True)
        
        pilotos_disponiveis = session.results['Abbreviation'].dropna().tolist()
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            piloto_a = st.selectbox("Piloto de Referência (A)", pilotos_disponiveis, index=0)
        with col_p2:
            piloto_b = st.selectbox("Piloto Comparado (B)", pilotos_disponiveis, index=1 if len(pilotos_disponiveis)>1 else 0)

        if st.button("Gerar Gráfico MoTeC", key="btn_motec"):
            with st.spinner('Processando canais de telemetria...'):
                try:
                    # Pegar as voltas mais rápidas de cada um
                    lap_a = session.laps.pick_driver(piloto_a).pick_fastest()
                    lap_b = session.laps.pick_driver(piloto_b).pick_fastest()
                    
                    # Obter telemetria
                    tel_a = lap_a.get_telemetry()
                    tel_b = lap_b.get_telemetry()
                    
                    # Calcular Delta Time (A vs B)
                    delta_time, ref_tel, comp_tel = utils.delta_time(lap_a, lap_b)
                    
                    # Cores das equipes (oficial da F1)
                    cor_a = fastf1.plotting.get_team_color(lap_a['TeamName'], session=session)
                    cor_b = fastf1.plotting.get_team_color(lap_b['TeamName'], session=session)
                    
                    # Se as cores forem iguais (mesma equipe), escurecemos uma para diferenciar
                    if cor_a == cor_b:
                        cor_b = "#ffffff" # Branco como contraste caso sejam companheiros
                        
                    # CRIAÇÃO DO GRÁFICO TIPO MOTEC (Fundo Escuro para contraste profissional)
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
                    
                    # 1. Velocidade
                    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Speed'], name=f"{piloto_a} (Speed)", line=dict(color=cor_a, width=2)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Speed'], name=f"{piloto_b} (Speed)", line=dict(color=cor_b, width=2)), row=1, col=1)
                    
                    # 2. Delta Time
                    fig.add_trace(go.Scatter(x=ref_tel['Distance'], y=delta_time, name=f"Delta {piloto_a}-{piloto_b}", line=dict(color="#f1c40f", width=2)), row=2, col=1)
                    # Linha zero do delta
                    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)
                    
                    # 3. Acelerador
                    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Throttle'], name=f"{piloto_a} (Thr)", line=dict(color=cor_a, width=2)), row=3, col=1)
                    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Throttle'], name=f"{piloto_b} (Thr)", line=dict(color=cor_b, width=2)), row=3, col=1)
                    
                    # 4. Freio
                    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['Brake'], name=f"{piloto_a} (Brk)", line=dict(color=cor_a, width=2, shape='hv')), row=4, col=1)
                    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['Brake'], name=f"{piloto_b} (Brk)", line=dict(color=cor_b, width=2, shape='hv')), row=4, col=1)
                    
                    # 5. Marcha
                    fig.add_trace(go.Scatter(x=tel_a['Distance'], y=tel_a['nGear'], name=f"{piloto_a} (Gear)", line=dict(color=cor_a, width=2, shape='hv')), row=5, col=1)
                    fig.add_trace(go.Scatter(x=tel_b['Distance'], y=tel_b['nGear'], name=f"{piloto_b} (Gear)", line=dict(color=cor_b, width=2, shape='hv')), row=5, col=1)
                    
                    # Ajustes de Layout MoTeC
                    fig.update_layout(
                        height=900,
                        plot_bgcolor='#111111',
                        paper_bgcolor='#ffffff',
                        font=dict(color='#333333'),
                        hovermode="x unified",
                        showlegend=False,
                        margin=dict(l=10, r=10, t=40, b=10)
                    )
                    
                    # Grades escuras sutis
                    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#333333', title_text="Distância (m)", row=5, col=1)
                    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#333333')
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                except Exception as e:
                    st.error(f"Erro ao processar a telemetria (talvez um piloto não tenha registrado volta rápida). Erro: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)

    # ABA 3: SUGESTÕES PARA O FUTURO
    with tab3:
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">🚀 Próximos Passos e Opções de Análise</div>', unsafe_allow_html=True)
        
        st.markdown("""
        Se você quiser expandir este projeto, aqui estão as análises mais valiosas que engenheiros de dados da F1 fazem (e que podem ser feitas com o `fastf1`):
        
        1. **Track Dominance (Minissetores):**
           * Dividir a pista em 25 ou 50 minissetores geométricos.
           * Avaliar qual piloto foi mais rápido em cada minissetor.
           * Colorir o mapa geográfico do circuito (`X` e `Y` da telemetria) com a cor da equipe que foi mais rápida em cada trecho (revela carros bons de reta vs carros bons de curva).
           
        2. **Cornering Analysis (Gráfico de Tração e Frenagem):**
           * Criar um gráfico de dispersão (*Scatter Plot*) onde o Eixo X é a **Aceleração Lateral** (Força G em curvas) e Eixo Y é a **Aceleração Longitudinal** (Frenagem e Motor).
           * Isso gera um "Círculo de Tração", permitindo ver quem está extraindo mais aderência combinada do pneu.
           
        3. **Gráfico de Ritmo de Corrida (Violin ou Box Plot):**
           * Pegar os tempos de todas as voltas de todos os pilotos durante a Corrida (`session.laps`).
           * Descartar voltas de entrada/saída de box e Safety Car.
           * Plotar a distribuição de ritmo ao longo dos stints. Isso prova quem tinha o melhor carro com o tanque pesado vs vazio.
           
        4. **Degradação de Pneus (Tire Strategy):**
           * Analisar a variável `lap['Compound']` (Soft, Medium, Hard) e `lap['TyreLife']`.
           * Fazer um gráfico de regressão linear para mostrar quantos décimos de segundo por volta um pneu Soft perde no Bahrain vs Pneu Hard.
        """)
        st.markdown('</div>', unsafe_allow_html=True)
