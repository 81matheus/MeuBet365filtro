import streamlit as st
import pandas as pd
import requests
import io
import ast
from datetime import datetime

# --- Configuração da Página e Título ---
st.set_page_config(layout="wide", page_title="BetAnalyzer - Backtesting Profissional")

# --- Mapeamento de Mercados e Odds ---
MARKET_TO_ODDS_MAPPING = {
    "Resultado Final (1X2 FT)": {
        "Vitória Casa (FT)": "Odd_H_FT",
        "Empate (FT)": "Odd_D_FT",
        "Vitória Visitante (FT)": "Odd_A_FT",
    },
    "Mais/Menos Gols (FT)": {
        "Mais de 0.5 Gols FT": "Odd_Over05_FT", "Menos de 0.5 Gols FT": "Odd_Under05_FT",
        "Mais de 1.5 Gols FT": "Odd_Over15_FT", "Menos de 1.5 Gols FT": "Odd_Under15_FT",
        "Mais de 2.5 Gols FT": "Odd_Over25_FT", "Menos de 2.5 Gols FT": "Odd_Under25_FT",
        "Mais de 3.5 Gols FT": "Odd_Over35_FT", "Menos de 3.5 Gols FT": "Odd_Under35_FT",
        "Mais de 4.5 Gols FT": "Odd_Over45_FT", "Menos de 4.5 Gols FT": "Odd_Under45_FT",
    },
    "Ambas Marcam (BTTS)": {
        "Sim (BTTS Yes)": "Odd_BTTS_Yes",
        "Não (BTTS No)": "Odd_BTTS_No",
    },
    "Dupla Chance (FT)": {
        "Casa ou Empate (1X)": "Odd_1X",
        "Casa ou Visitante (12)": "Odd_12",
        "Empate ou Visitante (X2)": "Odd_X2",
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

        # Conversões e colunas calculadas
        df['Date'] = pd.to_datetime(df['Date'])
        for col in df.columns:
            if 'Odd' in col:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            if 'Goals' in col and 'Min' not in col:
                 df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

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

        # Ordenar por data é crucial para o backtesting
        df = df.sort_values(by='Date').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar/processar dados: {e}")
        return pd.DataFrame()

def get_team_last_n_games(df_full, team_name, current_game_date, n_games):
    """Pega os últimos N jogos de um time antes de uma data específica."""
    team_games = df_full[((df_full['Home'] == team_name) | (df_full['Away'] == team_name)) & (df_full['Date'] < current_game_date)]
    return team_games.tail(n_games) # .tail() é mais eficiente que sort+head em um dataframe já ordenado

def calculate_avg_goals_scored(historical_games, team_name):
    """Calcula a média de gols marcados por um time em seus jogos históricos."""
    if historical_games.empty: return 0
    goals_scored = 0
    for _, game in historical_games.iterrows():
        if game['Home'] == team_name: goals_scored += game['Goals_H_FT']
        elif game['Away'] == team_name: goals_scored += game['Goals_A_FT']
    return goals_scored / len(historical_games)

def calculate_win_rate(historical_games, team_name):
    """Calcula a taxa de vitória de um time em seus jogos históricos."""
    if historical_games.empty: return 0
    wins = 0
    for _, game in historical_games.iterrows():
        if game['Home'] == team_name and game['Result_FT'] == 'H': wins += 1
        elif game['Away'] == team_name and game['Result_FT'] == 'A': wins += 1
    return (wins / len(historical_games)) * 100

def determine_bet_outcome(game_row, selected_odd_col_name):
    """Determina se uma aposta foi 'WIN', 'LOSS', ou 'PUSH'."""
    # Retorna o lucro líquido para uma aposta de 1 unidade
    # Win: odd - 1, Loss: -1, Push: 0
    odd = game_row[selected_odd_col_name]
    if pd.isna(odd): return None, None

    result_status = "LOSS" # Padrão
    
    # Mais/Menos Gols FT
    if "Over" in selected_odd_col_name and "FT" in selected_odd_col_name:
        goal_line = float(selected_odd_col_name.split('_')[1].replace('Over', '').replace('FT', '')) / 10
        if game_row['Total_Goals_FT'] > goal_line: result_status = "WIN"
    elif "Under" in selected_odd_col_name and "FT" in selected_odd_col_name:
        goal_line = float(selected_odd_col_name.split('_')[1].replace('Under', '').replace('FT', '')) / 10
        if game_row['Total_Goals_FT'] < goal_line: result_status = "WIN"

    # Mais/Menos Gols HT
    if "Over" in selected_odd_col_name and "HT" in selected_odd_col_name:
        goal_line = float(selected_odd_col_name.split('_')[1].replace('Over', '').replace('HT', '')) / 10
        if game_row['Total_Goals_HT'] > goal_line: result_status = "WIN"
    elif "Under" in selected_odd_col_name and "HT" in selected_odd_col_name:
        goal_line = float(selected_odd_col_name.split('_')[1].replace('Under', '').replace('HT', '')) / 10
        if game_row['Total_Goals_HT'] < goal_line: result_status = "WIN"

    # Resultado Final FT
    elif selected_odd_col_name == "Odd_H_FT" and game_row['Result_FT'] == 'H': result_status = "WIN"
    elif selected_odd_col_name == "Odd_D_FT" and game_row['Result_FT'] == 'D': result_status = "WIN"
    elif selected_odd_col_name == "Odd_A_FT" and game_row['Result_FT'] == 'A': result_status = "WIN"
    
    # Resultado Intervalo HT
    elif selected_odd_col_name == "Odd_H_HT" and game_row['Result_HT'] == 'H': result_status = "WIN"
    elif selected_odd_col_name == "Odd_D_HT" and game_row['Result_HT'] == 'D': result_status = "WIN"
    elif selected_odd_col_name == "Odd_A_HT" and game_row['Result_HT'] == 'A': result_status = "WIN"

    # Dupla Chance
    elif selected_odd_col_name == "Odd_1X" and game_row['Result_FT'] in ['H', 'D']: result_status = "WIN"
    elif selected_odd_col_name == "Odd_12" and game_row['Result_FT'] in ['H', 'A']: result_status = "WIN"
    elif selected_odd_col_name == "Odd_X2" and game_row['Result_FT'] in ['D', 'A']: result_status = "WIN"
    
    # Ambas Marcam
    elif selected_odd_col_name == "Odd_BTTS_Yes" and game_row['BTTS_Yes_Outcome']: result_status = "WIN"
    elif selected_odd_col_name == "Odd_BTTS_No" and not game_row['BTTS_Yes_Outcome']: result_status = "WIN"
    
    profit = (odd - 1) if result_status == "WIN" else -1.0
    return result_status, profit

# --- <NOVO> Função de Backtesting ---
def run_backtest(df_filtered, selected_odd_col_name, selected_bet_key):
    """Executa o backtest nos jogos filtrados e retorna os resultados."""
    if df_filtered.empty:
        return pd.DataFrame(), {}

    results = []
    for _, game in df_filtered.iterrows():
        outcome, profit = determine_bet_outcome(game, selected_odd_col_name)
        if outcome:
            results.append({
                'Date': game['Date'],
                'League': game['League'],
                'Home': game['Home'],
                'Away': game['Away'],
                'Score': f"{game['Goals_H_FT']}-{game['Goals_A_FT']}",
                'Bet': selected_bet_key,
                'Odd': game[selected_odd_col_name],
                'Outcome': outcome,
                'Profit': profit
            })

    df_results = pd.DataFrame(results)
    if df_results.empty:
        return pd.DataFrame(), {}
        
    df_results['Cumulative_Profit'] = df_results['Profit'].cumsum()

    # Calcular Métricas
    total_bets = len(df_results)
    wins = len(df_results[df_results['Outcome'] == 'WIN'])
    win_rate = (wins / total_bets) * 100 if total_bets > 0 else 0
    total_staked = total_bets # 1 unidade por aposta
    net_profit = df_results['Profit'].sum()
    roi = (net_profit / total_staked) * 100 if total_staked > 0 else 0
    avg_odd = df_results['Odd'].mean()
    avg_win_odd = df_results[df_results['Outcome'] == 'WIN']['Odd'].mean()


    metrics = {
        "total_bets": total_bets,
        "win_rate": win_rate,
        "net_profit": net_profit,
        "roi": roi,
        "avg_odd": avg_odd,
        "avg_win_odd": avg_win_odd
    }

    return df_results, metrics


# --- Interface do Streamlit ---

# --- Carregar Dados ---
GITHUB_RAW_URL = "https://raw.githubusercontent.com/81matheus/BasedeDadosBet365/main/pagesbet365/Exel-Base_de_Dados_Bet365_FiltradaCompleta.xlsx"
df_original = load_data(GITHUB_RAW_URL)


st.title("BetAnalyzer 🔬 - Construtor de Estratégias")
st.caption("Crie, teste e valide suas estratégias de apostas com dados históricos.")

if df_original.empty:
    st.warning("Não foi possível carregar os dados. Verifique a URL ou a conexão.")
else:
    # --- Coluna de Filtros (Sidebar) ---
    with st.sidebar:
        st.image("https://i.imgur.com/V9Lcw00.png", width=50)
        st.header("Filtros da Estratégia")

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

    # --- Área de Resultados ---
    if run_analysis:
        matched_games = []
        with st.spinner(f"Analisando milhares de jogos... Por favor, aguarde."):
            # Filtragem dos jogos
            df_filtered_by_odd = df_original[
                (df_original[selected_odd_column_name] >= min_odd) &
                (df_original[selected_odd_column_name] <= max_odd)
            ].copy()

            # Loop para aplicar filtros históricos (que não podem ser vetorizados facilmente)
            for index, game in df_filtered_by_odd.iterrows():
                # Condições para pular o jogo rapidamente se não atender
                passes_filters = True
                
                # Histórico do Time da Casa
                home_hist = get_team_last_n_games(df_original, game['Home'], game['Date'], n_games_home)
                if len(home_hist) < n_games_home: continue
                
                avg_goals_h = calculate_avg_goals_scored(home_hist, game['Home'])
                if not (min_avg_goals_home <= avg_goals_h <= max_avg_goals_home): continue
                
                win_rate_h = calculate_win_rate(home_hist, game['Home'])
                if not (min_win_rate_home <= win_rate_h <= max_win_rate_home): continue

                # Histórico do Time Visitante
                away_hist = get_team_last_n_games(df_original, game['Away'], game['Date'], n_games_away)
                if len(away_hist) < n_games_away: continue

                avg_goals_a = calculate_avg_goals_scored(away_hist, game['Away'])
                if not (min_avg_goals_away <= avg_goals_a <= max_avg_goals_away): continue

                win_rate_a = calculate_win_rate(away_hist, game['Away'])
                if not (min_win_rate_away <= win_rate_a <= max_win_rate_away): continue
                
                # Se passou em todos os filtros, adiciona à lista
                matched_games.append(game)
        
        df_matched = pd.DataFrame(matched_games)
        
        st.success(f"Análise concluída! {len(df_matched)} jogos encontrados que correspondem à sua estratégia.")

        if not df_matched.empty:
            # --- <NOVO> Executa a função de backtest e obtém os resultados ---
            df_results, metrics = run_backtest(df_matched, selected_odd_column_name, selected_bet_key)

            # --- <NOVO> Exibição dos KPIs ---
            st.header("📈 Resultados do Backtest")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Apostas", f"{metrics['total_bets']}", help="Número de jogos que corresponderam aos filtros.")
            col2.metric("Taxa de Acerto", f"{metrics['win_rate']:.2f}%", help="Percentual de apostas vencedoras.")
            col3.metric("Lucro/Prejuízo Líquido", f"{metrics['net_profit']:.2f} un.", help="Lucro total em unidades (stake de 1 un. por aposta).")
            col4.metric("ROI (Retorno s/ Invest.)", f"{metrics['roi']:.2f}%", "Lucro líquido / Total apostado. A métrica chave de eficiência.",
                        delta_color=("inverse" if metrics['roi'] < 0 else "normal"))

            c1, c2 = st.columns(2)
            c1.metric("Odd Média da Estratégia", f"{metrics['avg_odd']:.2f}")
            c2.metric("Odd Média das Vitórias", f"{metrics['avg_win_odd']:.2f}")
            
            # --- <NOVO> Gráfico de Lucro Cumulativo ---
            st.subheader("Evolução do Lucro (Bankroll)")
            st.line_chart(df_results, x='Date', y='Cumulative_Profit')

            # --- Tabela com os jogos ---
            with st.expander("Ver todos os jogos analisados no backtest"):
                st.dataframe(df_results, use_container_width=True)

        else:
            st.info("Nenhum jogo encontrado com os critérios definidos. Tente filtros mais flexíveis.")
    else:
        st.info("Configure os filtros na barra lateral e clique em 'Executar Backtest' para começar.")
        if not df_original.empty:
            st.write("Amostra da base de dados carregada:")
            st.dataframe(df_original.head())
