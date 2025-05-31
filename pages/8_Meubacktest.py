import streamlit as st
import pandas as pd
import requests
import io
import ast # For safely evaluating string representations of lists
from datetime import datetime

# --- Configuration ---
GITHUB_RAW_URL = "https://raw.githubusercontent.com/81matheus/BasedeDadosBet365/main/pagesbet365/Exel-Base_de_Dados_Bet365_FiltradaCompleta.xlsx"

# --- Helper Functions ---

@st.cache_data # Cache the data loading to speed up app
def load_data(url):
    """Loads data from the given URL."""
    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an exception for HTTP errors
        excel_file = io.BytesIO(response.content)
        df = pd.read_excel(excel_file)
        
        # --- Data Preprocessing ---
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Parse goal minutes (handle potential NaNs or non-string values)
        def parse_goal_minutes(minute_str):
            if pd.isna(minute_str) or not isinstance(minute_str, str) or minute_str.strip() == "":
                return []
            try:
                # Safely evaluate string representations of lists
                return ast.literal_eval(minute_str)
            except (ValueError, SyntaxError):
                return [] # Return empty list if parsing fails

        df['Goals_Min_H_Parsed'] = df['Goals_Min_H'].apply(parse_goal_minutes)
        df['Goals_Min_A_Parsed'] = df['Goals_Min_A'].apply(parse_goal_minutes)
        
        # Calculate total full-time goals for convenience
        df['Total_Goals_FT'] = df['Goals_H_FT'] + df['Goals_A_FT']
        
        # Determine game result for win rate calculation
        def determine_result(row):
            if row['Goals_H_FT'] > row['Goals_A_FT']:
                return 'H'
            elif row['Goals_A_FT'] > row['Goals_H_FT']:
                return 'A'
            else:
                return 'D'
        df['Result_FT'] = df.apply(determine_result, axis=1)

        df = df.sort_values(by='Date').reset_index(drop=True) # Sort by date for historical lookups
        return df
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar os dados: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Erro ao processar os dados: {e}")
        return pd.DataFrame()

def get_team_last_n_games(df_full, team_name, current_game_date, n_games):
    """
    Fetches the last N games for a specific team before a given date.
    """
    team_games = df_full[((df_full['Home'] == team_name) | (df_full['Away'] == team_name)) & (df_full['Date'] < current_game_date)]
    return team_games.sort_values(by='Date', ascending=False).head(n_games)

def calculate_avg_goals_scored(historical_games, team_name):
    """
    Calculates the average goals scored by the specified team in their historical games.
    """
    if historical_games.empty:
        return 0
    goals_scored = 0
    for _, game in historical_games.iterrows():
        if game['Home'] == team_name:
            goals_scored += game['Goals_H_FT']
        elif game['Away'] == team_name:
            goals_scored += game['Goals_A_FT']
    return goals_scored / len(historical_games) if len(historical_games) > 0 else 0

def calculate_win_rate(historical_games, team_name):
    """
    Calculates the win rate for the specified team in their historical games.
    """
    if historical_games.empty:
        return 0
    wins = 0
    for _, game in historical_games.iterrows():
        if game['Home'] == team_name and game['Result_FT'] == 'H':
            wins += 1
        elif game['Away'] == team_name and game['Result_FT'] == 'A':
            wins += 1
    return (wins / len(historical_games)) * 100 if len(historical_games) > 0 else 0

def check_goal_timing(game_row, before_minute_val, after_minute_val, team_scope,
                      apply_before_filter, apply_after_filter):
    """
    Checks if goals were scored according to the timing criteria.
    """
    if not apply_before_filter and not apply_after_filter:
        return True # No timing filter applied

    goal_times_to_check = []
    if team_scope == "Time Casa" or team_scope == "Ambos os Times":
        goal_times_to_check.extend(game_row['Goals_Min_H_Parsed'])
    if team_scope == "Time Visitante" or team_scope == "Ambos os Times":
        goal_times_to_check.extend(game_row['Goals_Min_A_Parsed'])
        
    if not goal_times_to_check and (apply_before_filter or apply_after_filter): # No goals scored by selected team(s)
        return False 

    found_goal_before = False
    if apply_before_filter:
        for minute in goal_times_to_check:
            if minute < before_minute_val:
                found_goal_before = True
                break
        if not found_goal_before: # If filter is active and no goal found before, fail
            return False
            
    found_goal_after = False
    if apply_after_filter:
        for minute in goal_times_to_check:
            if minute > after_minute_val:
                found_goal_after = True
                break
        if not found_goal_after: # If filter is active and no goal found after, fail
            return False
            
    return True


# --- Load Data ---
df_original = load_data(GITHUB_RAW_URL)

# --- Sidebar ---
st.sidebar.image("https://i.imgur.com/V9Lcw00.png", width=50) # Placeholder icon, replace with your logo
st.sidebar.title("BetAnalyzer")
st.sidebar.caption("Backtest Profissional")

st.sidebar.header("ANÁLISE")
page = st.sidebar.radio("", ["Dashboard", "Estratégias", "Backtest", "Importar Dados"], index=1)

st.sidebar.header("PERFORMANCE")
st.sidebar.metric("ROI Médio", "+12.4%", "dummy_delta") # Placeholder
st.sidebar.metric("Estratégias Ativas", "3", "dummy_delta") # Placeholder

# --- Main Page Content ---

if page == "Estratégias":
    st.header("Construtor de Estratégias")

    if df_original.empty:
        st.warning("Não foi possível carregar os dados. Verifique a URL ou a conexão.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            with st.container(border=True):
                st.subheader("Análise Gols - Time Casa")
                n_games_goals_home = st.number_input("Últimos jogos para análise (Casa Gols)", min_value=1, max_value=50, value=10, key="n_home_goals")
                c1_gh, c2_gh = st.columns(2)
                min_avg_goals_home = c1_gh.number_input("Média mín. gols (Casa)", min_value=0.0, max_value=10.0, value=0.0, step=0.1, key="min_avg_h_goals")
                max_avg_goals_home = c2_gh.number_input("Média máx. gols (Casa)", min_value=0.0, max_value=10.0, value=10.0, step=0.1, key="max_avg_h_goals")

            with st.container(border=True):
                st.subheader("Taxa de Vitórias - Casa")
                n_games_wins_home = st.number_input("Últimos jogos para análise (Casa Vitórias)", min_value=1, max_value=50, value=10, key="n_home_wins")
                c1_vh, c2_vh = st.columns(2)
                min_win_rate_home = c1_vh.number_input("% mín. vitórias (Casa)", min_value=0, max_value=100, value=0, step=1, key="min_win_h")
                max_win_rate_home = c2_vh.number_input("% máx. vitórias (Casa)", min_value=0, max_value=100, value=100, step=1, key="max_win_h")

        with col2:
            with st.container(border=True):
                st.subheader("Análise Gols - Time Visitante")
                n_games_goals_away = st.number_input("Últimos jogos para análise (Visitante Gols)", min_value=1, max_value=50, value=10, key="n_away_goals")
                c1_ga, c2_ga = st.columns(2)
                min_avg_goals_away = c1_ga.number_input("Média mín. gols (Visitante)", min_value=0.0, max_value=10.0, value=0.0, step=0.1, key="min_avg_a_goals")
                max_avg_goals_away = c2_ga.number_input("Média máx. gols (Visitante)", min_value=0.0, max_value=10.0, value=10.0, step=0.1, key="max_avg_a_goals")
            
            with st.container(border=True):
                st.subheader("Taxa de Vitórias - Visitante")
                n_games_wins_away = st.number_input("Últimos jogos para análise (Visitante Vitórias)", min_value=1, max_value=50, value=10, key="n_away_wins")
                c1_va, c2_va = st.columns(2)
                min_win_rate_away = c1_va.number_input("% mín. vitórias (Visitante)", min_value=0, max_value=100, value=0, step=1, key="min_win_a")
                max_win_rate_away = c2_va.number_input("% máx. vitórias (Visitante)", min_value=0, max_value=100, value=100, step=1, key="max_win_a")
        
        st.markdown("---") # Separator
        with st.container(border=True):
            st.subheader("Timing de Gols")
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                apply_goal_before = st.toggle("Gol antes do minuto", value=False, key="toggle_goal_before")
                minute_goal_before = st.number_input("Minuto (antes)", min_value=1, max_value=90, value=45, disabled=not apply_goal_before, key="minute_before")
            with col_t2:
                apply_goal_after = st.toggle("Gol depois do minuto", value=False, key="toggle_goal_after")
                minute_goal_after = st.number_input("Minuto (depois)", min_value=1, max_value=90, value=80, disabled=not apply_goal_after, key="minute_after")
            with col_t3:
                timing_team_scope = st.selectbox("Time para análise (Timing)", ["Ambos os Times", "Time Casa", "Time Visitante"], key="timing_scope",
                                                 disabled=not (apply_goal_before or apply_goal_after))

        st.markdown("---")

        if st.button("Analisar Estratégia", type="primary", use_container_width=True):
            matched_games = []
            if df_original.empty:
                st.error("Dados não carregados, não é possível analisar.")
            else:
                with st.spinner("Analisando jogos... Por favor, aguarde."):
                    for index, game in df_original.iterrows():
                        current_date = game['Date']
                        home_team = game['Home']
                        away_team = game['Away']

                        # --- Home Team Analysis ---
                        # Goals
                        home_team_hist_goals = get_team_last_n_games(df_original, home_team, current_date, n_games_goals_home)
                        if len(home_team_hist_goals) < n_games_goals_home : # Not enough historical data
                            continue 
                        avg_goals_home_actual = calculate_avg_goals_scored(home_team_hist_goals, home_team)
                        
                        # Wins
                        home_team_hist_wins = get_team_last_n_games(df_original, home_team, current_date, n_games_wins_home)
                        if len(home_team_hist_wins) < n_games_wins_home :
                            continue
                        win_rate_home_actual = calculate_win_rate(home_team_hist_wins, home_team)

                        # --- Away Team Analysis ---
                        # Goals
                        away_team_hist_goals = get_team_last_n_games(df_original, away_team, current_date, n_games_goals_away)
                        if len(away_team_hist_goals) < n_games_goals_away:
                            continue
                        avg_goals_away_actual = calculate_avg_goals_scored(away_team_hist_goals, away_team)
                        
                        # Wins
                        away_team_hist_wins = get_team_last_n_games(df_original, away_team, current_date, n_games_wins_away)
                        if len(away_team_hist_wins) < n_games_wins_away:
                            continue
                        win_rate_away_actual = calculate_win_rate(away_team_hist_wins, away_team)
                        
                        # --- Check Conditions ---
                        # Goal Averages
                        cond_home_goals = (min_avg_goals_home <= avg_goals_home_actual <= max_avg_goals_home)
                        cond_away_goals = (min_avg_goals_away <= avg_goals_away_actual <= max_avg_goals_away)
                        
                        # Win Rates
                        cond_home_wins = (min_win_rate_home <= win_rate_home_actual <= max_win_rate_home)
                        cond_away_wins = (min_win_rate_away <= win_rate_away_actual <= max_win_rate_away)

                        # Goal Timing
                        cond_goal_timing = check_goal_timing(game, minute_goal_before, minute_goal_after, 
                                                             timing_team_scope, apply_goal_before, apply_goal_after)

                        if cond_home_goals and cond_away_goals and cond_home_wins and cond_away_wins and cond_goal_timing:
                            # Add stats to the game row for display if needed
                            game_data_to_add = game.copy() # Make a copy to avoid modifying original df rows
                            game_data_to_add['Hist_Avg_G_H'] = round(avg_goals_home_actual,2)
                            game_data_to_add['Hist_Avg_G_A'] = round(avg_goals_away_actual,2)
                            game_data_to_add['Hist_Win_%_H'] = round(win_rate_home_actual,1)
                            game_data_to_add['Hist_Win_%_A'] = round(win_rate_away_actual,1)
                            matched_games.append(game_data_to_add)
                
                st.success(f"Análise concluída! {len(matched_games)} jogos encontrados que correspondem à estratégia.")
                
                if matched_games:
                    df_matched = pd.DataFrame(matched_games)
                    # Select and reorder columns for display
                    display_cols = ['Date', 'League', 'Season', 'Home', 'Away', 
                                    'Goals_H_FT', 'Goals_A_FT', 'Total_Goals_FT',
                                    'Hist_Avg_G_H', 'Hist_Avg_G_A', 'Hist_Win_%_H', 'Hist_Win_%_A',
                                    'Odd_H_FT', 'Odd_D_FT', 'Odd_A_FT']
                    # Filter out columns not present in df_matched (like if original df didn't have some Odds)
                    display_cols = [col for col in display_cols if col in df_matched.columns]
                    st.dataframe(df_matched[display_cols])
                else:
                    st.info("Nenhum jogo encontrado com os critérios definidos.")

elif page == "Dashboard":
    st.header("Dashboard")
    st.write("Conteúdo do Dashboard aqui...")
    if not df_original.empty:
        st.write("Primeiras 5 linhas da base de dados:")
        st.dataframe(df_original.head())

elif page == "Backtest":
    st.header("Backtest")
    st.write("Funcionalidade de Backtest detalhado aqui...")
    st.info("Esta seção seria para simular apostas com base nas estratégias e calcular o ROI.")

elif page == "Importar Dados":
    st.header("Importar Dados")
    st.write("Interface para importar novos dados ou atualizar a base existente aqui...")
