import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, date, timedelta
import re
import random
import json
import os
import time
import base64

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Mentor SpartaJus",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CONSTANTES GLOBAIS ---
DB_FILE = "sparta_users.json"
LOGO_FILE = "logo_spartajus.jpg" 
ADMIN_USER = "fux_concurseiro" # Usuário Moderador

# --- FUNÇÕES DE PERSISTÊNCIA (JSON) ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_db(db_data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=4, default=str)

# --- ESTILOS CSS (CLEAN UI + TEMA ESPARTANO) ---
st.markdown("""
    <style>
    /* --- REMOÇÃO DE ELEMENTOS VISUAIS DO STREAMLIT --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    
    /* Fundo Geral */
    .stApp {
        background-color: #708090; /* Ardósia */
        color: #C2D5ED; /* Azul Claro/Gelo */
    }
    
    /* Texto Geral e Labels */
    .stMarkdown, .stText, p, label, .stDataFrame, .stExpander {
        color: #C2D5ED !important;
    }

    /* Inputs */
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input, 
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea > div > div > textarea {
        background-color: #4a5a6a; /* Tom mais escuro de ardósia */
        color: #C2D5ED;
        border-color: #C4A484; /* Marrom */
    }
    
    /* Placeholder e textos secundários */
    ::placeholder {
        color: #a0b0c0 !important;
        opacity: 0.7;
    }
    
    /* Títulos - Azul Gelo (#C2D5ED) */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #C2D5ED !important; 
        font-family: 'Helvetica Neue', sans-serif;
        text-shadow: 1px 1px 2px black;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #586878; 
        border-right: 2px solid #C4A484;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #C2D5ED !important;
    }
    
    /* Botões */
    .stButton>button {
        background-color: #4a5a6a;
        color: #C2D5ED; 
        border: 1px solid #D4AF37; 
        border-radius: 4px;
        height: 3em;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #D4AF37; 
        color: #2c3e50; 
        border-color: #C2D5ED;
    }
    
    /* Cards Personalizados */
    .metric-card {
        background-color: #586878;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        text-align: center;
        border: 1px solid #C4A484; 
    }
    .metric-card h4, .metric-card p {
        color: #C2D5ED !important;
    }
    
    .rank-card {
        background: linear-gradient(90deg, #3e4e5e, #586878);
        color: #C2D5ED;
        padding: 20px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
        border: 2px solid #D4AF37;
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.2);
    }
    
    /* Mod Message Box (Alertas) */
    .mod-message {
        background-color: #2c3e50;
        border-left: 5px solid #D4AF37;
        border-right: 1px solid #D4AF37;
        border-top: 1px solid #D4AF37;
        border-bottom: 1px solid #D4AF37;
        padding: 15px;
        margin-top: 15px;
        border-radius: 8px;
        color: #C2D5ED;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }

    /* Podium Cards */
    .podium-gold {
        background: linear-gradient(180deg, #D4AF37 0%, #B8860B 100%);
        color: #000 !important;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #FFD700;
        transform: scale(1.05);
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.5);
    }
    .podium-gold h1, .podium-gold h2, .podium-gold p {
        color: #000 !important;
        text-shadow: none;
    }
    
    .podium-silver {
        background: linear-gradient(180deg, #C0C0C0 0%, #A9A9A9 100%);
        color: #000 !important;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #D3D3D3;
        margin-top: 15px;
    }
    .podium-silver h2, .podium-silver h3, .podium-silver p {
        color: #000 !important;
        text-shadow: none;
    }

    .podium-bronze {
        background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%);
        color: #fff !important;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #A0522D;
        margin-top: 25px;
    }
    .podium-bronze h2, .podium-bronze h3, .podium-bronze p {
        color: #fff !important;
        text-shadow: none;
    }
    
    /* Tabelas */
    [data-testid="stDataFrame"] {
        border: 1px solid #C4A484;
        background-color: #4a5a6a;
    }
    
    /* Container da Árvore */
    .tree-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-top: 20px;
        background-color: #4a5a6a;
        border-radius: 100%;
        width: 350px;
        height: 350px;
        margin-left: auto;
        margin-right: auto;
        border: 4px solid #C4A484;
        overflow: hidden; 
    }
    
    /* Toast e Mensagens */
    .stToast {
        background-color: #586878 !important;
        color: #C2D5ED !important;
    }
    .stAlert {
        background-color: #4a5a6a;
        color: #C2D5ED;
        border: 1px solid #C4A484;
    }

    /* LOGO HARMONIZATION */
    .stImage {
        display: flex;
        justify-content: center;
    }
    .stImage img {
        width: 100%; 
        mix-blend-mode: multiply;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---

def parse_time_str_to_min(t_str):
    t_str = str(t_str).lower().replace(' ', '')
    total_min = 0
    try:
        if 'h' in t_str:
            parts = t_str.split('h')
            hours = int(parts[0]) if parts[0].isdigit() else 0
            rest = parts[1]
            if 'm' in rest:
                mins = int(rest.split('m')[0]) if rest.split('m')[0].isdigit() else 0
            elif rest.isdigit():
                mins = int(rest)
            else:
                mins = 0
            total_min = hours * 60 + mins
        elif 'm' in t_str:
            total_min = int(t_str.split('m')[0])
        elif ':' in t_str:
            h, m = t_str.split(':')
            total_min = int(h)*60 + int(m)
        elif t_str.isdigit():
            total_min = int(t_str)
    except:
        return 0
    return total_min

def generate_tree_svg(branches):
    scale = min(max(branches, 1), 50) / 10.0
    if branches <= 0:
        return """
        <svg width="300" height="300" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect x="40" y="80" width="20" height="20" fill="#5c4033" />
            <text x="50" y="70" font-size="5" text-anchor="middle" fill="#C2D5ED">A árvore secou...</text>
        </svg>
        """
    
    leaves_svg = ""
    random.seed(42)
    trunk_h = 30 + (branches * 0.5)
    trunk_h = min(trunk_h, 60)
    trunk_y = 100 - trunk_h
    count = max(1, branches)
    count = min(count, 150)
    
    for i in range(count):
        cx = 50 + random.randint(-20 - int(branches/2), 20 + int(branches/2))
        cy = trunk_y + random.randint(-20 - int(branches/2), 10)
        r = random.randint(3, 6)
        color = "#047a0a" # Verde
        leaves_svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{color}" opacity="0.9" />'

    return f"""
    <svg width="350" height="350" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <rect x="45" y="{trunk_y}" width="10" height="{trunk_h}" fill="#8B4513" />
        {leaves_svg}
        <text x="50" y="95" font-size="4" text-anchor="middle" fill="#C2D5ED">Ramos Vivos: {branches}</text>
    </svg>
    """

def get_patent(total_questions):
    patentes = [
        "Andarilho de Vade Mecum",
        "Saco de Pancada da Banca",
        "Cadastro de Reserva",
        "Titã Nota de Corte",
        "Espartano Jurídico"
    ]
    index = min(int(total_questions / 5000), 4)
    return patentes[index]

def get_stars(total_pages):
    raw_bronze = int(total_pages / 1000)
    gold = raw_bronze // 9
    remainder_gold = raw_bronze % 9
    if gold >= 3: return 3, 0, 0
    silver = remainder_gold // 3
    bronze = remainder_gold % 3
    return gold, silver, bronze

def calculate_streak(logs):
    if not logs: return 0
    study_dates = sorted([log['data'] for log in logs if log.get('estudou')], reverse=True)
    if not study_dates: return 0
    
    streak = 0
    last_date_obj = datetime.strptime(study_dates[0], "%Y-%m-%d").date()
    today = date.today()
    
    if (today - last_date_obj).days > 1:
        return 0

    current_check = last_date_obj
    for d_str in study_dates:
        d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        if d_obj == current_check:
            streak += 1
            current_check -= timedelta(days=1)
        elif d_obj < current_check:
            break
            
    return streak

# --- AUTH SYSTEM ---
def login_page():
    c1, c2, c3 = st.columns([1, 2, 1]) 
    if os.path.exists(LOGO_FILE):
        with c2:
            st.image(LOGO_FILE)
        
    st.title("🏛️ Mentor SpartaJus - Login")
    st.markdown("### Bem-vindo ao Campo de Batalha do Conhecimento")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("Entrar")
        username = st.text_input("Usuário").strip() 
        password = st.text_input("Senha", type="password")
        if st.button("Login"):
            db = load_db()
            if username in db and db[username]['password'] == password:
                st.session_state['user'] = username
                st.session_state['user_data'] = db[username]
                if 'admin_user' in st.session_state: del st.session_state['admin_user']
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

    with col2:
        st.subheader("Registrar")
        new_user = st.text_input("Novo Usuário").strip()
        new_pass = st.text_input("Nova Senha", type="password")
        if st.button("Criar Conta"):
            db = load_db()
            if new_user in db:
                st.error("Usuário já existe.")
            elif new_user and new_pass:
                db[new_user] = {
                    "password": new_pass,
                    "logs": [],
                    "tree_branches": 1,
                    "created_at": str(datetime.now())
                }
                save_db(db)
                st.success("Conta criada! Faça login.")
            else:
                st.warning("Preencha todos os campos.")

def save_current_user_data():
    if 'user' in st.session_state and 'user_data' in st.session_state:
        db = load_db()
        db[st.session_state['user']] = st.session_state['user_data']
        save_db(db)

# --- APP PRINCIPAL ---
def main_app():
    user = st.session_state['user']
    user_data = st.session_state['user_data']
    
    is_admin_mode = False
    admin_name = ""
    is_real_admin = (user == ADMIN_USER)
    
    if 'admin_user' in st.session_state and st.session_state['admin_user'] == ADMIN_USER:
        is_admin_mode = True
        admin_name = st.session_state['admin_user']

    # Garantir chaves básicas no JSON
    if 'logs' not in user_data: user_data['logs'] = []
    if 'tree_branches' not in user_data: user_data['tree_branches'] = 1
    if 'mod_message' not in user_data: user_data['mod_message'] = "" 
    
    # --- CONFIGURAR API KEY FIXA (Decodificando) ---
    # (API Key foi removida a pedido em passos anteriores, mas lógica base mantida se necessário no futuro)
    
    # --- CÁLCULOS TOTAIS ---
    total_questions = sum([log.get('questoes', 0) for log in user_data['logs']])
    total_pages = sum([log.get('paginas', 0) for log in user_data['logs']])
    streak = calculate_streak(user_data['logs'])
    
    current_level = int(total_questions / 1000)
    current_patent = get_patent(total_questions)
    g_stars, s_stars, b_stars = get_stars(total_pages)

    # --- BARRA LATERAL ---
    with st.sidebar:
        if os.path.exists(LOGO_FILE):
            st.image(LOGO_FILE)
            
        if is_real_admin or is_admin_mode:
            with st.expander("🛡️ PAINEL DO MODERADOR", expanded=True):
                st.caption("Área restrita de comando")
                
                if is_real_admin:
                    db = load_db()
                    # Filtra apenas usuários, removendo a chave de alertas globais se aparecer
                    all_users = [k for k in db.keys() if k != "global_alerts"]
                    
                    st.markdown("**Gerenciar Usuários**")
                    target_user = st.selectbox("Selecione:", all_users)
                    
                    if st.button("👁️ Acessar Dashboard"):
                        st.session_state['admin_user'] = ADMIN_USER
                        st.session_state['user'] = target_user
                        st.session_state['user_data'] = db[target_user]
                        st.rerun()
                    
                    st.markdown("**Enviar Recado (Individual)**")
                    current_msg = db[target_user].get('mod_message', '')
                    new_message = st.text_area("Mensagem:", value=current_msg)
                    if st.button("📨 Enviar Recado"):
                        db[target_user]['mod_message'] = new_message
                        save_db(db)
                        st.success("Recado enviado!")
                    
                    # (Removido criar/excluir daqui pois foi para a nova aba)
                
                elif is_admin_mode:
                    st.warning(f"Visualizando: {user}")
                    if st.button("⬅️ Voltar ao Admin"):
                        st.session_state['user'] = ADMIN_USER
                        st.session_state['user_data'] = load_db()[ADMIN_USER]
                        st.rerun()

        st.divider()
        st.header(f"Olá, {user}")
        
        if st.button("Sair / Logout"):
            del st.session_state['user']
            del st.session_state['user_data']
            if 'admin_user' in st.session_state: del st.session_state['admin_user']
            st.rerun()
            
        st.divider()
        st.header("⚙️ Configurações")
        st.info("Versão: SpartaJus Clean Edition")

    # --- CABEÇALHO ---
    st.title("🏛️ Mentor SpartaJus")
    
    # --- BARRA DE PROGRESSO (Patente) ---
    progress_val = total_questions % 5000
    percent_val = (progress_val / 5000) * 100
    next_goal = (int(total_questions / 5000) + 1) * 5000
    remaining = 5000 - progress_val
    
    st.markdown(f"""
    <div style="background-color: #4a5a6a; border-radius: 12px; padding: 4px; margin-bottom: 10px; border: 1px solid #D4AF37; box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
        <div style="width: {percent_val}%; background-color: #047a0a; height: 24px; border-radius: 8px; text-align: center; line-height: 24px; color: white; font-weight: bold; font-size: 0.9em; white-space: nowrap; overflow: visible; transition: width 0.8s;">
            &nbsp;{percent_val:.1f}%
        </div>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 0.85em; color: #C2D5ED; margin-top: -8px; margin-bottom: 20px;">
        <span>⚔️ Atual: {progress_val} questões</span>
        <span>🎯 Próxima Patente: Falta {remaining}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col_status1, col_status2 = st.columns([2, 1])
    with col_status1:
        st.markdown(f"""
        <div class="rank-card">
            <h2>{user.upper()}</h2>
            <h3>🛡️ Patente: {current_patent}</h3>
            <p>Total Acumulado: {total_questions} | 🔥 Fogo Espartano: {streak} dias</p>
        </div>
        """, unsafe_allow_html=True)
        
    with col_status2:
        star_html = ""
        for _ in range(g_stars): star_html += "🟡"
        for _ in range(s_stars): star_html += "⚪"
        for _ in range(b_stars): star_html += "🟤"
        if star_html == "": star_html = "<span style='color:#a0b0c0'>Sem estrelas</span>"

        st.markdown(f"""
        <div class="metric-card">
            <h4>⭐ Estrelas de Leitura</h4>
            <div class="star-container">{star_html}</div>
            <p style="font-size: 0.8em; margin-top: 5px;">Total Páginas: {total_pages}</p>
        </div>
        """, unsafe_allow_html=True)

    # --- DEFINIÇÃO DE ABAS (Dinâmico) ---
    if user == ADMIN_USER:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Diário & Árvore", "📈 Análise e Dashboard", "🏆 Ranking Global", "📢 Alertas do Mentor", "🛡️ Moderação"])
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Diário & Árvore", "📈 Análise e Dashboard", "🏆 Ranking Global", "📢 Alertas do Mentor"])

    # --- ABA 1: DIÁRIO ---
    with tab1:
        col_tree, col_form = st.columns([1, 1])

        with col_tree:
            st.subheader("Árvore da Constância")
            st.markdown(f'<div class="tree-container">{generate_tree_svg(user_data["tree_branches"])}</div>', unsafe_allow_html=True)
            
            # --- RECADO DO MODERADOR (Individual) ---
            if user_data.get('mod_message'):
                st.markdown(f"""
                <div class="mod-message">
                    <strong>📨 Recado do Mentor (Individual):</strong><br>
                    {user_data['mod_message']}
                </div>
                """, unsafe_allow_html=True)

        with col_form:
            st.subheader("📝 Registro de Batalha")
            with st.form("daily_log"):
                date_log = st.date_input("Data da Batalha", value=date.today(), format="DD/MM/YYYY")
                
                c1, c2 = st.columns(2)
                with c1:
                    wake_time = st.text_input("Acordou às (Ex: 08:02)", value="06:00")
                    pages = st.number_input("Páginas Lidas", min_value=0, step=1)
                    workout_sets = st.number_input("Séries Musculação", min_value=0, step=1)
                with c2:
                    sleep_time = st.text_input("Dormiu às (Ex: 22:30)", value="22:30")
                    questions = st.number_input("Questões Feitas", min_value=0, step=1)
                
                st.divider()
                st.markdown("##### 📚 Detalhes de Estudo")
                
                default_subjects = pd.DataFrame([{"Matéria": "", "Tempo": ""}])
                edited_subjects_df = st.data_editor(
                    default_subjects, 
                    num_rows="dynamic", 
                    use_container_width=True,
                    key="subjects_editor_new"
                )
                
                submitted = st.form_submit_button("💾 Salvar Registro")
                
                if submitted:
                    clean_subjects = []
                    for index, row in edited_subjects_df.iterrows():
                        if row["Matéria"] and str(row["Matéria"]).strip() != "":
                            clean_subjects.append(f"{row['Tempo']} - {row['Matéria']}")
                    
                    is_study_day = (pages > 0) or (questions > 0) or (len(clean_subjects) > 0)
                    date_str = date_log.strftime("%Y-%m-%d")
                    existing_dates = [log['data'] for log in user_data['logs']]
                    
                    if date_str in existing_dates:
                        st.warning("⚠️ Já existe um registro nesta data. Vá em Histórico para editar.")
                    else:
                        entry = {
                            "data": date_str,
                            "acordou": wake_time, 
                            "dormiu": sleep_time, 
                            "paginas": pages,
                            "questoes": questions,
                            "series": workout_sets,
                            "estudou": is_study_day,
                            "materias": clean_subjects
                        }
                        user_data['logs'].append(entry)
                        
                        if is_study_day:
                            user_data['tree_branches'] += 1
                            st.toast("Vitória diária! +1 Ramo.", icon="🌿")
                        else:
                            user_data['tree_branches'] -= 2
                            st.toast("Dia perdido. -2 Ramos.", icon="🪓")
                        
                        save_current_user_data()
                        st.rerun()

    # --- ABA 2: HISTÓRICO E DASHBOARD ---
    with tab2:
        st.header("📊 Inteligência de Dados")
        
        if len(user_data['logs']) > 0:
            filter_opts = ["Total", "Diário", "Semanal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"]
            period = st.selectbox("📅 Selecione o Período de Análise:", filter_opts)
            
            df_all = pd.DataFrame(user_data['logs'])
            if 'data' in df_all.columns:
                df_all['data_obj'] = pd.to_datetime(df_all['data']).dt.date
            
            today = date.today()
            
            if period == "Diário":
                df_filtered = df_all[df_all['data_obj'] == today]
            elif period == "Semanal":
                start_date = today - timedelta(days=7)
                df_filtered = df_all[df_all['data_obj'] >= start_date]
            elif period == "Mensal":
                start_date = today - timedelta(days=30)
                df_filtered = df_all[df_all['data_obj'] >= start_date]
            elif period == "Bimestral":
                start_date = today - timedelta(days=60)
                df_filtered = df_all[df_all['data_obj'] >= start_date]
            elif period == "Trimestral":
                start_date = today - timedelta(days=90)
                df_filtered = df_all[df_all['data_obj'] >= start_date]
            elif period == "Semestral":
                start_date = today - timedelta(days=180)
                df_filtered = df_all[df_all['data_obj'] >= start_date]
            elif period == "Anual":
                start_date = today - timedelta(days=365)
                df_filtered = df_all[df_all['data_obj'] >= start_date]
            else: # Total
                df_filtered = df_all

            if not df_filtered.empty:
                f_quest = df_filtered['questoes'].sum()
                f_pag = df_filtered['paginas'].sum()
                f_ser = df_filtered['series'].sum()
                
                cm1, cm2, cm3 = st.columns(3)
                cm1.metric("Questões no Período", f_quest)
                cm2.metric("Páginas no Período", f_pag)
                cm3.metric("Séries no Período", f_ser)
            
                st.subheader("Gráfico de Tempo por Matéria")
                
                subject_mins = {}
                for idx, row in df_filtered.iterrows():
                    if 'materias' in row and isinstance(row['materias'], list):
                        for item in row['materias']:
                            if '-' in item:
                                parts = item.split('-', 1)
                                time_str = parts[0].strip()
                                subj_name = parts[1].strip()
                                
                                mins = parse_time_str_to_min(time_str)
                                if mins > 0:
                                    subject_mins[subj_name] = subject_mins.get(subj_name, 0) + mins
                
                if subject_mins:
                    labels = list(subject_mins.keys())
                    sizes = list(subject_mins.values())
                    
                    fig, ax = plt.subplots(figsize=(6, 3)) 
                    fig.patch.set_facecolor('#F2F6FA') 
                    ax.set_facecolor('#F2F6FA')
                    
                    colors = ['#FF0033', '#00FF33', '#3366FF', '#FF33FF', '#FFFF33', '#00FFFF', '#FF9933', '#9933FF']
                    
                    wedges, texts, autotexts = ax.pie(
                        sizes, labels=None, autopct='%1.1f%%', 
                        startangle=90, colors=colors[:len(labels)],
                        textprops={'color':"#333333", 'fontsize': 8, 'weight': 'bold'} 
                    )
                    
                    leg = ax.legend(wedges, labels,
                              title="Matérias",
                              loc="center left",
                              bbox_to_anchor=(1, 0, 0.5, 1),
                              frameon=False,
                              labelcolor='#333333', 
                              title_fontsize='small')
                    plt.setp(leg.get_title(), color='#333333') 

                    for text in texts: text.set_color('#333333')
                    for autotext in autotexts: autotext.set_color('#333333')
                    
                    ax.axis('equal') 
                    st.pyplot(fig)
                else:
                    st.info("Sem dados de tempo/matéria para este período.")
            
                st.subheader("📈 Evolução de Questões")
                
                df_line = df_filtered.copy()
                df_line = df_line.sort_values(by='data_obj')
                
                if not df_line.empty:
                    fig_line, ax_line = plt.subplots(figsize=(6, 2)) 
                    fig_line.patch.set_facecolor('#F2F6FA') 
                    ax_line.set_facecolor('#F2F6FA')
                    
                    df_line_grouped = df_line.groupby('data_obj')['questoes'].sum().reset_index()
                    
                    ax_line.plot(df_line_grouped['data_obj'], df_line_grouped['questoes'], 
                                 marker='o', linestyle='-', color='#0044FF', 
                                 linewidth=2, markersize=6, markerfacecolor='#FF0000') 
                    
                    ax_line.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                    ax_line.tick_params(axis='x', colors='#333333', rotation=45, labelsize=8)
                    ax_line.tick_params(axis='y', colors='#333333', labelsize=8)
                    
                    ax_line.spines['top'].set_visible(False)
                    ax_line.spines['right'].set_visible(False)
                    ax_line.spines['bottom'].set_color('#333333')
                    ax_line.spines['left'].set_color('#333333')
                    
                    ax_line.grid(color='#333333', linestyle=':', linewidth=0.5, alpha=0.2)
                    
                    fig_line.autofmt_xdate()
                    
                    st.pyplot(fig_line)
                else:
                    st.info("Dados insuficientes para gerar gráfico de evolução.")

            else:
                st.warning("Nenhum registro encontrado para este período.")

            st.divider()
            
            st.subheader("📜 Pergaminho de Registros (Editável - Todos)")
            
            df = pd.DataFrame(user_data['logs'])
            if 'materias' not in df.columns: df['materias'] = [[] for _ in range(len(df))]
            df['materias_str'] = df['materias'].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
            
            if 'data' in df.columns:
                df['data'] = pd.to_datetime(df['data']).dt.date
            
            column_config = {
                "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True),
                "acordou": st.column_config.TextColumn("Acordou"), 
                "dormiu": st.column_config.TextColumn("Dormiu"),   
                "paginas": st.column_config.NumberColumn("Páginas", min_value=0),
                "questoes": st.column_config.NumberColumn("Questões", min_value=0),
                "series": st.column_config.NumberColumn("Séries", min_value=0),
                "estudou": st.column_config.CheckboxColumn("Estudou?"),
                "materias_str": st.column_config.TextColumn("Matérias (Texto)"),
            }
            
            if 'data_obj' not in df.columns:
                 df['data_dt'] = pd.to_datetime(df['data'])
            
            df = df.sort_values(by='data', ascending=False)
            
            edited_df = st.data_editor(
                df[['data', 'acordou', 'dormiu', 'paginas', 'questoes', 'series', 'estudou', 'materias_str']],
                column_config=column_config,
                use_container_width=True,
                num_rows="dynamic",
                key="history_editor"
            )
            
            if st.button("💾 Salvar Alterações na Tabela"):
                new_logs = []
                for index, row in edited_df.iterrows():
                    mat_str = row['materias_str']
                    mat_list = [m.strip() for m in mat_str.split(',')] if mat_str else []
                    entry = {
                        "data": row['data'],
                        "acordou": str(row['acordou']), 
                        "dormiu": str(row['dormiu']),   
                        "paginas": int(row['paginas']),
                        "questoes": int(row['questoes']),
                        "series": int(row['series']),
                        "estudou": bool(row['estudou']),
                        "materias": mat_list
                    }
                    if isinstance(entry['data'], (date, datetime)):
                        entry['data'] = entry['data'].strftime("%Y-%m-%d")
                    new_logs.append(entry)
                
                branches = 1
                for log in sorted(new_logs, key=lambda x: x['data']):
                    if log['estudou']: branches += 1
                    else: branches -= 2
                
                user_data['logs'] = new_logs
                user_data['tree_branches'] = branches
                save_current_user_data()
                st.success("Registros atualizados!")
                time.sleep(1)
                st.rerun()
        else:
            st.warning("Nenhum registro encontrado.")

    # --- ABA 3: RANKING GLOBAL (COMUNIDADE) ---
    with tab3:
        st.header("🏆 Hall da Fama Espartano")
        st.caption("Classificação baseada no total de Questões.")
        
        all_db = load_db()
        community_data = []
        
        for u_name, u_data in all_db.items():
            # IGNORAR A CHAVE DE ALERTAS GLOBAIS
            if u_name == "global_alerts":
                continue
                
            u_logs = u_data.get('logs', [])
            tot_q = sum(l.get('questoes', 0) for l in u_logs)
            tot_p = sum(l.get('paginas', 0) for l in u_logs)
            u_streak = calculate_streak(u_logs)
            patente = get_patent(tot_q)
            
            total_min = 0
            for l in u_logs:
                for m in l.get('materias', []):
                    if '-' in m:
                        total_min += parse_time_str_to_min(m.split('-', 1)[0])
            total_hours = round(total_min / 60, 1)
            
            community_data.append({
                "Espartano": u_name,
                "Patente": patente,
                "Questões": tot_q,
                "Páginas": tot_p,
                "Fogo (Dias)": u_streak,
                "Tempo Total (h)": total_hours
            })
            
        if community_data:
            df_comm = pd.DataFrame(community_data)
            # Ordenar por Questões (Ranking)
            df_comm = df_comm.sort_values(by="Questões", ascending=False).reset_index(drop=True)
            df_comm.index += 1 
            df_comm.index.name = "Rank"
            
            # --- PÓDIO ---
            top_users = df_comm.head(3)
            if not top_users.empty:
                cols = st.columns([1, 1, 1])
                
                # Prata (2º Lugar) - Esquerda
                if len(top_users) >= 2:
                    with cols[0]:
                        u2 = top_users.iloc[1]
                        st.markdown(f"""
                        <div class="podium-silver">
                            <h2>🥈 2º Lugar</h2>
                            <h3>{u2['Espartano']}</h3>
                            <p>{u2['Questões']} Questões</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Ouro (1º Lugar) - Centro
                if len(top_users) >= 1:
                    with cols[1]:
                        u1 = top_users.iloc[0]
                        st.markdown(f"""
                        <div class="podium-gold">
                            <h1>🥇 1º Lugar</h1>
                            <h2>{u1['Espartano']}</h2>
                            <p><strong>{u1['Patente']}</strong></p>
                            <p>{u1['Questões']} Questões</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Bronze (3º Lugar) - Direita
                if len(top_users) >= 3:
                    with cols[2]:
                        u3 = top_users.iloc[2]
                        st.markdown(f"""
                        <div class="podium-bronze">
                            <h2>🥉 3º Lugar</h2>
                            <h3>{u3['Espartano']}</h3>
                            <p>{u3['Questões']} Questões</p>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.divider()
            st.subheader("Classificação Geral")
            
            def highlight_self(row):
                if row['Espartano'] == user:
                    return ['background-color: #5C4033; color: white'] * len(row)
                return [''] * len(row)

            st.dataframe(
                df_comm.style.apply(highlight_self, axis=1), 
                use_container_width=True
            )
        else:
            st.info("Nenhum dado comunitário disponível.")

    # --- ABA 4: ALERTAS DO MENTOR (NOVA) ---
    with tab4:
        st.header("📢 Alertas do Mentor")
        st.caption("Quadro de avisos oficial de Esparta")
        
        db = load_db()
        # Garantir que a lista de alertas existe
        if "global_alerts" not in db:
            db["global_alerts"] = []
            
        # --- INTERFACE DO MENTOR (POSTAR) ---
        if user == ADMIN_USER:
            with st.expander("📝 Escrever Novo Alerta", expanded=True):
                with st.form("new_alert_form"):
                    new_alert_text = st.text_area("Mensagem para todos:", height=100)
                    submit_alert = st.form_submit_button("📢 Publicar Aviso")
                    
                    if submit_alert and new_alert_text.strip():
                        alert_obj = {
                            "id": str(datetime.now().timestamp()),
                            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "text": new_alert_text,
                            "author": user
                        }
                        # Adiciona no início da lista (mais recente primeiro)
                        db["global_alerts"].insert(0, alert_obj)
                        save_db(db)
                        st.success("Alerta publicado com sucesso!")
                        st.rerun()
        
        st.divider()
        
        # --- LISTA DE ALERTAS (PARA TODOS) ---
        alerts = db.get("global_alerts", [])
        
        if not alerts:
            st.info("Nenhum alerta publicado no momento.")
        else:
            for alert in alerts:
                # Container visual do alerta
                st.markdown(f"""
                <div class="mod-message" style="margin-bottom: 20px;">
                    <div style="font-size: 0.8em; color: #D4AF37; margin-bottom: 5px;">
                        📅 {alert.get('date', 'Data desc.')} | 🏛️ MENTOR SUPREMO
                    </div>
                    <div style="font-size: 1.1em; white-space: pre-wrap;">
                        {alert.get('text', '')}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Botão de apagar (apenas para o Mentor)
                if user == ADMIN_USER:
                    if st.button(f"🗑️ Apagar Alerta de {alert.get('date')}", key=alert.get('id')):
                        db["global_alerts"].remove(alert)
                        save_db(db)
                        st.rerun()

    # --- ABA 5: MODERAÇÃO (NOVA E EXCLUSIVA) ---
    if user == ADMIN_USER:
        with tab5:
            st.header("🛡️ Central de Comando - Moderação")
            st.markdown("---")
            
            col_add, col_del = st.columns(2)
            
            # --- INCLUIR USUÁRIO ---
            with col_add:
                st.subheader("✨ Incluir Novo Espartano")
                with st.form("create_user_form"):
                    new_u = st.text_input("Nome do Usuário")
                    new_p = st.text_input("Senha", type="password")
                    submit_create = st.form_submit_button("Criar Conta")
                    
                    if submit_create:
                        db = load_db()
                        if new_u and new_p:
                            if new_u not in db:
                                db[new_u] = {
                                    "password": new_p,
                                    "logs": [],
                                    "tree_branches": 1,
                                    "created_at": str(datetime.now()),
                                    "mod_message": ""
                                }
                                save_db(db)
                                st.success(f"Usuário '{new_u}' recrutado com sucesso!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("Este nome de usuário já existe.")
                        else:
                            st.warning("Preencha nome e senha.")

            # --- EXCLUIR USUÁRIO ---
            with col_del:
                st.subheader("💀 Excluir Espartano")
                db = load_db()
                # Filter users, excluding admin and global_alerts
                users_list = [u for u in db.keys() if u != "global_alerts" and u != ADMIN_USER]
                
                if users_list:
                    target_del = st.selectbox("Selecione o usuário para banir:", users_list)
                    st.warning(f"Atenção: A exclusão de **{target_del}** é irreversível.")
                    
                    if st.button("Confirmar Exclusão 🗑️"):
                        if target_del in db:
                            del db[target_del]
                            save_db(db)
                            st.success(f"Usuário '{target_del}' foi banido de Esparta.")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.info("Não há outros usuários para excluir.")

# --- CONTROLE DE FLUXO LOGIN ---
if 'user' not in st.session_state:
    login_page()
else:
    main_app()
