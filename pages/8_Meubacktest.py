import streamlit as st
import pandas as pd
import numpy as np
import io
import requests # Se for carregar do GitHub

# --- Constantes e Funções Auxiliares (Copie as relevantes da sua versão anterior) ---
# EXPECTED_COLUMNS, ODD_COLUMNS_TO_CONVERT, GOAL_COLUMNS_TO_CONVERT
# load_data_from_github (se usar) ou load_dataframe_local
# get_team_history
# engineer_historical_features_expanded (ESSENCIAL!)
# Funções de checagem de condição (check_sequence_result, check_count_result, etc. - ESSENCIAIS!)
# simulate_strategy (ESSENCIAL!)

# --- COLUNAS ESPERADAS (AJUSTE CONFORME SUA PLANILHA FINAL) ---
EXPECTED_COLUMNS = [
    'Date', 'League', 'Season', 'Home', 'Away',
    'Odd_H_HT', 'Odd_D_HT', 'Odd_A_HT', 'Odd_Over05_HT', 'Odd_Under05_HT',
    'Odd_Over15_HT', 'Odd_Under15_HT', 'Odd_Over25_HT', 'Odd_Under25_HT',
    'Odd_H_FT', 'Odd_D_FT', 'Odd_A_FT', 'Odd_1X', 'Odd_12', 'Odd_X2',
    'Odd_Over05_FT', 'Odd_Under05_FT', 'Odd_Over15_FT', 'Odd_Under15_FT',
    'Odd_Over25_FT', 'Odd_Under25_FT', 'Odd_Over35_FT', 'Odd_Under35_FT',
    'Odd_Over45_FT', 'Odd_Under45_FT', 'Odd_BTTS_Yes', 'Odd_BTTS_No',
    'Goals_H_HT', 'Goals_A_HT', 'Goals_H_FT', 'Goals_A_FT'
    # Se 'Goals_Min_H' e 'Goals_Min_A' forem usadas, adicione-as e trate-as
]
ODD_COLUMNS_TO_CONVERT = [col for col in EXPECTED_COLUMNS if "Odd_" in col]
GOAL_COLUMNS_TO_CONVERT = ['Goals_H_HT', 'Goals_A_HT', 'Goals_H_FT', 'Goals_A_FT']


# %%%%%%%%%% INÍCIO: COLE AQUI AS FUNÇÕES DA SUA VERSÃO ANTERIOR %%%%%%%%%%
# load_and_prepare_data (Ajustada para usar as listas de colunas globais)
# get_team_history
# engineer_historical_features_expanded
# check_sequence_result
# check_count_result
# check_goals_metric_value
# check_goals_metric_each_game
# simulate_strategy
# (Certifique-se de que essas funções estejam completas e corretas)

@st.cache_data(ttl=3600)
def load_data_from_github_cached(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content), engine='openpyxl')
        st.success("Base de dados carregada com sucesso do GitHub!")
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do GitHub: {e}")
        return None

def load_and_prepare_data(df_input, expected_cols_list, odd_cols_list, goal_cols_convert_list):
    if df_input is None:
        return None
    df = df_input.copy()

    if 'ate' in df.columns and 'Date' not in df.columns:
        df.rename(columns={'ate': 'Date'}, inplace=True)

    actual_cols_in_file = df.columns.tolist()
    cols_to_use_from_expected = [col for col in expected_cols_list if col in actual_cols_in_file]
    missing_from_expected = [col for col in expected_cols_list if col not in actual_cols_in_file]
    if missing_from_expected:
        st.warning(f"Colunas esperadas não encontradas: {missing_from_expected}")

    if not cols_to_use_from_expected:
        st.error("Nenhuma das colunas esperadas foi encontrada.")
        return None
    df = df[cols_to_use_from_expected].copy()

    if 'Date' not in df.columns:
        st.error("Coluna 'Date' é essencial e não foi encontrada.")
        return None
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

    for col in goal_cols_convert_list:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in odd_cols_list:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')

    essential_cols_for_logic = ['Date', 'Home', 'Away', 'Goals_H_FT', 'Goals_A_FT', 'Odd_H_FT']
    if any(col not in df.columns for col in essential_cols_for_logic):
        st.error("Colunas essenciais para lógica (Data, Times, Gols, Odd_H_FT) estão faltando.")
        return None
        
    df.dropna(subset=essential_cols_for_logic, inplace=True)
    if df.empty:
        st.info("DataFrame vazio após remover NaNs em colunas essenciais.")
        return None

    df['Result_H'] = df.apply(lambda r: 'W' if r['Goals_H_FT'] > r['Goals_A_FT'] else ('D' if r['Goals_H_FT'] == r['Goals_A_FT'] else 'L'), axis=1)
    df['Result_A'] = df.apply(lambda r: 'W' if r['Goals_A_FT'] > r['Goals_H_FT'] else ('D' if r['Goals_A_FT'] == r['Goals_H_FT'] else 'L'), axis=1)
    df.sort_values(by='Date', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def get_team_history(df_all_matches, team_name, current_match_date, num_matches):
    team_matches = df_all_matches[
        ((df_all_matches['Home'] == team_name) | (df_all_matches['Away'] == team_name)) &
        (df_all_matches['Date'] < current_match_date)
    ].copy()
    team_matches.sort_values(by='Date', ascending=False, inplace=True)
    history = []
    for _i, game in team_matches.head(num_matches).iterrows():
        is_home = game['Home'] == team_name
        goals_h = game.get('Goals_H_FT', 0)
        goals_a = game.get('Goals_A_FT', 0)
        result_h_val = game.get('Result_H', 'U')
        result_a_val = game.get('Result_A', 'U')
        history.append({
            'result': result_h_val if is_home else result_a_val,
            'goals_for': goals_h if is_home else goals_a,
            'goals_against': goals_a if is_home else goals_h
        })
    return history

def engineer_historical_features_expanded(df_input, max_lookback=10):
    if df_input is None or df_input.empty:
        st.warning("DataFrame de entrada para engenharia de features está vazio. Nenhuma feature será calculada.")
        return pd.DataFrame() # Retorna um DataFrame vazio para evitar erros subsequentes

    df = df_input.copy() # Trabalhar com uma cópia
    st.info(f"Iniciando engenharia de features para {len(df)} jogos (max_lookback={max_lookback})...")
    
    feature_cols_to_init = {'Results': [], 'GF': [], 'GA': [], 'GD': [], 'BTTS_Y_List': [], 'TotalGoals_List': [], 'CS_List': []}
    agg_cols_to_init = {'WinCount': 0, 'LossCount': 0, 'DrawCount': 0, 'AvgGF': 0.0, 'AvgGA': 0.0, 'TotalCS': 0, 'TotalBTTS_Y': 0, 'TotalGD': 0, 'NoScoreCount': 0}

    for n_val in range(1, max_lookback + 1):
        for team_prefix in ['H', 'A']:
            for col_name, init_val_list in feature_cols_to_init.items():
                df[f'{team_prefix}_Last{n_val}_{col_name}'] = [list(init_val_list) for _ in range(len(df))]
            for col_name, init_val_scalar in agg_cols_to_init.items():
                df[f'{team_prefix}_Last{n_val}_{col_name}'] = init_val_scalar

     total_rows = len(df)
    # Adicionar verificação de total_rows antes de criar a barra de progresso e iterar
    if total_rows == 0:
        st.warning("DataFrame tem 0 linhas após a cópia. Nenhuma feature será calculada.")
        progress_bar_features.empty() # Limpa a barra se ela foi criada antes e o df ficou vazio
        return df # Retorna o DataFrame (agora vazio ou como estava)

    progress_bar_features = st.progress(0)
    for index, row in df.iterrows():
        # Sua lógica de atualização da barra de progresso
        # Garantir que total_rows é > 0 aqui por segurança, embora a verificação acima deva cobrir
        if total_rows > 0:
            progress_value = min(1.0, (float(index) + 1.0) / float(total_rows)) # Força float e limita a 1.0
            progress_bar_features.progress(progress_value)
        else:
            # Isso não deveria acontecer se a checagem anterior de total_rows funcionou
            pass

        for team_prefix, team_name_col in [('H', 'Home'), ('A', 'Away')]:
            team_name = row[team_name_col]
            full_hist = get_team_history(df, team_name, row['Date'], max_lookback)
            for n_val_loop in range(1, max_lookback + 1):
                if len(full_hist) >= n_val_loop:
                    current_n_hist = full_hist[:n_val_loop]
                    results_l = [h['result'] for h in current_n_hist]
                    gf_l = [h['goals_for'] for h in current_n_hist]
                    ga_l = [h['goals_against'] for h in current_n_hist]
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_Results'] = results_l
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_GF'] = gf_l
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_GA'] = ga_l
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_GD'] = [gfi - gai for gfi, gai in zip(gf_l, ga_l)]
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_BTTS_Y_List'] = [gfi > 0 and gai > 0 for gfi, gai in zip(gf_l, ga_l)]
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_TotalGoals_List'] = [gfi + gai for gfi, gai in zip(gf_l, ga_l)]
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_CS_List'] = [gai == 0 for gai in ga_l]
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_WinCount'] = results_l.count('W')
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_LossCount'] = results_l.count('L')
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_DrawCount'] = results_l.count('D')
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_AvgGF'] = np.mean(gf_l) if gf_l else 0.0
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_AvgGA'] = np.mean(ga_l) if ga_l else 0.0
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_TotalCS'] = sum(df.at[index, f'{team_prefix}_Last{n_val_loop}_CS_List'])
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_TotalBTTS_Y'] = sum(df.at[index, f'{team_prefix}_Last{n_val_loop}_BTTS_Y_List'])
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_TotalGD'] = sum(df.at[index, f'{team_prefix}_Last{n_val_loop}_GD'])
                    df.at[index, f'{team_prefix}_Last{n_val_loop}_NoScoreCount'] = sum(1 for g in gf_l if g == 0)
    progress_bar_features.empty() # Limpa a barra ao final
    st.success("Engenharia de features concluída.")
    return df

def check_sequence_result(row, team_prefix, n_games, result_char, mode='all'):
    results_col = f'{team_prefix}_Last{n_games}_Results'
    if not (results_col in row and isinstance(row[results_col], list) and len(row[results_col]) == n_games): return False
    sequence = row[results_col]
    if mode == 'all': return all(r == result_char for r in sequence)
    if mode == 'none': return not any(r == result_char for r in sequence)
    if mode == 'any': return any(r == result_char for r in sequence)
    return False

def check_count_result(row, team_prefix, n_games, result_char_or_metric, comparison, value):
    count_col_map = {'W': 'WinCount', 'L': 'LossCount', 'D': 'DrawCount', 'CS': 'TotalCS', 'BTTS_Y': 'TotalBTTS_Y', 'NoScore': 'NoScoreCount'}
    if result_char_or_metric not in count_col_map: return False
    count_col = f'{team_prefix}_Last{n_games}_{count_col_map[result_char_or_metric]}'
    if count_col not in row or pd.isna(row[count_col]): return False
    actual_count = row[count_col]
    ops = {'>=': actual_count >= value, '==': actual_count == value, '<=': actual_count <= value, '>': actual_count > value, '<': actual_count < value}
    return ops.get(comparison, False)

def check_goals_metric_value(row, team_prefix, n_games, metric_prefix, comparison, value):
    metric_col = f'{team_prefix}_Last{n_games}_{metric_prefix}'
    if metric_col not in row or pd.isna(row[metric_col]): return False
    metric_val = row[metric_col]
    ops = {'>=': metric_val >= value, '==': metric_val == value, '<=': metric_val <= value, '>': metric_val > value, '<': metric_val < value}
    return ops.get(comparison, False)

def check_goals_metric_each_game(row, team_prefix, n_games, metric_list_suffix, comparison, value):
    metric_list_col = f'{team_prefix}_Last{n_games}_{metric_list_suffix}'
    if not (metric_list_col in row and isinstance(row[metric_list_col], list) and len(row[metric_list_col]) == n_games): return False
    sequence = row[metric_list_col]
    if not sequence: return False
    ops_map = { '>=': lambda g, v: g >= v, '==': lambda g, v: g == v, '<=': lambda g, v: g <= v, '>': lambda g, v: g > v, '<': lambda g, v: g < v}
    op_func = ops_map.get(comparison)
    if not op_func: return False
    return all(op_func(g_val, value) for g_val in sequence)

def simulate_strategy(df_filtered, strategy_name, target_market_col, stake=1, commission=0.00):
    if df_filtered.empty:
        return {'strategy_name': strategy_name, 'num_games': 0, 'num_wins': 0, 'win_rate': 0, 'total_staked': 0, 'total_return': 0, 'profit': 0, 'roi': 0, 'avg_odd_staked': np.nan}

    strategy_games = df_filtered.copy() # Já foi filtrado
    if target_market_col not in strategy_games.columns or strategy_games[target_market_col].isnull().all():
        st.warning(f"Coluna de odd '{target_market_col}' não encontrada ou toda NaN para '{strategy_name}'.")
        return {'strategy_name': strategy_name, 'num_games': len(strategy_games), 'num_wins': 0, 'win_rate': 0, 'total_staked': 0, 'total_return': 0, 'profit': 0, 'roi': 0, 'avg_odd_staked': np.nan}

    strategy_games[target_market_col] = pd.to_numeric(strategy_games[target_market_col], errors='coerce')
    strategy_games.dropna(subset=[target_market_col, 'Goals_H_FT', 'Goals_A_FT'], inplace=True)
    strategy_games = strategy_games[strategy_games[target_market_col] > 1.0]

    num_games_valid_odds = len(strategy_games)
    if num_games_valid_odds == 0:
         return {'strategy_name': strategy_name, 'num_games': 0, 'num_wins': 0, 'win_rate': 0, 'total_staked': 0, 'total_return': 0, 'profit': 0, 'roi': 0, 'avg_odd_staked': np.nan}

    total_staked_val, total_return_val, num_wins_val = 0.0, 0.0, 0
    for _index, game in strategy_games.iterrows():
        odd = game[target_market_col]
        total_staked_val += float(stake)
        bet_won_flag = False
        goals_h_ft = float(game['Goals_H_FT'])
        goals_a_ft = float(game['Goals_A_FT'])
        if target_market_col == 'Odd_H_FT' and goals_h_ft > goals_a_ft: bet_won_flag = True
        elif target_market_col == 'Odd_A_FT' and goals_a_ft > goals_h_ft: bet_won_flag = True
        # Adicionar mais mercados aqui...
        
        if bet_won_flag:
            num_wins_val += 1
            total_return_val += float(stake) * float(odd) * (1.0 - float(commission))
    profit_val = total_return_val - total_staked_val
    roi_val = (profit_val / total_staked_val) if total_staked_val > 0 else 0.0
    win_rate_val = (float(num_wins_val) / num_games_valid_odds) if num_games_valid_odds > 0 else 0.0
    avg_odd_staked_val = strategy_games[target_market_col].mean() if num_games_valid_odds > 0 else np.nan
    return {'strategy_name': strategy_name, 'num_games': num_games_valid_odds, 'num_wins': num_wins_val, 'win_rate': win_rate_val, 'total_staked': total_staked_val, 'total_return': total_return_val, 'profit': profit_val, 'roi': roi_val, 'avg_odd_staked': avg_odd_staked_val}

# %%%%%%%%%% FIM: COLE AQUI AS FUNÇÕES DA SUA VERSÃO ANTERIOR %%%%%%%%%%


# --- Definição da Interface Streamlit ---
st.set_page_config(layout="wide", page_title="Backtesting Dinâmico de Futebol")
st.title("⚽ Backtesting Dinâmico de Estratégias de Futebol")

# --- Carregamento de Dados ---
if 'df_historico_raw' not in st.session_state:
    st.session_state.df_historico_raw = None
if 'df_historico_prepared' not in st.session_state:
    st.session_state.df_historico_prepared = None
if 'df_historico_featured' not in st.session_state:
    st.session_state.df_historico_featured = None # Para guardar o DF com features

# Opção de carregar do GitHub ou localmente
data_source = st.sidebar.radio("Fonte dos Dados Históricos:", ("GitHub (Recomendado)", "Upload Local"))
github_url = "https://raw.githubusercontent.com/81matheus/BasedeDadosBet365/main/pagesbet365/Exel-Base_de_Dados_Bet365_FiltradaCompleta.xlsx" # URL Padrão

if data_source == "GitHub (Recomendado)":
    if st.sidebar.button("Carregar Dados do GitHub"):
        with st.spinner("Carregando dados do GitHub..."):
            st.session_state.df_historico_raw = load_data_from_github_cached(github_url)
            st.session_state.df_historico_prepared = None # Resetar preparado e features
            st.session_state.df_historico_featured = None
            st.rerun() # Força o rerun para atualizar a interface com os dados carregados
else:
    uploaded_file_local = st.sidebar.file_uploader("Upload da Base Histórica (.xlsx ou .csv)", type=["xlsx", "csv"])
    if uploaded_file_local is not None:
        if st.session_state.df_historico_raw is None: # Carrega só se não tiver sido carregado antes
             with st.spinner("Carregando arquivo local..."):
                # Para upload local, vamos usar uma função simples de leitura que não está no cache_data
                # Você pode adaptar a load_dataframe_local que você já tem
                try:
                    if uploaded_file_local.name.endswith('.xlsx'):
                        st.session_state.df_historico_raw = pd.read_excel(uploaded_file_local)
                    else:
                        st.session_state.df_historico_raw = pd.read_csv(uploaded_file_local, sep=None, engine='python') # Tenta detectar sep
                    st.sidebar.success("Arquivo local carregado!")
                    st.session_state.df_historico_prepared = None
                    st.session_state.df_historico_featured = None
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Erro ao ler arquivo local: {e}")
                    st.session_state.df_historico_raw = None


if st.session_state.df_historico_raw is None:
    st.warning("Por favor, carregue a base de dados histórica para começar.")
    st.stop()

# Prepara os dados se ainda não foram preparados
if st.session_state.df_historico_prepared is None and st.session_state.df_historico_raw is not None:
    with st.spinner("Preparando dados históricos (limpeza, ordenação)..."):
        st.session_state.df_historico_prepared = load_and_prepare_data(
            st.session_state.df_historico_raw,
            EXPECTED_COLUMNS,
            ODD_COLUMNS_TO_CONVERT,
            GOAL_COLUMNS_TO_CONVERT
        )
    if st.session_state.df_historico_prepared is None:
        st.error("Falha ao preparar os dados históricos.")
        st.stop()
    # st.success("Dados históricos preparados.")

df_prepared = st.session_state.df_historico_prepared

# --- Filtros Globais ---
st.sidebar.header("Filtros Globais")
# Datas
try:
    min_date = df_prepared['Date'].min().date()
    max_date = df_prepared['Date'].max().date()
    selected_date_range = st.sidebar.date_input(
        "Intervalo de Datas:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="date_filter_main"
    )
    start_date, end_date = selected_date_range
    df_filtered_global = df_prepared[(df_prepared['Date'].dt.date >= start_date) & (df_prepared['Date'].dt.date <= end_date)]
except Exception as e:
    st.sidebar.error(f"Erro ao configurar filtro de data: {e}. Usando dados completos.")
    df_filtered_global = df_prepared.copy()


# Ligas
available_leagues = sorted(df_filtered_global['League'].unique())
selected_leagues = st.sidebar.multiselect(
    "Filtrar por Ligas:",
    options=available_leagues,
    default=available_leagues[:min(5, len(available_leagues))], # Default para as primeiras 5 ou todas
    key="league_filter_main"
)
if selected_leagues:
    df_filtered_global = df_filtered_global[df_filtered_global['League'].isin(selected_leagues)]

if df_filtered_global.empty:
    st.warning("Nenhum jogo encontrado com os filtros de data e liga selecionados.")
    st.stop()

# --- Mercado Principal para Backtest ---
st.sidebar.header("Mercado para Backtest")
mercado_principal_options = {
    "Vitória Casa (FT)": "Odd_H_FT",
    "Empate (FT)": "Odd_D_FT",
    "Vitória Visitante (FT)": "Odd_A_FT",
    "Over 2.5 Gols (FT)": "Odd_Over25_FT",
    "Under 2.5 Gols (FT)": "Odd_Under25_FT",
    "Ambos Marcam - Sim (FT)": "Odd_BTTS_Yes",
    "Ambos Marcam - Não (FT)": "Odd_BTTS_No",
    # Adicionar mais mercados FT e HT se desejar
}
selected_mercado_label = st.sidebar.selectbox(
    "Selecione o mercado principal:",
    options=list(mercado_principal_options.keys()),
    key="main_market_select"
)
selected_mercado_odd_col = mercado_principal_options[selected_mercado_label]


# --- Engenharia de Features (se necessário e ainda não feita para o N máximo) ---
MAX_LOOKBACK_USER = st.sidebar.slider("Máximo de jogos no histórico a considerar (N):", 1, 10, 5, key="max_lookback_slider")

# Verifica se as features precisam ser recalculadas
recalculate_features = False
if st.session_state.df_historico_featured is None:
    recalculate_features = True
else:
    # Verifica se o max_lookback atual é maior que o usado anteriormente
    # Precisamos de uma forma de saber qual foi o max_lookback usado para gerar df_historico_featured
    # Por simplicidade, vamos recalcular se o df_filtered_global mudou ou se o slider mudou significativamente.
    # Uma forma mais robusta seria armazenar o max_lookback usado em st.session_state.
    if 'last_max_lookback_used' not in st.session_state or st.session_state.last_max_lookback_used != MAX_LOOKBACK_USER:
        recalculate_features = True
    # Adicionar outras condições que invalidariam o cache de features, ex: mudança no df_prepared

if recalculate_features and not df_filtered_global.empty:
    with st.spinner(f"Calculando features de histórico (até {MAX_LOOKBACK_USER} jogos)... Por favor, aguarde."):
        # É importante passar uma cópia do df_filtered_global aqui
        st.session_state.df_historico_featured = engineer_historical_features_expanded(df_filtered_global.copy(), max_lookback=MAX_LOOKBACK_USER)
        st.session_state.last_max_lookback_used = MAX_LOOKBACK_USER # Armazena o lookback usado
    if st.session_state.df_historico_featured.empty and not df_filtered_global.empty:
        st.warning("Engenharia de features resultou em DataFrame vazio. Verifique os dados ou o processo de feature engineering.")
        st.stop()
    # st.success("Features de histórico calculadas/atualizadas.")

df_featured = st.session_state.df_historico_featured if st.session_state.df_historico_featured is not None else pd.DataFrame()

if df_featured.empty and not df_filtered_global.empty:
    st.warning("DataFrame com features está vazio. Não é possível construir estratégias.")
    # Não necessariamente st.stop() aqui, pois pode ser que o usuário ainda não clicou para calcular features
    # Mas a seção de filtros não funcionará.

# --- Interface de Criação de Estratégia Interativa ---
st.header("🛠️ Construtor de Estratégia")

if 'current_filters' not in st.session_state:
    st.session_state.current_filters = [] # Lista para armazenar os filtros adicionados

# --- Formulário para adicionar novo filtro ---
filter_types = [
    "Resultado da Equipe", "Gols Marcados (GF)", "Gols Sofridos (GA)",
    "Saldo de Gols (GD)", "Clean Sheets (CS)", "Jogos Sem Marcar (NoScore)",
    "BTTS nos Jogos", "Total de Gols nos Jogos", "Odd do Jogo Atual"
]
comparisons_numeric = {">=": ">=", "==": "==", "<=": "<=", ">": ">", "<": "<"}
comparisons_sequence = {"Todos Iguais a": "all", "Nenhum Igual a": "none", "Pelo Menos Um Igual a": "any"}


with st.expander("Adicionar Novo Filtro à Estratégia", expanded=True):
    cols_filter_form = st.columns([2,1,1,2,1,1]) # Ajuste o layout conforme necessário
    
    with cols_filter_form[0]:
        filter_type = st.selectbox("Tipo de Filtro:", filter_types, key="new_filter_type")
    with cols_filter_form[1]:
        team_apply = st.selectbox("Aplicar a:", ["Casa (H)", "Visitante (A)", "Ambos", "Jogo Atual"], key="new_filter_team",
                                  disabled=(filter_type == "Odd do Jogo Atual"))
    with cols_filter_form[2]:
        n_games_history = st.number_input("Nº Jogos Histórico:", min_value=1, max_value=MAX_LOOKBACK_USER, value=3, step=1, key="new_filter_n_games",
                                          disabled=(filter_type == "Odd do Jogo Atual"))
    
    # Parâmetros dinâmicos baseados no tipo de filtro
    param1_val, param2_val, param3_val = None, None, None
    
    if filter_type == "Resultado da Equipe":
        with cols_filter_form[3]:
            param1_val = st.selectbox("Métrica:", list(comparisons_sequence.keys()) + ["Contagem de Resultados"], key="res_metric")
        if param1_val == "Contagem de Resultados":
            with cols_filter_form[4]:
                param2_val = st.selectbox("Resultado:", ["W", "D", "L"], key="res_char_count")
            with cols_filter_form[5]:
                param3_val_comp = st.selectbox("Comparação:", list(comparisons_numeric.keys()), key="res_comp_count")
                param3_val_val = st.number_input("Valor:", min_value=0, max_value=n_games_history, value=1, step=1, key="res_val_count")
                param3_val = (param3_val_comp, param3_val_val)
        else: # Sequência
            with cols_filter_form[4]:
                param2_val = st.selectbox("Resultado:", ["W", "D", "L"], key="res_char_seq")
    
    elif filter_type in ["Gols Marcados (GF)", "Gols Sofridos (GA)", "Saldo de Gols (GD)"]:
        metric_map_gfga = {"Gols Marcados (GF)": "GF", "Gols Sofridos (GA)": "GA", "Saldo de Gols (GD)": "GD"}
        metric_suffix = metric_map_gfga[filter_type]
        with cols_filter_form[3]:
            param1_val = st.selectbox("Métrica:", ["Média por Jogo", "Total no Período", "Em Cada Jogo"], key=f"{metric_suffix}_metric")
        with cols_filter_form[4]:
            param2_val = st.selectbox("Comparação:", list(comparisons_numeric.keys()), key=f"{metric_suffix}_comp")
        with cols_filter_form[5]:
            param3_val = st.number_input("Valor:", value=1.0, step=0.1, format="%.1f", key=f"{metric_suffix}_val")

    elif filter_type in ["Clean Sheets (CS)", "Jogos Sem Marcar (NoScore)", "BTTS nos Jogos"]:
        metric_map_count = {"Clean Sheets (CS)": "CS", "Jogos Sem Marcar (NoScore)": "NoScore", "BTTS nos Jogos": "BTTS_Y"}
        metric_suffix_count = metric_map_count[filter_type]
        with cols_filter_form[3]: # Único modo é contagem
             param1_val = "Contagem de Ocorrências" # Label informativo
        with cols_filter_form[4]:
            param2_val = st.selectbox("Comparação:", list(comparisons_numeric.keys()), key=f"{metric_suffix_count}_comp")
        with cols_filter_form[5]:
            param3_val = st.number_input("Valor (Contagem):", min_value=0, max_value=n_games_history, value=1, step=1, key=f"{metric_suffix_count}_val")
            
    elif filter_type == "Total de Gols nos Jogos":
        with cols_filter_form[3]:
            param1_val = st.selectbox("Métrica:", ["Média por Jogo", "Em Cada Jogo"], key="tg_metric") # Total não faz muito sentido aqui
        with cols_filter_form[4]:
            param2_val = st.selectbox("Comparação:", list(comparisons_numeric.keys()), key="tg_comp")
        with cols_filter_form[5]:
            param3_val = st.number_input("Valor (Gols):", value=2.5, step=0.1, format="%.1f", key="tg_val")

    elif filter_type == "Odd do Jogo Atual":
        # Coletar todas as colunas de Odd disponíveis no df_featured
        odd_cols_available = [col for col in df_featured.columns if "Odd_" in col and df_featured[col].dtype in [np.float64, np.int64]]
        with cols_filter_form[3]:
            param1_val = st.selectbox("Coluna da Odd:", odd_cols_available, key="odd_col_select")
        with cols_filter_form[4]:
            param2_val = st.selectbox("Comparação:", list(comparisons_numeric.keys()), key="odd_comp")
        with cols_filter_form[5]:
            param3_val = st.number_input("Valor da Odd:", value=1.5, step=0.01, format="%.2f", key="odd_val")


    if st.button("➕ Adicionar Filtro", key="add_filter_btn"):
        if df_featured.empty:
            st.error("Calcule as features de histórico primeiro (ajuste o slider 'Máximo de jogos no histórico').")
        else:
            # Construir a descrição do filtro e a função lambda
            filter_description = f"{filter_type} ({team_apply}, N={n_games_history if filter_type != 'Odd do Jogo Atual' else 'N/A'}): "
            condition_lambda = None
            
            # Simplificação: A lógica exata para construir a lambda para CADA combinação
            # de filtro_type e params é complexa e requer muitos if/elifs.
            # Vou mostrar um exemplo e você precisará expandir.
            
            # Exemplo para "Resultado da Equipe" -> "Sequência"
            if filter_type == "Resultado da Equipe" and param1_val != "Contagem de Resultados":
                mode = comparisons_sequence[param1_val]
                res_char = param2_val
                team_p = 'H' if team_apply == "Casa (H)" else ('A' if team_apply == "Visitante (A)" else None) # Simplificado
                if team_p:
                    filter_description += f"{param1_val} {res_char}"
                    condition_lambda = lambda r, tp=team_p, N=n_games_history, rc=res_char, m=mode: check_sequence_result(r, tp, N, rc, m)
                else: st.error("Selecione 'Casa (H)' ou 'Visitante (A)' para este tipo de filtro.")

            # Exemplo para "Odd do Jogo Atual"
            elif filter_type == "Odd do Jogo Atual":
                odd_col_selected = param1_val
                comp_op = param2_val
                odd_val_thresh = param3_val
                filter_description += f"Odd '{odd_col_selected}' {comp_op} {odd_val_thresh}"
                
                # Cria um dicionário para mapear operadores string para funções
                op_map = {'>=': lambda x, y: x >= y, '==': lambda x, y: x == y, '<=': lambda x, y: x <= y,
                          '>': lambda x, y: x > y, '<': lambda x, y: x < y}
                actual_op_func = op_map.get(comp_op)

                if actual_op_func and odd_col_selected in df_featured.columns:
                     condition_lambda = lambda r, oc=odd_col_selected, opf=actual_op_func, ov=odd_val_thresh: \
                                        pd.notna(r[oc]) and opf(r[oc], ov) if oc in r else False
                else: st.error(f"Operador ou coluna de odd inválida: {odd_col_selected}")


            # ADICIONAR MAIS IF/ELIFS AQUI PARA CADA TIPO DE FILTRO E MÉTRICA
            # Esta é a parte mais trabalhosa para tornar totalmente dinâmico.
            
            if condition_lambda:
                st.session_state.current_filters.append({
                    "description": filter_description,
                    "condition_func": condition_lambda,
                    "id": len(st.session_state.current_filters) # Para ter um ID único para remoção
                })
                st.success(f"Filtro adicionado: {filter_description}")
            elif filter_type != "Odd do Jogo Atual": # Não mostrar erro se for Odd e não tiver lambda ainda
                st.warning("Lógica para este tipo de filtro ainda não implementada completamente no exemplo.")


# --- Exibir Filtros Atuais e Opção de Remover ---
st.subheader("Filtros da Estratégia Atual:")
if not st.session_state.current_filters:
    st.info("Nenhum filtro adicionado ainda.")
else:
    for i, f in enumerate(st.session_state.current_filters):
        cols_display_filter = st.columns([3,1])
        cols_display_filter[0].write(f"{i+1}. {f['description']}")
        if cols_display_filter[1].button("Remover", key=f"remove_filter_{f['id']}"):
            st.session_state.current_filters = [filt for filt in st.session_state.current_filters if filt['id'] != f['id']]
            st.rerun() # Rerun para atualizar a lista de filtros

    # Opção de lógica E/OU (simplificado para 'E' por enquanto)
    # filter_logic = st.radio("Combinar filtros usando:", ("E (AND)", "OU (OR)"), key="filter_logic_radio", horizontal=True)
    filter_logic = "AND" # Hardcoded para simplificar


# --- Executar Backtest ---
if st.button("🚀 Executar Backtest com Estratégia Atual", type="primary", disabled=df_featured.empty or not st.session_state.current_filters):
    if df_featured.empty:
        st.error("Os dados com features de histórico não estão prontos. Ajuste o slider e aguarde o cálculo.")
    elif not st.session_state.current_filters:
        st.error("Adicione pelo menos um filtro para a estratégia.")
    else:
        df_to_backtest = df_featured.copy()
        
        st.write("Aplicando filtros...")
        combined_mask = pd.Series(True, index=df_to_backtest.index) # Começa com todos True para AND

        for f_dict in st.session_state.current_filters:
            try:
                current_mask = df_to_backtest.apply(f_dict['condition_func'], axis=1)
                if filter_logic == "AND":
                    combined_mask &= current_mask
                # else: # Lógica OR (não implementada neste exemplo simplificado)
                #    combined_mask |= current_mask
            except Exception as e_apply:
                st.error(f"Erro ao aplicar filtro '{f_dict['description']}': {e}. Este filtro será ignorado.")
                # Não modificar combined_mask se um filtro falhar, para não quebrar tudo

        df_strategy_games = df_to_backtest[combined_mask]
        
        st.write(f"Número de jogos encontrados após aplicar {len(st.session_state.current_filters)} filtros: {len(df_strategy_games)}")

        if not df_strategy_games.empty:
            strategy_name_user = "Estrategia_Dinamica_Usuario" # Pode ser gerado a partir das descrições dos filtros
            
            # Pegar comissão do usuário
            commission_user = st.sidebar.number_input("Comissão da Bolsa (ex: 0.02 para 2%):", min_value=0.0, max_value=0.2, value=0.02, step=0.005, format="%.3f")

            with st.spinner(f"Executando simulação no mercado '{selected_mercado_label}'..."):
                results = simulate_strategy(
                    df_strategy_games,
                    strategy_name_user,
                    selected_mercado_odd_col,
                    commission=commission_user
                )
            
            st.subheader("Resultados do Backtest:")
            col_res1, col_res2, col_res3, col_res4 = st.columns(4)
            col_res1.metric("Nº de Jogos", results['num_games'])
            col_res2.metric("Taxa de Acerto", f"{results['win_rate']:.2%}")
            col_res3.metric("Lucro Total", f"{results['profit']:.2f} unidades")
            col_res4.metric("ROI", f"{results['roi']:.2%}")
            st.metric("Odd Média Apostada", f"{results['avg_odd_staked']:.2f}" if pd.notna(results['avg_odd_staked']) else "N/A")

            if results['num_games'] > 0:
                st.write("Amostra dos jogos que passaram nos filtros:")
                st.dataframe(df_strategy_games[['Date', 'League', 'Home', 'Away', 'Goals_H_FT', 'Goals_A_FT', selected_mercado_odd_col]].head(20))
        else:
            st.info("Nenhum jogo correspondeu à combinação de filtros selecionada.")

elif not df_featured.empty and not st.session_state.current_filters:
    st.info("Adicione filtros para construir sua estratégia e executar o backtest.")
elif df_featured.empty and not df_filtered_global.empty :
     st.info("Aguardando cálculo das features de histórico. Ajuste o slider 'Máximo de jogos no histórico' se necessário.")
