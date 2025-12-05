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

# --- FUSO HORÁRIO BRASÍLIA ---
BRT = timezone(timedelta(hours=-3))

def get_now_br():
    """Retorna o timestamp atual em Brasília"""
    return datetime.now(BRT)

def get_today_br():
    """Retorna a data de hoje em Brasília"""
    return get_now_br().date()

# --- GERENCIAMENTO DE API KEY ---
ENCRYPTED_KEY_LOCAL = "QUl6YVN5RFI1VTdHeHNCZVVVTFE5M1N3UG9VNl9CaGl3VHZzMU9n"

def get_api_key():
    if "GEMINI_API_KEY" in st.secrets:
        return st.secrets["GEMINI_API_KEY"]
    try:
        return base64.b64decode(ENCRYPTED_KEY_LOCAL).decode("utf-8")
    except Exception:
        return ""

# --- FUNÇÕES DE GOOGLE SHEETS ---
def get_google_credentials():
    if "gcp_service_account" in st.secrets:
        return st.secrets["gcp_service_account"]
    return None

def connect_to_sheets():
    if not SHEETS_AVAILABLE: return None
    creds_dict = get_google_credentials()
    if not creds_dict: return None
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Erro ao conectar Google Sheets: {e}")
        return None

def sync_down_from_sheets():
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
                except: pass 
        if cloud_db:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(cloud_db, f, indent=4, default=str)
            return True
    except Exception as e:
        print(f"Erro ao baixar do Sheets: {e}")
        return False

def sync_up_to_sheets(db_data):
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

# --- PERSISTÊNCIA LOCAL ---
def load_db():
    if "db_synced" not in st.session_state:
        success = sync_down_from_sheets()
        if success: st.session_state["db_synced"] = True
    if not os.path.exists(DB_FILE): return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: return {} 
            return json.loads(content)
    except json.JSONDecodeError: return {}

def save_db(db_data):
    temp_file = f"{DB_FILE}.tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=4, default=str)
            f.flush()
            os.fsync(f.fileno()) 
        os.replace(temp_file, DB_FILE)
    except Exception as e:
        st.error(f"Erro salvamento local: {e}")
    try: sync_up_to_sheets(db_data)
    except: pass 

# --- AUTO-CRIAÇÃO ---
def ensure_users_exist():
    db = load_db()
    data_changed = False
    vip_users = { "fux_concurseiro": "Senha128", "steissy": "Mudar123", "JuOlebar": "Mudar123" }
    for user, default_pass in vip_users.items():
        if user not in db:
            db[user] = {
                "password": default_pass,
                "logs": [],
                "agendas": {},
                "subjects_list": ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"],
                "tree_branches": 1,
                "created_at": str(get_now_br()),
                "mod_message": ""
            }
            data_changed = True
    if data_changed: save_db(db)

ensure_users_exist()

# --- ESTILOS CSS (GHOSTWHITE & NAVAJOWHITE) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); visibility: visible;}
    
    [data-testid="stSidebarCollapsedControl"] {
        color: #8B4513 !important; 
        background-color: #FFDEAD; 
        border-radius: 5px;
    }

    /* CORES GERAIS */
    .stApp { background-color: #F8F8FF; color: #333333; }
    .stMarkdown, .stText, p, label, .stDataFrame, .stExpander { color: #4A4A4A !important; }
    
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #8B4513 !important; font-family: 'Georgia', serif; text-shadow: none;
    }

    /* SIDEBAR */
    [data-testid="stSidebar"] { background-color: #FFDEAD; border-right: 2px solid #DEB887; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { 
        color: #5C4033 !important; 
    }

    /* INPUTS */
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stDateInput > div > div > input, .stTimeInput > div > div > input, .stSelectbox > div > div > div, .stTextArea > div > div > textarea {
        background-color: #FFFFFF; color: #333333; border: 1px solid #DEB887;
    }
    ::placeholder { color: #999999 !important; }

    /* BUTTONS */
    .stButton>button {
        background-color: #FFDEAD; color: #5C4033; border: 1px solid #8B4513; 
        border-radius: 6px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #FFE4C4; color: #000000; border-color: #A0522D;
    }

    /* CARDS */
    .metric-card { background-color: #FFF8DC; padding: 15px; border-radius: 10px; border: 1px solid #DEB887; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .metric-card h4, .metric-card p { color: #5C4033 !important; }

    .rank-card {
        background: linear-gradient(135deg, #FFDEAD, #FFE4C4); color: #5C4033;
        padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;
        border: 2px solid #DAA520; box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    .mod-message { background-color: #FFFaf0; border-left: 5px solid #DAA520; padding: 15px; margin-top: 15px; border-radius: 8px; color: #333; border: 1px solid #EEE; }
    .private-message { background-color: #FFF0F5; border: 2px dashed #C71585; padding: 15px; margin-bottom: 20px; border-radius: 8px; color: #800000; }

    /* THRONE RANKING */
    .throne-container { display: flex; flex-direction: column; align-items: center; width: 100%; }
    .throne-item { width: 80%; margin: 10px 0; padding: 15px; border-radius: 8px; text-align: center; position: relative; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    
    .rank-1 { background: linear-gradient(180deg, #FFD700 0%, #FDB931 100%); border: 3px solid #DAA520; transform: scale(1.1); z-index: 10; color: #4B3621; }
    .rank-1::before { content: '👑'; font-size: 2em; display: block; margin-bottom: -10px;}
    .rank-2 { background: linear-gradient(180deg, #E0E0E0 0%, #C0C0C0 100%); border: 2px solid #A9A9A9; width: 70%; color: #333; }
    .rank-3 { background: linear-gradient(180deg, #CD7F32 0%, #A0522D 100%); border: 2px solid #8B4513; width: 60%; color: #FFF; }

    .stImage img { width: 100%; mix-blend-mode: multiply; }
    
    .cal-day { background-color: #FFFFFF; border: 1px solid #DEB887; border-radius: 4px; padding: 10px; text-align: center; margin: 2px; min-height: 60px; color: #333; }
    .cal-day.planned { border: 2px solid #047a0a; background-color: #F0FFF0; }
    
    .tree-container { background-color: #FFFFFF; border: 4px solid #8B4513; border-radius: 100%; width: 350px; height: 350px; margin-left: auto; margin-right: auto; overflow: hidden; display: flex; justify-content: center; align-items: center; }
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
            mins = int(rest.split('m')[0]) if rest.split('m')[0].isdigit() else (int(rest) if rest.isdigit() else 0)
            return hours * 60 + mins
        elif 'm' in t_str: return int(t_str.split('m')[0])
        elif ':' in t_str:
            h, m = t_str.split(':')
            return int(h)*60 + int(m)
        elif t_str.isdigit(): return int(t_str)
    except: pass
    return 0

def parse_time_str_to_obj(t_str):
    try:
        t_str = t_str.strip()
        for fmt in ("%H:%M", "%Hh%M", "%H:%M:%S"):
            try: return datetime.strptime(t_str, fmt).time()
            except ValueError: continue
    except: pass
    return None

def generate_tree_svg(branches):
    scale = min(max(branches, 1), 50) / 10.0
    if branches <= 0:
        return """<svg width="300" height="300" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect x="40" y="80" width="20" height="20" fill="#8B4513" /><text x="50" y="70" font-size="5" text-anchor="middle" fill="#555">A árvore secou...</text></svg>"""
    leaves_svg = ""
    random.seed(42)
    trunk_h = min(30 + (branches * 0.5), 60)
    trunk_y = 100 - trunk_h
    count = min(max(1, branches), 150)
    for i in range(count):
        cx = 50 + random.randint(-20 - int(branches/2), 20 + int(branches/2))
        cy = trunk_y + random.randint(-20 - int(branches/2), 10)
        r = random.randint(3, 6)
        leaves_svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#228B22" opacity="0.8" />'
    return f"""<svg width="350" height="350" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg"><rect x="45" y="{trunk_y}" width="10" height="{trunk_h}" fill="#8B4513" />{leaves_svg}<text x="50" y="95" font-size="4" text-anchor="middle" fill="#555">Ramos Vivos: {branches}</text></svg>"""

def get_patent(total_questions):
    patentes = ["O Maltrapilho (fase iniciante)", "O Comum (fase q banca te humilha)", "O Cadastrado (fase mediana)", "O Altivo (fase da perseverança)", "O Espartano (fase da autonomia)"]
    return patentes[min(int(total_questions / 5000), 4)]

def get_stars(total_pages):
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
    last = datetime.strptime(study_dates[0], "%Y-%m-%d").date()
    if (today - last).days > 1: return 0
    current_check = last
    streak = 0
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
        with c2: 
            st.image(LOGO_FILE)
    st.title("🏛️ Mentor SpartaJus")
    st.markdown("<h3 style='text-align:center; color:#8B4513;'>Login</h3>", unsafe_allow_html=True)
    tab1, tab2, tab3 = st.tabs(["🔑 Entrar", "📝 Registrar", "🔄 Alterar Senha"])
    with tab1:
        u = st.text_input("Usuário", key="l_u").strip()
        p = st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar", type="primary"):
            db = load_db()
            if u in db and db[u]['password'] == p:
                st.session_state['user'] = u
                st.session_state['user_data'] = db[u]
                if 'admin_user' in st.session_state: del st.session_state['admin_user']
                st.rerun()
            else: st.error("Dados inválidos.")
    with tab2:
        nu = st.text_input("Novo Usuário", key="r_u").strip()
        np = st.text_input("Nova Senha", type="password", key="r_p")
        if st.button("Registrar"):
            db = load_db()
            if nu in db: st.error("Já existe.")
            elif nu and np:
                db[nu] = {"password": np, "logs": [], "agendas": {}, "subjects_list": ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"], "tree_branches": 1, "created_at": str(get_now_br()), "mod_message": ""}
                save_db(db)
                st.success("Criado!")
            else: st.warning("Preencha tudo.")
    with tab3:
        cu = st.text_input("Usuário", key="c_u").strip()
        op = st.text_input("Senha Atual", type="password", key="c_op")
        nop = st.text_input("Nova Senha", type="password", key="c_np")
        if st.button("Alterar"):
            db = load_db()
            if cu in db and db[cu]['password'] == op:
                db[cu]['password'] = nop
                save_db(db)
                st.success("Senha alterada!")
            else: st.error("Erro.")

def save_current_user_data():
    if 'user' in st.session_state:
        db = load_db()
        db[st.session_state['user']] = st.session_state['user_data']
        save_db(db)

# --- APP PRINCIPAL ---
def main_app():
    user = st.session_state['user']
    user_data = st.session_state['user_data']
    is_real_admin = (user == ADMIN_USER)
    is_admin_mode = ('admin_user' in st.session_state and st.session_state['admin_user'] == ADMIN_USER)

    if 'subjects_list' not in user_data: user_data['subjects_list'] = ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"]
    
    if 'logs' in user_data:
        for log in user_data['logs']:
            if 'questoes_detalhadas' not in log:
                log['questoes_detalhadas'] = {}

    st.session_state.api_key = get_api_key()
    total_q = sum([l.get('questoes', 0) for l in user_data['logs']])
    total_p = sum([l.get('paginas', 0) for l in user_data['logs']])
    streak = calculate_streak(user_data['logs'])
    
    with st.sidebar:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE)
        st.write(f"### Olá, {user}")
        
        # STATUS DO GOOGLE SHEETS (Recuperado)
        if SHEETS_AVAILABLE and get_google_credentials():
            st.caption("🟢 Conectado à Nuvem (Google Sheets)")
        else:
            st.caption("🟠 Modo Offline (Local JSON)")

        st.markdown("""
        <div style='background-color: rgba(255, 255, 255, 0.5); padding: 10px; border-radius: 5px; margin-bottom: 15px; border: 1px solid #DEB887; font-size: 0.85em; color: #5C4033;'>
            <strong>🎖️ PATENTES DO SPARTAJUS:</strong><br>
            1ª O Maltrapilho (fase iniciante)<br>
            2ª O Comum (fase q banca te humilha)<br>
            3ª O Cadastrado (fase mediana)<br>
            4ª O Altivo (fase da perseverança)<br>
            5ª O Espartano (fase da autonomia)
        </div>""", unsafe_allow_html=True)
        if st.button("Sair"):
            del st.session_state['user']
            st.rerun()
        st.divider()
        st.markdown(f"### 💾 Backup: {get_now_br().strftime('%H:%M')}")
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                st.download_button("Baixar Dados (JSON)", f, f"backup_{get_now_br().strftime('%Y%m%d_%H%M')}.json", "application/json")
        
        st.divider()
        with st.expander("📚 Gerenciar Matérias"):
            new_sub = st.text_input("Nova Matéria:")
            if st.button("Adicionar") and new_sub:
                if new_sub not in user_data['subjects_list']:
                    user_data['subjects_list'].append(new_sub)
                    save_current_user_data()
                    st.success(f"{new_sub} adicionada!")
                    st.rerun()
            rem_sub = st.selectbox("Remover Matéria:", [""] + user_data['subjects_list'])
            if st.button("Remover") and rem_sub:
                user_data['subjects_list'].remove(rem_sub)
                save_current_user_data()
                st.rerun()
        
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

    st.title("🏛️ Mentor SpartaJus")
    prog = total_q % 5000
    perc = (prog / 5000) * 100
    rem_q = 5000 - prog
    st.markdown(f"""
    <div style="background-color: #FFF; border: 1px solid #DEB887; border-radius: 12px; padding: 4px;">
        <div style="width: {perc}%; background-color: #047a0a; height: 24px; border-radius: 8px; text-align: center; color: white; font-size: 0.8em; line-height: 24px;">{perc:.1f}%</div>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:0.8em; color:#555;"><span>Atual: {prog}</span><span>Falta: {rem_q}</span></div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([2, 1])
    with c1: st.markdown(f"<div class='rank-card'><h2>{user.upper()}</h2><h3>🛡️ {get_patent(total_q)}</h3><p>Total: {total_q} | 🔥 Fogo: {streak} dias</p></div>", unsafe_allow_html=True)
    with c2:
        stars = "".join(["🟡"]*get_stars(total_p)[0] + ["⚪"]*get_stars(total_p)[1] + ["🟤"]*get_stars(total_p)[2]) or "Sem estrelas"
        st.markdown(f"<div class='metric-card'><h4>⭐ Leitura</h4><div style='font-size:1.5em;'>{stars}</div><p>Páginas: {total_p}</p></div>", unsafe_allow_html=True)

    tabs = st.tabs(["📊 Diário", "📈 Dashboard", "🏆 Ranking", "📢 Avisos", "📅 Agenda", "🦁 Comportamento"] + (["🛡️ Admin"] if user==ADMIN_USER else []))

    with tabs[0]:
        c_tree, c_form = st.columns([1, 1])
        with c_tree:
            st.subheader("Árvore da Constância")
            st.markdown(f'<div class="tree-container">{generate_tree_svg(user_data["tree_branches"])}</div>', unsafe_allow_html=True)
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
                quest_editor = st.data_editor(quest_df, num_rows="dynamic", column_config={"Matéria": st.column_config.SelectboxColumn("Matéria", options=user_data['subjects_list'], required=True), "Qtd": st.column_config.NumberColumn("Qtd", min_value=0, step=1)}, use_container_width=True)
                if st.form_submit_button("💾 Salvar"):
                    q_details = {}
                    total_q_day = 0
                    for _, r in quest_editor.iterrows():
                        mat = r["Matéria"]
                        qtd = int(r["Qtd"]) if pd.notnull(r["Qtd"]) else 0
                        if mat and qtd > 0:
                            q_details[mat] = q_details.get(mat, 0) + qtd
                            total_q_day += qtd
                    
                    is_study = (pg > 0) or (total_q_day > 0)
                    d_str = d_log.strftime("%Y-%m-%d")
                    
                    new_log = {"data": d_str, "acordou": wt, "dormiu": sl, "paginas": pg, "series": ws, "questoes": total_q_day, "questoes_detalhadas": q_details, "estudou": is_study}
                    exists = False
                    for idx, l in enumerate(user_data['logs']):
                        if l['data'] == new_log['data']:
                            user_data['logs'][idx] = new_log
                            exists = True
                            break
                    if not exists:
                        user_data['logs'].append(new_log)
                        if is_study: user_data['tree_branches'] += 1
                        else: user_data['tree_branches'] -= 2
                    save_current_user_data()
                    st.success("Salvo!")
                    time.sleep(1)
                    st.rerun()

    with tabs[1]:
        st.header("📈 Análise")
        if user_data['logs']:
            all_q_details = {}
            for l in user_data['logs']:
                dets = l.get('questoes_detalhadas', {})
                for m, q in dets.items(): all_q_details[m] = all_q_details.get(m, 0) + q
            
            st.subheader("Distribuição de Questões")
            if all_q_details:
                labels = list(all_q_details.keys())
                sizes = list(all_q_details.values())
                total = sum(sizes)
                
                fig, ax = plt.subplots(figsize=(6, 3))
                fig.patch.set_facecolor('white')
                ax.set_facecolor('white')
                colors = ['#FF6347', '#4682B4', '#32CD32', '#FFD700', '#8A2BE2', '#FF69B4', '#00CED1']
                wedges, texts = ax.pie(sizes, labels=None, startangle=90, colors=colors)
                legend_labels = [f"{(s/total)*100:.1f}% - {l}" for l, s in zip(labels, sizes)]
                ax.legend(wedges, legend_labels, title="Matérias", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), frameon=False)
                ax.axis('equal')
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2: st.pyplot(fig)
            else: st.info("Sem detalhes de questões.")
            
            st.subheader("📈 Evolução de Questões")
            df_l = pd.DataFrame(user_data['logs'])
            if 'data' in df_l.columns:
                df_l['data_obj'] = pd.to_datetime(df_l['data']).dt.date
                df_l = df_l.sort_values(by='data_obj')
                
                if not df_l.empty:
                    fig_l, ax_l = plt.subplots(figsize=(5, 1.5))
                    fig_l.patch.set_facecolor('white')
                    ax_l.set_facecolor('white')
                    grp = df_l.groupby('data_obj')['questoes'].sum().reset_index()
                    ax_l.plot(grp['data_obj'], grp['questoes'], marker='o', color='#0044FF', linewidth=2, markerfacecolor='#FF0000')
                    ax_l.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                    ax_l.tick_params(colors='#333333', rotation=45, labelsize=8)
                    for spine in ax_l.spines.values(): spine.set_edgecolor('#333333')
                    ax_l.grid(color='#333333', linestyle=':', alpha=0.2)
                    cl1, cl2, cl3 = st.columns([1, 4, 1])
                    with cl2: st.pyplot(fig_l)
            
            st.divider()
            st.subheader("📜 Histórico Editável")
            df_hist = pd.DataFrame(user_data['logs'])
            if 'questoes_detalhadas' not in df_hist.columns: df_hist['questoes_detalhadas'] = [{} for _ in range(len(df_hist))]
            def format_details(d):
                if isinstance(d, dict): return ", ".join([f"{k}: {v}" for k, v in d.items()])
                return ""
            df_hist['detalhes_str'] = df_hist['questoes_detalhadas'].apply(format_details)
            if 'data' in df_hist.columns: df_hist['data'] = pd.to_datetime(df_hist['data']).dt.date
            
            edited = st.data_editor(
                df_hist[['data', 'paginas', 'series', 'questoes', 'detalhes_str']],
                use_container_width=True, num_rows="dynamic", key="hist_ed",
                column_config={
                    "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                    "detalhes_str": st.column_config.TextColumn("Detalhes (Mat: Qtd)", help="Ex: Const: 10, Penal: 5"),
                    "questoes": st.column_config.NumberColumn("Total Q", disabled=True)
                }
            )
            if st.button("Salvar Correções"):
                nl = []
                for _, r in edited.iterrows():
                    d_str_val = r['detalhes_str']
                    new_dets = {}
                    tq = 0
                    if d_str_val:
                        for p in str(d_str_val).split(','):
                            if ':' in p:
                                m, q = p.split(':')
                                try:
                                    qtd = int(q.strip())
                                    new_dets[m.strip()] = qtd
                                    tq += qtd
                                except: pass
                    orig_log = next((l for l in user_data['logs'] if l['data'] == r['data']), {})
                    data_val = r['data']
                    if isinstance(data_val, (date, datetime)): data_val = data_val.strftime("%Y-%m-%d")
                    nl.append({"data": data_val, "acordou": orig_log.get('acordou', '00:00'), "dormiu": orig_log.get('dormiu', '00:00'), "paginas": int(r['paginas']), "series": int(r['series']), "questoes": tq, "questoes_detalhadas": new_dets, "estudou": (int(r['paginas']) > 0 or tq > 0)})
                user_data['logs'] = nl
                save_current_user_data()
                st.success("Atualizado!")
                time.sleep(1)
                st.rerun()
        else: st.info("Sem registros.")

    with tabs[2]:
        st.header("🏆 Hall da Fama Real")
        db = load_db()
        ur = []
        for u, d in db.items():
            if u == "global_alerts": continue
            q = sum([l.get('questoes', 0) for l in d.get('logs', [])])
            ur.append({"User": u, "Q": q, "Patente": get_patent(q)})
        ur.sort(key=lambda x: x['Q'], reverse=True)
        st.markdown("<div class='throne-container'>", unsafe_allow_html=True)
        for i, p in enumerate(ur):
            cls = "rank-1" if i==0 else "rank-2" if i==1 else "rank-3" if i==2 else "throne-item"
            mdl = "👑" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"#{i+1}"
            if i > 2: st.markdown(f"<div style='background: #FFF; border: 1px solid #DEB887; padding: 10px; margin: 5px; border-radius: 5px; width: 80%; text-align:center; color: #555;'><strong>{i+1}. {p['User']}</strong> - {p['Q']} Questões<br><small>{p['Patente']}</small></div>", unsafe_allow_html=True)
            else: st.markdown(f"<div class='{cls} throne-item'><h3>{mdl} {p['User']}</h3><p style='margin:0; font-weight:bold;'>{p['Q']} Questões</p><small>{p['Patente']}</small></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with tabs[3]:
        st.header("📢 Avisos")
        db = load_db()
        alerts = db.get("global_alerts", [])
        if not alerts: st.info("Silêncio.")
        for a in alerts: st.markdown(f"<div class='mod-message'><strong>{a['date']}</strong><br>{a['text']}</div>", unsafe_allow_html=True)

    with tabs[4]:
        st.header("📅 Agenda")
        plan_date = st.date_input("Data:", format="DD/MM/YYYY")
        pk = plan_date.strftime("%Y-%m-%d")
        curr = user_data['agendas'].get(pk, "")
        nt = st.text_area("Plano:", value=curr, placeholder="Ex. Fazer 2 cadernos do TEC de Constitucional e 1 de Penal.")
        if st.button("Salvar Plano"):
            user_data['agendas'][pk] = nt
            save_current_user_data()
            st.success("Plano traçado!")

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
        else: st.info("Sem dados.")

    if user == ADMIN_USER:
        with tabs[6]:
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
                else: st.info("Ninguém para banir.")

# --- EXECUÇÃO ---
if 'user' not in st.session_state: login_page()
else: main_app()
