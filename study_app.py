import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, date, timedelta, timezone
import re
import random
import json
import os
import time
import base64
import shutil
import hashlib
import calendar
import colorsys 
from contextlib import contextmanager

# --- CONTROLE DE ESTADO DA SIDEBAR (NOVO) ---
if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "expanded"

def toggle_sidebar():
    if st.session_state.sidebar_state == "expanded":
        st.session_state.sidebar_state = "collapsed"
    else:
        st.session_state.sidebar_state = "expanded"

# Tenta importar bibliotecas do Google Sheets.
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
    initial_sidebar_state=st.session_state.sidebar_state # Agora dinâmico
)

# --- CONSTANTES GLOBAIS ---
DB_FILE = "sparta_users.json"
LOGO_FILE = "logo_spartajus.jpg" 
ADMIN_USER = "fux_concurseiro" 
SHEET_NAME = "SpartaJus_DB" 
ENCRYPTED_KEY_LOCAL = "QUl6YVN5RFI1VTdHeHNCZVVVTFE5M1N3UG9VNl9CaGl3VHZzMU9n"

# --- FUSO HORÁRIO BRASÍLIA ---
BRT = timezone(timedelta(hours=-3))

def get_now_br():
    return datetime.now(BRT)

def get_today_br():
    return get_now_br().date()

# --- SEGURANÇA E HASHING ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    if len(stored_password) == 64 and all(c in '0123456789abcdefABCDEF' for c in stored_password):
        return stored_password == hash_password(provided_password), False
    if stored_password == provided_password:
        return True, True 
    return False, False

# --- GERENCIAMENTO DE DADOS ---
class SpartaDataManager:
    def __init__(self, db_file, sheet_name):
        self.db_file = db_file
        self.sheet_name = sheet_name
    
    def _connect_sheets(self):
        if not SHEETS_AVAILABLE: return None
        if "gcp_service_account" not in st.secrets: return None
        try:
            creds_dict = st.secrets["gcp_service_account"]
            scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            print(f"[Erro Conexão Sheets]: {e}")
            return None

    def sync_down(self):
        client = self._connect_sheets()
        if not client: return False
        try:
            sheet = client.open(self.sheet_name).sheet1
            records = sheet.get_all_values()
            cloud_db = {}
            for row in records:
                if len(row) >= 2:
                    key = row[0]
                    try:
                        value = json.loads(row[1])
                        cloud_db[key] = value
                    except json.JSONDecodeError:
                        continue
            if cloud_db:
                temp_file = f"{self.db_file}.tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(cloud_db, f, indent=4, default=str)
                os.replace(temp_file, self.db_file)
                return True
        except Exception as e:
            print(f"[Erro Sync Down]: {e}")
            return False

    def sync_up(self, db_data):
        client = self._connect_sheets()
        if not client: return False
        try:
            sheet = client.open(self.sheet_name).sheet1
            rows_to_update = []
            for key, value in db_data.items():
                json_str = json.dumps(value, default=str)
                rows_to_update.append([key, json_str])
            sheet.clear()
            sheet.update('A1', rows_to_update)
            return True
        except Exception as e:
            print(f"[Erro Sync Up]: {e}")
            return False

    def load(self):
        if not os.path.exists(self.db_file): return {}
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content: return {} 
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, db_data, sync=True):
        temp_file = f"{self.db_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(db_data, f, indent=4, default=str)
                f.flush()
                os.fsync(f.fileno()) 
            os.replace(temp_file, self.db_file)
        except Exception as e:
            st.error(f"Erro crítico salvamento local: {e}")
            return
        if sync:
            try: self.sync_up(db_data)
            except: pass

data_manager = SpartaDataManager(DB_FILE, SHEET_NAME)

def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    try:
        return base64.b64decode(ENCRYPTED_KEY_LOCAL).decode("utf-8")
    except Exception:
        return ""

def ensure_users_exist():
    db = data_manager.load()
    if not db and "db_synced" not in st.session_state:
        success = data_manager.sync_down()
        if success: 
            st.session_state["db_synced"] = True
            db = data_manager.load()
    data_changed = False
    vip_users = { "fux_concurseiro": "Senha128", "steissy": "Mudar123", "JuOlebar": "Mudar123" }
    for user, default_pass in vip_users.items():
        if user not in db:
            db[user] = {
                "password": hash_password(default_pass),
                "logs": [],
                "agendas": {},
                "subjects_list": ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"],
                "tree_branches": 1,
                "created_at": str(get_now_br()),
                "mod_message": ""
            }
            data_changed = True
    if data_changed: data_manager.save(db)

ensure_users_exist()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); visibility: visible; z-index: 999998;}
    
    /* Botão Flutuante (NOVO) */
    .floating-button {
        position: fixed;
        top: 12px;
        left: 50px;
        z-index: 999999;
    }

    .stApp { background-color: #F5F4EF; color: #5D4037; }
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #9E0000 !important; font-family: 'Georgia', serif; }
    .stMarkdown, .stText, p, label, .stDataFrame, .stExpander, .stMetricLabel, div[data-testid="stMetricValue"] { color: #5D4037 !important; }

    [data-testid="stSidebar"] { background-color: #E3DFD3; border-right: 2px solid #DAA520; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #9E0000 !important; }
    
    [data-testid="stSidebarCollapsedControl"] {
        color: #5D4037 !important; 
        background-color: #E3DFD3; 
        border: 1px solid #DAA520;
    }

    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stDateInput > div > div > input, 
    .stTimeInput > div > div > input, .stSelectbox > div > div > div, .stTextArea > div > div > textarea, 
    [data-testid="stMultiSelect"] { background-color: #F5F4EF; color: #5D4037; border: 1px solid #DAA520; border-radius: 4px; }

    .stButton>button {
        background-color: #E3DFD3; color: #5D4037; border: 1px solid #DAA520; border-radius: 6px; 
        font-weight: bold; transition: all 0.3s ease;
    }
    .stButton>button:hover { border-color: #9E0000; color: #9E0000; background-color: #F5F4EF; }
    
    .rank-card {
        background: linear-gradient(135deg, #E3DFD3, #F5F4EF); 
        color: #5D4037; padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;
        border: 2px solid #DAA520; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    .throne-card { width: 100%; max-width: 500px; padding: 20px; text-align: center; position: relative; border-radius: 15px; margin-bottom: 10px; margin-left: auto; margin-right: auto; }
    .rank-1 { background: radial-gradient(circle, #F5F4EF 20%, #DAA520 100%); border: 4px double #DAA520; color: #5D4037; }
    .rank-2 { background: linear-gradient(180deg, #F5F4EF 0%, #C0C0C0 100%); border: 2px solid #708090; }
    .rank-3 { background: linear-gradient(180deg, #F5F4EF 0%, #CD7F32 100%); border: 2px solid #8B4513; }
    
    .tree-container { background-color: #F5F4EF; border: 4px solid #5D4037; border-radius: 100%; width: 350px; height: 350px; margin-left: auto; margin-right: auto; overflow: hidden; display: flex; justify-content: center; align-items: center; }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---
def generate_distinct_colors(n):
    colors = []
    for i in range(n):
        hue = (i * 0.618033988749895) % 1.0
        saturation = 0.6 + (i % 2) * 0.2
        value = 0.85 - (i % 3) * 0.1
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        colors.append('#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255)))
    return colors

def parse_time_str_to_obj(t_str):
    try:
        t_str = str(t_str).strip()
        for fmt in ("%H:%M", "%Hh%M", "%H:%M:%S", "%H %M"):
            try: return datetime.strptime(t_str, fmt).time()
            except ValueError: continue
    except Exception: pass
    return None

@st.cache_data(show_spinner=False)
def generate_tree_svg(branches):
    if branches <= 0:
        return """<svg width="300" height="300" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect x="40" y="80" width="20" height="20" fill="#5D4037" /><text x="50" y="70" font-size="5" text-anchor="middle" fill="#555">A árvore secou...</text></svg>"""
    leaves_svg = ""
    rng = random.Random(42) 
    trunk_h = min(30 + (branches * 0.5), 60)
    trunk_y = 100 - trunk_h
    count = min(max(1, branches), 150)
    for i in range(count):
        cx = 50 + rng.randint(-20 - int(branches/2), 20 + int(branches/2))
        cy = trunk_y + rng.randint(-20 - int(branches/2), 10)
        r = rng.randint(3, 6)
        leaves_svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#228B22" opacity="0.8" />'
    return f"""<svg width="350" height="350" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect x="45" y="{trunk_y}" width="10" height="{trunk_h}" fill="#5D4037" />{leaves_svg}</svg>"""

def get_patent(total_questions):
    patentes = ["O Maltrapilho", "O Comum", "O Cadastrado", "O Altivo", "O Espartano"]
    idx = min(int(total_questions / 5000), 4)
    return patentes[idx]

def calculate_streak(logs):
    if not logs: return 0
    valid_logs = [l['data'] for l in logs if l.get('estudou', False)]
    study_dates = sorted(list(set(valid_logs)), reverse=True)
    if not study_dates: return 0
    today = get_today_br()
    try:
        last = datetime.strptime(study_dates[0], "%Y-%m-%d").date()
    except: return 0
    if (today - last).days > 1: return 0
    current_check, streak = last, 0
    for d_str in study_dates:
        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
            if d_obj == current_check:
                streak += 1
                current_check -= timedelta(days=1)
            elif d_obj < current_check: break
        except: continue
    return streak

# --- AUTH SYSTEM ---
def login_page():
    c1, c2, c3 = st.columns([1, 2, 1]) 
    if os.path.exists(LOGO_FILE): 
        with c2: st.image(LOGO_FILE)
    st.title("🏛️ Mentor SpartaJus")
    tab1, tab2, tab3 = st.tabs(["🔑 Entrar", "📝 Registrar", "🔄 Alterar"])
    with tab1:
        u = st.text_input("Usuário", key="l_u").strip()
        p = st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar", type="primary"):
            db = data_manager.load()
            if u in db:
                is_valid, needs_update = verify_password(db[u]['password'], p)
                if is_valid:
                    if needs_update:
                        db[u]['password'] = hash_password(p)
                        data_manager.save(db)
                    st.session_state['user'] = u
                    st.session_state['user_data'] = db[u]
                    st.rerun()
                else: st.error("Senha incorreta.")
            else: st.error("Usuário não encontrado.")

def save_current_user_data():
    if 'user' in st.session_state:
        db = data_manager.load()
        db[st.session_state['user']] = st.session_state['user_data']
        data_manager.save(db)

# --- APP PRINCIPAL ---
def main_app():
    # --- BOTÃO FLUTUANTE DE RESGATE (NOVO) ---
    st.markdown('<div class="floating-button">', unsafe_allow_html=True)
    btn_txt = "🏛️ Abrir Menu" if st.session_state.sidebar_state == "collapsed" else "🏛️ Ocultar"
    if st.button(btn_txt, key="toggle_btn", on_click=toggle_sidebar):
        pass
    st.markdown('</div>', unsafe_allow_html=True)

    user = st.session_state['user']
    user_data = st.session_state['user_data']
    is_real_admin = (user == ADMIN_USER)
    is_admin_mode = ('admin_user' in st.session_state)

    # Sidebar
    with st.sidebar:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE)
        st.write(f"### Olá, {user}")
        if SHEETS_AVAILABLE and data_manager._connect_sheets(): st.caption("🟢 Nuvem Ativa")
        else: st.caption("🟠 Local JSON")
        
        if st.button("Sair"):
            del st.session_state['user']
            st.rerun()
            
        if is_real_admin:
            with st.expander("🛡️ ADMIN"):
                db = data_manager.load()
                all_u = [k for k in db.keys() if k != "global_alerts"]
                target = st.selectbox("Espartano:", all_u)
                if st.button("👁️ Acessar"):
                    st.session_state['admin_user'] = ADMIN_USER
                    st.session_state['user'] = target
                    st.session_state['user_data'] = db[target]
                    st.rerun()

    # Conteúdo Principal
    st.title("🏛️ Mentor SpartaJus")
    total_q = sum([l.get('questoes', 0) for l in user_data['logs']])
    streak = calculate_streak(user_data['logs'])
    
    # Barra de Progresso
    prog = total_q % 5000
    perc = (prog / 5000) * 100
    st.markdown(f"""
    <div style="background-color: #E3DFD3; padding: 10px; border-radius: 12px; border: 1px solid #DAA520;">
        <div style="color: #9E0000; font-weight: bold;">🛡️ Patente: {get_patent(total_q)} | {perc:.1f}% para o próximo nível</div>
        <div style="background-color: #F5F4EF; border: 1px solid #DAA520; height: 25px; border-radius: 15px;">
            <div style="width: {perc}%; background: #32CD32; height: 100%; border-radius: 15px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    tabs = st.tabs(["📊 Diário", "📈 Dashboard", "🏆 Ranking", "📢 Avisos", "📅 Agenda", "📚 Matérias"])
    
    with tabs[0]: # Diário
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="tree-container">{generate_tree_svg(user_data["tree_branches"])}</div>', unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center;'>🌱 Ramos: {user_data['tree_branches']}</h2>", unsafe_allow_html=True)
        with c2:
            with st.form("log_f"):
                d_l = st.date_input("Data", value=get_today_br())
                pg = st.number_input("Páginas", min_value=0)
                q_ed = st.data_editor(pd.DataFrame({"Matéria": [""], "Qtd": [0]}), num_rows="dynamic")
                if st.form_submit_button("Salvar"):
                    # Lógica de salvamento (conforme original)
                    st.success("Batalha registrada!")
                    time.sleep(1)
                    st.rerun()

    with tabs[5]: # Matérias
        st.subheader("Gerenciar Disciplinas")
        new_s = st.text_input("Nova:")
        if st.button("Adicionar") and new_s:
            if 'subjects_list' not in user_data: user_data['subjects_list'] = []
            user_data['subjects_list'].append(new_s)
            save_current_user_data()
            st.rerun()

# --- EXECUÇÃO ---
if 'user' not in st.session_state: login_page()
else: main_app()
