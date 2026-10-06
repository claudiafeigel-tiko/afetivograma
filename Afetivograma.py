import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
from io import BytesIO
from datetime import datetime, timedelta
import gspread

st.set_page_config(page_title="Afetivograma", layout="wide")

NOME_PLANILHA = "Banco de Dados - Afetivograma"

def get_gspread_client():
    if "gcp_service_account" in st.secrets:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        return gspread.service_account_from_dict(credentials_dict)
    else:
        json_files = [f for f in os.listdir('.') if f.endswith('.json')]
        if json_files:
            return gspread.service_account(filename=json_files[0])
        else:
            st.error("Arquivo de credenciais JSON do Google não encontrado na pasta e st.secrets não configurado.")
            st.stop()

# --- DICIONÁRIOS ---
niveis_humor = {
    3: "+3 - Mania (Ideias)",
    2: "+2 - Hipomania (Agitada, produtiva)",
    1: "+1 - Levemente elevada",
    0: "0 - Neutro / Estável",
    -1: "-1 - Levemente deprimida",
    -2: "-2 - Depressão moderada",
    -3: "-3 - Depressão grave (Vazio, isolamento)"
}
niveis_ansiedade = {0: "0 - Nenhuma", 1: "1 - Leve", 2: "2 - Moderada", 3: "3 - Grave"}
niveis_irritabilidade = {0: "0 - Nenhuma", 1: "1 - Pequenos incômodos", 2: "2 - Impaciência", 3: "3 - Frustração severa"}
niveis_sociedade = {
    3: "+3 - Positiva Severa", 2: "+2 - Positiva Média", 1: "+1 - Positiva Suave",
    0: "0 - Nenhuma",
    -1: "-1 - Negativa Suave", -2: "-2 - Negativa Média", -3: "-3 - Negativa Severa"
}
niveis_esquizofrenia = {
    0: "0 - Nenhuma (Realidade)",
    1: "1 - Discreta (Somente Imaginação)",
    2: "2 - Intermediária (Imaginação com ação leve)",
    3: "3 - Grave (Imaginação com ações Concretas)"
}
esquizofrenia_clinico = {
    0: "Ausência de sintomas",
    1: "Sintomas prodrômicos / Somente Imaginação",
    2: "Episódio psicótico / Imaginação com ação leve",
    3: "Surto psicótico grave / Imaginação com ações Concretas"
}
niveis_sexo = {0: "Não", 1: "Sim"}

def carregar_dados():
    colunas_padrao = [
        'ID', 'Data_Str', 'Horario_Str', 'Humor_Val', 'Humor_Desc', 
        'Ansiedade_Val', 'Ansiedade_Desc', 'Irritabilidade_Val', 'Irritabilidade_Desc',
        'Sono', 'Sexo_Val', 'Condicao_Fisica', 'Social_Val', 'Social_Desc',
        'Esquizofrenia_Val', 'Esquizofrenia_Clinico', 'Gatilhos', 'Notas'
    ]
    try:
        gc = get_gspread_client()
        sheet = gc.open(NOME_PLANILHA).sheet1
        dados = sheet.get_all_records()
        df = pd.DataFrame(dados) if dados else pd.DataFrame(columns=colunas_padrao)
    except Exception as e:
        df = pd.DataFrame(columns=colunas_padrao)

    for col in colunas_padrao:
        if col not in df.columns:
            df[col] = ""
    
    if df.empty or df['ID'].isnull().all() or df['ID'].eq("").all():
        df['ID'] = pd.Series(dtype=int)
    else:
        df['ID'] = pd.to_numeric(df['ID'], errors='coerce').fillna(0).astype(int)
    return df.fillna("")

def salvar_dados_no_sheets(df):
    gc = get_gspread_client()
    sheet = gc.open(NOME_PLANILHA).sheet1
    sheet.clear()
    dados_para_enviar = [df.columns.values.tolist()] + df.astype(str).values.tolist()
    sheet.update(dados_para_enviar)

df_historico = carregar_dados()

horarios_opcoes = [f"{h:02d}:{m:02d}" for h in range(23, -1, -1) for m in (45, 30, 15, 0)]

opcoes_id_dict = {"[ + ] Novo Registro": None}
for _, row in df_historico.iterrows():
    if row['Data_Str'] != "" and row['Horario_Str'] != "":
        label = f"ID {int(row['ID'])} ({row['Data_Str']} {row['Horario_Str']})"
        opcoes_id_dict[label] = int(row['ID'])

opcoes_id = list(opcoes_id_dict.keys())

# --- INICIALIZAÇÃO DO SESSION STATE ---
if 'in_id_sel' not in st.session_state:
    st.session_state['in_id_sel'] = "[ + ] Novo Registro"
if 'in_data' not in st.session_state:
    st.session_state['in_data'] = datetime.today().date()
if 'in_hora' not in st.session_state:
    st.session_state['in_hora'] = "21:30"
if 'in_humor' not in st.session_state:
    st.session_state['in_humor'] = 0
if 'in_ans' not in st.session_state:
    st.session_state['in_ans'] = 0
if 'in_irr' not in st.session_state:
    st.session_state['in_irr'] = 0
if 'in_sono' not in st.session_state:
    st.session_state['in_sono'] = 8.0
if 'in_sex' not in st.session_state:
    st.session_state['in_sex'] = 0
if 'in_fis' not in st.session_state:
    st.session_state['in_fis'] = []
if 'in_soc' not in st.session_state:
    st.session_state['in_soc'] = 0
if 'in_gat' not in st.session_state:
    st.session_state['in_gat'] = []
if 'in_esq' not in st.session_state:
    st.session_state['in_esq'] = 0
if 'in_not' not in st.session_state:
    st.session_state['in_not'] = ""

def carregar_registro_callback():
    sel_label = st.session_state['in_id_sel']
    if sel_label != "[ + ] Novo Registro" and sel_label in opcoes_id_dict:
        id_num = opcoes_id_dict[sel_label]
        match = df_historico[df_historico['ID'] == id_num]
        if not match.empty:
            reg = match.iloc[0]
            try:
                st.session_state['in_data'] = datetime.strptime(str(reg['Data_Str']), "%d/%m/%Y").date()
            except:
                st.session_state['in_data'] = datetime.today().date()
            st.session_state['in_hora'] = str(reg['Horario_Str']) if str(reg['Horario_Str']) in horarios_opcoes else "21:30"
            st.session_state['in_humor'] = int(reg['Humor_Val']) if reg['Humor_Val'] != "" else 0
            st.session_state['in_ans'] = int(reg['Ansiedade_Val']) if reg['Ansiedade_Val'] != "" else 0
            st.session_state['in_irr'] = int(reg['Irritabilidade_Val']) if reg['Irritabilidade_Val'] != "" else 0
            st.session_state['in_sono'] = float(reg['Sono']) if reg['Sono'] != "" else 8.0
            st.session_state['in_sex'] = int(reg['Sexo_Val']) if reg['Sexo_Val'] != "" else 0
            st.session_state['in_fis'] = [x.strip() for x in str(reg['Condicao_Fisica']).split(",") if x.strip()]
            st.session_state['in_soc'] = int(reg['Social_Val']) if reg['Social_Val'] != "" else 0
            st.session_state['in_gat'] = [x.strip() for x in str(reg['Gatilhos']).split(",") if x.strip()]
            st.session_state['in_esq'] = int(reg['Esquizofrenia_Val']) if reg['Esquizofrenia_Val'] != "" else 0
            st.session_state['in_not'] = str(reg['Notas'])
    else:
        st.session_state['in_data'] = datetime.today().date()
        st.session_state['in_hora'] = "21:30"
        st.session_state['in_humor'] = 0
        st.session_state['in_ans'] = 0
        st.session_state['in_irr'] = 0
        st.session_state['in_sono'] = 8.0
        st.session_state['in_sex'] = 0
        st.session_state['in_fis'] = []
        st.session_state['in_soc'] = 0
        st.session_state['in_gat'] = []
        st.session_state['in_esq'] = 0
        st.session_state['in_not'] = ""

st.markdown("<h1 style='text-align: center;'>Afetivograma - Claudia Feigel</h1>", unsafe_allow_html=True)
st.write("")

# --- INTERFACE DE ENTRADA ---
col_id, col_dt, col_hr, _ = st.columns([3, 2, 2, 5])
with col_id:
    st.selectbox("Registro (ID)", options=opcoes_id, key="in_id_sel", on_change=carregar_registro_callback)
with col_dt:
    st.date_input("Data", key="in_data", format="DD/MM/YYYY")
with col_hr:
    st.selectbox("Horário", options=horarios_opcoes, key="in_hora")

st.write("") 

col_h, col_a, col_i, col_s, col_x, col_f, _ = st.columns([2, 2, 2, 1.5, 1.5, 2, 1.5])
with col_h:
    st.selectbox("Humor", options=list(niveis_humor.keys()), format_func=lambda x: niveis_humor[x], key="in_humor") 
with col_a:
    st.selectbox("Ansiedade", options=list(niveis_ansiedade.keys()), format_func=lambda x: niveis_ansiedade[x], key="in_ans")
with col_i:
    st.selectbox("Irritabilidade", options=list(niveis_irritabilidade.keys()), format_func=lambda x: niveis_irritabilidade[x], key="in_irr")
with col_s:
    st.number_input("Sono", min_value=0.0, max_value=24.0, step=0.5, format="%.1f", key="in_sono")
with col_x:
    st.selectbox("Ativ. Sexual", options=list(niveis_sexo.keys()), format_func=lambda x: niveis_sexo[x], key="in_sex")
with col_f:
    opcoes_fisico = ["Enxaqueca", "Herpes", "Fadiga/Cansaço", "Dores no corpo"]
    st.multiselect("Condições Físicas", options=opcoes_fisico, placeholder="Escolha...", key="in_fis")

st.write("") 

col_soc, col_gat, col_esq, col_not = st.columns([2, 3, 3, 5])
with col_soc:
    st.selectbox("Sociedade", options=list(niveis_sociedade.keys()), format_func=lambda x: niveis_sociedade[x], key="in_soc")
with col_gat:
    opcoes_gatilhos = ["Expectativas sobre eventos", "Interação negativa com filha ou outros", "Frustração com tarefas", "Notícia triste", "Alteração no clima", "Esquecimento", "Incapacidade"]
    st.multiselect("Gatilhos", options=opcoes_gatilhos, placeholder="Escolha...", key="in_gat")
with col_esq:
    st.selectbox("Delírios/Psicose", options=list(niveis_esquizofrenia.keys()), format_func=lambda x: niveis_esquizofrenia[x], key="in_esq")
with col_not:
    st.text_input("Anotações Livres", placeholder="Pressione Enter para confirmar o texto...", key="in_not")

st.write("")
is_novo = st.session_state['in_id_sel'] == "[ + ] Novo Registro"
texto_botao = "Salvar Registro" if is_novo else f"Salvar Alterações no {st.session_state['in_id_sel']}"
salvar = st.button(texto_botao, width='stretch')

# --- LÓGICA DE SALVAMENTO ---
if salvar:
    if is_novo:
        novo_id = pd.to_numeric(df_historico['ID'], errors='coerce').max() + 1 if not df_historico.empty else 1
        if pd.isnull(novo_id): novo_id = 1
    else:
        novo_id = opcoes_id_dict[st.session_state['in_id_sel']]
        df_historico = df_historico[df_historico['ID'] != novo_id]
    
    novo_dado = pd.DataFrame({
        'ID': [int(novo_id)],
        'Data_Str': [st.session_state['in_data'].strftime("%d/%m/%Y")],
        'Horario_Str': [st.session_state['in_hora']],
        'Humor_Val': [st.session_state['in_humor']],
        'Humor_Desc': [niveis_humor[st.session_state['in_humor']]],
        'Ansiedade_Val': [st.session_state['in_ans']],
        'Ansiedade_Desc': [niveis_ansiedade[st.session_state['in_ans']]],
        'Irritabilidade_Val': [st.session_state['in_irr']],
        'Irritabilidade_Desc': [niveis_irritabilidade[st.session_state['in_irr']]],
        'Sono': [st.session_state['in_sono']],
        'Sexo_Val': [st.session_state['in_sex']],
        'Condicao_Fisica': [", ".join(st.session_state['in_fis']) if st.session_state['in_fis'] else ""],
        'Social_Val': [st.session_state['in_soc']],
        'Social_Desc': [niveis_sociedade[st.session_state['in_soc']]],
        'Esquizofrenia_Val': [st.session_state['in_esq']],
        'Esquizofrenia_Clinico': [esquizofrenia_clinico[st.session_state['in_esq']]],
        'Gatilhos': [", ".join(st.session_state['in_gat']) if st.session_state['in_gat'] else ""],
        'Notas': [st.session_state['in_not']]
    })
    
    df_historico = pd.concat([df_historico, novo_dado], ignore_index=True).fillna("")
    salvar_dados_no_sheets(df_historico)
    
    chaves_para_limpar = [
        'in_id_sel', 'in_data', 'in_hora', 'in_humor', 'in_ans', 
        'in_irr', 'in_sono', 'in_sex', 'in_fis', 'in_soc', 
        'in_gat', 'in_esq', 'in_not'
    ]
    for key in chaves_para_limpar:
        if key in st.session_state:
            del st.session_state[key]
            
    st.rerun()

# --- CONSTRUÇÃO DO GRÁFICO (PLOTLY) ---
st.divider()

if not df_historico.empty:
    df_historico['DataHora_Real'] = pd.to_datetime(df_historico['Data_Str'] + ' ' + df_historico['Horario_Str'], format="%d/%m/%Y %H:%M", errors='coerce')
    df_historico = df_historico.dropna(subset=['DataHora_Real']).sort_values(by='DataHora_Real').reset_index(drop=True)
    df_historico['Sono_Vis'] = df_historico['Sono'].apply(lambda x: f"{int(x)}h{int((x % 1) * 60):02d}m".replace("h00m", "h") if pd.notnull(x) and x != "" else "")

    col_f1, col_f2 = st.columns([5, 4])
    with col_f1:
        filtro_tempo = st.radio("Período de Visualização:", ["Semanal (Dom-Sáb)", "Quinzenal", "Mensal", "Todos"], index=3, horizontal=True)

    df_plot = df_historico.copy()

    if not df_plot.empty:
        if filtro_tempo == "Semanal (Dom-Sáb)":
            df_plot['Semana_Inicio'] = df_plot['DataHora_Real'].apply(lambda d: (d - timedelta(days=(d.weekday() + 1) % 7)).replace(hour=0, minute=0, second=0))
            semanas_unicas = sorted(df_plot['Semana_Inicio'].unique(), reverse=True)
            
            opcoes_semana = {}
            for sem in semanas_unicas:
                fim_sem = sem + timedelta(days=6, hours=23, minutes=59)
                lbl = f"Semana: {sem.strftime('%d/%m/%Y')} a {fim_sem.strftime('%d/%m/%Y')}"
                opcoes_semana[lbl] = sem

            with col_f2:
                sel_sem = st.selectbox("Selecione a Semana:", options=list(opcoes_semana.keys()))
            
            sem_ini = opcoes_semana[sel_sem]
            sem_fim = sem_ini + timedelta(days=6, hours=23, minutes=59)
            df_plot = df_plot[(df_plot['DataHora_Real'] >= sem_ini) & (df_plot['DataHora_Real'] <= sem_fim)]

        elif filtro_tempo == "Quinzenal":
            def get_quinzena_tuple(d):
                q = 1 if d.day <= 15 else 2
                return (d.year, d.month, q, f"{q}ª Quinzena de {d.strftime('%m/%Y')}")

            q_raw = df_plot['DataHora_Real'].apply(get_quinzena_tuple).unique()
            q_sorted = sorted(q_raw, key=lambda x: (x[0], x[1], x[2]), reverse=True)
            opcoes_quinzena = {x[3]: (x[0], x[1], x[2]) for x in q_sorted}

            with col_f2:
                sel_q = st.selectbox("Selecione a Quinzena:", options=list(opcoes_quinzena.keys()))

            ano, mes, q_num = opcoes_quinzena[sel_q]
            if q_num == 1:
                df_plot = df_plot[(df_plot['DataHora_Real'].dt.year == ano) & (df_plot['DataHora_Real'].dt.month == mes) & (df_plot['DataHora_Real'].dt.day <= 15)]
            else:
                df_plot = df_plot[(df_plot['DataHora_Real'].dt.year == ano) & (df_plot['DataHora_Real'].dt.month == mes) & (df_plot['DataHora_Real'].dt.day > 15)]

        elif filtro_tempo == "Mensal":
            m_raw = df_plot['DataHora_Real'].apply(lambda d: (d.year, d.month, d.strftime('%m/%Y'))).unique()
            m_sorted = sorted(m_raw, key=lambda x: (x[0], x[1]), reverse=True)
            opcoes_mes = {x[2]: (x[0], x[1]) for x in m_sorted}

            with col_f2:
                sel_m = st.selectbox("Selecione o Mês:", options=list(opcoes_mes.keys()))

            ano, mes = opcoes_mes[sel_m]
            df_plot = df_plot[(df_plot['DataHora_Real'].dt.year == ano) & (df_plot['DataHora_Real'].dt.month == mes)]

    fig = go.Figure()

    if not df_plot.empty:
        for dt_reg in df_plot['DataHora_Real']:
            fig.add_vline(x=dt_reg, line_width=1, line_dash="dot", line_color="#555555")

        fig.add_trace(go.Scatter(x=df_plot['DataHora_Real'], y=df_plot['Humor_Val'], name="Humor", customdata=df_plot['Humor_Desc'], mode='lines+markers', line_shape='spline', line=dict(color="#3498DB", width=3), marker=dict(size=9), hovertemplate="<b>Humor:</b> %{customdata}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df_plot['DataHora_Real'], y=df_plot['Ansiedade_Val'], name="Ansiedade", customdata=df_plot['Ansiedade_Desc'], mode='lines+markers', line_shape='spline', line=dict(color="#E67E22", width=2), hovertemplate="<b>Ansiedade:</b> %{customdata}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df_plot['DataHora_Real'], y=df_plot['Irritabilidade_Val'], name="Irritabilidade", customdata=df_plot['Irritabilidade_Desc'], mode='lines+markers', line_shape='spline', line=dict(color="#FF1493", width=2), hovertemplate="<b>Irritabilidade:</b> %{customdata}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df_plot['DataHora_Real'], y=df_plot['Social_Val'], name="Sociedade", customdata=df_plot['Social_Desc'], mode='lines+markers', line_shape='spline', line=dict(color="#00FFFF", width=2), hovertemplate="<b>Sociedade:</b> %{customdata}<extra></extra>"))
        fig.add_trace(go.Scatter(x=df_plot['DataHora_Real'], y=df_plot['Esquizofrenia_Val'], name="Delírios", customdata=df_plot['Esquizofrenia_Clinico'], mode='lines+markers', line_shape='spline', line=dict(color="#9B59B6", width=2), hovertemplate="<b>Delírios/Psicose:</b> %{customdata}<extra></extra>"))

        fig.add_trace(go.Scatter(x=df_plot['DataHora_Real'], y=[-3.6] * len(df_plot), name="Sono", text=df_plot['Sono_Vis'], mode='text', textposition='top center', textfont=dict(color="#2ECC71", size=11), hovertemplate="<b>Horas de Sono:</b> %{text}<extra></extra>"))

        df_sexo = df_plot[df_plot['Sexo_Val'] == 1]
        if not df_sexo.empty:
            fig.add_trace(go.Scatter(x=df_sexo['DataHora_Real'], y=[-4.2] * len(df_sexo), name="Sexo", mode='markers', marker=dict(symbol='square', color='#F1C40F', size=9), hovertemplate="<b>Atividade Sexual:</b> Sim<extra></extra>"))

        df_dor = df_plot[df_plot['Condicao_Fisica'].astype(str) != ""]
        if not df_dor.empty:
            fig.add_trace(go.Scatter(x=df_dor['DataHora_Real'], y=[-4.8] * len(df_dor), name="Dor / Físico", customdata=df_dor['Condicao_Fisica'], mode='markers', marker=dict(symbol='square', color='#E74C3C', size=9), hovertemplate="<b>Condição Física:</b> %{customdata}<extra></extra>"))

        df_notas = df_plot[(df_plot['Notas'].astype(str) != "") | (df_plot['Gatilhos'].astype(str) != "")].copy()
        if not df_notas.empty:
            df_notas['Hover_Notas'] = "Anotação: " + df_notas['Notas'].astype(str) + "<br>Gatilhos: " + df_notas['Gatilhos'].astype(str)
            fig.add_trace(go.Scatter(x=df_notas['DataHora_Real'], y=[-5.4] * len(df_notas), name="Anotações / Gatilhos", customdata=df_notas['Hover_Notas'], mode='markers', marker=dict(symbol='star', color='white', size=11), hovertemplate="<b>%{customdata}</b><extra></extra>"))

    fig.update_layout(
        plot_bgcolor='#111111', paper_bgcolor='#111111', font=dict(color='white'),
        hovermode="x unified", legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=20, b=20)
    )
    
    fig.update_xaxes(
        showgrid=False,
        tickmode='array',
        tickvals=df_plot['DataHora_Real'] if not df_plot.empty else [],
        ticktext=df_plot['DataHora_Real'].dt.strftime("%d/%m\n%H:%M") if not df_plot.empty else []
    )
    
    fig.update_yaxes(
        title_text="Evolução",
        range=[-6.0, 3.8],
        tickvals=[-3, -2, -1, 0, 1, 2, 3],
        showgrid=True,
        gridcolor='#222222',
        gridwidth=1
    )

    st.plotly_chart(fig, width='stretch')

    col_dl1, col_dl2 = st.columns([2, 10])
    with col_dl1:
        output_xlsx = BytesIO()
        df_historico.drop(columns=['DataHora_Real', 'Sono_Vis'], errors='ignore').to_excel(output_xlsx, index=False, engine='openpyxl')
        st.download_button("📥 Baixar Tabela (.xlsx)", data=output_xlsx.getvalue(), file_name="afetivograma_dados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col_dl2:
        html_grafico = fig.to_html(full_html=True, include_plotlyjs='cdn')
        st.download_button("📉 Baixar Gráfico (.html)", data=html_grafico, file_name="afetivograma_grafico.html", mime="text/html")

else:
    st.info("Registre o primeiro dado para visualizar a evolução.")
