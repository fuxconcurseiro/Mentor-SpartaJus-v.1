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
import shutil
import calendar

# Tenta importar bibliotecas do Google Sheets. Se falhar, roda em modo offline.
try:
    import gspread
    from google.oauth2.service_account import Credentials
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False

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
ADMIN_USER = "fux_concurseiro" 
SHEET_NAME = "SpartaJus_DB" 

# --- GERENCIAMENTO DE API KEY (IA) ---
ENCRYPTED_KEY_LOCAL = "QUl6YVN5RFI1VTdHeHNCZVVVTFE5M1N3UG9VNl9CaGl3VHZzMU9n"

def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    try:
        return base64.b64decode(ENCRYPTED_KEY_LOCAL).decode("utf-8")
    except Exception:
        return ""

# --- FUNÇÕES DE GOOGLE SHEETS (PERSISTÊNCIA NA NUVEM) ---

def get_google_credentials():
    """Tenta obter credenciais do st.secrets para o Google Sheets."""
    if "gcp_service_account" in st.secrets:
        return st.secrets["gcp_service_account"]
    return None

def connect_to_sheets():
    """Conecta ao Google Sheets usando gspread."""
    if not SHEETS_AVAILABLE:
        return None
    
    creds_dict = get_google_credentials()
    if not creds_dict:
        return None

    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Erro ao conectar Google Sheets: {e}")
        return None

def sync_down_from_sheets():
    """Baixa os dados da planilha e atualiza o JSON local."""
    client = connect_to_sheets()
    if not client: return False 

    try:
        sheet = client.open(SHEET_NAME).sheet1
        records = sheet.get_all_values()
        
        cloud_db = {}
        for row in records:
            if len(row) >= 2:
                key = row[0]
                try:
                    value = json.loads(row[1])
                    cloud_db[key] = value
                except:
                    pass 
        
        if cloud_db:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(cloud_db, f, indent=4, default=str)
            return True
            
    except Exception as e:
        print(f"Erro ao baixar do Sheets: {e}")
        return False

def sync_up_to_sheets(db_data):
    """Envia os dados locais para a planilha."""
    client = connect_to_sheets()
    if not client: return False

    try:
        sheet = client.open(SHEET_NAME).sheet1
        rows_to_update = []
        for key, value in db_data.items():
            json_str = json.dumps(value, default=str)
            rows_to_update.append([key, json_str])
        
        sheet.clear()
        sheet.update('A1', rows_to_update)
        return True
    except Exception as e:
        print(f"Erro ao subir para Sheets: {e}")
        return False

# --- FUNÇÕES DE PERSISTÊNCIA LOCAL ---
def load_db():
    if "db_synced" not in st.session_state:
        success = sync_down_from_sheets()
        if success:
            st.session_state["db_synced"] = True
    
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: return {} 
            return json.loads(content)
    except json.JSONDecodeError:
        return {}

def save_db(db_data):
    # 1. Salva Local
    temp_file = f"{DB_FILE}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=4, default=str)
            f.flush()
            os.fsync(f.fileno()) 
        os.replace(temp_file, DB_FILE)
    except Exception as e:
        st.error(f"Erro salvamento local: {e}")
    
    # 2. Salva na Nuvem
    try:
        sync_up_to_sheets(db_data)
    except:
        pass 

# --- AUTO-CRIAÇÃO E PROTEÇÃO DE USUÁRIOS ---
def ensure_users_exist():
    db = load_db()
    data_changed = False
    vip_users = {
        "fux_concurseiro": "Senha128",
        "steissy": "Mudar123",
        "JuOlebar": "Mudar123"
    }
    for user, default_pass in vip_users.items():
        if user not in db:
            db[user] = {
                "password": default_pass,
                "logs": [],
                "agendas": {},
                "tree_branches": 1,
                "created_at": str(datetime.now()),
                "mod_message": ""
            }
            data_changed = True
    if data_changed:
        save_db(db)

ensure_users_exist()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    /* Elementos que queremos esconder totalmente */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {visibility: hidden;}
    
    /* Barra de ferramentas (menu de 3 pontos) - Opcional: comente se quiser ver */
    [data-testid="stToolbar"] {visibility: hidden;}
    
    /* HEADER: Deixamos transparente para nao bloquear a visao, mas VISIVEL para que os botoes funcionem */
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
        visibility: visible;
    }

    /* BOTÃO DA SIDEBAR (CHEVRON): Forçamos a visibilidade e estilizamos */
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        display: block !important;
        color: #D4AF37 !important; /* Dourado */
        background-color: rgba(74, 90, 106, 0.3); /* Fundo sutil para garantir contraste */
        border-radius: 5px;
        z-index: 100000; /* Garante que fique acima de tudo */
    }
    
    /* Estilos Gerais do App */
    .stApp { background-color: #708090; color: #C2D5ED; }
    .stMarkdown, .stText, p, label, .stDataFrame, .stExpander { color: #C2D5ED !important; }
    
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input, 
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea > div > div > textarea {
        background-color: #4a5a6a; color: #C2D5ED; border-color: #C4A484;
    }
    ::placeholder { color: #a0b0c0 !important; opacity: 0.7; }
    
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #C2D5ED !important; font-family: 'Helvetica Neue', sans-serif; text-shadow: 1px 1px 2px black;
    }
    
    [data-testid="stSidebar"] { background-color: #586878; border-right: 2px solid #C4A484; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #C2D5ED !important; }
    
    .stButton>button {
        background-color: #4a5a6a; color: #C2D5ED; border: 1px solid #D4AF37; 
        border-radius: 4px; height: 3em; font-weight: bold; transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #D4AF37; color: #2c3e50; border-color: #C2D5ED;
    }
    
    .metric-card { background-color: #586878; padding: 15px; border-radius: 8px; border: 1px solid #C4A484; }
    .metric-card h4, .metric-card p { color: #C2D5ED !important; }
    
    .rank-card {
        background: linear-gradient(90deg, #3e4e5e, #586878); color: #C2D5ED;
        padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px;
        border: 2px solid #D4AF37; box-shadow: 0 0 15px rgba(212, 175, 55, 0.2);
    }
    
    .mod-message {
        background-color: #2c3e50; border-left: 5px solid #D4AF37;
        border: 1px solid #D4AF37; padding: 15px; margin-top: 15px;
        border-radius: 8px; color: #C2D5ED; box-shadow: 0 4px 10px rgba(0,0,0,0.5);
    }
    .private-message {
        background-color: #3e2723; border: 2px dashed #D4AF37;
        padding: 15px; margin-bottom: 20px; border-radius: 8px; color: #C2D5ED;
    }

    .podium-gold { background: linear-gradient(180deg, #D4AF37 0%, #B8860B 100%); color: #000 !important; padding: 20px; border-radius: 10px; text-align: center; border: 2px solid #FFD700; transform: scale(1.05); }
    .podium-silver { background: linear-gradient(180deg, #C0C0C0 0%, #A9A9A9 100%); color: #000 !important; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #D3D3D3; margin-top: 15px; }
    .podium-bronze { background: linear-gradient(180deg, #CD7F32 0%, #8B4513 100%); color: #fff !important; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #A0522D; margin-top: 25px; }
    .podium-gold p, .podium-silver p, .podium-bronze p, .podium-gold h*, .podium-silver h*, .podium-bronze h* { color: inherit !important; text-shadow: none; }
    
    [data-testid="stDataFrame"] { border: 1px solid #C4A484; background-color: #4a5a6a; }
    
    .tree-container {
        display: flex; justify-content: center; align-items: center; margin-top: 20px;
        background-color: #4a5a6a; border-radius: 100%; width: 350px; height: 350px;
        margin-left: auto; margin-right: auto; border: 4px solid #C4A484; overflow: hidden; 
    }
    
    .stToast { background-color: #586878 !important; color: #C2D5ED !important; }
    .stAlert { background-color: #4a5a6a; color: #C2D5ED; border: 1px solid #C4A484; }
    
    .stImage { display: flex; justify-content: center; }
    .stImage img { width: 100%; mix-blend-mode: multiply; border-radius: 10px; }
    
    /* CALENDÁRIO */
    .cal-day {
        background-color: #4a5a6a; border: 1px solid #586878; 
        border-radius: 4px; padding: 10px; text-align: center; margin: 2px;
        min-height: 60px; display: flex; flex-direction: column; justify-content: center;
    }
    .cal-day.planned { border: 2px solid #047a0a; background-color: #1b3a2b; }
    .cal-day.empty { opacity: 0.5; }
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
                mins = int(rest.split('m')[0]) if rest.split('m')[0].isdigit() else (int(rest) if rest.isdigit() else 0)
            return hours * 60 + mins
        elif 'm' in t_str: return int(t_str.split('m')[0])
        elif ':' in t_str:
            h, m = t_str.split(':')
            return int(h)*60 + int(m)
        elif t_str.isdigit(): return int(t_str)
    except: pass
    return 0

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
    trunk_h = min(30 + (branches * 0.5), 60)
    trunk_y = 100 - trunk_h
    count = min(max(1, branches), 150)
    
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
    patentes = ["Andarilho de Vade Mecum", "Saco de Pancada da Banca", "Cadastro de Reserva", "Titã Nota de Corte", "Espartano Jurídico"]
    return patentes[min(int(total_questions / 5000), 4)]

def get_stars(total_pages):
    raw_bronze = int(total_pages / 1000)
    gold = raw_bronze // 9
    if gold >= 3: return 3, 0, 0
    rem = raw_bronze % 9
    return gold, rem // 3, rem % 3

def calculate_streak(logs):
    if not logs: return 0
    study_dates = sorted([log['data'] for log in logs if log.get('estudou')], reverse=True)
    if not study_dates: return 0
    streak = 0
    current_check = datetime.strptime(study_dates[0], "%Y-%m-%d").date()
    if (date.today() - current_check).days > 1: return 0
    for d_str in study_dates:
        d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        if d_obj == current_check:
            streak += 1
            current_check -= timedelta(days=1)
        elif d_obj < current_check: break
    return streak

# --- AUTH SYSTEM ---
def login_page():
    c1, c2, c3 = st.columns([1, 2, 1]) 
    if os.path.exists(LOGO_FILE):
        with c2: st.image(LOGO_FILE)
    st.title("🏛️ Mentor SpartaJus - Login")
    st.markdown("### Bem-vindo ao Campo de Batalha do Conhecimento")
    
    tab1, tab2, tab3 = st.tabs(["🔑 Entrar", "📝 Registrar", "🔄 Alterar Senha"])
    
    with tab1:
        st.subheader("Acessar o Sistema")
        username = st.text_input("Usuário", key="login_user").strip() 
        password = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Login", key="btn_login"):
            db = load_db()
            if username in db and db[username]['password'] == password:
                st.session_state['user'] = username
                st.session_state['user_data'] = db[username]
                if 'admin_user' in st.session_state: del st.session_state['admin_user']
                st.rerun()
            else: st.error("Usuário ou senha incorretos.")

    with tab2:
        st.subheader("Novo Recruta")
        new_user = st.text_input("Novo Usuário", key="reg_user").strip()
        new_pass = st.text_input("Nova Senha", type="password", key="reg_pass")
        if st.button("Criar Conta", key="btn_reg"):
            db = load_db()
            if new_user in db: st.error("Usuário já existe.")
            elif new_user and new_pass:
                db[new_user] = {"password": new_pass, "logs": [], "agendas": {}, "tree_branches": 1, "created_at": str(datetime.now()), "mod_message": ""}
                save_db(db)
                st.success("Conta criada! Faça login na aba 'Entrar'.")
            else: st.warning("Preencha todos os campos.")

    with tab3:
        st.subheader("Atualizar Credenciais")
        with st.form("change_pass_form"):
            cp_user = st.text_input("Usuário").strip()
            cp_old_pass = st.text_input("Senha Atual", type="password")
            cp_new_pass = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Salvar Nova Senha"):
                db = load_db()
                if cp_user in db and db[cp_user]['password'] == cp_old_pass:
                    db[cp_user]['password'] = cp_new_pass
                    save_db(db)
                    st.success("Senha alterada com sucesso!")
                else: st.error("Dados incorretos.")

def save_current_user_data():
    if 'user' in st.session_state and 'user_data' in st.session_state:
        db = load_db()
        db[st.session_state['user']] = st.session_state['user_data']
        save_db(db)

# --- APP PRINCIPAL ---
def main_app():
    user = st.session_state['user']
    user_data = st.session_state['user_data']
    is_real_admin = (user == ADMIN_USER)
    is_admin_mode = ('admin_user' in st.session_state and st.session_state['admin_user'] == ADMIN_USER)

    if 'logs' not in user_data: user_data['logs'] = []
    if 'agendas' not in user_data: user_data['agendas'] = {} # Garante campo de agendas
    if 'tree_branches' not in user_data: user_data['tree_branches'] = 1
    if 'mod_message' not in user_data: user_data['mod_message'] = "" 

    st.session_state.api_key = get_api_key()
    
    total_questions = sum([log.get('questoes', 0) for log in user_data['logs']])
    total_pages = sum([log.get('paginas', 0) for log in user_data['logs']])
    streak = calculate_streak(user_data['logs'])
    current_patent = get_patent(total_questions)
    g_stars, s_stars, b_stars = get_stars(total_pages)

    with st.sidebar:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE)
        
        # STATUS DO GOOGLE SHEETS
        if SHEETS_AVAILABLE and get_google_credentials():
            st.caption("🟢 Conectado à Nuvem (Google Sheets)")
        else:
            st.caption("🟠 Modo Offline (Local JSON)")
            
        if is_real_admin or is_admin_mode:
            with st.expander("🛡️ PAINEL DO MODERADOR", expanded=True):
                st.caption("Área restrita de comando")
                if is_real_admin:
                    db = load_db()
                    all_users = [k for k in db.keys() if k != "global_alerts"]
                    target_user = st.selectbox("Selecione o Espartano:", all_users)
                    if st.button("👁️ Acessar Dashboard Selecionado"):
                        st.session_state['admin_user'] = ADMIN_USER
                        st.session_state['user'] = target_user
                        st.session_state['user_data'] = db[target_user]
                        st.rerun()
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
        st.markdown("### 💾 Backup de Segurança")
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                st.download_button("Baixar Dados (JSON)", f, f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json", "application/json")
        else: st.info("Sem dados.")
        st.info("Versão: SpartaJus Clean Edition")

    st.title("🏛️ Mentor SpartaJus")
    
    progress_val = total_questions % 5000
    percent_val = (progress_val / 5000) * 100
    remaining = 5000 - progress_val
    st.markdown(f"""
    <div style="background-color: #4a5a6a; border-radius: 12px; padding: 4px; margin-bottom: 10px; border: 1px solid #D4AF37; box-shadow: 0 2px 5px rgba(0,0,0,0.3);">
        <div style="width: {percent_val}%; background-color: #047a0a; height: 24px; border-radius: 8px; text-align: center; line-height: 24px; color: white; font-weight: bold; font-size: 0.9em; white-space: nowrap; overflow: visible; transition: width 0.8s;">&nbsp;{percent_val:.1f}%</div>
    </div>
    <div style="display: flex; justify-content: space-between; font-size: 0.85em; color: #C2D5ED; margin-top: -8px; margin-bottom: 20px;"><span>⚔️ Atual: {progress_val} questões</span><span>🎯 Próxima Patente: Falta {remaining}</span></div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([2, 1])
    with c1: st.markdown(f"<div class='rank-card'><h2>{user.upper()}</h2><h3>🛡️ Patente: {current_patent}</h3><p>Total: {total_questions} | 🔥 Fogo: {streak} dias</p></div>", unsafe_allow_html=True)
    with c2: 
        star_html = "".join(["🟡"]*g_stars + ["⚪"]*s_stars + ["🟤"]*b_stars) or "<span style='color:#a0b0c0'>Sem estrelas</span>"
        st.markdown(f"<div class='metric-card'><h4>⭐ Estrelas de Leitura</h4><div class='star-container'>{star_html}</div><p style='font-size: 0.8em; margin-top: 5px;'>Total Páginas: {total_pages}</p></div>", unsafe_allow_html=True)

    tabs = ["📊 Diário & Árvore", "📈 Análise e Dashboard", "🏆 Ranking Global", "📢 Alertas do Mentor", "📅 Agenda de Guerra", "🤖 Oráculo IA"]
    if user == ADMIN_USER: tabs.append("🛡️ Moderação")
    current_tabs = st.tabs(tabs)

    # ABA 1
    with current_tabs[0]:
        col_tree, col_form = st.columns([1, 1])
        with col_tree:
            st.subheader("Árvore da Constância")
            st.markdown(f'<div class="tree-container">{generate_tree_svg(user_data["tree_branches"])}</div>', unsafe_allow_html=True)
            if user_data.get('mod_message'):
                st.markdown(f"<div class='private-message'><strong>📨 MENSAGEM DO MENTOR:</strong><br>{user_data['mod_message']}</div>", unsafe_allow_html=True)
        with col_form:
            st.subheader("📝 Registro de Batalha")
            with st.form("daily_log"):
                date_log = st.date_input("Data da Batalha", value=date.today(), format="DD/MM/YYYY")
                cc1, cc2 = st.columns(2)
                with cc1: 
                    wt = st.text_input("Acordou (Ex: 08:00)", value="06:00")
                    pg = st.number_input("Páginas", min_value=0, step=1)
                    ws = st.number_input("Séries", min_value=0, step=1)
                with cc2:
                    sl = st.text_input("Dormiu (Ex: 22:00)", value="22:30")
                    qs = st.number_input("Questões", min_value=0, step=1)
                st.divider()
                st.markdown("##### 📚 Matérias")
                sub_df = st.data_editor(pd.DataFrame([{"Matéria": "", "Tempo": ""}]), num_rows="dynamic", use_container_width=True)
                if st.form_submit_button("💾 Salvar"):
                    clean_subs = [f"{r['Tempo']} - {r['Matéria']}" for _, r in sub_df.iterrows() if r["Matéria"]]
                    is_study = (pg > 0) or (qs > 0) or (len(clean_subs) > 0)
                    d_str = d_log.strftime("%Y-%m-%d")
                    if d_str in [l['data'] for l in user_data['logs']]:
                        st.warning("Data já registrada. Edite no Histórico.")
                    else:
                        user_data['logs'].append({"data": d_str, "acordou": wt, "dormiu": sl, "paginas": pg, "questoes": qs, "series": ws, "estudou": is_study, "materias": clean_subs})
                        if is_study: 
                            user_data['tree_branches'] += 1
                            st.toast("Vitória! +1 Ramo.", icon="🌿")
                        else:
                            user_data['tree_branches'] -= 2
                            st.toast("Dia perdido. -2 Ramos.", icon="🪓")
                        save_current_user_data()
                        st.rerun()

    # ABA 2
    with current_tabs[1]:
        st.header("📊 Inteligência de Dados")
        if len(user_data['logs']) > 0:
            period = st.selectbox("📅 Período:", ["Total", "Diário", "Semanal", "Mensal", "Bimestral", "Trimestral", "Semestral", "Anual"])
            df_all = pd.DataFrame(user_data['logs'])
            if 'data' in df_all.columns: df_all['data_obj'] = pd.to_datetime(df_all['data']).dt.date
            today = date.today()
            
            if period == "Diário": df_f = df_all[df_all['data_obj'] == today]
            elif period == "Semanal": df_f = df_all[df_all['data_obj'] >= today - timedelta(days=7)]
            elif period == "Mensal": df_f = df_all[df_all['data_obj'] >= today - timedelta(days=30)]
            elif period == "Bimestral": df_f = df_all[df_all['data_obj'] >= today - timedelta(days=60)]
            elif period == "Trimestral": df_f = df_all[df_all['data_obj'] >= today - timedelta(days=90)]
            elif period == "Semestral": df_f = df_all[df_all['data_obj'] >= today - timedelta(days=180)]
            elif period == "Anual": df_f = df_all[df_all['data_obj'] >= today - timedelta(days=365)]
            else: df_f = df_all

            if not df_f.empty:
                m1, m2, m3 = st.columns(3)
                m1.metric("Questões", df_f['questoes'].sum())
                m2.metric("Páginas", df_f['paginas'].sum())
                m3.metric("Séries", df_f['series'].sum())
                
                st.subheader("Tempo por Matéria")
                sub_mins = {}
                for _, r in df_f.iterrows():
                    if 'materias' in r and isinstance(r['materias'], list):
                        for item in r['materias']:
                            if '-' in item:
                                p = item.split('-', 1)
                                sub_mins[p[1].strip()] = sub_mins.get(p[1].strip(), 0) + parse_time_str_to_min(p[0].strip())
                
                if sub_mins:
                    fig, ax = plt.subplots(figsize=(6, 3))
                    fig.patch.set_facecolor('#F2F6FA')
                    ax.set_facecolor('#F2F6FA')
                    colors = ['#FF0033', '#00FF33', '#3366FF', '#FF33FF', '#FFFF33', '#00FFFF', '#FF9933', '#9933FF']
                    w, t, at = ax.pie(sub_mins.values(), labels=None, autopct='%1.1f%%', startangle=90, colors=colors[:len(sub_mins)], textprops={'color':"#333333", 'fontsize': 8, 'weight': 'bold'})
                    ax.legend(w, sub_mins.keys(), title="Matérias", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), frameon=False, labelcolor='#333333')
                    st.pyplot(fig)
                
                st.subheader("📈 Evolução de Questões")
                df_l = df_f.sort_values(by='data_obj')
                if not df_l.empty:
                    fig_l, ax_l = plt.subplots(figsize=(6, 2))
                    fig_l.patch.set_facecolor('#F2F6FA')
                    ax_l.set_facecolor('#F2F6FA')
                    grp = df_l.groupby('data_obj')['questoes'].sum().reset_index()
                    ax_l.plot(grp['data_obj'], grp['questoes'], marker='o', color='#0044FF', linewidth=2, markerfacecolor='#FF0000')
                    ax_l.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                    ax_l.tick_params(colors='#333333', rotation=45, labelsize=8)
                    for spine in ax_l.spines.values(): spine.set_edgecolor('#333333')
                    ax_l.grid(color='#333333', linestyle=':', alpha=0.2)
                    st.pyplot(fig_l)
            else: st.warning("Sem dados para o período.")
            
            st.divider()
            st.subheader("📜 Histórico Editável")
            df_e = df_all.copy().sort_values(by='data_obj', ascending=False)
            df_e['materias_str'] = df_e['materias'].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
            df_e['data'] = pd.to_datetime(df_e['data']).dt.date
            
            edited = st.data_editor(
                df_e[['data', 'acordou', 'dormiu', 'paginas', 'questoes', 'series', 'estudou', 'materias_str']],
                use_container_width=True, num_rows="dynamic", key="hist_ed",
                column_config={
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "acordou": st.column_config.TextColumn("Acordou"),
                    "dormiu": st.column_config.TextColumn("Dormiu"),
                    "paginas": st.column_config.NumberColumn("Páginas"),
                    "questoes": st.column_config.NumberColumn("Questões"),
                    "series": st.column_config.NumberColumn("Séries"),
                    "estudou": st.column_config.CheckboxColumn("Estudou?"),
                    "materias_str": st.column_config.TextColumn("Matérias")
                }
            )
            
            if st.button("💾 Salvar Alterações"):
                nl = []
                for _, r in edited.iterrows():
                    ms = r['materias_str']
                    ml = [m.strip() for m in ms.split(',')] if ms else []
                    try: pv = int(r['paginas']) if pd.notnull(r['paginas']) else 0
                    except: pv = 0
                    try: qv = int(r['questoes']) if pd.notnull(r['questoes']) else 0
                    except: qv = 0
                    try: sv = int(r['series']) if pd.notnull(r['series']) else 0
                    except: sv = 0
                    
                    d_val = r['data']
                    if isinstance(d_val, (date, datetime)): d_val = d_val.strftime("%Y-%m-%d")
                    
                    nl.append({"data": d_val, "acordou": str(r['acordou']), "dormiu": str(r['dormiu']), "paginas": pv, "questoes": qv, "series": sv, "estudou": bool(r['estudou']), "materias": ml})
                
                br = 1
                for l in sorted(nl, key=lambda x: x['data']):
                    if l['estudou']: br += 1
                    else: br -= 2
                user_data['logs'] = nl
                user_data['tree_branches'] = br
                save_current_user_data()
                st.success("Atualizado!")
                time.sleep(1)
                st.rerun()
        else: st.info("Sem registros.")

    # ABA 3
    with current_tabs[2]:
        st.header("🏆 Hall da Fama")
        db = load_db()
        c_data = []
        for u, d in db.items():
            if u == "global_alerts": continue
            qs = sum(l.get('questoes', 0) for l in d.get('logs', []))
            pg = sum(l.get('paginas', 0) for l in d.get('logs', []))
            stk = calculate_streak(d.get('logs', []))
            tm = 0
            for l in d.get('logs', []):
                for m in l.get('materias', []):
                    if '-' in m: tm += parse_time_str_to_min(m.split('-', 1)[0])
            c_data.append({"Espartano": u, "Patente": get_patent(qs), "Questões": qs, "Páginas": pg, "Fogo": stk, "Horas": round(tm/60, 1)})
        
        if c_data:
            cdf = pd.DataFrame(c_data).sort_values(by="Questões", ascending=False).reset_index(drop=True)
            cdf.index += 1
            
            top = cdf.head(3)
            if not top.empty:
                c = st.columns(3)
                if len(top) >= 2: c[0].markdown(f"<div class='podium-silver'><h2>🥈</h2><h3>{top.iloc[1]['Espartano']}</h3><p>{top.iloc[1]['Questões']} Questões</p></div>", unsafe_allow_html=True)
                if len(top) >= 1: c[1].markdown(f"<div class='podium-gold'><h1>🥇</h1><h2>{top.iloc[0]['Espartano']}</h2><p>{top.iloc[0]['Questões']} Questões</p></div>", unsafe_allow_html=True)
                if len(top) >= 3: c[2].markdown(f"<div class='podium-bronze'><h2>🥉</h2><h3>{top.iloc[2]['Espartano']}</h3><p>{top.iloc[2]['Questões']} Questões</p></div>", unsafe_allow_html=True)
            
            st.divider()
            st.dataframe(cdf.style.apply(lambda r: ['background-color: #5C4033; color: white']*len(r) if r['Espartano']==user else ['']*len(r), axis=1), use_container_width=True)
        else:
            st.info("Nenhum dado comunitário disponível.")

    # ABA 4
    with current_tabs[3]:
        st.header("📢 Alertas do Mentor")
        db = load_db()
        if "global_alerts" not in db: db["global_alerts"] = []
        
        c_gl, c_pr = st.columns([1, 1])
        
        with c_gl:
            st.subheader("🌍 Mural Global")
            if user == ADMIN_USER:
                with st.expander("Novo Alerta"):
                    nat = st.text_area("Texto:")
                    if st.button("Publicar"):
                        db["global_alerts"].insert(0, {"id": str(time.time()), "date": datetime.now().strftime("%d/%m %H:%M"), "text": nat, "author": user})
                        save_db(db)
                        st.rerun()
            
            alts = db.get("global_alerts", [])
            if not alts: st.info("Vazio.")
            else:
                for a in alts:
                    st.markdown(f"<div class='mod-message'><div style='font-size:0.7em; color:#D4AF37;'>{a['date']}</div><div>{a['text']}</div></div>", unsafe_allow_html=True)
                    if user == ADMIN_USER and st.button("🗑️", key=a['id']):
                        db["global_alerts"].remove(a)
                        save_db(db)
                        st.rerun()

        with c_pr:
            st.subheader("📨 Mensagens Privadas")
            if user == ADMIN_USER:
                st.markdown("**Enviar/Gerenciar**")
                usrs = [k for k in db.keys() if k not in ["global_alerts", ADMIN_USER]]
                tgt = st.selectbox("Para:", usrs, key="mt")
                if tgt:
                    curr = db[tgt].get('mod_message', '')
                    if curr: st.warning(f"Atual: {curr}")
                    new_m = st.text_area("Msg:")
                    if st.button("Enviar"):
                        db[tgt]['mod_message'] = new_m
                        save_db(db)
                        st.success("Enviado!")
                    
                    if curr and st.button("Apagar Msg Atual"):
                        db[tgt]['mod_message'] = ""
                        save_db(db)
                        st.rerun()
            else:
                mm = user_data.get('mod_message', '')
                if mm: st.markdown(f"<div class='private-message'><h3>⚠️ MENSAGEM</h3>{mm}</div>", unsafe_allow_html=True)
                else: st.info("Sem mensagens novas.")

    # ABA 5: AGENDA DE GUERRA
    with current_tabs[4]:
        st.header("📅 Agenda & Metas")
        
        c_plan, c_stats = st.columns([2, 1])
        
        with c_plan:
            st.subheader("Plano de Batalha")
            
            # Seletor de Data com formato DD/MM/YYYY
            plan_date = st.date_input("Para qual dia você está planejando?", value=date.today() + timedelta(days=1), format="DD/MM/YYYY")
            plan_key = plan_date.strftime("%Y-%m-%d")
            
            current_plan = user_data['agendas'].get(plan_key, "")
            
            new_plan_text = st.text_area("Objetivos e Estratégia:", value=current_plan, height=200, placeholder="Ex. Fazer 2 cadernos do TEC de Constitucional e 1 de Penal.")
            
            if st.button("💾 Salvar Planejamento"):
                if new_plan_text.strip():
                    user_data['agendas'][plan_key] = new_plan_text
                    st.success(f"Agenda para {plan_date.strftime('%d/%m')} salva com honra!")
                else:
                    if plan_key in user_data['agendas']:
                        del user_data['agendas'][plan_key]
                        st.info("Planejamento removido.")
                save_current_user_data()
                st.rerun()

        with c_stats:
            st.subheader("Disciplina Mensal")
            
            today = date.today()
            current_month = today.month
            current_year = today.year
            
            num_days = calendar.monthrange(current_year, current_month)[1]
            days_planned = 0
            
            st.markdown(f"**{calendar.month_name[current_month]} {current_year}**")
            
            cols = st.columns(7)
            days_abbrev = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            for i, d_name in enumerate(days_abbrev):
                cols[i].markdown(f"<div style='text-align:center; font-size:0.8em; color:#a0b0c0;'>{d_name}</div>", unsafe_allow_html=True)
            
            month_start_weekday = date(current_year, current_month, 1).weekday()
            cal_html_grid = []
            for _ in range(month_start_weekday):
                cal_html_grid.append(f"<div class='cal-day empty'></div>")
            
            for d in range(1, num_days + 1):
                d_str = date(current_year, current_month, d).strftime("%Y-%m-%d")
                has_plan = d_str in user_data['agendas'] and user_data['agendas'][d_str].strip() != ""
                
                if has_plan:
                    days_planned += 1
                    style_class = "cal-day planned"
                    icon = "✅"
                else:
                    style_class = "cal-day"
                    icon = ""
                
                cal_html_grid.append(f"<div class='{style_class}'>{d}<br>{icon}</div>")
            
            for i in range(0, len(cal_html_grid), 7):
                row_cols = st.columns(7)
                for j in range(7):
                    if i + j < len(cal_html_grid):
                        row_cols[j].markdown(cal_html_grid[i+j], unsafe_allow_html=True)
            
            st.divider()
            st.metric("Dias Planejados", f"{days_planned} / {num_days}")
            if days_planned == 0:
                st.warning("Ainda sem planos este mês. Comece agora!")
            elif days_planned == num_days:
                st.balloons()
                st.success("Disciplina Perfeita! Um verdadeiro Espartano!")

    # ABA 6 (Oráculo)
    with current_tabs[5]:
        st.subheader("🤖 Oráculo SpartaJus")
        if not st.session_state.api_key: st.warning("Chave API não configurada.")
        else:
            if 'chat_history' not in st.session_state: st.session_state.chat_history = []
            for m in st.session_state.chat_history:
                with st.chat_message(m["role"]): st.write(m["content"])
            
            if p := st.chat_input("Consulte o Oráculo..."):
                st.session_state.chat_history.append({"role": "user", "content": p})
                with st.chat_message("user"): st.write(p)
                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        try:
                            genai.configure(api_key=st.session_state.api_key)
                            try:
                                model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=ORACLE_SYSTEM_PROMPT)
                                res = model.generate_content(p)
                            except:
                                model = genai.GenerativeModel('gemini-pro', system_instruction=ORACLE_SYSTEM_PROMPT)
                                res = model.generate_content(p)
                            
                            r_text = remove_markdown(res.text)
                            st.write(r_text)
                            st.session_state.chat_history.append({"role": "assistant", "content": r_text})
                        except Exception as e:
                            if "429" in str(e): st.warning("Muitas requisições. Tente em breve.")
                            else: st.error(f"Erro: {e}")

    # ABA 7 (Moderação)
    if user == ADMIN_USER:
        with current_tabs[6]:
            st.header("🛡️ Moderação")
            ca, cd = st.columns(2)
            with ca:
                st.subheader("Recrutar")
                with st.form("new_usr"):
                    nu = st.text_input("User")
                    np = st.text_input("Pass", type="password")
                    if st.form_submit_button("Criar"):
                        db = load_db()
                        if nu not in db:
                            db[nu] = {"password": np, "logs": [], "agendas": {}, "tree_branches": 1, "created_at": str(datetime.now()), "mod_message": ""}
                            save_db(db)
                            st.success("Criado!")
                        else: st.error("Já existe.")
            
            with cd:
                st.subheader("Banir")
                db = load_db()
                usrs = [u for u in db.keys() if u not in ["global_alerts", ADMIN_USER]]
                if usrs:
                    target = st.selectbox("Alvo:", usrs)
                    if st.button("Banir"):
                        del db[target]
                        save_db(db)
                        st.success("Banido!")
                        time.sleep(1)
                        st.rerun()
            
            st.divider()
            st.subheader("🔧 Reconstrução de Histórico")
            rec_u = st.selectbox("Usuário:", usrs, key="ru")
            if rec_u:
                with st.form("rec_form"):
                    rd = st.date_input("Data Antiga", value=date.today())
                    c1, c2, c3 = st.columns(3)
                    rp = c1.number_input("Páginas", min_value=0)
                    rq = c2.number_input("Questões", min_value=0)
                    rs = c3.number_input("Séries", min_value=0)
                    if st.form_submit_button("Adicionar"):
                        db = load_db()
                        db[rec_u]['logs'].append({
                            "data": rd.strftime("%Y-%m-%d"), "acordou": "00:00", "dormiu": "00:00",
                            "paginas": rp, "questoes": rq, "series": rs, "estudou": True, "materias": ["Recuperado Admin"]
                        })
                        db[rec_u]['tree_branches'] += 1
                        save_db(db)
                        st.success("Adicionado!")

# --- EXECUÇÃO ---
if 'user' not in st.session_state:
    login_page()
else:
    main_app()
