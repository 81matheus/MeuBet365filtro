import streamlit as st
import pandas as pd
import io
import re
import numpy as np
import plotly.express as px

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="BetAnalyzer Pro - Análise de Dados")

# --- Funções de Processamento de Dados ---

def parse_combined_score(score_str):
    """Extrai placares HT e FT de uma string como '1-0 2-1'."""
    if not isinstance(score_str, str):
        return [np.nan] * 4
    
    parts = score_str.replace(' ', '-').split('-')
    if len(parts) == 4:
        return [int(p) if p.isdigit() else np.nan for p in parts]
    
    # Tenta um regex mais robusto para '1-0 2-1' ou '1-0'
    match = re.match(r'(\d+)-(\d+)\s+(\d+)-(\d+)', score_str)
    if match:
        return [int(g) for g in match.groups()]
    
    match_ft_only = re.match(r'(\d+)-(\d+)', score_str)
    if match_ft_only:
         # Se só temos FT, preenchemos HT com NaN para lidar depois
        return [np.nan, np.nan, int(match_ft_only.group(1)), int(match_ft_only.group(2))]
        
    return [np.nan] * 4


@st.cache_data
def preprocess_user_data(df):
    """Processa a planilha do usuário para criar uma base de dados estruturada."""
    try:
        original_cols = df.columns
        # Usa regex para encontrar colunas com placares (HT e FT)
        score_col = next((col for col in original_cols if re.search(r'\d+-\d+\s+\d+-\d+', str(df[col].iloc[0]))), None)
        
        # Se não encontrar, tenta encontrar apenas o placar FT
        if not score_col:
            score_col = next((col for col in original_cols if re.search(r'\d+-\d+', str(df[col].iloc[0]))), None)
            if not score_col:
                 st.error("Não foi possível encontrar uma coluna com o placar (ex: '1-0 2-1' ou '2-1').")
                 return pd.DataFrame()
        
        # Extrai placares
        scores = df[score_col].apply(parse_combined_score)
        df[['GOALS_H_HT', 'GOALS_A_HT', 'GOALS_H_FT', 'GOALS_A_FT']] = pd.DataFrame(scores.tolist(), index=df.index)

        # Identifica e renomeia outras colunas
        df.columns = [str(col).strip().upper() for col in original_cols]
        rename_map = {
            'EQUIPA CASA': 'HOME', 'EQUIPA VISITANTE': 'AWAY'
        }
        df = df.rename(columns=rename_map)
        
        # Limpeza de colunas essenciais
        for col in ['HOME', 'AWAY', 'LIGA']:
            if col not in df.columns: df[col] = 'N/A'
        
        # Converte gols para número, preenchendo NaN com 0
        for col in ['GOALS_H_HT', 'GOALS_A_HT', 'GOALS_H_FT', 'GOALS_A_FT']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        # Converte Data
        def robust_date_parser(date_val):
            if isinstance(date_val, (int, float)):
                return pd.to_datetime('1899-12-30') + pd.to_timedelta(date_val, 'D')
            try: return pd.to_datetime(date_val, dayfirst=True)
            except (ValueError, TypeError): return pd.NaT
        df['DATE'] = df['DATA'].apply(robust_date_parser)
        df = df.dropna(subset=['DATE']).sort_values(by='DATE').reset_index(drop=True)

        # DERIVAÇÃO DE MERCADOS (A MÁGICA ACONTECE AQUI)
        df['TOTAL_GOALS_FT'] = df['GOALS_H_FT'] + df['GOALS_A_FT']
        df['TOTAL_GOALS_HT'] = df['GOALS_H_HT'] + df['GOALS_A_HT']
        df['CASA'] = np.where(df['GOALS_H_FT'] > df['GOALS_A_FT'], 'SIM', 'NÃO')
        df['EMPATE'] = np.where(df['GOALS_H_FT'] == df['GOALS_A_FT'], 'SIM', 'NÃO')
        df['VISITANTE'] = np.where(df['GOALS_H_FT'] < df['GOALS_A_FT'], 'SIM', 'NÃO')
        df['BTTS SIM'] = np.where((df['GOALS_H_FT'] > 0) & (df['GOALS_A_FT'] > 0), 'SIM', 'NÃO')
        
        # Adiciona múltiplos mercados Over/Under
        for i in np.arange(0.5, 7.0, 1.0):
            df[f'OVER {i}FT'] = np.where(df['TOTAL_GOALS_FT'] > i, 'SIM', 'NÃO')
            df[f'UNDER {i}FT'] = np.where(df['TOTAL_GOALS_FT'] < i, 'SIM', 'NÃO')
        for i in np.arange(0.5, 3.0, 1.0):
            df[f'OVER {i}HT'] = np.where(df['TOTAL_GOALS_HT'] > i, 'SIM', 'NÃO')

        st.success("Planilha processada com sucesso!")
        return df
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar sua planilha: {e}. Verifique se a estrutura dos dados está correta.")
        return pd.DataFrame()

# --- Funções de Análise ---

def create_correct_score_matrix(df):
    """Cria uma matriz de calor para a frequência de placares exatos."""
    if df.empty: return None
    cs_crosstab = pd.crosstab(df['GOALS_H_FT'], df['GOALS_A_FT'])
    # Reindex para garantir uma matriz de tamanho razoável (0-5 gols)
    max_goals = max(cs_crosstab.index.max(), cs_crosstab.columns.max(), 5)
    all_indices = np.arange(0, max_goals + 1)
    cs_crosstab = cs_crosstab.reindex(index=all_indices, columns=all_indices, fill_value=0)
    
    fig = px.imshow(cs_crosstab,
                    labels=dict(x="Gols Visitante", y="Gols Casa", color="Nº de Jogos"),
                    x=cs_crosstab.columns, y=cs_crosstab.index,
                    text_auto=True, aspect="auto", color_continuous_scale='Blues')
    fig.update_layout(title_text='Mapa de Calor de Placares Exatos (Correct Score)', title_x=0.5)
    return fig

def analyze_scenario_tied_at_minute(df, minute_mark):
    """Analisa jogos que estavam empatados em um determinado minuto."""
    if 'PRIMEIRO GOLO' not in df.columns: return None
    
    tied_games = []
    for _, row in df.iterrows():
        # Lógica simples para o intervalo, pois não temos a minutagem de todos os gols
        if minute_mark == 45 and row['GOALS_H_HT'] == row['GOALS_A_HT']:
            tied_games.append(row['CASA']) # Adiciona 'SIM' se a casa venceu, 'NÃO' caso contrário
            
    if not tied_games: return None

    total_cases = len(tied_games)
    home_wins = tied_games.count('SIM')
    draws_or_away_wins = total_cases - home_wins
    
    return {
        "total_cases": total_cases,
        "home_wins": home_wins,
        "home_win_rate": (home_wins / total_cases * 100) if total_cases > 0 else 0
    }

def analyze_comebacks(df):
    """Analisa viradas no segundo tempo."""
    # Casa estava perdendo no HT e não perdeu no FT
    home_comeback = df[(df['GOALS_H_HT'] < df['GOALS_A_HT']) & (df['GOALS_H_FT'] >= df['GOALS_A_FT'])].shape[0]
    home_losing_at_ht = df[df['GOALS_H_HT'] < df['GOALS_A_HT']].shape[0]
    
    # Visitante estava perdendo no HT e não perdeu no FT
    away_comeback = df[(df['GOALS_H_HT'] > df['GOALS_A_HT']) & (df['GOALS_H_FT'] <= df['GOALS_A_FT'])].shape[0]
    away_losing_at_ht = df[df['GOALS_H_HT'] > df['GOALS_A_HT']].shape[0]

    return {
        "home_comeback_rate": (home_comeback / home_losing_at_ht * 100) if home_losing_at_ht > 0 else 0,
        "home_total_cases": home_losing_at_ht,
        "away_comeback_rate": (away_comeback / away_losing_at_ht * 100) if away_losing_at_ht > 0 else 0,
        "away_total_cases": away_losing_at_ht
    }


# --- Interface Principal do Streamlit ---

st.title("BetAnalyzer Pro 🔬 - Análise de Dados e Backtesting")

st.sidebar.header("Fonte de Dados")
uploaded_file = st.sidebar.file_uploader("Carregue sua planilha (.xlsx, .xls)", type=['xlsx', 'xls'])

if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()

if uploaded_file is not None:
    with st.spinner("Lendo e processando sua planilha..."):
        # Usa 'openpyxl' para .xlsx e 'xlrd' para o formato antigo .xls
        engine = 'openpyxl' if uploaded_file.name.endswith('xlsx') else 'xlrd'
        df_user = pd.read_excel(uploaded_file, engine=engine)
        st.session_state.df = preprocess_user_data(df_user)

if not st.session_state.df.empty:
    df = st.session_state.df

    # Filtros Gerais na Sidebar
    st.sidebar.header("Filtros Gerais")
    leagues = ['Todas'] + sorted(df['LIGA'].unique().tolist())
    selected_league = st.sidebar.selectbox("Filtrar por Liga", leagues)
    
    filtered_df = df.copy()
    if selected_league != 'Todas':
        filtered_df = filtered_df[filtered_df['LIGA'] == selected_league]

    st.success(f"Análise baseada em **{len(filtered_df)}** jogos.")

    # --- Abas de Análise ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard Geral", " сценаários de Jogo", "🎯 Placar Exato (CS)", "⚙️ Backtesting Detalhado"])

    with tab1:
        st.header("Dashboard Geral de Tendências")
        col1, col2, col3 = st.columns(3)
        col1.metric("Média de Gols (FT)", f"{filtered_df['TOTAL_GOALS_FT'].mean():.2f}")
        col2.metric("Média de Gols (HT)", f"{filtered_df['TOTAL_GOALS_HT'].mean():.2f}")
        btts_rate = (filtered_df['BTTS SIM'] == 'SIM').mean() * 100
        col3.metric("Ambas Marcam (BTTS)", f"{btts_rate:.2f}%")
        
        st.markdown("---")
        
        st.subheader("Análise de Resultados Finais")
        results_counts = filtered_df[['CASA', 'EMPATE', 'VISITANTE']].apply(lambda x: (x == 'SIM').sum())
        results_counts.name = "Ocorrências"
        st.bar_chart(results_counts)

    with tab2:
        st.header("Análise de Cenários de Jogo")
        
        st.subheader("Cenário: Jogo Empatado no Intervalo (HT)")
        ht_tied_scenario = analyze_scenario_tied_at_minute(filtered_df, 45)
        if ht_tied_scenario:
            c1, c2 = st.columns(2)
            c1.metric("Nº de Jogos Empatados no HT", f"{ht_tied_scenario['total_cases']}")
            c2.metric("% de Vitória da Casa no Final", f"{ht_tied_scenario['home_win_rate']:.2f}%", help="Dos jogos empatados no HT, quantos a casa venceu no final.")
        else:
            st.info("Não há dados suficientes para analisar este cenário.")
            
        st.markdown("---")
        
        st.subheader("Análise de 'Comebacks' (Viradas)")
        comeback_data = analyze_comebacks(filtered_df)
        c1, c2 = st.columns(2)
        with c1:
            st.metric(
                "Taxa de Comeback da CASA", f"{comeback_data['home_comeback_rate']:.2f}%",
                help=f"Das {comeback_data['home_total_cases']} vezes que a casa estava perdendo no HT, ela evitou a derrota (empatou ou venceu)."
            )
        with c2:
             st.metric(
                "Taxa de Comeback do VISITANTE", f"{comeback_data['away_comeback_rate']:.2f}%",
                help=f"Das {comeback_data['away_total_cases']} vezes que o visitante estava perdendo no HT, ele evitou a derrota."
            )

    with tab3:
        st.header("Análise de Placar Exato (Correct Score)")
        fig = create_correct_score_matrix(filtered_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Não foi possível gerar a matriz de placares.")

    with tab4:
        st.header("Backtesting de Estratégias Específicas")
        
        all_markets = [col for col in filtered_df.columns if col in ['CASA', 'EMPATE', 'VISITANTE', 'BTTS SIM'] or 'OVER' in col or 'UNDER' in col]
        selected_market = st.selectbox("Escolha o mercado para o backtest:", sorted(all_markets))
        
        if st.button("Executar Backtest da Estratégia", type="primary"):
            wins = (filtered_df[selected_market] == 'SIM').sum()
            total_bets = len(filtered_df)
            win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
            
            st.subheader(f"Resultados para a aposta: '{selected_market}'")
            kpi1, kpi2 = st.columns(2)
            kpi1.metric("Total de Apostas", total_bets)
            kpi2.metric("Taxa de Acerto", f"{win_rate:.2f}%")
            
            if 'ODD' in filtered_df.columns and not filtered_df['ODD'].isna().all():
                # Simulação de lucro se a coluna ODD existir
                lucro = np.where(filtered_df[selected_market] == 'SIM', filtered_df['ODD'] - 1, -1).sum()
                roi = (lucro / total_bets) * 100 if total_bets > 0 else 0
                st.metric("Lucro/Perda Simulado", f"{lucro:.2f} unidades", help="Calculado apenas se a coluna 'ODD' existir e for válida.")
                st.metric("ROI Simulado", f"{roi:.2f}%")

else:
    st.info("👋 Bem-vindo ao BetAnalyzer Pro! Por favor, carregue sua planilha na barra lateral para começar.")
