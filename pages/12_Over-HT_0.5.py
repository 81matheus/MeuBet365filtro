import streamlit as st
import pandas as pd
import requests
import io
import ast
from datetime import datetime
import numpy as np

# --- Configuração da Página e Título ---
st.set_page_config(layout="wide", page_title="BetAnalyzer - Backtesting Profissional")

# --- Mapeamento de Mercados e Odds ---
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
    },
    "Dupla Chance (FT)": {
        "Casa ou Empate (1X)": "Odd_1X", "Casa ou Visitante (12)": "Odd_12", "Empate ou Visitante (X2)": "Odd_X2",
    },
    "Resultado Intervalo (1X2 HT)": {
        "Vitória Casa (HT)": "Odd_H_HT", "Empate (HT)": "Odd_D_HT", "Vitória Visitante (HT)": "Odd_A_HT",
    },
    "Mais/Menos Gols (HT)": {
        "Mais de 0.5 Gols HT": "Odd_Over05_HT", "Menos de 0.5 Gols HT": "Odd_Under05_HT",
        "Mais de 1.5 Gols HT": "Odd_Over15_HT", "Menos de 1.5 Gols HT": "Odd_Under15_HT",
        "Mais de 2.5 Gols HT": "Odd_Over25_HT", "Menos de 2.5 Gols HT": "Odd_Under25_HT",
    },
}

# --- Funções Auxiliares ---

@st.cache_data
def load_data(url):
    """Carrega e pré-processa os dados da URL do GitHub."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        excel_file = io.BytesIO(response.content)
        df = pd.read_excel(excel_file)
        df['Date'] = pd.to_datetime(df['Date'])
        for col in df.columns:
            if 'Odd' in col:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            if 'Goals' in col and 'Min' not in col:
                 df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        # <--- LÓGICA DE PARSING DE MINUTOS DE GOLS MELHORADA --->
        def parse_goal_minutes(minute_str):
            if pd.isna(minute_str) or not isinstance(minute_str, str) or minute_str.strip() == '[]':
                return []
            try:
                # Usa ast.literal_eval para converter a string de lista para uma lista Python
                parsed_list = ast.literal_eval(minute_str)
                # Garante que é uma lista e converte todos os elementos para inteiros
                return [int(item) for item in parsed_list if str(item).isdigit()]
            except (ValueError, SyntaxError):
                return []
        
        df['Goals_Min_H_Parsed'] = df['Goals_Min_H'].apply(parse_goal_minutes)
        df['Goals_Min_A_Parsed'] = df['Goals_Min_A'].apply(parse_goal_minutes)
        
        df['Total_Goals_FT'] = df['Goals_H_FT'] + df['Goals_A_FT']
        df['Total_Goals_HT'] = df['Goals_H_HT'] + df['Goals_A_HT']
        def determine_result_ft(row):
            if row['Goals_H_FT'] > row['Goals_A_FT']: return 'H'
            elif row['Goals_A_FT'] > row['Goals_H_FT']: return 'A'
            else: return 'D'
        df['Result_FT'] = df.apply(determine_result_ft, axis=1)
        def determine_result_ht(row):
            if row['Goals_H_HT'] > row['Goals_A_HT']: return 'H'
            elif row['Goals_A_HT'] > row['Goals_H_HT']: return 'A'
            else: return 'D'
        df['Result_HT'] = df.apply(determine_result_ht, axis=1)
        df['BTTS_Yes_Outcome'] = (df['Goals_H_FT'] > 0) & (df['Goals_A_FT'] > 0)
        df = df.sort_values(by='Date').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar/processar dados: {e}")
        return pd.DataFrame()

# ... (Funções get_team_last_n_games, calculate_avg_goals_scored, calculate_win_rate, determine_bet_outcome, etc... permanecem as mesmas)
def get_team_last_n_games(df_full, team_name, current_game_date, n_games):
    team_games = df_full[((df_full['Home'] == team_name) | (df_full['Away'] == team_name)) & (df_full['Date'] < current_game_date)]
    return team_games.tail(n_games)

def calculate_avg_goals_scored(historical_games, team_name):
    if historical_games.empty: return 0
    goals_scored = 0
    for _, game in historical_games.iterrows():
        if game['Home'] == team_name: goals_scored += game['Goals_H_FT']
        elif game['Away'] == team_name: goals_scored += game['Goals_A_FT']
    return goals_scored / len(historical_games)

def calculate_win_rate(historical_games, team_name):
    if historical_games.empty: return 0
    wins = 0
    for _, game in historical_games.iterrows():
        if game['Home'] == team_name and game['Result_FT'] == 'H': wins += 1
        elif game['Away'] == team_name and game['Result_FT'] == 'A': wins += 1
    return (wins / len(historical_games)) * 100

def determine_bet_outcome(game_row, selected_odd_col_name):
    odd = game_row[selected_odd_col_name]
    if pd.isna(odd): return None, None
    result_status = "LOSS"
    if "Over" in selected_odd_col_name and "FT" in selected_odd_col_name:
        goal_line = float(selected_odd_col_name.split('_')[1].replace('Over', '').replace('FT', '')) / 10
        if game_row['Total_Goals_FT'] > goal_line: result_status = "WIN"
    elif "Under" in selected_odd_col_name and "FT" in selected_odd_col_name:
        goal_line = float(selected_odd_col_name.split('_')[1].replace('Under', '').replace('FT', '')) / 10
        if game_row['Total_Goals_FT'] < goal_line: result_status = "WIN"
    elif "Over" in selected_odd_col_name and "HT" in selected_odd_col_name:
        goal_line = float(selected_odd_col_name.split('_')[1].replace('Over', '').replace('HT', '')) / 10
        if game_row['Total_Goals_HT'] > goal_line: result_status = "WIN"
    elif "Under" in selected_odd_col_name and "HT" in selected_odd_col_name:
        goal_line = float(selected_odd_col_name.split('_')[1].replace('Under', '').replace('HT', '')) / 10
        if game_row['Total_Goals_HT'] < goal_line: result_status = "WIN"
    elif selected_odd_col_name == "Odd_H_FT" and game_row['Result_FT'] == 'H': result_status = "WIN"
    elif selected_odd_col_name == "Odd_D_FT" and game_row['Result_FT'] == 'D': result_status = "WIN"
    elif selected_odd_col_name == "Odd_A_FT" and game_row['Result_FT'] == 'A': result_status = "WIN"
    elif selected_odd_col_name == "Odd_H_HT" and game_row['Result_HT'] == 'H': result_status = "WIN"
    elif selected_odd_col_name == "Odd_D_HT" and game_row['Result_HT'] == 'D': result_status = "WIN"
    elif selected_odd_col_name == "Odd_A_HT" and game_row['Result_HT'] == 'A': result_status = "WIN"
    elif selected_odd_col_name == "Odd_1X" and game_row['Result_FT'] in ['H', 'D']: result_status = "WIN"
    elif selected_odd_col_name == "Odd_12" and game_row['Result_FT'] in ['H', 'A']: result_status = "WIN"
    elif selected_odd_col_name == "Odd_X2" and game_row['Result_FT'] in ['D', 'A']: result_status = "WIN"
    elif selected_odd_col_name == "Odd_BTTS_Yes" and game_row['BTTS_Yes_Outcome']: result_status = "WIN"
    elif selected_odd_col_name == "Odd_BTTS_No" and not game_row['BTTS_Yes_Outcome']: result_status = "WIN"
    profit = (odd - 1) if result_status == "WIN" else -1.0
    return result_status, profit

def run_backtest(df_filtered, selected_odd_col_name, selected_bet_key):
    # ... (sem mudanças aqui)
    if df_filtered.empty:
        return pd.DataFrame(), {}
    results = []
    for _, game in df_filtered.iterrows():
        outcome, profit = determine_bet_outcome(game, selected_odd_col_name)
        if outcome:
            results.append({
                'Date': game['Date'], 'League': game['League'], 'Home': game['Home'], 'Away': game['Away'],
                'Score': f"{game['Goals_H_FT']}-{game['Goals_A_FT']}", 'Bet': selected_bet_key,
                'Odd': game[selected_odd_col_name], 'Outcome': outcome, 'Profit': profit
            })
    df_results = pd.DataFrame(results)
    if df_results.empty:
        return pd.DataFrame(), {}
    df_results['Cumulative_Profit'] = df_results['Profit'].cumsum()
    total_bets = len(df_results)
    wins = len(df_results[df_results['Outcome'] == 'WIN'])
    win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
    net_profit = df_results['Profit'].sum()
    roi = (net_profit / total_bets) * 100 if total_bets > 0 else 0
    avg_odd = df_results['Odd'].mean()
    avg_win_odd = df_results[df_results['Outcome'] == 'WIN']['Odd'].mean() if wins > 0 else 0
    metrics = {
        "total_bets": total_bets, "win_rate": win_rate, "net_profit": net_profit, "roi": roi,
        "avg_odd": avg_odd, "avg_win_odd": avg_win_odd
    }
    return df_results, metrics

def analyze_odds_performance(df_results, odd_bin_size=0.25):
    # ... (sem mudanças aqui)
    if df_results.empty or 'Odd' not in df_results.columns:
        return pd.DataFrame()
    df_results['Is_Win'] = (df_results['Outcome'] == 'WIN').astype(int)
    min_odd_val = df_results['Odd'].min()
    max_odd_val = df_results['Odd'].max()
    bins = np.arange(min_odd_val // odd_bin_size * odd_bin_size, max_odd_val + odd_bin_size, odd_bin_size)
    df_results['Odd_Range'] = pd.cut(df_results['Odd'], bins=bins, right=False)
    summary = df_results.groupby('Odd_Range', observed=True).agg(
        Total_Bets=('Outcome', 'count'), Wins=('Is_Win', 'sum'),
        Total_Profit=('Profit', 'sum'), Avg_Odd=('Odd', 'mean')
    ).reset_index()
    summary['Win_Rate_%'] = (summary['Wins'] / summary['Total_Bets']) * 100
    summary['ROI_%'] = (summary['Total_Profit'] / summary['Total_Bets']) * 100
    summary['Odd_Range'] = summary['Odd_Range'].apply(lambda x: f"{x.left:.2f} - {x.right:.2f}")
    summary = summary[['Odd_Range', 'Total_Bets', 'Win_Rate_%', 'Avg_Odd', 'Total_Profit', 'ROI_%']]
    return summary

def analyze_single_parameter(df_full, parameter_to_analyze, n_games, selected_odd_col_name, selected_bet_key, bin_size):
    # ... (sem mudanças aqui)
    parameter_results = []
    for index, game in df_full.iterrows():
        if pd.isna(game[selected_odd_col_name]):
            continue
        home_team = game['Home']; away_team = game['Away']; current_date = game['Date']
        value = None
        if 'home' in parameter_to_analyze:
            hist_games = get_team_last_n_games(df_full, home_team, current_date, n_games)
            if len(hist_games) < n_games: continue
            if 'avg_goals' in parameter_to_analyze: value = calculate_avg_goals_scored(hist_games, home_team)
            elif 'win_rate' in parameter_to_analyze: value = calculate_win_rate(hist_games, home_team)
        elif 'away' in parameter_to_analyze:
            hist_games = get_team_last_n_games(df_full, away_team, current_date, n_games)
            if len(hist_games) < n_games: continue
            if 'avg_goals' in parameter_to_analyze: value = calculate_avg_goals_scored(hist_games, away_team)
            elif 'win_rate' in parameter_to_analyze: value = calculate_win_rate(hist_games, away_team)
        if value is None: continue
        outcome, profit = determine_bet_outcome(game, selected_odd_col_name)
        if outcome is None: continue
        parameter_results.append({'ParameterValue': value, 'Outcome': outcome, 'Profit': profit, 'Odd': game[selected_odd_col_name]})
    if not parameter_results: return pd.DataFrame()
    df_param = pd.DataFrame(parameter_results)
    df_param['Is_Win'] = (df_param['Outcome'] == 'WIN').astype(int)
    min_val = df_param['ParameterValue'].min(); max_val = df_param['ParameterValue'].max()
    bins = np.arange(np.floor(min_val / bin_size) * bin_size, max_val + bin_size, bin_size)
    df_param['Parameter_Range'] = pd.cut(df_param['ParameterValue'], bins=bins, right=False)
    summary = df_param.groupby('Parameter_Range', observed=True).agg(
        Total_Bets=('Outcome', 'count'), Wins=('Is_Win', 'sum'),
        Total_Profit=('Profit', 'sum'), Avg_Odd=('Odd', 'mean')
    ).reset_index()
    summary = summary[summary['Total_Bets'] > 0]
    summary['Win_Rate_%'] = (summary['Wins'] / summary['Total_Bets']) * 100
    summary['ROI_%'] = (summary['Total_Profit'] / summary['Total_Bets']) * 100
    summary['Parameter_Range'] = summary['Parameter_Range'].apply(lambda x: f"{x.left:.2f} - {x.right:.2f}")
    return summary[['Parameter_Range', 'Total_Bets', 'Win_Rate_%', 'Avg_Odd', 'Total_Profit', 'ROI_%']]

# <--- NOVAS FUNÇÕES DE ANÁLISE EM JOGO --->
def analyze_goal_timing_distribution(df_matched_games, team_scope='Home'):
    """Calcula a distribuição de gols em intervalos de 15 minutos."""
    goal_col = 'Goals_Min_H_Parsed' if team_scope == 'Home' else 'Goals_Min_A_Parsed'
    
    bins = {
        '01-15 min': 0, '16-30 min': 0, '31-45 min': 0,
        '46-60 min': 0, '61-75 min': 0, '76-90+ min': 0
    }
    total_goals = 0
    
    for _, game in df_matched_games.iterrows():
        for minute in game[goal_col]:
            total_goals += 1
            if 1 <= minute <= 15: bins['01-15 min'] += 1
            elif 16 <= minute <= 30: bins['16-30 min'] += 1
            elif 31 <= minute <= 45: bins['31-45 min'] += 1
            elif 46 <= minute <= 60: bins['46-60 min'] += 1
            elif 61 <= minute <= 75: bins['61-75 min'] += 1
            else: bins['76-90+ min'] += 1

    if total_goals == 0:
        return pd.DataFrame()

    summary = pd.DataFrame(list(bins.items()), columns=['Intervalo', 'Nº de Gols'])
    summary['Distribuição %'] = (summary['Nº de Gols'] / total_goals) * 100
    return summary

def analyze_leading_scenario(df_matched_games, lead_minute, team_scope='Home'):
    """Analisa o que acontece quando um time está liderando em um certo minuto."""
    leading_games = []
    
    for _, game in df_matched_games.iterrows():
        goals_h_at_min = sum(1 for m in game['Goals_Min_H_Parsed'] if m <= lead_minute)
        goals_a_at_min = sum(1 for m in game['Goals_Min_A_Parsed'] if m <= lead_minute)
        
        is_leading = (goals_h_at_min > goals_a_at_min) if team_scope == 'Home' else (goals_a_at_min > goals_h_at_min)
        
        if is_leading:
            final_result_char = 'H' if team_scope == 'Home' else 'A'
            won_game = 1 if game['Result_FT'] == final_result_char else 0
            leading_games.append({'won_game': won_game})
            
    if not leading_games:
        return None

    df_leading = pd.DataFrame(leading_games)
    total_leading = len(df_leading)
    final_wins = df_leading['won_game'].sum()
    final_did_not_win = total_leading - final_wins
    
    return {
        "total_leading": total_leading,
        "final_wins": final_wins,
        "final_did_not_win": final_did_not_win,
        "win_rate_%": (final_wins / total_leading) * 100 if total_leading > 0 else 0
    }

# --- Interface do Streamlit ---
GITHUB_RAW_URL = "https://raw.githubusercontent.com/81matheus/BasedeDadosBet365/main/pagesbet365/Exel-Base_de_Dados_Bet365_FiltradaCompleta.xlsx"
df_original = load_data(GITHUB_RAW_URL)

st.title("BetAnalyzer 🔬 - Construtor & Descobridor de Estratégias")
st.caption("Valide suas ideias com o construtor manual ou use a análise automática para encontrar novas oportunidades.")

with st.expander("🔍 Análise Automática de Parâmetros (Descobridor de Estratégias)", expanded=False):
    # ... (código do descobridor de estratégias, sem mudanças) ...
    st.info("**Como usar:** Selecione uma aposta alvo abaixo (ex: 'Mais de 2.5 Gols FT'). Depois, clique em um dos botões 'Analisar' para ver como o ROI dessa aposta se comporta em diferentes cenários estatísticos, ajudando a encontrar filtros lucrativos.")
    auto_col1, auto_col2 = st.columns(2)
    with auto_col1:
        auto_market_type = st.selectbox("Mercado Alvo", list(MARKET_TO_ODDS_MAPPING.keys()), key="auto_market")
    with auto_col2:
        auto_bet_key = st.selectbox("Aposta Alvo", list(MARKET_TO_ODDS_MAPPING[auto_market_type].keys()), key="auto_bet")
    auto_odd_col = MARKET_TO_ODDS_MAPPING[auto_market_type][auto_bet_key]
    auto_n_games = st.slider("Analisar o histórico dos últimos N jogos:", 1, 20, 5, key="auto_n_games")
    st.markdown("---")
    auto_c1, auto_c2 = st.columns(2)
    with auto_c1:
        st.markdown("##### Análises do Time da Casa")
        if st.button("Analisar por Média de Gols (Casa)", use_container_width=True):
            with st.spinner(f"Analisando ROI para '{auto_bet_key}' vs. Média de Gols do Time da Casa..."):
                summary_df = analyze_single_parameter(df_original, 'avg_goals_home', auto_n_games, auto_odd_col, auto_bet_key, bin_size=0.2)
                if not summary_df.empty:
                    st.write(f"**Resultado para '{auto_bet_key}' vs. Média Gols (Casa) nos últimos {auto_n_games} jogos**")
                    st.bar_chart(summary_df, x='Parameter_Range', y='ROI_%')
                    st.dataframe(summary_df.style.background_gradient(subset=['ROI_%'], cmap='RdYlGn'), use_container_width=True)
                else: st.warning("Nenhum dado encontrado para esta análise.")
        if st.button("Analisar por Taxa de Vitória (Casa)", use_container_width=True):
            with st.spinner(f"Analisando ROI para '{auto_bet_key}' vs. Taxa de Vitória do Time da Casa..."):
                summary_df = analyze_single_parameter(df_original, 'win_rate_home', auto_n_games, auto_odd_col, auto_bet_key, bin_size=10)
                if not summary_df.empty:
                    st.write(f"**Resultado para '{auto_bet_key}' vs. Taxa de Vitória (Casa) nos últimos {auto_n_games} jogos**")
                    st.bar_chart(summary_df, x='Parameter_Range', y='ROI_%')
                    st.dataframe(summary_df.style.background_gradient(subset=['ROI_%'], cmap='RdYlGn'), use_container_width=True)
                else: st.warning("Nenhum dado encontrado para esta análise.")
    with auto_c2:
        st.markdown("##### Análises do Time Visitante")
        if st.button("Analisar por Média de Gols (Visitante)", use_container_width=True):
            with st.spinner(f"Analisando ROI para '{auto_bet_key}' vs. Média de Gols do Time Visitante..."):
                summary_df = analyze_single_parameter(df_original, 'avg_goals_away', auto_n_games, auto_odd_col, auto_bet_key, bin_size=0.2)
                if not summary_df.empty:
                    st.write(f"**Resultado para '{auto_bet_key}' vs. Média Gols (Visitante) nos últimos {auto_n_games} jogos**")
                    st.bar_chart(summary_df, x='Parameter_Range', y='ROI_%')
                    st.dataframe(summary_df.style.background_gradient(subset=['ROI_%'], cmap='RdYlGn'), use_container_width=True)
                else: st.warning("Nenhum dado encontrado para esta análise.")
        if st.button("Analisar por Taxa de Vitória (Visitante)", use_container_width=True):
            with st.spinner(f"Analisando ROI para '{auto_bet_key}' vs. Taxa de Vitória do Time Visitante..."):
                summary_df = analyze_single_parameter(df_original, 'win_rate_away', auto_n_games, auto_odd_col, auto_bet_key, bin_size=10)
                if not summary_df.empty:
                    st.write(f"**Resultado para '{auto_bet_key}' vs. Taxa de Vitória (Visitante) nos últimos {auto_n_games} jogos**")
                    st.bar_chart(summary_df, x='Parameter_Range', y='ROI_%')
                    st.dataframe(summary_df.style.background_gradient(subset=['ROI_%'], cmap='RdYlGn'), use_container_width=True)
                else: st.warning("Nenhum dado encontrado para esta análise.")

st.markdown("---")

if df_original.empty:
    st.warning("Não foi possível carregar os dados. Verifique a URL ou a conexão.")
else:
    with st.sidebar:
        st.image("https://i.imgur.com/V9Lcw00.png", width=50)
        st.header("Construtor de Estratégias (Manual)")
        with st.expander("🎯 MERCADO E ODDS", expanded=True):
            market_type_options = list(MARKET_TO_ODDS_MAPPING.keys())
            selected_market_type = st.selectbox("Mercado Principal", market_type_options)
            bet_selection_options = list(MARKET_TO_ODDS_MAPPING[selected_market_type].keys())
            selected_bet_key = st.selectbox("Sua Seleção de Aposta", bet_selection_options)
            selected_odd_column_name = MARKET_TO_ODDS_MAPPING[selected_market_type][selected_bet_key]
            min_odd, max_odd = st.slider("Range de Odds para a Seleção", 1.0, 15.0, (1.5, 3.5), 0.05)
        with st.expander("📊 ESTATÍSTICAS DOS TIMES (PRÉ-JOGO)"):
            st.info("Filtros baseados no desempenho das equipes ANTES da partida.")
            st.markdown("##### Time da Casa")
            n_games_home = st.slider("Analisar últimos N jogos (Casa)", 1, 20, 5, key="n_home")
            min_avg_goals_home, max_avg_goals_home = st.slider("Média de Gols Marcados (Casa)", 0.0, 5.0, (0.0, 5.0), 0.1, key="avg_h_goals")
            min_win_rate_home, max_win_rate_home = st.slider("% de Vitórias (Casa)", 0, 100, (0, 100), 1, key="win_h")
            st.markdown("---")
            st.markdown("##### Time Visitante")
            n_games_away = st.slider("Analisar últimos N jogos (Visitante)", 1, 20, 5, key="n_away")
            min_avg_goals_away, max_avg_goals_away = st.slider("Média de Gols Marcados (Visitante)", 0.0, 5.0, (0.0, 5.0), 0.1, key="avg_a_goals")
            min_win_rate_away, max_win_rate_away = st.slider("% de Vitórias (Visitante)", 0, 100, (0, 100), 1, key="win_a")
        run_analysis = st.button("Executar Backtest da Estratégia", type="primary", use_container_width=True)

    if run_analysis:
        with st.spinner("Analisando milhares de jogos com seus filtros... Por favor, aguarde."):
            # ... (Lógica de filtragem dos jogos, sem mudanças)
            df_filtered_by_odd = df_original[(df_original[selected_odd_column_name] >= min_odd) & (df_original[selected_odd_column_name] <= max_odd)].copy()
            matched_games_list = []
            for index, game in df_filtered_by_odd.iterrows():
                home_hist = get_team_last_n_games(df_original, game['Home'], game['Date'], n_games_home)
                if len(home_hist) < n_games_home: continue
                avg_goals_h = calculate_avg_goals_scored(home_hist, game['Home'])
                if not (min_avg_goals_home <= avg_goals_h <= max_avg_goals_home): continue
                win_rate_h = calculate_win_rate(home_hist, game['Home'])
                if not (min_win_rate_home <= win_rate_h <= max_win_rate_home): continue
                away_hist = get_team_last_n_games(df_original, game['Away'], game['Date'], n_games_away)
                if len(away_hist) < n_games_away: continue
                avg_goals_a = calculate_avg_goals_scored(away_hist, game['Away'])
                if not (min_avg_goals_away <= avg_goals_a <= max_avg_goals_away): continue
                win_rate_a = calculate_win_rate(away_hist, game['Away'])
                if not (min_win_rate_away <= win_rate_a <= max_win_rate_away): continue
                matched_games_list.append(game)
        
        df_matched = pd.DataFrame(matched_games_list)
        st.success(f"Análise concluída! {len(df_matched)} jogos encontrados que correspondem à sua estratégia manual.")

        if not df_matched.empty:
            df_results, metrics = run_backtest(df_matched, selected_odd_column_name, selected_bet_key)
            st.header("📈 Resultados do Backtest (Estratégia Manual)")
            # ... (código dos KPIs e gráfico de lucro, sem mudanças)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Apostas", f"{metrics['total_bets']}")
            col2.metric("Taxa de Acerto", f"{metrics['win_rate']:.2f}%")
            col3.metric("Lucro/Prejuízo Líquido", f"{metrics['net_profit']:.2f} un.")
            col4.metric("ROI (Retorno s/ Invest.)", f"{metrics['roi']:.2f}%", delta_color=("inverse" if metrics['roi'] < 0 else "normal"))
            st.subheader("Evolução do Lucro (Bankroll)")
            st.line_chart(df_results, x='Date', y='Cumulative_Profit')
            
            st.header("📊 Análise de Performance por Faixa de Odd")
            # ... (código da análise de odds, sem mudanças)
            odd_bin_size = st.slider("Defina o tamanho do intervalo das Odds para análise:", 0.10, 1.0, 0.25, 0.05, format="%.2f")
            df_odds_summary = analyze_odds_performance(df_results, odd_bin_size)
            if not df_odds_summary.empty:
                st.subheader("ROI por Faixa de Odd")
                st.bar_chart(df_odds_summary, x='Odd_Range', y='ROI_%')
                st.subheader("Resumo Detalhado por Faixa de Odd")
                st.dataframe(
                    df_odds_summary.style.format({'Win_Rate_%': '{:.2f}%', 'Avg_Odd': '{:.2f}', 'Total_Profit': '{:.2f}', 'ROI_%': '{:.2f}%'})
                    .background_gradient(subset=['ROI_%'], cmap='RdYlGn').bar(subset=["Total_Bets"], color='#2B90B4', align='zero').hide(axis="index"),
                    use_container_width=True)
            else: st.info("Não há dados suficientes para gerar a análise por faixa de odd.")
            
            # --- <NOVA SEÇÃO DE ANÁLISE EM JOGO> ---
            st.header("⏱️ Análise de Timing e Cenários nos Jogos Filtrados")
            st.info("Esta seção analisa o comportamento dos jogos que **passaram nos seus filtros**.")
            
            home_tab, away_tab = st.tabs(["Análise Time da Casa", "Análise Time Visitante"])

            with home_tab:
                st.subheader("Distribuição de Gols (Casa)")
                goal_dist_home = analyze_goal_timing_distribution(df_matched, 'Home')
                if not goal_dist_home.empty:
                    st.bar_chart(goal_dist_home.set_index('Intervalo'), y='Distribuição %')
                    st.dataframe(goal_dist_home, use_container_width=True)
                else:
                    st.write("Nenhum gol do time da casa encontrado nos jogos filtrados.")

                st.markdown("---")
                st.subheader("Cenário: Casa Liderando aos 25 Minutos")
                scenario_25_home = analyze_leading_scenario(df_matched, 25, 'Home')
                if scenario_25_home:
                    s_col1, s_col2, s_col3 = st.columns(3)
                    s_col1.metric("Jogos Liderando aos 25'", f"{scenario_25_home['total_leading']}")
                    s_col2.metric("Terminou Vencendo", f"{scenario_25_home['final_wins']} ({scenario_25_home['win_rate_%']:.1f}%)")
                    s_col3.metric("NÃO Terminou Vencendo", f"{scenario_25_home['final_did_not_win']}")
                else:
                    st.write("Nenhum jogo em que o time da casa liderava aos 25 minutos.")
                
                st.markdown("---")
                st.subheader("Cenário: Casa Liderando aos 70 Minutos")
                scenario_70_home = analyze_leading_scenario(df_matched, 70, 'Home')
                if scenario_70_home:
                    s_col1, s_col2, s_col3 = st.columns(3)
                    s_col1.metric("Jogos Liderando aos 70'", f"{scenario_70_home['total_leading']}")
                    s_col2.metric("Terminou Vencendo", f"{scenario_70_home['final_wins']} ({scenario_70_home['win_rate_%']:.1f}%)")
                    s_col3.metric("NÃO Terminou Vencendo", f"{scenario_70_home['final_did_not_win']}")
                else:
                    st.write("Nenhum jogo em que o time da casa liderava aos 70 minutos.")

            with away_tab:
                st.subheader("Distribuição de Gols (Visitante)")
                goal_dist_away = analyze_goal_timing_distribution(df_matched, 'Away')
                if not goal_dist_away.empty:
                    st.bar_chart(goal_dist_away.set_index('Intervalo'), y='Distribuição %')
                    st.dataframe(goal_dist_away, use_container_width=True)
                else:
                    st.write("Nenhum gol do time visitante encontrado nos jogos filtrados.")

                st.markdown("---")
                st.subheader("Cenário: Visitante Liderando aos 25 Minutos")
                scenario_25_away = analyze_leading_scenario(df_matched, 25, 'Away')
                if scenario_25_away:
                    s_col1, s_col2, s_col3 = st.columns(3)
                    s_col1.metric("Jogos Liderando aos 25'", f"{scenario_25_away['total_leading']}")
                    s_col2.metric("Terminou Vencendo", f"{scenario_25_away['final_wins']} ({scenario_25_away['win_rate_%']:.1f}%)")
                    s_col3.metric("NÃO Terminou Vencendo", f"{scenario_25_away['final_did_not_win']}")
                else:
                    st.write("Nenhum jogo em que o time visitante liderava aos 25 minutos.")

                st.markdown("---")
                st.subheader("Cenário: Visitante Liderando aos 70 Minutos")
                scenario_70_away = analyze_leading_scenario(df_matched, 70, 'Away')
                if scenario_70_away:
                    s_col1, s_col2, s_col3 = st.columns(3)
                    s_col1.metric("Jogos Liderando aos 70'", f"{scenario_70_away['total_leading']}")
                    s_col2.metric("Terminou Vencendo", f"{scenario_70_away['final_wins']} ({scenario_70_away['win_rate_%']:.1f}%)")
                    s_col3.metric("NÃO Terminou Vencendo", f"{scenario_70_away['final_did_not_win']}")
                else:
                    st.write("Nenhum jogo em que o time visitante liderava aos 70 minutos.")

            with st.expander("Ver todos os jogos analisados no backtest"):
                st.dataframe(df_results, use_container_width=True)
        else:
            st.info("Nenhum jogo encontrado com os critérios definidos na sua estratégia manual. Tente filtros mais flexíveis.")
    else:
        st.info("Use o 'Descobridor de Estratégias' acima ou configure seus filtros na barra lateral e clique em 'Executar Backtest' para começar.")
