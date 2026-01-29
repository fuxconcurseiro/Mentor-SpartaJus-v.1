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
import colorsys # Importação necessária para gerar cores
from contextlib import contextmanager

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
    initial_sidebar_state="expanded"
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
    """Retorna o timestamp atual em Brasília"""
    return datetime.now(BRT)

def get_today_br():
    """Retorna a data de hoje em Brasília"""
    return get_now_br().date()

# --- SEGURANÇA E HASHING ---
def hash_password(password):
    """Gera um hash SHA-256 da senha."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_password, provided_password):
    """
    Verifica a senha. Suporta legado (texto plano) e migração automática.
    Retorna (bool_is_valid, bool_needs_update).
    """
    # Verifica se é hash (len 64 hex)
    if len(stored_password) == 64 and all(c in '0123456789abcdefABCDEF' for c in stored_password):
        return stored_password == hash_password(provided_password), False
    
    # Fallback para legado (texto plano)
    if stored_password == provided_password:
        return True, True # Válido, mas precisa atualizar para hash
    return False, False

# --- GERENCIAMENTO DE DADOS (CLASSE ROBUSTA) ---
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
        """Baixa do Sheets e atualiza local atomicamente."""
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
                # Escrita atômica para evitar corrupção
                temp_file = f"{self.db_file}.tmp"
                with open(temp_file, "w", encoding="utf-8") as f:
                    json.dump(cloud_db, f, indent=4, default=str)
                os.replace(temp_file, self.db_file)
                return True
        except Exception as e:
            print(f"[Erro Sync Down]: {e}")
            return False

    def sync_up(self, db_data):
        """Sobe dados locais para o Sheets."""
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
        """Carrega DB local com tratamento de erro."""
        if not os.path.exists(self.db_file): return {}
        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content: return {} 
                return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, db_data, sync=True):
        """Salva DB localmente e tenta sync."""
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
            # Sync em background idealmente, mas aqui síncrono para garantir
            try: self.sync_up(db_data)
            except: pass

# Instância Global do Gerenciador
data_manager = SpartaDataManager(DB_FILE, SHEET_NAME)

# --- FUNÇÕES DE LÓGICA DE NEGÓCIO ---

def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    try:
        return base64.b64decode(ENCRYPTED_KEY_LOCAL).decode("utf-8")
    except Exception:
        return ""

def ensure_users_exist():
    # Carrega sem sync inicial para velocidade, o sync ocorre no login ou load_db
    db = data_manager.load()
    if not db and "db_synced" not in st.session_state:
        success = data_manager.sync_down()
        if success: 
            st.session_state["db_synced"] = True
            db = data_manager.load()

    data_changed = False
    # Senhas padrão (serão convertidas para hash no primeiro login se necessário)
    vip_users = { 
        "fux_concurseiro": "Senha128", 
        "steissy": "Mudar123", 
        "JuOlebar": "Mudar123" 
    }
    
    for user, default_pass in vip_users.items():
        if user not in db:
            # Criando já com hash para novos registros
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

# Chama inicialização
ensure_users_exist()

# --- ESTILOS CSS (REBRANDING ESPARTANO) ---
st.markdown("""
    <style>
    /* Ocultar elementos padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); visibility: visible;}
    
    /* 1. FUNDO GERAL (Pergaminho) */
    .stApp { 
        background-color: #F5F4EF; 
        color: #5D4037; 
    }
    
    /* 2. TIPOGRAFIA (Sangue e Couro) */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #9E0000 !important; 
        font-family: 'Georgia', serif; 
        text-shadow: none;
    }
    .stMarkdown, .stText, p, label, .stDataFrame, .stExpander, .stMetricLabel, div[data-testid="stMetricValue"] { 
        color: #5D4037 !important; 
    }

    /* 3. SIDEBAR (Areia) */
    [data-testid="stSidebar"] { 
        background-color: #E3DFD3; 
        border-right: 2px solid #DAA520; /* Dourado na divisão */
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #9E0000 !important;
    }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label { 
        color: #5D4037 !important; 
    }
    
    /* Botão de colapso da sidebar */
    [data-testid="stSidebarCollapsedControl"] {
        color: #5D4037 !important; 
        background-color: #E3DFD3; 
        border: 1px solid #DAA520;
    }

    /* 4. INPUTS E CAIXAS (Camuflagem) */
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input, 
    .stDateInput > div > div > input, 
    .stTimeInput > div > div > input, 
    .stSelectbox > div > div > div, 
    .stTextArea > div > div > textarea, 
    [data-testid="stMultiSelect"] {
        background-color: #F5F4EF; /* Mesmo do fundo */
        color: #5D4037; 
        border: 1px solid #DAA520; /* Borda Dourada */
        border-radius: 4px;
    }
    ::placeholder { color: #8C7B75 !important; }

    /* 5. BOTÕES (Estilo Espartano) */
    .stButton>button {
        background-color: #E3DFD3; /* Bege Escuro */
        color: #5D4037; /* Marrom */
        border: 1px solid #DAA520; /* Borda Dourada */
        border-radius: 6px; 
        font-weight: bold; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        border-color: #9E0000; /* Vermelho Sangue */
        color: #9E0000;
        background-color: #F5F4EF;
    }
    /* Botões Primários (Ações Fortes) */
    div.stButton > button[kind="primary"] {
        background-color: #DAA520;
        color: #FFFFFF;
        border: 1px solid #B8860B;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #9E0000;
        border-color: #800000;
    }

    /* 6. CARDS E CONTAINERS */
    .metric-card { 
        background-color: #E3DFD3; /* Areia */
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #DAA520; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
    }
    .metric-card h4, .metric-card p { color: #5D4037 !important; }

    .rank-card {
        background: linear-gradient(135deg, #E3DFD3, #F5F4EF); 
        color: #5D4037;
        padding: 20px; 
        border-radius: 12px; 
        text-align: center; 
        margin-bottom: 20px;
        border: 2px solid #DAA520; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    /* Mensagens */
    .mod-message { 
        background-color: #E3DFD3; 
        border-left: 5px solid #9E0000; 
        padding: 15px; 
        margin-top: 15px; 
        border-radius: 4px; 
        color: #5D4037; 
        border: 1px solid #DAA520; 
    }
    .private-message { 
        background-color: #F5F4EF; 
        border: 2px dashed #9E0000; 
        padding: 15px; 
        margin-bottom: 20px; 
        border-radius: 8px; 
        color: #9E0000; 
    }

    /* THRONE RANKING - Ajuste de Cores */
    .throne-container { display: flex; flex-direction: column; align-items: center; width: 100%; gap: 15px; }
    
    .throne-card {
        width: 100%;
        max-width: 500px;
        padding: 20px;
        text-align: center;
        position: relative;
        border-radius: 15px;
        margin-bottom: 10px;
        transition: transform 0.2s;
        margin-left: auto;
        margin-right: auto;
    }
    .throne-card:hover { transform: scale(1.02); }

    /* RANK 1 - Ouro & Rubi */
    .rank-1 {
        background: radial-gradient(circle, #F5F4EF 20%, #DAA520 100%);
        border: 4px double #DAA520; 
        box-shadow: 
            0 0 15px rgba(218, 165, 32, 0.4), 
            inset 0 0 20px rgba(158, 0, 0, 0.1);
        color: #5D4037;
    }
    .rank-1::before, .rank-1::after {
        content: ''; position: absolute; width: 12px; height: 12px; border-radius: 50%;
        background: radial-gradient(circle at 30% 30%, #9E0000, #5D4037);
        box-shadow: 0 0 5px #9E0000; border: 1px solid #DAA520;
    }
    .rank-1::before { top: 10px; left: 10px; }
    .rank-1::after { top: 10px; right: 10px; }

    /* RANK 2 - Prata (Ajustado) */
    .rank-2 {
        background: linear-gradient(180deg, #F5F4EF 0%, #C0C0C0 100%);
        border: 2px solid #708090;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        color: #5D4037;
    }

    /* RANK 3 - Bronze (Ajustado) */
    .rank-3 {
        background: linear-gradient(180deg, #F5F4EF 0%, #CD7F32 100%);
        border: 2px solid #8B4513;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        color: #3E2723;
    }

    .laurel-text { font-family: 'Georgia', serif; font-weight: bold; font-size: 1.2em; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .laurel-icon { font-size: 1.5em; opacity: 0.8; color: #9E0000; }

    .stImage img { width: 100%; mix-blend-mode: multiply; }
    
    .cal-day { background-color: #F5F4EF; border: 1px solid #DAA520; border-radius: 4px; padding: 10px; text-align: center; margin: 2px; min-height: 60px; color: #5D4037; }
    .cal-day.planned { border: 2px solid #9E0000; background-color: #E3DFD3; }
    
    .tree-container { background-color: #F5F4EF; border: 4px solid #5D4037; border-radius: 100%; width: 350px; height: 350px; margin-left: auto; margin-right: auto; overflow: hidden; display: flex; justify-content: center; align-items: center; }
    
    /* Tabs */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        color: #5D4037 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #9E0000 !important;
        border-bottom-color: #9E0000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES OTIMIZADAS ---
def generate_distinct_colors(n):
    """Gera N cores distintas usando a Proporção Áurea para evitar repetição e tangência."""
    colors = []
    for i in range(n):
        # Golden Angle (~0.618) garante que cada nova cor esteja o mais longe possível das anteriores no círculo cromático
        hue = (i * 0.618033988749895) % 1.0
        # Variação de saturação e valor para aumentar ainda mais o contraste visual
        saturation = 0.6 + (i % 2) * 0.2  # Alterna entre 0.6 e 0.8
        value = 0.85 - (i % 3) * 0.1      # Alterna brilho
        
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        # Converte para Hex
        colors.append('#{:02x}{:02x}{:02x}'.format(int(r*255), int(g*255), int(b*255)))
    return colors

def parse_time_str_to_min(t_str):
    t_str = str(t_str).lower().replace(' ', '')
    try:
        if 'h' in t_str:
            parts = t_str.split('h')
            hours = int(parts[0]) if parts[0].isdigit() else 0
            rest = parts[1]
            mins_str = rest.split('m')[0]
            mins = int(mins_str) if mins_str.isdigit() else (int(rest) if rest.isdigit() else 0)
            return hours * 60 + mins
        elif 'm' in t_str: return int(t_str.split('m')[0])
        elif ':' in t_str:
            h, m = t_str.split(':')
            return int(h)*60 + int(m)
        elif t_str.isdigit(): return int(t_str)
    except Exception: pass
    return 0

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
    scale = min(max(branches, 1), 50) / 10.0
    if branches <= 0:
        return """<svg width="300" height="300" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect x="40" y="80" width="20" height="20" fill="#5D4037" /><text x="50" y="70" font-size="5" text-anchor="middle" fill="#555">A árvore secou...</text></svg>"""
    leaves_svg = ""
    # Usando seed local para consistência visual sem afetar random global
    rng = random.Random(42) 
    trunk_h = min(30 + (branches * 0.5), 60)
    # Revertendo: Base do tronco volta para 100 (sem texto embaixo dentro do SVG)
    trunk_y = 100 - trunk_h
    count = min(max(1, branches), 150)
    for i in range(count):
        cx = 50 + rng.randint(-20 - int(branches/2), 20 + int(branches/2))
        cy = trunk_y + rng.randint(-20 - int(branches/2), 10)
        r = rng.randint(3, 6)
        leaves_svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#228B22" opacity="0.8" />'
    
    # Revertendo: Removemos o texto de dentro do SVG
    return f"""<svg width="350" height="350" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect x="45" y="{trunk_y}" width="10" height="{trunk_h}" fill="#5D4037" />{leaves_svg}</svg>"""

def get_patent(total_questions):
    patentes = ["O Maltrapilho (fase iniciante)", "O Comum (fase q banca te humilha)", "O Cadastrado (fase mediana)", "O Altivo (fase da perseverança)", "O Espartano (fase da autonomia)"]
    idx = min(int(total_questions / 5000), 4)
    return patentes[idx]

def get_stars(total_pages):
    if total_pages == 0: return 0, 0, 0
    raw_bronze = int(total_pages / 1000)
    gold = raw_bronze // 9
    if gold >= 3: return 3, 0, 0
    rem = raw_bronze % 9
    return gold, rem // 3, rem % 3

def calculate_streak(logs):
    if not logs: return 0
    valid_logs = [l['data'] for l in logs if l.get('estudou', False)]
    study_dates = sorted(list(set(valid_logs)), reverse=True)
    if not study_dates: return 0
    
    today = get_today_br()
    try:
        last = datetime.strptime(study_dates[0], "%Y-%m-%d").date()
    except ValueError:
        return 0

    if (today - last).days > 1: return 0
    
    current_check = last
    streak = 0
    for d_str in study_dates:
        try:
            d_obj = datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError: continue
        
        if d_obj == current_check:
            streak += 1
            current_check -= timedelta(days=1)
        elif d_obj < current_check: break
    return streak

# --- AUTH SYSTEM ---
def login_page():
    c1, c2, c3 = st.columns([1, 2, 1]) 
    if os.path.exists(LOGO_FILE): 
        with c2: 
            st.image(LOGO_FILE)
    
    st.title("🏛️ Mentor SpartaJus")
    st.markdown("<h3 style='text-align:center; color:#9E0000;'>Login</h3>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔑 Entrar", "📝 Registrar", "🔄 Alterar Senha"])
    
    with tab1:
        u = st.text_input("Usuário", key="l_u").strip()
        p = st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar", type="primary"):
            db = data_manager.load()
            if u in db:
                stored_pass = db[u]['password']
                is_valid, needs_update = verify_password(stored_pass, p)
                
                if is_valid:
                    # Atualiza hash se for senha antiga
                    if needs_update:
                        db[u]['password'] = hash_password(p)
                        data_manager.save(db)
                    
                    st.session_state['user'] = u
                    st.session_state['user_data'] = db[u]
                    if 'admin_user' in st.session_state: del st.session_state['admin_user']
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("Usuário não encontrado.")
    
    with tab2:
        nu = st.text_input("Novo Usuário", key="r_u").strip()
        np = st.text_input("Nova Senha", type="password", key="r_p")
        if st.button("Registrar"):
            db = data_manager.load()
            if nu in db: st.error("Já existe este guerreiro.")
            elif nu and np:
                db[nu] = {
                    "password": hash_password(np), # Já salva com hash
                    "logs": [], "agendas": {}, 
                    "subjects_list": ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"], 
                    "tree_branches": 1, 
                    "created_at": str(get_now_br()), 
                    "mod_message": ""
                }
                data_manager.save(db)
                st.success("Conta criada! Vá para o Login.")
            else: st.warning("Preencha todos os campos.")
            
    with tab3:
        cu = st.text_input("Usuário", key="c_u").strip()
        op = st.text_input("Senha Atual", type="password", key="c_op")
        nop = st.text_input("Nova Senha", type="password", key="c_np")
        if st.button("Alterar"):
            db = data_manager.load()
            if cu in db:
                is_valid, _ = verify_password(db[cu]['password'], op)
                if is_valid:
                    db[cu]['password'] = hash_password(nop)
                    data_manager.save(db)
                    st.success("Senha atualizada com segurança!")
                else: st.error("Senha atual incorreta.")
            else: st.error("Usuário não encontrado.")

def save_current_user_data():
    if 'user' in st.session_state:
        db = data_manager.load()
        # Merge simples: Atualiza apenas o usuário atual, mantém outros
        db[st.session_state['user']] = st.session_state['user_data']
        data_manager.save(db)

# --- APP PRINCIPAL ---
def main_app():
    user = st.session_state['user']
    user_data = st.session_state['user_data']
    is_real_admin = (user == ADMIN_USER)
    is_admin_mode = ('admin_user' in st.session_state and st.session_state['admin_user'] == ADMIN_USER)

    # Garante estrutura de dados mínima
    if 'subjects_list' not in user_data: user_data['subjects_list'] = ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"]
    if 'logs' in user_data:
        for log in user_data['logs']:
            if 'questoes_detalhadas' not in log: log['questoes_detalhadas'] = {}

    st.session_state.api_key = get_api_key()
    total_q = sum([l.get('questoes', 0) for l in user_data['logs']])
    total_p = sum([l.get('paginas', 0) for l in user_data['logs']])
    streak = calculate_streak(user_data['logs'])
    
    with st.sidebar:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE)
        st.write(f"### Olá, {user}")
        
        # STATUS DO GOOGLE SHEETS
        if SHEETS_AVAILABLE and data_manager._connect_sheets():
            st.caption("🟢 Conectado à Nuvem (Google Sheets)")
        else:
            st.caption("🟠 Modo Offline (Local JSON)")

        st.markdown("""
        <div style='background-color: #E3DFD3; padding: 10px; border-radius: 5px; margin-bottom: 15px; border: 1px solid #DAA520; font-size: 0.85em; color: #5D4037;'>
            <strong>🎖️ PATENTES DO SPARTAJUS:</strong><br>
            1ª O Maltrapilho (Iniciante)<br>
            2ª O Comum (Em apuros)<br>
            3ª O Cadastrado (Mediano)<br>
            4ª O Altivo (Perseverante)<br>
            5ª O Espartano (Autônomo)
        </div>""", unsafe_allow_html=True)
        
        if st.button("Sair"):
            del st.session_state['user']
            st.rerun()
            
        st.divider()
        # --- ATENÇÃO: GERENCIAR MATÉRIAS REMOVIDO DAQUI PARA UMA ABA PRÓPRIA ---
        # ISSO CORRIGE O ERRO DE VISUALIZAÇÃO NO MOBILE
        
        if is_real_admin or is_admin_mode:
            with st.expander("🛡️ PAINEL DO MODERADOR", expanded=True):
                st.caption("Área restrita de comando")
                if is_real_admin:
                    db = data_manager.load()
                    all_users = [k for k in db.keys() if k != "global_alerts"]
                    target_user = st.selectbox("Selecione o Espartano:", all_users)
                    if st.button("👁️ Acessar Dashboard"):
                        st.session_state['admin_user'] = ADMIN_USER
                        st.session_state['user'] = target_user
                        st.session_state['user_data'] = db[target_user]
                        st.rerun()
                elif is_admin_mode:
                    st.warning(f"Visualizando: {user}")
                    if st.button("⬅️ Voltar ao Admin"):
                        st.session_state['user'] = ADMIN_USER
                        st.session_state['user_data'] = data_manager.load()[ADMIN_USER]
                        st.rerun()

        # BACKUP NO FINAL
        st.divider()
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                st.download_button("Baixar Backup (JSON)", f, f"backup_{get_now_br().strftime('%Y%m%d_%H%M')}.json", "application/json")

    # --- BODY PRINCIPAL ---
    st.title("🏛️ Mentor SpartaJus")
    
    # Barra de Progresso Melhorada
    prog = total_q % 5000
    perc = (prog / 5000) * 100
    rem_q = 5000 - prog
    
    st.markdown(f"""
    <div style="background-color: #E3DFD3; padding: 10px; border-radius: 12px; margin-bottom: 25px; border: 1px solid #DAA520; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
        <div style="color: #9E0000; font-weight: bold; margin-bottom: 8px; display: flex; justify-content: space-between; font-size: 1.1em;">
            <span>🛡️ Progresso da Patente</span>
            <span>Próximo nível em: {rem_q} questões</span>
        </div>
        <div style="background-color: #F5F4EF; border: 2px solid #DAA520; border-radius: 20px; height: 35px; position: relative; box-shadow: inset 0 2px 5px rgba(0,0,0,0.1);">
            <div style="width: {perc}%; background: linear-gradient(90deg, #047a0a, #32CD32); height: 100%; border-radius: 16px; display: flex; align-items: center; justify-content: center; box-shadow: 2px 0 5px rgba(0,0,0,0.2); min-width: 40px;">
                <span style="color: white; font-weight: bold; text-shadow: 1px 1px 2px #333; font-size: 1.1em;">{perc:.1f}%</span>
            </div>
            <div style="position: absolute; right: 15px; top: 0; bottom: 0; display: flex; align-items: center; color: #5D4037; font-size: 0.9em; font-weight: bold; opacity: 0.8;">
                Faltam {rem_q}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([2, 1])
    with c1: 
        st.markdown(f"<div class='rank-card'><h2>{user.upper()}</h2><h3>🛡️ {get_patent(total_q)}</h3><p>Total: {total_q} | 🔥 Fogo: {streak} dias</p></div>", unsafe_allow_html=True)
    with c2:
        g, s, b = get_stars(total_p)
        stars = "".join(["🟡"]*g + ["⚪"]*s + ["🟤"]*b) or "Sem estrelas"
        st.markdown(f"<div class='metric-card'><h4>⭐ Leitura</h4><div style='font-size:1.5em;'>{stars}</div><p>Páginas: {total_p}</p></div>", unsafe_allow_html=True)

    # --- ATUALIZAÇÃO: ADICIONADA ABA DE MATÉRIAS ---
    tabs = st.tabs(["📊 Diário", "📈 Dashboard", "🏆 Ranking", "📢 Avisos", "📅 Agenda", "🦁 Comportamento", "📚 Matérias"] + (["🛡️ Admin"] if user==ADMIN_USER else []))

    # --- TAB 1: DIÁRIO ---
    with tabs[0]:
        c_tree, c_form = st.columns([1, 1])
        with c_tree:
            st.subheader("Árvore da Constância")
            st.markdown(f'<div class="tree-container">{generate_tree_svg(user_data["tree_branches"])}</div>', unsafe_allow_html=True)
            # Novo local do texto: Fora do SVG, destacado e centralizado
            st.markdown(f"<h2 style='text-align: center; color: #9E0000; margin-top: 10px;'>🌱 Ramos Vivos: {user_data['tree_branches']}</h2>", unsafe_allow_html=True)
            
            if user_data.get('mod_message'):
                st.markdown(f"<div class='private-message'><strong>📨 MENSAGEM DO MENTOR:</strong><br>{user_data['mod_message']}</div>", unsafe_allow_html=True)
        
        with c_form:
            st.subheader("📝 Registro de Batalha")
            with st.form("log_form"):
                d_log = st.date_input("Data", value=get_today_br(), format="DD/MM/YYYY")
                c_t1, c_t2 = st.columns(2)
                wt = c_t1.text_input("Acordou (HH:MM)", value="06:00")
                sl = c_t2.text_input("Dormiu (HH:MM)", value="22:00")
                pg = st.number_input("Páginas Lidas", min_value=0)
                ws = st.number_input("Séries Musculação", min_value=0)
                
                st.markdown("---")
                st.markdown("##### ⚔️ Questões por Matéria")
                quest_df = pd.DataFrame({"Matéria": [""], "Qtd": [0]})
                quest_editor = st.data_editor(
                    quest_df, 
                    num_rows="dynamic", 
                    column_config={
                        "Matéria": st.column_config.SelectboxColumn(
                            "Matéria", 
                            options=[""] + user_data['subjects_list'], # Adicionado opção vazia
                            required=False
                        ), 
                        "Qtd": st.column_config.NumberColumn("Qtd", min_value=0, step=1)
                    }, 
                    use_container_width=True
                )
                
                if st.form_submit_button("💾 Salvar"):
                    q_details = {}
                    total_q_day = 0
                    if quest_editor is not None and not quest_editor.empty:
                        for _, r in quest_editor.iterrows():
                            mat = r.get("Matéria")
                            try: qtd = int(r.get("Qtd", 0))
                            except: qtd = 0
                            
                            if mat and qtd > 0:
                                q_details[mat] = q_details.get(mat, 0) + qtd
                                total_q_day += qtd
                    
                    is_study = (pg > 0) or (total_q_day > 0)
                    d_str = d_log.strftime("%Y-%m-%d")
                    
                    new_log = {
                        "data": d_str, 
                        "acordou": wt, 
                        "dormiu": sl, 
                        "paginas": pg, 
                        "series": ws, 
                        "questoes": total_q_day, 
                        "questoes_detalhadas": q_details, 
                        "estudou": is_study
                    }
                    
                    # Atualiza ou insere log
                    exists = False
                    for idx, l in enumerate(user_data['logs']):
                        if l['data'] == new_log['data']:
                            user_data['logs'][idx] = new_log
                            exists = True
                            break
                    if not exists:
                        user_data['logs'].append(new_log)
                        if is_study: user_data['tree_branches'] += 1
                        else: user_data['tree_branches'] = max(0, user_data['tree_branches'] - 2) # Evita negativo
                    
                    save_current_user_data()
                    st.success("Salvo com glória!")
                    time.sleep(1)
                    st.rerun()

    # --- TAB 2: DASHBOARD ---
    with tabs[1]:
        st.header("📈 Análise Tática")
        if user_data['logs']:
            # -----------------------------------
            # FILTROS DE INTELIGÊNCIA
            # -----------------------------------
            st.markdown("##### 🔍 Filtros Personalizados")
            
            # Recuperar datas para limites do Date Input
            all_dates = [datetime.strptime(l['data'], "%Y-%m-%d").date() for l in user_data['logs']]
            min_date = min(all_dates) if all_dates else get_today_br()
            max_date = max(all_dates) if all_dates else get_today_br()
            
            # Layout dos Filtros
            c_f1, c_f2 = st.columns([1, 1])
            
            with c_f1:
                # Seletor de Período (Padrão: Todo o histórico)
                date_range = st.date_input(
                    "Período de Análise:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    format="DD/MM/YYYY"
                )
            
            with c_f2:
                # Seletor de Matérias (Padrão: Todas)
                all_subjects = user_data['subjects_list']
                selected_subjects = st.multiselect(
                    "Matérias de Interesse:",
                    options=all_subjects,
                    default=all_subjects,
                    placeholder="Selecione as matérias..."
                )

            st.divider()

            # -----------------------------------
            # PROCESSAMENTO DOS DADOS FILTRADOS
            # -----------------------------------
            filtered_q_details = {}
            filtered_total = 0
            
            # Validação do Range de Data (evita erro se usuário selecionar só data inicial)
            start_d, end_d = min_date, max_date
            if isinstance(date_range, tuple):
                if len(date_range) == 2:
                    start_d, end_d = date_range
                elif len(date_range) == 1:
                    start_d = end_d = date_range[0]

            for l in user_data['logs']:
                log_date = datetime.strptime(l['data'], "%Y-%m-%d").date()
                
                # Aplica Filtro de Data
                if start_d <= log_date <= end_d:
                    dets = l.get('questoes_detalhadas', {})
                    for m, q in dets.items():
                        # Aplica Filtro de Matéria
                        if m in selected_subjects:
                            filtered_q_details[m] = filtered_q_details.get(m, 0) + q
                            filtered_total += q
            
            # -----------------------------------
            # PLOTAGEM DO GRÁFICO
            # -----------------------------------
            st.subheader("Distribuição de Questões (Personalizado)")
            if filtered_q_details:
                labels = list(filtered_q_details.keys())
                sizes = list(filtered_q_details.values())
                
                fig, ax = plt.subplots(figsize=(6, 3))
                fig.patch.set_facecolor('#F5F4EF')
                ax.set_facecolor('#F5F4EF')
                
                # GERAÇÃO DINÂMICA DE CORES (Baseado apenas nas matérias filtradas)
                colors = generate_distinct_colors(len(labels))
                
                wedges, _ = ax.pie(sizes, labels=None, startangle=90, colors=colors)
                legend_labels = [f"{(s/filtered_total)*100:.1f}% - {l}" for l, s in zip(labels, sizes)]
                
                ax.legend(wedges, legend_labels, title="Matérias", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), frameon=False, labelcolor='#5D4037')
                ax.axis('equal')
                
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2: st.pyplot(fig)
                plt.close(fig) 
            else: 
                st.warning("⚠️ Nenhum registro encontrado para os filtros selecionados.")
            
            # -----------------------------------
            # GRÁFICO DE EVOLUÇÃO (MANTIDO GERAL)
            # -----------------------------------
            st.divider()
            st.subheader("📈 Evolução de Questões (Histórico Completo)")
            df_l = pd.DataFrame(user_data['logs'])
            if 'data' in df_l.columns and not df_l.empty:
                df_l['data_obj'] = pd.to_datetime(df_l['data']).dt.date
                df_l = df_l.sort_values(by='data_obj')
                
                fig_l, ax_l = plt.subplots(figsize=(5, 1.5))
                fig_l.patch.set_facecolor('#F5F4EF')
                ax_l.set_facecolor('#F5F4EF')
                grp = df_l.groupby('data_obj')['questoes'].sum().reset_index()
                ax_l.plot(grp['data_obj'], grp['questoes'], marker='o', color='#9E0000', linewidth=2, markerfacecolor='#DAA520')
                ax_l.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                ax_l.tick_params(colors='#5D4037', rotation=45, labelsize=8)
                for spine in ax_l.spines.values(): spine.set_edgecolor('#DAA520')
                ax_l.grid(color='#5D4037', linestyle=':', alpha=0.2)
                
                cl1, cl2, cl3 = st.columns([1, 4, 1])
                with cl2: st.pyplot(fig_l)
                plt.close(fig_l) 
            
            st.divider()
            st.subheader("📜 Histórico Editável")
            # Preparação dos dados para edição
            df_hist = pd.DataFrame(user_data['logs'])
            
            # Garante que colunas essenciais existam no DataFrame
            for col in ['acordou', 'dormiu']:
                if col not in df_hist.columns: df_hist[col] = "00:00"
            if 'questoes_detalhadas' not in df_hist.columns: df_hist['questoes_detalhadas'] = [{} for _ in range(len(df_hist))]
            
            def format_details(d):
                if isinstance(d, dict): return ", ".join([f"{k}: {v}" for k, v in d.items()])
                return ""
                
            df_hist['detalhes_str'] = df_hist['questoes_detalhadas'].apply(format_details)
            if 'data' in df_hist.columns: df_hist['data'] = pd.to_datetime(df_hist['data']).dt.date
            
            # Ajuste: Removido 'estudou' da visualização, mantendo horários
            cols_to_show = ['data', 'acordou', 'dormiu', 'paginas', 'series', 'questoes', 'detalhes_str']
            # Intersecção para garantir que colunas existam
            cols_final = [c for c in cols_to_show if c in df_hist.columns]
            
            # --- CORREÇÃO APLICADA AQUI ---
            # Removido 'disabled=True' da coluna questoes e adicionado min_value
            edited = st.data_editor(
                df_hist[cols_final],
                use_container_width=True, num_rows="dynamic", key="hist_ed",
                column_config={
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "detalhes_str": st.column_config.TextColumn("Detalhes (Mat: Qtd)", help="Ex: Const: 10, Penal: 5"),
                    "questoes": st.column_config.NumberColumn("Total Q", min_value=0, step=1), # Agora editável
                    "acordou": st.column_config.TextColumn("Acordou (HH:MM)"),
                    "dormiu": st.column_config.TextColumn("Dormiu (HH:MM)")
                }
            )
            
            if st.button("Salvar Correções"):
                nl = []
                for _, r in edited.iterrows():
                    d_str_val = r['detalhes_str']
                    new_dets = {}
                    tq_calc = 0
                    
                    # Tenta extrair a quantidade manual que o usuário digitou na coluna
                    try: manual_q = int(r.get('questoes', 0))
                    except: manual_q = 0

                    if d_str_val:
                        parts = str(d_str_val).split(',')
                        for p in parts:
                            if ':' in p:
                                try:
                                    m, q = p.split(':')
                                    qtd = int(q.strip())
                                    new_dets[m.strip()] = qtd
                                    tq_calc += qtd
                                except: pass
                    
                    # --- LÓGICA DE PREVENÇÃO DE ERROS ---
                    # Se a soma dos detalhes for maior que 0, usamos ela (consistência).
                    # Se não houver detalhes (tq_calc == 0), respeitamos o valor manual inserido na coluna "Total Q".
                    final_q = tq_calc if tq_calc > 0 else manual_q

                    data_val = r['data']
                    if isinstance(data_val, (date, datetime)): data_val = data_val.strftime("%Y-%m-%d")
                    
                    # Lógica Automática: Se tem página ou questão, estudou = True
                    is_study = (int(r['paginas']) > 0 or final_q > 0)

                    nl.append({
                        "data": data_val, 
                        "acordou": str(r.get('acordou', '06:00')), 
                        "dormiu": str(r.get('dormiu', '22:00')), 
                        "paginas": int(r['paginas']), 
                        "series": int(r['series']), 
                        "questoes": final_q, 
                        "questoes_detalhadas": new_dets, 
                        "estudou": is_study
                    })
                
                user_data['logs'] = nl
                save_current_user_data()
                st.success("Histórico reescrito!")
                time.sleep(1)
                st.rerun()
        else: st.info("Sem registros ainda.")

    # --- TAB 3: RANKING ---
    with tabs[2]:
        st.header("🏆 Hall da Fama Real")
        db = data_manager.load()
        ur = []
        for u, d in db.items():
            if u == "global_alerts": continue
            q = sum([l.get('questoes', 0) for l in d.get('logs', [])])
            ur.append({"User": u, "Q": q, "Patente": get_patent(q)})
        
        ur.sort(key=lambda x: x['Q'], reverse=True)
        
        # 1. PRIMEIRO LUGAR (CENTRALIZADO)
        if len(ur) > 0:
            p1 = ur[0]
            # Usa rank-1 (luxuoso)
            extra_jewel = "<div style='font-size:0.8em; margin-top:5px;'>💎 ♦️ 💎</div>"
            html_1 = f"""
            <div class='throne-container'>
                <div class='throne-card rank-1'>
                    <div class='laurel-text'>
                        <span class='laurel-icon'>🌿</span>
                        <span>👑 {p1['User']}</span>
                        <span class='laurel-icon'>🌿</span>
                    </div>
                    {extra_jewel}
                    <hr style='border-top: 1px solid rgba(0,0,0,0.1); margin: 10px 0;'>
                    <p style='margin:0; font-weight:bold; font-size:1.1em;'>{p1['Q']} Questões</p>
                    <small style='font-style:italic;'>{p1['Patente']}</small>
                </div>
            </div>
            """.replace("\n", " ")
            st.markdown(html_1, unsafe_allow_html=True)
        
        # 2. SEGUNDO E TERCEIRO (LADO A LADO)
        if len(ur) > 1:
            c_rank2, c_rank3 = st.columns(2)
            
            # Rank 2
            p2 = ur[1]
            html_2 = f"""
            <div class='throne-card rank-2'>
                <h3>🥈 {p2['User']}</h3>
                <p style='margin:0; font-weight:bold;'>{p2['Q']} Questões</p>
                <small>{p2['Patente']}</small>
            </div>
            """.replace("\n", " ")
            with c_rank2:
                st.markdown(html_2, unsafe_allow_html=True)
            
            # Rank 3 (se existir)
            if len(ur) > 2:
                p3 = ur[2]
                html_3 = f"""
                <div class='throne-card rank-3'>
                    <h3>🥉 {p3['User']}</h3>
                    <p style='margin:0; font-weight:bold;'>{p3['Q']} Questões</p>
                    <small>{p3['Patente']}</small>
                </div>
                """.replace("\n", " ")
                with c_rank3:
                    st.markdown(html_3, unsafe_allow_html=True)

        st.divider()
        st.subheader("📜 Lista Geral de Guerreiros")
        
        if ur:
            # Criação da Tabela Nominal
            df_rank = pd.DataFrame(ur)
            df_rank.index += 1 # Começar ranking do 1
            df_rank.reset_index(inplace=True)
            df_rank.columns = ['Posição', 'Guerreiro', 'Questões', 'Patente']
            
            st.dataframe(
                df_rank,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Posição": st.column_config.NumberColumn("Rank", format="#%d", width="small"),
                    "Guerreiro": st.column_config.TextColumn("Guerreiro", width="medium"),
                    "Questões": st.column_config.ProgressColumn(
                        "Poder de Fogo", 
                        format="%d", 
                        min_value=0, 
                        max_value=max(df_rank['Questões']) if not df_rank.empty else 100
                    ),
                    "Patente": st.column_config.TextColumn("Patente", width="large"),
                }
            )
        else:
            st.info("O exército ainda está sendo recrutado.")

    # --- TAB 4: AVISOS ---
    with tabs[3]:
        st.header("📢 Central de Comandos")
        
        # --- ÁREA DO USUÁRIO (LEITURA) ---
        # 1. Alertas Pessoais
        if user_data.get('mod_message'):
            st.markdown(f"""
            <div class='private-message'>
                <h3>📨 Mensagem Pessoal do Mentor</h3>
                {user_data['mod_message']}
            </div>
            """, unsafe_allow_html=True)
        else:
            if user != ADMIN_USER:
                st.info("Nenhuma mensagem pessoal do mentor.")

        st.divider()

        # 2. Alertas Gerais
        st.subheader("📢 Alertas Gerais")
        db = data_manager.load() # Reload to get fresh alerts
        alerts = db.get("global_alerts", [])
        
        if not alerts:
            st.caption("Sem alertas globais no momento.")
        
        for i, a in enumerate(alerts):
            st.markdown(f"<div class='mod-message'><strong>{a['date']}</strong><br>{a['text']}</div>", unsafe_allow_html=True)
            # Se for admin, mostra botão de apagar aqui mesmo
            if user == ADMIN_USER:
                if st.button(f"🗑️ Apagar Alerta #{i+1}", key=f"del_alert_{i}"):
                    del db["global_alerts"][i]
                    data_manager.save(db)
                    st.rerun()

        # --- ÁREA DO ADMIN (ESCRITA) ---
        if user == ADMIN_USER:
            st.divider()
            st.subheader("🛡️ Painel de Transmissão (Moderador)")
            
            with st.container(border=True):
                mode = st.radio("Destino da Mensagem:", ["📢 Todos (Geral)", "👤 Espartano (Pessoal)"], horizontal=True)
                
                if "Todos" in mode:
                    new_alert_text = st.text_area("Novo Alerta Geral:", height=100)
                    if st.button("🚀 Publicar para Todos"):
                        if new_alert_text:
                            if "global_alerts" not in db: db["global_alerts"] = []
                            # Insere no início para ser o mais recente
                            db["global_alerts"].insert(0, {
                                "date": get_now_br().strftime("%d/%m/%Y %H:%M"), 
                                "text": new_alert_text
                            })
                            data_manager.save(db)
                            st.success("Alerta Global enviado!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("Escreva algo.")
                else:
                    # Carrega usuários para o selectbox
                    all_users = [u for u in db.keys() if u not in ["global_alerts", ADMIN_USER]]
                    target_u = st.selectbox("Selecione o Soldado:", all_users)
                    
                    if target_u:
                        current_msg = db[target_u].get("mod_message", "")
                        st.caption(f"Mensagem atual: {current_msg if current_msg else '(Vazio)'}")
                        
                        msg_text = st.text_area("Mensagem Pessoal:", value=current_msg, height=100)
                        
                        c_save, c_clear = st.columns(2)
                        with c_save:
                            if st.button("💾 Enviar/Atualizar"):
                                db[target_u]["mod_message"] = msg_text
                                data_manager.save(db)
                                st.success(f"Mensagem para {target_u} atualizada!")
                        with c_clear:
                            if st.button("🗑️ Apagar Mensagem"):
                                db[target_u]["mod_message"] = ""
                                data_manager.save(db)
                                st.success(f"Mensagem para {target_u} removida!")

    # --- TAB 5: AGENDA ---
    with tabs[4]:
        st.header("📅 Agenda")
        
        # Seção de Planejamento (existente)
        st.subheader("Traçar Meta")
        # Default para amanhã, conforme solicitado
        plan_date = st.date_input("Data Alvo:", value=get_today_br() + timedelta(days=1), format="DD/MM/YYYY") 
        pk = plan_date.strftime("%Y-%m-%d")
        curr = user_data['agendas'].get(pk, "")
        nt = st.text_area("Plano para este dia:", value=curr, placeholder="Ex. Fazer 2 cadernos do TEC de Constitucional e 1 de Penal.", height=150)
        
        if st.button("💾 Salvar Meta"):
            if nt.strip():
                user_data['agendas'][pk] = nt
                save_current_user_data()
                st.success("Meta definida!")
            else:
                if pk in user_data['agendas']:
                    del user_data['agendas'][pk]
                    save_current_user_data()
                    st.success("Meta removida.")
                else:
                    st.warning("A meta está vazia.")

        st.divider()
        
        # Seção de Estatísticas (nova)
        st.subheader("📊 Consistência do Planejamento")
        
        # 1. Identificar meses disponíveis
        agendas_keys = list(user_data['agendas'].keys())
        # Convert keys to date objects to sort and extract months
        dates = []
        for k in agendas_keys:
            try:
                dates.append(datetime.strptime(k, "%Y-%m-%d").date())
            except: pass
            
        # Add current month to ensure it's always an option
        today = get_today_br()
        if today not in dates:
            dates.append(today)
            
        # Extract unique months (YYYY-MM)
        unique_months = sorted(list(set([d.strftime("%Y-%m") for d in dates])), reverse=True)
        
        # Formatter for display
        def format_month(m_str):
            y, m = m_str.split('-')
            return f"{m}/{y}"
            
        # Selectbox
        selected_month_str = st.selectbox("Selecione o Mês:", unique_months, format_func=format_month)
        
        # Count days planned in selected month
        count_planned = 0
        if selected_month_str:
            y_sel, m_sel = selected_month_str.split('-')
            for k, v in user_data['agendas'].items():
                if v and v.strip(): # Check if not empty
                    try:
                        kd = datetime.strptime(k, "%Y-%m-%d").date()
                        if kd.year == int(y_sel) and kd.month == int(m_sel):
                            count_planned += 1
                    except: pass
        
        # Display Metric
        st.metric(label=f"Dias Planejados em {format_month(selected_month_str)}", value=f"{count_planned} dias")
        
        # Visual feedback (Progress bar)
        year = int(selected_month_str.split('-')[0])
        month = int(selected_month_str.split('-')[1])
        _, num_days = calendar.monthrange(year, month)
        
        progress = min(count_planned / num_days, 1.0)
        st.progress(progress)
        st.caption(f"Você planejou {int(progress*100)}% dos dias deste mês.")

    # --- TAB 6: COMPORTAMENTO ---
    with tabs[5]:
        st.header("🦁 Comportamento")
        if user_data['logs']:
            df_beh = pd.DataFrame(user_data['logs'])
            if 'data' in df_beh.columns:
                df_beh['dt'] = pd.to_datetime(df_beh['data'])
                df_beh['month_year'] = df_beh['dt'].dt.strftime('%m/%Y')
            
                av_months = sorted(df_beh['month_year'].unique(), reverse=True)
                sel_m = st.selectbox("Mês:", av_months)
                df_m = df_beh[df_beh['month_year'] == sel_m]
                
                cw, cs, ct, cr = 0, 0, 0, 0
                for _, r in df_m.iterrows():
                    tw = parse_time_str_to_obj(str(r.get('acordou', '')))
                    # Lógica simplificada e segura
                    if tw and tw < datetime.strptime("06:00", "%H:%M").time(): cw += 1
                    
                    ts = parse_time_str_to_obj(str(r.get('dormiu', '')))
                    if ts and ts >= datetime.strptime("18:00", "%H:%M").time() and ts < datetime.strptime("22:00", "%H:%M").time(): cs += 1
                    
                    if int(r.get('series', 0)) > 0: ct += 1
                    if int(r.get('paginas', 0)) > 0: cr += 1
                    
                st.markdown(f"### {sel_m}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("🌅 < 6h", f"{cw} dias")
                c2.metric("🌙 < 22h", f"{cs} dias")
                c3.metric("💪 Treino", f"{ct} dias")
                c4.metric("📚 Leitura", f"{cr} dias")
        else: st.info("Sem dados suficientes.")

    # --- TAB 7: MATÉRIAS (NOVA) ---
    with tabs[6]:
        st.header("📚 Gerenciar Matérias")
        st.caption("Adicione ou remova disciplinas do seu plano de estudo.")
        
        c_add, c_rem = st.columns(2)
        
        with c_add:
            st.subheader("Adicionar")
            new_sub = st.text_input("Nova Matéria:")
            if st.button("➕ Adicionar Matéria", type="primary") and new_sub:
                if new_sub not in user_data['subjects_list']:
                    user_data['subjects_list'].append(new_sub)
                    save_current_user_data()
                    st.success(f"{new_sub} adicionada com sucesso!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.warning("Essa matéria já existe na sua lista.")
        
        with c_rem:
            st.subheader("Remover")
            rem_sub = st.selectbox("Selecione para remover:", [""] + user_data['subjects_list'])
            if st.button("🗑️ Remover Matéria") and rem_sub:
                user_data['subjects_list'].remove(rem_sub)
                save_current_user_data()
                st.success(f"{rem_sub} removida!")
                time.sleep(0.5)
                st.rerun()
                
        st.divider()
        st.markdown("### 📋 Lista Atual")
        st.write(", ".join(user_data['subjects_list']))

    # --- TAB 8: ADMIN (SE TIVER PERMISSÃO) ---
    if user == ADMIN_USER:
        with tabs[7]:
            st.header("🛡️ Moderação")
            ca, cd = st.columns(2)
            with ca:
                st.subheader("Recrutar")
                with st.form("new_usr"):
                    nu = st.text_input("User")
                    np = st.text_input("Pass", type="password")
                    if st.form_submit_button("Criar"):
                        db = data_manager.load()
                        if nu not in db:
                            db[nu] = {
                                "password": hash_password(np), # Hash aqui também
                                "logs": [], "agendas": {}, "tree_branches": 1, 
                                "created_at": str(datetime.now()), "mod_message": ""
                            }
                            data_manager.save(db)
                            st.success("Recruta adicionado!")
                        else: st.error("Já existe.")
            with cd:
                st.subheader("Banir")
                db = data_manager.load()
                usrs = [u for u in db.keys() if u not in ["global_alerts", ADMIN_USER]]
                if usrs:
                    target = st.selectbox("Alvo:", usrs)
                    if st.button("Banir"):
                        del db[target]
                        data_manager.save(db)
                        st.success("Banido!")
                        time.sleep(1)
                        st.rerun()
                else: st.info("Ninguém para banir.")

# --- EXECUÇÃO ---
if 'user' not in st.session_state: login_page()
else: main_app()
