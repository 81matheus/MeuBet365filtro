import streamlit as st
import pandas as pd
import numpy as np
import io # Necessário para ler o buffer do arquivo carregado e da web
import re # Para extrair partes dos nomes das estratégias combinadas
import requests # Para buscar dados do GitHub
from io import BytesIO # Importado da API
import warnings # Importado da API
from datetime import date # Para o st.date_input

warnings.filterwarnings("ignore") # Da API

# --- FUNÇÕES DA API FUTPYTHONTRADER ---
def drop_reset_index(df): # Função da API
    df = df.dropna()
    df = df.reset_index(drop=True)
    df.index += 1
    return df

@st.cache_data(ttl=3600) # Cacheia os dados por 1 hora
def obter_dados_github(file_path): # Função da API adaptada para Streamlit
    """Função para obter dados do repositório GitHub"""
    GITHUB_API_URL = "https://api.github.com/repos"
    OWNER = "futpythontrader"
    REPO = "FutPythonTrader"
    # ATENÇÃO: O token abaixo é o fornecido no exemplo.
    # Em um ambiente de produção, gerencie tokens de forma segura (ex: Streamlit secrets).
    #TOKEN = "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"
    TOKEN = "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"

    url = f"{GITHUB_API_URL}/{OWNER}/{REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {TOKEN}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        download_url = data['download_url']
        content_response = requests.get(download_url, headers=headers)
        content_response.raise_for_status() # Adicionado para verificar download do conteúdo
        content = content_response.content
        df = pd.read_csv(io.BytesIO(content)) # API especifica CSV
        st.success(f"Dados de '{file_path}' carregados com sucesso do GitHub!")
        return drop_reset_index(df)
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            st.error(f"Erro ao acessar os dados: Arquivo '{file_path}' não encontrado no repositório. (404)")
        else:
            st.error(f"Erro HTTP ao acessar os dados de '{file_path}': {http_err} (Status: {response.status_code})")
        return None
    except Exception as e:
        st.error(f"Erro ao acessar os dados de '{file_path}': {e}")
        return None
# --- FIM DAS FUNÇÕES DA API FUTPYTHONTRADER ---


# --- Função Auxiliar para Carregar Dados (Mantida para Upload Local - NÃO USADA NESTE FLUXO MODIFICADO) ---
# Esta função não será chamada no fluxo principal, mas é mantida caso queira reativar o upload local.
def load_dataframe_local(uploaded_file):
    """Carrega um DataFrame de um arquivo XLSX ou CSV carregado via Streamlit."""
    if uploaded_file is None:
        return None
    try:
        file_content = uploaded_file.getvalue()
        if uploaded_file.name.lower().endswith('.xlsx'):
            try:
                df = pd.read_excel(io.BytesIO(file_content), engine='openpyxl')
            except Exception as e_xlsx:
                 st.error(f"Erro ao ler .xlsx: {e_xlsx}. Tente salvar como CSV ou 'Excel 97-2003 Workbook (*.xls)' se possível.")
                 return None
            return df
        elif uploaded_file.name.lower().endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(file_content), sep=',')
                if df.shape[1] <= 1:
                    df = pd.read_csv(io.BytesIO(file_content), sep=';')
            except Exception as e_csv:
                 st.warning(f"Não foi possível determinar o separador CSV automaticamente, tentando ';'. Erro: {e_csv}")
                 try:
                     df = pd.read_csv(io.BytesIO(file_content), sep=';')
                 except Exception as e_final:
                     st.error(f"Falha ao ler o arquivo CSV com separador ',' ou ';'. Verifique o formato. Erro: {e_final}")
                     return None
            if df.empty or df.shape[1] <= 1:
                 st.error("Falha ao ler o arquivo CSV corretamente. Verifique o separador (',' ou ';') e o formato.")
                 return None
            return df
        else:
            st.error("Formato de arquivo não suportado. Use .xlsx ou .csv")
            return None
    except Exception as e:
        st.error(f"Erro geral ao ler o arquivo '{uploaded_file.name}': {e}")
        return None
# --- Fim da Função Auxiliar ---

# --- INÍCIO: Definição das Ligas Aprovadas ---
APPROVED_LEAGUES = set([
    "ARGENTINA 1", "ARGENTINA 2", "AUSTRALIA 1", "AUSTRIA 1", "AUSTRIA 2", "BELGIUM 1", "BELGIUM 2", "BOLIVIA 1", "BRAZIL 1", "BRAZIL 2",
    "BULGARIA 1", "CHILE 1", "CHINA 1", "CHINA 2", "COLOMBIA 1", "COLOMBIA 2", "CROATIA 1", "CZECH 1", "DENMARK 1", "DENMARK 2",
    "ECUADOR 1", "EGYPT 1", "ENGLAND 1", "ENGLAND 2", "ENGLAND 3", "ENGLAND 4", "ENGLAND 5", "ESTONIA 1", "EUROPA CHAMPIONS LEAGUE",
    "EUROPA CONFERENCE LEAGUE", "EUROPA LEAGUE", "FINLAND 1", "FRANCE 1", "GREECE 1", "HUNGARY 1", "IRELAND 1", "IRELAND 2", "ISRAEL 1",
    "ITALY 1", "ITALY 2", "JAPAN 1", "JAPAN 2", "MEXICO 1", "MEXICO 2",  "NETHERLANDS 1", "NETHERLANDS 2", "NORTHERN IRELAND 2", "NORWAY 1",
    "NORWAY 2", "PARAGUAY 1", "PERU 1", "POLAND 1", "POLAND 2", "PORTUGAL 1", "PORTUGAL 2", "ROMANIA 1", "ROMANIA 2", "SAUDI ARABIA 1",
    "SCOTLAND 1", "SCOTLAND 2", "SCOTLAND 3", "SCOTLAND 4", "SERBIA 1",  "SLOVAKIA 1", "SOUTH KOREA 1", "SOUTH KOREA 2", "SPAIN 1", "SPAIN 2",
    "SWEDEN 1", "SWEDEN 2", "SWITZERLAND 1", "SWITZERLAND 2", "TURKEY 1", "TURKEY 2", "UKRAINE 1", "URUGUAY 1", "USA 1", "VENEZUELA 1", "WALES 1"
])
# --- FIM: Definição das Ligas Aprovadas ---

# --- INÍCIO: Definição das Estratégias Correct Score Lay a Testar ---
cs_lay_strategies_to_test = [
    'Lay_Hand35_Casa', 'Lay_Hand45_Casa', 'Lay_Hand35_Fora', 'Lay_Hand45_Fora'
]
# --- FIM: Definição das Estratégias Correct Score Lay a Testar ---

# --- Função para obter a condição de ocorrência do placar ---
# (Mantida como antes)
def get_score_condition(df, cs_lay_name):
    ocorrencias = pd.Series(False, index=df.index)
    try:
        if cs_lay_name == 'Lay_Hand35_Casa':
            ocorrencias = (((df['Goals_H'] ) - ( df['Goals_A'])) > 3)
        elif cs_lay_name == 'Lay_Hand45_Casa':
            ocorrencias = (((df['Goals_H'] ) - ( df['Goals_A'])) > 4)
        elif cs_lay_name == 'Lay_Hand35_Fora':
            ocorrencias = (((df['Goals_H'] ) - ( df['Goals_A'])) < -3)
        elif cs_lay_name == 'Lay_Hand45_Fora':
            ocorrencias = (((df['Goals_H'] ) - ( df['Goals_A'])) < -4)
        else:
            st.warning(f"Nome de estratégia CS Lay desconhecido: {cs_lay_name}")
            ocorrencias = pd.Series(False, index=df.index)
    except KeyError as e:
        st.error(f"Erro em get_score_condition para {cs_lay_name}: Coluna '{e}' ausente.")
        return pd.Series(False, index=df.index)
    if not isinstance(ocorrencias, pd.Series):
         ocorrencias = pd.Series(ocorrencias, index=df.index)
    if ocorrencias.dtype != bool:
         ocorrencias = ocorrencias.fillna(False).astype(bool)
    return ocorrencias

# --- Função de Backtest para COMBINAÇÃO (Filtro VAR + CS Lay) ---
# (Mantida como antes)
def run_combined_backtest(df_filtered_by_var, cs_lay_name, combined_strategy_name, profit_win=0.10, profit_loss=-1.0):
    df_copy = df_filtered_by_var.copy()
    total_jogos = len(df_copy)
    if total_jogos == 0:
        return {
            "Estratégia": combined_strategy_name, "Total de Jogos": 0,
            "Taxa de Acerto": "N/A", "Lucro Total": "0.00", "Dataframe": pd.DataFrame()
        }
    try:
        score_occurred = get_score_condition(df_copy, cs_lay_name)
        if score_occurred is None:
             raise ValueError("Falha ao obter condição de placar.")
        df_copy['Profit'] = np.where(score_occurred, profit_loss, profit_win)
        acertos = (~score_occurred).sum()
        taxa_acerto = acertos / total_jogos
        lucro_total = df_copy['Profit'].sum()
        return {
            "Estratégia": combined_strategy_name, "Total de Jogos": total_jogos,
            "Taxa de Acerto": f"{taxa_acerto:.2%}", "Lucro Total": f"{lucro_total:.2f}",
            "Dataframe": df_copy
        }
    except KeyError as e:
         st.error(f"Erro (KeyError) no backtest de {combined_strategy_name}: Coluna '{e}' ausente no subset filtrado.")
         return { "Estratégia": combined_strategy_name, "Total de Jogos": 0, "Taxa de Acerto": "Erro", "Lucro Total": "0.00", "Dataframe": pd.DataFrame()}
    except Exception as e:
         st.error(f"Erro inesperado no backtest de {combined_strategy_name}: {e}")
         return { "Estratégia": combined_strategy_name, "Total de Jogos": 0, "Taxa de Acerto": "Erro", "Lucro Total": "0.00", "Dataframe": pd.DataFrame()}

# --- Função de Análise de Médias Móveis para COMBINAÇÃO ---
# (Mantida como antes)
def check_combined_moving_averages(df_backtest_result, combined_strategy_name):
    if df_backtest_result is None or df_backtest_result.empty:
        return {
            "Estratégia": combined_strategy_name, "Média 8": "0.00% (0 acertos em 0)",
            "Média 40": "0.00% (0 acertos em 0)", "Lucro Últimos 8": "0.00 (em 0 jogos)",
            "Lucro Últimos 40": "0.00 (em 0 jogos)", "Acima dos Limiares": False
        }
    match = re.search(r'CS_(Lay_\w+)$', combined_strategy_name)
    if not match:
        st.error(f"Não foi possível extrair o nome CS Lay de: {combined_strategy_name}")
        return { "Estratégia": combined_strategy_name, "Média 8": "Erro", "Média 40": "Erro", "Lucro Últimos 8": "Erro", "Lucro Últimos 40": "Erro", "Acima dos Limiares": False }
    cs_lay_name = match.group(1)
    try:
        score_occurred = get_score_condition(df_backtest_result, cs_lay_name)
        if score_occurred is None: raise ValueError("Falha ao obter condição de placar.")
        df_backtest_result['Acerto'] = (~score_occurred).astype(int)
        if 'Profit' not in df_backtest_result.columns:
             st.error(f"Coluna 'Profit' não encontrada para {combined_strategy_name} ao calcular médias.")
             df_backtest_result['Profit'] = 0.0
        num_jogos = len(df_backtest_result)
        ultimos_8_n = min(num_jogos, 80)
        ultimos_40_n = min(num_jogos, 170)
        ultimos_8 = df_backtest_result.tail(ultimos_8_n)
        ultimos_40 = df_backtest_result.tail(ultimos_40_n)
        media_8 = ultimos_8['Acerto'].mean() if not ultimos_8.empty else 0
        media_40 = ultimos_40['Acerto'].mean() if not ultimos_40.empty else 0
        lucro_8 = ultimos_8['Profit'].sum()
        lucro_40 = ultimos_40['Profit'].sum()
        acima_limiares = media_8 >= 0.98 and media_40 >= 0.98
        return {
            "Estratégia": combined_strategy_name,
            "Média 8": f"{media_8:.2%} ({ultimos_8['Acerto'].sum()} acertos em {len(ultimos_8)})",
            "Média 40": f"{media_40:.2%} ({ultimos_40['Acerto'].sum()} acertos em {len(ultimos_40)})",
            "Lucro Últimos 8": f"{lucro_8:.2f} (em {len(ultimos_8)} jogos)",
            "Lucro Últimos 40": f"{lucro_40:.2f} (em {len(ultimos_40)} jogos)",
            "Acima dos Limiares": acima_limiares
        }
    except KeyError as e:
         st.error(f"Erro (KeyError) nas médias de {combined_strategy_name}: Coluna '{e}' ausente.")
         return { "Estratégia": combined_strategy_name, "Média 8": "Erro", "Média 40": "Erro", "Lucro Últimos 8": "Erro", "Lucro Últimos 40": "Erro", "Acima dos Limiares": False}
    except Exception as e:
         st.error(f"Erro inesperado nas médias de {combined_strategy_name}: {e}")
         return { "Estratégia": combined_strategy_name, "Média 8": "Erro", "Média 40": "Erro", "Lucro Últimos 8": "Erro", "Lucro Últimos 40": "Erro", "Acima dos Limiares": False}

# --- Pre-calcular variáveis ---
# (Mantida como antes)
def pre_calculate_all_vars(df):
    required_odds_cols = [
        'Odd_H_Back', 'Odd_D_Back', 'Odd_A_Back',
        'Odd_Over25_FT_Back', 'Odd_Under25_FT_Back',
        'Odd_BTTS_Yes_Back', 'Odd_BTTS_No_Back',
        'Odd_CS_0x0_Lay', 'Odd_CS_0x1_Lay', 'Odd_CS_1x0_Lay'
    ]
    missing_cols = [col for col in required_odds_cols if col not in df.columns]
    if missing_cols:
        st.error(f"As colunas de odds {', '.join(missing_cols)} são necessárias e não foram encontradas.")
        return None
    df_copy = df.copy()
    for col in required_odds_cols:
        if pd.api.types.is_numeric_dtype(df_copy[col]):
            invalid_mask = df_copy[col].isnull() | np.isinf(df_copy[col]) | (df_copy[col] <= 0)
            if invalid_mask.any():
                 df_copy.loc[invalid_mask, col] = 1e12
        else:
            try:
                df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce')
                invalid_mask = df_copy[col].isnull() | np.isinf(df_copy[col]) | (df_copy[col] <= 0)
                if invalid_mask.any():
                    df_copy.loc[invalid_mask, col] = 1e12
            except Exception as e_conv:
                 st.error(f"Não foi possível converter a coluna de odds '{col}' para numérica: {e_conv}. Cálculo das VARs pode falhar.")
                 return None
    probs = {}
    prob_name_map = {
        'Odd_H_Back': 'pH', 'Odd_D_Back': 'pD', 'Odd_A_Back': 'pA',
        'Odd_Over25_FT_Back': 'pOver', 'Odd_Under25_FT_Back': 'pUnder',
        'Odd_BTTS_Yes_Back': 'pBTTS_Y', 'Odd_BTTS_No_Back': 'pBTTS_N',
        'Odd_CS_0x0_Lay': 'pCS_0x0', 'Odd_CS_0x1_Lay': 'pCS_0x1', 'Odd_CS_1x0_Lay': 'pCS_1x0'
    }
    for col, prob_name in prob_name_map.items():
        if col in df_copy.columns:
             probs[prob_name] = 1 / df_copy[col].replace(0, 1e-12)
        else:
            st.error(f"Coluna {col} inesperadamente ausente durante cálculo de probabilidade.")
            return None
    try:
        temp_vars = {}
        temp_vars['VAR01'] = probs['pH'] / probs['pD']
        temp_vars['VAR02'] = probs['pH'] / probs['pA']
        temp_vars['VAR03'] = probs['pD'] / probs['pH']
        temp_vars['VAR04'] = probs['pD'] / probs['pA']
        temp_vars['VAR05'] = probs['pA'] / probs['pH']
        temp_vars['VAR06'] = probs['pA'] / probs['pD']
        temp_vars['VAR07'] = probs['pOver'] / probs['pUnder']
        temp_vars['VAR08'] = probs['pUnder'] / probs['pOver']
        temp_vars['VAR09'] = probs['pBTTS_Y'] / probs['pBTTS_N']
        temp_vars['VAR10'] = probs['pBTTS_N'] / probs['pBTTS_Y']
        temp_vars['VAR11'] = probs['pH'] / probs['pOver']
        temp_vars['VAR12'] = probs['pD'] / probs['pOver']
        temp_vars['VAR13'] = probs['pA'] / probs['pOver']
        temp_vars['VAR14'] = probs['pH'] / probs['pUnder']
        temp_vars['VAR15'] = probs['pD'] / probs['pUnder']
        temp_vars['VAR16'] = probs['pA'] / probs['pUnder']
        temp_vars['VAR17'] = probs['pH'] / probs['pBTTS_Y']
        temp_vars['VAR18'] = probs['pD'] / probs['pBTTS_Y']
        temp_vars['VAR19'] = probs['pA'] / probs['pBTTS_Y']
        temp_vars['VAR20'] = probs['pH'] / probs['pBTTS_N']
        temp_vars['VAR21'] = probs['pD'] / probs['pBTTS_N']
        temp_vars['VAR22'] = probs['pA'] / probs['pBTTS_N']
        temp_vars['VAR23'] = probs['pCS_0x0'] / probs['pH']
        temp_vars['VAR24'] = probs['pCS_0x0'] / probs['pD']
        temp_vars['VAR25'] = probs['pCS_0x0'] / probs['pA']
        temp_vars['VAR26'] = probs['pCS_0x0'] / probs['pOver']
        temp_vars['VAR27'] = probs['pCS_0x0'] / probs['pUnder']
        temp_vars['VAR28'] = probs['pCS_0x0'] / probs['pBTTS_Y']
        temp_vars['VAR29'] = probs['pCS_0x0'] / probs['pBTTS_N']
        temp_vars['VAR30'] = probs['pCS_0x1'] / probs['pH']
        temp_vars['VAR31'] = probs['pCS_0x1'] / probs['pD']
        temp_vars['VAR32'] = probs['pCS_0x1'] / probs['pA']
        temp_vars['VAR33'] = probs['pCS_0x1'] / probs['pOver']
        temp_vars['VAR34'] = probs['pCS_0x1'] / probs['pUnder']
        temp_vars['VAR35'] = probs['pCS_0x1'] / probs['pBTTS_Y']
        temp_vars['VAR36'] = probs['pCS_0x1'] / probs['pBTTS_N']
        temp_vars['VAR37'] = probs['pCS_1x0'] / probs['pH']
        temp_vars['VAR38'] = probs['pCS_1x0'] / probs['pD']
        temp_vars['VAR39'] = probs['pCS_1x0'] / probs['pA']
        temp_vars['VAR40'] = probs['pCS_1x0'] / probs['pOver']
        temp_vars['VAR41'] = probs['pCS_1x0'] / probs['pUnder']
        temp_vars['VAR42'] = probs['pCS_1x0'] / probs['pBTTS_Y']
        temp_vars['VAR43'] = probs['pCS_1x0'] / probs['pBTTS_N']
        temp_vars['VAR44'] = probs['pCS_0x0'] / probs['pCS_0x1']
        temp_vars['VAR45'] = probs['pCS_0x0'] / probs['pCS_1x0']
        temp_vars['VAR46'] = probs['pCS_0x1'] / probs['pCS_0x0']
        temp_vars['VAR47'] = probs['pCS_0x1'] / probs['pCS_1x0']
        temp_vars['VAR48'] = probs['pCS_1x0'] / probs['pCS_0x0']
        temp_vars['VAR49'] = probs['pCS_1x0'] / probs['pCS_0x1']
        df_HDA = pd.concat([probs['pH'], probs['pD'], probs['pA']], axis=1)
        temp_vars['VAR50'] = df_HDA.std(axis=1, skipna=True) / df_HDA.mean(axis=1, skipna=True).replace(0, 1e-12)
        df_OU = pd.concat([probs['pOver'], probs['pUnder']], axis=1)
        temp_vars['VAR51'] = df_OU.std(axis=1, skipna=True) / df_OU.mean(axis=1, skipna=True).replace(0, 1e-12)
        df_BTTS = pd.concat([probs['pBTTS_Y'], probs['pBTTS_N']], axis=1)
        temp_vars['VAR52'] = df_BTTS.std(axis=1, skipna=True) / df_BTTS.mean(axis=1, skipna=True).replace(0, 1e-12)
        df_CS = pd.concat([probs['pCS_0x0'], probs['pCS_0x1'], probs['pCS_1x0']], axis=1)
        temp_vars['VAR53'] = df_CS.std(axis=1, skipna=True) / df_CS.mean(axis=1, skipna=True).replace(0, 1e-12)
        temp_vars['VAR54'] = abs(probs['pH'] - probs['pA'])
        temp_vars['VAR55'] = abs(probs['pH'] - probs['pD'])
        temp_vars['VAR56'] = abs(probs['pD'] - probs['pA'])
        temp_vars['VAR57'] = abs(probs['pOver'] - probs['pUnder'])
        temp_vars['VAR58'] = abs(probs['pBTTS_Y'] - probs['pBTTS_N'])
        temp_vars['VAR59'] = abs(probs['pCS_0x0'] - probs['pCS_0x1'])
        temp_vars['VAR60'] = abs(probs['pCS_0x0'] - probs['pCS_1x0'])
        temp_vars['VAR61'] = abs(probs['pCS_0x1'] - probs['pCS_1x0'])
        temp_vars['VAR62'] = np.arctan((probs['pA'] - probs['pH']) / 2) * 180 / np.pi
        temp_vars['VAR63'] = np.arctan((probs['pD'] - probs['pH']) / 2) * 180 / np.pi
        temp_vars['VAR64'] = np.arctan((probs['pA'] - probs['pD']) / 2) * 180 / np.pi
        temp_vars['VAR65'] = np.arctan((probs['pUnder'] - probs['pOver']) / 2) * 180 / np.pi
        temp_vars['VAR66'] = np.arctan((probs['pBTTS_N'] - probs['pBTTS_Y']) / 2) * 180 / np.pi
        temp_vars['VAR67'] = np.arctan((probs['pCS_0x1'] - probs['pCS_0x0']) / 2) * 180 / np.pi
        temp_vars['VAR68'] = np.arctan((probs['pCS_1x0'] - probs['pCS_0x0']) / 2) * 180 / np.pi
        temp_vars['VAR69'] = np.arctan((probs['pCS_1x0'] - probs['pCS_0x1']) / 2) * 180 / np.pi
        temp_vars['VAR70'] = abs(probs['pH'] - probs['pA']) / probs['pA'].replace(0, 1e-12)
        temp_vars['VAR71'] = abs(probs['pH'] - probs['pD']) / probs['pD'].replace(0, 1e-12)
        temp_vars['VAR72'] = abs(probs['pD'] - probs['pA']) / probs['pA'].replace(0, 1e-12)
        temp_vars['VAR73'] = abs(probs['pOver'] - probs['pUnder']) / probs['pUnder'].replace(0, 1e-12)
        temp_vars['VAR74'] = abs(probs['pBTTS_Y'] - probs['pBTTS_N']) / probs['pBTTS_N'].replace(0, 1e-12)
        temp_vars['VAR75'] = abs(probs['pCS_0x0'] - probs['pCS_0x1']) / probs['pCS_0x1'].replace(0, 1e-12)
        temp_vars['VAR76'] = abs(probs['pCS_0x0'] - probs['pCS_1x0']) / probs['pCS_1x0'].replace(0, 1e-12)
        temp_vars['VAR77'] = abs(probs['pCS_0x1'] - probs['pCS_1x0']) / probs['pCS_1x0'].replace(0, 1e-12)
        vars_dict = {}
        for key, series in temp_vars.items():
            vars_dict[key] = series.replace([np.inf, -np.inf], np.nan).fillna(0)
        return vars_dict
    except ZeroDivisionError as zde:
        st.error(f"Erro de divisão por zero durante o cálculo das VARs. Verifique se há odds inválidas ou zero no seu arquivo. Detalhe: {zde}")
        return None
    except KeyError as ke:
         st.error(f"Erro de chave durante cálculo das VARs: Probabilidade '{ke}' não encontrada. Verifique mapeamento 'prob_name_map'.")
         return None
    except Exception as e:
        st.error(f"Erro inesperado durante o cálculo das VARs: {e}")
        return None

# --- Definição das estratégias VAR ---
# (Mantida como antes)
def define_var_strategies(vars_dict):
    if vars_dict is None:
        return [], {}
    def estrategia_1(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR30'] >= 0.0444) & (vars_dict['VAR30'] <= 0.05)].copy()
    def estrategia_2(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR29'] >= 0.0842) & (vars_dict['VAR29'] <= 0.0918)].copy()
    def estrategia_3(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR16'] >= 0.3028) & (vars_dict['VAR16'] <= 0.3409)].copy()
    def estrategia_4(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR42'] >= 0.1691) & (vars_dict['VAR42'] <= 0.1872)].copy()
    def estrategia_5(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR25'] >= 0.3) & (vars_dict['VAR25'] <= 0.3429)].copy()
    def estrategia_6(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR40'] >= 0.1524) & (vars_dict['VAR40'] <= 0.1722)].copy()
    def estrategia_7(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR45'] >= 0.4348) & (vars_dict['VAR45'] <= 0.4545)].copy()
    def estrategia_8(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR11'] >= 1.0805) & (vars_dict['VAR11'] <= 1.1164)].copy()
    def estrategia_9(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR05'] >= 0.158) & (vars_dict['VAR05'] <= 0.1732)].copy()
    def estrategia_10(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR20'] >= 1.4656) & (vars_dict['VAR20'] <= 1.5159)].copy()
    def estrategia_11(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR51'] >= 0.2308) & (vars_dict['VAR51'] <= 0.271)].copy()
    def estrategia_12(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR02'] >= 5.7746) & (vars_dict['VAR02'] <= 6.3309)].copy()
    def estrategia_13(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR70'] >= 4.7746) & (vars_dict['VAR70'] <= 5.3309)].copy()
    def estrategia_14(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR06'] >= 0.6375) & (vars_dict['VAR06'] <= 0.6818)].copy()
    def estrategia_15(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR28'] >= 0.0022) & (vars_dict['VAR28'] <= 0.0348)].copy()
    def estrategia_16(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR72'] >= 0.4667) & (vars_dict['VAR72'] <= 0.5686)].copy()
    def estrategia_17(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR04'] >= 1.4667) & (vars_dict['VAR04'] <= 1.5686)].copy()
    def estrategia_18(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR38'] >= 0.4455) & (vars_dict['VAR38'] <= 0.4857)].copy()
    def estrategia_19(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR44'] >= 1.3043) & (vars_dict['VAR44'] <= 1.3913)].copy()
    def estrategia_20(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR53'] >= 0.6209) & (vars_dict['VAR53'] <= 0.6798)].copy()
    def estrategia_21(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR39'] >= 0.6727) & (vars_dict['VAR39'] <= 0.7838)].copy()
    def estrategia_22(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR73'] >= 0.5949) & (vars_dict['VAR73'] <= 0.7403)].copy()
    def estrategia_23(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR01'] >= 3.125) & (vars_dict['VAR01'] <= 3.3553)].copy()
    def estrategia_24(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR71'] >= 2.125) & (vars_dict['VAR71'] <= 2.3553)].copy()
    def estrategia_25(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR59'] >= 0.0094) & (vars_dict['VAR59'] <= 0.0117)].copy()
    def estrategia_26(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR67'] >= -0.3217) & (vars_dict['VAR67'] <= -0.2593)].copy()
    def estrategia_27(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR75'] >= 0.1852) & (vars_dict['VAR75'] <= 0.3095)].copy()
    def estrategia_28(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR22'] >= 0.2702) & (vars_dict['VAR22'] <= 0.3081)].copy()
    def estrategia_29(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR23'] >= 0.0612) & (vars_dict['VAR23'] <= 0.0692)].copy()
    def estrategia_30(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR50'] >= 0.8208) & (vars_dict['VAR50'] <= 0.8619)].copy()
    def estrategia_31(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR66'] >= 3.8242) & (vars_dict['VAR66'] <= 5.4202)].copy()
    def estrategia_32(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR03'] >= 0.298) & (vars_dict['VAR03'] <= 0.32)].copy()
    def estrategia_33(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR62'] >= -17.3739) & (vars_dict['VAR62'] <= -16.7698)].copy()
    def estrategia_34(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR46'] >= 0.7188) & (vars_dict['VAR46'] <= 0.7667)].copy()
    def estrategia_35(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR48'] >= 4.1379) & (vars_dict['VAR48'] <= 148.4848)].copy()
    def estrategia_36(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR74'] >= 0.1713) & (vars_dict['VAR74'] <= 0.2156)].copy()
    def estrategia_37(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR18'] >= 0.449) & (vars_dict['VAR18'] <= 0.9106)].copy()
    def estrategia_38(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR76'] >= 0.5484) & (vars_dict['VAR76'] <= 0.5676)].copy()
    def estrategia_39(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR26'] >= 0.0018) & (vars_dict['VAR26'] <= 0.0255)].copy()
    def estrategia_40(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR52'] >= 0.0863) & (vars_dict['VAR52'] <= 0.1111)].copy()
    def estrategia_41(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR17'] >= 1.2333) & (vars_dict['VAR17'] <= 1.3007)].copy()
    def estrategia_42(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR37'] >= 0.1776) & (vars_dict['VAR37'] <= 0.2944)].copy()
    def estrategia_43(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR07'] >= 1.5901) & (vars_dict['VAR07'] <= 1.7403)].copy()
    def estrategia_44(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR32'] >= 0.2417) & (vars_dict['VAR32'] <= 0.2604)].copy()
    def estrategia_45(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR14'] >= 2.3894) & (vars_dict['VAR14'] <= 2.7928)].copy()
    def estrategia_46(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR61'] >= 0.1033) & (vars_dict['VAR61'] <= 0.1603)].copy()
    def estrategia_47(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR69'] >= 2.9555) & (vars_dict['VAR69'] <= 4.5816)].copy()
    def estrategia_48(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR58'] >= 0.0895) & (vars_dict['VAR58'] <= 0.1136)].copy()
    def estrategia_49(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR08'] >= 0.5746) & (vars_dict['VAR08'] <= 0.6289)].copy()
    def estrategia_50(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR60'] >= 0.0682) & (vars_dict['VAR60'] <= 0.0759)].copy()
    def estrategia_51(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR68'] >= 1.9525) & (vars_dict['VAR68'] <= 2.1734)].copy()
    def estrategia_52(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR09'] >= 0.6897) & (vars_dict['VAR09'] <= 0.7719)].copy()
    def estrategia_53(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR56'] >= 0.0649) & (vars_dict['VAR56'] <= 0.0699)].copy()
    def estrategia_54(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR10'] >= 1.2955) & (vars_dict['VAR10'] <= 1.45)].copy()
    def estrategia_55(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR34'] >= 0.074) & (vars_dict['VAR34'] <= 0.0794)].copy()
    def estrategia_56(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR64'] >= -2.0019) & (vars_dict['VAR64'] <= -1.8576)].copy()
    def estrategia_57(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR36'] >= 0.0432) & (vars_dict['VAR36'] <= 0.05)].copy()
    def estrategia_58(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR35'] >= 0.0603) & (vars_dict['VAR35'] <= 0.0693)].copy()
    def estrategia_59(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR65'] >= -7.8232) & (vars_dict['VAR65'] <= -6.6597)].copy()
    def estrategia_60(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR41'] >= 0.2267) & (vars_dict['VAR41'] <= 0.234)].copy()
    def estrategia_61(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR54'] >= 0.6027) & (vars_dict['VAR54'] <= 0.6258)].copy()
    def estrategia_62(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR21'] >= 0.3878) & (vars_dict['VAR21'] <= 0.4078)].copy()
    def estrategia_63(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR24'] >= 0.2632) & (vars_dict['VAR24'] <= 0.2974)].copy()
    def estrategia_64(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR43'] >= 0.2064) & (vars_dict['VAR43'] <= 0.2217)].copy()
    def estrategia_65(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR13'] >= 0.1543) & (vars_dict['VAR13'] <= 0.1733)].copy()
    def estrategia_66(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR15'] >= 0.42) & (vars_dict['VAR15'] <= 0.4392)].copy()
    def estrategia_67(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR57'] >= 0.0) & (vars_dict['VAR57'] <= 0.061)].copy()
    def estrategia_68(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR12'] >= 0.3302) & (vars_dict['VAR12'] <= 0.3553)].copy()
    def estrategia_69(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR31'] >= 0.15) & (vars_dict['VAR31'] <= 0.1579)].copy()
    def estrategia_70(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR47'] >= 0.2857) & (vars_dict['VAR47'] <= 0.3125)].copy()
    def estrategia_71(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR27'] >= 0.12) & (vars_dict['VAR27'] <= 0.1958)].copy()
    def estrategia_72(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR33'] >= 0.0521) & (vars_dict['VAR33'] <= 0.062)].copy()
    def estrategia_73(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR55'] >= 0.4583) & (vars_dict['VAR55'] <= 0.4803)].copy()
    def estrategia_74(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR49'] >= 3.2) & (vars_dict['VAR49'] <= 3.5)].copy()
    def estrategia_75(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR63'] >= -16.158) & (vars_dict['VAR63'] <= -15.4123)].copy()
    def estrategia_76(df): return df[(vars_dict['VAR19'] >= 0.0533) & (vars_dict['VAR19'] <= 0.2675) & (vars_dict['VAR77'] >= 0.6912) & (vars_dict['VAR77'] <= 0.7167)].copy()

    strategy_list = [
        (estrategia_1, "Estrategia_1"), (estrategia_2, "Estrategia_2"), (estrategia_3, "Estrategia_3"),
        (estrategia_4, "Estrategia_4"), (estrategia_5, "Estrategia_5"), (estrategia_6, "Estrategia_6"),
        (estrategia_7, "Estrategia_7"), (estrategia_8, "Estrategia_8"), (estrategia_9, "Estrategia_9"),
        (estrategia_10, "Estrategia_10"), (estrategia_11, "Estrategia_11"), (estrategia_12, "Estrategia_12"),
        (estrategia_13, "Estrategia_13"), (estrategia_14, "Estrategia_14"), (estrategia_15, "Estrategia_15"),
        (estrategia_16, "Estrategia_16"), (estrategia_17, "Estrategia_17"), (estrategia_18, "Estrategia_18"),
        (estrategia_19, "Estrategia_19"), (estrategia_20, "Estrategia_20"), (estrategia_21, "Estrategia_21"),
        (estrategia_22, "Estrategia_22"), (estrategia_23, "Estrategia_23"), (estrategia_24, "Estrategia_24"),
        (estrategia_25, "Estrategia_25"), (estrategia_26, "Estrategia_26"), (estrategia_27, "Estrategia_27"),
        (estrategia_28, "Estrategia_28"), (estrategia_29, "Estrategia_29"), (estrategia_30, "Estrategia_30"),
        (estrategia_31, "Estrategia_31"), (estrategia_32, "Estrategia_32"), (estrategia_33, "Estrategia_33"),
        (estrategia_34, "Estrategia_34"), (estrategia_35, "Estrategia_35"), (estrategia_36, "Estrategia_36"),
        (estrategia_37, "Estrategia_37"), (estrategia_38, "Estrategia_38"), (estrategia_39, "Estrategia_39"),
        (estrategia_40, "Estrategia_40"), (estrategia_41, "Estrategia_41"), (estrategia_42, "Estrategia_42"),
        (estrategia_43, "Estrategia_43"), (estrategia_44, "Estrategia_44"), (estrategia_45, "Estrategia_45"),
        (estrategia_46, "Estrategia_46"), (estrategia_47, "Estrategia_47"), (estrategia_48, "Estrategia_48"),
        (estrategia_49, "Estrategia_49"), (estrategia_50, "Estrategia_50"), (estrategia_51, "Estrategia_51"),
        (estrategia_52, "Estrategia_52"), (estrategia_53, "Estrategia_53"), (estrategia_54, "Estrategia_54"),
        (estrategia_55, "Estrategia_55"), (estrategia_56, "Estrategia_56"), (estrategia_57, "Estrategia_57"),
        (estrategia_58, "Estrategia_58"), (estrategia_59, "Estrategia_59"), (estrategia_60, "Estrategia_60"),
        (estrategia_61, "Estrategia_61"), (estrategia_62, "Estrategia_62"), (estrategia_63, "Estrategia_63"),
        (estrategia_64, "Estrategia_64"), (estrategia_65, "Estrategia_65"), (estrategia_66, "Estrategia_66"),
        (estrategia_67, "Estrategia_67"), (estrategia_68, "Estrategia_68"), (estrategia_69, "Estrategia_69"),
        (estrategia_70, "Estrategia_70"), (estrategia_71, "Estrategia_71"), (estrategia_72, "Estrategia_72"),
        (estrategia_73, "Estrategia_73"), (estrategia_74, "Estrategia_74"), (estrategia_75, "Estrategia_75"),
        (estrategia_76, "Estrategia_76")
  ]
    strategy_map = {name: func for func, name in strategy_list}
    return strategy_list, strategy_map
# --- Fim Definição das estratégias VAR ---

# --- Título ---
st.title("Estratégia: Handicap 3.5 e 4.5 >> 98% Betfair ")

# --- Carregar Histórico do GitHub ---
st.header("Carregamento da Base Histórica (via API FutPythonTrader)")
# O file_path para a base de dados histórica Betfair Exchange, conforme exemplo da API
file_path_historico = "Bases_de_Dados/Betfair/Base_de_Dados_Betfair_Exchange_Back_Lay.csv"

with st.spinner("Buscando e carregando dados históricos da API FutPythonTrader..."):
    # Usando a função obter_dados_github da API
    df_historico_original = obter_dados_github(file_path_historico)

# --- Processamento ---
if df_historico_original is not None:
    st.info(f"Base histórica carregada com {len(df_historico_original)} linhas.")

    required_base_cols = ['League', 'Goals_H', 'Goals_A']
    required_odds_cols = [
        'Odd_H_Back', 'Odd_D_Back', 'Odd_A_Back',
        'Odd_Over25_FT_Back', 'Odd_Under25_FT_Back',
        'Odd_BTTS_Yes_Back', 'Odd_BTTS_No_Back',
        'Odd_CS_0x0_Lay', 'Odd_CS_0x1_Lay', 'Odd_CS_1x0_Lay'
    ]
    all_required_cols = required_base_cols + required_odds_cols
    missing_cols = [col for col in all_required_cols if col not in df_historico_original.columns]

    if missing_cols:
        st.error(f"Colunas essenciais ausentes na base histórica: {', '.join(missing_cols)}. Não é possível continuar.")
        df_historico = None
    else:
        df_historico = df_historico_original[df_historico_original['League'].isin(APPROVED_LEAGUES)].copy()
        if df_historico.empty:
            st.warning("Nenhum jogo da base histórica pertence às ligas aprovadas. O backtest será vazio.")
        else:
            st.info(f"Histórico filtrado para {len(df_historico)} jogos nas ligas aprovadas.")

    if df_historico is not None and not df_historico.empty:
        vars_dict_historico = pre_calculate_all_vars(df_historico)
        if vars_dict_historico is None:
            st.error("Falha ao pré-calcular variáveis VAR do histórico. Verifique os dados e mensagens acima.")
        else:
            var_strategy_list, var_strategy_map = define_var_strategies(vars_dict_historico)
            if not var_strategy_list:
                 st.warning("Nenhuma estratégia VAR foi definida.")
            else:
                combined_backtest_results_list = []
                combined_medias_results_list = []
                approved_combined_strategies = []
                total_combinations = len(var_strategy_list) * len(cs_lay_strategies_to_test)
                st.write(f"Executando backtest para {total_combinations} combinações (Estratégias VAR x Lay CS)...")
                progress_bar = st.progress(0)
                processed_count = 0
                for var_strategy_func, var_strategy_name in var_strategy_list:
                    try:
                        df_filtered_by_var = var_strategy_func(df_historico)
                    except Exception as e_filter:
                        st.error(f"Erro ao aplicar filtro {var_strategy_name} no histórico: {e_filter}")
                        df_filtered_by_var = pd.DataFrame()
                    if not df_filtered_by_var.empty:
                         for cs_lay_name in cs_lay_strategies_to_test:
                            combined_name = f"VAR_{var_strategy_name}_CS_{cs_lay_name}"
                            backtest_result = run_combined_backtest(df_filtered_by_var.copy(), cs_lay_name, combined_name)
                            combined_backtest_results_list.append(backtest_result)
                            if backtest_result["Total de Jogos"] > 0:
                                medias_result = check_combined_moving_averages(backtest_result["Dataframe"], combined_name)
                                combined_medias_results_list.append(medias_result)
                                if medias_result["Acima dos Limiares"]:
                                    approved_combined_strategies.append(combined_name)
                            else:
                                combined_medias_results_list.append({
                                    "Estratégia": combined_name, "Média 8": "N/A (0 jogos)", "Média 40": "N/A (0 jogos)",
                                    "Lucro Últimos 8": "N/A (0 jogos)", "Lucro Últimos 40": "N/A (0 jogos)",
                                    "Acima dos Limiares": False
                                })
                            processed_count += 1
                            progress_bar.progress(min(1.0, processed_count / total_combinations))
                    else:
                        processed_count += len(cs_lay_strategies_to_test)
                        progress_bar.progress(min(1.0, processed_count / total_combinations))
                progress_bar.empty()
                st.success("Backtest combinado concluído.")
                with st.expander("📊 Resultados Detalhados do Backtest Combinado"):
                    st.subheader("📊 Resumo do Backtest por Combinação")
                    df_summary_combined = pd.DataFrame([r for r in combined_backtest_results_list if r['Total de Jogos'] > 0])
                    if not df_summary_combined.empty:
                        st.dataframe(df_summary_combined.drop(columns=["Dataframe"], errors='ignore').set_index("Estratégia"))
                    else:
                        st.write("Nenhuma combinação de estratégia resultou em jogos no backtest.")
                with st.expander ("📈 Análise das Médias e Lucros Recentes por Combinação"):
                    st.subheader("📈 Análise das Médias e Lucros Recentes (Combinado)")
                    df_medias_combined = pd.DataFrame(combined_medias_results_list)
                    if not df_medias_combined.empty:
                        df_medias_combined = df_medias_combined.sort_values(by="Acima dos Limiares", ascending=False)
                        st.dataframe(df_medias_combined.set_index("Estratégia"))
                    else:
                        st.write("Nenhuma análise de médias gerada.")

                # --- Seção de Jogos do Dia ---
                st.divider()
                st.header("🔍 Análise dos Jogos do Dia (via API FutPythonTrader)")

                if not approved_combined_strategies:
                     st.info("Nenhuma estratégia combinada foi aprovada no backtest histórico. Não há recomendações para os jogos do dia.")
                else:
                    st.success(f"{len(approved_combined_strategies)} combinações foram aprovadas no histórico!")

                    # Input para selecionar a data dos jogos do dia
                    data_selecionada = st.date_input("Selecione a data para buscar os jogos do dia:", date.today())
                    dia_formatado = data_selecionada.strftime('%Y-%m-%d')
                    st.write(f"Buscando jogos para o dia: {dia_formatado}")

                    # File path para os jogos do dia Betfair Exchange, conforme exemplo da API
                    file_path_jogos_dia = f"Jogos_do_Dia/Betfair/Jogos_do_Dia_Betfair_Back_Lay_{dia_formatado}.csv"

                    with st.spinner(f"Buscando jogos do dia ({dia_formatado}) da API FutPythonTrader..."):
                        # Usando a função obter_dados_github da API para os jogos do dia
                        # Note que não estamos usando cache aqui, pois os jogos do dia mudam diariamente.
                        # Se quiser cachear por um período curto (ex: 1 hora), pode criar uma função wrapper
                        # ou adicionar lógica de cache com `dia_formatado` como parte da chave.
                        df_daily_original = obter_dados_github(file_path_jogos_dia) # Sem cache aqui intencionalmente

                    if df_daily_original is not None:
                        st.info(f"Jogos do dia {dia_formatado} carregados ({len(df_daily_original)} linhas).")

                        missing_daily_cols = [col for col in required_odds_cols if col not in df_daily_original.columns]
                        if 'League' not in df_daily_original.columns:
                            missing_daily_cols.append('League')

                        if missing_daily_cols:
                             st.error(f"Colunas necessárias ({', '.join(missing_daily_cols)}) não encontradas nos jogos do dia. Não é possível gerar recomendações.")
                             df_daily = None
                        else:
                            df_daily = df_daily_original[df_daily_original['League'].isin(APPROVED_LEAGUES)].copy()
                            if df_daily.empty and not df_daily_original.empty:
                                st.warning("Nenhum jogo do dia pertence às ligas aprovadas.")
                            elif not df_daily.empty:
                                st.info(f"Encontrados {len(df_daily)} jogos do dia nas ligas aprovadas para análise.")
                            else:
                                st.info("Não há jogos do dia nas ligas aprovadas para analisar.")

                        if df_daily is not None and not df_daily.empty:
                            st.subheader("📋 Recomendações para os Jogos do Dia")
                            with st.spinner("Calculando variáveis VAR e aplicando filtros aprovados..."):
                                vars_dict_daily = pre_calculate_all_vars(df_daily.copy())
                                if vars_dict_daily is None:
                                    st.error("Falha ao calcular VARs para os jogos do dia. Não é possível gerar recomendações.")
                                else:
                                    _, daily_var_strategy_map = define_var_strategies(vars_dict_daily)
                                    daily_recommendations_list = []
                                    cols_to_display_base = ['Time', 'League', 'Home', 'Away'] # Corrigido de Time para Date
                                    # Tentativa de encontrar colunas comuns para identificação do jogo
                                    # A API FutPythonTrader pode ter colunas como 'Date', 'Time', 'League', 'HomeTeam', 'AwayTeam'
                                    # Ajuste conforme as colunas reais retornadas pela API para jogos do dia
                                    id_cols = ['Date', 'Time', 'League', 'Home', 'Away'] # Exemplo, ajuste se necessário
                                    if 'HomeTeam' in df_daily.columns and 'AwayTeam' in df_daily.columns: # Alternativa comum
                                        id_cols = ['Date', 'Time', 'League', 'HomeTeam', 'AwayTeam']

                                    cols_exist_daily = [col for col in id_cols if col in df_daily.columns]
                                    if not cols_exist_daily: # Fallback se nenhuma das colunas de ID esperadas existir
                                        st.warning("Não foi possível identificar colunas padrão (Date, Time, League, Home, Away, HomeTeam, AwayTeam) para agrupar jogos. Recomendações podem não ser agrupadas corretamente.")
                                        # Pega as primeiras N colunas como identificadores, ou apenas mostra sem agrupar
                                        cols_exist_daily = list(df_daily.columns[:3])


                                    for combined_name in approved_combined_strategies:
                                        match_var = re.search(r'VAR_(Estrategia_\d+)_CS_(Lay_\w+)$', combined_name)
                                        if match_var:
                                            var_name = match_var.group(1)
                                            cs_lay_name_approved = match_var.group(2)
                                            if var_name in daily_var_strategy_map:
                                                var_func = daily_var_strategy_map[var_name]
                                                try:
                                                    df_daily_filtered = var_func(df_daily)
                                                    if not df_daily_filtered.empty:
                                                        for idx, row in df_daily_filtered.iterrows():
                                                            rec = row[cols_exist_daily].to_dict() if cols_exist_daily else {"Jogo_Index": idx}
                                                            rec['Recomendação'] = cs_lay_name_approved
                                                            rec['Filtro_VAR'] = var_name
                                                            daily_recommendations_list.append(rec)
                                                except Exception as e_apply_daily:
                                                    st.warning(f"Erro ao aplicar filtro {var_name} (de {combined_name}) aos jogos do dia: {e_apply_daily}. Pulando este filtro.")
                                            else:
                                                st.warning(f"Filtro VAR '{var_name}' (de {combined_name}) não encontrado no mapa diário.")
                                        else:
                                             st.warning(f"Não foi possível extrair nome VAR e CS Lay de: {combined_name}")

                                    if daily_recommendations_list:
                                        df_final_recommendations = pd.DataFrame(daily_recommendations_list)
                                        if cols_exist_daily and not df_final_recommendations.empty:
                                            try:
                                                df_grouped_recs = df_final_recommendations.groupby(cols_exist_daily).agg(
                                                    Recomendações=('Recomendação', lambda x: ', '.join(sorted(list(set(x))))),
                                                    Filtros_VAR=('Filtro_VAR', lambda x: ', '.join(sorted(list(set(x)))))
                                                ).reset_index()
                                                st.dataframe(df_grouped_recs)
                                            except Exception as e_group:
                                                st.warning(f"Erro ao agrupar recomendações: {e_group}. Exibindo lista não agrupada.")
                                                st.dataframe(df_final_recommendations)
                                        elif not df_final_recommendations.empty:
                                             st.dataframe(df_final_recommendations)
                                        else: # Caso df_final_recommendations seja criado vazio
                                            st.info("Nenhum jogo do dia (nas ligas aprovadas) correspondeu aos filtros VAR das estratégias combinadas aprovadas no histórico.")

                                    else:
                                        st.info("Nenhum jogo do dia (nas ligas aprovadas) correspondeu aos filtros VAR das estratégias combinadas aprovadas no histórico.")
                        elif df_daily is not None and df_daily.empty:
                            pass
                    # else: df_daily_original é None, erro já foi mostrado por obter_dados_github
        # else: Falha ao calcular vars_dict_historico, erro já mostrado
    elif df_historico is None:
         pass
# else: Erro ao carregar df_historico_original, erro já foi mostrado por obter_dados_github
