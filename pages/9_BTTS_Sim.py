import streamlit as st
import pandas as pd
import requests
import io
import ast # For safely evaluating string representations of lists
from datetime import datetime

# --- Configuration ---
GITHUB_RAW_URL = "https://raw.githubusercontent.com/81matheus/BasedeDadosBet365/main/pagesbet365/Exel-Base_de_Dados_Bet365_FiltradaCompleta.xlsx"

# --- Market and Bet Selection Mapping ---
# This maps user-friendly names to DataFrame column names for odds
MARKET_TO_ODDS_MAPPING = {
    "Over/Under FT": {
        "Mais de 0.5 Gols FT": "Odd_Over05_FT",
        "Menos de 0.5 Gols FT": "Odd_Under05_FT",
        "Mais de 1.5 Gols FT": "Odd_Over15_FT",
        "Menos de 1.5 Gols FT": "Odd_Under15_FT",
        "Mais de 2.5 Gols FT": "Odd_Over25_FT",
        "Menos de 2.5 Gols FT": "Odd_Under25_FT",
        "Mais de 3.5 Gols FT": "Odd_Over35_FT",
        "Menos de 3.5 Gols FT": "Odd_Under35_FT",
        "Mais de 4.5 Gols FT": "Odd_Over45_FT",
        "Menos de 4.5 Gols FT": "Odd_Under45_FT",
    },
    "Over/Under HT": {
        "Mais de 0.5 Gols HT": "Odd_Over05_HT",
        "Menos de 0.5 Gols HT": "Odd_Under05_HT",
        "Mais de 1.5 Gols HT": "Odd_Over15_HT",
        "Menos de 1.5 Gols HT": "Odd_Under15_HT",
        "Mais de 2.5 Gols HT": "Odd_Over25_HT",
        "Menos de 2.5 Gols HT": "Odd_Under25_HT",
    },
    "Resultado Final (1X2 FT)": {
        "Vitória Casa (FT)": "Odd_H_FT",
        "Empate (FT)": "Odd_D_FT",
        "Vitória Visitante (FT)": "Odd_A_FT",
    },
    "Resultado Intervalo (1X2 HT)": {
        "Vitória Casa (HT)": "Odd_H_HT",
        "Empate (HT)": "Odd_D_HT",
        "Vitória Visitante (HT)": "Odd_A_HT",
    },
    "Dupla Chance (FT)": {
        "Casa ou Empate (1X)": "Odd_1X",
        "Casa ou Visitante (12)": "Odd_12",
        "Empate ou Visitante (X2)": "Odd_X2",
    },
    "Ambas Marcam (BTTS)": {
        "Sim (BTTS Yes)": "Odd_BTTS_Yes",
        "Não (BTTS No)": "Odd_BTTS_No",
    }
}

# --- Helper Functions ---

@st.cache_data
def load_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        excel_file = io.BytesIO(response.content)
        df = pd.read_excel(excel_file)
        
        df['Date'] = pd.to_datetime(df['Date'])
        
        def parse_goal_minutes(minute_str):
            if pd.isna(minute_str) or not isinstance(minute_str, str) or minute_str.strip() == "":
                return []
            try:
                return ast.literal_eval(minute_str)
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

def get_team_last_n_games(df_full, team_name, current_game_date, n_games):
    team_games = df_full[((df_full['Home'] == team_name) | (df_full['Away'] == team_name)) & (df_full['Date'] < current_game_date)]
    return team_games.sort_values(by='Date', ascending=False).head(n_games)

def calculate_avg_goals_scored(historical_games, team_name):
    if historical_games.empty: return 0
    goals_scored = 0
    for _, game in historical_games.iterrows():
        if game['Home'] == team_name: goals_scored += game['Goals_H_FT']
        elif game['Away'] == team_name: goals_scored += game['Goals_A_FT']
    return goals_scored / len(historical_games) if len(historical_games) > 0 else 0

def calculate_win_rate(historical_games, team_name):
    if historical_games.empty: return 0
    wins = 0
    for _, game in historical_games.iterrows():
        if game['Home'] == team_name and game['Result_FT'] == 'H': wins += 1
        elif game['Away'] == team_name and game['Result_FT'] == 'A': wins += 1
    return (wins / len(historical_games)) * 100 if len(historical_games) > 0 else 0

def check_goal_timing(game_row, before_minute_val, after_minute_val, team_scope,
                      apply_before_filter, apply_after_filter):
    if not apply_before_filter and not apply_after_filter: return True
    goal_times_to_check = []
    if team_scope == "Time Casa" or team_scope == "Ambos os Times":
        goal_times_to_check.extend(game_row['Goals_Min_H_Parsed'])
    if team_scope == "Time Visitante" or team_scope == "Ambos os Times":
        goal_times_to_check.extend(game_row['Goals_Min_A_Parsed'])
    if not goal_times_to_check and (apply_before_filter or apply_after_filter): return False
    
    found_goal_before = not apply_before_filter # If filter not active, condition is met
    if apply_before_filter:
        for minute in goal_times_to_check:
            if minute < before_minute_val: found_goal_before = True; break
    
    found_goal_after = not apply_after_filter # If filter not active, condition is met
    if apply_after_filter:
        for minute in goal_times_to_check:
            if minute > after_minute_val: found_goal_after = True; break
            
    if apply_before_filter and apply_after_filter:
        return found_goal_before and found_goal_after
    elif apply_before_filter:
        return found_goal_before
    elif apply_after_filter:
        return found_goal_after
    return True # Should not be reached if logic is correct

def determine_bet_outcome(game_row, selected_odd_col_name):
    """
    Determines if the selected bet would have won, lost, or pushed.
    Returns: "WIN", "LOSS", "PUSH" (or None if outcome cannot be determined)
    """
    if pd.isna(game_row[selected_odd_col_name]):
        return None # No odd, can't determine

    # Over/Under FT
    if selected_odd_col_name == "Odd_Over05_FT": return "WIN" if game_row['Total_Goals_FT'] > 0.5 else "LOSS"
    if selected_odd_col_name == "Odd_Under05_FT": return "WIN" if game_row['Total_Goals_FT'] < 0.5 else "LOSS"
    if selected_odd_col_name == "Odd_Over15_FT": return "WIN" if game_row['Total_Goals_FT'] > 1.5 else "LOSS"
    if selected_odd_col_name == "Odd_Under15_FT": return "WIN" if game_row['Total_Goals_FT'] < 1.5 else "LOSS"
    if selected_odd_col_name == "Odd_Over25_FT": return "WIN" if game_row['Total_Goals_FT'] > 2.5 else "LOSS"
    if selected_odd_col_name == "Odd_Under25_FT": return "WIN" if game_row['Total_Goals_FT'] < 2.5 else "LOSS"
    # ... add other Over/Under FT lines (3.5, 4.5)

    # Over/Under HT
    if selected_odd_col_name == "Odd_Over05_HT": return "WIN" if game_row['Total_Goals_HT'] > 0.5 else "LOSS"
    if selected_odd_col_name == "Odd_Under05_HT": return "WIN" if game_row['Total_Goals_HT'] < 0.5 else "LOSS"
    # ... add other Over/Under HT lines

    # 1X2 FT
    if selected_odd_col_name == "Odd_H_FT": return "WIN" if game_row['Result_FT'] == 'H' else "LOSS"
    if selected_odd_col_name == "Odd_D_FT": return "WIN" if game_row['Result_FT'] == 'D' else "LOSS"
    if selected_odd_col_name == "Odd_A_FT": return "WIN" if game_row['Result_FT'] == 'A' else "LOSS"

    # 1X2 HT
    if selected_odd_col_name == "Odd_H_HT": return "WIN" if game_row['Result_HT'] == 'H' else "LOSS"
    if selected_odd_col_name == "Odd_D_HT": return "WIN" if game_row['Result_HT'] == 'D' else "LOSS"
    if selected_odd_col_name == "Odd_A_HT": return "WIN" if game_row['Result_HT'] == 'A' else "LOSS"

    # Double Chance FT
    if selected_odd_col_name == "Odd_1X": return "WIN" if game_row['Result_FT'] in ['H', 'D'] else "LOSS"
    if selected_odd_col_name == "Odd_12": return "WIN" if game_row['Result_FT'] in ['H', 'A'] else "LOSS"
    if selected_odd_col_name == "Odd_X2": return "WIN" if game_row['Result_FT'] in ['D', 'A'] else "LOSS"

    # BTTS
    if selected_odd_col_name == "Odd_BTTS_Yes": return "WIN" if game_row['BTTS_Yes_Outcome'] else "LOSS"
    if selected_odd_col_name == "Odd_BTTS_No": return "WIN" if not game_row['BTTS_Yes_Outcome'] else "LOSS"
    
    return None # If no specific rule matches

# --- Load Data ---
df_original = load_data(GITHUB_RAW_URL)

# --- Sidebar ---
st.sidebar.image("https://i.imgur.com/V9Lcw00.png", width=50)
st.sidebar.title("BetAnalyzer")
st.sidebar.caption("Backtest Profissional")
st.sidebar.header("ANÁLISE")
page = st.sidebar.radio("", ["Dashboard", "Estratégias", "Backtest", "Importar Dados"], index=1, key="main_page_nav")
st.sidebar.header("PERFORMANCE")
st.sidebar.metric("ROI Médio", "+12.4%", "dummy_delta_roi")
st.sidebar.metric("Estratégias Ativas", "3", "dummy_delta_strat")

# --- Main Page Content ---
if page == "Estratégias":
    st.header("Construtor de Estratégias")

    if df_original.empty:
        st.warning("Não foi possível carregar os dados. Verifique a URL ou a conexão.")
    else:
        with st.container(border=True):
            st.subheader("⚙️ Informações Básicas da Estratégia")
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                strategy_name = st.text_input("Nome da Estratégia", "Minha Estratégia")
            with col_s2:
                market_type_options = list(MARKET_TO_ODDS_MAPPING.keys())
                selected_market_type = st.selectbox("Tipo de Mercado", market_type_options, key="market_type")

            strategy_desc = st.text_area("Descrição", "Descreva sua estratégia aqui...")

            bet_selection_options = list(MARKET_TO_ODDS_MAPPING[selected_market_type].keys())
            selected_bet_key = st.selectbox("Seleção da Aposta", bet_selection_options, key="bet_selection")
            # This is the actual DataFrame column name for the selected odd
            selected_odd_column_name = MARKET_TO_ODDS_MAPPING[selected_market_type][selected_bet_key]

            col_o1, col_o2 = st.columns(2)
            with col_o1:
                min_odd = st.number_input("Odd Mínima", min_value=1.0, value=1.5, step=0.01, format="%.2f", key="min_odd_strat")
            with col_o2:
                max_odd = st.number_input("Odd Máxima", min_value=1.0, value=5.0, step=0.01, format="%.2f", key="max_odd_strat")
        
        st.markdown("---")
        st.subheader("Filtros Estatísticos Adicionais")

        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("##### Análise Gols - Time Casa")
                n_games_goals_home = st.number_input("Últimos jogos (Casa Gols)", 1, 50, 10, key="n_home_goals")
                c1_gh, c2_gh = st.columns(2)
                min_avg_goals_home = c1_gh.number_input("Média mín. gols (Casa)", 0.0, 10.0, 0.0, 0.1, key="min_avg_h_goals")
                max_avg_goals_home = c2_gh.number_input("Média máx. gols (Casa)", 0.0, 10.0, 10.0, 0.1, key="max_avg_h_goals")

            with st.container(border=True):
                st.markdown("##### Taxa de Vitórias - Casa")
                n_games_wins_home = st.number_input("Últimos jogos (Casa Vitórias)", 1, 50, 10, key="n_home_wins")
                c1_vh, c2_vh = st.columns(2)
                min_win_rate_home = c1_vh.number_input("% mín. vitórias (Casa)", 0, 100, 0, 1, key="min_win_h")
                max_win_rate_home = c2_vh.number_input("% máx. vitórias (Casa)", 0, 100, 100, 1, key="max_win_h")

        with col2:
            with st.container(border=True):
                st.markdown("##### Análise Gols - Time Visitante")
                n_games_goals_away = st.number_input("Últimos jogos (Visitante Gols)", 1, 50, 10, key="n_away_goals")
                c1_ga, c2_ga = st.columns(2)
                min_avg_goals_away = c1_ga.number_input("Média mín. gols (Visitante)", 0.0, 10.0, 0.0, 0.1, key="min_avg_a_goals")
                max_avg_goals_away = c2_ga.number_input("Média máx. gols (Visitante)", 0.0, 10.0, 10.0, 0.1, key="max_avg_a_goals")
            
            with st.container(border=True):
                st.markdown("##### Taxa de Vitórias - Visitante")
                n_games_wins_away = st.number_input("Últimos jogos (Visitante Vitórias)", 1, 50, 10, key="n_away_wins")
                c1_va, c2_va = st.columns(2)
                min_win_rate_away = c1_va.number_input("% mín. vitórias (Visitante)", 0, 100, 0, 1, key="min_win_a")
                max_win_rate_away = c2_va.number_input("% máx. vitórias (Visitante)", 0, 100, 100, 1, key="max_win_a")
        
        st.markdown("---")
        with st.container(border=True):
            st.markdown("##### Timing de Gols")
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                apply_goal_before = st.toggle("Gol antes do minuto", value=False, key="toggle_goal_before")
                minute_goal_before = st.number_input("Minuto (antes)", 1, 90, 45, disabled=not apply_goal_before, key="minute_before")
            with col_t2:
                apply_goal_after = st.toggle("Gol depois do minuto", value=False, key="toggle_goal_after")
                minute_goal_after = st.number_input("Minuto (depois)", 1, 90, 80, disabled=not apply_goal_after, key="minute_after")
            with col_t3:
                timing_team_scope = st.selectbox("Time para análise (Timing)", ["Ambos os Times", "Time Casa", "Time Visitante"], key="timing_scope",
                                                 disabled=not (apply_goal_before or apply_goal_after))
        st.markdown("---")

        if st.button("Analisar Estratégia", type="primary", use_container_width=True):
            matched_games = []
            if df_original.empty:
                st.error("Dados não carregados, não é possível analisar.")
            else:
                with st.spinner(f"Analisando jogos para a estratégia '{strategy_name}'... Por favor, aguarde."):
                    for index, game in df_original.iterrows():
                        current_date = game['Date']
                        home_team = game['Home']
                        away_team = game['Away']

                        # --- Statistical Filters ---
                        # Home Team Goals
                        home_team_hist_goals = get_team_last_n_games(df_original, home_team, current_date, n_games_goals_home)
                        if len(home_team_hist_goals) < n_games_goals_home: continue
                        avg_goals_home_actual = calculate_avg_goals_scored(home_team_hist_goals, home_team)
                        if not (min_avg_goals_home <= avg_goals_home_actual <= max_avg_goals_home): continue
                        
                        # Home Team Wins
                        home_team_hist_wins = get_team_last_n_games(df_original, home_team, current_date, n_games_wins_home)
                        if len(home_team_hist_wins) < n_games_wins_home: continue
                        win_rate_home_actual = calculate_win_rate(home_team_hist_wins, home_team)
                        if not (min_win_rate_home <= win_rate_home_actual <= max_win_rate_home): continue

                        # Away Team Goals
                        away_team_hist_goals = get_team_last_n_games(df_original, away_team, current_date, n_games_goals_away)
                        if len(away_team_hist_goals) < n_games_goals_away: continue
                        avg_goals_away_actual = calculate_avg_goals_scored(away_team_hist_goals, away_team)
                        if not (min_avg_goals_away <= avg_goals_away_actual <= max_avg_goals_away): continue
                        
                        # Away Team Wins
                        away_team_hist_wins = get_team_last_n_games(df_original, away_team, current_date, n_games_wins_away)
                        if len(away_team_hist_wins) < n_games_wins_away: continue
                        win_rate_away_actual = calculate_win_rate(away_team_hist_wins, away_team)
                        if not (min_win_rate_away <= win_rate_away_actual <= max_win_rate_away): continue
                        
                        # Goal Timing
                        if not check_goal_timing(game, minute_goal_before, minute_goal_after, 
                                                 timing_team_scope, apply_goal_before, apply_after_filter):
                            continue
                        
                        # --- Selected Bet Odds Filter ---
                        if selected_odd_column_name not in game or pd.isna(game[selected_odd_column_name]):
                            continue # Selected odd not available for this game
                        
                        game_odd_for_selected_bet = game[selected_odd_column_name]
                        if not (min_odd <= game_odd_for_selected_bet <= max_odd):
                            continue

                        # If all filters passed, add the game
                        game_data_to_add = game.copy()
                        game_data_to_add['Hist_Avg_G_H'] = round(avg_goals_home_actual, 2)
                        game_data_to_add['Hist_Avg_G_A'] = round(avg_goals_away_actual, 2)
                        game_data_to_add['Hist_Win_%_H'] = round(win_rate_home_actual, 1)
                        game_data_to_add['Hist_Win_%_A'] = round(win_rate_away_actual, 1)
                        game_data_to_add[f'Odd_Selecionada ({selected_bet_key})'] = game_odd_for_selected_bet
                        
                        # Determine bet outcome for display/later use (optional for filtering step)
                        # bet_outcome_result = determine_bet_outcome(game, selected_odd_column_name)
                        # game_data_to_add['Resultado_Aposta'] = bet_outcome_result

                        matched_games.append(game_data_to_add)
                
                st.success(f"Análise concluída! {len(matched_games)} jogos encontrados que correspondem à estratégia '{strategy_name}'.")
                
                if matched_games:
                    df_matched = pd.DataFrame(matched_games)
                    cols_to_show = ['Date', 'League', 'Home', 'Away', 'Goals_H_FT', 'Goals_A_FT',
                                    f'Odd_Selecionada ({selected_bet_key})',
                                    'Hist_Avg_G_H', 'Hist_Avg_G_A', 'Hist_Win_%_H', 'Hist_Win_%_A']
                    # Add other relevant odds or info if desired
                    # if 'Resultado_Aposta' in df_matched.columns:
                    #    cols_to_show.append('Resultado_Aposta')
                    
                    st.dataframe(df_matched[[col for col in cols_to_show if col in df_matched.columns]])
                else:
                    st.info("Nenhum jogo encontrado com os critérios definidos.")

elif page == "Dashboard":
    st.header("Dashboard")
    st.write("Conteúdo do Dashboard aqui...")
    if not df_original.empty:
        st.write("Amostra da base de dados:")
        st.dataframe(df_original.head())

elif page == "Backtest":
    st.header("Backtest")
    st.write("""
    Esta seção será usada para simular apostas com base nas estratégias definidas e calcular o desempenho.
    1. Defina uma estratégia na página "Estratégias".
    2. Use os jogos filtrados para simular apostas (ex: R$100 por jogo).
    3. Calcule o Lucro/Prejuízo Total, ROI, Taxa de Acerto, etc.
    """)
    st.info("Funcionalidade de backtesting detalhado a ser implementada.")
    # Here, you would take the `matched_games` from a saved strategy (not implemented yet)
    # or re-run the filter, then apply the `determine_bet_outcome` function,
    # simulate bets, and calculate performance metrics.

elif page == "Importar Dados":
    st.header("Importar Dados")
    st.write("Interface para importar novos dados ou atualizar a base existente aqui...")
