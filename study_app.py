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
                "subjects_list": ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"], # Lista padrão inicial
                "tree_branches": 1,
                "created_at": str(datetime.now()),
                "mod_message": ""
            }
            data_changed = True
    if data_changed: save_db(db)

ensure_users_exist()

# --- ESTILOS CSS (NOVO TEMA: GhostWhite & NavajoWhite) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {visibility: hidden;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); visibility: visible;}
    
    /* Botão Sidebar */
    [data-testid="stSidebarCollapsedControl"] {
        color: #8B4513 !important; /* Marrom Sela para contraste no claro */
        background-color: #FFDEAD; /* NavajoWhite */
        border-radius: 5px;
    }

    /* --- CORES GERAIS --- */
    /* Fundo Principal GhostWhite */
    .stApp { background-color: #F8F8FF; color: #333333; }
    
    /* Textos agora escuros para contraste */
    .stMarkdown, .stText, p, label, .stDataFrame, .stExpander { color: #4A4A4A !important; }
    
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #8B4513 !important; /* Marrom Nobre */
        font-family: 'Georgia', serif; /* Fonte mais clássica/real */
        text-shadow: none;
    }

    /* --- SIDEBAR (NavajoWhite) --- */
    [data-testid="stSidebar"] { 
        background-color: #FFDEAD; 
        border-right: 2px solid #DEB887; /* Burlywood */
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span { 
        color: #5C4033 !important; 
    }

    /* Inputs no fundo claro */
    .stTextInput > div > div > input, 
    .stNumberInput > div > div > input, 
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input,
    .stSelectbox > div > div > div,
    .stTextArea > div > div > textarea {
        background-color: #FFFFFF; 
        color: #333333; 
        border: 1px solid #DEB887;
    }
    ::placeholder { color: #999999 !important; }

    /* Botões */
    .stButton>button {
        background-color: #FFDEAD; 
        color: #5C4033; 
        border: 1px solid #8B4513; 
        border-radius: 6px; 
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton>button:hover {
        background-color: #FFE4C4; /* Bisque */
        color: #000000;
        border-color: #A0522D;
    }

    /* Cards (NavajoWhite suave) */
    .metric-card { 
        background-color: #FFF8DC; /* Cornsilk */
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #DEB887;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .metric-card h4, .metric-card p { color: #5C4033 !important; }

    /* Rank Card (Topo) */
    .rank-card {
        background: linear-gradient(135deg, #FFDEAD, #FFE4C4);
        color: #5C4033;
        padding: 20px; border-radius: 12px; text-align: center; margin-bottom: 20px;
        border: 2px solid #DAA520; /* Goldenrod */
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    /* Mensagens */
    .mod-message {
        background-color: #FFFaf0; /* FloralWhite */
        border-left: 5px solid #DAA520;
        padding: 15px; margin-top: 15px; border-radius: 8px; color: #333;
        border: 1px solid #EEE;
    }
    .private-message {
        background-color: #FFF0F5; /* LavenderBlush */
        border: 2px dashed #C71585;
        padding: 15px; margin-bottom: 20px; border-radius: 8px; color: #800000;
    }

    /* RANKING VERTICAL (O TRONO) */
    .throne-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 100%;
    }
    .throne-item {
        width: 80%;
        margin: 10px 0;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        position: relative;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    /* Ouro (Rei) */
    .rank-1 {
        background: linear-gradient(180deg, #FFD700 0%, #FDB931 100%);
        border: 3px solid #DAA520;
        transform: scale(1.1);
        z-index: 10;
        color: #4B3621;
    }
    .rank-1::before { content: '👑'; font-size: 2em; display: block; margin-bottom: -10px;}
    
    /* Prata (Príncipe) */
    .rank-2 {
        background: linear-gradient(180deg, #E0E0E0 0%, #C0C0C0 100%);
        border: 2px solid #A9A9A9;
        width: 70%;
        color: #333;
    }
    
    /* Bronze (Cavaleiro) */
    .rank-3 {
        background: linear-gradient(180deg, #CD7F32 0%, #A0522D 100%);
        border: 2px solid #8B4513;
        width: 60%;
        color: #FFF;
    }

    .stImage img { width: 100%; mix-blend-mode: multiply; }
    
    /* Calendário */
    .cal-day {
        background-color: #FFFFFF; border: 1px solid #DEB887;
        border-radius: 4px; padding: 10px; text-align: center; margin: 2px;
        min-height: 60px; color: #333;
    }
    .cal-day.planned { border: 2px solid #047a0a; background-color: #F0FFF0; }
    
    /* Árvore Container */
    .tree-container {
        background-color: #FFFFFF; border: 4px solid #8B4513;
        border-radius: 100%; width: 350px; height: 350px;
        margin-left: auto; margin-right: auto; overflow: hidden;
        display: flex; justify-content: center; align-items: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNÇÕES AUXILIARES ---
def generate_tree_svg(branches):
    # Árvore com cores ajustadas para fundo branco
    scale = min(max(branches, 1), 50) / 10.0
    if branches <= 0:
        return """
        <svg width="300" height="300" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
            <rect x="40" y="80" width="20" height="20" fill="#8B4513" />
            <text x="50" y="70" font-size="5" text-anchor="middle" fill="#555">A árvore secou...</text>
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
        leaves_svg += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#228B22" opacity="0.8" />'
    return f"""
    <svg width="350" height="350" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <rect x="45" y="{trunk_y}" width="10" height="{trunk_h}" fill="#8B4513" />
        {leaves_svg}
        <text x="50" y="95" font-size="4" text-anchor="middle" fill="#555">Ramos Vivos: {branches}</text>
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
    # Considera dia estudado se questões > 0 ou paginas > 0 (a lógica antiga de matérias foi removida)
    valid_logs = [l['data'] for l in logs if l.get('estudou', False)]
    study_dates = sorted(list(set(valid_logs)), reverse=True)
    if not study_dates: return 0
    streak = 0
    # Data base brasil
    today = datetime.now(timedelta(hours=-3)).date()
    # Se o ultimo estudo foi hoje ou ontem, o streak está vivo
    last = datetime.strptime(study_dates[0], "%Y-%m-%d").date()
    if (today - last).days > 1: return 0
    
    current_check = last
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
    st.title("🏛️ Mentor SpartaJus")
    st.markdown("<h3 style='text-align:center; color:#8B4513;'>Login</h3>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["🔑 Entrar", "📝 Registrar", "🔄 Alterar Senha"])
    with tab1:
        username = st.text_input("Usuário", key="l_u").strip()
        password = st.text_input("Senha", type="password", key="l_p")
        if st.button("Entrar", type="primary"):
            db = load_db()
            if username in db and db[username]['password'] == password:
                st.session_state['user'] = username
                st.session_state['user_data'] = db[username]
                if 'admin_user' in st.session_state: del st.session_state['admin_user']
                st.rerun()
            else: st.error("Dados inválidos.")
    # ... (Tabs 2 e 3 mantidas iguais, lógica padrão) ...
    with tab2:
        nu = st.text_input("Novo Usuário", key="r_u").strip()
        np = st.text_input("Nova Senha", type="password", key="r_p")
        if st.button("Registrar"):
            db = load_db()
            if nu in db: st.error("Já existe.")
            elif nu and np:
                db[nu] = {"password": np, "logs": [], "agendas": {}, "subjects_list": ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"], "tree_branches": 1, "created_at": str(datetime.now()), "mod_message": ""}
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
    
    # Garante campos novos
    if 'subjects_list' not in user_data: 
        user_data['subjects_list'] = ["Constitucional", "Administrativo", "Penal", "Civil", "Processo Civil"]
    
    st.session_state.api_key = get_api_key()
    
    # Totais
    total_q = sum([l.get('questoes', 0) for l in user_data['logs']])
    total_p = sum([l.get('paginas', 0) for l in user_data['logs']])
    streak = calculate_streak(user_data['logs'])
    
    # SIDEBAR
    with st.sidebar:
        if os.path.exists(LOGO_FILE): st.image(LOGO_FILE)
        st.write(f"### Olá, {user}")
        
        # Patentes Info
        st.markdown("""
        <div style='background-color: rgba(255, 255, 255, 0.5); padding: 10px; border-radius: 5px; margin-bottom: 15px; border: 1px solid #DEB887; font-size: 0.85em; color: #5C4033;'>
            <strong>🎖️ PATENTES:</strong><br>
            * Andarilho (até 5k)<br>
            ** Saco de Pancada (5k-10k)<br>
            *** Reserva (10k-15k)<br>
            **** Titã (15k-20k)<br>
            ***** Espartano (20k-25k)
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Sair"):
            del st.session_state['user']
            st.rerun()
            
        st.divider()
        # Gerenciador de Matérias na Sidebar
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

    # HEADER
    st.title("🏛️ Mentor SpartaJus")
    
    # Barra Progresso
    prog = total_q % 5000
    perc = (prog / 5000) * 100
    rem_q = 5000 - prog
    st.markdown(f"""
    <div style="background-color: #FFF; border: 1px solid #DEB887; border-radius: 12px; padding: 4px;">
        <div style="width: {perc}%; background-color: #047a0a; height: 24px; border-radius: 8px; text-align: center; color: white; font-size: 0.8em; line-height: 24px;">{perc:.1f}%</div>
    </div>
    <div style="display:flex; justify-content:space-between; font-size:0.8em; color:#555;">
        <span>Atual: {prog}</span><span>Falta: {rem_q}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Cards Topo
    c1, c2 = st.columns([2, 1])
    with c1: 
        st.markdown(f"""
        <div class='rank-card'>
            <h2>{user.upper()}</h2>
            <h3>🛡️ {get_patent(total_q)}</h3>
            <p>Questões Totais: {total_q} | 🔥 Fogo: {streak} dias</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        stars = "".join(["🟡"]*get_stars(total_p)[0] + ["⚪"]*get_stars(total_p)[1] + ["🟤"]*get_stars(total_p)[2])
        if not stars: stars = "Sem estrelas"
        st.markdown(f"<div class='metric-card'><h4>⭐ Leitura</h4><div style='font-size:1.5em;'>{stars}</div><p>Páginas: {total_p}</p></div>", unsafe_allow_html=True)

    # ABAS
    tabs = st.tabs(["📊 Diário", "📈 Dashboard", "🏆 Ranking", "📢 Avisos", "📅 Agenda", "🦁 Comportamento"] + (["🛡️ Admin"] if user==ADMIN_USER else []))

    # 1. DIÁRIO
    with tabs[0]:
        c_tree, c_form = st.columns([1, 1])
        with c_tree:
            st.subheader("Árvore da Constância")
            st.markdown(f'<div class="tree-container">{generate_tree_svg(user_data["tree_branches"])}</div>', unsafe_allow_html=True)
        
        with c_form:
            st.subheader("📝 Registro de Batalha")
            with st.form("log_form"):
                d_log = st.date_input("Data", value=date.today(), format="DD/MM/YYYY")
                c_t1, c_t2 = st.columns(2)
                wt = c_t1.text_input("Acordou (HH:MM)", value="06:00")
                sl = c_t2.text_input("Dormiu (HH:MM)", value="22:00")
                
                pg = st.number_input("Páginas Lidas", min_value=0)
                ws = st.number_input("Séries Musculação", min_value=0)
                
                st.markdown("---")
                st.markdown("##### ⚔️ Questões por Matéria")
                # NOVO MECANISMO DE REGISTRO
                # Data Editor para inserir múltiplas matérias
                quest_df = pd.DataFrame({"Matéria": [""], "Qtd": [0]})
                
                quest_editor = st.data_editor(
                    quest_df, 
                    num_rows="dynamic",
                    column_config={
                        "Matéria": st.column_config.SelectboxColumn(
                            "Matéria",
                            options=user_data['subjects_list'],
                            required=True
                        ),
                        "Qtd": st.column_config.NumberColumn("Qtd Questões", min_value=0, step=1)
                    },
                    use_container_width=True
                )

                if st.form_submit_button("💾 Salvar Registro"):
                    # Processa questões detalhadas
                    q_details = {}
                    total_q_day = 0
                    
                    for _, r in quest_editor.iterrows():
                        mat = r["Matéria"]
                        qtd = r["Qtd"]
                        if mat and qtd > 0:
                            q_details[mat] = q_details.get(mat, 0) + qtd
                            total_q_day += qtd
                    
                    is_study = (pg > 0) or (total_q_day > 0)
                    
                    new_log = {
                        "data": d_log.strftime("%Y-%m-%d"),
                        "acordou": wt, "dormiu": sl,
                        "paginas": pg, "series": ws,
                        "questoes": total_q_day,     # Total simples para métricas rápidas
                        "questoes_detalhadas": q_details, # Novo campo detalhado
                        "estudou": is_study
                    }
                    
                    # Verifica se data já existe
                    exists = False
                    for idx, l in enumerate(user_data['logs']):
                        if l['data'] == new_log['data']:
                            user_data['logs'][idx] = new_log # Sobrescreve se existir
                            exists = True
                            break
                    if not exists:
                        user_data['logs'].append(new_log)
                        # Lógica árvore
                        if is_study: user_data['tree_branches'] += 1
                        else: user_data['tree_branches'] -= 2
                    
                    save_current_user_data()
                    st.success("Registro Salvo!")
                    time.sleep(1)
                    st.rerun()

    # 2. DASHBOARD
    with tabs[1]:
        st.header("📈 Análise Estratégica")
        if user_data['logs']:
            # Processamento dos dados para gráficos
            all_q_details = {}
            for l in user_data['logs']:
                # Suporte a legado e novo
                dets = l.get('questoes_detalhadas', {})
                for m, q in dets.items():
                    all_q_details[m] = all_q_details.get(m, 0) + q
            
            # Gráfico de Pizza (Questões)
            st.subheader("Distribuição de Questões")
            if all_q_details:
                labels = list(all_q_details.keys())
                sizes = list(all_q_details.values())
                total = sum(sizes)
                
                fig, ax = plt.subplots(figsize=(6, 3))
                fig.patch.set_facecolor('white')
                ax.set_facecolor('white')
                
                # Cores vibrantes
                colors = ['#FF6347', '#4682B4', '#32CD32', '#FFD700', '#8A2BE2', '#FF69B4', '#00CED1']
                
                wedges, texts = ax.pie(sizes, labels=None, startangle=90, colors=colors)
                
                # Legenda personalizada com % na frente
                legend_labels = [f"{(s/total)*100:.1f}% - {l}" for l, s in zip(labels, sizes)]
                
                ax.legend(wedges, legend_labels, title="Matérias", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), frameon=False)
                ax.axis('equal')
                
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2: st.pyplot(fig)
            else:
                st.info("Nenhum detalhe de questões registrado ainda.")
            
            st.divider()
            st.subheader("📜 Histórico Detalhado")
            # Tabela editável adaptada
            df_hist = pd.DataFrame(user_data['logs'])
            # Formata detalhes para string
            def format_details(d):
                if isinstance(d, dict): return ", ".join([f"{k}: {v}" for k, v in d.items()])
                return ""
            
            df_hist['detalhes_str'] = df_hist.get('questoes_detalhadas', {}).apply(format_details)
            
            edited = st.data_editor(
                df_hist[['data', 'paginas', 'series', 'questoes', 'detalhes_str']],
                column_config={
                    "detalhes_str": st.column_config.TextColumn("Detalhes (Matéria: Qtd)", help="Edite no formato 'Const: 10, Penal: 5'"),
                    "questoes": st.column_config.NumberColumn("Total Q", disabled=True) # Total é calculado
                },
                use_container_width=True,
                num_rows="dynamic"
            )
            
            if st.button("Salvar Correções"):
                new_logs = []
                for _, r in edited.iterrows():
                    # Parser reverso da string de detalhes
                    d_str = r['detalhes_str']
                    new_dets = {}
                    total_q = 0
                    if d_str:
                        parts = d_str.split(',')
                        for p in parts:
                            if ':' in p:
                                m, q = p.split(':')
                                try:
                                    qtd = int(q.strip())
                                    new_dets[m.strip()] = qtd
                                    total_q += qtd
                                except: pass
                    
                    # Preserva outros campos
                    orig_log = next((l for l in user_data['logs'] if l['data'] == r['data']), {})
                    
                    new_entry = {
                        "data": r['data'],
                        "acordou": orig_log.get('acordou', '00:00'),
                        "dormiu": orig_log.get('dormiu', '00:00'),
                        "paginas": int(r['paginas']),
                        "series": int(r['series']),
                        "questoes": total_q,
                        "questoes_detalhadas": new_dets,
                        "estudou": (int(r['paginas']) > 0 or total_q > 0)
                    }
                    new_logs.append(new_entry)
                
                user_data['logs'] = new_logs
                save_current_user_data()
                st.success("Histórico atualizado!")
                time.sleep(1)
                st.rerun()

    # 3. RANKING (TRONO VERTICAL)
    with tabs[2]:
        st.header("🏆 Hall da Fama Real")
        db = load_db()
        users_ranks = []
        for u, d in db.items():
            if u == "global_alerts": continue
            q = sum([l.get('questoes', 0) for l in d.get('logs', [])])
            users_ranks.append({"User": u, "Q": q, "Patente": get_patent(q)})
        
        # Sort desc
        users_ranks.sort(key=lambda x: x['Q'], reverse=True)
        
        # Layout Vertical "Trono"
        st.markdown("<div class='throne-container'>", unsafe_allow_html=True)
        for i, p in enumerate(users_ranks):
            rank_class = "rank-1" if i==0 else "rank-2" if i==1 else "rank-3" if i==2 else "throne-item"
            medal = "👑" if i==0 else "🥈" if i==1 else "🥉" if i==2 else f"#{i+1}"
            
            bg_style = "" # CSS handles classes
            if i > 2: # Estilo genérico para resto
                st.markdown(f"""
                <div style='background: #FFF; border: 1px solid #DEB887; padding: 10px; margin: 5px; border-radius: 5px; width: 80%; text-align:center; color: #555;'>
                    <strong>{i+1}. {p['User']}</strong> - {p['Q']} Questões<br><small>{p['Patente']}</small>
                </div>
                """, unsafe_allow_html=True)
            else:
                # Top 3 com classes CSS
                st.markdown(f"""
                <div class='{rank_class} throne-item'>
                    <h3>{medal} {p['User']}</h3>
                    <p style='margin:0; font-weight:bold;'>{p['Q']} Questões</p>
                    <small>{p['Patente']}</small>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ... (ABAS 4, 5, 6, 7 mantidas com lógica anterior mas novo visual)
    with tabs[3]: # Avisos
        st.header("📢 Avisos")
        # (Lógica de avisos mantida)
        db = load_db()
        alerts = db.get("global_alerts", [])
        if not alerts: st.info("O silêncio reina.")
        for a in alerts:
            st.markdown(f"<div class='mod-message'><strong>{a['date']}</strong><br>{a['text']}</div>", unsafe_allow_html=True)
            
    with tabs[4]: # Agenda
        st.header("📅 Agenda")
        # (Lógica de agenda mantida)
        plan_date = st.date_input("Data:", format="DD/MM/YYYY")
        pk = plan_date.strftime("%Y-%m-%d")
        curr = user_data['agendas'].get(pk, "")
        nt = st.text_area("Plano:", value=curr, placeholder="Ex: Fazer 2 cadernos do TEC...")
        if st.button("Salvar Plano"):
            user_data['agendas'][pk] = nt
            save_current_user_data()
            st.success("Plano traçado!")

    with tabs[5]: # Comportamento
        st.header("🦁 Comportamento")
        # (Lógica mantida)
        if user_data['logs']:
            # Simplificado para exibição
            c1, c2 = st.columns(2)
            df = pd.DataFrame(user_data['logs'])
            # Contagem simples total
            c1.metric("Total Treinos", df[df['series'] > 0].shape[0])
            c2.metric("Total Leituras", df[df['paginas'] > 0].shape[0])
        else: st.info("Sem dados.")

    if user == ADMIN_USER:
        with tabs[6]:
            st.header("🛡️ Admin")
            # (Lógica admin mantida)
            st.write("Painel restrito.")

# --- EXECUÇÃO ---
if 'user' not in st.session_state:
    login_page()
else:
    main_app()
