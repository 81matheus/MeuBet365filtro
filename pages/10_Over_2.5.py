import streamlit as st
import pandas as pd
import io
import re
import numpy as np
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard de Análise de Apostas")

# --- Funções de Processamento de Dados ---

@st.cache_data
def preprocess_user_data(df):
    """
    Processa a planilha do usuário, adaptando-se de forma inteligente a diferentes formatos de dados.
    """
    try:
        # 1. Normaliza cabeçalhos e renomeia colunas essenciais
        df.columns = [str(col).strip().upper() for col in df.columns]
        df = df.rename(columns={'EQUIPA CASA': 'HOME', 'EQUIPA VISITANTE': 'AWAY'})

        # 2. Lógica Inteligente para obter placares
        # Cenário A: Colunas já estão separadas
        if all(col in df.columns for col in ['RESULTADO FT CASA', 'RESULTADO FT FORA']):
            df = df.rename(columns={
                'RESULTADO HT CASA': 'GOALS_H_HT', 'RESULTADO HT FORA': 'GOALS_A_HT',
                'RESULTADO FT CASA': 'GOALS_H_FT', 'RESULTADO FT FORA': 'GOALS_A_FT'
            })
            for col in ['GOALS_H_HT', 'GOALS_A_HT']:
                if col not in df.columns: df[col] = 0
        # Cenário B: Procura por coluna de placar combinado
        else:
            score_col_name = next((col for col in df.columns if df[col].astype(str).str.match(r'^\d+-\d+.*').any()), None)
            if not score_col_name:
                st.error("Não foi possível encontrar colunas de placar.")
                return pd.DataFrame()
            def parse_combined_score(score_str):
                if not isinstance(score_str, str): return [0, 0, 0, 0]
                match = re.match(r'(\d+)-(\d+)\s+(\d+)-(\d+)', score_str)
                if match: return [int(g) for g in match.groups()]
                match_ft_only = re.match(r'(\d+)-(\d+)', score_str)
                if match_ft_only: return [0, 0, int(match_ft_only.group(1)), int(match_ft_only.group(2))]
                return [0, 0, 0, 0]
            scores = df[score_col_name].apply(parse_combined_score)
            df[['GOALS_H_HT', 'GOALS_A_HT', 'GOALS_H_FT', 'GOALS_A_FT']] = pd.DataFrame(scores.tolist(), index=df.index)

        # 3. Limpeza final e conversão de tipos
        for col in ['HOME', 'AWAY', 'LIGA']:
            if col not in df.columns: df[col] = 'N/A'
        for col in ['GOALS_H_HT', 'GOALS_A_HT', 'GOALS_H_FT', 'GOALS_A_FT']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        def robust_date_parser(date_val):
            if isinstance(date_val, (int, float)):
                try: return pd.to_datetime('1899-12-30') + pd.to_timedelta(date_val, 'D')
                except: return pd.NaT
            try: return pd.to_datetime(date_val, dayfirst=True, errors='coerce')
            except: return pd.NaT
        df['DATE'] = df['DATA'].apply(robust_date_parser).dropna()
        df = df.sort_values(by='DATE').reset_index(drop=True)

        # 4. DERIVAÇÃO INTELIGENTE DE MERCADOS (SÓ CRIA SE NÃO EXISTIR)
        df['TOTAL_GOALS_FT'] = df['GOALS_H_FT'] + df['GOALS_A_FT']
        df['TOTAL_GOALS_HT'] = df['GOALS_H_HT'] + df['GOALS_A_HT']
        df['GOALS_2T'] = df['TOTAL_GOALS_FT'] - df['TOTAL_GOALS_HT']
        
        # Resultado Final
        if 'CASA' not in df.columns: df['CASA'] = np.where(df['GOALS_H_FT'] > df['GOALS_A_FT'], 'SIM', 'NÃO')
        if 'EMPATE' not in df.columns: df['EMPATE'] = np.where(df['GOALS_H_FT'] == df['GOALS_A_FT'], 'SIM', 'NÃO')
        if 'VISITANTE' not in df.columns: df['VISITANTE'] = np.where(df['GOALS_H_FT'] < df['GOALS_A_FT'], 'SIM', 'NÃO')
        
        # Resultado ao Intervalo
        if 'CASA_VENCE_HT' not in df.columns: df['CASA_VENCE_HT'] = df['GOALS_H_HT'] > df['GOALS_A_HT']
        if 'VISITANTE_VENCE_HT' not in df.columns: df['VISITANTE_VENCE_HT'] = df['GOALS_H_HT'] < df['GOALS_A_HT']

        # Mercados de Gols
        market_list = {
            'Mais de 0,5 HT': ('TOTAL_GOALS_HT', '>', 0.5), 'Menos de 1,5 HT': ('TOTAL_GOALS_HT', '<', 1.5),
            'Mais de 0,5 ft': ('TOTAL_GOALS_FT', '>', 0.5), 'Mais de 1,5': ('TOTAL_GOALS_FT', '>', 1.5),
            'Menos de 1,5': ('TOTAL_GOALS_FT', '<', 1.5), 'Mais de 2,5': ('TOTAL_GOALS_FT', '>', 2.5),
            'Menos de 2,5': ('TOTAL_GOALS_FT', '<', 2.5), 'Mais de 3,5': ('TOTAL_GOALS_FT', '>', 3.5),
            'Menos de 3,5': ('TOTAL_GOALS_FT', '<', 3.5), 'Menos de 4,5': ('TOTAL_GOALS_FT', '<', 4.5),
            'Menos de 6,5': ('TOTAL_GOALS_FT', '<', 6.5)
        }
        for market, (col, op, val) in market_list.items():
            if market.upper() not in df.columns: # Converte para upper para comparar
                if op == '>': df[market] = np.where(df[col] > val, 'SIM', 'NÃO')
                else: df[market] = np.where(df[col] < val, 'SIM', 'NÃO')

        # Cenários Específicos
        if 'CASA_ABRIU_2x0_HT' not in df.columns: df['CASA_ABRIU_2x0_HT'] = (df['GOALS_H_HT'] == 2) & (df['GOALS_A_HT'] == 0)
        if 'FORA_ABRIU_0x2_HT' not in df.columns: df['FORA_ABRIU_0x2_HT'] = (df['GOALS_H_HT'] == 0) & (df['GOALS_A_HT'] == 2)

        st.success("Planilha processada com sucesso!")
        return df
    except Exception as e:
        st.error(f"Ocorreu um erro crítico ao processar sua planilha: {e}. Verifique se o arquivo não está corrompido.")
        return pd.DataFrame()

# --- Funções de Análise ---
def analyze_correct_score_table(df):
    if df.empty: return pd.DataFrame()
    df['CS'] = df['GOALS_H_FT'].astype(str) + 'x' + df['GOALS_A_FT'].astype(str)
    cs_counts = df['CS'].value_counts().reset_index()
    cs_counts.columns = ['Placar Exato', 'Acertos']
    total_entries = len(df)
    cs_counts['Entradas'] = total_entries
    cs_counts['Taxa de Acerto (%)'] = (cs_counts['Acertos'] / total_entries) * 100
    return cs_counts[['Placar Exato', 'Entradas', 'Acertos', 'Taxa de Acerto (%)']].sort_values(by='Acertos', ascending=False)

def analyze_scenarios(df):
    scenarios = {}
    df_tied_ht = df[df['GOALS_H_HT'] == df['GOALS_A_HT']]
    if not df_tied_ht.empty:
        scenarios['tied_at_ht'] = {
            'total_cases': len(df_tied_ht),
            'home_win_rate': (df['CASA'] == 'SIM')[df['GOALS_H_HT'] == df['GOALS_A_HT']].mean() * 100,
            'away_win_rate': (df['VISITANTE'] == 'SIM')[df['GOALS_H_HT'] == df['GOALS_A_HT']].mean() * 100
        }
    
    df_casa_2x0 = df[df['CASA_ABRIU_2x0_HT']]
    if not df_casa_2x0.empty:
        scenarios['casa_2x0_lead'] = {
            'total_cases': len(df_casa_2x0),
            'final_win_rate': (df_casa_2x0['CASA'] == 'SIM').mean() * 100
        }
        
    df_fora_0x2 = df[df['FORA_ABRIU_0x2_HT']]
    if not df_fora_0x2.empty:
        scenarios['fora_0x2_lead'] = {
            'total_cases': len(df_fora_0x2),
            'final_win_rate': (df_fora_0x2['VISITANTE'] == 'SIM').mean() * 100
        }

    return scenarios

# --- Interface Principal do Streamlit ---
st.title("BetAnalyzer Pro 📊 - Dashboard de Análise de Dados")

st.sidebar.header("Fonte de Dados")
uploaded_file = st.sidebar.file_uploader("Carregue sua planilha (.xlsx, .xls)", type=['xlsx', 'xls'])

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

if uploaded_file is not None:
    with st.spinner("Lendo e processando sua planilha..."):
        engine = 'openpyxl' if uploaded_file.name.endswith('xlsx') else 'xlrd'
        try:
            df_user = pd.read_excel(uploaded_file, engine=engine)
            st.session_state.df = preprocess_user_data(df_user)
        except Exception as e:
            st.error(f"Não foi possível ler o arquivo. Pode estar corrompido ou num formato inesperado. Erro: {e}")
            st.session_state.df = pd.DataFrame()

if not st.session_state.df.empty:
    df = st.session_state.df
    
    st.sidebar.header("Filtros Gerais")
    leagues = ['Todas'] + sorted(df['LIGA'].unique().tolist())
    selected_league = st.sidebar.selectbox("Filtrar por Liga", leagues)
    
    filtered_df = df.copy()
    if selected_league != 'Todas':
        filtered_df = filtered_df[filtered_df['LIGA'] == selected_league]

    st.success(f"Análise baseada em **{len(filtered_df)}** jogos.")
    
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard Geral", "📈 Análise de Cenários", "🎯 Placar Exato (CS)"])

    with tab1:
        st.header("Dashboard Geral de Tendências")
        
        st.markdown("<h4 style='color: #54a0ff;'>🏁 Resultados Finais (FT)</h4>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        col1.metric("Vitórias equipa Casa", f"{(filtered_df['CASA'] == 'SIM').mean()*100:.2f}%")
        col2.metric("Empates", f"{(filtered_df['EMPATE'] == 'SIM').mean()*100:.2f}%")
        col3.metric("Vitórias equipa Fora", f"{(filtered_df['VISITANTE'] == 'SIM').mean()*100:.2f}%")
        
        st.markdown("<h4 style='color: #54a0ff;'>⏱️ Resultados ao Intervalo (HT)</h4>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        col1.metric("Vitórias equipa Casa em HT", f"{filtered_df['CASA_VENCE_HT'].mean()*100:.2f}%")
        col2.metric("Vitórias equipa Fora em HT", f"{filtered_df['VISITANTE_VENCE_HT'].mean()*100:.2f}%")

        st.markdown("<h4 style='color: #54a0ff;'>⚽ Mercados de Gols (Over/Under)</h4>", unsafe_allow_html=True)
        markets_to_display = [
            'Mais de 0,5 HT', 'Mais de 0,5 ft', 'Mais de 1,5', 'Mais de 2,5', 'Mais de 3,5',
            'Menos de 1,5 HT', 'Menos de 1,5', 'Menos de 2,5', 'Menos de 3,5', 'Menos de 4,5', 'Menos de 6,5'
        ]
        
        num_cols = 4
        cols = st.columns(num_cols)
        for i, market_name in enumerate(markets_to_display):
            if market_name in filtered_df.columns:
                rate = (filtered_df[market_name] == 'SIM').mean() * 100
                cols[i % num_cols].metric(market_name, f"{rate:.2f}%")
            
    with tab2:
        st.header("Análise de Cenários de Jogo")
        scenarios = analyze_scenarios(filtered_df)

        st.subheader("Cenário: Jogo Empatado no Intervalo (HT)")
        if 'tied_at_ht' in scenarios:
            scenario = scenarios['tied_at_ht']
            c1, c2, c3 = st.columns(3)
            c1.metric("Nº de Jogos Empatados no HT", f"{scenario['total_cases']}")
            c2.metric("Casa Venceu no Final", f"{scenario['home_win_rate']:.2f}%", help="Dos jogos empatados no HT, em quantos a casa venceu no final.")
            c3.metric("Visitante Venceu no Final", f"{scenario['away_win_rate']:.2f}%", help="Dos jogos empatados no HT, em quantos o visitante venceu no final.")
        else: st.info("Não há jogos empatados no intervalo para analisar.")

        st.markdown("---")
        
        st.subheader("Cenário: Liderança Segura?")
        c1, c2 = st.columns(2)
        with c1:
            if 'casa_2x0_lead' in scenarios:
                scenario = scenarios['casa_2x0_lead']
                st.metric(f"Nº Jogos Casa abriu 2-0 HT", f"{scenario['total_cases']}")
                st.metric("Taxa de Vitória Final", f"{scenario['final_win_rate']:.2f}%", help="Das vezes que a casa fez 2-0 no HT, em quantas ela ganhou o jogo.")
            else: st.info("Nenhum jogo onde a casa abriu 2-0 no HT.")
        with c2:
            if 'fora_0x2_lead' in scenarios:
                scenario = scenarios['fora_0x2_lead']
                st.metric("Nº Jogos Fora abriu 0-2 HT", f"{scenario['total_cases']}")
                st.metric("Taxa de Vitória Final", f"{scenario['final_win_rate']:.2f}%", help="Das vezes que o visitante fez 0-2 no HT, em quantas ele ganhou o jogo.")
            else: st.info("Nenhum jogo onde o visitante abriu 0-2 no HT.")
            
    with tab3:
        st.header("Desempenho do Placar Exato (Correct Score)")
        cs_df = analyze_correct_score_table(filtered_df)
        if not cs_df.empty:
            st.dataframe(
                cs_df.style.format({'Taxa de Acerto (%)': '{:.2f}%'}).bar(subset=['Acertos'], color='#2e86de', align='zero'),
                use_container_width=True,
                height=600 
            )
        else:
            st.warning("Não foi possível gerar a tabela de placares.")
else:
    st.info("👋 Bem-vindo ao BetAnalyzer Pro! Por favor, carregue sua planilha na barra lateral para começar.")
