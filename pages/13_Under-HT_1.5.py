import streamlit as st
import pandas as pd
import requests
import io
import ast
import re
import numpy as np

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="BetAnalyzer Pro - Análise e Backtesting")

# --- Mapeamento de Mercados e Odds (para a base de dados padrão) ---
# Este mapeamento é usado principalmente com a base de dados do GitHub, que tem odds detalhadas.
# A ferramenta se adaptará se a planilha do usuário não tiver todas essas colunas.
MARKET_TO_ODDS_MAPPING = {
    "Resultado Final (1X2 FT)": {
        "Vitória Casa (FT)": "Odd_H_FT", "Empate (FT)": "Odd_D_FT", "Vitória Visitante (FT)": "Odd_A_FT",
    },
    "Mais/Menos Gols (FT)": {
        "Mais de 0.5 Gols FT": "Odd_Over05_FT", "Menos de 0.5 Gols FT": "Odd_Under05_FT",
        "Mais de 1.5 Gols FT": "Odd_Over15_FT", "Menos de 1.5 Gols FT": "Odd_Under15_FT",
        "Mais de 2.5 Gols FT": "Odd_Over25_FT", "Menos de 2.5 Gols FT": "Odd_Under25_FT",
        "Mais de 3.5 Gols FT": "Odd_Over35_FT", "Menos de 3.5 Gols FT": "Odd_Under35_FT",
        "Mais de 4.5 Gols FT": "Odd_Over45_FT", "Menos de 4.5 Gols FT": "Odd_Under45_FT",
    },
    "Ambas Marcam (BTTS)": {
        "Sim (BTTS Yes)": "Odd_BTTS_Yes", "Não (BTTS No)": "Odd_BTTS_No",
    }
}
# Lista simplificada para a planilha do usuário, que será preenchida dinamicamente
SIMPLE_MARKET_LIST = ['CASA', 'EMPATE', 'VISITANTE', 'OVER 0.5HT', 'OVER 0.5FT', 'OVER 1.5FT', 'OVER 2.5FT', 'BTTS SIM']


# --- Funções de Carregamento e Processamento de Dados ---

@st.cache_data
def load_default_data(url):
    """Carrega a base de dados padrão do GitHub."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        excel_file = io.BytesIO(response.content)
        df = pd.read_excel(excel_file)
        # Processamento específico para a base padrão
        df['Date'] = pd.to_datetime(df['Date'])
        for col in df.columns:
            if 'Odd' in col:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            if 'Goals' in col and 'Min' not in col:
                 df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        def parse_goal_minutes(minute_str):
            if pd.isna(minute_str) or not isinstance(minute_str, str) or minute_str.strip() == '[]': return []
            try:
                return [int(item) for item in ast.literal_eval(minute_str) if str(item).isdigit()]
            except (ValueError, SyntaxError): return []
        
        df['Goals_Min_H_Parsed'] = df['Goals_Min_H'].apply(parse_goal_minutes)
        df['Goals_Min_A_Parsed'] = df['Goals_Min_A'].apply(parse_goal_minutes)
        df = df.sort_values(by='Date').reset_index(drop=True)
        return df, True
    except Exception as e:
        st.error(f"Erro ao carregar a base de dados padrão: {e}")
        return pd.DataFrame(), False

def preprocess_user_data(df):
    """Processa a planilha enviada pelo usuário para torná-la compatível."""
    try:
        # 1. Normalizar nomes das colunas (MAIÚSCULAS, SEM ESPAÇOS)
        df.columns = [str(col).strip().upper() for col in df.columns]

        # 2. Identificar e renomear colunas essenciais
        rename_map = {
            'EQUIPA CASA': 'HOME', 'EQUIPA VISITANTE': 'AWAY',
            'RESULTADO HT CASA': 'GOALS_H_HT', 'RESULTADO HT FORA': 'GOALS_A_HT',
            'RESULTADO FT CASA': 'GOALS_H_FT', 'RESULTADO FT FORA': 'GOALS_A_FT',
        }
        df = df.rename(columns=rename_map)
        
        # 3. Converter colunas de gols para número
        for col in ['GOALS_H_HT', 'GOALS_A_HT', 'GOALS_H_FT', 'GOALS_A_FT']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # 4. Criar colunas de resultados e totais
        df['TOTAL_GOALS_FT'] = df['GOALS_H_FT'] + df['GOALS_A_FT']
        df['TOTAL_GOALS_HT'] = df['GOALS_H_HT'] + df['GOALS_A_HT']
        
        # 5. DERIVAR as colunas de resultado (SIM/NÃO)
        df['CASA'] = np.where(df['GOALS_H_FT'] > df['GOALS_A_FT'], 'SIM', 'NÃO')
        df['EMPATE'] = np.where(df['GOALS_H_FT'] == df['GOALS_A_FT'], 'SIM', 'NÃO')
        df['VISITANTE'] = np.where(df['GOALS_H_FT'] < df['GOALS_A_FT'], 'SIM', 'NÃO')
        df['OVER 0.5HT'] = np.where(df['TOTAL_GOALS_HT'] > 0.5, 'SIM', 'NÃO')
        df['OVER 0.5FT'] = np.where(df['TOTAL_GOALS_FT'] > 0.5, 'SIM', 'NÃO')
        df['OVER 1.5FT'] = np.where(df['TOTAL_GOALS_FT'] > 1.5, 'SIM', 'NÃO')
        df['OVER 2.5FT'] = np.where(df['TOTAL_GOALS_FT'] > 2.5, 'SIM', 'NÃO')
        df['BTTS SIM'] = np.where((df['GOALS_H_FT'] > 0) & (df['GOALS_A_FT'] > 0), 'SIM', 'NÃO')

        # 6. DERIVAR as colunas de Correct Score (CS)
        for h in range(6):
            for a in range(6):
                cs_col_name = f'CS {h}x{a}'
                df[cs_col_name] = np.where((df['GOALS_H_FT'] == h) & (df['GOALS_A_FT'] == a), 'SIM', 'NÃO')

        # 7. Limpar e converter ODD
        if 'ODD' in df.columns:
            df['ODD'] = pd.to_numeric(df['ODD'].astype(str).str.replace(',', '.'), errors='coerce')
        else: # Se não houver coluna ODD, cria uma vazia para evitar erros
            df['ODD'] = np.nan

        # 8. Converter coluna de DATA
        # Tenta múltiplos formatos, incluindo o numérico do Excel
        def robust_date_parser(date_val):
            if isinstance(date_val, (int, float)):
                return pd.to_datetime('1899-12-30') + pd.to_timedelta(date_val, 'D')
            try:
                return pd.to_datetime(date_val)
            except (ValueError, TypeError):
                return pd.NaT

        df['DATE'] = df['DATA'].apply(robust_date_parser)
        df = df.dropna(subset=['DATE']).sort_values(by='DATE').reset_index(drop=True)

        st.success("Planilha processada com sucesso!")
        return df, True
    except Exception as e:
        st.error(f"Erro ao processar sua planilha: {e}. Verifique se as colunas principais (DATA, EQUIPA CASA/VISITANTE, RESULTADOS) existem.")
        return pd.DataFrame(), False

# --- Funções de Análise (Backtesting, CS, Gols) ---
def run_backtest_simple(df_filtered, selected_strategy):
    """Executa um backtest simples para planilhas de usuário."""
    if df_filtered.empty:
        return pd.DataFrame(), {}

    results = []
    for _, game in df_filtered.iterrows():
        outcome = game.get(selected_strategy, 'NÃO').upper()
        odd = game.get('ODD', 1.0) # Usa ODD se existir, senão assume 1.0 para não quebrar
        profit = (odd - 1) if outcome == 'SIM' and not pd.isna(odd) else -1.0 if not pd.isna(odd) else 0.0
        
        results.append({
            'Data': game['DATE'],
            'Liga': game.get('LIGA', 'N/A'),
            'Jogo': f"{game.get('HOME', 'N/A')} vs {game.get('AWAY', 'N/A')}",
            'Placar': f"{game['GOALS_H_FT']}-{game['GOALS_A_FT']}",
            'Aposta': selected_strategy,
            'Odd': odd,
            'Resultado': 'WIN' if outcome == 'SIM' else 'LOSS',
            'Lucro': profit
        })
    df_results = pd.DataFrame(results)
    if df_results.empty: return pd.DataFrame(), {}

    df_results['Lucro Acumulado'] = df_results['Lucro'].cumsum()
    
    total_bets = len(df_results)
    wins = len(df_results[df_results['Resultado'] == 'WIN'])
    win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
    net_profit = df_results['Lucro'].sum()
    roi = (net_profit / total_bets) * 100 if total_bets > 0 and total_bets > df_results['Odd'].isna().sum() else 0
    
    metrics = {"total_bets": total_bets, "win_rate": win_rate, "net_profit": net_profit, "roi": roi}
    return df_results, metrics

def analyze_correct_score(df_filtered):
    """Analisa o desempenho das apostas de Placar Exato."""
    cs_cols = [col for col in df_filtered.columns if col.startswith('CS ')]
    if not cs_cols:
        return pd.DataFrame()

    summary = []
    for cs_col in cs_cols:
        wins = df_filtered[df_filtered[cs_col] == 'SIM'].shape[0]
        if wins > 0: # Só mostra placares que ocorreram pelo menos uma vez
            summary.append({
                'Placar Exato': cs_col.replace('CS ', ''),
                'Ocorrências': wins,
                'Frequência (%)': (wins / len(df_filtered)) * 100
            })
    
    if not summary:
        return pd.DataFrame()

    df_summary = pd.DataFrame(summary).sort_values(by='Ocorrências', ascending=False)
    return df_summary

def analyze_goal_timing(df_filtered):
    """Analisa quando e quem marcou o primeiro gol."""
    if 'PRIMEIRO GOLO' not in df_filtered.columns:
        return None, None
        
    casa_primeiro = 0
    visitante_primeiro = 0
    sem_gols_info = 0
    
    bins = {'0-15': 0, '16-30': 0, '31-45+': 0, '46-60': 0, '61-75': 0, '76-90+': 0}
    
    for _, row in df_filtered.iterrows():
        golo_info = row['PRIMEIRO GOLO']
        if pd.isna(golo_info) or golo_info in ['-', '---']:
            sem_gols_info += 1
            continue
            
        if 'casa' in golo_info.lower():
            casa_primeiro += 1
        elif 'visitante' in golo_info.lower():
            visitante_primeiro += 1
            
        minute_match = re.search(r'(\d+)', golo_info)
        if minute_match:
            minute = int(minute_match.group(1))
            if minute <= 15: bins['0-15'] += 1
            elif minute <= 30: bins['16-30'] += 1
            elif minute <= 45: bins['31-45+'] += 1
            elif minute <= 60: bins['46-60'] += 1
            elif minute <= 75: bins['61-75'] += 1
            else: bins['76-90+'] += 1
    
    total_com_info = casa_primeiro + visitante_primeiro
    quem_marcou_summary = {
        'Casa': casa_primeiro,
        'Visitante': visitante_primeiro,
        'Casa (%)': (casa_primeiro / total_com_info * 100) if total_com_info > 0 else 0,
        'Visitante (%)': (visitante_primeiro / total_com_info * 100) if total_com_info > 0 else 0,
        'Jogos sem Info/Gols': sem_gols_info
    }
    
    df_timing = pd.DataFrame(list(bins.items()), columns=['Intervalo (min)', 'Nº de Gols'])
    return quem_marcou_summary, df_timing


# --- Interface Principal do Streamlit ---

st.title("BetAnalyzer Pro 🔬 - Análise e Backtesting de Estratégias")

st.sidebar.image("https://i.imgur.com/V9Lcw00.png", width=50)
st.sidebar.header("Fonte de Dados")
data_source = st.sidebar.radio(
    "Escolha a base de dados para analisar:",
    ('Padrão (GitHub - Odds Detalhadas)', 'Carregar minha Planilha')
)

df = pd.DataFrame()
is_default_db = True

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
    st.session_state.is_default_db = True

if data_source == 'Padrão (GitHub - Odds Detalhadas)':
    with st.spinner("Carregando base de dados padrão..."):
        df, success = load_default_data("https://raw.githubusercontent.com/81matheus/BasedeDadosBet365/main/pagesbet365/Exel-Base_de_Dados_Bet365_FiltradaCompleta.xlsx")
        if success:
            st.session_state.df = df
            st.session_state.is_default_db = True
else:
    uploaded_file = st.sidebar.file_uploader("Carregue sua planilha (.xlsx, .xls)", type=['xlsx', 'xls'])
    if uploaded_file is not None:
        with st.spinner("Lendo e processando sua planilha..."):
            df_user = pd.read_excel(uploaded_file, engine='openpyxl' if uploaded_file.name.endswith('xlsx') else 'xlrd')
            df, success = preprocess_user_data(df_user)
            if success:
                st.session_state.df = df
                st.session_state.is_default_db = False

# --- UI Principal ---
if not st.session_state.df.empty:
    df_to_analyze = st.session_state.df
    
    # Filtros Gerais
    st.sidebar.header("Filtros Gerais")
    leagues = ['Todas'] + sorted(df_to_analyze['LIGA'].unique().tolist())
    selected_league = st.sidebar.selectbox("Filtrar por Liga", leagues)

    min_odd_val = 1.0
    max_odd_val = 20.0
    if 'ODD' in df_to_analyze.columns and not df_to_analyze['ODD'].isna().all():
        min_odd_val = max(1.0, float(df_to_analyze['ODD'].min()))
        max_odd_val = float(df_to_analyze['ODD'].max())

    min_odd_filter, max_odd_filter = st.sidebar.slider(
        "Filtrar por Faixa de Odd", min_odd_val, max_odd_val, (min_odd_val, max_odd_val)
    )

    # Aplica os filtros
    filtered_df = df_to_analyze.copy()
    if selected_league != 'Todas':
        filtered_df = filtered_df[filtered_df['LIGA'] == selected_league]
    if 'ODD' in filtered_df.columns:
        filtered_df = filtered_df[(filtered_df['ODD'] >= min_odd_filter) & (filtered_df['ODD'] <= max_odd_filter)]
    
    st.header("Análise Geral")
    st.info(f"{len(filtered_df)} jogos encontrados com os filtros aplicados.")

    # Abas de Análise
    tab1, tab2, tab3 = st.tabs(["📊 Backtest de Estratégias", "🎯 Placar Exato (Correct Score)", "⏱️ Análise de Gols"])

    with tab1:
        st.subheader("Selecione uma estratégia para o backtest:")
        # O seletor de mercado se adapta à base de dados
        selected_strategy = st.selectbox("Estratégia", SIMPLE_MARKET_LIST, help="Resultados baseados nas colunas SIM/NÃO da sua planilha.")
        
        if st.button("Executar Backtest", key="run_simple_backtest", type="primary"):
            if not filtered_df.empty:
                with st.spinner("Calculando resultados..."):
                    results_df, metrics = run_backtest_simple(filtered_df, selected_strategy)
                    
                    if not results_df.empty:
                        st.markdown(f"#### Resultados para a Estratégia: **{selected_strategy}**")
                        kpi1, kpi2, kpi3 = st.columns(3)
                        kpi1.metric("Total de Apostas", metrics['total_bets'])
                        kpi2.metric("Taxa de Acerto", f"{metrics['win_rate']:.2f}%")
                        kpi3.metric("ROI", f"{metrics['roi']:.2f}%")
                        
                        st.line_chart(results_df, x='Data', y='Lucro Acumulado')
                        
                        with st.expander("Ver jogos do backtest"):
                            st.dataframe(results_df)
                    else:
                        st.warning("Nenhum resultado para exibir.")
            else:
                st.warning("Nenhum jogo corresponde aos filtros para executar o backtest.")

    with tab2:
        st.subheader("Análise de Frequência de Placar Exato")
        if st.button("Analisar Placares", key="run_cs_analysis"):
            with st.spinner("Analisando placares..."):
                cs_summary = analyze_correct_score(filtered_df)
                if not cs_summary.empty:
                    st.bar_chart(cs_summary.head(15).set_index('Placar Exato'), y='Ocorrências')
                    st.dataframe(cs_summary, use_container_width=True)
                else:
                    st.warning("Não foi possível analisar os placares. Verifique se a planilha contém os resultados dos jogos.")

    with tab3:
        st.subheader("Análise de Timing do Primeiro Gol")
        if st.button("Analisar Gols", key="run_goal_analysis"):
            with st.spinner("Analisando gols..."):
                quem_marcou, timing_gols = analyze_goal_timing(filtered_df)
                if quem_marcou:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("##### Quem Marcou Primeiro?")
                        st.metric("Casa", f"{quem_marcou['Casa']} ({quem_marcou['Casa (%)']:.1f}%)")
                        st.metric("Visitante", f"{quem_marcou['Visitante']} ({quem_marcou['Visitante (%)']:.1f}%)")
                        st.caption(f"Jogos sem info/gols: {quem_marcou['Jogos sem Info/Gols']}")
                    with col2:
                        st.markdown("##### Quando Saiu o Primeiro Gol?")
                        st.bar_chart(timing_gols.set_index('Intervalo (min)'), y='Nº de Gols')
                else:
                    st.warning("Coluna 'PRIMEIRO GOLO' não encontrada ou vazia.")

else:
    st.info("Aguardando carregamento de dados. Use a barra lateral para começar.")
