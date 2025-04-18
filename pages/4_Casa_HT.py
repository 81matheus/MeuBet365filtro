import streamlit as st
import pandas as pd
import numpy as np
import io # Necessário para ler o buffer do arquivo carregado

# --- CONSTANTES ---
# URL direta para o conteúdo raw do arquivo no GitHub
GITHUB_RAW_URL = "https://raw.githubusercontent.com/81matheus/BasedeDadosBet365/main/pagesbet365/Exel-Base_de_Dados_Bet365_FiltradaCompleta.xlsx"
# Alternativa: GITHUB_RAW_URL = "https://github.com/81matheus/BasedeDadosBet365/raw/main/pagesbet365/Exel-Base_de_Dados_Bet365_FiltradaCompleta.xlsx"

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

# --- Função para Carregar Dados do GitHub com Caching ---
@st.cache_data # IMPORTANTE: Cache para evitar downloads repetidos
def load_data_from_github(url):
    """Carrega o DataFrame histórico de uma URL raw do GitHub."""
    try:
        st.info(f"Carregando base histórica do GitHub...")
        # Especificar engine='openpyxl' pode ser necessário para URLs
        df = pd.read_excel(url, engine='openpyxl')
        st.success("Base histórica carregada com sucesso do GitHub!")
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do GitHub ({url}): {e}")
        st.error("Verifique a URL, sua conexão com a internet ou se o arquivo é muito grande/está disponível.")
        return None

# --- Função Auxiliar para Carregar Dados de Upload (para jogos do dia) ---
def load_dataframe_from_upload(uploaded_file):
    """Carrega um DataFrame de um arquivo XLSX ou CSV carregado via Streamlit."""
    if uploaded_file is None:
        return None
    try:
        # Verifica a extensão do nome do arquivo
        if uploaded_file.name.lower().endswith('.xlsx'):
            df = pd.read_excel(uploaded_file)
            return df
        elif uploaded_file.name.lower().endswith('.csv'):
            file_content = uploaded_file.getvalue()
            try:
                df = pd.read_csv(io.BytesIO(file_content))
                if df.shape[1] <= 1:
                    df = pd.read_csv(io.BytesIO(file_content), sep=';')
            except Exception as e_csv:
                 st.warning(f"Não foi possível determinar o separador CSV automaticamente, tentando ';'. Erro: {e_csv}")
                 df = pd.read_csv(io.BytesIO(file_content), sep=';')
            if df.empty or df.shape[1] <= 1:
                 st.error("Falha ao ler o arquivo CSV corretamente. Verifique o separador (',' ou ';') e o formato.")
                 return None
            return df
        else:
            st.error("Formato de arquivo não suportado. Use .xlsx ou .csv")
            return None
    except Exception as e:
        st.error(f"Erro ao ler o arquivo carregado '{uploaded_file.name}': {e}")
        return None
# --- Fim da Função Auxiliar ---

# --- Funções de Backtest e Análise (sem alterações) ---
def run_backtest(df, estrategia_func, estrategia_nome):
     # Filtrar pela Odd_H_Back maior que 1.30
   # df = df[df['Odd_H_HT'] >= 1.30].copy() # Use .copy() para evitar SettingWithCopyWarning
     # Aplicar a estratégia
    df_filtrado = estrategia_func(df)

    # Verifica se o df_filtrado não está vazio antes de calcular o Profit
    if not df_filtrado.empty:
        df_filtrado['Profit'] = df_filtrado.apply(
            lambda row: (row['Odd_H_HT'] - 1) if row['Goals_H_HT'] > row['Goals_A_HT'] else -1,
            axis=1
        )
        total_jogos = len(df_filtrado)
        acertos = len(df_filtrado[df_filtrado['Goals_H_HT'] > df_filtrado['Goals_A_HT']])
        taxa_acerto = acertos / total_jogos if total_jogos > 0 else 0
        lucro_total = df_filtrado['Profit'].sum()
    else:
        # Define valores padrão se não houver jogos após o filtro da estratégia
        total_jogos = 0
        acertos = 0
        taxa_acerto = 0
        lucro_total = 0.0
        # Retorna um DataFrame vazio com as colunas esperadas se necessário,
        # ou ajusta a lógica downstream para lidar com df_filtrado vazio.
        # Aqui, vamos garantir que df_filtrado tenha a coluna Profit se não estiver vazio
        # Se estiver vazio, o retorno abaixo lida com isso.

    return {
        "Estratégia": estrategia_nome,
        "Total de Jogos": total_jogos,
        "Taxa de Acerto": f"{taxa_acerto:.2%}",
        "Lucro Total": f"{lucro_total:.2f}",
        "Dataframe": df_filtrado # Pode ser um DataFrame vazio
    }

def check_moving_averages(df_filtrado, estrategia_nome):
    if df_filtrado.empty:
        return {
            "Estratégia": estrategia_nome,
            "Média 8": "0.00% (0 acertos em 0)",
            "Média 40": "0.00% (0 acertos em 0)",
            "Lucro Últimos 8": "0.00 (em 0 jogos)",
            "Lucro Últimos 40": "0.00 (em 0 jogos)",
            "Acima dos Limiares": False
        }

    
    df_filtrado['Acerto'] = (df_filtrado['Goals_H_HT'] > df_filtrado['Goals_A_HT']).astype(int)
    ultimos_8 = df_filtrado.tail(8)
    ultimos_40 = df_filtrado.tail(40)
    media_8 = ultimos_8['Acerto'].mean() if not ultimos_8.empty else 0
    media_40 = ultimos_40['Acerto'].mean() if not ultimos_40.empty else 0
    lucro_8 = ultimos_8['Profit'].sum()
    lucro_40 = ultimos_40['Profit'].sum()
    acima_das_medias = lucro_8 >= 0.1 and lucro_40 > 0.1 and media_8 >= 0.5 and media_40 > 0.5

    return {
        "Estratégia": estrategia_nome,
        "Média 8": f"{media_8:.2%} ({ultimos_8['Acerto'].sum()} acertos em {len(ultimos_8)})",
        "Média 40": f"{media_40:.2%} ({ultimos_40['Acerto'].sum()} acertos em {len(ultimos_40)})",
        "Lucro Últimos 8": f"{lucro_8:.2f} (em {len(ultimos_8)} jogos)",
        "Lucro Últimos 40": f"{lucro_40:.2f} (em {len(ultimos_40)} jogos)",
        "Acima dos Limiares": acima_das_medias
    }

def analyze_daily_games(df_daily, estrategia_func, estrategia_nome):
    df_filtrado = estrategia_func(df_daily)
    if df_filtrado is not None and not df_filtrado.empty: # Adicionado check df_filtrado is not None
        # Ajuste para incluir 'League' se existir
        cols_to_return = ['Time', 'Home', 'Away']
        if 'League' in df_filtrado.columns:
            cols_to_return.insert(1, 'League')
        # Garante que apenas colunas existentes sejam selecionadas
        cols_exist = [col for col in cols_to_return if col in df_filtrado.columns]
        if cols_exist:
             return df_filtrado[cols_exist].copy()
        else: # Se nenhuma das colunas básicas existir, retorna None
             st.warning(f"Colunas essenciais ('Time', 'Home', 'Away') não encontradas no resultado da estratégia {estrategia_nome}")
             return None
    return None

def pre_calculate_all_vars(df):
    # Substitui 0 por NaN ANTES de calcular as probabilidades para evitar Divisão por Zero
    odds_cols = ['Odd_H_FT', 'Odd_D_FT', 'Odd_A_FT', 'Odd_Over25_FT', 'Odd_Under25_FT',
                 'Odd_BTTS_Yes', 'Odd_BTTS_No', 'Odd_12', 'Odd_X2', 'Odd_1X']
    for col in odds_cols:
        if col in df.columns:
            # Converte para numérico, forçando erros para NaN, depois substitui 0 por NaN
            df[col] = pd.to_numeric(df[col], errors='coerce').replace(0, np.nan)
        else:
            st.warning(f"Coluna de odd esperada '{col}' não encontrada no DataFrame.")
            # Cria a coluna com NaNs se não existir para evitar KeyErrors posteriores
            df[col] = np.nan


    # Calcula as probabilidades, NaN se propagará se a odd for NaN (ou era 0 ou não numérica)
    probs = {
        'pH': 1 / df['Odd_H_FT'],
        'pD': 1 / df['Odd_D_FT'],
        'pA': 1 / df['Odd_A_FT'],
        'pOver': 1 / df['Odd_Over25_FT'],
        'pUnder': 1 / df['Odd_Under25_FT'],
        'pBTTS_Y': 1 / df['Odd_BTTS_Yes'],
        'pBTTS_N': 1 / df['Odd_BTTS_No'],
        'p0x0': 1 / df['Odd_12'],
        'p0x1': 1 / df['Odd_X2'],
        'p1x0': 1 / df['Odd_1X']
    }

    # Calcula VARs - Erros aqui geralmente indicam colunas de odds ausentes ou inválidas
    # Usar .get(key, pd.Series(np.nan, index=df.index)) pode adicionar robustez se
    # uma probabilidade específica falhar, mas o ideal é garantir que as colunas de odds existam.
    vars_dict = {}
    try:
        vars_dict = {
        'VAR01': probs['pH'] / probs['pD'],
        'VAR02': probs['pH'] / probs['pA'],
        'VAR03': probs['pD'] / probs['pH'],
        'VAR04': probs['pD'] / probs['pA'],
        'VAR05': probs['pA'] / probs['pH'],
        'VAR06': probs['pA'] / probs['pD'],
        'VAR07': probs['pOver'] / probs['pUnder'],
        'VAR08': probs['pUnder'] / probs['pOver'],
        'VAR09': probs['pBTTS_Y'] / probs['pBTTS_N'],
        'VAR10': probs['pBTTS_N'] / probs['pBTTS_Y'],
        'VAR11': probs['pH'] / probs['pOver'],
        'VAR12': probs['pD'] / probs['pOver'],
        'VAR13': probs['pA'] / probs['pOver'],
        'VAR14': probs['pH'] / probs['pUnder'],
        'VAR15': probs['pD'] / probs['pUnder'],
        'VAR16': probs['pA'] / probs['pUnder'],
        'VAR17': probs['pH'] / probs['pBTTS_Y'],
        'VAR18': probs['pD'] / probs['pBTTS_Y'],
        'VAR19': probs['pA'] / probs['pBTTS_Y'],
        'VAR20': probs['pH'] / probs['pBTTS_N'],
        'VAR21': probs['pD'] / probs['pBTTS_N'],
        'VAR22': probs['pA'] / probs['pBTTS_N'],
        'VAR23': probs['p0x0'] / probs['pH'],
        'VAR24': probs['p0x0'] / probs['pD'],
        'VAR25': probs['p0x0'] / probs['pA'],
        'VAR26': probs['p0x0'] / probs['pOver'],
        'VAR27': probs['p0x0'] / probs['pUnder'],
        'VAR28': probs['p0x0'] / probs['pBTTS_Y'],
        'VAR29': probs['p0x0'] / probs['pBTTS_N'],
        'VAR30': probs['p0x1'] / probs['pH'],
        'VAR31': probs['p0x1'] / probs['pD'],
        'VAR32': probs['p0x1'] / probs['pA'],
        'VAR33': probs['p0x1'] / probs['pOver'],
        'VAR34': probs['p0x1'] / probs['pUnder'],
        'VAR35': probs['p0x1'] / probs['pBTTS_Y'],
        'VAR36': probs['p0x1'] / probs['pBTTS_N'],
        'VAR37': probs['p1x0'] / probs['pH'],
        'VAR38': probs['p1x0'] / probs['pD'],
        'VAR39': probs['p1x0'] / probs['pA'],
        'VAR40': probs['p1x0'] / probs['pOver'],
        'VAR41': probs['p1x0'] / probs['pUnder'],
        'VAR42': probs['p1x0'] / probs['pBTTS_Y'],
        'VAR43': probs['p1x0'] / probs['pBTTS_N'],
        'VAR44': probs['p0x0'] / probs['p0x1'],
        'VAR45': probs['p0x0'] / probs['p1x0'],
        'VAR46': probs['p0x1'] / probs['p0x0'],
        'VAR47': probs['p0x1'] / probs['p1x0'],
        'VAR48': probs['p1x0'] / probs['p0x0'],
        'VAR49': probs['p1x0'] / probs['p0x1'],
        'VAR50': (probs['pH'].to_frame().join(probs['pD'].to_frame()).join(probs['pA'].to_frame())).std(axis=1) /
                 (probs['pH'].to_frame().join(probs['pD'].to_frame()).join(probs['pA'].to_frame())).mean(axis=1),
        'VAR51': (probs['pOver'].to_frame().join(probs['pUnder'].to_frame())).std(axis=1) /
                 (probs['pOver'].to_frame().join(probs['pUnder'].to_frame())).mean(axis=1),
        'VAR52': (probs['pBTTS_Y'].to_frame().join(probs['pBTTS_N'].to_frame())).std(axis=1) /
                 (probs['pBTTS_Y'].to_frame().join(probs['pBTTS_N'].to_frame())).mean(axis=1),
        'VAR53': (probs['p0x0'].to_frame().join(probs['p0x1'].to_frame()).join(probs['p1x0'].to_frame())).std(axis=1) /
                 (probs['p0x0'].to_frame().join(probs['p0x1'].to_frame()).join(probs['p1x0'].to_frame())).mean(axis=1),
        'VAR54': abs(probs['pH'] - probs['pA']),
        'VAR55': abs(probs['pH'] - probs['pD']),
        'VAR56': abs(probs['pD'] - probs['pA']),
        'VAR57': abs(probs['pOver'] - probs['pUnder']),
        'VAR58': abs(probs['pBTTS_Y'] - probs['pBTTS_N']),
        'VAR59': abs(probs['p0x0'] - probs['p0x1']),
        'VAR60': abs(probs['p0x0'] - probs['p1x0']),
        'VAR61': abs(probs['p0x1'] - probs['p1x0']),
        'VAR62': np.arctan((probs['pA'] - probs['pH']) / 2) * 180 / np.pi,
        'VAR63': np.arctan((probs['pD'] - probs['pH']) / 2) * 180 / np.pi,
        'VAR64': np.arctan((probs['pA'] - probs['pD']) / 2) * 180 / np.pi,
        'VAR65': np.arctan((probs['pUnder'] - probs['pOver']) / 2) * 180 / np.pi,
        'VAR66': np.arctan((probs['pBTTS_N'] - probs['pBTTS_Y']) / 2) * 180 / np.pi,
        'VAR67': np.arctan((probs['p0x1'] - probs['p0x0']) / 2) * 180 / np.pi,
        'VAR68': np.arctan((probs['p1x0'] - probs['p0x0']) / 2) * 180 / np.pi,
        'VAR69': np.arctan((probs['p1x0'] - probs['p0x1']) / 2) * 180 / np.pi,
        'VAR70': abs(probs['pH'] - probs['pA']) / probs['pA'],
        'VAR71': abs(probs['pH'] - probs['pD']) / probs['pD'],
        'VAR72': abs(probs['pD'] - probs['pA']) / probs['pA'],
        'VAR73': abs(probs['pOver'] - probs['pUnder']) / probs['pUnder'],
        'VAR74': abs(probs['pBTTS_Y'] - probs['pBTTS_N']) / probs['pBTTS_N'],
        'VAR75': abs(probs['p0x0'] - probs['p0x1']) / probs['p0x1'],
        'VAR76': abs(probs['p0x0'] - probs['p1x0']) / probs['p1x0'],
        'VAR77': abs(probs['p0x1'] - probs['p1x0']) / probs['p1x0']
    }
    except KeyError as e:
         st.error(f"Erro ao calcular variáveis: Coluna de odd ausente ou inválida - {e}. Verifique o arquivo de entrada.")
         # Retorna um dicionário vazio ou parcial para evitar quebrar o resto
         # Idealmente, o erro já deve ter sido capturado antes, mas isso é um fallback.
         return {}
    except Exception as e:
        st.error(f"Erro inesperado ao calcular variáveis: {e}")
        return {}

    return vars_dict


def apply_strategies(df):
    vars_dict = pre_calculate_all_vars(df)

    # Verifica se vars_dict foi criado corretamente
    if not vars_dict:
        st.error("Cálculo de variáveis falhou. Não é possível aplicar estratégias.")
        return [] # Retorna lista vazia para evitar mais erros

    # Teste com Ligas "FINLAND 1"
    df_finland1 =     df[    df['League'] == "FINLAND 1"].copy()
    def estrategia_1(    df): return     df_finland1[(vars_dict['VAR34'] >= 1.2428) & (vars_dict['VAR34'] <= 1.3313)].copy()
    def estrategia_2(    df): return     df_finland1[(vars_dict['VAR77'] >= 0.149) & (vars_dict['VAR77'] <= 0.218)].copy()
    def estrategia_3(    df): return     df_finland1[(vars_dict['VAR31'] >= 2.4248) & (vars_dict['VAR31'] <= 2.6379)].copy()
    def estrategia_4(    df): return     df_finland1[(vars_dict['VAR58'] >= 0.1226) & (vars_dict['VAR58'] <= 0.1627)].copy()
    def estrategia_5(    df): return     df_finland1[(vars_dict['VAR15'] >= 0.5694) & (vars_dict['VAR15'] <= 0.5824)].copy()
    def estrategia_6(    df): return     df_finland1[(vars_dict['VAR60'] >= 0.1216) & (vars_dict['VAR60'] <= 0.1963)].copy()
    def estrategia_7(    df): return     df_finland1[(vars_dict['VAR06'] >= 1.4667) & (vars_dict['VAR06'] <= 1.7003)].copy()
    def estrategia_8(    df): return     df_finland1[(vars_dict['VAR07'] >= 1.0263) & (vars_dict['VAR07'] <= 1.1093)].copy()
    def estrategia_9(    df): return     df_finland1[(vars_dict['VAR54'] >= 0.1094) & (vars_dict['VAR54'] <= 0.1489)].copy()
    def estrategia_10(    df): return     df_finland1[(vars_dict['VAR45'] >= 1.186) & (vars_dict['VAR45'] <= 1.337)].copy()
    def estrategia_11(    df): return     df_finland1[(vars_dict['VAR76'] >= 0.186) & (vars_dict['VAR76'] <= 0.337)].copy()
    def estrategia_12(    df): return     df_finland1[(vars_dict['VAR08'] >= 0.9015) & (vars_dict['VAR08'] <= 0.9744)].copy()
    def estrategia_13(    df): return     df_finland1[(vars_dict['VAR65'] >= -1.542) & (vars_dict['VAR65'] <= -0.3866)].copy()
    def estrategia_14(    df): return     df_finland1[(vars_dict['VAR48'] >= 0.9051) & (vars_dict['VAR48'] <= 0.95)].copy()
    def estrategia_15(    df): return     df_finland1[(vars_dict['VAR68'] >= -2.0357) & (vars_dict['VAR68'] <= -1.0769)].copy()
    def estrategia_16(    df): return     df_finland1[(vars_dict['VAR21'] >= 0.5857) & (vars_dict['VAR21'] <= 0.6042)].copy()
    def estrategia_17(    df): return     df_finland1[(vars_dict['VAR11'] >= 0.7519) & (vars_dict['VAR11'] <= 0.8229)].copy()
    def estrategia_18(    df): return     df_finland1[(vars_dict['VAR40'] >= 1.1597) & (vars_dict['VAR40'] <= 1.2296)].copy()
    def estrategia_19(    df): return     df_finland1[(vars_dict['VAR16'] >= 0.7473) & (vars_dict['VAR16'] <= 0.8651)].copy()
    def estrategia_20(    df): return     df_finland1[(vars_dict['VAR04'] >= 0.5881) & (vars_dict['VAR04'] <= 0.6818)].copy()


    # Teste com Ligas "FRANCE 1"
    df_france1 =     df[    df['League'] == "FRANCE 1"].copy()
    def estrategia_21(    df): return     df_france1[(vars_dict['VAR77'] >= 0.4512) & (vars_dict['VAR77'] <= 0.5439)].copy()
    def estrategia_22(    df): return     df_france1[(vars_dict['VAR08'] >= 1.2023) & (vars_dict['VAR08'] <= 1.3174)].copy()
    def estrategia_23(    df): return     df_france1[(vars_dict['VAR65'] >= 2.7843) & (vars_dict['VAR65'] <= 4.1255)].copy()
    def estrategia_24(    df): return     df_france1[(vars_dict['VAR61'] >= 0.4103) & (vars_dict['VAR61'] <= 0.485)].copy()
    def estrategia_25(    df): return     df_france1[(vars_dict['VAR07'] >= 0.7591) & (vars_dict['VAR07'] <= 0.8317)].copy()
    def estrategia_26(    df): return     df_france1[(vars_dict['VAR30'] >= 0.6826) & (vars_dict['VAR30'] <= 0.875)].copy()
    def estrategia_27(    df): return     df_france1[(vars_dict['VAR63'] >= -11.0171) & (vars_dict['VAR63'] <= -8.6641)].copy()
    def estrategia_28(    df): return     df_france1[(vars_dict['VAR54'] >= 0.4242) & (vars_dict['VAR54'] <= 0.5)].copy()
    def estrategia_29(    df): return     df_france1[(vars_dict['VAR66'] >= -3.3755) & (vars_dict['VAR66'] <= -2.0454)].copy()
    def estrategia_30(    df): return     df_france1[(vars_dict['VAR74'] >= 0.2059) & (vars_dict['VAR74'] <= 0.2575)].copy()
    def estrategia_31(    df): return     df_france1[(vars_dict['VAR10'] >= 0.803) & (vars_dict['VAR10'] <= 0.875)].copy()
    def estrategia_32(    df): return     df_france1[(vars_dict['VAR76'] >= 0.0827) & (vars_dict['VAR76'] <= 0.0982)].copy()
    def estrategia_33(    df): return     df_france1[(vars_dict['VAR19'] >= 0.3143) & (vars_dict['VAR19'] <= 0.3935)].copy()
    def estrategia_34(    df): return     df_france1[(vars_dict['VAR55'] >= 0.0) & (vars_dict['VAR55'] <= 0.0184)].copy()
    def estrategia_35(    df): return     df_france1[(vars_dict['VAR71'] >= 0.0) & (vars_dict['VAR71'] <= 0.0658)].copy()
    def estrategia_36(    df): return     df_france1[(vars_dict['VAR03'] >= 0.3857) & (vars_dict['VAR03'] <= 0.4667)].copy()
    def estrategia_37(    df): return     df_france1[(vars_dict['VAR21'] >= 0.5909) & (vars_dict['VAR21'] <= 0.6081)].copy()
    def estrategia_38(    df): return     df_france1[(vars_dict['VAR46'] >= 0.5304) & (vars_dict['VAR46'] <= 0.6253)].copy()
    def estrategia_39(    df): return     df_france1[(vars_dict['VAR37'] >= 1.3821) & (vars_dict['VAR37'] <= 1.4785)].copy()
    def estrategia_40(    df): return     df_france1[(vars_dict['VAR62'] >= -13.0352) & (vars_dict['VAR62'] <= -9.6615)].copy()


    # Teste com Ligas "FRANCE 2"
    df_france2 =     df[    df['League'] == "FRANCE 2"].copy()
    def estrategia_41(    df): return     df_france2[(vars_dict['VAR22'] >= 0.5631) & (vars_dict['VAR22'] <= 0.635)].copy()
    def estrategia_42(    df): return     df_france2[(vars_dict['VAR30'] >= 1.6013) & (vars_dict['VAR30'] <= 1.875)].copy()
    def estrategia_43(    df): return     df_france2[(vars_dict['VAR13'] >= 0.7579) & (vars_dict['VAR13'] <= 0.8367)].copy()
    def estrategia_44(    df): return     df_france2[(vars_dict['VAR26'] >= 1.5441) & (vars_dict['VAR26'] <= 1.5809)].copy()
    def estrategia_45(    df): return     df_france2[(vars_dict['VAR17'] >= 0.764) & (vars_dict['VAR17'] <= 0.8372)].copy()
    def estrategia_46(    df): return     df_france2[(vars_dict['VAR04'] >= 0.9355) & (vars_dict['VAR04'] <= 1.0)].copy()
    def estrategia_47(    df): return     df_france2[(vars_dict['VAR05'] >= 1.6585) & (vars_dict['VAR05'] <= 4.4828)].copy()
    def estrategia_48(    df): return     df_france2[(vars_dict['VAR15'] >= 0.4722) & (vars_dict['VAR15'] <= 0.4912)].copy()
    def estrategia_49(    df): return     df_france2[(vars_dict['VAR39'] >= 0.5513) & (vars_dict['VAR39'] <= 1.1976)].copy()
    def estrategia_50(    df): return     df_france2[(vars_dict['VAR02'] >= 0.9696) & (vars_dict['VAR02'] <= 1.1765)].copy()
    def estrategia_51(    df): return     df_france2[(vars_dict['VAR47'] >= 0.915) & (vars_dict['VAR47'] <= 1.0286)].copy()
    def estrategia_52(    df): return     df_france2[(vars_dict['VAR16'] >= 0.6429) & (vars_dict['VAR16'] <= 0.7292)].copy()
    def estrategia_53(    df): return     df_france2[(vars_dict['VAR25'] >= 1.9338) & (vars_dict['VAR25'] <= 2.1429)].copy()
    def estrategia_54(    df): return     df_france2[(vars_dict['VAR49'] >= 0.4221) & (vars_dict['VAR49'] <= 0.7588)].copy()
    def estrategia_55(    df): return     df_france2[(vars_dict['VAR69'] >= -14.5923) & (vars_dict['VAR69'] <= -5.3404)].copy()
    def estrategia_56(    df): return     df_france2[(vars_dict['VAR59'] >= 0.0575) & (vars_dict['VAR59'] <= 0.0844)].copy()
    def estrategia_57(    df): return     df_france2[(vars_dict['VAR19'] >= 0.6407) & (vars_dict['VAR19'] <= 0.7208)].copy()
    def estrategia_58(    df): return     df_france2[(vars_dict['VAR64'] >= 0.0) & (vars_dict['VAR64'] <= 0.6613)].copy()
    def estrategia_59(    df): return     df_france2[(vars_dict['VAR07'] >= 0.8317) & (vars_dict['VAR07'] <= 0.878)].copy()
    def estrategia_60(    df): return     df_france2[(vars_dict['VAR62'] >= -1.7453) & (vars_dict['VAR62'] <= 0.3417)].copy()


    # Teste com Ligas "FRANCE 3"
    df_france3 =     df[    df['League'] == "FRANCE 3"].copy()
    def estrategia_61(    df): return     df_france3[(vars_dict['VAR42'] >= 1.1213) & (vars_dict['VAR42'] <= 1.2028)].copy()
    def estrategia_62(    df): return     df_france3[(vars_dict['VAR34'] >= 1.1568) & (vars_dict['VAR34'] <= 1.2357)].copy()
    def estrategia_63(    df): return     df_france3[(vars_dict['VAR29'] >= 1.3582) & (vars_dict['VAR29'] <= 1.371)].copy()
    def estrategia_64(    df): return     df_france3[(vars_dict['VAR22'] >= 0.7087) & (vars_dict['VAR22'] <= 0.7932)].copy()
    def estrategia_65(    df): return     df_france3[(vars_dict['VAR72'] >= 0.1392) & (vars_dict['VAR72'] <= 0.1847)].copy()
    def estrategia_66(    df): return     df_france3[(vars_dict['VAR70'] >= 0.165) & (vars_dict['VAR70'] <= 0.2716)].copy()
    def estrategia_67(    df): return     df_france3[(vars_dict['VAR16'] >= 0.6352) & (vars_dict['VAR16'] <= 0.7136)].copy()
    def estrategia_68(    df): return     df_france3[(vars_dict['VAR38'] >= 2.1967) & (vars_dict['VAR38'] <= 2.2857)].copy()
    def estrategia_69(    df): return     df_france3[(vars_dict['VAR33'] >= 1.2093) & (vars_dict['VAR33'] <= 1.2727)].copy()
    def estrategia_70(    df): return     df_france3[(vars_dict['VAR37'] >= 1.6667) & (vars_dict['VAR37'] <= 1.7197)].copy()
    def estrategia_71(    df): return     df_france3[(vars_dict['VAR23'] >= 2.0521) & (vars_dict['VAR23'] <= 2.3841)].copy()
    def estrategia_72(    df): return     df_france3[(vars_dict['VAR74'] >= 0.0642) & (vars_dict['VAR74'] <= 0.0851)].copy()
    def estrategia_73(    df): return     df_france3[(vars_dict['VAR58'] >= 0.0367) & (vars_dict['VAR58'] <= 0.0495)].copy()
    def estrategia_74(    df): return     df_france3[(vars_dict['VAR31'] >= 1.8611) & (vars_dict['VAR31'] <= 1.9292)].copy()
    def estrategia_75(    df): return     df_france3[(vars_dict['VAR19'] >= 0.5053) & (vars_dict['VAR19'] <= 0.5447)].copy()
    def estrategia_76(    df): return     df_france3[(vars_dict['VAR12'] >= 0.7192) & (vars_dict['VAR12'] <= 0.7517)].copy()
    def estrategia_77(    df): return     df_france3[(vars_dict['VAR26'] >= 1.6541) & (vars_dict['VAR26'] <= 1.6844)].copy()
    def estrategia_78(    df): return     df_france3[(vars_dict['VAR15'] >= 0.5689) & (vars_dict['VAR15'] <= 0.6421)].copy()
    def estrategia_79(    df): return     df_france3[(vars_dict['VAR27'] >= 1.213) & (vars_dict['VAR27'] <= 1.2406)].copy()
    def estrategia_80(    df): return     df_france3[(vars_dict['VAR65'] >= 3.4064) & (vars_dict['VAR65'] <= 4.0311)].copy()


    # Teste com Ligas "GERMANY 1"
    df_germany1 =     df[    df['League'] == "GERMANY 1"].copy()
    def estrategia_81(    df): return     df_germany1[(vars_dict['VAR13'] >= 0.4605) & (vars_dict['VAR13'] <= 0.5233)].copy()
    def estrategia_82(    df): return     df_germany1[(vars_dict['VAR26'] >= 1.2743) & (vars_dict['VAR26'] <= 1.3077)].copy()
    def estrategia_83(    df): return     df_germany1[(vars_dict['VAR19'] >= 0.4365) & (vars_dict['VAR19'] <= 0.4839)].copy()
    def estrategia_84(    df): return     df_germany1[(vars_dict['VAR22'] >= 0.5556) & (vars_dict['VAR22'] <= 0.65)].copy()
    def estrategia_85(    df): return     df_germany1[(vars_dict['VAR35'] >= 0.6667) & (vars_dict['VAR35'] <= 0.798)].copy()
    def estrategia_86(    df): return     df_germany1[(vars_dict['VAR38'] >= 2.9508) & (vars_dict['VAR38'] <= 3.284)].copy()
    def estrategia_87(    df): return     df_germany1[(vars_dict['VAR56'] >= 0.0) & (vars_dict['VAR56'] <= 0.0146)].copy()
    def estrategia_88(    df): return     df_germany1[(vars_dict['VAR12'] >= 0.3333) & (vars_dict['VAR12'] <= 0.3825)].copy()
    def estrategia_89(    df): return     df_germany1[(vars_dict['VAR21'] >= 0.5456) & (vars_dict['VAR21'] <= 0.5714)].copy()
    def estrategia_90(    df): return     df_germany1[(vars_dict['VAR20'] >= 1.0324) & (vars_dict['VAR20'] <= 1.1435)].copy()
    def estrategia_91(    df): return     df_germany1[(vars_dict['VAR06'] >= 0.8936) & (vars_dict['VAR06'] <= 0.9567)].copy()
    def estrategia_92(    df): return     df_germany1[(vars_dict['VAR04'] >= 1.0452) & (vars_dict['VAR04'] <= 1.1191)].copy()
    def estrategia_93(    df): return     df_germany1[(vars_dict['VAR43'] >= 1.8786) & (vars_dict['VAR43'] <= 2.0179)].copy()
    def estrategia_94(    df): return     df_germany1[(vars_dict['VAR33'] >= 0.6222) & (vars_dict['VAR33'] <= 0.8037)].copy()
    def estrategia_95(    df): return     df_germany1[(vars_dict['VAR54'] >= 0.4479) & (vars_dict['VAR54'] <= 0.5396)].copy()
    def estrategia_96(    df): return     df_germany1[(vars_dict['VAR60'] >= 0.0516) & (vars_dict['VAR60'] <= 0.0647)].copy()
    def estrategia_97(    df): return     df_germany1[(vars_dict['VAR41'] >= 2.2279) & (vars_dict['VAR41'] <= 2.815)].copy()
    def estrategia_98(    df): return     df_germany1[(vars_dict['VAR09'] >= 1.2575) & (vars_dict['VAR09'] <= 1.358)].copy()
    def estrategia_99(    df): return     df_germany1[(vars_dict['VAR10'] >= 0.7952) & (vars_dict['VAR10'] <= 0.8293)].copy()
    def estrategia_100(    df): return     df_germany1[(vars_dict['VAR66'] >= -3.5082) & (vars_dict['VAR66'] <= -2.8747)].copy()


    # Teste com Ligas "GERMANY 2"
    df_germany2 =     df[    df['League'] == "GERMANY 2"].copy()
    def estrategia_101(    df): return     df_germany2[(vars_dict['VAR64'] >= 1.9201) & (vars_dict['VAR64'] <= 2.9807)].copy()
    def estrategia_102(    df): return     df_germany2[(vars_dict['VAR06'] >= 1.2414) & (vars_dict['VAR06'] <= 1.375)].copy()
    def estrategia_103(    df): return     df_germany2[(vars_dict['VAR20'] >= 0.9367) & (vars_dict['VAR20'] <= 1.0233)].copy()
    def estrategia_104(    df): return     df_germany2[(vars_dict['VAR45'] >= 1.0853) & (vars_dict['VAR45'] <= 1.1524)].copy()
    def estrategia_105(    df): return     df_germany2[(vars_dict['VAR56'] >= 0.0684) & (vars_dict['VAR56'] <= 0.1041)].copy()
    def estrategia_106(    df): return     df_germany2[(vars_dict['VAR22'] >= 0.7586) & (vars_dict['VAR22'] <= 0.8333)].copy()
    def estrategia_107(    df): return     df_germany2[(vars_dict['VAR34'] >= 1.4172) & (vars_dict['VAR34'] <= 1.4969)].copy()
    def estrategia_108(    df): return     df_germany2[(vars_dict['VAR19'] >= 0.4909) & (vars_dict['VAR19'] <= 0.5333)].copy()
    def estrategia_109(    df): return     df_germany2[(vars_dict['VAR14'] >= 0.8775) & (vars_dict['VAR14'] <= 0.9638)].copy()
    def estrategia_110(    df): return     df_germany2[(vars_dict['VAR28'] >= 1.2946) & (vars_dict['VAR28'] <= 1.336)].copy()
    def estrategia_111(    df): return     df_germany2[(vars_dict['VAR24'] >= 2.6154) & (vars_dict['VAR24'] <= 2.7132)].copy()
    def estrategia_112(    df): return     df_germany2[(vars_dict['VAR16'] >= 0.7258) & (vars_dict['VAR16'] <= 0.7848)].copy()
    def estrategia_113(    df): return     df_germany2[(vars_dict['VAR40'] >= 1.1029) & (vars_dict['VAR40'] <= 1.1544)].copy()
    def estrategia_114(    df): return     df_germany2[(vars_dict['VAR04'] >= 0.7273) & (vars_dict['VAR04'] <= 0.8056)].copy()
    def estrategia_115(    df): return     df_germany2[(vars_dict['VAR12'] >= 0.4361) & (vars_dict['VAR12'] <= 0.4487)].copy()
    def estrategia_116(    df): return     df_germany2[(vars_dict['VAR55'] >= 0.157) & (vars_dict['VAR55'] <= 0.1843)].copy()
    def estrategia_117(    df): return     df_germany2[(vars_dict['VAR72'] >= 0.2) & (vars_dict['VAR72'] <= 0.2632)].copy()
    def estrategia_118(    df): return     df_germany2[(vars_dict['VAR70'] >= 0.3982) & (vars_dict['VAR70'] <= 0.5238)].copy()
    def estrategia_119(    df): return     df_germany2[(vars_dict['VAR18'] >= 0.4054) & (vars_dict['VAR18'] <= 0.4167)].copy()
    def estrategia_120(    df): return     df_germany2[(vars_dict['VAR68'] >= -2.9518) & (vars_dict['VAR68'] <= -1.7443)].copy()


    # Teste com Ligas "GERMANY 3"
    df_germany3 =     df[    df['League'] == "GERMANY 3"].copy()
    def estrategia_121(    df): return     df_germany3[(vars_dict['VAR43'] >= 1.4706) & (vars_dict['VAR43'] <= 1.5441)].copy()
    def estrategia_122(    df): return     df_germany3[(vars_dict['VAR28'] >= 1.2558) & (vars_dict['VAR28'] <= 1.2946)].copy()
    def estrategia_123(    df): return     df_germany3[(vars_dict['VAR42'] >= 1.2279) & (vars_dict['VAR42'] <= 1.2796)].copy()
    def estrategia_124(    df): return     df_germany3[(vars_dict['VAR38'] >= 2.0949) & (vars_dict['VAR38'] <= 2.1662)].copy()
    def estrategia_125(    df): return     df_germany3[(vars_dict['VAR12'] >= 0.4243) & (vars_dict['VAR12'] <= 0.4418)].copy()
    def estrategia_126(    df): return     df_germany3[(vars_dict['VAR34'] >= 1.6544) & (vars_dict['VAR34'] <= 2.2131)].copy()
    def estrategia_127(    df): return     df_germany3[(vars_dict['VAR75'] >= 0.0526) & (vars_dict['VAR75'] <= 0.0853)].copy()
    def estrategia_128(    df): return     df_germany3[(vars_dict['VAR70'] >= 0.4286) & (vars_dict['VAR70'] <= 0.5674)].copy()
    def estrategia_129(    df): return     df_germany3[(vars_dict['VAR59'] >= 0.0394) & (vars_dict['VAR59'] <= 0.0609)].copy()
    def estrategia_130(    df): return     df_germany3[(vars_dict['VAR09'] >= 1.358) & (vars_dict['VAR09'] <= 1.4331)].copy()
    def estrategia_131(    df): return     df_germany3[(vars_dict['VAR74'] >= 0.358) & (vars_dict['VAR74'] <= 0.4331)].copy()
    def estrategia_132(    df): return     df_germany3[(vars_dict['VAR58'] >= 0.1627) & (vars_dict['VAR58'] <= 0.1925)].copy()
    def estrategia_133(    df): return     df_germany3[(vars_dict['VAR21'] >= 0.6) & (vars_dict['VAR21'] <= 0.6154)].copy()
    def estrategia_134(    df): return     df_germany3[(vars_dict['VAR29'] >= 1.528) & (vars_dict['VAR29'] <= 1.5789)].copy()
    def estrategia_135(    df): return     df_germany3[(vars_dict['VAR37'] >= 1.5) & (vars_dict['VAR37'] <= 1.5454)].copy()
    def estrategia_136(    df): return     df_germany3[(vars_dict['VAR19'] >= 0.5414) & (vars_dict['VAR19'] <= 0.5815)].copy()
    def estrategia_137(    df): return     df_germany3[(vars_dict['VAR76'] >= 0.0543) & (vars_dict['VAR76'] <= 0.064)].copy()
    def estrategia_138(    df): return     df_germany3[(vars_dict['VAR60'] >= 0.1764) & (vars_dict['VAR60'] <= 0.3849)].copy()
    def estrategia_139(    df): return     df_germany3[(vars_dict['VAR45'] >= 1.2946) & (vars_dict['VAR45'] <= 1.8852)].copy()
    def estrategia_140(    df): return     df_germany3[(vars_dict['VAR44'] >= 1.0526) & (vars_dict['VAR44'] <= 1.0853)].copy()


    # Teste com Ligas "GREECE 1"
    df_greece1 =     df[    df['League'] == "GREECE 1"].copy()
    def estrategia_141(    df): return     df_greece1[(vars_dict['VAR04'] >= 0.1388) & (vars_dict['VAR04'] <= 0.3263)].copy()
    def estrategia_142(    df): return     df_greece1[(vars_dict['VAR42'] >= 0.3846) & (vars_dict['VAR42'] <= 0.764)].copy()
    def estrategia_143(    df): return     df_greece1[(vars_dict['VAR40'] >= 0.2215) & (vars_dict['VAR40'] <= 0.7)].copy()
    def estrategia_144(    df): return     df_greece1[(vars_dict['VAR06'] >= 3.0645) & (vars_dict['VAR06'] <= 7.2072)].copy()
    def estrategia_145(    df): return     df_greece1[(vars_dict['VAR56'] >= 0.4733) & (vars_dict['VAR56'] <= 0.7759)].copy()
    def estrategia_146(    df): return     df_greece1[(vars_dict['VAR16'] >= 1.3592) & (vars_dict['VAR16'] <= 2.4407)].copy()
    def estrategia_147(    df): return     df_greece1[(vars_dict['VAR31'] >= 4.0093) & (vars_dict['VAR31'] <= 8.0189)].copy()
    def estrategia_148(    df): return     df_greece1[(vars_dict['VAR60'] >= 0.4672) & (vars_dict['VAR60'] <= 0.7721)].copy()
    def estrategia_149(    df): return     df_greece1[(vars_dict['VAR64'] >= 13.3135) & (vars_dict['VAR64'] <= 21.2038)].copy()
    def estrategia_150(    df): return     df_greece1[(vars_dict['VAR34'] >= 1.7949) & (vars_dict['VAR34'] <= 2.7692)].copy()
    def estrategia_151(    df): return     df_greece1[(vars_dict['VAR39'] >= 0.1708) & (vars_dict['VAR39'] <= 0.5164)].copy()
    def estrategia_152(    df): return     df_greece1[(vars_dict['VAR24'] >= 4.2735) & (vars_dict['VAR24'] <= 5.531)].copy()
    def estrategia_153(    df): return     df_greece1[(vars_dict['VAR43'] >= 0.2308) & (vars_dict['VAR43'] <= 0.6464)].copy()
    def estrategia_154(    df): return     df_greece1[(vars_dict['VAR32'] >= 1.0882) & (vars_dict['VAR32'] <= 1.3063)].copy()
    def estrategia_155(    df): return     df_greece1[(vars_dict['VAR68'] >= -21.1086) & (vars_dict['VAR68'] <= -13.1493)].copy()
    def estrategia_156(    df): return     df_greece1[(vars_dict['VAR02'] >= 0.0584) & (vars_dict['VAR02'] <= 0.1893)].copy()
    def estrategia_157(    df): return     df_greece1[(vars_dict['VAR48'] >= 0.1662) & (vars_dict['VAR48'] <= 0.4436)].copy()
    def estrategia_158(    df): return     df_greece1[(vars_dict['VAR17'] >= 0.1316) & (vars_dict['VAR17'] <= 0.2769)].copy()
    def estrategia_159(    df): return     df_greece1[(vars_dict['VAR11'] >= 0.0758) & (vars_dict['VAR11'] <= 0.2492)].copy()
    def estrategia_160(    df): return     df_greece1[(vars_dict['VAR45'] >= 2.2541) & (vars_dict['VAR45'] <= 6.0185)].copy()


    # WARNING: Could not find 'Melhores faixas' for league: HUNGARY 1
    # Teste com Ligas "IRELAND 1"
    df_ireland1 =     df[    df['League'] == "IRELAND 1"].copy()
    def estrategia_161(    df): return     df_ireland1[(vars_dict['VAR11'] >= 1.0695) & (vars_dict['VAR11'] <= 1.1636)].copy()
    def estrategia_162(    df): return     df_ireland1[(vars_dict['VAR54'] >= 0.1353) & (vars_dict['VAR54'] <= 0.1759)].copy()
    def estrategia_163(    df): return     df_ireland1[(vars_dict['VAR40'] >= 1.5809) & (vars_dict['VAR40'] <= 1.6455)].copy()
    def estrategia_164(    df): return     df_ireland1[(vars_dict['VAR70'] >= 0.255) & (vars_dict['VAR70'] <= 0.3691)].copy()
    def estrategia_165(    df): return     df_ireland1[(vars_dict['VAR55'] >= 0.0) & (vars_dict['VAR55'] <= 0.0237)].copy()
    def estrategia_166(    df): return     df_ireland1[(vars_dict['VAR71'] >= 0.0) & (vars_dict['VAR71'] <= 0.0712)].copy()
    def estrategia_167(    df): return     df_ireland1[(vars_dict['VAR42'] >= 1.5091) & (vars_dict['VAR42'] <= 1.6259)].copy()
    def estrategia_168(    df): return     df_ireland1[(vars_dict['VAR33'] >= 1.5711) & (vars_dict['VAR33'] <= 1.6667)].copy()
    def estrategia_169(    df): return     df_ireland1[(vars_dict['VAR01'] >= 0.9711) & (vars_dict['VAR01'] <= 1.1099)].copy()
    def estrategia_170(    df): return     df_ireland1[(vars_dict['VAR63'] >= -1.0396) & (vars_dict['VAR63'] <= 0.2468)].copy()
    def estrategia_171(    df): return     df_ireland1[(vars_dict['VAR03'] >= 0.901) & (vars_dict['VAR03'] <= 1.0298)].copy()
    def estrategia_172(    df): return     df_ireland1[(vars_dict['VAR77'] >= 0.1856) & (vars_dict['VAR77'] <= 0.2435)].copy()
    def estrategia_173(    df): return     df_ireland1[(vars_dict['VAR37'] >= 1.8692) & (vars_dict['VAR37'] <= 2.0281)].copy()
    def estrategia_174(    df): return     df_ireland1[(vars_dict['VAR04'] >= 0.9688) & (vars_dict['VAR04'] <= 1.0792)].copy()
    def estrategia_175(    df): return     df_ireland1[(vars_dict['VAR06'] >= 0.9267) & (vars_dict['VAR06'] <= 1.0323)].copy()
    def estrategia_176(    df): return     df_ireland1[(vars_dict['VAR43'] >= 1.1765) & (vars_dict['VAR43'] <= 1.274)].copy()
    def estrategia_177(    df): return     df_ireland1[(vars_dict['VAR76'] >= 0.0) & (vars_dict['VAR76'] <= 0.0239)].copy()
    def estrategia_178(    df): return     df_ireland1[(vars_dict['VAR60'] >= 0.0) & (vars_dict['VAR60'] <= 0.0194)].copy()
    def estrategia_179(    df): return     df_ireland1[(vars_dict['VAR08'] >= 1.2874) & (vars_dict['VAR08'] <= 1.3889)].copy()
    def estrategia_180(    df): return     df_ireland1[(vars_dict['VAR65'] >= 3.8241) & (vars_dict['VAR65'] <= 4.9392)].copy()


    # Teste com Ligas "IRELAND 2"
    df_ireland2 =     df[    df['League'] == "IRELAND 2"].copy()
    def estrategia_181(    df): return     df_ireland2[(vars_dict['VAR19'] >= 0.5822) & (vars_dict['VAR19'] <= 0.6453)].copy()
    def estrategia_182(    df): return     df_ireland2[(vars_dict['VAR35'] >= 1.0606) & (vars_dict['VAR35'] <= 1.1329)].copy()
    def estrategia_183(    df): return     df_ireland2[(vars_dict['VAR24'] >= 2.5194) & (vars_dict['VAR24'] <= 2.5781)].copy()
    def estrategia_184(    df): return     df_ireland2[(vars_dict['VAR37'] >= 1.6794) & (vars_dict['VAR37'] <= 1.7467)].copy()
    def estrategia_185(    df): return     df_ireland2[(vars_dict['VAR29'] >= 1.5891) & (vars_dict['VAR29'] <= 1.6429)].copy()
    def estrategia_186(    df): return     df_ireland2[(vars_dict['VAR59'] >= 0.042) & (vars_dict['VAR59'] <= 0.0651)].copy()
    def estrategia_187(    df): return     df_ireland2[(vars_dict['VAR33'] >= 1.1765) & (vars_dict['VAR33'] <= 1.2726)].copy()
    def estrategia_188(    df): return     df_ireland2[(vars_dict['VAR41'] >= 1.2126) & (vars_dict['VAR41'] <= 1.3095)].copy()
    def estrategia_189(    df): return     df_ireland2[(vars_dict['VAR77'] >= 0.1903) & (vars_dict['VAR77'] <= 0.2384)].copy()
    def estrategia_190(    df): return     df_ireland2[(vars_dict['VAR70'] >= 0.2123) & (vars_dict['VAR70'] <= 0.2996)].copy()
    def estrategia_191(    df): return     df_ireland2[(vars_dict['VAR58'] >= 0.0309) & (vars_dict['VAR58'] <= 0.0367)].copy()
    def estrategia_192(    df): return     df_ireland2[(vars_dict['VAR74'] >= 0.0541) & (vars_dict['VAR74'] <= 0.0642)].copy()
    def estrategia_193(    df): return     df_ireland2[(vars_dict['VAR71'] >= 0.2081) & (vars_dict['VAR71'] <= 0.2963)].copy()
    def estrategia_194(    df): return     df_ireland2[(vars_dict['VAR14'] >= 0.7021) & (vars_dict['VAR14'] <= 0.7841)].copy()
    def estrategia_195(    df): return     df_ireland2[(vars_dict['VAR36'] >= 1.2949) & (vars_dict['VAR36'] <= 1.3653)].copy()
    def estrategia_196(    df): return     df_ireland2[(vars_dict['VAR30'] >= 1.4375) & (vars_dict['VAR30'] <= 1.7193)].copy()
    def estrategia_197(    df): return     df_ireland2[(vars_dict['VAR54'] >= 0.0821) & (vars_dict['VAR54'] <= 0.1215)].copy()
    def estrategia_198(    df): return     df_ireland2[(vars_dict['VAR61'] >= 0.0607) & (vars_dict['VAR61'] <= 0.0871)].copy()
    def estrategia_199(    df): return     df_ireland2[(vars_dict['VAR15'] >= 0.5625) & (vars_dict['VAR15'] <= 0.5755)].copy()
    def estrategia_200(    df): return     df_ireland2[(vars_dict['VAR28'] >= 1.1575) & (vars_dict['VAR28'] <= 1.2461)].copy()


    # Teste com Ligas "ISRAEL 1"
    df_israel1 =     df[    df['League'] == "ISRAEL 1"].copy()
    def estrategia_201(    df): return     df_israel1[(vars_dict['VAR33'] >= 1.2604) & (vars_dict['VAR33'] <= 1.358)].copy()
    def estrategia_202(    df): return     df_israel1[(vars_dict['VAR54'] >= 0.1348) & (vars_dict['VAR54'] <= 0.1919)].copy()
    def estrategia_203(    df): return     df_israel1[(vars_dict['VAR70'] >= 0.3778) & (vars_dict['VAR70'] <= 0.4884)].copy()
    def estrategia_204(    df): return     df_israel1[(vars_dict['VAR30'] >= 1.2963) & (vars_dict['VAR30'] <= 1.5033)].copy()
    def estrategia_205(    df): return     df_israel1[(vars_dict['VAR20'] >= 0.7952) & (vars_dict['VAR20'] <= 0.8707)].copy()
    def estrategia_206(    df): return     df_israel1[(vars_dict['VAR47'] >= 0.8144) & (vars_dict['VAR47'] <= 0.8889)].copy()
    def estrategia_207(    df): return     df_israel1[(vars_dict['VAR41'] >= 1.2279) & (vars_dict['VAR41'] <= 1.3203)].copy()
    def estrategia_208(    df): return     df_israel1[(vars_dict['VAR61'] >= 0.1346) & (vars_dict['VAR61'] <= 0.1732)].copy()
    def estrategia_209(    df): return     df_israel1[(vars_dict['VAR62'] >= -4.3637) & (vars_dict['VAR62'] <= -2.4994)].copy()
    def estrategia_210(    df): return     df_israel1[(vars_dict['VAR23'] >= 1.6165) & (vars_dict['VAR23'] <= 1.7293)].copy()
    def estrategia_211(    df): return     df_israel1[(vars_dict['VAR07'] >= 0.6957) & (vars_dict['VAR07'] <= 0.7567)].copy()
    def estrategia_212(    df): return     df_israel1[(vars_dict['VAR14'] >= 0.7244) & (vars_dict['VAR14'] <= 0.8152)].copy()
    def estrategia_213(    df): return     df_israel1[(vars_dict['VAR35'] >= 1.1111) & (vars_dict['VAR35'] <= 1.1976)].copy()
    def estrategia_214(    df): return     df_israel1[(vars_dict['VAR02'] >= 1.2522) & (vars_dict['VAR02'] <= 1.4795)].copy()
    def estrategia_215(    df): return     df_israel1[(vars_dict['VAR45'] >= 1.0) & (vars_dict['VAR45'] <= 1.0286)].copy()
    def estrategia_216(    df): return     df_israel1[(vars_dict['VAR36'] >= 1.3933) & (vars_dict['VAR36'] <= 1.5454)].copy()
    def estrategia_217(    df): return     df_israel1[(vars_dict['VAR17'] >= 0.7864) & (vars_dict['VAR17'] <= 0.8685)].copy()
    def estrategia_218(    df): return     df_israel1[(vars_dict['VAR72'] >= 0.3476) & (vars_dict['VAR72'] <= 0.4728)].copy()
    def estrategia_219(    df): return     df_israel1[(vars_dict['VAR77'] >= 0.1856) & (vars_dict['VAR77'] <= 0.2452)].copy()
    def estrategia_220(    df): return     df_israel1[(vars_dict['VAR05'] >= 0.6759) & (vars_dict['VAR05'] <= 0.7986)].copy()


    # Teste com Ligas "ITALY 1"
    df_italy1 =     df[    df['League'] == "ITALY 1"].copy()
    def estrategia_221(    df): return     df_italy1[(vars_dict['VAR33'] >= 1.3397) & (vars_dict['VAR33'] <= 1.4583)].copy()
    def estrategia_222(    df): return     df_italy1[(vars_dict['VAR36'] >= 1.6393) & (vars_dict['VAR36'] <= 1.9231)].copy()
    def estrategia_223(    df): return     df_italy1[(vars_dict['VAR22'] >= 1.1055) & (vars_dict['VAR22'] <= 1.4789)].copy()
    def estrategia_224(    df): return     df_italy1[(vars_dict['VAR26'] >= 1.1619) & (vars_dict['VAR26'] <= 1.3592)].copy()
    def estrategia_225(    df): return     df_italy1[(vars_dict['VAR32'] >= 1.4745) & (vars_dict['VAR32'] <= 1.6261)].copy()
    def estrategia_226(    df): return     df_italy1[(vars_dict['VAR68'] >= -8.5308) & (vars_dict['VAR68'] <= -5.1711)].copy()
    def estrategia_227(    df): return     df_italy1[(vars_dict['VAR24'] >= 2.7132) & (vars_dict['VAR24'] <= 2.7907)].copy()
    def estrategia_228(    df): return     df_italy1[(vars_dict['VAR11'] >= 0.4) & (vars_dict['VAR11'] <= 0.5522)].copy()
    def estrategia_229(    df): return     df_italy1[(vars_dict['VAR70'] >= 0.5799) & (vars_dict['VAR70'] <= 0.7084)].copy()
    def estrategia_230(    df): return     df_italy1[(vars_dict['VAR07'] >= 1.3174) & (vars_dict['VAR07'] <= 3.5492)].copy()
    def estrategia_231(    df): return     df_italy1[(vars_dict['VAR60'] >= 0.181) & (vars_dict['VAR60'] <= 0.3)].copy()
    def estrategia_232(    df): return     df_italy1[(vars_dict['VAR56'] >= 0.1887) & (vars_dict['VAR56'] <= 0.3083)].copy()
    def estrategia_233(    df): return     df_italy1[(vars_dict['VAR63'] >= 0.9367) & (vars_dict['VAR63'] <= 1.8889)].copy()
    def estrategia_234(    df): return     df_italy1[(vars_dict['VAR64'] >= 5.391) & (vars_dict['VAR64'] <= 8.7623)].copy()
    def estrategia_235(    df): return     df_italy1[(vars_dict['VAR06'] >= 1.6234) & (vars_dict['VAR06'] <= 2.1557)].copy()
    def estrategia_236(    df): return     df_italy1[(vars_dict['VAR55'] >= 0.0457) & (vars_dict['VAR55'] <= 0.064)].copy()
    def estrategia_237(    df): return     df_italy1[(vars_dict['VAR54'] >= 0.6036) & (vars_dict['VAR54'] <= 0.8565)].copy()
    def estrategia_238(    df): return     df_italy1[(vars_dict['VAR38'] >= 1.7855) & (vars_dict['VAR38'] <= 1.9136)].copy()
    def estrategia_239(    df): return     df_italy1[(vars_dict['VAR72'] >= 0.7076) & (vars_dict['VAR72'] <= 1.8)].copy()
    def estrategia_240(    df): return     df_italy1[(vars_dict['VAR18'] >= 0.1773) & (vars_dict['VAR18'] <= 0.4)].copy()


    # Teste com Ligas "ITALY 2"
    df_italy2 =     df[    df['League'] == "ITALY 2"].copy()
    def estrategia_241(    df): return     df_italy2[(vars_dict['VAR37'] >= 1.56) & (vars_dict['VAR37'] <= 1.6183)].copy()
    def estrategia_242(    df): return     df_italy2[(vars_dict['VAR07'] >= 0.8095) & (vars_dict['VAR07'] <= 0.8537)].copy()
    def estrategia_243(    df): return     df_italy2[(vars_dict['VAR14'] >= 0.7598) & (vars_dict['VAR14'] <= 0.8354)].copy()
    def estrategia_244(    df): return     df_italy2[(vars_dict['VAR21'] >= 0.5) & (vars_dict['VAR21'] <= 0.5311)].copy()
    def estrategia_245(    df): return     df_italy2[(vars_dict['VAR57'] >= 0.0973) & (vars_dict['VAR57'] <= 0.1275)].copy()
    def estrategia_246(    df): return     df_italy2[(vars_dict['VAR47'] >= 0.6944) & (vars_dict['VAR47'] <= 0.7588)].copy()
    def estrategia_247(    df): return     df_italy2[(vars_dict['VAR32'] >= 1.9333) & (vars_dict['VAR32'] <= 2.0359)].copy()
    def estrategia_248(    df): return     df_italy2[(vars_dict['VAR04'] >= 1.1613) & (vars_dict['VAR04'] <= 1.2357)].copy()
    def estrategia_249(    df): return     df_italy2[(vars_dict['VAR19'] >= 0.4887) & (vars_dict['VAR19'] <= 0.5357)].copy()
    def estrategia_250(    df): return     df_italy2[(vars_dict['VAR28'] >= 1.478) & (vars_dict['VAR28'] <= 1.5116)].copy()
    def estrategia_251(    df): return     df_italy2[(vars_dict['VAR75'] >= 0.25) & (vars_dict['VAR75'] <= 0.3235)].copy()
    def estrategia_252(    df): return     df_italy2[(vars_dict['VAR44'] >= 1.25) & (vars_dict['VAR44'] <= 1.3235)].copy()
    def estrategia_253(    df): return     df_italy2[(vars_dict['VAR06'] >= 0.8092) & (vars_dict['VAR06'] <= 0.8611)].copy()
    def estrategia_254(    df): return     df_italy2[(vars_dict['VAR30'] >= 1.1111) & (vars_dict['VAR30'] <= 1.2874)].copy()
    def estrategia_255(    df): return     df_italy2[(vars_dict['VAR35'] >= 1.018) & (vars_dict['VAR35'] <= 1.0833)].copy()
    def estrategia_256(    df): return     df_italy2[(vars_dict['VAR22'] >= 0.4017) & (vars_dict['VAR22'] <= 0.4567)].copy()
    def estrategia_257(    df): return     df_italy2[(vars_dict['VAR59'] >= 0.1471) & (vars_dict['VAR59'] <= 0.1797)].copy()
    def estrategia_258(    df): return     df_italy2[(vars_dict['VAR18'] >= 0.5538) & (vars_dict['VAR18'] <= 0.5806)].copy()
    def estrategia_259(    df): return     df_italy2[(vars_dict['VAR64'] >= -1.693) & (vars_dict['VAR64'] <= -1.2833)].copy()
    def estrategia_260(    df): return     df_italy2[(vars_dict['VAR38'] >= 2.623) & (vars_dict['VAR38'] <= 2.8)].copy()


    # Teste com Ligas "JAPAN 1"
    df_japan1 =     df[    df['League'] == "JAPAN 1"].copy()
    def estrategia_261(    df): return     df_japan1[(vars_dict['VAR18'] >= 0.4172) & (vars_dict['VAR18'] <= 0.4503)].copy()
    def estrategia_262(    df): return     df_japan1[(vars_dict['VAR12'] >= 0.4221) & (vars_dict['VAR12'] <= 0.4722)].copy()
    def estrategia_263(    df): return     df_japan1[(vars_dict['VAR08'] >= 0.72) & (vars_dict['VAR08'] <= 0.8317)].copy()
    def estrategia_264(    df): return     df_japan1[(vars_dict['VAR65'] >= -4.9392) & (vars_dict['VAR65'] <= -2.7843)].copy()
    def estrategia_265(    df): return     df_japan1[(vars_dict['VAR07'] >= 1.2023) & (vars_dict['VAR07'] <= 1.3889)].copy()
    def estrategia_266(    df): return     df_japan1[(vars_dict['VAR73'] >= 0.2845) & (vars_dict['VAR73'] <= 0.3333)].copy()
    def estrategia_267(    df): return     df_japan1[(vars_dict['VAR16'] >= 0.9557) & (vars_dict['VAR16'] <= 1.6457)].copy()
    def estrategia_268(    df): return     df_japan1[(vars_dict['VAR40'] >= 0.6654) & (vars_dict['VAR40'] <= 1.0558)].copy()
    def estrategia_269(    df): return     df_japan1[(vars_dict['VAR42'] >= 0.72) & (vars_dict['VAR42'] <= 0.9794)].copy()
    def estrategia_270(    df): return     df_japan1[(vars_dict['VAR27'] >= 1.6393) & (vars_dict['VAR27'] <= 1.7829)].copy()
    def estrategia_271(    df): return     df_japan1[(vars_dict['VAR34'] >= 1.5376) & (vars_dict['VAR34'] <= 2.304)].copy()
    def estrategia_272(    df): return     df_japan1[(vars_dict['VAR22'] >= 1.0168) & (vars_dict['VAR22'] <= 1.5029)].copy()
    def estrategia_273(    df): return     df_japan1[(vars_dict['VAR04'] >= 0.3418) & (vars_dict['VAR04'] <= 0.6018)].copy()
    def estrategia_274(    df): return     df_japan1[(vars_dict['VAR31'] >= 2.6428) & (vars_dict['VAR31'] <= 3.9009)].copy()
    def estrategia_275(    df): return     df_japan1[(vars_dict['VAR06'] >= 1.6618) & (vars_dict['VAR06'] <= 2.9257)].copy()
    def estrategia_276(    df): return     df_japan1[(vars_dict['VAR36'] >= 1.6) & (vars_dict['VAR36'] <= 2.104)].copy()
    def estrategia_277(    df): return     df_japan1[(vars_dict['VAR29'] >= 1.6525) & (vars_dict['VAR29'] <= 1.776)].copy()
    def estrategia_278(    df): return     df_japan1[(vars_dict['VAR72'] >= 0.4702) & (vars_dict['VAR72'] <= 1.0833)].copy()
    def estrategia_279(    df): return     df_japan1[(vars_dict['VAR26'] >= 1.2946) & (vars_dict['VAR26'] <= 1.3735)].copy()
    def estrategia_280(    df): return     df_japan1[(vars_dict['VAR57'] >= 0.1902) & (vars_dict['VAR57'] <= 0.2369)].copy()


    # Teste com Ligas "JAPAN 2"
    df_japan2 =     df[    df['League'] == "JAPAN 2"].copy()
    def estrategia_281(    df): return     df_japan2[(vars_dict['VAR36'] >= 1.543) & (vars_dict['VAR36'] <= 1.8803)].copy()
    def estrategia_282(    df): return     df_japan2[(vars_dict['VAR21'] >= 0.4771) & (vars_dict['VAR21'] <= 0.5062)].copy()
    def estrategia_283(    df): return     df_japan2[(vars_dict['VAR55'] >= 0.1937) & (vars_dict['VAR55'] <= 0.2458)].copy()
    def estrategia_284(    df): return     df_japan2[(vars_dict['VAR76'] >= 0.05) & (vars_dict['VAR76'] <= 0.0588)].copy()
    def estrategia_285(    df): return     df_japan2[(vars_dict['VAR57'] >= 0.1515) & (vars_dict['VAR57'] <= 0.1902)].copy()
    def estrategia_286(    df): return     df_japan2[(vars_dict['VAR72'] >= 0.5082) & (vars_dict['VAR72'] <= 1.1111)].copy()
    def estrategia_287(    df): return     df_japan2[(vars_dict['VAR40'] >= 1.7054) & (vars_dict['VAR40'] <= 1.822)].copy()
    def estrategia_288(    df): return     df_japan2[(vars_dict['VAR03'] >= 0.5401) & (vars_dict['VAR03'] <= 0.6115)].copy()
    def estrategia_289(    df): return     df_japan2[(vars_dict['VAR01'] >= 1.6354) & (vars_dict['VAR01'] <= 1.8516)].copy()
    def estrategia_290(    df): return     df_japan2[(vars_dict['VAR71'] >= 0.6354) & (vars_dict['VAR71'] <= 0.8516)].copy()
    def estrategia_291(    df): return     df_japan2[(vars_dict['VAR75'] >= 0.3308) & (vars_dict['VAR75'] <= 0.4692)].copy()
    def estrategia_292(    df): return     df_japan2[(vars_dict['VAR44'] >= 1.3308) & (vars_dict['VAR44'] <= 1.4692)].copy()
    def estrategia_293(    df): return     df_japan2[(vars_dict['VAR61'] >= 0.4327) & (vars_dict['VAR61'] <= 0.6405)].copy()
    def estrategia_294(    df): return     df_japan2[(vars_dict['VAR42'] >= 0.6291) & (vars_dict['VAR42'] <= 0.9773)].copy()
    def estrategia_295(    df): return     df_japan2[(vars_dict['VAR22'] >= 0.9959) & (vars_dict['VAR22'] <= 1.4286)].copy()
    def estrategia_296(    df): return     df_japan2[(vars_dict['VAR18'] >= 0.4486) & (vars_dict['VAR18'] <= 0.4787)].copy()
    def estrategia_297(    df): return     df_japan2[(vars_dict['VAR15'] >= 0.51) & (vars_dict['VAR15'] <= 0.5219)].copy()
    def estrategia_298(    df): return     df_japan2[(vars_dict['VAR77'] >= 0.4719) & (vars_dict['VAR77'] <= 0.5795)].copy()
    def estrategia_299(    df): return     df_japan2[(vars_dict['VAR59'] >= 0.1912) & (vars_dict['VAR59'] <= 0.2457)].copy()
    def estrategia_300(    df): return     df_japan2[(vars_dict['VAR34'] >= 1.496) & (vars_dict['VAR34'] <= 2.1818)].copy()


    # Teste com Ligas "ARGENTINA 1"
    df_argentina1 =     df[    df['League'] == "ARGENTINA 1"].copy()
    def estrategia_301(    df): return     df_argentina1[(vars_dict['VAR14'] >= 0.8528) & (vars_dict['VAR14'] <= 1.0)].copy()
    def estrategia_302(    df): return     df_argentina1[(vars_dict['VAR29'] >= 1.2148) & (vars_dict['VAR29'] <= 1.25)].copy()
    def estrategia_303(    df): return     df_argentina1[(vars_dict['VAR38'] >= 1.5209) & (vars_dict['VAR38'] <= 1.8426)].copy()
    def estrategia_304(    df): return     df_argentina1[(vars_dict['VAR17'] >= 0.8208) & (vars_dict['VAR17'] <= 0.9518)].copy()
    def estrategia_305(    df): return     df_argentina1[(vars_dict['VAR26'] >= 1.8797) & (vars_dict['VAR26'] <= 1.9549)].copy()
    def estrategia_306(    df): return     df_argentina1[(vars_dict['VAR37'] >= 2.2668) & (vars_dict['VAR37'] <= 3.2319)].copy()
    def estrategia_307(    df): return     df_argentina1[(vars_dict['VAR34'] >= 1.1628) & (vars_dict['VAR34'] <= 1.664)].copy()
    def estrategia_308(    df): return     df_argentina1[(vars_dict['VAR57'] >= 0.3241) & (vars_dict['VAR57'] <= 0.3671)].copy()
    def estrategia_309(    df): return     df_argentina1[(vars_dict['VAR75'] >= 0.4806) & (vars_dict['VAR75'] <= 0.7171)].copy()
    def estrategia_310(    df): return     df_argentina1[(vars_dict['VAR44'] >= 1.4806) & (vars_dict['VAR44'] <= 1.7171)].copy()
    def estrategia_311(    df): return     df_argentina1[(vars_dict['VAR59'] >= 0.2475) & (vars_dict['VAR59'] <= 0.3237)].copy()
    def estrategia_312(    df): return     df_argentina1[(vars_dict['VAR56'] >= 0.1489) & (vars_dict['VAR56'] <= 0.4444)].copy()
    def estrategia_313(    df): return     df_argentina1[(vars_dict['VAR08'] >= 1.875) & (vars_dict['VAR08'] <= 2.0571)].copy()
    def estrategia_314(    df): return     df_argentina1[(vars_dict['VAR65'] >= 9.204) & (vars_dict['VAR65'] <= 10.3999)].copy()
    def estrategia_315(    df): return     df_argentina1[(vars_dict['VAR67'] >= -9.193) & (vars_dict['VAR67'] <= -7.0542)].copy()
    def estrategia_316(    df): return     df_argentina1[(vars_dict['VAR30'] >= 0.75) & (vars_dict['VAR30'] <= 0.9231)].copy()
    def estrategia_317(    df): return     df_argentina1[(vars_dict['VAR32'] >= 2.0571) & (vars_dict['VAR32'] <= 2.1656)].copy()
    def estrategia_318(    df): return     df_argentina1[(vars_dict['VAR40'] >= 0.7909) & (vars_dict['VAR40'] <= 1.5413)].copy()
    def estrategia_319(    df): return     df_argentina1[(vars_dict['VAR39'] >= 0.5475) & (vars_dict['VAR39'] <= 1.3174)].copy()
    def estrategia_320(    df): return     df_argentina1[(vars_dict['VAR12'] >= 0.8438) & (vars_dict['VAR12'] <= 0.9035)].copy()


    # Teste com Ligas "ARGENTINA 2"
    df_argentina2 =     df[    df['League'] == "ARGENTINA 2"].copy()
    def estrategia_321(    df): return     df_argentina2[(vars_dict['VAR15'] >= 0.475) & (vars_dict['VAR15'] <= 0.4828)].copy()
    def estrategia_322(    df): return     df_argentina2[(vars_dict['VAR76'] >= 0.1176) & (vars_dict['VAR76'] <= 0.1286)].copy()
    def estrategia_323(    df): return     df_argentina2[(vars_dict['VAR31'] >= 1.2667) & (vars_dict['VAR31'] <= 1.5652)].copy()
    def estrategia_324(    df): return     df_argentina2[(vars_dict['VAR35'] >= 1.3072) & (vars_dict['VAR35'] <= 1.3757)].copy()
    def estrategia_325(    df): return     df_argentina2[(vars_dict['VAR41'] >= 1.1538) & (vars_dict['VAR41'] <= 1.2)].copy()
    def estrategia_326(    df): return     df_argentina2[(vars_dict['VAR59'] >= 0.0) & (vars_dict['VAR59'] <= 0.0198)].copy()
    def estrategia_327(    df): return     df_argentina2[(vars_dict['VAR20'] >= 0.7539) & (vars_dict['VAR20'] <= 0.8)].copy()
    def estrategia_328(    df): return     df_argentina2[(vars_dict['VAR77'] >= 0.2941) & (vars_dict['VAR77'] <= 0.3443)].copy()
    def estrategia_329(    df): return     df_argentina2[(vars_dict['VAR46'] >= 1.0) & (vars_dict['VAR46'] <= 1.0294)].copy()
    def estrategia_330(    df): return     df_argentina2[(vars_dict['VAR67'] >= 0.0) & (vars_dict['VAR67'] <= 0.6018)].copy()
    def estrategia_331(    df): return     df_argentina2[(vars_dict['VAR42'] >= 2.3707) & (vars_dict['VAR42'] <= 3.6408)].copy()
    def estrategia_332(    df): return     df_argentina2[(vars_dict['VAR23'] >= 1.4386) & (vars_dict['VAR23'] <= 1.5074)].copy()
    def estrategia_333(    df): return     df_argentina2[(vars_dict['VAR03'] >= 0.6562) & (vars_dict['VAR03'] <= 0.7118)].copy()
    def estrategia_334(    df): return     df_argentina2[(vars_dict['VAR68'] >= 3.8302) & (vars_dict['VAR68'] <= 5.5632)].copy()
    def estrategia_335(    df): return     df_argentina2[(vars_dict['VAR71'] >= 0.4091) & (vars_dict['VAR71'] <= 0.5251)].copy()
    def estrategia_336(    df): return     df_argentina2[(vars_dict['VAR75'] >= 0.0) & (vars_dict['VAR75'] <= 0.0286)].copy()
    def estrategia_337(    df): return     df_argentina2[(vars_dict['VAR19'] >= 0.4579) & (vars_dict['VAR19'] <= 0.5238)].copy()
    def estrategia_338(    df): return     df_argentina2[(vars_dict['VAR18'] >= 0.8065) & (vars_dict['VAR18'] <= 0.8333)].copy()
    def estrategia_339(    df): return     df_argentina2[(vars_dict['VAR57'] >= 0.3671) & (vars_dict['VAR57'] <= 0.4127)].copy()
    def estrategia_340(    df): return     df_argentina2[(vars_dict['VAR65'] >= 10.3999) & (vars_dict['VAR65'] <= 11.6597)].copy()


    # Teste com Ligas "AUSTRALIA 1"
    df_australia1 =     df[    df['League'] == "AUSTRALIA 1"].copy()
    def estrategia_341(    df): return     df_australia1[(vars_dict['VAR24'] >= 3.8136) & (vars_dict['VAR24'] <= 4.0254)].copy()
    def estrategia_342(    df): return     df_australia1[(vars_dict['VAR57'] >= 0.4228) & (vars_dict['VAR57'] <= 0.5887)].copy()
    def estrategia_343(    df): return     df_australia1[(vars_dict['VAR73'] >= 1.3529) & (vars_dict['VAR73'] <= 2.5492)].copy()
    def estrategia_344(    df): return     df_australia1[(vars_dict['VAR07'] >= 2.3529) & (vars_dict['VAR07'] <= 3.5492)].copy()
    def estrategia_345(    df): return     df_australia1[(vars_dict['VAR67'] >= -8.4327) & (vars_dict['VAR67'] <= -6.6008)].copy()
    def estrategia_346(    df): return     df_australia1[(vars_dict['VAR13'] >= 0.3887) & (vars_dict['VAR13'] <= 0.45)].copy()
    def estrategia_347(    df): return     df_australia1[(vars_dict['VAR44'] >= 1.418) & (vars_dict['VAR44'] <= 1.5679)].copy()
    def estrategia_348(    df): return     df_australia1[(vars_dict['VAR75'] >= 0.418) & (vars_dict['VAR75'] <= 0.5679)].copy()
    def estrategia_349(    df): return     df_australia1[(vars_dict['VAR06'] >= 2.0942) & (vars_dict['VAR06'] <= 3.5211)].copy()
    def estrategia_350(    df): return     df_australia1[(vars_dict['VAR30'] >= 0.6) & (vars_dict['VAR30'] <= 0.7964)].copy()
    def estrategia_351(    df): return     df_australia1[(vars_dict['VAR15'] >= 0.6972) & (vars_dict['VAR15'] <= 0.7304)].copy()
    def estrategia_352(    df): return     df_australia1[(vars_dict['VAR08'] >= 0.2818) & (vars_dict['VAR08'] <= 0.425)].copy()
    def estrategia_353(    df): return     df_australia1[(vars_dict['VAR65'] >= -16.4025) & (vars_dict['VAR65'] <= -11.9364)].copy()
    def estrategia_354(    df): return     df_australia1[(vars_dict['VAR39'] >= 2.1387) & (vars_dict['VAR39'] <= 2.4812)].copy()
    def estrategia_355(    df): return     df_australia1[(vars_dict['VAR23'] >= 1.2593) & (vars_dict['VAR23'] <= 1.3917)].copy()
    def estrategia_356(    df): return     df_australia1[(vars_dict['VAR12'] >= 0.2867) & (vars_dict['VAR12'] <= 0.322)].copy()
    def estrategia_357(    df): return     df_australia1[(vars_dict['VAR59'] >= 0.2314) & (vars_dict['VAR59'] <= 0.2965)].copy()
    def estrategia_358(    df): return     df_australia1[(vars_dict['VAR63'] >= -8.5801) & (vars_dict['VAR63'] <= -6.789)].copy()
    def estrategia_359(    df): return     df_australia1[(vars_dict['VAR27'] >= 2.7644) & (vars_dict['VAR27'] <= 3.7009)].copy()
    def estrategia_360(    df): return     df_australia1[(vars_dict['VAR62'] >= -13.585) & (vars_dict['VAR62'] <= -10.5184)].copy()


    # Teste com Ligas "AUSTRIA 1"
    df_austria1 =     df[    df['League'] == "AUSTRIA 1"].copy()
    def estrategia_361(    df): return     df_austria1[(vars_dict['VAR26'] >= 1.4278) & (vars_dict['VAR26'] <= 1.4957)].copy()
    def estrategia_362(    df): return     df_austria1[(vars_dict['VAR29'] >= 1.5414) & (vars_dict['VAR29'] <= 1.5984)].copy()
    def estrategia_363(    df): return     df_austria1[(vars_dict['VAR67'] >= -0.9721) & (vars_dict['VAR67'] <= 0.0)].copy()
    def estrategia_364(    df): return     df_austria1[(vars_dict['VAR46'] >= 0.9559) & (vars_dict['VAR46'] <= 1.0)].copy()
    def estrategia_365(    df): return     df_austria1[(vars_dict['VAR18'] >= 0.4912) & (vars_dict['VAR18'] <= 0.508)].copy()
    def estrategia_366(    df): return     df_austria1[(vars_dict['VAR19'] >= 0.7659) & (vars_dict['VAR19'] <= 0.8571)].copy()
    def estrategia_367(    df): return     df_austria1[(vars_dict['VAR33'] >= 1.4) & (vars_dict['VAR33'] <= 1.5355)].copy()
    def estrategia_368(    df): return     df_austria1[(vars_dict['VAR71'] >= 0.0) & (vars_dict['VAR71'] <= 0.0658)].copy()
    def estrategia_369(    df): return     df_austria1[(vars_dict['VAR24'] >= 2.6154) & (vars_dict['VAR24'] <= 2.7132)].copy()
    def estrategia_370(    df): return     df_austria1[(vars_dict['VAR28'] >= 1.3566) & (vars_dict['VAR28'] <= 1.3953)].copy()
    def estrategia_371(    df): return     df_austria1[(vars_dict['VAR77'] >= 0.1544) & (vars_dict['VAR77'] <= 0.2267)].copy()
    def estrategia_372(    df): return     df_austria1[(vars_dict['VAR58'] >= 0.1004) & (vars_dict['VAR58'] <= 0.1226)].copy()
    def estrategia_373(    df): return     df_austria1[(vars_dict['VAR74'] >= 0.1911) & (vars_dict['VAR74'] <= 0.2575)].copy()
    def estrategia_374(    df): return     df_austria1[(vars_dict['VAR21'] >= 0.5714) & (vars_dict['VAR21'] <= 0.5882)].copy()
    def estrategia_375(    df): return     df_austria1[(vars_dict['VAR07'] >= 1.0272) & (vars_dict['VAR07'] <= 1.1111)].copy()
    def estrategia_376(    df): return     df_austria1[(vars_dict['VAR10'] >= 0.8293) & (vars_dict['VAR10'] <= 0.875)].copy()
    def estrategia_377(    df): return     df_austria1[(vars_dict['VAR66'] >= -2.8747) & (vars_dict['VAR66'] <= -2.0454)].copy()
    def estrategia_378(    df): return     df_austria1[(vars_dict['VAR38'] >= 2.9932) & (vars_dict['VAR38'] <= 3.2479)].copy()
    def estrategia_379(    df): return     df_austria1[(vars_dict['VAR44'] >= 2.1557) & (vars_dict['VAR44'] <= 7.5472)].copy()
    def estrategia_380(    df): return     df_austria1[(vars_dict['VAR75'] >= 1.1557) & (vars_dict['VAR75'] <= 6.5472)].copy()


    # Teste com Ligas "AUSTRIA 2"
    df_austria2 =     df[    df['League'] == "AUSTRIA 2"].copy()
    def estrategia_381(    df): return     df_austria2[(vars_dict['VAR12'] >= 0.3816) & (vars_dict['VAR12'] <= 0.4105)].copy()
    def estrategia_382(    df): return     df_austria2[(vars_dict['VAR15'] >= 0.5831) & (vars_dict['VAR15'] <= 0.5976)].copy()
    def estrategia_383(    df): return     df_austria2[(vars_dict['VAR18'] >= 0.4093) & (vars_dict['VAR18'] <= 0.4306)].copy()
    def estrategia_384(    df): return     df_austria2[(vars_dict['VAR48'] >= 0.7257) & (vars_dict['VAR48'] <= 0.7855)].copy()
    def estrategia_385(    df): return     df_austria2[(vars_dict['VAR27'] >= 1.7323) & (vars_dict['VAR27'] <= 1.8151)].copy()
    def estrategia_386(    df): return     df_austria2[(vars_dict['VAR45'] >= 1.2732) & (vars_dict['VAR45'] <= 1.378)].copy()
    def estrategia_387(    df): return     df_austria2[(vars_dict['VAR76'] >= 0.2732) & (vars_dict['VAR76'] <= 0.378)].copy()
    def estrategia_388(    df): return     df_austria2[(vars_dict['VAR26'] >= 1.3752) & (vars_dict['VAR26'] <= 1.4062)].copy()
    def estrategia_389(    df): return     df_austria2[(vars_dict['VAR32'] >= 1.5313) & (vars_dict['VAR32'] <= 1.5994)].copy()
    def estrategia_390(    df): return     df_austria2[(vars_dict['VAR60'] >= 0.166) & (vars_dict['VAR60'] <= 0.2176)].copy()
    def estrategia_391(    df): return     df_austria2[(vars_dict['VAR72'] >= 0.3229) & (vars_dict['VAR72'] <= 0.4011)].copy()
    def estrategia_392(    df): return     df_austria2[(vars_dict['VAR68'] >= -6.208) & (vars_dict['VAR68'] <= -4.7456)].copy()
    def estrategia_393(    df): return     df_austria2[(vars_dict['VAR54'] >= 0.0936) & (vars_dict['VAR54'] <= 0.1249)].copy()
    def estrategia_394(    df): return     df_austria2[(vars_dict['VAR31'] >= 2.4244) & (vars_dict['VAR31'] <= 2.6232)].copy()
    def estrategia_395(    df): return     df_austria2[(vars_dict['VAR06'] >= 1.5162) & (vars_dict['VAR06'] <= 1.7125)].copy()
    def estrategia_396(    df): return     df_austria2[(vars_dict['VAR04'] >= 0.5839) & (vars_dict['VAR04'] <= 0.6596)].copy()
    def estrategia_397(    df): return     df_austria2[(vars_dict['VAR70'] >= 0.3102) & (vars_dict['VAR70'] <= 0.3911)].copy()
    def estrategia_398(    df): return     df_austria2[(vars_dict['VAR58'] >= 0.1299) & (vars_dict['VAR58'] <= 0.1522)].copy()
    def estrategia_399(    df): return     df_austria2[(vars_dict['VAR20'] >= 0.8805) & (vars_dict['VAR20'] <= 0.9559)].copy()
    def estrategia_400(    df): return     df_austria2[(vars_dict['VAR65'] >= -1.333) & (vars_dict['VAR65'] <= -0.5767)].copy()


    # Teste com Ligas "BELGIUM 1"
    df_belgium1 =     df[    df['League'] == "BELGIUM 1"].copy()
    def estrategia_401(    df): return     df_belgium1[(vars_dict['VAR56'] >= 0.0163) & (vars_dict['VAR56'] <= 0.0286)].copy()
    def estrategia_402(    df): return     df_belgium1[(vars_dict['VAR33'] >= 1.3768) & (vars_dict['VAR33'] <= 1.4754)].copy()
    def estrategia_403(    df): return     df_belgium1[(vars_dict['VAR27'] >= 1.8852) & (vars_dict['VAR27'] <= 2.0688)].copy()
    def estrategia_404(    df): return     df_belgium1[(vars_dict['VAR61'] >= 0.0607) & (vars_dict['VAR61'] <= 0.097)].copy()
    def estrategia_405(    df): return     df_belgium1[(vars_dict['VAR77'] >= 0.085) & (vars_dict['VAR77'] <= 0.1338)].copy()
    def estrategia_406(    df): return     df_belgium1[(vars_dict['VAR35'] >= 1.2558) & (vars_dict['VAR35'] <= 1.4044)].copy()
    def estrategia_407(    df): return     df_belgium1[(vars_dict['VAR26'] >= 1.2846) & (vars_dict['VAR26'] <= 1.3178)].copy()
    def estrategia_408(    df): return     df_belgium1[(vars_dict['VAR29'] >= 1.706) & (vars_dict['VAR29'] <= 1.7584)].copy()
    def estrategia_409(    df): return     df_belgium1[(vars_dict['VAR40'] >= 1.3077) & (vars_dict['VAR40'] <= 1.3759)].copy()
    def estrategia_410(    df): return     df_belgium1[(vars_dict['VAR70'] >= 0.125) & (vars_dict['VAR70'] <= 0.2581)].copy()
    def estrategia_411(    df): return     df_belgium1[(vars_dict['VAR64'] >= -0.8003) & (vars_dict['VAR64'] <= -0.211)].copy()
    def estrategia_412(    df): return     df_belgium1[(vars_dict['VAR42'] >= 1.6376) & (vars_dict['VAR42'] <= 2.0755)].copy()
    def estrategia_413(    df): return     df_belgium1[(vars_dict['VAR28'] >= 1.3566) & (vars_dict['VAR28'] <= 1.4)].copy()
    def estrategia_414(    df): return     df_belgium1[(vars_dict['VAR08'] >= 0.6325) & (vars_dict['VAR08'] <= 0.6681)].copy()
    def estrategia_415(    df): return     df_belgium1[(vars_dict['VAR65'] >= -6.9036) & (vars_dict['VAR65'] <= -6.0341)].copy()
    def estrategia_416(    df): return     df_belgium1[(vars_dict['VAR11'] >= 1.1408) & (vars_dict['VAR11'] <= 1.2857)].copy()
    def estrategia_417(    df): return     df_belgium1[(vars_dict['VAR16'] >= 0.6452) & (vars_dict['VAR16'] <= 0.7384)].copy()
    def estrategia_418(    df): return     df_belgium1[(vars_dict['VAR54'] >= 0.0505) & (vars_dict['VAR54'] <= 0.0978)].copy()
    def estrategia_419(    df): return     df_belgium1[(vars_dict['VAR06'] >= 0.8929) & (vars_dict['VAR06'] <= 0.973)].copy()
    def estrategia_420(    df): return     df_belgium1[(vars_dict['VAR04'] >= 1.0278) & (vars_dict['VAR04'] <= 1.12)].copy()


    # Teste com Ligas "BELGIUM 2"
    df_belgium2 =     df[    df['League'] == "BELGIUM 2"].copy()
    def estrategia_421(    df): return     df_belgium2[(vars_dict['VAR20'] >= 0.7759) & (vars_dict['VAR20'] <= 0.8655)].copy()
    def estrategia_422(    df): return     df_belgium2[(vars_dict['VAR38'] >= 2.8462) & (vars_dict['VAR38'] <= 3.125)].copy()
    def estrategia_423(    df): return     df_belgium2[(vars_dict['VAR41'] >= 1.5625) & (vars_dict['VAR41'] <= 1.6667)].copy()
    def estrategia_424(    df): return     df_belgium2[(vars_dict['VAR35'] >= 1.0903) & (vars_dict['VAR35'] <= 1.1544)].copy()
    def estrategia_425(    df): return     df_belgium2[(vars_dict['VAR13'] >= 0.6893) & (vars_dict['VAR13'] <= 0.7692)].copy()
    def estrategia_426(    df): return     df_belgium2[(vars_dict['VAR34'] >= 1.0266) & (vars_dict['VAR34'] <= 1.1257)].copy()
    def estrategia_427(    df): return     df_belgium2[(vars_dict['VAR19'] >= 0.3976) & (vars_dict['VAR19'] <= 0.45)].copy()
    def estrategia_428(    df): return     df_belgium2[(vars_dict['VAR72'] >= 0.2051) & (vars_dict['VAR72'] <= 0.2647)].copy()
    def estrategia_429(    df): return     df_belgium2[(vars_dict['VAR54'] >= 0.2937) & (vars_dict['VAR54'] <= 0.3501)].copy()
    def estrategia_430(    df): return     df_belgium2[(vars_dict['VAR25'] >= 1.9615) & (vars_dict['VAR25'] <= 2.1705)].copy()
    def estrategia_431(    df): return     df_belgium2[(vars_dict['VAR69'] >= 4.3768) & (vars_dict['VAR69'] <= 7.4738)].copy()
    def estrategia_432(    df): return     df_belgium2[(vars_dict['VAR37'] >= 1.4153) & (vars_dict['VAR37'] <= 1.48)].copy()
    def estrategia_433(    df): return     df_belgium2[(vars_dict['VAR56'] >= 0.0727) & (vars_dict['VAR56'] <= 0.1025)].copy()
    def estrategia_434(    df): return     df_belgium2[(vars_dict['VAR47'] >= 0.8889) & (vars_dict['VAR47'] <= 1.0)].copy()
    def estrategia_435(    df): return     df_belgium2[(vars_dict['VAR05'] >= 0.8182) & (vars_dict['VAR05'] <= 0.98)].copy()
    def estrategia_436(    df): return     df_belgium2[(vars_dict['VAR62'] >= -2.3137) & (vars_dict['VAR62'] <= -0.2339)].copy()
    def estrategia_437(    df): return     df_belgium2[(vars_dict['VAR61'] >= 0.2961) & (vars_dict['VAR61'] <= 0.3455)].copy()
    def estrategia_438(    df): return     df_belgium2[(vars_dict['VAR36'] >= 1.4773) & (vars_dict['VAR36'] <= 1.5789)].copy()
    def estrategia_439(    df): return     df_belgium2[(vars_dict['VAR28'] >= 1.1163) & (vars_dict['VAR28'] <= 1.1912)].copy()
    def estrategia_440(    df): return     df_belgium2[(vars_dict['VAR02'] >= 1.5476) & (vars_dict['VAR02'] <= 1.9737)].copy()


    # Teste com Ligas "BOLIVIA 1"
    df_bolivia1 =     df[    df['League'] == "BOLIVIA 1"].copy()
    def estrategia_441(    df): return     df_bolivia1[(vars_dict['VAR70'] >= 0.378) & (vars_dict['VAR70'] <= 0.5843)].copy()
    def estrategia_442(    df): return     df_bolivia1[(vars_dict['VAR28'] >= 1.3689) & (vars_dict['VAR28'] <= 1.4044)].copy()
    def estrategia_443(    df): return     df_bolivia1[(vars_dict['VAR39'] >= 0.3686) & (vars_dict['VAR39'] <= 1.3174)].copy()
    def estrategia_444(    df): return     df_bolivia1[(vars_dict['VAR61'] >= 0.2807) & (vars_dict['VAR61'] <= 0.3597)].copy()
    def estrategia_445(    df): return     df_bolivia1[(vars_dict['VAR34'] >= 1.5646) & (vars_dict['VAR34'] <= 4.1401)].copy()
    def estrategia_446(    df): return     df_bolivia1[(vars_dict['VAR69'] >= -18.203) & (vars_dict['VAR69'] <= -3.9041)].copy()
    def estrategia_447(    df): return     df_bolivia1[(vars_dict['VAR49'] >= 0.3029) & (vars_dict['VAR49'] <= 0.8144)].copy()
    def estrategia_448(    df): return     df_bolivia1[(vars_dict['VAR16'] >= 0.9513) & (vars_dict['VAR16'] <= 3.2308)].copy()
    def estrategia_449(    df): return     df_bolivia1[(vars_dict['VAR37'] >= 1.1905) & (vars_dict['VAR37'] <= 1.2911)].copy()
    def estrategia_450(    df): return     df_bolivia1[(vars_dict['VAR72'] >= 0.4738) & (vars_dict['VAR72'] <= 0.6026)].copy()
    def estrategia_451(    df): return     df_bolivia1[(vars_dict['VAR38'] >= 1.5) & (vars_dict['VAR38'] <= 2.0926)].copy()
    def estrategia_452(    df): return     df_bolivia1[(vars_dict['VAR20'] >= 0.18) & (vars_dict['VAR20'] <= 0.6483)].copy()
    def estrategia_453(    df): return     df_bolivia1[(vars_dict['VAR19'] >= 0.7669) & (vars_dict['VAR19'] <= 1.4806)].copy()
    def estrategia_454(    df): return     df_bolivia1[(vars_dict['VAR45'] >= 1.2892) & (vars_dict['VAR45'] <= 3.0088)].copy()
    def estrategia_455(    df): return     df_bolivia1[(vars_dict['VAR76'] >= 0.2892) & (vars_dict['VAR76'] <= 2.0088)].copy()
    def estrategia_456(    df): return     df_bolivia1[(vars_dict['VAR64'] >= 4.964) & (vars_dict['VAR64'] <= 16.9415)].copy()
    def estrategia_457(    df): return     df_bolivia1[(vars_dict['VAR05'] >= 1.4273) & (vars_dict['VAR05'] <= 7.7519)].copy()
    def estrategia_458(    df): return     df_bolivia1[(vars_dict['VAR02'] >= 0.129) & (vars_dict['VAR02'] <= 0.7008)].copy()
    def estrategia_459(    df): return     df_bolivia1[(vars_dict['VAR48'] >= 0.3324) & (vars_dict['VAR48'] <= 0.7757)].copy()
    def estrategia_460(    df): return     df_bolivia1[(vars_dict['VAR56'] >= 0.1737) & (vars_dict['VAR56'] <= 0.6092)].copy()


    # Teste com Ligas "BRAZIL 1"
    df_brazil1 =     df[    df['League'] == "BRAZIL 1"].copy()
    def estrategia_461(    df): return     df_brazil1[(vars_dict['VAR72'] >= 0.2672) & (vars_dict['VAR72'] <= 0.3233)].copy()
    def estrategia_462(    df): return     df_brazil1[(vars_dict['VAR26'] >= 1.5789) & (vars_dict['VAR26'] <= 1.6124)].copy()
    def estrategia_463(    df): return     df_brazil1[(vars_dict['VAR24'] >= 2.0) & (vars_dict['VAR24'] <= 2.2059)].copy()
    def estrategia_464(    df): return     df_brazil1[(vars_dict['VAR38'] >= 1.9976) & (vars_dict['VAR38'] <= 2.1914)].copy()
    def estrategia_465(    df): return     df_brazil1[(vars_dict['VAR74'] >= 0.0) & (vars_dict['VAR74'] <= 0.0769)].copy()
    def estrategia_466(    df): return     df_brazil1[(vars_dict['VAR10'] >= 1.0) & (vars_dict['VAR10'] <= 1.0833)].copy()
    def estrategia_467(    df): return     df_brazil1[(vars_dict['VAR58'] >= 0.0) & (vars_dict['VAR58'] <= 0.0427)].copy()
    def estrategia_468(    df): return     df_brazil1[(vars_dict['VAR66'] >= 0.0) & (vars_dict['VAR66'] <= 1.2241)].copy()
    def estrategia_469(    df): return     df_brazil1[(vars_dict['VAR09'] >= 1.0) & (vars_dict['VAR09'] <= 1.0833)].copy()
    def estrategia_470(    df): return     df_brazil1[(vars_dict['VAR71'] >= 0.0) & (vars_dict['VAR71'] <= 0.0904)].copy()
    def estrategia_471(    df): return     df_brazil1[(vars_dict['VAR36'] >= 1.0) & (vars_dict['VAR36'] <= 1.0778)].copy()
    def estrategia_472(    df): return     df_brazil1[(vars_dict['VAR57'] >= 0.112) & (vars_dict['VAR57'] <= 0.1515)].copy()
    def estrategia_473(    df): return     df_brazil1[(vars_dict['VAR01'] >= 0.9676) & (vars_dict['VAR01'] <= 1.1481)].copy()
    def estrategia_474(    df): return     df_brazil1[(vars_dict['VAR20'] >= 0.6533) & (vars_dict['VAR20'] <= 0.7347)].copy()
    def estrategia_475(    df): return     df_brazil1[(vars_dict['VAR76'] >= 0.1203) & (vars_dict['VAR76'] <= 0.1576)].copy()
    def estrategia_476(    df): return     df_brazil1[(vars_dict['VAR03'] >= 0.871) & (vars_dict['VAR03'] <= 1.0334)].copy()
    def estrategia_477(    df): return     df_brazil1[(vars_dict['VAR29'] >= 1.36) & (vars_dict['VAR29'] <= 1.4)].copy()
    def estrategia_478(    df): return     df_brazil1[(vars_dict['VAR16'] >= 0.4182) & (vars_dict['VAR16'] <= 0.4575)].copy()
    def estrategia_479(    df): return     df_brazil1[(vars_dict['VAR12'] >= 0.6143) & (vars_dict['VAR12'] <= 0.6508)].copy()
    def estrategia_480(    df): return     df_brazil1[(vars_dict['VAR63'] >= -1.3688) & (vars_dict['VAR63'] <= 0.3102)].copy()


    # Teste com Ligas "BRAZIL 2"
    df_brazil2 =     df[    df['League'] == "BRAZIL 2"].copy()
    def estrategia_481(    df): return     df_brazil2[(vars_dict['VAR19'] >= 0.3333) & (vars_dict['VAR19'] <= 0.3896)].copy()
    def estrategia_482(    df): return     df_brazil2[(vars_dict['VAR20'] >= 0.9693) & (vars_dict['VAR20'] <= 1.0346)].copy()
    def estrategia_483(    df): return     df_brazil2[(vars_dict['VAR72'] >= 0.5179) & (vars_dict['VAR72'] <= 0.6447)].copy()
    def estrategia_484(    df): return     df_brazil2[(vars_dict['VAR41'] >= 1.409) & (vars_dict['VAR41'] <= 1.5182)].copy()
    def estrategia_485(    df): return     df_brazil2[(vars_dict['VAR22'] >= 0.267) & (vars_dict['VAR22'] <= 0.3154)].copy()
    def estrategia_486(    df): return     df_brazil2[(vars_dict['VAR27'] >= 1.2557) & (vars_dict['VAR27'] <= 1.3525)].copy()
    def estrategia_487(    df): return     df_brazil2[(vars_dict['VAR55'] >= 0.3283) & (vars_dict['VAR55'] <= 0.3964)].copy()
    def estrategia_488(    df): return     df_brazil2[(vars_dict['VAR31'] >= 1.6095) & (vars_dict['VAR31'] <= 1.6558)].copy()
    def estrategia_489(    df): return     df_brazil2[(vars_dict['VAR32'] >= 2.5) & (vars_dict['VAR32'] <= 2.6434)].copy()
    def estrategia_490(    df): return     df_brazil2[(vars_dict['VAR16'] >= 0.2727) & (vars_dict['VAR16'] <= 0.3054)].copy()
    def estrategia_491(    df): return     df_brazil2[(vars_dict['VAR26'] >= 1.7857) & (vars_dict['VAR26'] <= 1.8382)].copy()
    def estrategia_492(    df): return     df_brazil2[(vars_dict['VAR23'] >= 1.2171) & (vars_dict['VAR23'] <= 1.277)].copy()
    def estrategia_493(    df): return     df_brazil2[(vars_dict['VAR17'] >= 1.377) & (vars_dict['VAR17'] <= 1.5335)].copy()
    def estrategia_494(    df): return     df_brazil2[(vars_dict['VAR05'] >= 0.2204) & (vars_dict['VAR05'] <= 0.2904)].copy()
    def estrategia_495(    df): return     df_brazil2[(vars_dict['VAR06'] >= 0.608) & (vars_dict['VAR06'] <= 0.6606)].copy()
    def estrategia_496(    df): return     df_brazil2[(vars_dict['VAR35'] >= 0.9232) & (vars_dict['VAR35'] <= 1.0101)].copy()
    def estrategia_497(    df): return     df_brazil2[(vars_dict['VAR24'] >= 2.548) & (vars_dict['VAR24'] <= 2.7907)].copy()
    def estrategia_498(    df): return     df_brazil2[(vars_dict['VAR25'] >= 4.414) & (vars_dict['VAR25'] <= 5.5105)].copy()
    def estrategia_499(    df): return     df_brazil2[(vars_dict['VAR54'] >= 0.4328) & (vars_dict['VAR54'] <= 0.5107)].copy()
    def estrategia_500(    df): return     df_brazil2[(vars_dict['VAR74'] >= 0.3022) & (vars_dict['VAR74'] <= 0.3571)].copy()


    # Teste com Ligas "BULGARIA 1"
    df_bulgaria1 =     df[    df['League'] == "BULGARIA 1"].copy()
    def estrategia_501(    df): return     df_bulgaria1[(vars_dict['VAR73'] >= 0.122) & (vars_dict['VAR73'] <= 0.1714)].copy()
    def estrategia_502(    df): return     df_bulgaria1[(vars_dict['VAR09'] >= 0.7952) & (vars_dict['VAR09'] <= 0.865)].copy()
    def estrategia_503(    df): return     df_bulgaria1[(vars_dict['VAR13'] >= 1.1752) & (vars_dict['VAR13'] <= 1.3522)].copy()
    def estrategia_504(    df): return     df_bulgaria1[(vars_dict['VAR10'] >= 1.2575) & (vars_dict['VAR10'] <= 1.358)].copy()
    def estrategia_505(    df): return     df_bulgaria1[(vars_dict['VAR66'] >= 3.5082) & (vars_dict['VAR66'] <= 4.6519)].copy()
    def estrategia_506(    df): return     df_bulgaria1[(vars_dict['VAR28'] >= 1.68) & (vars_dict['VAR28'] <= 1.7718)].copy()
    def estrategia_507(    df): return     df_bulgaria1[(vars_dict['VAR18'] >= 0.6667) & (vars_dict['VAR18'] <= 0.7006)].copy()
    def estrategia_508(    df): return     df_bulgaria1[(vars_dict['VAR07'] >= 0.8317) & (vars_dict['VAR07'] <= 0.925)].copy()
    def estrategia_509(    df): return     df_bulgaria1[(vars_dict['VAR75'] >= 0.0734) & (vars_dict['VAR75'] <= 0.1)].copy()
    def estrategia_510(    df): return     df_bulgaria1[(vars_dict['VAR15'] >= 0.4391) & (vars_dict['VAR15'] <= 0.4575)].copy()
    def estrategia_511(    df): return     df_bulgaria1[(vars_dict['VAR57'] >= 0.0678) & (vars_dict['VAR57'] <= 0.0973)].copy()
    def estrategia_512(    df): return     df_bulgaria1[(vars_dict['VAR26'] >= 1.6541) & (vars_dict['VAR26'] <= 1.6912)].copy()
    def estrategia_513(    df): return     df_bulgaria1[(vars_dict['VAR71'] >= 0.3226) & (vars_dict['VAR71'] <= 0.4223)].copy()
    def estrategia_514(    df): return     df_bulgaria1[(vars_dict['VAR59'] >= 0.0817) & (vars_dict['VAR59'] <= 0.0989)].copy()
    def estrategia_515(    df): return     df_bulgaria1[(vars_dict['VAR44'] >= 0.9016) & (vars_dict['VAR44'] <= 0.9385)].copy()
    def estrategia_516(    df): return     df_bulgaria1[(vars_dict['VAR33'] >= 1.8196) & (vars_dict['VAR33'] <= 1.9312)].copy()
    def estrategia_517(    df): return     df_bulgaria1[(vars_dict['VAR58'] >= 0.1226) & (vars_dict['VAR58'] <= 0.1627)].copy()
    def estrategia_518(    df): return     df_bulgaria1[(vars_dict['VAR74'] >= 0.2048) & (vars_dict['VAR74'] <= 0.2636)].copy()
    def estrategia_519(    df): return     df_bulgaria1[(vars_dict['VAR37'] >= 2.2222) & (vars_dict['VAR37'] <= 2.61)].copy()
    def estrategia_520(    df): return     df_bulgaria1[(vars_dict['VAR40'] >= 1.6544) & (vars_dict['VAR40'] <= 1.7332)].copy()


    # Teste com Ligas "CHILE 1"
    df_chile1 =     df[    df['League'] == "CHILE 1"].copy()
    def estrategia_521(    df): return     df_chile1[(vars_dict['VAR42'] >= 1.2279) & (vars_dict['VAR42'] <= 1.2721)].copy()
    def estrategia_522(    df): return     df_chile1[(vars_dict['VAR54'] >= 0.2217) & (vars_dict['VAR54'] <= 0.2628)].copy()
    def estrategia_523(    df): return     df_chile1[(vars_dict['VAR21'] >= 0.5083) & (vars_dict['VAR21'] <= 0.5395)].copy()
    def estrategia_524(    df): return     df_chile1[(vars_dict['VAR61'] >= 0.2196) & (vars_dict['VAR61'] <= 0.2536)].copy()
    def estrategia_525(    df): return     df_chile1[(vars_dict['VAR35'] >= 0.5457) & (vars_dict['VAR35'] <= 0.7638)].copy()
    def estrategia_526(    df): return     df_chile1[(vars_dict['VAR19'] >= 0.4618) & (vars_dict['VAR19'] <= 0.5118)].copy()
    def estrategia_527(    df): return     df_chile1[(vars_dict['VAR67'] >= -4.9192) & (vars_dict['VAR67'] <= -3.9041)].copy()
    def estrategia_528(    df): return     df_chile1[(vars_dict['VAR26'] >= 1.2974) & (vars_dict['VAR26'] <= 1.3411)].copy()
    def estrategia_529(    df): return     df_chile1[(vars_dict['VAR11'] >= 0.8462) & (vars_dict['VAR11'] <= 0.8901)].copy()
    def estrategia_530(    df): return     df_chile1[(vars_dict['VAR25'] >= 2.8682) & (vars_dict['VAR25'] <= 3.1008)].copy()
    def estrategia_531(    df): return     df_chile1[(vars_dict['VAR20'] >= 1.2575) & (vars_dict['VAR20'] <= 1.5517)].copy()
    def estrategia_532(    df): return     df_chile1[(vars_dict['VAR76'] >= 0.0) & (vars_dict['VAR76'] <= 0.0078)].copy()
    def estrategia_533(    df): return     df_chile1[(vars_dict['VAR14'] >= 1.3631) & (vars_dict['VAR14'] <= 1.9549)].copy()
    def estrategia_534(    df): return     df_chile1[(vars_dict['VAR56'] >= 0.0) & (vars_dict['VAR56'] <= 0.0111)].copy()
    def estrategia_535(    df): return     df_chile1[(vars_dict['VAR33'] >= 0.4371) & (vars_dict['VAR33'] <= 0.7269)].copy()
    def estrategia_536(    df): return     df_chile1[(vars_dict['VAR40'] >= 1.3983) & (vars_dict['VAR40'] <= 1.4393)].copy()
    def estrategia_537(    df): return     df_chile1[(vars_dict['VAR13'] >= 0.153) & (vars_dict['VAR13'] <= 0.3116)].copy()
    def estrategia_538(    df): return     df_chile1[(vars_dict['VAR77'] >= 0.289) & (vars_dict['VAR77'] <= 0.3333)].copy()
    def estrategia_539(    df): return     df_chile1[(vars_dict['VAR55'] >= 0.2504) & (vars_dict['VAR55'] <= 0.321)].copy()
    def estrategia_540(    df): return     df_chile1[(vars_dict['VAR43'] >= 1.6754) & (vars_dict['VAR43'] <= 1.7797)].copy()


    # Teste com Ligas "CHINA 1"
    df_china1 =     df[    df['League'] == "CHINA 1"].copy()
    def estrategia_541(    df): return     df_china1[(vars_dict['VAR29'] >= 1.5984) & (vars_dict['VAR29'] <= 1.6455)].copy()
    def estrategia_542(    df): return     df_china1[(vars_dict['VAR58'] >= 0.1226) & (vars_dict['VAR58'] <= 0.1925)].copy()
    def estrategia_543(    df): return     df_china1[(vars_dict['VAR26'] >= 1.3925) & (vars_dict['VAR26'] <= 1.4511)].copy()
    def estrategia_544(    df): return     df_china1[(vars_dict['VAR06'] >= 0.9333) & (vars_dict['VAR06'] <= 1.0858)].copy()
    def estrategia_545(    df): return     df_china1[(vars_dict['VAR11'] >= 0.8435) & (vars_dict['VAR11'] <= 0.9223)].copy()
    def estrategia_546(    df): return     df_china1[(vars_dict['VAR72'] >= 0.0) & (vars_dict['VAR72'] <= 0.0769)].copy()
    def estrategia_547(    df): return     df_china1[(vars_dict['VAR61'] >= 0.187) & (vars_dict['VAR61'] <= 0.2444)].copy()
    def estrategia_548(    df): return     df_china1[(vars_dict['VAR16'] >= 0.5343) & (vars_dict['VAR16'] <= 0.6076)].copy()
    def estrategia_549(    df): return     df_china1[(vars_dict['VAR74'] >= 0.2575) & (vars_dict['VAR74'] <= 0.3706)].copy()
    def estrategia_550(    df): return     df_china1[(vars_dict['VAR04'] >= 0.921) & (vars_dict['VAR04'] <= 1.0714)].copy()
    def estrategia_551(    df): return     df_china1[(vars_dict['VAR07'] >= 1.2023) & (vars_dict['VAR07'] <= 1.2874)].copy()
    def estrategia_552(    df): return     df_china1[(vars_dict['VAR40'] >= 1.1842) & (vars_dict['VAR40'] <= 1.2576)].copy()
    def estrategia_553(    df): return     df_china1[(vars_dict['VAR65'] >= -3.8241) & (vars_dict['VAR65'] <= -2.7843)].copy()
    def estrategia_554(    df): return     df_china1[(vars_dict['VAR08'] >= 0.7767) & (vars_dict['VAR08'] <= 0.8317)].copy()
    def estrategia_555(    df): return     df_china1[(vars_dict['VAR32'] >= 1.9353) & (vars_dict['VAR32'] <= 2.0833)].copy()
    def estrategia_556(    df): return     df_china1[(vars_dict['VAR70'] >= 0.323) & (vars_dict['VAR70'] <= 0.4835)].copy()
    def estrategia_557(    df): return     df_china1[(vars_dict['VAR24'] >= 2.4436) & (vars_dict['VAR24'] <= 2.6154)].copy()
    def estrategia_558(    df): return     df_china1[(vars_dict['VAR56'] >= 0.0558) & (vars_dict['VAR56'] <= 0.0751)].copy()
    def estrategia_559(    df): return     df_china1[(vars_dict['VAR13'] >= 0.5651) & (vars_dict['VAR13'] <= 0.6893)].copy()
    def estrategia_560(    df): return     df_china1[(vars_dict['VAR21'] >= 0.6) & (vars_dict['VAR21'] <= 0.6286)].copy()


    # Teste com Ligas "CHINA 2"
    df_china2 =     df[    df['League'] == "CHINA 2"].copy()
    def estrategia_561(    df): return     df_china2[(vars_dict['VAR74'] >= 0.3279) & (vars_dict['VAR74'] <= 0.5368)].copy()
    def estrategia_562(    df): return     df_china2[(vars_dict['VAR66'] >= 5.769) & (vars_dict['VAR66'] <= 11.4943)].copy()
    def estrategia_563(    df): return     df_china2[(vars_dict['VAR58'] >= 0.2021) & (vars_dict['VAR58'] <= 0.4067)].copy()
    def estrategia_564(    df): return     df_china2[(vars_dict['VAR10'] >= 1.4445) & (vars_dict['VAR10'] <= 2.1591)].copy()
    def estrategia_565(    df): return     df_china2[(vars_dict['VAR09'] >= 0.4632) & (vars_dict['VAR09'] <= 0.6923)].copy()
    def estrategia_566(    df): return     df_china2[(vars_dict['VAR24'] >= 2.3664) & (vars_dict['VAR24'] <= 2.4615)].copy()
    def estrategia_567(    df): return     df_china2[(vars_dict['VAR72'] >= 0.6158) & (vars_dict['VAR72'] <= 0.8274)].copy()
    def estrategia_568(    df): return     df_china2[(vars_dict['VAR36'] >= 1.2214) & (vars_dict['VAR36'] <= 1.2942)].copy()
    def estrategia_569(    df): return     df_china2[(vars_dict['VAR15'] >= 0.3386) & (vars_dict['VAR15'] <= 0.4205)].copy()
    def estrategia_570(    df): return     df_china2[(vars_dict['VAR28'] >= 1.8248) & (vars_dict['VAR28'] <= 2.5909)].copy()
    def estrategia_571(    df): return     df_china2[(vars_dict['VAR18'] >= 0.6395) & (vars_dict['VAR18'] <= 0.6807)].copy()
    def estrategia_572(    df): return     df_china2[(vars_dict['VAR57'] >= 0.18) & (vars_dict['VAR57'] <= 0.2086)].copy()
    def estrategia_573(    df): return     df_china2[(vars_dict['VAR43'] >= 1.0112) & (vars_dict['VAR43'] <= 1.1591)].copy()
    def estrategia_574(    df): return     df_china2[(vars_dict['VAR70'] >= 0.8856) & (vars_dict['VAR70'] <= 1.7035)].copy()
    def estrategia_575(    df): return     df_china2[(vars_dict['VAR73'] >= 0.3958) & (vars_dict['VAR73'] <= 0.9632)].copy()
    def estrategia_576(    df): return     df_china2[(vars_dict['VAR61'] >= 0.0817) & (vars_dict['VAR61'] <= 0.1238)].copy()
    def estrategia_577(    df): return     df_china2[(vars_dict['VAR49'] >= 1.4) & (vars_dict['VAR49'] <= 1.7542)].copy()
    def estrategia_578(    df): return     df_china2[(vars_dict['VAR38'] >= 2.5608) & (vars_dict['VAR38'] <= 2.9064)].copy()
    def estrategia_579(    df): return     df_china2[(vars_dict['VAR42'] >= 1.165) & (vars_dict['VAR42'] <= 1.2525)].copy()
    def estrategia_580(    df): return     df_china2[(vars_dict['VAR29'] >= 1.2052) & (vars_dict['VAR29'] <= 1.246)].copy()


    # Teste com Ligas "COLOMBIA 1"
    df_colombia1 =     df[    df['League'] == "COLOMBIA 1"].copy()
    def estrategia_581(    df): return     df_colombia1[(vars_dict['VAR64'] >= -1.429) & (vars_dict['VAR64'] <= -0.5601)].copy()
    def estrategia_582(    df): return     df_colombia1[(vars_dict['VAR60'] >= 0.021) & (vars_dict['VAR60'] <= 0.0399)].copy()
    def estrategia_583(    df): return     df_colombia1[(vars_dict['VAR40'] >= 1.7333) & (vars_dict['VAR40'] <= 1.8054)].copy()
    def estrategia_584(    df): return     df_colombia1[(vars_dict['VAR42'] >= 1.4644) & (vars_dict['VAR42'] <= 1.5597)].copy()
    def estrategia_585(    df): return     df_colombia1[(vars_dict['VAR19'] >= 0.6697) & (vars_dict['VAR19'] <= 0.7609)].copy()
    def estrategia_586(    df): return     df_colombia1[(vars_dict['VAR05'] >= 0.7703) & (vars_dict['VAR05'] <= 0.982)].copy()
    def estrategia_587(    df): return     df_colombia1[(vars_dict['VAR02'] >= 1.0183) & (vars_dict['VAR02'] <= 1.2982)].copy()
    def estrategia_588(    df): return     df_colombia1[(vars_dict['VAR62'] >= -2.7204) & (vars_dict['VAR62'] <= -0.1888)].copy()
    def estrategia_589(    df): return     df_colombia1[(vars_dict['VAR24'] >= 2.7907) & (vars_dict['VAR24'] <= 3.2787)].copy()
    def estrategia_590(    df): return     df_colombia1[(vars_dict['VAR23'] >= 1.8015) & (vars_dict['VAR23'] <= 1.9853)].copy()
    def estrategia_591(    df): return     df_colombia1[(vars_dict['VAR06'] >= 0.8506) & (vars_dict['VAR06'] <= 0.9394)].copy()
    def estrategia_592(    df): return     df_colombia1[(vars_dict['VAR69'] >= 0.0) & (vars_dict['VAR69'] <= 2.3392)].copy()
    def estrategia_593(    df): return     df_colombia1[(vars_dict['VAR49'] >= 1.0) & (vars_dict['VAR49'] <= 1.125)].copy()
    def estrategia_594(    df): return     df_colombia1[(vars_dict['VAR25'] >= 2.0221) & (vars_dict['VAR25'] <= 2.3214)].copy()
    def estrategia_595(    df): return     df_colombia1[(vars_dict['VAR11'] >= 1.2121) & (vars_dict['VAR11'] <= 1.2737)].copy()
    def estrategia_596(    df): return     df_colombia1[(vars_dict['VAR47'] >= 0.8889) & (vars_dict['VAR47'] <= 1.0)].copy()
    def estrategia_597(    df): return     df_colombia1[(vars_dict['VAR30'] >= 1.6013) & (vars_dict['VAR30'] <= 1.9643)].copy()
    def estrategia_598(    df): return     df_colombia1[(vars_dict['VAR68'] >= 0.5885) & (vars_dict['VAR68'] <= 1.3745)].copy()
    def estrategia_599(    df): return     df_colombia1[(vars_dict['VAR04'] >= 1.0645) & (vars_dict['VAR04'] <= 1.1757)].copy()
    def estrategia_600(    df): return     df_colombia1[(vars_dict['VAR76'] >= 0.0286) & (vars_dict['VAR76'] <= 0.0515)].copy()


    # Teste com Ligas "COLOMBIA 2"
    df_colombia2 =     df[    df['League'] == "COLOMBIA 2"].copy()
    def estrategia_601(    df): return     df_colombia2[(vars_dict['VAR76'] >= 0.0902) & (vars_dict['VAR76'] <= 0.1059)].copy()
    def estrategia_602(    df): return     df_colombia2[(vars_dict['VAR74'] >= 0.1875) & (vars_dict['VAR74'] <= 0.2098)].copy()
    def estrategia_603(    df): return     df_colombia2[(vars_dict['VAR09'] >= 0.7729) & (vars_dict['VAR09'] <= 0.8095)].copy()
    def estrategia_604(    df): return     df_colombia2[(vars_dict['VAR60'] >= 0.0688) & (vars_dict['VAR60'] <= 0.0759)].copy()
    def estrategia_605(    df): return     df_colombia2[(vars_dict['VAR14'] >= 1.0855) & (vars_dict['VAR14'] <= 1.2696)].copy()
    def estrategia_606(    df): return     df_colombia2[(vars_dict['VAR40'] >= 1.7267) & (vars_dict['VAR40'] <= 1.7872)].copy()
    def estrategia_607(    df): return     df_colombia2[(vars_dict['VAR41'] >= 1.5035) & (vars_dict['VAR41'] <= 1.678)].copy()
    def estrategia_608(    df): return     df_colombia2[(vars_dict['VAR11'] >= 1.2581) & (vars_dict['VAR11'] <= 1.3206)].copy()
    def estrategia_609(    df): return     df_colombia2[(vars_dict['VAR77'] >= 0.2914) & (vars_dict['VAR77'] <= 0.3457)].copy()
    def estrategia_610(    df): return     df_colombia2[(vars_dict['VAR54'] >= 0.2611) & (vars_dict['VAR54'] <= 0.3104)].copy()
    def estrategia_611(    df): return     df_colombia2[(vars_dict['VAR37'] >= 1.8093) & (vars_dict['VAR37'] <= 1.8843)].copy()
    def estrategia_612(    df): return     df_colombia2[(vars_dict['VAR43'] >= 1.1054) & (vars_dict['VAR43'] <= 1.2222)].copy()
    def estrategia_613(    df): return     df_colombia2[(vars_dict['VAR39'] >= 6.0909) & (vars_dict['VAR39'] <= 16.9903)].copy()
    def estrategia_614(    df): return     df_colombia2[(vars_dict['VAR35'] >= 1.0941) & (vars_dict['VAR35'] <= 1.1804)].copy()
    def estrategia_615(    df): return     df_colombia2[(vars_dict['VAR58'] >= 0.101) & (vars_dict['VAR58'] <= 0.1222)].copy()
    def estrategia_616(    df): return     df_colombia2[(vars_dict['VAR03'] >= 0.8846) & (vars_dict['VAR03'] <= 0.9847)].copy()
    def estrategia_617(    df): return     df_colombia2[(vars_dict['VAR01'] >= 1.0156) & (vars_dict['VAR01'] <= 1.1304)].copy()
    def estrategia_618(    df): return     df_colombia2[(vars_dict['VAR63'] >= -1.3415) & (vars_dict['VAR63'] <= -0.1371)].copy()
    def estrategia_619(    df): return     df_colombia2[(vars_dict['VAR18'] >= 0.6799) & (vars_dict['VAR18'] <= 0.7203)].copy()
    def estrategia_620(    df): return     df_colombia2[(vars_dict['VAR34'] >= 1.1514) & (vars_dict['VAR34'] <= 1.306)].copy()


    # Teste com Ligas "CROATIA 1"
    df_croatia1 =     df[    df['League'] == "CROATIA 1"].copy()
    def estrategia_621(    df): return     df_croatia1[(vars_dict['VAR20'] >= 0.2922) & (vars_dict['VAR20'] <= 0.4383)].copy()
    def estrategia_622(    df): return     df_croatia1[(vars_dict['VAR23'] >= 3.2334) & (vars_dict['VAR23'] <= 4.8)].copy()
    def estrategia_623(    df): return     df_croatia1[(vars_dict['VAR30'] >= 3.542) & (vars_dict['VAR30'] <= 5.3384)].copy()
    def estrategia_624(    df): return     df_croatia1[(vars_dict['VAR05'] >= 2.3419) & (vars_dict['VAR05'] <= 3.9451)].copy()
    def estrategia_625(    df): return     df_croatia1[(vars_dict['VAR02'] >= 0.2535) & (vars_dict['VAR02'] <= 0.427)].copy()
    def estrategia_626(    df): return     df_croatia1[(vars_dict['VAR25'] >= 1.2322) & (vars_dict['VAR25'] <= 1.4)].copy()
    def estrategia_627(    df): return     df_croatia1[(vars_dict['VAR19'] >= 1.0297) & (vars_dict['VAR19'] <= 1.3072)].copy()
    def estrategia_628(    df): return     df_croatia1[(vars_dict['VAR69'] >= -13.2127) & (vars_dict['VAR69'] <= -8.8044)].copy()
    def estrategia_629(    df): return     df_croatia1[(vars_dict['VAR49'] >= 0.4723) & (vars_dict['VAR49'] <= 0.6267)].copy()
    def estrategia_630(    df): return     df_croatia1[(vars_dict['VAR47'] >= 1.5957) & (vars_dict['VAR47'] <= 2.1176)].copy()
    def estrategia_631(    df): return     df_croatia1[(vars_dict['VAR62'] >= 9.0639) & (vars_dict['VAR62'] <= 13.7188)].copy()
    def estrategia_632(    df): return     df_croatia1[(vars_dict['VAR17'] >= 0.3469) & (vars_dict['VAR17'] <= 0.4452)].copy()
    def estrategia_633(    df): return     df_croatia1[(vars_dict['VAR38'] >= 1.6191) & (vars_dict['VAR38'] <= 1.7931)].copy()
    def estrategia_634(    df): return     df_croatia1[(vars_dict['VAR43'] >= 0.7269) & (vars_dict['VAR43'] <= 0.9424)].copy()
    def estrategia_635(    df): return     df_croatia1[(vars_dict['VAR13'] >= 0.9777) & (vars_dict['VAR13'] <= 1.1153)].copy()
    def estrategia_636(    df): return     df_croatia1[(vars_dict['VAR39'] >= 0.6429) & (vars_dict['VAR39'] <= 0.9581)].copy()
    def estrategia_637(    df): return     df_croatia1[(vars_dict['VAR01'] >= 0.6507) & (vars_dict['VAR01'] <= 0.8225)].copy()
    def estrategia_638(    df): return     df_croatia1[(vars_dict['VAR03'] >= 1.2158) & (vars_dict['VAR03'] <= 1.5369)].copy()
    def estrategia_639(    df): return     df_croatia1[(vars_dict['VAR44'] >= 0.907) & (vars_dict['VAR44'] <= 0.9456)].copy()
    def estrategia_640(    df): return     df_croatia1[(vars_dict['VAR35'] >= 1.5508) & (vars_dict['VAR35'] <= 1.797)].copy()


    # Teste com Ligas "CZECH 1"
    df_czech1 =     df[    df['League'] == "CZECH 1"].copy()
    def estrategia_641(    df): return     df_czech1[(vars_dict['VAR31'] >= 1.5455) & (vars_dict['VAR31'] <= 1.6744)].copy()
    def estrategia_642(    df): return     df_czech1[(vars_dict['VAR45'] >= 0.9184) & (vars_dict['VAR45'] <= 0.9402)].copy()
    def estrategia_643(    df): return     df_czech1[(vars_dict['VAR26'] >= 1.4231) & (vars_dict['VAR26'] <= 1.4603)].copy()
    def estrategia_644(    df): return     df_czech1[(vars_dict['VAR28'] >= 1.5082) & (vars_dict['VAR28'] <= 1.6237)].copy()
    def estrategia_645(    df): return     df_czech1[(vars_dict['VAR13'] >= 0.2882) & (vars_dict['VAR13'] <= 0.3851)].copy()
    def estrategia_646(    df): return     df_czech1[(vars_dict['VAR64'] >= -3.6452) & (vars_dict['VAR64'] <= -2.1742)].copy()
    def estrategia_647(    df): return     df_czech1[(vars_dict['VAR56'] >= 0.062) & (vars_dict['VAR56'] <= 0.0772)].copy()
    def estrategia_648(    df): return     df_czech1[(vars_dict['VAR04'] >= 1.6667) & (vars_dict['VAR04'] <= 2.6154)].copy()
    def estrategia_649(    df): return     df_czech1[(vars_dict['VAR32'] >= 2.5455) & (vars_dict['VAR32'] <= 3.7143)].copy()
    def estrategia_650(    df): return     df_czech1[(vars_dict['VAR46'] >= 0.4727) & (vars_dict['VAR46'] <= 0.5952)].copy()
    def estrategia_651(    df): return     df_czech1[(vars_dict['VAR09'] >= 0.8293) & (vars_dict['VAR09'] <= 0.9231)].copy()
    def estrategia_652(    df): return     df_czech1[(vars_dict['VAR48'] >= 1.0636) & (vars_dict['VAR48'] <= 1.0889)].copy()
    def estrategia_653(    df): return     df_czech1[(vars_dict['VAR19'] >= 0.3086) & (vars_dict['VAR19'] <= 0.3789)].copy()
    def estrategia_654(    df): return     df_czech1[(vars_dict['VAR29'] >= 1.5789) & (vars_dict['VAR29'] <= 1.6154)].copy()
    def estrategia_655(    df): return     df_czech1[(vars_dict['VAR15'] >= 0.5) & (vars_dict['VAR15'] <= 0.5219)].copy()
    def estrategia_656(    df): return     df_czech1[(vars_dict['VAR23'] >= 1.2177) & (vars_dict['VAR23'] <= 1.3525)].copy()
    def estrategia_657(    df): return     df_czech1[(vars_dict['VAR68'] >= 2.0396) & (vars_dict['VAR68'] <= 3.8302)].copy()
    def estrategia_658(    df): return     df_czech1[(vars_dict['VAR33'] >= 0.683) & (vars_dict['VAR33'] <= 0.8629)].copy()
    def estrategia_659(    df): return     df_czech1[(vars_dict['VAR63'] >= -12.5288) & (vars_dict['VAR63'] <= -9.3215)].copy()
    def estrategia_660(    df): return     df_czech1[(vars_dict['VAR06'] >= 0.3824) & (vars_dict['VAR06'] <= 0.6)].copy()


    # Teste com Ligas "DENMARK 1"
    df_denmark1 =     df[    df['League'] == "DENMARK 1"].copy()
    def estrategia_661(    df): return     df_denmark1[(vars_dict['VAR16'] >= 0.8944) & (vars_dict['VAR16'] <= 1.047)].copy()
    def estrategia_662(    df): return     df_denmark1[(vars_dict['VAR34'] >= 1.4661) & (vars_dict['VAR34'] <= 1.6173)].copy()
    def estrategia_663(    df): return     df_denmark1[(vars_dict['VAR29'] >= 1.5385) & (vars_dict['VAR29'] <= 1.5789)].copy()
    def estrategia_664(    df): return     df_denmark1[(vars_dict['VAR74'] >= 0.0833) & (vars_dict['VAR74'] <= 0.1429)].copy()
    def estrategia_665(    df): return     df_denmark1[(vars_dict['VAR12'] >= 0.4538) & (vars_dict['VAR12'] <= 0.4762)].copy()
    def estrategia_666(    df): return     df_denmark1[(vars_dict['VAR48'] >= 0.7167) & (vars_dict['VAR48'] <= 0.817)].copy()
    def estrategia_667(    df): return     df_denmark1[(vars_dict['VAR28'] >= 1.1475) & (vars_dict['VAR28'] <= 1.2171)].copy()
    def estrategia_668(    df): return     df_denmark1[(vars_dict['VAR59'] >= 0.0212) & (vars_dict['VAR59'] <= 0.035)].copy()
    def estrategia_669(    df): return     df_denmark1[(vars_dict['VAR18'] >= 0.4763) & (vars_dict['VAR18'] <= 0.5)].copy()
    def estrategia_670(    df): return     df_denmark1[(vars_dict['VAR68'] >= -6.2671) & (vars_dict['VAR68'] <= -4.1867)].copy()
    def estrategia_671(    df): return     df_denmark1[(vars_dict['VAR40'] >= 0.9818) & (vars_dict['VAR40'] <= 1.1089)].copy()
    def estrategia_672(    df): return     df_denmark1[(vars_dict['VAR24'] >= 2.6154) & (vars_dict['VAR24'] <= 2.7132)].copy()
    def estrategia_673(    df): return     df_denmark1[(vars_dict['VAR17'] >= 0.5649) & (vars_dict['VAR17'] <= 0.6398)].copy()
    def estrategia_674(    df): return     df_denmark1[(vars_dict['VAR35'] >= 1.0417) & (vars_dict['VAR35'] <= 1.1229)].copy()
    def estrategia_675(    df): return     df_denmark1[(vars_dict['VAR26'] >= 1.5009) & (vars_dict['VAR26'] <= 1.5736)].copy()
    def estrategia_676(    df): return     df_denmark1[(vars_dict['VAR09'] >= 1.0833) & (vars_dict['VAR09'] <= 1.1429)].copy()
    def estrategia_677(    df): return     df_denmark1[(vars_dict['VAR31'] >= 2.3529) & (vars_dict['VAR31'] <= 2.5451)].copy()
    def estrategia_678(    df): return     df_denmark1[(vars_dict['VAR76'] >= 0.224) & (vars_dict['VAR76'] <= 0.3953)].copy()
    def estrategia_679(    df): return     df_denmark1[(vars_dict['VAR45'] >= 1.224) & (vars_dict['VAR45'] <= 1.3953)].copy()
    def estrategia_680(    df): return     df_denmark1[(vars_dict['VAR11'] >= 0.5048) & (vars_dict['VAR11'] <= 0.6033)].copy()


    # Teste com Ligas "DENMARK 2"
    df_denmark2 =     df[    df['League'] == "DENMARK 2"].copy()
    def estrategia_681(    df): return     df_denmark2[(vars_dict['VAR54'] >= 0.3275) & (vars_dict['VAR54'] <= 0.3679)].copy()
    def estrategia_682(    df): return     df_denmark2[(vars_dict['VAR61'] >= 0.3197) & (vars_dict['VAR61'] <= 0.3682)].copy()
    def estrategia_683(    df): return     df_denmark2[(vars_dict['VAR20'] >= 1.4654) & (vars_dict['VAR20'] <= 1.75)].copy()
    def estrategia_684(    df): return     df_denmark2[(vars_dict['VAR26'] >= 1.4129) & (vars_dict['VAR26'] <= 1.4729)].copy()
    def estrategia_685(    df): return     df_denmark2[(vars_dict['VAR34'] >= 1.1171) & (vars_dict['VAR34'] <= 1.2085)].copy()
    def estrategia_686(    df): return     df_denmark2[(vars_dict['VAR23'] >= 1.3447) & (vars_dict['VAR23'] <= 1.435)].copy()
    def estrategia_687(    df): return     df_denmark2[(vars_dict['VAR13'] >= 0.2583) & (vars_dict['VAR13'] <= 0.3632)].copy()
    def estrategia_688(    df): return     df_denmark2[(vars_dict['VAR21'] >= 0.4884) & (vars_dict['VAR21'] <= 0.5306)].copy()
    def estrategia_689(    df): return     df_denmark2[(vars_dict['VAR48'] >= 1.0) & (vars_dict['VAR48'] <= 1.0346)].copy()
    def estrategia_690(    df): return     df_denmark2[(vars_dict['VAR68'] >= 0.0) & (vars_dict['VAR68'] <= 0.8295)].copy()
    def estrategia_691(    df): return     df_denmark2[(vars_dict['VAR43'] >= 1.9323) & (vars_dict['VAR43'] <= 2.2288)].copy()
    def estrategia_692(    df): return     df_denmark2[(vars_dict['VAR31'] >= 1.976) & (vars_dict['VAR31'] <= 2.0778)].copy()
    def estrategia_693(    df): return     df_denmark2[(vars_dict['VAR35'] >= 1.2534) & (vars_dict['VAR35'] <= 1.3701)].copy()
    def estrategia_694(    df): return     df_denmark2[(vars_dict['VAR56'] >= 0.0162) & (vars_dict['VAR56'] <= 0.0285)].copy()
    def estrategia_695(    df): return     df_denmark2[(vars_dict['VAR41'] >= 1.0485) & (vars_dict['VAR41'] <= 1.1833)].copy()
    def estrategia_696(    df): return     df_denmark2[(vars_dict['VAR65'] >= -3.8241) & (vars_dict['VAR65'] <= -3.2065)].copy()
    def estrategia_697(    df): return     df_denmark2[(vars_dict['VAR08'] >= 0.7767) & (vars_dict['VAR08'] <= 0.8095)].copy()
    def estrategia_698(    df): return     df_denmark2[(vars_dict['VAR19'] >= 0.2833) & (vars_dict['VAR19'] <= 0.3642)].copy()
    def estrategia_699(    df): return     df_denmark2[(vars_dict['VAR76'] >= 0.0208) & (vars_dict['VAR76'] <= 0.0339)].copy()
    def estrategia_700(    df): return     df_denmark2[(vars_dict['VAR60'] >= 0.0158) & (vars_dict['VAR60'] <= 0.0297)].copy()


    # Teste com Ligas "ECUADOR 1"
    df_ecuador1 =     df[    df['League'] == "ECUADOR 1"].copy()
    def estrategia_701(    df): return     df_ecuador1[(vars_dict['VAR57'] >= 0.112) & (vars_dict['VAR57'] <= 0.1337)].copy()
    def estrategia_702(    df): return     df_ecuador1[(vars_dict['VAR55'] >= 0.0728) & (vars_dict['VAR55'] <= 0.1133)].copy()
    def estrategia_703(    df): return     df_ecuador1[(vars_dict['VAR16'] >= 0.4411) & (vars_dict['VAR16'] <= 0.4872)].copy()
    def estrategia_704(    df): return     df_ecuador1[(vars_dict['VAR42'] >= 1.3456) & (vars_dict['VAR42'] <= 1.4286)].copy()
    def estrategia_705(    df): return     df_ecuador1[(vars_dict['VAR08'] >= 1.2311) & (vars_dict['VAR08'] <= 1.2874)].copy()
    def estrategia_706(    df): return     df_ecuador1[(vars_dict['VAR65'] >= 3.1674) & (vars_dict['VAR65'] <= 3.8241)].copy()
    def estrategia_707(    df): return     df_ecuador1[(vars_dict['VAR61'] >= 0.4103) & (vars_dict['VAR61'] <= 0.5007)].copy()
    def estrategia_708(    df): return     df_ecuador1[(vars_dict['VAR73'] >= 0.1905) & (vars_dict['VAR73'] <= 0.2233)].copy()
    def estrategia_709(    df): return     df_ecuador1[(vars_dict['VAR45'] >= 0.9457) & (vars_dict['VAR45'] <= 0.9714)].copy()
    def estrategia_710(    df): return     df_ecuador1[(vars_dict['VAR06'] >= 0.8395) & (vars_dict['VAR06'] <= 0.9231)].copy()
    def estrategia_711(    df): return     df_ecuador1[(vars_dict['VAR60'] >= 0.0308) & (vars_dict['VAR60'] <= 0.0444)].copy()
    def estrategia_712(    df): return     df_ecuador1[(vars_dict['VAR26'] >= 1.5441) & (vars_dict['VAR26'] <= 1.5809)].copy()
    def estrategia_713(    df): return     df_ecuador1[(vars_dict['VAR54'] >= 0.4201) & (vars_dict['VAR54'] <= 0.5128)].copy()
    def estrategia_714(    df): return     df_ecuador1[(vars_dict['VAR14'] >= 0.6464) & (vars_dict['VAR14'] <= 0.7268)].copy()
    def estrategia_715(    df): return     df_ecuador1[(vars_dict['VAR71'] >= 0.2391) & (vars_dict['VAR71'] <= 0.3796)].copy()
    def estrategia_716(    df): return     df_ecuador1[(vars_dict['VAR04'] >= 1.0833) & (vars_dict['VAR04'] <= 1.1911)].copy()
    def estrategia_717(    df): return     df_ecuador1[(vars_dict['VAR03'] >= 0.7321) & (vars_dict['VAR03'] <= 0.8308)].copy()
    def estrategia_718(    df): return     df_ecuador1[(vars_dict['VAR68'] >= 1.274) & (vars_dict['VAR68'] <= 1.6474)].copy()
    def estrategia_719(    df): return     df_ecuador1[(vars_dict['VAR76'] >= 0.0385) & (vars_dict['VAR76'] <= 0.0543)].copy()
    def estrategia_720(    df): return     df_ecuador1[(vars_dict['VAR43'] >= 1.4077) & (vars_dict['VAR43'] <= 1.4613)].copy()


    # Teste com Ligas "EGYPT 1"
    df_egypt1 =     df[    df['League'] == "EGYPT 1"].copy()
    def estrategia_721(    df): return     df_egypt1[(vars_dict['VAR29'] >= 1.4462) & (vars_dict['VAR29'] <= 1.6693)].copy()
    def estrategia_722(    df): return     df_egypt1[(vars_dict['VAR10'] >= 0.7406) & (vars_dict['VAR10'] <= 0.9435)].copy()
    def estrategia_723(    df): return     df_egypt1[(vars_dict['VAR09'] >= 1.0599) & (vars_dict['VAR09'] <= 1.3503)].copy()
    def estrategia_724(    df): return     df_egypt1[(vars_dict['VAR66'] >= -4.7232) & (vars_dict['VAR66'] <= -0.907)].copy()
    def estrategia_725(    df): return     df_egypt1[(vars_dict['VAR20'] >= 1.0803) & (vars_dict['VAR20'] <= 1.3793)].copy()
    def estrategia_726(    df): return     df_egypt1[(vars_dict['VAR17'] >= 0.9655) & (vars_dict['VAR17'] <= 1.0842)].copy()
    def estrategia_727(    df): return     df_egypt1[(vars_dict['VAR26'] >= 1.2685) & (vars_dict['VAR26'] <= 1.4627)].copy()
    def estrategia_728(    df): return     df_egypt1[(vars_dict['VAR41'] >= 1.5772) & (vars_dict['VAR41'] <= 2.5192)].copy()
    def estrategia_729(    df): return     df_egypt1[(vars_dict['VAR33'] >= 1.4691) & (vars_dict['VAR33'] <= 1.5757)].copy()
    def estrategia_730(    df): return     df_egypt1[(vars_dict['VAR72'] >= 0.3352) & (vars_dict['VAR72'] <= 0.4323)].copy()
    def estrategia_731(    df): return     df_egypt1[(vars_dict['VAR34'] >= 0.7947) & (vars_dict['VAR34'] <= 0.8585)].copy()
    def estrategia_732(    df): return     df_egypt1[(vars_dict['VAR36'] >= 0.8718) & (vars_dict['VAR36'] <= 0.9798)].copy()
    def estrategia_733(    df): return     df_egypt1[(vars_dict['VAR65'] >= -9.8775) & (vars_dict['VAR65'] <= -0.3349)].copy()
    def estrategia_734(    df): return     df_egypt1[(vars_dict['VAR08'] >= 0.5229) & (vars_dict['VAR08'] <= 0.9786)].copy()
    def estrategia_735(    df): return     df_egypt1[(vars_dict['VAR14'] >= 1.0857) & (vars_dict['VAR14'] <= 2.2586)].copy()
    def estrategia_736(    df): return     df_egypt1[(vars_dict['VAR35'] >= 0.4086) & (vars_dict['VAR35'] <= 0.8213)].copy()
    def estrategia_737(    df): return     df_egypt1[(vars_dict['VAR30'] >= 0.9292) & (vars_dict['VAR30'] <= 1.1829)].copy()
    def estrategia_738(    df): return     df_egypt1[(vars_dict['VAR73'] >= 0.0107) & (vars_dict['VAR73'] <= 0.0843)].copy()
    def estrategia_739(    df): return     df_egypt1[(vars_dict['VAR07'] >= 1.0219) & (vars_dict['VAR07'] <= 1.9124)].copy()
    def estrategia_740(    df): return     df_egypt1[(vars_dict['VAR28'] >= 1.194) & (vars_dict['VAR28'] <= 1.3185)].copy()


    # Teste com Ligas "ENGLAND 1"
    df_england1 =     df[    df['League'] == "ENGLAND 1"].copy()
    def estrategia_741(    df): return     df_england1[(vars_dict['VAR22'] >= 0.5789) & (vars_dict['VAR22'] <= 0.7)].copy()
    def estrategia_742(    df): return     df_england1[(vars_dict['VAR37'] >= 1.5116) & (vars_dict['VAR37'] <= 1.6279)].copy()
    def estrategia_743(    df): return     df_england1[(vars_dict['VAR32'] >= 1.9231) & (vars_dict['VAR32'] <= 2.0461)].copy()
    def estrategia_744(    df): return     df_england1[(vars_dict['VAR72'] >= 0.0) & (vars_dict['VAR72'] <= 0.0526)].copy()
    def estrategia_745(    df): return     df_england1[(vars_dict['VAR60'] >= 0.0) & (vars_dict['VAR60'] <= 0.019)].copy()
    def estrategia_746(    df): return     df_england1[(vars_dict['VAR76'] >= 0.0) & (vars_dict['VAR76'] <= 0.0233)].copy()
    def estrategia_747(    df): return     df_england1[(vars_dict['VAR39'] >= 2.3529) & (vars_dict['VAR39'] <= 3.04)].copy()
    def estrategia_748(    df): return     df_england1[(vars_dict['VAR23'] >= 1.5164) & (vars_dict['VAR23'] <= 1.6912)].copy()
    def estrategia_749(    df): return     df_england1[(vars_dict['VAR05'] >= 0.5026) & (vars_dict['VAR05'] <= 0.6774)].copy()
    def estrategia_750(    df): return     df_england1[(vars_dict['VAR31'] >= 2.0229) & (vars_dict['VAR31'] <= 2.1557)].copy()
    def estrategia_751(    df): return     df_england1[(vars_dict['VAR29'] >= 1.7442) & (vars_dict['VAR29'] <= 1.8056)].copy()
    def estrategia_752(    df): return     df_england1[(vars_dict['VAR56'] >= 0.0) & (vars_dict['VAR56'] <= 0.0139)].copy()
    def estrategia_753(    df): return     df_england1[(vars_dict['VAR24'] >= 3.2787) & (vars_dict['VAR24'] <= 3.4426)].copy()
    def estrategia_754(    df): return     df_england1[(vars_dict['VAR34'] >= 1.6112) & (vars_dict['VAR34'] <= 1.8726)].copy()
    def estrategia_755(    df): return     df_england1[(vars_dict['VAR44'] >= 1.2869) & (vars_dict['VAR44'] <= 1.4663)].copy()
    def estrategia_756(    df): return     df_england1[(vars_dict['VAR75'] >= 0.2869) & (vars_dict['VAR75'] <= 0.4663)].copy()
    def estrategia_757(    df): return     df_england1[(vars_dict['VAR18'] >= 0.319) & (vars_dict['VAR18'] <= 0.35)].copy()
    def estrategia_758(    df): return     df_england1[(vars_dict['VAR73'] >= 0.0848) & (vars_dict['VAR73'] <= 0.1159)].copy()
    def estrategia_759(    df): return     df_england1[(vars_dict['VAR16'] >= 0.5757) & (vars_dict['VAR16'] <= 0.691)].copy()
    def estrategia_760(    df): return     df_england1[(vars_dict['VAR36'] >= 1.1777) & (vars_dict['VAR36'] <= 1.3487)].copy()


    # Teste com Ligas "ENGLAND 2"
    df_england2 =     df[    df['League'] == "ENGLAND 2"].copy()
    def estrategia_761(    df): return     df_england2[(vars_dict['VAR01'] >= 0.4737) & (vars_dict['VAR01'] <= 0.9487)].copy()
    def estrategia_762(    df): return     df_england2[(vars_dict['VAR03'] >= 1.0541) & (vars_dict['VAR03'] <= 2.1111)].copy()
    def estrategia_763(    df): return     df_england2[(vars_dict['VAR37'] >= 2.0733) & (vars_dict['VAR37'] <= 3.1667)].copy()
    def estrategia_764(    df): return     df_england2[(vars_dict['VAR57'] >= 0.0538) & (vars_dict['VAR57'] <= 0.0836)].copy()
    def estrategia_765(    df): return     df_england2[(vars_dict['VAR46'] >= 1.0231) & (vars_dict['VAR46'] <= 1.1525)].copy()
    def estrategia_766(    df): return     df_england2[(vars_dict['VAR67'] >= 0.4971) & (vars_dict['VAR67'] <= 3.2099)].copy()
    def estrategia_767(    df): return     df_england2[(vars_dict['VAR66'] >= 3.5082) & (vars_dict['VAR66'] <= 9.9443)].copy()
    def estrategia_768(    df): return     df_england2[(vars_dict['VAR10'] >= 1.2575) & (vars_dict['VAR10'] <= 1.9643)].copy()
    def estrategia_769(    df): return     df_england2[(vars_dict['VAR32'] >= 1.217) & (vars_dict['VAR32'] <= 1.5504)].copy()
    def estrategia_770(    df): return     df_england2[(vars_dict['VAR60'] >= 0.2196) & (vars_dict['VAR60'] <= 0.5915)].copy()
    def estrategia_771(    df): return     df_england2[(vars_dict['VAR58'] >= 0.1226) & (vars_dict['VAR58'] <= 0.1627)].copy()
    def estrategia_772(    df): return     df_england2[(vars_dict['VAR44'] >= 0.8676) & (vars_dict['VAR44'] <= 0.9774)].copy()
    def estrategia_773(    df): return     df_england2[(vars_dict['VAR39'] >= 0.3686) & (vars_dict['VAR39'] <= 1.0833)].copy()
    def estrategia_774(    df): return     df_england2[(vars_dict['VAR77'] >= 0.64) & (vars_dict['VAR77'] <= 2.3019)].copy()
    def estrategia_775(    df): return     df_england2[(vars_dict['VAR45'] >= 1.3953) & (vars_dict['VAR45'] <= 3.0702)].copy()
    def estrategia_776(    df): return     df_england2[(vars_dict['VAR76'] >= 0.3953) & (vars_dict['VAR76'] <= 2.0702)].copy()
    def estrategia_777(    df): return     df_england2[(vars_dict['VAR63'] >= 0.4227) & (vars_dict['VAR63'] <= 3.3542)].copy()
    def estrategia_778(    df): return     df_england2[(vars_dict['VAR35'] >= 1.4661) & (vars_dict['VAR35'] <= 2.2288)].copy()
    def estrategia_779(    df): return     df_england2[(vars_dict['VAR41'] >= 0.6286) & (vars_dict['VAR41'] <= 1.0105)].copy()
    def estrategia_780(    df): return     df_england2[(vars_dict['VAR56'] >= 0.2271) & (vars_dict['VAR56'] <= 0.6013)].copy()


    # Teste com Ligas "ENGLAND 3"
    df_england3 =     df[    df['League'] == "ENGLAND 3"].copy()
    def estrategia_781(    df): return     df_england3[(vars_dict['VAR72'] >= 0.32) & (vars_dict['VAR72'] <= 0.392)].copy()
    def estrategia_782(    df): return     df_england3[(vars_dict['VAR32'] >= 1.528) & (vars_dict['VAR32'] <= 1.6396)].copy()
    def estrategia_783(    df): return     df_england3[(vars_dict['VAR26'] >= 1.4344) & (vars_dict['VAR26'] <= 1.4961)].copy()
    def estrategia_784(    df): return     df_england3[(vars_dict['VAR59'] >= 0.0236) & (vars_dict['VAR59'] <= 0.0408)].copy()
    def estrategia_785(    df): return     df_england3[(vars_dict['VAR75'] >= 0.031) & (vars_dict['VAR75'] <= 0.0543)].copy()
    def estrategia_786(    df): return     df_england3[(vars_dict['VAR56'] >= 0.1637) & (vars_dict['VAR56'] <= 0.2406)].copy()
    def estrategia_787(    df): return     df_england3[(vars_dict['VAR64'] >= 4.679) & (vars_dict['VAR64'] <= 6.8598)].copy()
    def estrategia_788(    df): return     df_england3[(vars_dict['VAR06'] >= 1.5588) & (vars_dict['VAR06'] <= 1.8421)].copy()
    def estrategia_789(    df): return     df_england3[(vars_dict['VAR27'] >= 1.5116) & (vars_dict['VAR27'] <= 1.584)].copy()
    def estrategia_790(    df): return     df_england3[(vars_dict['VAR02'] >= 0.6935) & (vars_dict['VAR02'] <= 0.954)].copy()
    def estrategia_791(    df): return     df_england3[(vars_dict['VAR69'] >= -3.9041) & (vars_dict['VAR69'] <= -0.7957)].copy()
    def estrategia_792(    df): return     df_england3[(vars_dict['VAR22'] >= 0.8913) & (vars_dict['VAR22'] <= 1.0263)].copy()
    def estrategia_793(    df): return     df_england3[(vars_dict['VAR49'] >= 0.8144) & (vars_dict['VAR49'] <= 0.96)].copy()
    def estrategia_794(    df): return     df_england3[(vars_dict['VAR36'] >= 1.47) & (vars_dict['VAR36'] <= 1.5789)].copy()
    def estrategia_795(    df): return     df_england3[(vars_dict['VAR62'] >= 0.5117) & (vars_dict['VAR62'] <= 4.0709)].copy()
    def estrategia_796(    df): return     df_england3[(vars_dict['VAR04'] >= 0.5429) & (vars_dict['VAR04'] <= 0.6415)].copy()
    def estrategia_797(    df): return     df_england3[(vars_dict['VAR18'] >= 0.5) & (vars_dict['VAR18'] <= 0.5143)].copy()
    def estrategia_798(    df): return     df_england3[(vars_dict['VAR05'] >= 1.0482) & (vars_dict['VAR05'] <= 1.4419)].copy()
    def estrategia_799(    df): return     df_england3[(vars_dict['VAR45'] >= 1.2559) & (vars_dict['VAR45'] <= 1.4186)].copy()
    def estrategia_800(    df): return     df_england3[(vars_dict['VAR76'] >= 0.2559) & (vars_dict['VAR76'] <= 0.4186)].copy()


    # Teste com Ligas "ENGLAND 4"
    df_england4 =     df[    df['League'] == "ENGLAND 4"].copy()
    def estrategia_801(    df): return     df_england4[(vars_dict['VAR28'] >= 1.3953) & (vars_dict['VAR28'] <= 1.4186)].copy()
    def estrategia_802(    df): return     df_england4[(vars_dict['VAR18'] >= 0.5) & (vars_dict['VAR18'] <= 0.5229)].copy()
    def estrategia_803(    df): return     df_england4[(vars_dict['VAR34'] >= 1.0722) & (vars_dict['VAR34'] <= 1.1257)].copy()
    def estrategia_804(    df): return     df_england4[(vars_dict['VAR22'] >= 0.625) & (vars_dict['VAR22'] <= 0.6897)].copy()
    def estrategia_805(    df): return     df_england4[(vars_dict['VAR72'] >= 0.1212) & (vars_dict['VAR72'] <= 0.1667)].copy()
    def estrategia_806(    df): return     df_england4[(vars_dict['VAR74'] >= 0.0611) & (vars_dict['VAR74'] <= 0.135)].copy()
    def estrategia_807(    df): return     df_england4[(vars_dict['VAR66'] >= -0.9165) & (vars_dict['VAR66'] <= 0.0)].copy()
    def estrategia_808(    df): return     df_england4[(vars_dict['VAR10'] >= 0.9424) & (vars_dict['VAR10'] <= 1.0)].copy()
    def estrategia_809(    df): return     df_england4[(vars_dict['VAR09'] >= 1.0611) & (vars_dict['VAR09'] <= 1.1561)].copy()
    def estrategia_810(    df): return     df_england4[(vars_dict['VAR58'] >= 0.032) & (vars_dict['VAR58'] <= 0.078)].copy()
    def estrategia_811(    df): return     df_england4[(vars_dict['VAR15'] >= 0.5489) & (vars_dict['VAR15'] <= 0.5639)].copy()
    def estrategia_812(    df): return     df_england4[(vars_dict['VAR43'] >= 1.2346) & (vars_dict['VAR43'] <= 1.3268)].copy()
    def estrategia_813(    df): return     df_england4[(vars_dict['VAR20'] >= 0.7605) & (vars_dict['VAR20'] <= 0.8264)].copy()
    def estrategia_814(    df): return     df_england4[(vars_dict['VAR60'] >= 0.0339) & (vars_dict['VAR60'] <= 0.0445)].copy()
    def estrategia_815(    df): return     df_england4[(vars_dict['VAR27'] >= 1.4186) & (vars_dict['VAR27'] <= 1.4729)].copy()
    def estrategia_816(    df): return     df_england4[(vars_dict['VAR38'] >= 2.0) & (vars_dict['VAR38'] <= 2.1327)].copy()
    def estrategia_817(    df): return     df_england4[(vars_dict['VAR37'] >= 1.6429) & (vars_dict['VAR37'] <= 1.7014)].copy()
    def estrategia_818(    df): return     df_england4[(vars_dict['VAR54'] >= 0.1914) & (vars_dict['VAR54'] <= 0.237)].copy()
    def estrategia_819(    df): return     df_england4[(vars_dict['VAR13'] >= 0.6894) & (vars_dict['VAR13'] <= 0.7454)].copy()
    def estrategia_820(    df): return     df_england4[(vars_dict['VAR19'] >= 0.6595) & (vars_dict['VAR19'] <= 0.7399)].copy()


    # Teste com Ligas "ENGLAND 5"
    df_england5 =     df[    df['League'] == "ENGLAND 5"].copy()
    def estrategia_821(    df): return     df_england5[(vars_dict['VAR24'] >= 2.7132) & (vars_dict['VAR24'] <= 2.7907)].copy()
    def estrategia_822(    df): return     df_england5[(vars_dict['VAR26'] >= 1.2558) & (vars_dict['VAR26'] <= 1.3141)].copy()
    def estrategia_823(    df): return     df_england5[(vars_dict['VAR61'] >= 0.2516) & (vars_dict['VAR61'] <= 0.3098)].copy()
    def estrategia_824(    df): return     df_england5[(vars_dict['VAR57'] >= 0.1728) & (vars_dict['VAR57'] <= 0.2369)].copy()
    def estrategia_825(    df): return     df_england5[(vars_dict['VAR72'] >= 0.4396) & (vars_dict['VAR72'] <= 0.5536)].copy()
    def estrategia_826(    df): return     df_england5[(vars_dict['VAR63'] >= -3.2705) & (vars_dict['VAR63'] <= -2.4171)].copy()
    def estrategia_827(    df): return     df_england5[(vars_dict['VAR33'] >= 1.3001) & (vars_dict['VAR33'] <= 1.384)].copy()
    def estrategia_828(    df): return     df_england5[(vars_dict['VAR36'] >= 1.68) & (vars_dict['VAR36'] <= 2.0388)].copy()
    def estrategia_829(    df): return     df_england5[(vars_dict['VAR16'] >= 0.3615) & (vars_dict['VAR16'] <= 0.4538)].copy()
    def estrategia_830(    df): return     df_england5[(vars_dict['VAR31'] >= 2.7869) & (vars_dict['VAR31'] <= 4.9065)].copy()
    def estrategia_831(    df): return     df_england5[(vars_dict['VAR54'] >= 0.2607) & (vars_dict['VAR54'] <= 0.3214)].copy()
    def estrategia_832(    df): return     df_england5[(vars_dict['VAR77'] >= 0.5154) & (vars_dict['VAR77'] <= 0.6398)].copy()
    def estrategia_833(    df): return     df_england5[(vars_dict['VAR46'] >= 0.1178) & (vars_dict['VAR46'] <= 0.472)].copy()
    def estrategia_834(    df): return     df_england5[(vars_dict['VAR74'] >= 0.358) & (vars_dict['VAR74'] <= 0.4331)].copy()
    def estrategia_835(    df): return     df_england5[(vars_dict['VAR30'] >= 0.1189) & (vars_dict['VAR30'] <= 0.5944)].copy()
    def estrategia_836(    df): return     df_england5[(vars_dict['VAR66'] >= -4.6519) & (vars_dict['VAR66'] <= -3.5082)].copy()
    def estrategia_837(    df): return     df_england5[(vars_dict['VAR10'] >= 0.7364) & (vars_dict['VAR10'] <= 0.7952)].copy()
    def estrategia_838(    df): return     df_england5[(vars_dict['VAR09'] >= 1.358) & (vars_dict['VAR09'] <= 1.4331)].copy()
    def estrategia_839(    df): return     df_england5[(vars_dict['VAR65'] >= -4.9392) & (vars_dict['VAR65'] <= -3.2065)].copy()
    def estrategia_840(    df): return     df_england5[(vars_dict['VAR08'] >= 0.72) & (vars_dict['VAR08'] <= 0.8095)].copy()


    # Teste com Ligas "ESTONIA 1"
    df_estonia1 =     df[    df['League'] == "ESTONIA 1"].copy()
    def estrategia_841(    df): return     df_estonia1[(vars_dict['VAR28'] >= 1.3675) & (vars_dict['VAR28'] <= 1.4286)].copy()
    def estrategia_842(    df): return     df_estonia1[(vars_dict['VAR26'] >= 1.4035) & (vars_dict['VAR26'] <= 1.5691)].copy()
    def estrategia_843(    df): return     df_estonia1[(vars_dict['VAR12'] >= 0.2621) & (vars_dict['VAR12'] <= 0.31)].copy()
    def estrategia_844(    df): return     df_estonia1[(vars_dict['VAR70'] >= 0.9189) & (vars_dict['VAR70'] <= 1.9063)].copy()
    def estrategia_845(    df): return     df_estonia1[(vars_dict['VAR66'] >= -3.4064) & (vars_dict['VAR66'] <= -2.6792)].copy()
    def estrategia_846(    df): return     df_estonia1[(vars_dict['VAR10'] >= 0.8) & (vars_dict['VAR10'] <= 0.839)].copy()
    def estrategia_847(    df): return     df_estonia1[(vars_dict['VAR59'] >= 0.0269) & (vars_dict['VAR59'] <= 0.0433)].copy()
    def estrategia_848(    df): return     df_estonia1[(vars_dict['VAR61'] >= 0.6182) & (vars_dict['VAR61'] <= 0.6892)].copy()
    def estrategia_849(    df): return     df_estonia1[(vars_dict['VAR20'] >= 0.4057) & (vars_dict['VAR20'] <= 0.6267)].copy()
    def estrategia_850(    df): return     df_estonia1[(vars_dict['VAR14'] >= 0.4122) & (vars_dict['VAR14'] <= 0.5641)].copy()
    def estrategia_851(    df): return     df_estonia1[(vars_dict['VAR01'] >= 1.8205) & (vars_dict['VAR01'] <= 2.3765)].copy()
    def estrategia_852(    df): return     df_estonia1[(vars_dict['VAR71'] >= 0.8205) & (vars_dict['VAR71'] <= 1.3765)].copy()
    def estrategia_853(    df): return     df_estonia1[(vars_dict['VAR38'] >= 1.5543) & (vars_dict['VAR38'] <= 1.7431)].copy()
    def estrategia_854(    df): return     df_estonia1[(vars_dict['VAR21'] >= 0.0) & (vars_dict['VAR21'] <= 0.3065)].copy()
    def estrategia_855(    df): return     df_estonia1[(vars_dict['VAR37'] >= 1.3675) & (vars_dict['VAR37'] <= 1.5116)].copy()
    def estrategia_856(    df): return     df_estonia1[(vars_dict['VAR15'] >= 0.5224) & (vars_dict['VAR15'] <= 0.5379)].copy()
    def estrategia_857(    df): return     df_estonia1[(vars_dict['VAR58'] >= 0.1388) & (vars_dict['VAR58'] <= 0.1627)].copy()
    def estrategia_858(    df): return     df_estonia1[(vars_dict['VAR74'] >= 0.2353) & (vars_dict['VAR74'] <= 0.287)].copy()
    def estrategia_859(    df): return     df_estonia1[(vars_dict['VAR03'] >= 0.4208) & (vars_dict['VAR03'] <= 0.5493)].copy()
    def estrategia_860(    df): return     df_estonia1[(vars_dict['VAR18'] >= 0.4429) & (vars_dict['VAR18'] <= 0.4548)].copy()


    # Teste com Ligas "MEXICO 1"
    df_mexico1 =     df[    df['League'] == "MEXICO 1"].copy()
    def estrategia_861(    df): return     df_mexico1[(vars_dict['VAR21'] >= 0.5625) & (vars_dict['VAR21'] <= 0.5806)].copy()
    def estrategia_862(    df): return     df_mexico1[(vars_dict['VAR37'] >= 1.8333) & (vars_dict['VAR37'] <= 1.9634)].copy()
    def estrategia_863(    df): return     df_mexico1[(vars_dict['VAR67'] >= -1.7443) & (vars_dict['VAR67'] <= -0.5635)].copy()
    def estrategia_864(    df): return     df_mexico1[(vars_dict['VAR46'] >= 0.9214) & (vars_dict['VAR46'] <= 0.976)].copy()
    def estrategia_865(    df): return     df_mexico1[(vars_dict['VAR49'] >= 0.8144) & (vars_dict['VAR49'] <= 0.96)].copy()
    def estrategia_866(    df): return     df_mexico1[(vars_dict['VAR69'] >= -3.9041) & (vars_dict['VAR69'] <= -0.7957)].copy()
    def estrategia_867(    df): return     df_mexico1[(vars_dict['VAR19'] >= 0.6667) & (vars_dict['VAR19'] <= 0.7767)].copy()
    def estrategia_868(    df): return     df_mexico1[(vars_dict['VAR55'] >= 0.0466) & (vars_dict['VAR55'] <= 0.0762)].copy()
    def estrategia_869(    df): return     df_mexico1[(vars_dict['VAR71'] >= 0.1613) & (vars_dict['VAR71'] <= 0.2692)].copy()
    def estrategia_870(    df): return     df_mexico1[(vars_dict['VAR08'] >= 1.1093) & (vars_dict['VAR08'] <= 1.2353)].copy()
    def estrategia_871(    df): return     df_mexico1[(vars_dict['VAR65'] >= 1.542) & (vars_dict['VAR65'] <= 3.2065)].copy()
    def estrategia_872(    df): return     df_mexico1[(vars_dict['VAR63'] >= -1.9596) & (vars_dict['VAR63'] <= -0.5457)].copy()
    def estrategia_873(    df): return     df_mexico1[(vars_dict['VAR43'] >= 1.2575) & (vars_dict['VAR43'] <= 1.3778)].copy()
    def estrategia_874(    df): return     df_mexico1[(vars_dict['VAR32'] >= 1.6544) & (vars_dict['VAR32'] <= 1.7708)].copy()
    def estrategia_875(    df): return     df_mexico1[(vars_dict['VAR75'] >= 0.0305) & (vars_dict['VAR75'] <= 0.0543)].copy()
    def estrategia_876(    df): return     df_mexico1[(vars_dict['VAR20'] >= 0.629) & (vars_dict['VAR20'] <= 0.7589)].copy()
    def estrategia_877(    df): return     df_mexico1[(vars_dict['VAR58'] >= 0.0427) & (vars_dict['VAR58'] <= 0.0714)].copy()
    def estrategia_878(    df): return     df_mexico1[(vars_dict['VAR59'] >= 0.0233) & (vars_dict['VAR59'] <= 0.0439)].copy()
    def estrategia_879(    df): return     df_mexico1[(vars_dict['VAR01'] >= 1.0667) & (vars_dict['VAR01'] <= 1.2336)].copy()
    def estrategia_880(    df): return     df_mexico1[(vars_dict['VAR27'] >= 1.2782) & (vars_dict['VAR27'] <= 1.391)].copy()


    # Teste com Ligas "MEXICO 2"
    df_mexico2 =     df[    df['League'] == "MEXICO 2"].copy()
    def estrategia_881(    df): return     df_mexico2[(vars_dict['VAR73'] >= 0.2983) & (vars_dict['VAR73'] <= 0.4248)].copy()
    def estrategia_882(    df): return     df_mexico2[(vars_dict['VAR07'] >= 1.2654) & (vars_dict['VAR07'] <= 1.3874)].copy()
    def estrategia_883(    df): return     df_mexico2[(vars_dict['VAR15'] >= 0.4929) & (vars_dict['VAR15'] <= 0.5093)].copy()
    def estrategia_884(    df): return     df_mexico2[(vars_dict['VAR08'] >= 0.7208) & (vars_dict['VAR08'] <= 0.7902)].copy()
    def estrategia_885(    df): return     df_mexico2[(vars_dict['VAR18'] >= 0.3983) & (vars_dict['VAR18'] <= 0.4316)].copy()
    def estrategia_886(    df): return     df_mexico2[(vars_dict['VAR40'] >= 1.6368) & (vars_dict['VAR40'] <= 2.1111)].copy()
    def estrategia_887(    df): return     df_mexico2[(vars_dict['VAR65'] >= -5.144) & (vars_dict['VAR65'] <= -3.7041)].copy()
    def estrategia_888(    df): return     df_mexico2[(vars_dict['VAR28'] >= 1.4334) & (vars_dict['VAR28'] <= 1.5139)].copy()
    def estrategia_889(    df): return     df_mexico2[(vars_dict['VAR31'] >= 2.3546) & (vars_dict['VAR31'] <= 2.7046)].copy()
    def estrategia_890(    df): return     df_mexico2[(vars_dict['VAR36'] >= 1.5648) & (vars_dict['VAR36'] <= 1.8357)].copy()
    def estrategia_891(    df): return     df_mexico2[(vars_dict['VAR24'] >= 2.7381) & (vars_dict['VAR24'] <= 2.84)].copy()
    def estrategia_892(    df): return     df_mexico2[(vars_dict['VAR21'] >= 0.4196) & (vars_dict['VAR21'] <= 0.4655)].copy()
    def estrategia_893(    df): return     df_mexico2[(vars_dict['VAR17'] >= 1.1485) & (vars_dict['VAR17'] <= 1.3162)].copy()
    def estrategia_894(    df): return     df_mexico2[(vars_dict['VAR76'] >= 0.0641) & (vars_dict['VAR76'] <= 0.0814)].copy()
    def estrategia_895(    df): return     df_mexico2[(vars_dict['VAR41'] >= 1.396) & (vars_dict['VAR41'] <= 1.5076)].copy()
    def estrategia_896(    df): return     df_mexico2[(vars_dict['VAR27'] >= 1.5971) & (vars_dict['VAR27'] <= 1.6801)].copy()
    def estrategia_897(    df): return     df_mexico2[(vars_dict['VAR33'] >= 1.2847) & (vars_dict['VAR33'] <= 1.3786)].copy()
    def estrategia_898(    df): return     df_mexico2[(vars_dict['VAR60'] >= 0.0481) & (vars_dict['VAR60'] <= 0.0561)].copy()
    def estrategia_899(    df): return     df_mexico2[(vars_dict['VAR56'] >= 0.071) & (vars_dict['VAR56'] <= 0.0806)].copy()
    def estrategia_900(    df): return     df_mexico2[(vars_dict['VAR66'] >= 0.8565) & (vars_dict['VAR66'] <= 2.8747)].copy()


    # Teste com Ligas "NETHERLANDS 1"
    df_netherlands1 =     df[    df['League'] == "NETHERLANDS 1"].copy()
    def estrategia_901(    df): return     df_netherlands1[(vars_dict['VAR08'] >= 0.8316) & (vars_dict['VAR08'] <= 0.9015)].copy()
    def estrategia_902(    df): return     df_netherlands1[(vars_dict['VAR65'] >= -2.7902) & (vars_dict['VAR65'] <= -1.542)].copy()
    def estrategia_903(    df): return     df_netherlands1[(vars_dict['VAR57'] >= 0.4127) & (vars_dict['VAR57'] <= 0.7183)].copy()
    def estrategia_904(    df): return     df_netherlands1[(vars_dict['VAR73'] >= 1.2794) & (vars_dict['VAR73'] <= 4.3097)].copy()
    def estrategia_905(    df): return     df_netherlands1[(vars_dict['VAR07'] >= 2.2794) & (vars_dict['VAR07'] <= 5.3097)].copy()
    def estrategia_906(    df): return     df_netherlands1[(vars_dict['VAR04'] >= 0.8333) & (vars_dict['VAR04'] <= 0.9688)].copy()
    def estrategia_907(    df): return     df_netherlands1[(vars_dict['VAR06'] >= 1.0323) & (vars_dict['VAR06'] <= 1.2)].copy()
    def estrategia_908(    df): return     df_netherlands1[(vars_dict['VAR21'] >= 0.1113) & (vars_dict['VAR21'] <= 0.2796)].copy()
    def estrategia_909(    df): return     df_netherlands1[(vars_dict['VAR28'] >= 1.5789) & (vars_dict['VAR28'] <= 1.7278)].copy()
    def estrategia_910(    df): return     df_netherlands1[(vars_dict['VAR16'] >= 0.8534) & (vars_dict['VAR16'] <= 1.0)].copy()
    def estrategia_911(    df): return     df_netherlands1[(vars_dict['VAR64'] >= 0.2888) & (vars_dict['VAR64'] <= 1.7357)].copy()
    def estrategia_912(    df): return     df_netherlands1[(vars_dict['VAR70'] >= 0.3261) & (vars_dict['VAR70'] <= 0.5113)].copy()
    def estrategia_913(    df): return     df_netherlands1[(vars_dict['VAR29'] >= 1.8033) & (vars_dict['VAR29'] <= 1.9244)].copy()
    def estrategia_914(    df): return     df_netherlands1[(vars_dict['VAR11'] >= 0.4949) & (vars_dict['VAR11'] <= 0.6206)].copy()
    def estrategia_915(    df): return     df_netherlands1[(vars_dict['VAR48'] >= 0.9286) & (vars_dict['VAR48'] <= 0.9923)].copy()
    def estrategia_916(    df): return     df_netherlands1[(vars_dict['VAR68'] >= -1.5737) & (vars_dict['VAR68'] <= -0.1708)].copy()
    def estrategia_917(    df): return     df_netherlands1[(vars_dict['VAR12'] >= 0.076) & (vars_dict['VAR12'] <= 0.2122)].copy()
    def estrategia_918(    df): return     df_netherlands1[(vars_dict['VAR33'] >= 1.1843) & (vars_dict['VAR33'] <= 1.2693)].copy()
    def estrategia_919(    df): return     df_netherlands1[(vars_dict['VAR27'] >= 2.8283) & (vars_dict['VAR27'] <= 5.6075)].copy()
    def estrategia_920(    df): return     df_netherlands1[(vars_dict['VAR77'] >= 0.2775) & (vars_dict['VAR77'] <= 0.3634)].copy()


    # Teste com Ligas "NETHERLANDS 2"
    df_netherlands2 =     df[    df['League'] == "NETHERLANDS 2"].copy()
    def estrategia_921(    df): return     df_netherlands2[(vars_dict['VAR28'] >= 1.186) & (vars_dict['VAR28'] <= 1.2171)].copy()
    def estrategia_922(    df): return     df_netherlands2[(vars_dict['VAR34'] >= 1.7197) & (vars_dict['VAR34'] <= 1.88)].copy()
    def estrategia_923(    df): return     df_netherlands2[(vars_dict['VAR70'] >= 0.2667) & (vars_dict['VAR70'] <= 0.381)].copy()
    def estrategia_924(    df): return     df_netherlands2[(vars_dict['VAR14'] >= 1.5924) & (vars_dict['VAR14'] <= 1.9014)].copy()
    def estrategia_925(    df): return     df_netherlands2[(vars_dict['VAR37'] >= 1.7246) & (vars_dict['VAR37'] <= 1.8301)].copy()
    def estrategia_926(    df): return     df_netherlands2[(vars_dict['VAR65'] >= -4.9392) & (vars_dict['VAR65'] <= -3.2065)].copy()
    def estrategia_927(    df): return     df_netherlands2[(vars_dict['VAR08'] >= 0.72) & (vars_dict['VAR08'] <= 0.8095)].copy()
    def estrategia_928(    df): return     df_netherlands2[(vars_dict['VAR43'] >= 1.68) & (vars_dict['VAR43'] <= 1.76)].copy()
    def estrategia_929(    df): return     df_netherlands2[(vars_dict['VAR54'] >= 0.1014) & (vars_dict['VAR54'] <= 0.1536)].copy()
    def estrategia_930(    df): return     df_netherlands2[(vars_dict['VAR60'] >= 0.0549) & (vars_dict['VAR60'] <= 0.0785)].copy()
    def estrategia_931(    df): return     df_netherlands2[(vars_dict['VAR59'] >= 0.0575) & (vars_dict['VAR59'] <= 0.1056)].copy()
    def estrategia_932(    df): return     df_netherlands2[(vars_dict['VAR27'] >= 1.6667) & (vars_dict['VAR27'] <= 1.7829)].copy()
    def estrategia_933(    df): return     df_netherlands2[(vars_dict['VAR46'] >= 0.8667) & (vars_dict['VAR46'] <= 0.9236)].copy()
    def estrategia_934(    df): return     df_netherlands2[(vars_dict['VAR67'] >= -3.0211) & (vars_dict['VAR67'] <= -1.6449)].copy()
    def estrategia_935(    df): return     df_netherlands2[(vars_dict['VAR38'] >= 2.0513) & (vars_dict['VAR38'] <= 2.2222)].copy()
    def estrategia_936(    df): return     df_netherlands2[(vars_dict['VAR26'] >= 1.3462) & (vars_dict['VAR26'] <= 1.4)].copy()
    def estrategia_937(    df): return     df_netherlands2[(vars_dict['VAR01'] >= 1.0417) & (vars_dict['VAR01'] <= 1.2097)].copy()
    def estrategia_938(    df): return     df_netherlands2[(vars_dict['VAR24'] >= 3.8136) & (vars_dict['VAR24'] <= 4.2735)].copy()
    def estrategia_939(    df): return     df_netherlands2[(vars_dict['VAR71'] >= 0.2364) & (vars_dict['VAR71'] <= 0.4)].copy()
    def estrategia_940(    df): return     df_netherlands2[(vars_dict['VAR33'] >= 1.0929) & (vars_dict['VAR33'] <= 1.193)].copy()


    # Teste com Ligas "NORTHERN IRELAND 2"
    df_northernireland2 =     df[    df['League'] == "NORTHERN IRELAND 2"].copy()
    def estrategia_941(    df): return     df_northernireland2[(vars_dict['VAR21'] >= 0.5775) & (vars_dict['VAR21'] <= 0.5909)].copy()
    def estrategia_942(    df): return     df_northernireland2[(vars_dict['VAR26'] >= 1.4385) & (vars_dict['VAR26'] <= 1.4688)].copy()
    def estrategia_943(    df): return     df_northernireland2[(vars_dict['VAR45'] >= 1.176) & (vars_dict['VAR45'] <= 1.2692)].copy()
    def estrategia_944(    df): return     df_northernireland2[(vars_dict['VAR77'] >= 0.822) & (vars_dict['VAR77'] <= 3.5238)].copy()
    def estrategia_945(    df): return     df_northernireland2[(vars_dict['VAR12'] >= 0.3951) & (vars_dict['VAR12'] <= 0.4286)].copy()
    def estrategia_946(    df): return     df_northernireland2[(vars_dict['VAR60'] >= 0.1173) & (vars_dict['VAR60'] <= 0.1636)].copy()
    def estrategia_947(    df): return     df_northernireland2[(vars_dict['VAR39'] >= 0.2505) & (vars_dict['VAR39'] <= 0.75)].copy()
    def estrategia_948(    df): return     df_northernireland2[(vars_dict['VAR76'] >= 0.176) & (vars_dict['VAR76'] <= 0.2692)].copy()
    def estrategia_949(    df): return     df_northernireland2[(vars_dict['VAR48'] >= 0.7879) & (vars_dict['VAR48'] <= 0.8503)].copy()
    def estrategia_950(    df): return     df_northernireland2[(vars_dict['VAR68'] >= -4.6776) & (vars_dict['VAR68'] <= -3.3565)].copy()
    def estrategia_951(    df): return     df_northernireland2[(vars_dict['VAR71'] >= 0.3333) & (vars_dict['VAR71'] <= 0.5566)].copy()
    def estrategia_952(    df): return     df_northernireland2[(vars_dict['VAR29'] >= 1.5495) & (vars_dict['VAR29'] <= 1.584)].copy()
    def estrategia_953(    df): return     df_northernireland2[(vars_dict['VAR04'] >= 0.1889) & (vars_dict['VAR04'] <= 0.4211)].copy()
    def estrategia_954(    df): return     df_northernireland2[(vars_dict['VAR49'] >= 0.2211) & (vars_dict['VAR49'] <= 0.5535)].copy()
    def estrategia_955(    df): return     df_northernireland2[(vars_dict['VAR32'] >= 1.1333) & (vars_dict['VAR32'] <= 1.3793)].copy()
    def estrategia_956(    df): return     df_northernireland2[(vars_dict['VAR25'] >= 1.0818) & (vars_dict['VAR25'] <= 1.36)].copy()
    def estrategia_957(    df): return     df_northernireland2[(vars_dict['VAR69'] >= -20.3512) & (vars_dict['VAR69'] <= -10.4597)].copy()
    def estrategia_958(    df): return     df_northernireland2[(vars_dict['VAR36'] >= 1.5385) & (vars_dict['VAR36'] <= 1.6348)].copy()
    def estrategia_959(    df): return     df_northernireland2[(vars_dict['VAR27'] >= 1.72) & (vars_dict['VAR27'] <= 1.7886)].copy()
    def estrategia_960(    df): return     df_northernireland2[(vars_dict['VAR61'] >= 0.0) & (vars_dict['VAR61'] <= 0.063)].copy()


    # Teste com Ligas "NORWAY 1"
    df_norway1 =     df[    df['League'] == "NORWAY 1"].copy()
    def estrategia_961(    df): return     df_norway1[(vars_dict['VAR74'] >= 0.5556) & (vars_dict['VAR74'] <= 0.8264)].copy()
    def estrategia_962(    df): return     df_norway1[(vars_dict['VAR58'] >= 0.2334) & (vars_dict['VAR58'] <= 0.3142)].copy()
    def estrategia_963(    df): return     df_norway1[(vars_dict['VAR09'] >= 1.5556) & (vars_dict['VAR09'] <= 1.8264)].copy()
    def estrategia_964(    df): return     df_norway1[(vars_dict['VAR38'] >= 2.1895) & (vars_dict['VAR38'] <= 2.3897)].copy()
    def estrategia_965(    df): return     df_norway1[(vars_dict['VAR08'] >= 0.6681) & (vars_dict['VAR08'] <= 0.75)].copy()
    def estrategia_966(    df): return     df_norway1[(vars_dict['VAR65'] >= -6.0341) & (vars_dict['VAR65'] <= -4.3323)].copy()
    def estrategia_967(    df): return     df_norway1[(vars_dict['VAR47'] >= 0.9581) & (vars_dict['VAR47'] <= 1.1544)].copy()
    def estrategia_968(    df): return     df_norway1[(vars_dict['VAR39'] >= 1.465) & (vars_dict['VAR39'] <= 1.875)].copy()
    def estrategia_969(    df): return     df_norway1[(vars_dict['VAR31'] >= 2.3512) & (vars_dict['VAR31'] <= 2.5654)].copy()
    def estrategia_970(    df): return     df_norway1[(vars_dict['VAR69'] >= -2.7999) & (vars_dict['VAR69'] <= 0.8332)].copy()
    def estrategia_971(    df): return     df_norway1[(vars_dict['VAR62'] >= -0.662) & (vars_dict['VAR62'] <= 2.6138)].copy()
    def estrategia_972(    df): return     df_norway1[(vars_dict['VAR02'] >= 0.7872) & (vars_dict['VAR02'] <= 1.0627)].copy()
    def estrategia_973(    df): return     df_norway1[(vars_dict['VAR05'] >= 0.9411) & (vars_dict['VAR05'] <= 1.2703)].copy()
    def estrategia_974(    df): return     df_norway1[(vars_dict['VAR12'] >= 0.285) & (vars_dict['VAR12'] <= 0.3295)].copy()
    def estrategia_975(    df): return     df_norway1[(vars_dict['VAR10'] >= 0.5475) & (vars_dict['VAR10'] <= 0.6429)].copy()
    def estrategia_976(    df): return     df_norway1[(vars_dict['VAR66'] >= -8.9286) & (vars_dict['VAR66'] <= -6.6571)].copy()
    def estrategia_977(    df): return     df_norway1[(vars_dict['VAR44'] >= 1.0561) & (vars_dict['VAR44'] <= 1.1628)].copy()
    def estrategia_978(    df): return     df_norway1[(vars_dict['VAR25'] >= 1.7829) & (vars_dict['VAR25'] <= 2.0785)].copy()
    def estrategia_979(    df): return     df_norway1[(vars_dict['VAR60'] >= 0.0248) & (vars_dict['VAR60'] <= 0.0339)].copy()
    def estrategia_980(    df): return     df_norway1[(vars_dict['VAR57'] >= 0.2114) & (vars_dict['VAR57'] <= 0.2369)].copy()


    # Teste com Ligas "NORWAY 2"
    df_norway2 =     df[   df['League'] == "NORWAY 2"].copy()
    def estrategia_981(    df): return     df_norway2[(vars_dict['VAR20'] >= 0.7019) & (vars_dict['VAR20'] <= 0.8264)].copy()
    def estrategia_982(    df): return     df_norway2[(vars_dict['VAR29'] >= 1.2857) & (vars_dict['VAR29'] <= 1.5832)].copy()
    def estrategia_983(    df): return     df_norway2[(vars_dict['VAR58'] >= 0.0) & (vars_dict['VAR58'] <= 0.078)].copy()
    def estrategia_984(    df): return     df_norway2[(vars_dict['VAR18'] >= 0.4765) & (vars_dict['VAR18'] <= 0.6632)].copy()
    def estrategia_985(    df): return     df_norway2[(vars_dict['VAR26'] >= 1.4185) & (vars_dict['VAR26'] <= 1.76)].copy()
    def estrategia_986(    df): return     df_norway2[(vars_dict['VAR46'] >= 0.9191) & (vars_dict['VAR46'] <= 0.9547)].copy()
    def estrategia_987(    df): return     df_norway2[(vars_dict['VAR67'] >= -1.853) & (vars_dict['VAR67'] <= -1.0181)].copy()
    def estrategia_988(    df): return     df_norway2[(vars_dict['VAR56'] >= 0.0369) & (vars_dict['VAR56'] <= 0.0504)].copy()
    def estrategia_989(    df): return     df_norway2[(vars_dict['VAR09'] >= 0.865) & (vars_dict['VAR09'] <= 1.1561)].copy()
    def estrategia_990(    df): return     df_norway2[(vars_dict['VAR74'] >= 0.0) & (vars_dict['VAR74'] <= 0.1561)].copy()
    def estrategia_991(    df): return     df_norway2[(vars_dict['VAR24'] >= 2.0571) & (vars_dict['VAR24'] <= 2.6154)].copy()
    def estrategia_992(    df): return     df_norway2[(vars_dict['VAR54'] >= 0.1923) & (vars_dict['VAR54'] <= 0.2464)].copy()
    def estrategia_993(    df): return     df_norway2[(vars_dict['VAR40'] >= 1.3934) & (vars_dict['VAR40'] <= 1.8803)].copy()
    def estrategia_994(    df): return     df_norway2[(vars_dict['VAR71'] >= 0.1539) & (vars_dict['VAR71'] <= 0.2851)].copy()
    def estrategia_995(    df): return     df_norway2[(vars_dict['VAR07'] >= 0.72) & (vars_dict['VAR07'] <= 1.1111)].copy()
    def estrategia_996(    df): return     df_norway2[(vars_dict['VAR38'] >= 2.0809) & (vars_dict['VAR38'] <= 2.2156)].copy()
    def estrategia_997(    df): return     df_norway2[(vars_dict['VAR66'] >= -2.2344) & (vars_dict['VAR66'] <= 2.2344)].copy()
    def estrategia_998(    df): return     df_norway2[(vars_dict['VAR10'] >= 0.865) & (vars_dict['VAR10'] <= 1.1561)].copy()
    def estrategia_999(    df): return     df_norway2[(vars_dict['VAR33'] >= 1.2684) & (vars_dict['VAR33'] <= 1.6372)].copy()
    def estrategia_1000(   df): return     df_norway2[(vars_dict['VAR69'] >= -4.9678) & (vars_dict['VAR69'] <= -2.2146)].copy()


    # Teste com Ligas "PARAGUAY 1"
    df_paraguay1 =     df[    df['League'] == "PARAGUAY 1"].copy()
    def estrategia_1001(    df): return     df_paraguay1[(vars_dict['VAR15'] >= 0.5276) & (vars_dict['VAR15'] <= 0.5371)].copy()
    def estrategia_1002(    df): return     df_paraguay1[(vars_dict['VAR18'] >= 0.6154) & (vars_dict['VAR18'] <= 0.6367)].copy()
    def estrategia_1003(    df): return     df_paraguay1[(vars_dict['VAR72'] >= 0.3817) & (vars_dict['VAR72'] <= 0.4706)].copy()
    def estrategia_1004(    df): return     df_paraguay1[(vars_dict['VAR28'] >= 1.4706) & (vars_dict['VAR28'] <= 1.5038)].copy()
    def estrategia_1005(    df): return     df_paraguay1[(vars_dict['VAR24'] >= 2.2794) & (vars_dict['VAR24'] <= 2.3529)].copy()
    def estrategia_1006(    df): return     df_paraguay1[(vars_dict['VAR29'] >= 1.2556) & (vars_dict['VAR29'] <= 1.2846)].copy()
    def estrategia_1007(    df): return     df_paraguay1[(vars_dict['VAR11'] >= 1.0217) & (vars_dict['VAR11'] <= 1.1231)].copy()
    def estrategia_1008(    df): return     df_paraguay1[(vars_dict['VAR21'] >= 0.5717) & (vars_dict['VAR21'] <= 0.5877)].copy()
    def estrategia_1009(    df): return     df_paraguay1[(vars_dict['VAR48'] >= 0.6885) & (vars_dict['VAR48'] <= 0.8144)].copy()
    def estrategia_1010(    df): return     df_paraguay1[(vars_dict['VAR68'] >= -6.7638) & (vars_dict['VAR68'] <= -3.9041)].copy()
    def estrategia_1011(    df): return     df_paraguay1[(vars_dict['VAR34'] >= 0.928) & (vars_dict['VAR34'] <= 1.0)].copy()
    def estrategia_1012(    df): return     df_paraguay1[(vars_dict['VAR76'] >= 0.2279) & (vars_dict['VAR76'] <= 0.4527)].copy()
    def estrategia_1013(    df): return     df_paraguay1[(vars_dict['VAR60'] >= 0.1365) & (vars_dict['VAR60'] <= 0.2372)].copy()
    def estrategia_1014(    df): return     df_paraguay1[(vars_dict['VAR45'] >= 1.2279) & (vars_dict['VAR45'] <= 1.4527)].copy()
    def estrategia_1015(    df): return     df_paraguay1[(vars_dict['VAR27'] >= 1.1912) & (vars_dict['VAR27'] <= 1.2132)].copy()
    def estrategia_1016(    df): return     df_paraguay1[(vars_dict['VAR73'] >= 0.1905) & (vars_dict['VAR73'] <= 0.2233)].copy()
    def estrategia_1017(    df): return     df_paraguay1[(vars_dict['VAR57'] >= 0.112) & (vars_dict['VAR57'] <= 0.1337)].copy()
    def estrategia_1018(    df): return     df_paraguay1[(vars_dict['VAR26'] >= 1.6541) & (vars_dict['VAR26'] <= 1.6912)].copy()
    def estrategia_1019(    df): return     df_paraguay1[(vars_dict['VAR36'] >= 1.0) & (vars_dict['VAR36'] <= 1.0915)].copy()
    def estrategia_1020(    df): return     df_paraguay1[(vars_dict['VAR04'] >= 0.5449) & (vars_dict['VAR04'] <= 0.697)].copy()


    # Teste com Ligas "PERU 1"
    df_peru1 =     df[    df['League'] == "PERU 1"].copy()
    def estrategia_1021(    df): return     df_peru1[(vars_dict['VAR70'] >= 0.1483) & (vars_dict['VAR70'] <= 0.3551)].copy()
    def estrategia_1022(    df): return     df_peru1[(vars_dict['VAR20'] >= 0.7194) & (vars_dict['VAR20'] <= 0.8315)].copy()
    def estrategia_1023(    df): return     df_peru1[(vars_dict['VAR17'] >= 0.678) & (vars_dict['VAR17'] <= 0.7814)].copy()
    def estrategia_1024(    df): return     df_peru1[(vars_dict['VAR43'] >= 1.0944) & (vars_dict['VAR43'] <= 1.271)].copy()
    def estrategia_1025(    df): return     df_peru1[(vars_dict['VAR14'] >= 0.6657) & (vars_dict['VAR14'] <= 0.7689)].copy()
    def estrategia_1026(    df): return     df_peru1[(vars_dict['VAR07'] >= 0.9495) & (vars_dict['VAR07'] <= 1.0532)].copy()
    def estrategia_1027(    df): return     df_peru1[(vars_dict['VAR54'] >= 0.056) & (vars_dict['VAR54'] <= 0.1281)].copy()
    def estrategia_1028(    df): return     df_peru1[(vars_dict['VAR41'] >= 1.6356) & (vars_dict['VAR41'] <= 1.7807)].copy()
    def estrategia_1029(    df): return     df_peru1[(vars_dict['VAR47'] >= 0.36) & (vars_dict['VAR47'] <= 0.4612)].copy()
    def estrategia_1030(    df): return     df_peru1[(vars_dict['VAR46'] >= 0.7688) & (vars_dict['VAR46'] <= 0.8383)].copy()
    def estrategia_1031(    df): return     df_peru1[(vars_dict['VAR74'] >= 0.0) & (vars_dict['VAR74'] <= 0.0576)].copy()
    def estrategia_1032(    df): return     df_peru1[(vars_dict['VAR58'] >= 0.0) & (vars_dict['VAR58'] <= 0.032)].copy()
    def estrategia_1033(    df): return     df_peru1[(vars_dict['VAR66'] >= 0.0) & (vars_dict['VAR66'] <= 0.9165)].copy()
    def estrategia_1034(    df): return     df_peru1[(vars_dict['VAR10'] >= 1.0) & (vars_dict['VAR10'] <= 1.0611)].copy()
    def estrategia_1035(    df): return     df_peru1[(vars_dict['VAR09'] >= 1.0) & (vars_dict['VAR09'] <= 1.0611)].copy()
    def estrategia_1036(    df): return     df_peru1[(vars_dict['VAR28'] >= 1.4286) & (vars_dict['VAR28'] <= 1.4806)].copy()
    def estrategia_1037(    df): return     df_peru1[(vars_dict['VAR60'] >= 0.021) & (vars_dict['VAR60'] <= 0.035)].copy()
    def estrategia_1038(    df): return     df_peru1[(vars_dict['VAR27'] >= 1.56) & (vars_dict['VAR27'] <= 1.6498)].copy()
    def estrategia_1039(    df): return     df_peru1[(vars_dict['VAR45'] >= 1.0226) & (vars_dict['VAR45'] <= 1.1029)].copy()
    def estrategia_1040(    df): return     df_peru1[(vars_dict['VAR55'] >= 0.4167) & (vars_dict['VAR55'] <= 0.5196)].copy()


    # Teste com Ligas "POLAND 1"
    df_poland1 =     df[    df['League'] == "POLAND 1"].copy()
    def estrategia_1041(    df): return     df_poland1[(vars_dict['VAR24'] >= 2.8682) & (vars_dict['VAR24'] <= 3.0738)].copy()
    def estrategia_1042(    df): return     df_poland1[(vars_dict['VAR27'] >= 1.418) & (vars_dict['VAR27'] <= 1.4887)].copy()
    def estrategia_1043(    df): return     df_poland1[(vars_dict['VAR74'] >= 0.358) & (vars_dict['VAR74'] <= 0.8264)].copy()
    def estrategia_1044(    df): return     df_poland1[(vars_dict['VAR71'] >= 0.28) & (vars_dict['VAR71'] <= 0.3878)].copy()
    def estrategia_1045(    df): return     df_poland1[(vars_dict['VAR09'] >= 1.358) & (vars_dict['VAR09'] <= 1.8264)].copy()
    def estrategia_1046(    df): return     df_poland1[(vars_dict['VAR20'] >= 1.2782) & (vars_dict['VAR20'] <= 1.6129)].copy()
    def estrategia_1047(    df): return     df_poland1[(vars_dict['VAR17'] >= 0.5786) & (vars_dict['VAR17'] <= 0.6681)].copy()
    def estrategia_1048(    df): return     df_poland1[(vars_dict['VAR61'] >= 0.3823) & (vars_dict['VAR61'] <= 0.457)].copy()
    def estrategia_1049(    df): return     df_poland1[(vars_dict['VAR43'] >= 1.76) & (vars_dict['VAR43'] <= 2.1368)].copy()
    def estrategia_1050(    df): return     df_poland1[(vars_dict['VAR41'] >= 1.877) & (vars_dict['VAR41'] <= 2.6182)].copy()
    def estrategia_1051(    df): return     df_poland1[(vars_dict['VAR56'] >= 0.1333) & (vars_dict['VAR56'] <= 0.218)].copy()
    def estrategia_1052(    df): return     df_poland1[(vars_dict['VAR72'] >= 0.512) & (vars_dict['VAR72'] <= 1.0785)].copy()
    def estrategia_1053(    df): return     df_poland1[(vars_dict['VAR60'] >= 0.1216) & (vars_dict['VAR60'] <= 0.2137)].copy()
    def estrategia_1054(    df): return     df_poland1[(vars_dict['VAR33'] >= 1.3603) & (vars_dict['VAR33'] <= 1.4815)].copy()
    def estrategia_1055(    df): return     df_poland1[(vars_dict['VAR42'] >= 1.1929) & (vars_dict['VAR42'] <= 1.2654)].copy()
    def estrategia_1056(    df): return     df_poland1[(vars_dict['VAR07'] >= 1.4375) & (vars_dict['VAR07'] <= 2.0571)].copy()
    def estrategia_1057(    df): return     df_poland1[(vars_dict['VAR40'] >= 1.36) & (vars_dict['VAR40'] <= 1.4191)].copy()
    def estrategia_1058(    df): return     df_poland1[(vars_dict['VAR03'] >= 1.0667) & (vars_dict['VAR03'] <= 1.6667)].copy()
    def estrategia_1059(    df): return     df_poland1[(vars_dict['VAR26'] >= 1.6356) & (vars_dict['VAR26'] <= 1.7279)].copy()
    def estrategia_1060(    df): return     df_poland1[(vars_dict['VAR58'] >= 0.1627) & (vars_dict['VAR58'] <= 0.1925)].copy()


    # Teste com Ligas "POLAND 2"
    df_poland2 =     df[    df['League'] == "POLAND 2"].copy()
    def estrategia_1061(    df): return     df_poland2[(vars_dict['VAR20'] >= 0.8511) & (vars_dict['VAR20'] <= 0.952)].copy()
    def estrategia_1062(    df): return     df_poland2[(vars_dict['VAR36'] >= 1.0471) & (vars_dict['VAR36'] <= 1.1111)].copy()
    def estrategia_1063(    df): return     df_poland2[(vars_dict['VAR35'] >= 1.0588) & (vars_dict['VAR35'] <= 1.1133)].copy()
    def estrategia_1064(    df): return     df_poland2[(vars_dict['VAR33'] >= 1.1561) & (vars_dict['VAR33'] <= 1.2556)].copy()
    def estrategia_1065(    df): return     df_poland2[(vars_dict['VAR11'] >= 0.9592) & (vars_dict['VAR11'] <= 1.0273)].copy()
    def estrategia_1066(    df): return     df_poland2[(vars_dict['VAR18'] >= 0.5538) & (vars_dict['VAR18'] <= 0.5719)].copy()
    def estrategia_1067(    df): return     df_poland2[(vars_dict['VAR13'] >= 0.6129) & (vars_dict['VAR13'] <= 0.6828)].copy()
    def estrategia_1068(    df): return     df_poland2[(vars_dict['VAR14'] >= 0.8) & (vars_dict['VAR14'] <= 0.8889)].copy()
    def estrategia_1069(    df): return     df_poland2[(vars_dict['VAR54'] >= 0.0718) & (vars_dict['VAR54'] <= 0.1314)].copy()
    def estrategia_1070(    df): return     df_poland2[(vars_dict['VAR30'] >= 1.4706) & (vars_dict['VAR30'] <= 1.6667)].copy()
    def estrategia_1071(    df): return     df_poland2[(vars_dict['VAR73'] >= 0.2023) & (vars_dict['VAR73'] <= 0.28)].copy()
    def estrategia_1072(    df): return     df_poland2[(vars_dict['VAR42'] >= 1.3643) & (vars_dict['VAR42'] <= 1.4361)].copy()
    def estrategia_1073(    df): return     df_poland2[(vars_dict['VAR26'] >= 1.3971) & (vars_dict['VAR26'] <= 1.4344)].copy()
    def estrategia_1074(    df): return     df_poland2[(vars_dict['VAR61'] >= 0.0476) & (vars_dict['VAR61'] <= 0.0686)].copy()
    def estrategia_1075(    df): return     df_poland2[(vars_dict['VAR15'] >= 0.5594) & (vars_dict['VAR15'] <= 0.5735)].copy()
    def estrategia_1076(    df): return     df_poland2[(vars_dict['VAR05'] >= 0.7759) & (vars_dict['VAR05'] <= 0.9273)].copy()
    def estrategia_1077(    df): return     df_poland2[(vars_dict['VAR62'] >= -2.8515) & (vars_dict['VAR62'] <= -0.817)].copy()
    def estrategia_1078(    df): return     df_poland2[(vars_dict['VAR37'] >= 1.6544) & (vars_dict['VAR37'] <= 1.7333)].copy()
    def estrategia_1079(    df): return     df_poland2[(vars_dict['VAR07'] >= 0.8317) & (vars_dict['VAR07'] <= 0.8939)].copy()
    def estrategia_1080(    df): return     df_poland2[(vars_dict['VAR40'] >= 1.531) & (vars_dict['VAR40'] <= 1.5891)].copy()


    # Teste com Ligas "PORTUGAL 1"
    df_portugal1 =     df[    df['League'] == "PORTUGAL 1"].copy()
    def estrategia_1081(    df): return     df_portugal1[(vars_dict['VAR46'] >= 1.0685) & (vars_dict['VAR46'] <= 1.1316)].copy()
    def estrategia_1082(    df): return     df_portugal1[(vars_dict['VAR67'] >= 1.658) & (vars_dict['VAR67'] <= 2.9195)].copy()
    def estrategia_1083(    df): return     df_portugal1[(vars_dict['VAR44'] >= 0.8837) & (vars_dict['VAR44'] <= 0.9359)].copy()
    def estrategia_1084(    df): return     df_portugal1[(vars_dict['VAR75'] >= 0.075) & (vars_dict['VAR75'] <= 0.1043)].copy()
    def estrategia_1085(    df): return     df_portugal1[(vars_dict['VAR63'] >= 1.9385) & (vars_dict['VAR63'] <= 3.2423)].copy()
    def estrategia_1086(    df): return     df_portugal1[(vars_dict['VAR27'] >= 1.5385) & (vars_dict['VAR27'] <= 1.6799)].copy()
    def estrategia_1087(    df): return     df_portugal1[(vars_dict['VAR72'] >= 0.5732) & (vars_dict['VAR72'] <= 0.7154)].copy()
    def estrategia_1088(    df): return     df_portugal1[(vars_dict['VAR24'] >= 3.4426) & (vars_dict['VAR24'] <= 4.5547)].copy()
    def estrategia_1089(    df): return     df_portugal1[(vars_dict['VAR57'] >= 0.0973) & (vars_dict['VAR57'] <= 0.1337)].copy()
    def estrategia_1090(    df): return     df_portugal1[(vars_dict['VAR77'] >= 0.8127) & (vars_dict['VAR77'] <= 1.4741)].copy()
    def estrategia_1091(    df): return     df_portugal1[(vars_dict['VAR29'] >= 1.3462) & (vars_dict['VAR29'] <= 1.3927)].copy()
    def estrategia_1092(    df): return     df_portugal1[(vars_dict['VAR18'] >= 0.4418) & (vars_dict['VAR18'] <= 0.4897)].copy()
    def estrategia_1093(    df): return     df_portugal1[(vars_dict['VAR31'] >= 2.7071) & (vars_dict['VAR31'] <= 4.0541)].copy()
    def estrategia_1094(    df): return     df_portugal1[(vars_dict['VAR16'] >= 0.879) & (vars_dict['VAR16'] <= 1.4572)].copy()
    def estrategia_1095(    df): return     df_portugal1[(vars_dict['VAR73'] >= 0.0) & (vars_dict['VAR73'] <= 0.0811)].copy()
    def estrategia_1096(    df): return     df_portugal1[(vars_dict['VAR59'] >= 0.2504) & (vars_dict['VAR59'] <= 0.3652)].copy()
    def estrategia_1097(    df): return     df_portugal1[(vars_dict['VAR36'] >= 1.3235) & (vars_dict['VAR36'] <= 1.4754)].copy()
    def estrategia_1098(    df): return     df_portugal1[(vars_dict['VAR70'] >= 0.6634) & (vars_dict['VAR70'] <= 0.82)].copy()
    def estrategia_1099(    df): return     df_portugal1[(vars_dict['VAR04'] >= 0.3233) & (vars_dict['VAR04'] <= 0.5868)].copy()
    def estrategia_1100(    df): return     df_portugal1[(vars_dict['VAR40'] >= 0.6488) & (vars_dict['VAR40'] <= 1.1458)].copy()


    # Teste com Ligas "PORTUGAL 2"
    df_portugal2 =     df[    df['League'] == "PORTUGAL 2"].copy()
    def estrategia_1101(    df): return     df_portugal2[(vars_dict['VAR41'] >= 1.5826) & (vars_dict['VAR41'] <= 2.5946)].copy()
    def estrategia_1102(    df): return     df_portugal2[(vars_dict['VAR60'] >= 0.0609) & (vars_dict['VAR60'] <= 0.0782)].copy()
    def estrategia_1103(    df): return     df_portugal2[(vars_dict['VAR33'] >= 0.4308) & (vars_dict['VAR33'] <= 0.9178)].copy()
    def estrategia_1104(    df): return     df_portugal2[(vars_dict['VAR18'] >= 0.4885) & (vars_dict['VAR18'] <= 0.5202)].copy()
    def estrategia_1105(    df): return     df_portugal2[(vars_dict['VAR14'] >= 1.1224) & (vars_dict['VAR14'] <= 2.2154)].copy()
    def estrategia_1106(    df): return     df_portugal2[(vars_dict['VAR06'] >= 1.2767) & (vars_dict['VAR06'] <= 1.4415)].copy()
    def estrategia_1107(    df): return     df_portugal2[(vars_dict['VAR04'] >= 0.6937) & (vars_dict['VAR04'] <= 0.7833)].copy()
    def estrategia_1108(    df): return     df_portugal2[(vars_dict['VAR20'] >= 1.0778) & (vars_dict['VAR20'] <= 1.6528)].copy()
    def estrategia_1109(    df): return     df_portugal2[(vars_dict['VAR46'] >= 0.7432) & (vars_dict['VAR46'] <= 0.7964)].copy()
    def estrategia_1110(    df): return     df_portugal2[(vars_dict['VAR43'] >= 1.5508) & (vars_dict['VAR43'] <= 2.1062)].copy()
    def estrategia_1111(    df): return     df_portugal2[(vars_dict['VAR27'] >= 1.4574) & (vars_dict['VAR27'] <= 1.5571)].copy()
    def estrategia_1112(    df): return     df_portugal2[(vars_dict['VAR45'] >= 1.072) & (vars_dict['VAR45'] <= 1.125)].copy()
    def estrategia_1113(    df): return     df_portugal2[(vars_dict['VAR72'] >= 0.2586) & (vars_dict['VAR72'] <= 0.3209)].copy()
    def estrategia_1114(    df): return     df_portugal2[(vars_dict['VAR55'] >= 0.201) & (vars_dict['VAR55'] <= 0.2523)].copy()
    def estrategia_1115(    df): return     df_portugal2[(vars_dict['VAR67'] >= -5.4753) & (vars_dict['VAR67'] <= -4.3768)].copy()
    def estrategia_1116(    df): return     df_portugal2[(vars_dict['VAR07'] >= 0.9495) & (vars_dict['VAR07'] <= 1.0811)].copy()
    def estrategia_1117(    df): return     df_portugal2[(vars_dict['VAR35'] >= 0.5138) & (vars_dict['VAR35'] <= 0.9104)].copy()
    def estrategia_1118(    df): return     df_portugal2[(vars_dict['VAR64'] >= 2.4937) & (vars_dict['VAR64'] <= 3.8706)].copy()
    def estrategia_1119(    df): return     df_portugal2[(vars_dict['VAR37'] >= 1.5) & (vars_dict['VAR37'] <= 1.5504)].copy()
    def estrategia_1120(    df): return     df_portugal2[(vars_dict['VAR73'] >= 0.0) & (vars_dict['VAR73'] <= 0.051)].copy()


    # Teste com Ligas "ROMANIA 1"
    df_romania1 =     df[    df['League'] == "ROMANIA 1"].copy()
    def estrategia_1121(    df): return     df_romania1[(vars_dict['VAR77'] >= 0.0667) & (vars_dict['VAR77'] <= 0.125)].copy()
    def estrategia_1122(    df): return     df_romania1[(vars_dict['VAR19'] >= 0.6536) & (vars_dict['VAR19'] <= 0.7074)].copy()
    def estrategia_1123(    df): return     df_romania1[(vars_dict['VAR41'] >= 1.1111) & (vars_dict['VAR41'] <= 1.1708)].copy()
    def estrategia_1124(    df): return     df_romania1[(vars_dict['VAR23'] >= 1.416) & (vars_dict['VAR23'] <= 1.5038)].copy()
    def estrategia_1125(    df): return     df_romania1[(vars_dict['VAR61'] >= 0.0817) & (vars_dict['VAR61'] <= 0.1361)].copy()
    def estrategia_1126(    df): return     df_romania1[(vars_dict['VAR27'] >= 1.3235) & (vars_dict['VAR27'] <= 1.4342)].copy()
    def estrategia_1127(    df): return     df_romania1[(vars_dict['VAR24'] >= 2.6154) & (vars_dict['VAR24'] <= 2.7132)].copy()
    def estrategia_1128(    df): return     df_romania1[(vars_dict['VAR14'] >= 0.6) & (vars_dict['VAR14'] <= 0.6821)].copy()
    def estrategia_1129(    df): return     df_romania1[(vars_dict['VAR21'] >= 0.5625) & (vars_dict['VAR21'] <= 0.5767)].copy()
    def estrategia_1130(    df): return     df_romania1[(vars_dict['VAR76'] >= 0.1543) & (vars_dict['VAR76'] <= 0.3235)].copy()
    def estrategia_1131(    df): return     df_romania1[(vars_dict['VAR13'] >= 0.759) & (vars_dict['VAR13'] <= 0.8682)].copy()
    def estrategia_1132(    df): return     df_romania1[(vars_dict['VAR54'] >= 0.0976) & (vars_dict['VAR54'] <= 0.1423)].copy()
    def estrategia_1133(    df): return     df_romania1[(vars_dict['VAR29'] >= 1.3419) & (vars_dict['VAR29'] <= 1.3534)].copy()
    def estrategia_1134(    df): return     df_romania1[(vars_dict['VAR38'] >= 1.8325) & (vars_dict['VAR38'] <= 1.9657)].copy()
    def estrategia_1135(    df): return     df_romania1[(vars_dict['VAR12'] >= 0.7097) & (vars_dict['VAR12'] <= 0.7581)].copy()
    def estrategia_1136(    df): return     df_romania1[(vars_dict['VAR55'] >= 0.0443) & (vars_dict['VAR55'] <= 0.0656)].copy()
    def estrategia_1137(    df): return     df_romania1[(vars_dict['VAR33'] >= 1.3889) & (vars_dict['VAR33'] <= 1.4791)].copy()
    def estrategia_1138(    df): return     df_romania1[(vars_dict['VAR31'] >= 1.813) & (vars_dict['VAR31'] <= 1.9)].copy()
    def estrategia_1139(    df): return     df_romania1[(vars_dict['VAR69'] >= 2.3392) & (vars_dict['VAR69'] <= 4.3768)].copy()
    def estrategia_1140(    df): return     df_romania1[(vars_dict['VAR49'] >= 1.125) & (vars_dict['VAR49'] <= 1.2556)].copy()


    # Teste com Ligas "ROMANIA 2"
    df_romania2 =     df[    df['League'] == "ROMANIA 2"].copy()
    def estrategia_1141(    df): return     df_romania2[(vars_dict['VAR11'] >= 0.9107) & (vars_dict['VAR11'] <= 1.0)].copy()
    def estrategia_1142(    df): return     df_romania2[(vars_dict['VAR27'] >= 1.1628) & (vars_dict['VAR27'] <= 1.2018)].copy()
    def estrategia_1143(    df): return     df_romania2[(vars_dict['VAR73'] >= 0.3024) & (vars_dict['VAR73'] <= 0.3332)].copy()
    def estrategia_1144(    df): return     df_romania2[(vars_dict['VAR21'] >= 0.4563) & (vars_dict['VAR21'] <= 0.4923)].copy()
    def estrategia_1145(    df): return     df_romania2[(vars_dict['VAR34'] >= 0.9578) & (vars_dict['VAR34'] <= 1.0204)].copy()
    def estrategia_1146(    df): return     df_romania2[(vars_dict['VAR24'] >= 2.2881) & (vars_dict['VAR24'] <= 2.3784)].copy()
    def estrategia_1147(    df): return     df_romania2[(vars_dict['VAR72'] >= 0.4697) & (vars_dict['VAR72'] <= 0.6052)].copy()
    def estrategia_1148(    df): return     df_romania2[(vars_dict['VAR06'] >= 0.8985) & (vars_dict['VAR06'] <= 1.0156)].copy()
    def estrategia_1149(    df): return     df_romania2[(vars_dict['VAR41'] >= 1.1111) & (vars_dict['VAR41'] <= 1.1739)].copy()
    def estrategia_1150(    df): return     df_romania2[(vars_dict['VAR19'] >= 0.3118) & (vars_dict['VAR19'] <= 0.3853)].copy()
    def estrategia_1151(    df): return     df_romania2[(vars_dict['VAR75'] >= 0.0847) & (vars_dict['VAR75'] <= 0.1414)].copy()
    def estrategia_1152(    df): return     df_romania2[(vars_dict['VAR64'] >= -0.9384) & (vars_dict['VAR64'] <= 0.1377)].copy()
    def estrategia_1153(    df): return     df_romania2[(vars_dict['VAR12'] >= 0.7541) & (vars_dict['VAR12'] <= 0.7931)].copy()
    def estrategia_1154(    df): return     df_romania2[(vars_dict['VAR65'] >= 6.0048) & (vars_dict['VAR65'] <= 7.125)].copy()
    def estrategia_1155(    df): return     df_romania2[(vars_dict['VAR08'] >= 1.4839) & (vars_dict['VAR08'] <= 1.6)].copy()
    def estrategia_1156(    df): return     df_romania2[(vars_dict['VAR32'] >= 1.914) & (vars_dict['VAR32'] <= 2.0303)].copy()
    def estrategia_1157(    df): return     df_romania2[(vars_dict['VAR18'] >= 0.6349) & (vars_dict['VAR18'] <= 0.6557)].copy()
    def estrategia_1158(    df): return     df_romania2[(vars_dict['VAR26'] >= 1.7558) & (vars_dict['VAR26'] <= 1.7901)].copy()
    def estrategia_1159(    df): return     df_romania2[(vars_dict['VAR04'] >= 0.9846) & (vars_dict['VAR04'] <= 1.113)].copy()
    def estrategia_1160(    df): return     df_romania2[(vars_dict['VAR35'] >= 1.1856) & (vars_dict['VAR35'] <= 1.2638)].copy()


    # Teste com Ligas "SAUDI ARABIA 1"
    df_saudiarabia1 =     df[    df['League'] == "SAUDI ARABIA 1"].copy()
    def estrategia_1161(    df): return     df_saudiarabia1[(vars_dict['VAR26'] >= 1.4158) & (vars_dict['VAR26'] <= 1.4662)].copy()
    def estrategia_1162(    df): return     df_saudiarabia1[(vars_dict['VAR45'] >= 1.2412) & (vars_dict['VAR45'] <= 1.5459)].copy()
    def estrategia_1163(    df): return     df_saudiarabia1[(vars_dict['VAR76'] >= 0.2412) & (vars_dict['VAR76'] <= 0.5459)].copy()
    def estrategia_1164(    df): return     df_saudiarabia1[(vars_dict['VAR48'] >= 0.6469) & (vars_dict['VAR48'] <= 0.8057)].copy()
    def estrategia_1165(    df): return     df_saudiarabia1[(vars_dict['VAR64'] >= 4.5535) & (vars_dict['VAR64'] <= 8.2755)].copy()
    def estrategia_1166(    df): return     df_saudiarabia1[(vars_dict['VAR56'] >= 0.1593) & (vars_dict['VAR56'] <= 0.2909)].copy()
    def estrategia_1167(    df): return     df_saudiarabia1[(vars_dict['VAR17'] >= 0.4067) & (vars_dict['VAR17'] <= 0.5751)].copy()
    def estrategia_1168(    df): return     df_saudiarabia1[(vars_dict['VAR25'] >= 1.3986) & (vars_dict['VAR25'] <= 1.7187)].copy()
    def estrategia_1169(    df): return     df_saudiarabia1[(vars_dict['VAR06'] >= 1.5455) & (vars_dict['VAR06'] <= 2.0976)].copy()
    def estrategia_1170(    df): return     df_saudiarabia1[(vars_dict['VAR68'] >= -8.2169) & (vars_dict['VAR68'] <= -4.351)].copy()
    def estrategia_1171(    df): return     df_saudiarabia1[(vars_dict['VAR60'] >= 0.1522) & (vars_dict['VAR60'] <= 0.2888)].copy()
    def estrategia_1172(    df): return     df_saudiarabia1[(vars_dict['VAR29'] >= 1.9147) & (vars_dict['VAR29'] <= 2.7928)].copy()
    def estrategia_1173(    df): return     df_saudiarabia1[(vars_dict['VAR04'] >= 0.4767) & (vars_dict['VAR04'] <= 0.6471)].copy()
    def estrategia_1174(    df): return     df_saudiarabia1[(vars_dict['VAR11'] >= 0.4339) & (vars_dict['VAR11'] <= 0.624)].copy()
    def estrategia_1175(    df): return     df_saudiarabia1[(vars_dict['VAR70'] >= 0.4064) & (vars_dict['VAR70'] <= 0.6003)].copy()
    def estrategia_1176(    df): return     df_saudiarabia1[(vars_dict['VAR71'] >= 0.25) & (vars_dict['VAR71'] <= 0.3336)].copy()
    def estrategia_1177(    df): return     df_saudiarabia1[(vars_dict['VAR13'] >= 0.745) & (vars_dict['VAR13'] <= 0.8449)].copy()
    def estrategia_1178(    df): return     df_saudiarabia1[(vars_dict['VAR72'] >= 0.3765) & (vars_dict['VAR72'] <= 0.5)].copy()
    def estrategia_1179(    df): return     df_saudiarabia1[(vars_dict['VAR69'] >= -9.1755) & (vars_dict['VAR69'] <= -3.1044)].copy()
    def estrategia_1180(    df): return     df_saudiarabia1[(vars_dict['VAR18'] >= 0.5088) & (vars_dict['VAR18'] <= 0.5323)].copy()


    # Teste com Ligas "SCOTLAND 1"
    df_scotland1 =     df[    df['League'] == "SCOTLAND 1"].copy()
    def estrategia_1181(    df): return     df_scotland1[(vars_dict['VAR59'] >= 0.0485) & (vars_dict['VAR59'] <= 0.0653)].copy()
    def estrategia_1182(    df): return     df_scotland1[(vars_dict['VAR67'] >= 1.4507) & (vars_dict['VAR67'] <= 3.0411)].copy()
    def estrategia_1183(    df): return     df_scotland1[(vars_dict['VAR26'] >= 1.3675) & (vars_dict['VAR26'] <= 1.4341)].copy()
    def estrategia_1184(    df): return     df_scotland1[(vars_dict['VAR03'] >= 1.3724) & (vars_dict['VAR03'] <= 2.5)].copy()
    def estrategia_1185(    df): return     df_scotland1[(vars_dict['VAR41'] >= 0.5) & (vars_dict['VAR41'] <= 0.8789)].copy()
    def estrategia_1186(    df): return     df_scotland1[(vars_dict['VAR14'] >= 0.1471) & (vars_dict['VAR14'] <= 0.3687)].copy()
    def estrategia_1187(    df): return     df_scotland1[(vars_dict['VAR01'] >= 0.4) & (vars_dict['VAR01'] <= 0.7287)].copy()
    def estrategia_1188(    df): return     df_scotland1[(vars_dict['VAR16'] >= 1.6575) & (vars_dict['VAR16'] <= 2.9825)].copy()
    def estrategia_1189(    df): return     df_scotland1[(vars_dict['VAR63'] >= 1.6172) & (vars_dict['VAR63'] <= 3.2365)].copy()
    def estrategia_1190(    df): return     df_scotland1[(vars_dict['VAR46'] >= 1.0585) & (vars_dict['VAR46'] <= 1.1296)].copy()
    def estrategia_1191(    df): return     df_scotland1[(vars_dict['VAR44'] >= 0.8852) & (vars_dict['VAR44'] <= 0.9447)].copy()
    def estrategia_1192(    df): return     df_scotland1[(vars_dict['VAR18'] >= 0.2727) & (vars_dict['VAR18'] <= 0.3417)].copy()
    def estrategia_1193(    df): return     df_scotland1[(vars_dict['VAR72'] >= 0.7336) & (vars_dict['VAR72'] <= 0.8462)].copy()
    def estrategia_1194(    df): return     df_scotland1[(vars_dict['VAR40'] >= 0.2418) & (vars_dict['VAR40'] <= 0.5817)].copy()
    def estrategia_1195(    df): return     df_scotland1[(vars_dict['VAR42'] >= 0.3636) & (vars_dict['VAR42'] <= 0.6464)].copy()
    def estrategia_1196(    df): return     df_scotland1[(vars_dict['VAR15'] >= 0.3993) & (vars_dict['VAR15'] <= 0.4495)].copy()
    def estrategia_1197(    df): return     df_scotland1[(vars_dict['VAR55'] >= 0.0703) & (vars_dict['VAR55'] <= 0.0976)].copy()
    def estrategia_1198(    df): return     df_scotland1[(vars_dict['VAR21'] >= 0.3312) & (vars_dict['VAR21'] <= 0.4522)].copy()
    def estrategia_1199(    df): return     df_scotland1[(vars_dict['VAR69'] >= -21.5306) & (vars_dict['VAR69'] <= -14.9017)].copy()
    def estrategia_1200(    df): return     df_scotland1[(vars_dict['VAR47'] >= 2.3998) & (vars_dict['VAR47'] <= 5.3398)].copy()


    # Teste com Ligas "SCOTLAND 2"
    df_scotland2 =     df[    df['League'] == "SCOTLAND 2"].copy()
    def estrategia_1201(    df): return     df_scotland2[(vars_dict['VAR09'] >= 1.0) & (vars_dict['VAR09'] <= 1.0611)].copy()
    def estrategia_1202(    df): return     df_scotland2[(vars_dict['VAR58'] >= 0.0) & (vars_dict['VAR58'] <= 0.032)].copy()
    def estrategia_1203(    df): return     df_scotland2[(vars_dict['VAR66'] >= 0.0) & (vars_dict['VAR66'] <= 0.9165)].copy()
    def estrategia_1204(    df): return     df_scotland2[(vars_dict['VAR74'] >= 0.0) & (vars_dict['VAR74'] <= 0.0576)].copy()
    def estrategia_1205(    df): return     df_scotland2[(vars_dict['VAR10'] >= 1.0) & (vars_dict['VAR10'] <= 1.0611)].copy()
    def estrategia_1206(    df): return     df_scotland2[(vars_dict['VAR72'] >= 0.4044) & (vars_dict['VAR72'] <= 0.5)].copy()
    def estrategia_1207(    df): return     df_scotland2[(vars_dict['VAR31'] >= 2.6) & (vars_dict['VAR31'] <= 3.0075)].copy()
    def estrategia_1208(    df): return     df_scotland2[(vars_dict['VAR68'] >= -8.0101) & (vars_dict['VAR68'] <= -5.2199)].copy()
    def estrategia_1209(    df): return     df_scotland2[(vars_dict['VAR48'] >= 0.6513) & (vars_dict['VAR48'] <= 0.7688)].copy()
    def estrategia_1210(    df): return     df_scotland2[(vars_dict['VAR64'] >= 5.4611) & (vars_dict['VAR64'] <= 7.9518)].copy()
    def estrategia_1211(    df): return     df_scotland2[(vars_dict['VAR56'] >= 0.1912) & (vars_dict['VAR56'] <= 0.2794)].copy()
    def estrategia_1212(    df): return     df_scotland2[(vars_dict['VAR45'] >= 1.3008) & (vars_dict['VAR45'] <= 1.5355)].copy()
    def estrategia_1213(    df): return     df_scotland2[(vars_dict['VAR76'] >= 0.3008) & (vars_dict['VAR76'] <= 0.5355)].copy()
    def estrategia_1214(    df): return     df_scotland2[(vars_dict['VAR60'] >= 0.1827) & (vars_dict['VAR60'] <= 0.2814)].copy()
    def estrategia_1215(    df): return     df_scotland2[(vars_dict['VAR32'] >= 1.4693) & (vars_dict['VAR32'] <= 1.5891)].copy()
    def estrategia_1216(    df): return     df_scotland2[(vars_dict['VAR43'] >= 0.9395) & (vars_dict['VAR43'] <= 1.1214)].copy()
    def estrategia_1217(    df): return     df_scotland2[(vars_dict['VAR59'] >= 0.047) & (vars_dict['VAR59'] <= 0.0677)].copy()
    def estrategia_1218(    df): return     df_scotland2[(vars_dict['VAR11'] >= 0.4728) & (vars_dict['VAR11'] <= 0.5989)].copy()
    def estrategia_1219(    df): return     df_scotland2[(vars_dict['VAR12'] >= 0.4441) & (vars_dict['VAR12'] <= 0.4835)].copy()
    def estrategia_1220(    df): return     df_scotland2[(vars_dict['VAR61'] >= 0.2416) & (vars_dict['VAR61'] <= 0.2919)].copy()


    # Teste com Ligas "SCOTLAND 3"
    df_scotland3 =     df[    df['League'] == "SCOTLAND 3"].copy()
    def estrategia_1221(    df): return     df_scotland3[(vars_dict['VAR70'] >= 0.8421) & (vars_dict['VAR70'] <= 1.0556)].copy()
    def estrategia_1222(    df): return     df_scotland3[(vars_dict['VAR08'] >= 0.1692) & (vars_dict['VAR08'] <= 0.5765)].copy()
    def estrategia_1223(    df): return     df_scotland3[(vars_dict['VAR65'] >= -20.6877) & (vars_dict['VAR65'] <= -8.1975)].copy()
    def estrategia_1224(    df): return     df_scotland3[(vars_dict['VAR12'] >= 0.0579) & (vars_dict['VAR12'] <= 0.3048)].copy()
    def estrategia_1225(    df): return     df_scotland3[(vars_dict['VAR15'] >= 0.25) & (vars_dict['VAR15'] <= 0.4813)].copy()
    def estrategia_1226(    df): return     df_scotland3[(vars_dict['VAR07'] >= 1.7347) & (vars_dict['VAR07'] <= 5.9091)].copy()
    def estrategia_1227(    df): return     df_scotland3[(vars_dict['VAR57'] >= 0.2881) & (vars_dict['VAR57'] <= 0.7552)].copy()
    def estrategia_1228(    df): return     df_scotland3[(vars_dict['VAR73'] >= 0.7347) & (vars_dict['VAR73'] <= 4.9091)].copy()
    def estrategia_1229(    df): return     df_scotland3[(vars_dict['VAR54'] >= 0.6359) & (vars_dict['VAR54'] <= 0.9513)].copy()
    def estrategia_1230(    df): return     df_scotland3[(vars_dict['VAR18'] >= 0.1263) & (vars_dict['VAR18'] <= 0.3462)].copy()
    def estrategia_1231(    df): return     df_scotland3[(vars_dict['VAR71'] >= 0.5814) & (vars_dict['VAR71'] <= 0.7073)].copy()
    def estrategia_1232(    df): return     df_scotland3[(vars_dict['VAR66'] >= 0.9165) & (vars_dict['VAR66'] <= 9.9443)].copy()
    def estrategia_1233(    df): return     df_scotland3[(vars_dict['VAR10'] >= 1.0611) & (vars_dict['VAR10'] <= 1.9643)].copy()
    def estrategia_1234(    df): return     df_scotland3[(vars_dict['VAR21'] >= 0.0805) & (vars_dict['VAR21'] <= 0.3818)].copy()
    def estrategia_1235(    df): return     df_scotland3[(vars_dict['VAR72'] >= 0.6667) & (vars_dict['VAR72'] <= 1.8333)].copy()
    def estrategia_1236(    df): return     df_scotland3[(vars_dict['VAR09'] >= 0.5091) & (vars_dict['VAR09'] <= 0.9424)].copy()
    def estrategia_1237(    df): return     df_scotland3[(vars_dict['VAR42'] >= 1.2556) & (vars_dict['VAR42'] <= 1.3071)].copy()
    def estrategia_1238(    df): return     df_scotland3[(vars_dict['VAR14'] >= 0.1275) & (vars_dict['VAR14'] <= 0.525)].copy()
    def estrategia_1239(    df): return     df_scotland3[(vars_dict['VAR19'] >= 0.9545) & (vars_dict['VAR19'] <= 2.3301)].copy()
    def estrategia_1240(    df): return     df_scotland3[(vars_dict['VAR13'] >= 1.0) & (vars_dict['VAR13'] <= 1.296)].copy()


    # Teste com Ligas "SCOTLAND 4"
    df_scotland4 =     df[    df['League'] == "SCOTLAND 4"].copy()
    def estrategia_1241(    df): return     df_scotland4[(vars_dict['VAR22'] >= 0.8512) & (vars_dict['VAR22'] <= 0.9416)].copy()
    def estrategia_1242(    df): return     df_scotland4[(vars_dict['VAR42'] >= 1.0443) & (vars_dict['VAR42'] <= 1.1603)].copy()
    def estrategia_1243(    df): return     df_scotland4[(vars_dict['VAR40'] >= 1.1206) & (vars_dict['VAR40'] <= 1.248)].copy()
    def estrategia_1244(    df): return     df_scotland4[(vars_dict['VAR11'] >= 0.6102) & (vars_dict['VAR11'] <= 0.7099)].copy()
    def estrategia_1245(    df): return     df_scotland4[(vars_dict['VAR34'] >= 1.3207) & (vars_dict['VAR34'] <= 1.4357)].copy()
    def estrategia_1246(    df): return     df_scotland4[(vars_dict['VAR18'] >= 0.5088) & (vars_dict['VAR18'] <= 0.5229)].copy()
    def estrategia_1247(    df): return     df_scotland4[(vars_dict['VAR16'] >= 0.7983) & (vars_dict['VAR16'] <= 0.8922)].copy()
    def estrategia_1248(    df): return     df_scotland4[(vars_dict['VAR36'] >= 1.4044) & (vars_dict['VAR36'] <= 1.5038)].copy()
    def estrategia_1249(    df): return     df_scotland4[(vars_dict['VAR38'] >= 2.0359) & (vars_dict['VAR38'] <= 2.1539)].copy()
    def estrategia_1250(    df): return     df_scotland4[(vars_dict['VAR31'] >= 2.2569) & (vars_dict['VAR31'] <= 2.4107)].copy()
    def estrategia_1251(    df): return     df_scotland4[(vars_dict['VAR04'] >= 0.6841) & (vars_dict['VAR04'] <= 0.7656)].copy()
    def estrategia_1252(    df): return     df_scotland4[(vars_dict['VAR37'] >= 1.8061) & (vars_dict['VAR37'] <= 1.8843)].copy()
    def estrategia_1253(    df): return     df_scotland4[(vars_dict['VAR19'] >= 0.7855) & (vars_dict['VAR19'] <= 0.8512)].copy()
    def estrategia_1254(    df): return     df_scotland4[(vars_dict['VAR17'] >= 0.5648) & (vars_dict['VAR17'] <= 0.6391)].copy()
    def estrategia_1255(    df): return     df_scotland4[(vars_dict['VAR21'] >= 0.6235) & (vars_dict['VAR21'] <= 0.7)].copy()
    def estrategia_1256(    df): return     df_scotland4[(vars_dict['VAR57'] >= 0.0201) & (vars_dict['VAR57'] <= 0.0245)].copy()
    def estrategia_1257(    df): return     df_scotland4[(vars_dict['VAR73'] >= 0.0368) & (vars_dict['VAR73'] <= 0.047)].copy()
    def estrategia_1258(    df): return     df_scotland4[(vars_dict['VAR45'] >= 1.2046) & (vars_dict['VAR45'] <= 1.2946)].copy()
    def estrategia_1259(    df): return     df_scotland4[(vars_dict['VAR76'] >= 0.2046) & (vars_dict['VAR76'] <= 0.2946)].copy()
    def estrategia_1260(    df): return     df_scotland4[(vars_dict['VAR64'] >= 3.9346) & (vars_dict['VAR64'] <= 5.3512)].copy()


    # Teste com Ligas "SERBIA 1"
    df_serbia1 =     df[    df['League'] == "SERBIA 1"].copy()
    def estrategia_1261(    df): return     df_serbia1[(vars_dict['VAR74'] >= 0.1707) & (vars_dict['VAR74'] <= 0.2134)].copy()
    def estrategia_1262(    df): return     df_serbia1[(vars_dict['VAR30'] >= 1.8409) & (vars_dict['VAR30'] <= 2.6619)].copy()
    def estrategia_1263(    df): return     df_serbia1[(vars_dict['VAR46'] >= 0.9013) & (vars_dict['VAR46'] <= 0.9969)].copy()
    def estrategia_1264(    df): return     df_serbia1[(vars_dict['VAR44'] >= 1.0031) & (vars_dict['VAR44'] <= 1.1095)].copy()
    def estrategia_1265(    df): return     df_serbia1[(vars_dict['VAR59'] >= 0.0526) & (vars_dict['VAR59'] <= 0.0771)].copy()
    def estrategia_1266(    df): return     df_serbia1[(vars_dict['VAR67'] >= -2.1211) & (vars_dict['VAR67'] <= -0.0673)].copy()
    def estrategia_1267(    df): return     df_serbia1[(vars_dict['VAR37'] >= 1.7708) & (vars_dict['VAR37'] <= 1.9678)].copy()
    def estrategia_1268(    df): return     df_serbia1[(vars_dict['VAR29'] >= 1.1716) & (vars_dict['VAR29'] <= 1.3093)].copy()
    def estrategia_1269(    df): return     df_serbia1[(vars_dict['VAR28'] >= 1.5257) & (vars_dict['VAR28'] <= 1.5787)].copy()
    def estrategia_1270(    df): return     df_serbia1[(vars_dict['VAR40'] >= 1.0873) & (vars_dict['VAR40'] <= 1.2189)].copy()
    def estrategia_1271(    df): return     df_serbia1[(vars_dict['VAR58'] >= 0.0932) & (vars_dict['VAR58'] <= 0.1269)].copy()
    def estrategia_1272(    df): return     df_serbia1[(vars_dict['VAR42'] >= 1.2755) & (vars_dict['VAR42'] <= 1.3636)].copy()
    def estrategia_1273(    df): return     df_serbia1[(vars_dict['VAR20'] >= 0.5355) & (vars_dict['VAR20'] <= 0.7087)].copy()
    def estrategia_1274(    df): return     df_serbia1[(vars_dict['VAR01'] >= 0.9351) & (vars_dict['VAR01'] <= 1.17)].copy()
    def estrategia_1275(    df): return     df_serbia1[(vars_dict['VAR63'] >= -1.6002) & (vars_dict['VAR63'] <= 0.4904)].copy()
    def estrategia_1276(    df): return     df_serbia1[(vars_dict['VAR03'] >= 0.8547) & (vars_dict['VAR03'] <= 1.0694)].copy()
    def estrategia_1277(    df): return     df_serbia1[(vars_dict['VAR14'] >= 0.5015) & (vars_dict['VAR14'] <= 0.6298)].copy()
    def estrategia_1278(    df): return     df_serbia1[(vars_dict['VAR09'] >= 1.1628) & (vars_dict['VAR09'] <= 1.2848)].copy()
    def estrategia_1279(    df): return     df_serbia1[(vars_dict['VAR36'] >= 1.5426) & (vars_dict['VAR36'] <= 1.9829)].copy()
    def estrategia_1280(    df): return     df_serbia1[(vars_dict['VAR12'] >= 0.7324) & (vars_dict['VAR12'] <= 1.0698)].copy()


    # Teste com Ligas "SLOVAKIA 1"
    df_slovakia1 =     df[    df['League'] == "SLOVAKIA 1"].copy()
    def estrategia_1281(    df): return     df_slovakia1[(vars_dict['VAR70'] >= 0.1448) & (vars_dict['VAR70'] <= 0.3)].copy()
    def estrategia_1282(    df): return     df_slovakia1[(vars_dict['VAR34'] >= 1.2421) & (vars_dict['VAR34'] <= 1.3807)].copy()
    def estrategia_1283(    df): return     df_slovakia1[(vars_dict['VAR22'] >= 0.8034) & (vars_dict['VAR22'] <= 0.9257)].copy()
    def estrategia_1284(    df): return     df_slovakia1[(vars_dict['VAR57'] >= 0.0115) & (vars_dict['VAR57'] <= 0.0292)].copy()
    def estrategia_1285(    df): return     df_slovakia1[(vars_dict['VAR73'] >= 0.0219) & (vars_dict['VAR73'] <= 0.0538)].copy()
    def estrategia_1286(    df): return     df_slovakia1[(vars_dict['VAR03'] >= 0.8351) & (vars_dict['VAR03'] <= 0.9291)].copy()
    def estrategia_1287(    df): return     df_slovakia1[(vars_dict['VAR01'] >= 1.0764) & (vars_dict['VAR01'] <= 1.1974)].copy()
    def estrategia_1288(    df): return     df_slovakia1[(vars_dict['VAR38'] >= 1.9905) & (vars_dict['VAR38'] <= 2.1123)].copy()
    def estrategia_1289(    df): return     df_slovakia1[(vars_dict['VAR39'] >= 2.0775) & (vars_dict['VAR39'] <= 2.5187)].copy()
    def estrategia_1290(    df): return     df_slovakia1[(vars_dict['VAR33'] >= 1.3499) & (vars_dict['VAR33'] <= 1.48)].copy()
    def estrategia_1291(    df): return     df_slovakia1[(vars_dict['VAR09'] >= 1.1628) & (vars_dict['VAR09'] <= 1.2727)].copy()
    def estrategia_1292(    df): return     df_slovakia1[(vars_dict['VAR64'] >= -0.1888) & (vars_dict['VAR64'] <= 1.2429)].copy()
    def estrategia_1293(    df): return     df_slovakia1[(vars_dict['VAR06'] >= 0.9747) & (vars_dict['VAR06'] <= 1.1406)].copy()
    def estrategia_1294(    df): return     df_slovakia1[(vars_dict['VAR04'] >= 0.8768) & (vars_dict['VAR04'] <= 1.026)].copy()
    def estrategia_1295(    df): return     df_slovakia1[(vars_dict['VAR12'] >= 0.5519) & (vars_dict['VAR12'] <= 0.5748)].copy()
    def estrategia_1296(    df): return     df_slovakia1[(vars_dict['VAR71'] >= 0.0861) & (vars_dict['VAR71'] <= 0.1567)].copy()
    def estrategia_1297(    df): return     df_slovakia1[(vars_dict['VAR59'] >= 0.0452) & (vars_dict['VAR59'] <= 0.0779)].copy()
    def estrategia_1298(    df): return     df_slovakia1[(vars_dict['VAR74'] >= 0.1882) & (vars_dict['VAR74'] <= 0.2727)].copy()
    def estrategia_1299(    df): return     df_slovakia1[(vars_dict['VAR54'] >= 0.0587) & (vars_dict['VAR54'] <= 0.1112)].copy()
    def estrategia_1300(    df): return     df_slovakia1[(vars_dict['VAR31'] >= 1.8914) & (vars_dict['VAR31'] <= 2.0588)].copy()


    # Teste com Ligas "SOUTH KOREA 1"
    df_southkorea1 =     df[    df['League'] == "SOUTH KOREA 1"].copy()
    def estrategia_1301(    df): return     df_southkorea1[(vars_dict['VAR21'] >= 0.5969) & (vars_dict['VAR21'] <= 0.6061)].copy()
    def estrategia_1302(    df): return     df_southkorea1[(vars_dict['VAR40'] >= 1.3635) & (vars_dict['VAR40'] <= 1.4191)].copy()
    def estrategia_1303(    df): return     df_southkorea1[(vars_dict['VAR54'] >= 0.1014) & (vars_dict['VAR54'] <= 0.1223)].copy()
    def estrategia_1304(    df): return     df_southkorea1[(vars_dict['VAR77'] >= 0.3846) & (vars_dict['VAR77'] <= 0.5917)].copy()
    def estrategia_1305(    df): return     df_southkorea1[(vars_dict['VAR07'] >= 0.72) & (vars_dict['VAR07'] <= 0.7767)].copy()
    def estrategia_1306(    df): return     df_southkorea1[(vars_dict['VAR17'] >= 0.7985) & (vars_dict['VAR17'] <= 0.8464)].copy()
    def estrategia_1307(    df): return     df_southkorea1[(vars_dict['VAR32'] >= 1.6543) & (vars_dict['VAR32'] <= 1.7293)].copy()
    def estrategia_1308(    df): return     df_southkorea1[(vars_dict['VAR11'] >= 0.7069) & (vars_dict['VAR11'] <= 0.7765)].copy()
    def estrategia_1309(    df): return     df_southkorea1[(vars_dict['VAR25'] >= 1.6912) & (vars_dict['VAR25'] <= 1.8382)].copy()
    def estrategia_1310(    df): return     df_southkorea1[(vars_dict['VAR73'] >= 0.0505) & (vars_dict['VAR73'] <= 0.0532)].copy()
    def estrategia_1311(    df): return     df_southkorea1[(vars_dict['VAR75'] >= 0.0526) & (vars_dict['VAR75'] <= 0.0769)].copy()
    def estrategia_1312(    df): return     df_southkorea1[(vars_dict['VAR61'] >= 0.3039) & (vars_dict['VAR61'] <= 0.4648)].copy()
    def estrategia_1313(    df): return     df_southkorea1[(vars_dict['VAR22'] >= 0.5714) & (vars_dict['VAR22'] <= 0.6207)].copy()
    def estrategia_1314(    df): return     df_southkorea1[(vars_dict['VAR16'] >= 0.5318) & (vars_dict['VAR16'] <= 0.5697)].copy()
    def estrategia_1315(    df): return     df_southkorea1[(vars_dict['VAR02'] >= 0.7064) & (vars_dict['VAR02'] <= 0.8681)].copy()
    def estrategia_1316(    df): return     df_southkorea1[(vars_dict['VAR36'] >= 1.1273) & (vars_dict['VAR36'] <= 1.1961)].copy()
    def estrategia_1317(    df): return     df_southkorea1[(vars_dict['VAR30'] >= 2.0714) & (vars_dict['VAR30'] <= 2.3529)].copy()
    def estrategia_1318(    df): return     df_southkorea1[(vars_dict['VAR42'] >= 1.4417) & (vars_dict['VAR42'] <= 1.5332)].copy()
    def estrategia_1319(    df): return     df_southkorea1[(vars_dict['VAR24'] >= 2.7132) & (vars_dict['VAR24'] <= 2.7953)].copy()
    def estrategia_1320(    df): return     df_southkorea1[(vars_dict['VAR57'] >= 0.1337) & (vars_dict['VAR57'] <= 0.1757)].copy()


    # Teste com Ligas "SOUTH KOREA 2"
    df_southkorea2 =     df[    df['League'] == "SOUTH KOREA 2"].copy()
    def estrategia_1321(    df): return     df_southkorea2[(vars_dict['VAR03'] >= 0.8765) & (vars_dict['VAR03'] <= 1.0)].copy()
    def estrategia_1322(    df): return     df_southkorea2[(vars_dict['VAR24'] >= 2.2556) & (vars_dict['VAR24'] <= 2.2794)].copy()
    def estrategia_1323(    df): return     df_southkorea2[(vars_dict['VAR62'] >= -5.7699) & (vars_dict['VAR62'] <= -4.0625)].copy()
    def estrategia_1324(    df): return     df_southkorea2[(vars_dict['VAR22'] >= 0.4616) & (vars_dict['VAR22'] <= 0.5479)].copy()
    def estrategia_1325(    df): return     df_southkorea2[(vars_dict['VAR21'] >= 0.5767) & (vars_dict['VAR21'] <= 0.5833)].copy()
    def estrategia_1326(    df): return     df_southkorea2[(vars_dict['VAR41'] >= 1.1133) & (vars_dict['VAR41'] <= 1.1544)].copy()
    def estrategia_1327(    df): return     df_southkorea2[(vars_dict['VAR70'] >= 0.4545) & (vars_dict['VAR70'] <= 0.5459)].copy()
    def estrategia_1328(    df): return     df_southkorea2[(vars_dict['VAR01'] >= 1.0) & (vars_dict['VAR01'] <= 1.1409)].copy()
    def estrategia_1329(    df): return     df_southkorea2[(vars_dict['VAR56'] >= 0.0256) & (vars_dict['VAR56'] <= 0.0396)].copy()
    def estrategia_1330(    df): return     df_southkorea2[(vars_dict['VAR18'] >= 0.6667) & (vars_dict['VAR18'] <= 0.8655)].copy()
    def estrategia_1331(    df): return     df_southkorea2[(vars_dict['VAR43'] >= 1.2089) & (vars_dict['VAR43'] <= 1.2708)].copy()
    def estrategia_1332(    df): return     df_southkorea2[(vars_dict['VAR35'] >= 1.2708) & (vars_dict['VAR35'] <= 1.3264)].copy()
    def estrategia_1333(    df): return     df_southkorea2[(vars_dict['VAR31'] >= 1.8222) & (vars_dict['VAR31'] <= 1.9075)].copy()
    def estrategia_1334(    df): return     df_southkorea2[(vars_dict['VAR39'] >= 2.6154) & (vars_dict['VAR39'] <= 3.0738)].copy()
    def estrategia_1335(    df): return     df_southkorea2[(vars_dict['VAR63'] >= -1.2787) & (vars_dict['VAR63'] <= 0.0)].copy()
    def estrategia_1336(    df): return     df_southkorea2[(vars_dict['VAR49'] >= 1.218) & (vars_dict['VAR49'] <= 1.336)].copy()
    def estrategia_1337(    df): return     df_southkorea2[(vars_dict['VAR68'] >= 0.4681) & (vars_dict['VAR68'] <= 1.0034)].copy()
    def estrategia_1338(    df): return     df_southkorea2[(vars_dict['VAR71'] >= 0.1807) & (vars_dict['VAR71'] <= 0.2544)].copy()
    def estrategia_1339(    df): return     df_southkorea2[(vars_dict['VAR16'] >= 0.5968) & (vars_dict['VAR16'] <= 0.6496)].copy()
    def estrategia_1340(    df): return     df_southkorea2[(vars_dict['VAR08'] >= 1.3889) & (vars_dict['VAR08'] <= 1.5184)].copy()


    # Teste com Ligas "SPAIN 1"
    df_spain1 =     df[    df['League'] == "SPAIN 1"].copy()
    def estrategia_1341(    df): return     df_spain1[(vars_dict['VAR09'] >= 0.9231) & (vars_dict['VAR09'] <= 1.0833)].copy()
    def estrategia_1342(    df): return     df_spain1[(vars_dict['VAR72'] >= 0.3333) & (vars_dict['VAR72'] <= 0.4165)].copy()
    def estrategia_1343(    df): return     df_spain1[(vars_dict['VAR28'] >= 1.5704) & (vars_dict['VAR28'] <= 1.6176)].copy()
    def estrategia_1344(    df): return     df_spain1[(vars_dict['VAR74'] >= 0.0769) & (vars_dict['VAR74'] <= 0.0833)].copy()
    def estrategia_1345(    df): return     df_spain1[(vars_dict['VAR16'] >= 0.757) & (vars_dict['VAR16'] <= 1.0514)].copy()
    def estrategia_1346(    df): return     df_spain1[(vars_dict['VAR31'] >= 1.7778) & (vars_dict['VAR31'] <= 1.8542)].copy()
    def estrategia_1347(    df): return     df_spain1[(vars_dict['VAR55'] >= 0.0447) & (vars_dict['VAR55'] <= 0.0679)].copy()
    def estrategia_1348(    df): return     df_spain1[(vars_dict['VAR14'] >= 1.0) & (vars_dict['VAR14'] <= 1.211)].copy()
    def estrategia_1349(    df): return     df_spain1[(vars_dict['VAR64'] >= -1.8922) & (vars_dict['VAR64'] <= -1.437)].copy()
    def estrategia_1350(    df): return     df_spain1[(vars_dict['VAR57'] >= 0.1443) & (vars_dict['VAR57'] <= 0.1825)].copy()
    def estrategia_1351(    df): return     df_spain1[(vars_dict['VAR58'] >= 0.0427) & (vars_dict['VAR58'] <= 0.0714)].copy()
    def estrategia_1352(    df): return     df_spain1[(vars_dict['VAR24'] >= 2.7907) & (vars_dict['VAR24'] <= 3.04)].copy()
    def estrategia_1353(    df): return     df_spain1[(vars_dict['VAR03'] >= 0.4112) & (vars_dict['VAR03'] <= 0.5)].copy()
    def estrategia_1354(    df): return     df_spain1[(vars_dict['VAR22'] >= 0.8259) & (vars_dict['VAR22'] <= 1.0617)].copy()
    def estrategia_1355(    df): return     df_spain1[(vars_dict['VAR63'] >= -10.2236) & (vars_dict['VAR63'] <= -8.1099)].copy()
    def estrategia_1356(    df): return     df_spain1[(vars_dict['VAR12'] >= 0.6118) & (vars_dict['VAR12'] <= 0.6747)].copy()
    def estrategia_1357(    df): return     df_spain1[(vars_dict['VAR44'] >= 1.5504) & (vars_dict['VAR44'] <= 1.8)].copy()
    def estrategia_1358(    df): return     df_spain1[(vars_dict['VAR75'] >= 0.5504) & (vars_dict['VAR75'] <= 0.8)].copy()
    def estrategia_1359(    df): return     df_spain1[(vars_dict['VAR59'] >= 0.2759) & (vars_dict['VAR59'] <= 0.3556)].copy()
    def estrategia_1360(    df): return     df_spain1[(vars_dict['VAR01'] >= 2.0) & (vars_dict['VAR01'] <= 2.4316)].copy()


    # Teste com Ligas "SPAIN 2"
    df_spain2 =     df[    df['League'] == "SPAIN 2"].copy()
    def estrategia_1361(    df): return     df_spain2[(vars_dict['VAR77'] >= 0.1111) & (vars_dict['VAR77'] <= 0.1605)].copy()
    def estrategia_1362(    df): return     df_spain2[(vars_dict['VAR57'] >= 0.3671) & (vars_dict['VAR57'] <= 0.55)].copy()
    def estrategia_1363(    df): return     df_spain2[(vars_dict['VAR65'] >= 10.3999) & (vars_dict['VAR65'] <= 15.3763)].copy()
    def estrategia_1364(    df): return     df_spain2[(vars_dict['VAR08'] >= 2.0571) & (vars_dict['VAR08'] <= 3.2)].copy()
    def estrategia_1365(    df): return     df_spain2[(vars_dict['VAR73'] >= 0.5139) & (vars_dict['VAR73'] <= 0.875)].copy()
    def estrategia_1366(    df): return     df_spain2[(vars_dict['VAR27'] >= 1.0) & (vars_dict['VAR27'] <= 1.0571)].copy()
    def estrategia_1367(    df): return     df_spain2[(vars_dict['VAR09'] >= 0.7364) & (vars_dict['VAR09'] <= 0.7952)].copy()
    def estrategia_1368(    df): return     df_spain2[(vars_dict['VAR54'] >= 0.0891) & (vars_dict['VAR54'] <= 0.1318)].copy()
    def estrategia_1369(    df): return     df_spain2[(vars_dict['VAR31'] >= 1.8033) & (vars_dict['VAR31'] <= 1.8563)].copy()
    def estrategia_1370(    df): return     df_spain2[(vars_dict['VAR66'] >= 4.6519) & (vars_dict['VAR66'] <= 5.4977)].copy()
    def estrategia_1371(    df): return     df_spain2[(vars_dict['VAR74'] >= 0.2636) & (vars_dict['VAR74'] <= 0.3022)].copy()
    def estrategia_1372(    df): return     df_spain2[(vars_dict['VAR10'] >= 1.358) & (vars_dict['VAR10'] <= 1.4331)].copy()
    def estrategia_1373(    df): return     df_spain2[(vars_dict['VAR06'] >= 0.7619) & (vars_dict['VAR06'] <= 0.8)].copy()
    def estrategia_1374(    df): return     df_spain2[(vars_dict['VAR40'] >= 1.8824) & (vars_dict['VAR40'] <= 1.9853)].copy()
    def estrategia_1375(    df): return     df_spain2[(vars_dict['VAR04'] >= 1.25) & (vars_dict['VAR04'] <= 1.3125)].copy()
    def estrategia_1376(    df): return     df_spain2[(vars_dict['VAR61'] >= 0.0817) & (vars_dict['VAR61'] <= 0.118)].copy()
    def estrategia_1377(    df): return     df_spain2[(vars_dict['VAR12'] >= 0.9) & (vars_dict['VAR12'] <= 1.0)].copy()
    def estrategia_1378(    df): return     df_spain2[(vars_dict['VAR23'] >= 1.6544) & (vars_dict['VAR23'] <= 1.7647)].copy()
    def estrategia_1379(    df): return     df_spain2[(vars_dict['VAR30'] >= 1.3889) & (vars_dict['VAR30'] <= 1.5686)].copy()
    def estrategia_1380(    df): return     df_spain2[(vars_dict['VAR19'] >= 0.6407) & (vars_dict['VAR19'] <= 0.7)].copy()


    # Teste com Ligas "SWEDEN 1"
    df_sweden1 =     df[    df['League'] == "SWEDEN 1"].copy()
    def estrategia_1381(    df): return     df_sweden1[(vars_dict['VAR28'] >= 1.296) & (vars_dict['VAR28'] <= 1.336)].copy()
    def estrategia_1382(    df): return     df_sweden1[(vars_dict['VAR58'] >= 0.1627) & (vars_dict['VAR58'] <= 0.1925)].copy()
    def estrategia_1383(    df): return     df_sweden1[(vars_dict['VAR66'] >= -4.6519) & (vars_dict['VAR66'] <= -3.5082)].copy()
    def estrategia_1384(    df): return     df_sweden1[(vars_dict['VAR10'] >= 0.7364) & (vars_dict['VAR10'] <= 0.7952)].copy()
    def estrategia_1385(    df): return     df_sweden1[(vars_dict['VAR74'] >= 0.358) & (vars_dict['VAR74'] <= 0.4331)].copy()
    def estrategia_1386(    df): return     df_sweden1[(vars_dict['VAR09'] >= 1.358) & (vars_dict['VAR09'] <= 1.4331)].copy()
    def estrategia_1387(    df): return     df_sweden1[(vars_dict['VAR16'] >= 1.0238) & (vars_dict['VAR16'] <= 1.7692)].copy()
    def estrategia_1388(    df): return     df_sweden1[(vars_dict['VAR59'] >= 0.0) & (vars_dict['VAR59'] <= 0.0339)].copy()
    def estrategia_1389(    df): return     df_sweden1[(vars_dict['VAR75'] >= 0.0) & (vars_dict['VAR75'] <= 0.0455)].copy()
    def estrategia_1390(    df): return     df_sweden1[(vars_dict['VAR04'] >= 0.26) & (vars_dict['VAR04'] <= 0.5588)].copy()
    def estrategia_1391(    df): return     df_sweden1[(vars_dict['VAR11'] >= 0.16) & (vars_dict['VAR11'] <= 0.5054)].copy()
    def estrategia_1392(    df): return     df_sweden1[(vars_dict['VAR31'] >= 2.788) & (vars_dict['VAR31'] <= 4.717)].copy()
    def estrategia_1393(    df): return     df_sweden1[(vars_dict['VAR54'] >= 0.2284) & (vars_dict['VAR54'] <= 0.277)].copy()
    def estrategia_1394(    df): return     df_sweden1[(vars_dict['VAR15'] >= 0.5426) & (vars_dict['VAR15'] <= 0.5563)].copy()
    def estrategia_1395(    df): return     df_sweden1[(vars_dict['VAR34'] >= 1.4478) & (vars_dict['VAR34'] <= 1.6683)].copy()
    def estrategia_1396(    df): return     df_sweden1[(vars_dict['VAR06'] >= 1.7895) & (vars_dict['VAR06'] <= 3.8462)].copy()
    def estrategia_1397(    df): return     df_sweden1[(vars_dict['VAR42'] >= 0.5735) & (vars_dict['VAR42'] <= 0.9363)].copy()
    def estrategia_1398(    df): return     df_sweden1[(vars_dict['VAR40'] >= 0.4706) & (vars_dict['VAR40'] <= 0.983)].copy()
    def estrategia_1399(    df): return     df_sweden1[(vars_dict['VAR60'] >= 0.2196) & (vars_dict['VAR60'] <= 0.5606)].copy()
    def estrategia_1400(    df): return     df_sweden1[(vars_dict['VAR32'] >= 1.2264) & (vars_dict['VAR32'] <= 1.5656)].copy()


    # Teste com Ligas "SWEDEN 2"
    df_sweden2 =     df[    df['League'] == "SWEDEN 2"].copy()
    def estrategia_1401(    df): return     df_sweden2[(vars_dict['VAR12'] >= 0.1773) & (vars_dict['VAR12'] <= 0.3854)].copy()
    def estrategia_1402(    df): return     df_sweden2[(vars_dict['VAR11'] >= 0.982) & (vars_dict['VAR11'] <= 1.0459)].copy()
    def estrategia_1403(    df): return     df_sweden2[(vars_dict['VAR41'] >= 0.7985) & (vars_dict['VAR41'] <= 1.1656)].copy()
    def estrategia_1404(    df): return     df_sweden2[(vars_dict['VAR70'] >= 0.7462) & (vars_dict['VAR70'] <= 1.1635)].copy()
    def estrategia_1405(    df): return     df_sweden2[(vars_dict['VAR48'] >= 0.4487) & (vars_dict['VAR48'] <= 0.7725)].copy()
    def estrategia_1406(    df): return     df_sweden2[(vars_dict['VAR18'] >= 0.2692) & (vars_dict['VAR18'] <= 0.3951)].copy()
    def estrategia_1407(    df): return     df_sweden2[(vars_dict['VAR24'] >= 3.4426) & (vars_dict['VAR24'] <= 6.9444)].copy()
    def estrategia_1408(    df): return     df_sweden2[(vars_dict['VAR77'] >= 0.5677) & (vars_dict['VAR77'] <= 1.3274)].copy()
    def estrategia_1409(    df): return     df_sweden2[(vars_dict['VAR17'] >= 0.875) & (vars_dict['VAR17'] <= 0.9349)].copy()
    def estrategia_1410(    df): return     df_sweden2[(vars_dict['VAR34'] >= 1.1909) & (vars_dict['VAR34'] <= 1.2662)].copy()
    def estrategia_1411(    df): return     df_sweden2[(vars_dict['VAR62'] >= -6.1655) & (vars_dict['VAR62'] <= -4.0765)].copy()
    def estrategia_1412(    df): return     df_sweden2[(vars_dict['VAR21'] >= 0.5706) & (vars_dict['VAR21'] <= 0.5909)].copy()
    def estrategia_1413(    df): return     df_sweden2[(vars_dict['VAR44'] >= 0.8872) & (vars_dict['VAR44'] <= 1.0226)].copy()
    def estrategia_1414(    df): return     df_sweden2[(vars_dict['VAR19'] >= 0.801) & (vars_dict['VAR19'] <= 1.3542)].copy()
    def estrategia_1415(    df): return     df_sweden2[(vars_dict['VAR13'] >= 0.8833) & (vars_dict['VAR13'] <= 1.1806)].copy()
    def estrategia_1416(    df): return     df_sweden2[(vars_dict['VAR35'] >= 1.2791) & (vars_dict['VAR35'] <= 1.7257)].copy()
    def estrategia_1417(    df): return     df_sweden2[(vars_dict['VAR68'] >= -13.1493) & (vars_dict['VAR68'] <= -5.0402)].copy()
    def estrategia_1418(    df): return     df_sweden2[(vars_dict['VAR29'] >= 1.5414) & (vars_dict['VAR29'] <= 1.5769)].copy()
    def estrategia_1419(    df): return     df_sweden2[(vars_dict['VAR25'] >= 2.6609) & (vars_dict['VAR25'] <= 3.1065)].copy()
    def estrategia_1420(    df): return     df_sweden2[(vars_dict['VAR39'] >= 0.5475) & (vars_dict['VAR39'] <= 1.2353)].copy()


    # Teste com Ligas "SWITZERLAND 1"
    df_switzerland1 =     df[    df['League'] == "SWITZERLAND 1"].copy()
    def estrategia_1421(    df): return     df_switzerland1[(vars_dict['VAR74'] >= 0.1561) & (vars_dict['VAR74'] <= 0.2575)].copy()
    def estrategia_1422(    df): return     df_switzerland1[(vars_dict['VAR27'] >= 1.68) & (vars_dict['VAR27'] <= 1.7605)].copy()
    def estrategia_1423(    df): return     df_switzerland1[(vars_dict['VAR26'] >= 1.4511) & (vars_dict['VAR26'] <= 1.5)].copy()
    def estrategia_1424(    df): return     df_switzerland1[(vars_dict['VAR66'] >= -2.2344) & (vars_dict['VAR66'] <= -0.9165)].copy()
    def estrategia_1425(    df): return     df_switzerland1[(vars_dict['VAR09'] >= 1.1561) & (vars_dict['VAR09'] <= 1.2575)].copy()
    def estrategia_1426(    df): return     df_switzerland1[(vars_dict['VAR10'] >= 0.865) & (vars_dict['VAR10'] <= 0.9424)].copy()
    def estrategia_1427(    df): return     df_switzerland1[(vars_dict['VAR73'] >= 0.0) & (vars_dict['VAR73'] <= 0.0532)].copy()
    def estrategia_1428(    df): return     df_switzerland1[(vars_dict['VAR11'] >= 0.7848) & (vars_dict['VAR11'] <= 0.8489)].copy()
    def estrategia_1429(    df): return     df_switzerland1[(vars_dict['VAR42'] >= 1.2544) & (vars_dict['VAR42'] <= 1.3302)].copy()
    def estrategia_1430(    df): return     df_switzerland1[(vars_dict['VAR32'] >= 1.9657) & (vars_dict['VAR32'] <= 2.0511)].copy()
    def estrategia_1431(    df): return     df_switzerland1[(vars_dict['VAR07'] >= 1.3383) & (vars_dict['VAR07'] <= 1.4375)].copy()
    def estrategia_1432(    df): return     df_switzerland1[(vars_dict['VAR58'] >= 0.078) & (vars_dict['VAR58'] <= 0.1226)].copy()
    def estrategia_1433(    df): return     df_switzerland1[(vars_dict['VAR43'] >= 1.7213) & (vars_dict['VAR43'] <= 1.8033)].copy()
    def estrategia_1434(    df): return     df_switzerland1[(vars_dict['VAR37'] >= 1.4367) & (vars_dict['VAR37'] <= 1.5)].copy()
    def estrategia_1435(    df): return     df_switzerland1[(vars_dict['VAR71'] >= 0.1841) & (vars_dict['VAR71'] <= 0.2963)].copy()
    def estrategia_1436(    df): return     df_switzerland1[(vars_dict['VAR15'] >= 0.55) & (vars_dict['VAR15'] <= 0.5609)].copy()
    def estrategia_1437(    df): return     df_switzerland1[(vars_dict['VAR40'] >= 1.4143) & (vars_dict['VAR40'] <= 1.4965)].copy()
    def estrategia_1438(    df): return     df_switzerland1[(vars_dict['VAR55'] >= 0.0476) & (vars_dict['VAR55'] <= 0.0847)].copy()
    def estrategia_1439(    df): return     df_switzerland1[(vars_dict['VAR29'] >= 1.528) & (vars_dict['VAR29'] <= 1.5504)].copy()
    def estrategia_1440(    df): return     df_switzerland1[(vars_dict['VAR57'] >= 0.0) & (vars_dict['VAR57'] <= 0.0269)].copy()


    # Teste com Ligas "SWITZERLAND 2"
    df_switzerland2 =     df[    df['League'] == "SWITZERLAND 2"].copy()
    def estrategia_1441(    df): return     df_switzerland2[(vars_dict['VAR15'] >= 0.6089) & (vars_dict['VAR15'] <= 0.6232)].copy()
    def estrategia_1442(    df): return     df_switzerland2[(vars_dict['VAR18'] >= 0.4225) & (vars_dict['VAR18'] <= 0.4329)].copy()
    def estrategia_1443(    df): return     df_switzerland2[(vars_dict['VAR12'] >= 0.4263) & (vars_dict['VAR12'] <= 0.4512)].copy()
    def estrategia_1444(    df): return     df_switzerland2[(vars_dict['VAR10'] >= 0.6414) & (vars_dict['VAR10'] <= 0.6681)].copy()
    def estrategia_1445(    df): return     df_switzerland2[(vars_dict['VAR66'] >= -6.7285) & (vars_dict['VAR66'] <= -6.111)].copy()
    def estrategia_1446(    df): return     df_switzerland2[(vars_dict['VAR28'] >= 1.1956) & (vars_dict['VAR28'] <= 1.216)].copy()
    def estrategia_1447(    df): return     df_switzerland2[(vars_dict['VAR25'] >= 1.9568) & (vars_dict['VAR25'] <= 2.1312)].copy()
    def estrategia_1448(    df): return     df_switzerland2[(vars_dict['VAR27'] >= 1.7274) & (vars_dict['VAR27'] <= 1.776)].copy()
    def estrategia_1449(    df): return     df_switzerland2[(vars_dict['VAR46'] >= 0.9261) & (vars_dict['VAR46'] <= 0.9768)].copy()
    def estrategia_1450(    df): return     df_switzerland2[(vars_dict['VAR44'] >= 1.0238) & (vars_dict['VAR44'] <= 1.0798)].copy()
    def estrategia_1451(    df): return     df_switzerland2[(vars_dict['VAR67'] >= -1.6556) & (vars_dict['VAR67'] <= -0.5273)].copy()
    def estrategia_1452(    df): return     df_switzerland2[(vars_dict['VAR77'] >= 0.4691) & (vars_dict['VAR77'] <= 0.6193)].copy()
    def estrategia_1453(    df): return     df_switzerland2[(vars_dict['VAR76'] >= 0.1798) & (vars_dict['VAR76'] <= 0.2844)].copy()
    def estrategia_1454(    df): return     df_switzerland2[(vars_dict['VAR45'] >= 1.1798) & (vars_dict['VAR45'] <= 1.2844)].copy()
    def estrategia_1455(    df): return     df_switzerland2[(vars_dict['VAR48'] >= 0.7786) & (vars_dict['VAR48'] <= 0.8476)].copy()
    def estrategia_1456(    df): return     df_switzerland2[(vars_dict['VAR60'] >= 0.1182) & (vars_dict['VAR60'] <= 0.1739)].copy()
    def estrategia_1457(    df): return     df_switzerland2[(vars_dict['VAR32'] >= 1.6032) & (vars_dict['VAR32'] <= 1.6768)].copy()
    def estrategia_1458(    df): return     df_switzerland2[(vars_dict['VAR64'] >= 2.8247) & (vars_dict['VAR64'] <= 4.4206)].copy()
    def estrategia_1459(    df): return     df_switzerland2[(vars_dict['VAR68'] >= -4.9701) & (vars_dict['VAR68'] <= -3.3811)].copy()
    def estrategia_1460(    df): return     df_switzerland2[(vars_dict['VAR31'] >= 2.2481) & (vars_dict['VAR31'] <= 2.4282)].copy()


    # Teste com Ligas "TURKEY 1"
    df_turkey1 =     df[    df['League'] == "TURKEY 1"].copy()
    def estrategia_1461(    df): return     df_turkey1[(vars_dict['VAR08'] >= 1.0532) & (vars_dict['VAR08'] <= 1.1389)].copy()
    def estrategia_1462(    df): return     df_turkey1[(vars_dict['VAR65'] >= 0.7696) & (vars_dict['VAR65'] <= 1.9402)].copy()
    def estrategia_1463(    df): return     df_turkey1[(vars_dict['VAR16'] >= 0.4159) & (vars_dict['VAR16'] <= 0.4667)].copy()
    def estrategia_1464(    df): return     df_turkey1[(vars_dict['VAR39'] >= 4.2735) & (vars_dict['VAR39'] <= 6.3636)].copy()
    def estrategia_1465(    df): return     df_turkey1[(vars_dict['VAR45'] >= 0.9661) & (vars_dict['VAR45'] <= 0.9774)].copy()
    def estrategia_1466(    df): return     df_turkey1[(vars_dict['VAR27'] >= 1.3553) & (vars_dict['VAR27'] <= 1.4307)].copy()
    def estrategia_1467(    df): return     df_turkey1[(vars_dict['VAR60'] >= 0.021) & (vars_dict['VAR60'] <= 0.0297)].copy()
    def estrategia_1468(    df): return     df_turkey1[(vars_dict['VAR57'] >= 0.0405) & (vars_dict['VAR57'] <= 0.0678)].copy()
    def estrategia_1469(    df): return     df_turkey1[(vars_dict['VAR13'] >= 0.2092) & (vars_dict['VAR13'] <= 0.3465)].copy()
    def estrategia_1470(    df): return     df_turkey1[(vars_dict['VAR38'] >= 3.3898) & (vars_dict['VAR38'] <= 4.6101)].copy()
    def estrategia_1471(    df): return     df_turkey1[(vars_dict['VAR36'] >= 0.6639) & (vars_dict['VAR36'] <= 0.8887)].copy()
    def estrategia_1472(    df): return     df_turkey1[(vars_dict['VAR58'] >= 0.032) & (vars_dict['VAR58'] <= 0.078)].copy()
    def estrategia_1473(    df): return     df_turkey1[(vars_dict['VAR14'] >= 0.4873) & (vars_dict['VAR14'] <= 0.6236)].copy()
    def estrategia_1474(    df): return     df_turkey1[(vars_dict['VAR69'] >= 11.3142) & (vars_dict['VAR69'] <= 15.7744)].copy()
    def estrategia_1475(    df): return     df_turkey1[(vars_dict['VAR25'] >= 4.0432) & (vars_dict['VAR25'] <= 6.0144)].copy()
    def estrategia_1476(    df): return     df_turkey1[(vars_dict['VAR07'] >= 0.878) & (vars_dict['VAR07'] <= 0.9495)].copy()
    def estrategia_1477(    df): return     df_turkey1[(vars_dict['VAR44'] >= 1.8013) & (vars_dict['VAR44'] <= 2.3932)].copy()
    def estrategia_1478(    df): return     df_turkey1[(vars_dict['VAR67'] >= -13.9582) & (vars_dict['VAR67'] <= -10.2133)].copy()
    def estrategia_1479(    df): return     df_turkey1[(vars_dict['VAR46'] >= 0.4184) & (vars_dict['VAR46'] <= 0.5552)].copy()
    def estrategia_1480(    df): return     df_turkey1[(vars_dict['VAR75'] >= 0.8013) & (vars_dict['VAR75'] <= 1.3932)].copy()


    # Teste com Ligas "TURKEY 2"
    df_turkey2 =     df[    df['League'] == "TURKEY 2"].copy()
    def estrategia_1481(    df): return     df_turkey2[(vars_dict['VAR36'] >= 1.2733) & (vars_dict['VAR36'] <= 1.3333)].copy()
    def estrategia_1482(    df): return     df_turkey2[(vars_dict['VAR31'] >= 2.1429) & (vars_dict['VAR31'] <= 2.3214)].copy()
    def estrategia_1483(    df): return     df_turkey2[(vars_dict['VAR72'] >= 0.1667) & (vars_dict['VAR72'] <= 0.2258)].copy()
    def estrategia_1484(    df): return     df_turkey2[(vars_dict['VAR56'] >= 0.0473) & (vars_dict['VAR56'] <= 0.0595)].copy()
    def estrategia_1485(    df): return     df_turkey2[(vars_dict['VAR12'] >= 0.6774) & (vars_dict['VAR12'] <= 0.7258)].copy()
    def estrategia_1486(    df): return     df_turkey2[(vars_dict['VAR45'] >= 1.0769) & (vars_dict['VAR45'] <= 1.1544)].copy()
    def estrategia_1487(    df): return     df_turkey2[(vars_dict['VAR18'] >= 0.5903) & (vars_dict['VAR18'] <= 0.625)].copy()
    def estrategia_1488(    df): return     df_turkey2[(vars_dict['VAR39'] >= 2.7907) & (vars_dict['VAR39'] <= 3.1967)].copy()
    def estrategia_1489(    df): return     df_turkey2[(vars_dict['VAR25'] >= 2.7068) & (vars_dict['VAR25'] <= 3.0233)].copy()
    def estrategia_1490(    df): return     df_turkey2[(vars_dict['VAR08'] >= 1.1714) & (vars_dict['VAR08'] <= 1.2353)].copy()
    def estrategia_1491(    df): return     df_turkey2[(vars_dict['VAR65'] >= 2.3942) & (vars_dict['VAR65'] <= 3.2065)].copy()
    def estrategia_1492(    df): return     df_turkey2[(vars_dict['VAR27'] >= 1.1912) & (vars_dict['VAR27'] <= 1.25)].copy()
    def estrategia_1493(    df): return     df_turkey2[(vars_dict['VAR28'] >= 1.3456) & (vars_dict['VAR28'] <= 1.3759)].copy()
    def estrategia_1494(    df): return     df_turkey2[(vars_dict['VAR70'] >= 0.8653) & (vars_dict['VAR70'] <= 1.1658)].copy()
    def estrategia_1495(    df): return     df_turkey2[(vars_dict['VAR07'] >= 1.2844) & (vars_dict['VAR07'] <= 3.8136)].copy()
    def estrategia_1496(    df): return     df_turkey2[(vars_dict['VAR64'] >= -1.711) & (vars_dict['VAR64'] <= -1.1355)].copy()
    def estrategia_1497(    df): return     df_turkey2[(vars_dict['VAR41'] >= 1.1951) & (vars_dict['VAR41'] <= 1.25)].copy()
    def estrategia_1498(    df): return     df_turkey2[(vars_dict['VAR19'] >= 0.4616) & (vars_dict['VAR19'] <= 0.5128)].copy()
    def estrategia_1499(    df): return     df_turkey2[(vars_dict['VAR59'] >= 0.0336) & (vars_dict['VAR59'] <= 0.0549)].copy()
    def estrategia_1500(    df): return     df_turkey2[(vars_dict['VAR42'] >= 1.3008) & (vars_dict['VAR42'] <= 1.3456)].copy()


    # Teste com Ligas "UKRAINE 1"
    df_ukraine1 =     df[    df['League'] == "UKRAINE 1"].copy()
    def estrategia_1501(    df): return     df_ukraine1[(vars_dict['VAR43'] >= 1.5) & (vars_dict['VAR43'] <= 1.7227)].copy()
    def estrategia_1502(    df): return     df_ukraine1[(vars_dict['VAR06'] >= 1.3556) & (vars_dict['VAR06'] <= 1.6321)].copy()
    def estrategia_1503(    df): return     df_ukraine1[(vars_dict['VAR75'] >= 0.0732) & (vars_dict['VAR75'] <= 0.0945)].copy()
    def estrategia_1504(    df): return     df_ukraine1[(vars_dict['VAR56'] >= 0.133) & (vars_dict['VAR56'] <= 0.2009)].copy()
    def estrategia_1505(    df): return     df_ukraine1[(vars_dict['VAR04'] >= 0.6127) & (vars_dict['VAR04'] <= 0.7377)].copy()
    def estrategia_1506(    df): return     df_ukraine1[(vars_dict['VAR27'] >= 1.3983) & (vars_dict['VAR27'] <= 1.5798)].copy()
    def estrategia_1507(    df): return     df_ukraine1[(vars_dict['VAR22'] >= 0.7659) & (vars_dict['VAR22'] <= 0.8808)].copy()
    def estrategia_1508(    df): return     df_ukraine1[(vars_dict['VAR15'] >= 0.5122) & (vars_dict['VAR15'] <= 0.5246)].copy()
    def estrategia_1509(    df): return     df_ukraine1[(vars_dict['VAR41'] >= 1.4583) & (vars_dict['VAR41'] <= 1.7905)].copy()
    def estrategia_1510(    df): return     df_ukraine1[(vars_dict['VAR62'] >= 3.633) & (vars_dict['VAR62'] <= 7.3617)].copy()
    def estrategia_1511(    df): return     df_ukraine1[(vars_dict['VAR23'] >= 2.3664) & (vars_dict['VAR23'] <= 2.9845)].copy()
    def estrategia_1512(    df): return     df_ukraine1[(vars_dict['VAR05'] >= 1.3964) & (vars_dict['VAR05'] <= 1.9948)].copy()
    def estrategia_1513(    df): return     df_ukraine1[(vars_dict['VAR09'] >= 0.9727) & (vars_dict['VAR09'] <= 1.0571)].copy()
    def estrategia_1514(    df): return     df_ukraine1[(vars_dict['VAR40'] >= 1.1543) & (vars_dict['VAR40'] <= 1.3231)].copy()
    def estrategia_1515(    df): return     df_ukraine1[(vars_dict['VAR17'] >= 0.4961) & (vars_dict['VAR17'] <= 0.5873)].copy()
    def estrategia_1516(    df): return     df_ukraine1[(vars_dict['VAR02'] >= 0.5013) & (vars_dict['VAR02'] <= 0.7161)].copy()
    def estrategia_1517(    df): return     df_ukraine1[(vars_dict['VAR12'] >= 0.7965) & (vars_dict['VAR12'] <= 0.8876)].copy()
    def estrategia_1518(    df): return     df_ukraine1[(vars_dict['VAR26'] >= 1.5682) & (vars_dict['VAR26'] <= 1.6098)].copy()
    def estrategia_1519(    df): return     df_ukraine1[(vars_dict['VAR59'] >= 0.0454) & (vars_dict['VAR59'] <= 0.0618)].copy()
    def estrategia_1520(    df): return     df_ukraine1[(vars_dict['VAR34'] >= 1.1746) & (vars_dict['VAR34'] <= 1.2931)].copy()


    # Teste com Ligas "URUGUAY 1"
    df_uruguay1 =     df[    df['League'] == "URUGUAY 1"].copy()
    def estrategia_1521(    df): return     df_uruguay1[(vars_dict['VAR73'] >= 0.28) & (vars_dict['VAR73'] <= 0.3319)].copy()
    def estrategia_1522(    df): return     df_uruguay1[(vars_dict['VAR12'] >= 0.7121) & (vars_dict['VAR12'] <= 0.75)].copy()
    def estrategia_1523(    df): return     df_uruguay1[(vars_dict['VAR60'] >= 0.0174) & (vars_dict['VAR60'] <= 0.0233)].copy()
    def estrategia_1524(    df): return     df_uruguay1[(vars_dict['VAR64'] >= -0.9258) & (vars_dict['VAR64'] <= -0.308)].copy()
    def estrategia_1525(    df): return     df_uruguay1[(vars_dict['VAR63'] >= 1.5852) & (vars_dict['VAR63'] <= 4.1552)].copy()
    def estrategia_1526(    df): return     df_uruguay1[(vars_dict['VAR03'] >= 1.2138) & (vars_dict['VAR03'] <= 2.4444)].copy()
    def estrategia_1527(    df): return     df_uruguay1[(vars_dict['VAR01'] >= 0.4091) & (vars_dict['VAR01'] <= 0.8239)].copy()
    def estrategia_1528(    df): return     df_uruguay1[(vars_dict['VAR20'] >= 0.1273) & (vars_dict['VAR20'] <= 0.4309)].copy()
    def estrategia_1529(    df): return     df_uruguay1[(vars_dict['VAR38'] >= 1.3846) & (vars_dict['VAR38'] <= 1.7872)].copy()
    def estrategia_1530(    df): return     df_uruguay1[(vars_dict['VAR57'] >= 0.1728) & (vars_dict['VAR57'] <= 0.1945)].copy()
    def estrategia_1531(    df): return     df_uruguay1[(vars_dict['VAR06'] >= 0.8964) & (vars_dict['VAR06'] <= 0.9677)].copy()
    def estrategia_1532(    df): return     df_uruguay1[(vars_dict['VAR43'] >= 1.2846) & (vars_dict['VAR43'] <= 1.3235)].copy()
    def estrategia_1533(    df): return     df_uruguay1[(vars_dict['VAR68'] >= 0.4751) & (vars_dict['VAR68'] <= 0.9583)].copy()
    def estrategia_1534(    df): return     df_uruguay1[(vars_dict['VAR48'] >= 1.0226) & (vars_dict['VAR48'] <= 1.0419)].copy()
    def estrategia_1535(    df): return     df_uruguay1[(vars_dict['VAR24'] >= 1.7347) & (vars_dict['VAR24'] <= 2.1765)].copy()
    def estrategia_1536(    df): return     df_uruguay1[(vars_dict['VAR37'] >= 2.2092) & (vars_dict['VAR37'] <= 3.3846)].copy()
    def estrategia_1537(    df): return     df_uruguay1[(vars_dict['VAR46'] >= 1.0684) & (vars_dict['VAR46'] <= 1.1682)].copy()
    def estrategia_1538(    df): return     df_uruguay1[(vars_dict['VAR76'] >= 0.0227) & (vars_dict['VAR76'] <= 0.0301)].copy()
    def estrategia_1539(    df): return     df_uruguay1[(vars_dict['VAR36'] >= 1.44) & (vars_dict['VAR36'] <= 1.7949)].copy()
    def estrategia_1540(    df): return     df_uruguay1[(vars_dict['VAR21'] >= 0.6061) & (vars_dict['VAR21'] <= 0.749)].copy()


    # Teste com Ligas "USA 1"
    df_usa1 =     df[    df['League'] == "USA 1"].copy()
    def estrategia_1541(    df): return     df_usa1[(vars_dict['VAR31'] >= 1.8826) & (vars_dict['VAR31'] <= 1.9479)].copy()
    def estrategia_1542(    df): return     df_usa1[(vars_dict['VAR20'] >= 0.5735) & (vars_dict['VAR20'] <= 0.8163)].copy()
    def estrategia_1543(    df): return     df_usa1[(vars_dict['VAR71'] >= 0.0294) & (vars_dict['VAR71'] <= 0.3046)].copy()
    def estrategia_1544(    df): return     df_usa1[(vars_dict['VAR03'] >= 0.7665) & (vars_dict['VAR03'] <= 1.0303)].copy()
    def estrategia_1545(    df): return     df_usa1[(vars_dict['VAR01'] >= 0.9706) & (vars_dict['VAR01'] <= 1.3046)].copy()
    def estrategia_1546(    df): return     df_usa1[(vars_dict['VAR76'] >= 0.1684) & (vars_dict['VAR76'] <= 0.5656)].copy()
    def estrategia_1547(    df): return     df_usa1[(vars_dict['VAR45'] >= 1.1684) & (vars_dict['VAR45'] <= 1.5656)].copy()
    def estrategia_1548(    df): return     df_usa1[(vars_dict['VAR60'] >= 0.1114) & (vars_dict['VAR60'] <= 0.2961)].copy()
    def estrategia_1549(    df): return     df_usa1[(vars_dict['VAR48'] >= 0.6387) & (vars_dict['VAR48'] <= 0.8559)].copy()
    def estrategia_1550(    df): return     df_usa1[(vars_dict['VAR56'] >= 0.1176) & (vars_dict['VAR56'] <= 0.3084)].copy()
    def estrategia_1551(    df): return     df_usa1[(vars_dict['VAR64'] >= 3.3653) & (vars_dict['VAR64'] <= 8.7646)].copy()
    def estrategia_1552(    df): return     df_usa1[(vars_dict['VAR68'] >= -8.4218) & (vars_dict['VAR68'] <= -3.1872)].copy()
    def estrategia_1553(    df): return     df_usa1[(vars_dict['VAR14'] >= 0.5235) & (vars_dict['VAR14'] <= 0.7609)].copy()
    def estrategia_1554(    df): return     df_usa1[(vars_dict['VAR75'] >= 0.0) & (vars_dict['VAR75'] <= 0.1163)].copy()
    def estrategia_1555(    df): return     df_usa1[(vars_dict['VAR44'] >= 0.9774) & (vars_dict['VAR44'] <= 1.1163)].copy()
    def estrategia_1556(    df): return     df_usa1[(vars_dict['VAR17'] >= 0.384) & (vars_dict['VAR17'] <= 0.5808)].copy()
    def estrategia_1557(    df): return     df_usa1[(vars_dict['VAR06'] >= 1.4286) & (vars_dict['VAR06'] <= 2.2951)].copy()
    def estrategia_1558(    df): return     df_usa1[(vars_dict['VAR46'] >= 0.8958) & (vars_dict['VAR46'] <= 1.0231)].copy()
    def estrategia_1559(    df): return     df_usa1[(vars_dict['VAR72'] >= 0.3076) & (vars_dict['VAR72'] <= 0.3857)].copy()
    def estrategia_1560(    df): return     df_usa1[(vars_dict['VAR63'] >= -2.5666) & (vars_dict['VAR63'] <= 0.2553)].copy()


    # Teste com Ligas "VENEZUELA 1"
    df_venezuela1 =     df[    df['League'] == "VENEZUELA 1"].copy()
    def estrategia_1561(    df): return     df_venezuela1[(vars_dict['VAR72'] >= 0.0856) & (vars_dict['VAR72'] <= 0.1253)].copy()
    def estrategia_1562(    df): return     df_venezuela1[(vars_dict['VAR32'] >= 2.1679) & (vars_dict['VAR32'] <= 2.3275)].copy()
    def estrategia_1563(    df): return     df_venezuela1[(vars_dict['VAR20'] >= 0.9198) & (vars_dict['VAR20'] <= 0.9839)].copy()
    def estrategia_1564(    df): return     df_venezuela1[(vars_dict['VAR33'] >= 1.0) & (vars_dict['VAR33'] <= 1.0996)].copy()
    def estrategia_1565(    df): return     df_venezuela1[(vars_dict['VAR55'] >= 0.064) & (vars_dict['VAR55'] <= 0.086)].copy()
    def estrategia_1566(    df): return     df_venezuela1[(vars_dict['VAR71'] >= 0.1857) & (vars_dict['VAR71'] <= 0.2593)].copy()
    def estrategia_1567(    df): return     df_venezuela1[(vars_dict['VAR41'] >= 1.3246) & (vars_dict['VAR41'] <= 1.3953)].copy()
    def estrategia_1568(    df): return     df_venezuela1[(vars_dict['VAR14'] >= 0.6391) & (vars_dict['VAR14'] <= 0.7064)].copy()
    def estrategia_1569(    df): return     df_venezuela1[(vars_dict['VAR35'] >= 0.9396) & (vars_dict['VAR35'] <= 1.0071)].copy()
    def estrategia_1570(    df): return     df_venezuela1[(vars_dict['VAR28'] >= 1.313) & (vars_dict['VAR28'] <= 1.3456)].copy()
    def estrategia_1571(    df): return     df_venezuela1[(vars_dict['VAR30'] >= 1.5817) & (vars_dict['VAR30'] <= 1.7619)].copy()
    def estrategia_1572(    df): return     df_venezuela1[(vars_dict['VAR06'] >= 0.6941) & (vars_dict['VAR06'] <= 0.7899)].copy()
    def estrategia_1573(    df): return     df_venezuela1[(vars_dict['VAR04'] >= 1.266) & (vars_dict['VAR04'] <= 1.4407)].copy()
    def estrategia_1574(    df): return     df_venezuela1[(vars_dict['VAR15'] >= 0.5618) & (vars_dict['VAR15'] <= 0.623)].copy()
    def estrategia_1575(    df): return     df_venezuela1[(vars_dict['VAR76'] >= 0.0909) & (vars_dict['VAR76'] <= 0.1077)].copy()
    def estrategia_1576(    df): return     df_venezuela1[(vars_dict['VAR13'] >= 0.4251) & (vars_dict['VAR13'] <= 0.5106)].copy()
    def estrategia_1577(    df): return     df_venezuela1[(vars_dict['VAR42'] >= 1.2919) & (vars_dict['VAR42'] <= 1.3642)].copy()
    def estrategia_1578(    df): return     df_venezuela1[(vars_dict['VAR16'] >= 0.6227) & (vars_dict['VAR16'] <= 0.7104)].copy()
    def estrategia_1579(    df): return     df_venezuela1[(vars_dict['VAR38'] >= 2.1889) & (vars_dict['VAR38'] <= 2.2963)].copy()
    def estrategia_1580(    df): return     df_venezuela1[(vars_dict['VAR77'] >= 0.3205) & (vars_dict['VAR77'] <= 0.3844)].copy()


    # Teste com Ligas "WALES 1"
    df_wales1 =     df[    df['League'] == "WALES 1"].copy()
    def estrategia_1581(    df): return     df_wales1[(vars_dict['VAR58'] >= 0.0437) & (vars_dict['VAR58'] <= 0.0609)].copy()
    def estrategia_1582(    df): return     df_wales1[(vars_dict['VAR74'] >= 0.0777) & (vars_dict['VAR74'] <= 0.1148)].copy()
    def estrategia_1583(    df): return     df_wales1[(vars_dict['VAR29'] >= 1.5197) & (vars_dict['VAR29'] <= 1.5649)].copy()
    def estrategia_1584(    df): return     df_wales1[(vars_dict['VAR18'] >= 0.4127) & (vars_dict['VAR18'] <= 0.4332)].copy()
    def estrategia_1585(    df): return     df_wales1[(vars_dict['VAR33'] >= 1.371) & (vars_dict['VAR33'] <= 1.5267)].copy()
    def estrategia_1586(    df): return     df_wales1[(vars_dict['VAR24'] >= 2.9435) & (vars_dict['VAR24'] <= 3.1048)].copy()
    def estrategia_1587(    df): return     df_wales1[(vars_dict['VAR09'] >= 0.9223) & (vars_dict['VAR09'] <= 1.0)].copy()
    def estrategia_1588(    df): return     df_wales1[(vars_dict['VAR72'] >= 0.8388) & (vars_dict['VAR72'] <= 2.75)].copy()
    def estrategia_1589(    df): return     df_wales1[(vars_dict['VAR36'] >= 1.3071) & (vars_dict['VAR36'] <= 1.4062)].copy()
    def estrategia_1590(    df): return     df_wales1[(vars_dict['VAR41'] >= 0.7468) & (vars_dict['VAR41'] <= 1.0)].copy()
    def estrategia_1591(    df): return     df_wales1[(vars_dict['VAR38'] >= 1.5094) & (vars_dict['VAR38'] <= 1.8056)].copy()
    def estrategia_1592(    df): return     df_wales1[(vars_dict['VAR67'] >= 0.0) & (vars_dict['VAR67'] <= 1.2351)].copy()
    def estrategia_1593(    df): return     df_wales1[(vars_dict['VAR71'] >= 0.5493) & (vars_dict['VAR71'] <= 0.7089)].copy()
    def estrategia_1594(    df): return     df_wales1[(vars_dict['VAR13'] >= 0.9817) & (vars_dict['VAR13'] <= 1.1442)].copy()
    def estrategia_1595(    df): return     df_wales1[(vars_dict['VAR26'] >= 1.1333) & (vars_dict['VAR26'] <= 1.2037)].copy()
    def estrategia_1596(    df): return     df_wales1[(vars_dict['VAR10'] >= 0.8293) & (vars_dict['VAR10'] <= 0.8838)].copy()
    def estrategia_1597(    df): return     df_wales1[(vars_dict['VAR66'] >= -2.8747) & (vars_dict['VAR66'] <= -1.9009)].copy()
    def estrategia_1598(    df): return     df_wales1[(vars_dict['VAR07'] >= 0.9529) & (vars_dict['VAR07'] <= 1.0124)].copy()
    def estrategia_1599(    df): return     df_wales1[(vars_dict['VAR17'] >= 0.6373) & (vars_dict['VAR17'] <= 0.7252)].copy()
    def estrategia_1600(    df): return     df_wales1[(vars_dict['VAR14'] >= 0.5072) & (vars_dict['VAR14'] <= 0.6279)].copy()










    # (Ensure all strategy functions defined above use the .loc pattern)
    return [
        (estrategia_1, "Estratégia 1"), (estrategia_2, "Estratégia 2"), (estrategia_3, "Estratégia 3"), (estrategia_4, "Estratégia 4"), (estrategia_5, "Estratégia 5"), (estrategia_6, "Estratégia 6"), (estrategia_7, "Estratégia 7"), 
        (estrategia_8, "Estratégia 8"), (estrategia_9, "Estratégia 9"), (estrategia_10, "Estratégia 10"), (estrategia_11, "Estratégia 11"), (estrategia_12, "Estratégia 12"), (estrategia_13, "Estratégia 13"), (estrategia_14, "Estratégia 14"), 
        (estrategia_15, "Estratégia 15"), (estrategia_16, "Estratégia 16"), (estrategia_17, "Estratégia 17"), (estrategia_18, "Estratégia 18"), (estrategia_19, "Estratégia 19"), (estrategia_20, "Estratégia 20"), (estrategia_21, "Estratégia 21"), 
        (estrategia_22, "Estratégia 22"), (estrategia_23, "Estratégia 23"), (estrategia_24, "Estratégia 24"), (estrategia_25, "Estratégia 25"), (estrategia_26, "Estratégia 26"), (estrategia_27, "Estratégia 27"), (estrategia_28, "Estratégia 28"), 
        (estrategia_29, "Estratégia 29"), (estrategia_30, "Estratégia 30"), (estrategia_31, "Estratégia 31"), (estrategia_32, "Estratégia 32"), (estrategia_33, "Estratégia 33"), (estrategia_34, "Estratégia 34"), (estrategia_35, "Estratégia 35"), 
        (estrategia_36, "Estratégia 36"), (estrategia_37, "Estratégia 37"), (estrategia_38, "Estratégia 38"), (estrategia_39, "Estratégia 39"), (estrategia_40, "Estratégia 40"), (estrategia_41, "Estratégia 41"), (estrategia_42, "Estratégia 42"), 
        (estrategia_43, "Estratégia 43"), (estrategia_44, "Estratégia 44"), (estrategia_45, "Estratégia 45"), (estrategia_46, "Estratégia 46"), (estrategia_47, "Estratégia 47"), (estrategia_48, "Estratégia 48"), (estrategia_49, "Estratégia 49"), 
        (estrategia_50, "Estratégia 50"), (estrategia_51, "Estratégia 51"), (estrategia_52, "Estratégia 52"), (estrategia_53, "Estratégia 53"), (estrategia_54, "Estratégia 54"), (estrategia_55, "Estratégia 55"), (estrategia_56, "Estratégia 56"), 
        (estrategia_57, "Estratégia 57"), (estrategia_58, "Estratégia 58"), (estrategia_59, "Estratégia 59"), (estrategia_60, "Estratégia 60"), (estrategia_61, "Estratégia 61"), (estrategia_62, "Estratégia 62"), (estrategia_63, "Estratégia 63"), 
        (estrategia_64, "Estratégia 64"), (estrategia_65, "Estratégia 65"), (estrategia_66, "Estratégia 66"), (estrategia_67, "Estratégia 67"), (estrategia_68, "Estratégia 68"), (estrategia_69, "Estratégia 69"), (estrategia_70, "Estratégia 70"), 
        (estrategia_71, "Estratégia 71"), (estrategia_72, "Estratégia 72"), (estrategia_73, "Estratégia 73"), (estrategia_74, "Estratégia 74"), (estrategia_75, "Estratégia 75"), (estrategia_76, "Estratégia 76"), (estrategia_77, "Estratégia 77"), (estrategia_78, "Estratégia 78"), (estrategia_79, "Estratégia 79"), 
        (estrategia_80, "Estratégia 80"), (estrategia_81, "Estratégia 81"), (estrategia_82, "Estratégia 82"), (estrategia_83, "Estratégia 83"), (estrategia_84, "Estratégia 84"), (estrategia_85, "Estratégia 85"), (estrategia_86, "Estratégia 86"), 
        (estrategia_87, "Estratégia 87"), (estrategia_88, "Estratégia 88"), (estrategia_89, "Estratégia 89"), (estrategia_90, "Estratégia 90"), (estrategia_91, "Estratégia 91"), (estrategia_92, "Estratégia 92"), (estrategia_93, "Estratégia 93"), 
        (estrategia_94, "Estratégia 94"), (estrategia_95, "Estratégia 95"), (estrategia_96, "Estratégia 96"), (estrategia_97, "Estratégia 97"), (estrategia_98, "Estratégia 98"), (estrategia_99, "Estratégia 99"), (estrategia_100, "Estratégia 100"), 
        (estrategia_101, "Estratégia 101"), (estrategia_102, "Estratégia 102"), (estrategia_103, "Estratégia 103"), (estrategia_104, "Estratégia 104"), (estrategia_105, "Estratégia 105"), (estrategia_106, "Estratégia 106"), (estrategia_107, "Estratégia 107"), 
        (estrategia_108, "Estratégia 108"), (estrategia_109, "Estratégia 109"), (estrategia_110, "Estratégia 110"), (estrategia_111, "Estratégia 111"), (estrategia_112, "Estratégia 112"), (estrategia_113, "Estratégia 113"), (estrategia_114, "Estratégia 114"), 
        (estrategia_115, "Estratégia 115"), (estrategia_116, "Estratégia 116"), (estrategia_117, "Estratégia 117"), (estrategia_118, "Estratégia 118"), (estrategia_119, "Estratégia 119"), (estrategia_120, "Estratégia 120"), (estrategia_121, "Estratégia 121"), 
        (estrategia_122, "Estratégia 122"), (estrategia_123, "Estratégia 123"), (estrategia_124, "Estratégia 124"), (estrategia_125, "Estratégia 125"), (estrategia_126, "Estratégia 126"), (estrategia_127, "Estratégia 127"), (estrategia_128, "Estratégia 128"), 
        (estrategia_129, "Estratégia 129"), (estrategia_130, "Estratégia 130"), (estrategia_131, "Estratégia 131"), (estrategia_132, "Estratégia 132"), (estrategia_133, "Estratégia 133"), (estrategia_134, "Estratégia 134"), (estrategia_135, "Estratégia 135"), 
        (estrategia_136, "Estratégia 136"), (estrategia_137, "Estratégia 137"), (estrategia_138, "Estratégia 138"), (estrategia_139, "Estratégia 139"), (estrategia_140, "Estratégia 140"), (estrategia_141, "Estratégia 141"), (estrategia_142, "Estratégia 142"), 
        (estrategia_143, "Estratégia 143"), (estrategia_144, "Estratégia 144"),        (estrategia_145, "Estratégia 145"), (estrategia_146, "Estratégia 146"), (estrategia_147, "Estratégia 147"), (estrategia_148, "Estratégia 148"), (estrategia_149, "Estratégia 149"), (estrategia_150, "Estratégia 150"), (estrategia_151, "Estratégia 151"), 
        (estrategia_152, "Estratégia 152"), (estrategia_153, "Estratégia 153"), (estrategia_154, "Estratégia 154"), (estrategia_155, "Estratégia 155"), (estrategia_156, "Estratégia 156"), (estrategia_157, "Estratégia 157"), (estrategia_158, "Estratégia 158"), 
        (estrategia_159, "Estratégia 159"), (estrategia_160, "Estratégia 160"), (estrategia_161, "Estratégia 161"), (estrategia_162, "Estratégia 162"), (estrategia_163, "Estratégia 163"), (estrategia_164, "Estratégia 164"), (estrategia_165, "Estratégia 165"), 
        (estrategia_166, "Estratégia 166"), (estrategia_167, "Estratégia 167"), (estrategia_168, "Estratégia 168"), (estrategia_169, "Estratégia 169"), (estrategia_170, "Estratégia 170"), (estrategia_171, "Estratégia 171"), (estrategia_172, "Estratégia 172"), 
        (estrategia_173, "Estratégia 173"), (estrategia_174, "Estratégia 174"), (estrategia_175, "Estratégia 175"), (estrategia_176, "Estratégia 176"), (estrategia_177, "Estratégia 177"), (estrategia_178, "Estratégia 178"), (estrategia_179, "Estratégia 179"), 
        (estrategia_180, "Estratégia 180"), (estrategia_181, "Estratégia 181"), (estrategia_182, "Estratégia 182"), (estrategia_183, "Estratégia 183"), (estrategia_184, "Estratégia 184"), (estrategia_185, "Estratégia 185"), (estrategia_186, "Estratégia 186"), 
        (estrategia_187, "Estratégia 187"), (estrategia_188, "Estratégia 188"), (estrategia_189, "Estratégia 189"), (estrategia_190, "Estratégia 190"), (estrategia_191, "Estratégia 191"), (estrategia_192, "Estratégia 192"), (estrategia_193, "Estratégia 193"), 
        (estrategia_194, "Estratégia 194"), (estrategia_195, "Estratégia 195"), (estrategia_196, "Estratégia 196"), (estrategia_197, "Estratégia 197"), (estrategia_198, "Estratégia 198"), (estrategia_199, "Estratégia 199"), (estrategia_200, "Estratégia 200"), 
        (estrategia_201, "Estratégia 201"), (estrategia_202, "Estratégia 202"), (estrategia_203, "Estratégia 203"), (estrategia_204, "Estratégia 204"), (estrategia_205, "Estratégia 205"), (estrategia_206, "Estratégia 206"), (estrategia_207, "Estratégia 207"), 
        (estrategia_208, "Estratégia 208"), (estrategia_209, "Estratégia 209"), (estrategia_210, "Estratégia 210"), (estrategia_211, "Estratégia 211"), (estrategia_212, "Estratégia 212"), (estrategia_213, "Estratégia 213"), (estrategia_214, "Estratégia 214"), 
        (estrategia_215, "Estratégia 215"), (estrategia_216, "Estratégia 216"),         (estrategia_217, "Estratégia 217"), (estrategia_218, "Estratégia 218"), (estrategia_219, "Estratégia 219"), (estrategia_220, "Estratégia 220"), 
        (estrategia_221, "Estratégia 221"), (estrategia_222, "Estratégia 222"), (estrategia_223, "Estratégia 223"), (estrategia_224, "Estratégia 224"), 
        (estrategia_225, "Estratégia 225"), (estrategia_226, "Estratégia 226"), (estrategia_227, "Estratégia 227"), (estrategia_228, "Estratégia 228"), 
        (estrategia_229, "Estratégia 229"), (estrategia_230, "Estratégia 230"), (estrategia_231, "Estratégia 231"), (estrategia_232, "Estratégia 232"), 
        (estrategia_233, "Estratégia 233"), (estrategia_234, "Estratégia 234"), (estrategia_235, "Estratégia 235"), (estrategia_236, "Estratégia 236"), 
        (estrategia_237, "Estratégia 237"), (estrategia_238, "Estratégia 238"), (estrategia_239, "Estratégia 239"), (estrategia_240, "Estratégia 240"), 
        (estrategia_241, "Estratégia 241"), (estrategia_242, "Estratégia 242"), (estrategia_243, "Estratégia 243"), (estrategia_244, "Estratégia 244"), 
        (estrategia_245, "Estratégia 245"), (estrategia_246, "Estratégia 246"), (estrategia_247, "Estratégia 247"), (estrategia_248, "Estratégia 248"), 
        (estrategia_249, "Estratégia 249"), (estrategia_250, "Estratégia 250"), (estrategia_251, "Estratégia 251"), (estrategia_252, "Estratégia 252"), 
        (estrategia_253, "Estratégia 253"), (estrategia_254, "Estratégia 254"), (estrategia_255, "Estratégia 255"), (estrategia_256, "Estratégia 256"), 
        (estrategia_257, "Estratégia 257"), (estrategia_258, "Estratégia 258"), (estrategia_259, "Estratégia 259"), (estrategia_260, "Estratégia 260"), 
        (estrategia_261, "Estratégia 261"), (estrategia_262, "Estratégia 262"),         (estrategia_263, "Estratégia 263"), (estrategia_264, "Estratégia 264"), (estrategia_265, "Estratégia 265"), (estrategia_266, "Estratégia 266"), 
        (estrategia_267, "Estratégia 267"), (estrategia_268, "Estratégia 268"), (estrategia_269, "Estratégia 269"), (estrategia_270, "Estratégia 270"), 
        (estrategia_271, "Estratégia 271"), (estrategia_272, "Estratégia 272"), (estrategia_273, "Estratégia 273"), (estrategia_274, "Estratégia 274"), 
        (estrategia_275, "Estratégia 275"), (estrategia_276, "Estratégia 276"), (estrategia_277, "Estratégia 277"), (estrategia_278, "Estratégia 278"), 
        (estrategia_279, "Estratégia 279"), (estrategia_280, "Estratégia 280"), (estrategia_281, "Estratégia 281"), (estrategia_282, "Estratégia 282"), 
        (estrategia_283, "Estratégia 283"), (estrategia_284, "Estratégia 284"), (estrategia_285, "Estratégia 285"), (estrategia_286, "Estratégia 286"), 
        (estrategia_287, "Estratégia 287"), (estrategia_288, "Estratégia 288"), (estrategia_289, "Estratégia 289"), (estrategia_290, "Estratégia 290"), 
        (estrategia_291, "Estratégia 291"), (estrategia_292, "Estratégia 292"), (estrategia_293, "Estratégia 293"), (estrategia_294, "Estratégia 294"), 
        (estrategia_295, "Estratégia 295"), (estrategia_296, "Estratégia 296"), (estrategia_297, "Estratégia 297"), (estrategia_298, "Estratégia 298"), 
        (estrategia_299, "Estratégia 299"), (estrategia_300, "Estratégia 300"), (estrategia_301, "Estratégia 301"), (estrategia_302, "Estratégia 302"), 
        (estrategia_303, "Estratégia 303"), (estrategia_304, "Estratégia 304"), (estrategia_305, "Estratégia 305"), (estrategia_306, "Estratégia 306"), 
        (estrategia_307, "Estratégia 307"), (estrategia_308, "Estratégia 308"), (estrategia_309, "Estratégia 309"), (estrategia_310, "Estratégia 310"), 
        (estrategia_311, "Estratégia 311"), (estrategia_312, "Estratégia 312"), (estrategia_313, "Estratégia 313"), (estrategia_314, "Estratégia 314"), 
        (estrategia_315, "Estratégia 315"), (estrategia_316, "Estratégia 316"), (estrategia_317, "Estratégia 317"), (estrategia_318, "Estratégia 318"), 
        (estrategia_319, "Estratégia 319"), (estrategia_320, "Estratégia 320"), (estrategia_321, "Estratégia 321"), (estrategia_322, "Estratégia 322"), 
        (estrategia_323, "Estratégia 323"), (estrategia_324, "Estratégia 324"), (estrategia_325, "Estratégia 325"), (estrategia_326, "Estratégia 326"), 
        (estrategia_327, "Estratégia 327"), (estrategia_328, "Estratégia 328"), (estrategia_329, "Estratégia 329"), (estrategia_330, "Estratégia 330"), 
        (estrategia_331, "Estratégia 331"), (estrategia_332, "Estratégia 332"), (estrategia_333, "Estratégia 333"), (estrategia_334, "Estratégia 334"),        (estrategia_335, "Estratégia 335"), (estrategia_336, "Estratégia 336"), (estrategia_337, "Estratégia 337"), (estrategia_338, "Estratégia 338"), 
        (estrategia_339, "Estratégia 339"), (estrategia_340, "Estratégia 340"), (estrategia_341, "Estratégia 341"), (estrategia_342, "Estratégia 342"), 
        (estrategia_343, "Estratégia 343"), (estrategia_344, "Estratégia 344"), (estrategia_345, "Estratégia 345"), (estrategia_346, "Estratégia 346"), 
        (estrategia_347, "Estratégia 347"), (estrategia_348, "Estratégia 348"), (estrategia_349, "Estratégia 349"), (estrategia_350, "Estratégia 350"), 
        (estrategia_351, "Estratégia 351"), (estrategia_352, "Estratégia 352"), (estrategia_353, "Estratégia 353"), (estrategia_354, "Estratégia 354"), 
        (estrategia_355, "Estratégia 355"), (estrategia_356, "Estratégia 356"), (estrategia_357, "Estratégia 357"), (estrategia_358, "Estratégia 358"), 
        (estrategia_359, "Estratégia 359"), (estrategia_360, "Estratégia 360"), (estrategia_361, "Estratégia 361"), (estrategia_362, "Estratégia 362"), 
        (estrategia_363, "Estratégia 363"), (estrategia_364, "Estratégia 364"), (estrategia_365, "Estratégia 365"), (estrategia_366, "Estratégia 366"), 
        (estrategia_367, "Estratégia 367"), (estrategia_368, "Estratégia 368"), (estrategia_369, "Estratégia 369"), (estrategia_370, "Estratégia 370"), 
        (estrategia_371, "Estratégia 371"), (estrategia_372, "Estratégia 372"), (estrategia_373, "Estratégia 373"), (estrategia_374, "Estratégia 374"), 
        (estrategia_375, "Estratégia 375"), (estrategia_376, "Estratégia 376"), (estrategia_377, "Estratégia 377"), (estrategia_378, "Estratégia 378"), 
        (estrategia_379, "Estratégia 379"), (estrategia_380, "Estratégia 380"), (estrategia_381, "Estratégia 381"), (estrategia_382, "Estratégia 382"), 
        (estrategia_383, "Estratégia 383"), (estrategia_384, "Estratégia 384"), (estrategia_385, "Estratégia 385"), (estrategia_386, "Estratégia 386"), 
        (estrategia_387, "Estratégia 387"), (estrategia_388, "Estratégia 388"), (estrategia_389, "Estratégia 389"), (estrategia_390, "Estratégia 390"), 
        (estrategia_391, "Estratégia 391"), (estrategia_392, "Estratégia 392"), (estrategia_393, "Estratégia 393"), (estrategia_394, "Estratégia 394"), 
        (estrategia_395, "Estratégia 395"), (estrategia_396, "Estratégia 396"), (estrategia_397, "Estratégia 397"), (estrategia_398, "Estratégia 398"), 
        (estrategia_399, "Estratégia 399"), (estrategia_400, "Estratégia 400"), (estrategia_401, "Estratégia 401"), (estrategia_402, "Estratégia 402"), 
        (estrategia_403, "Estratégia 403"), (estrategia_404, "Estratégia 404"), (estrategia_405, "Estratégia 405"), (estrategia_406, "Estratégia 406"),        (estrategia_407, "Estratégia 407"), (estrategia_408, "Estratégia 408"), (estrategia_409, "Estratégia 409"), (estrategia_410, "Estratégia 410"), 
        (estrategia_411, "Estratégia 411"), (estrategia_412, "Estratégia 412"), (estrategia_413, "Estratégia 413"), (estrategia_414, "Estratégia 414"), 
        (estrategia_415, "Estratégia 415"), (estrategia_416, "Estratégia 416"), (estrategia_417, "Estratégia 417"), (estrategia_418, "Estratégia 418"), 
        (estrategia_419, "Estratégia 419"), (estrategia_420, "Estratégia 420"), (estrategia_421, "Estratégia 421"), (estrategia_422, "Estratégia 422"), 
        (estrategia_423, "Estratégia 423"), (estrategia_424, "Estratégia 424"), (estrategia_425, "Estratégia 425"), (estrategia_426, "Estratégia 426"), 
        (estrategia_427, "Estratégia 427"), (estrategia_428, "Estratégia 428"), (estrategia_429, "Estratégia 429"), (estrategia_430, "Estratégia 430"), 
        (estrategia_431, "Estratégia 431"), (estrategia_432, "Estratégia 432"), (estrategia_433, "Estratégia 433"), (estrategia_434, "Estratégia 434"), 
        (estrategia_435, "Estratégia 435"), (estrategia_436, "Estratégia 436"), (estrategia_437, "Estratégia 437"), (estrategia_438, "Estratégia 438"), 
        (estrategia_439, "Estratégia 439"), (estrategia_440, "Estratégia 440"), (estrategia_441, "Estratégia 441"), (estrategia_442, "Estratégia 442"), 
        (estrategia_443, "Estratégia 443"), (estrategia_444, "Estratégia 444"), (estrategia_445, "Estratégia 445"), (estrategia_446, "Estratégia 446"), 
        (estrategia_447, "Estratégia 447"), (estrategia_448, "Estratégia 448"), (estrategia_449, "Estratégia 449"), (estrategia_450, "Estratégia 450"), 
        (estrategia_451, "Estratégia 451"), (estrategia_452, "Estratégia 452"), (estrategia_453, "Estratégia 453"), (estrategia_454, "Estratégia 454"), 
        (estrategia_455, "Estratégia 455"), (estrategia_456, "Estratégia 456"), (estrategia_457, "Estratégia 457"), (estrategia_458, "Estratégia 458"), 
        (estrategia_459, "Estratégia 459"), (estrategia_460, "Estratégia 460"), (estrategia_461, "Estratégia 461"), (estrategia_462, "Estratégia 462"), 
        (estrategia_463, "Estratégia 463"), (estrategia_464, "Estratégia 464"), (estrategia_465, "Estratégia 465"), (estrategia_466, "Estratégia 466"), 
        (estrategia_467, "Estratégia 467"), (estrategia_468, "Estratégia 468"), (estrategia_469, "Estratégia 469"), (estrategia_470, "Estratégia 470"), 
        (estrategia_471, "Estratégia 471"), (estrategia_472, "Estratégia 472"), (estrategia_473, "Estratégia 473"), (estrategia_474, "Estratégia 474"), 
        (estrategia_475, "Estratégia 475"), (estrategia_476, "Estratégia 476"), (estrategia_477, "Estratégia 477"), (estrategia_478, "Estratégia 478"),        (estrategia_479, "Estratégia 479"), (estrategia_480, "Estratégia 480"), (estrategia_481, "Estratégia 481"), (estrategia_482, "Estratégia 482"), 
        (estrategia_483, "Estratégia 483"), (estrategia_484, "Estratégia 484"), (estrategia_485, "Estratégia 485"), (estrategia_486, "Estratégia 486"), 
        (estrategia_487, "Estratégia 487"), (estrategia_488, "Estratégia 488"), (estrategia_489, "Estratégia 489"), (estrategia_490, "Estratégia 490"), 
        (estrategia_491, "Estratégia 491"), (estrategia_492, "Estratégia 492"), (estrategia_493, "Estratégia 493"), (estrategia_494, "Estratégia 494"), 
        (estrategia_495, "Estratégia 495"), (estrategia_496, "Estratégia 496"), (estrategia_497, "Estratégia 497"), (estrategia_498, "Estratégia 498"), 
        (estrategia_499, "Estratégia 499"), (estrategia_500, "Estratégia 500"), (estrategia_501, "Estratégia 501"), (estrategia_502, "Estratégia 502"), 
        (estrategia_503, "Estratégia 503"), (estrategia_504, "Estratégia 504"), (estrategia_505, "Estratégia 505"), (estrategia_506, "Estratégia 506"), 
        (estrategia_507, "Estratégia 507"), (estrategia_508, "Estratégia 508"), (estrategia_509, "Estratégia 509"), (estrategia_510, "Estratégia 510"), 
        (estrategia_511, "Estratégia 511"), (estrategia_512, "Estratégia 512"), (estrategia_513, "Estratégia 513"), (estrategia_514, "Estratégia 514"), 
        (estrategia_515, "Estratégia 515"), (estrategia_516, "Estratégia 516"), (estrategia_517, "Estratégia 517"), (estrategia_518, "Estratégia 518"), 
        (estrategia_519, "Estratégia 519"), (estrategia_520, "Estratégia 520"), (estrategia_521, "Estratégia 521"), (estrategia_522, "Estratégia 522"), 
        (estrategia_523, "Estratégia 523"), (estrategia_524, "Estratégia 524"), (estrategia_525, "Estratégia 525"), (estrategia_526, "Estratégia 526"), 
        (estrategia_527, "Estratégia 527"), (estrategia_528, "Estratégia 528"), (estrategia_529, "Estratégia 529"), (estrategia_530, "Estratégia 530"), 
        (estrategia_531, "Estratégia 531"), (estrategia_532, "Estratégia 532"), (estrategia_533, "Estratégia 533"), (estrategia_534, "Estratégia 534"), 
        (estrategia_535, "Estratégia 535"), (estrategia_536, "Estratégia 536"), (estrategia_537, "Estratégia 537"), (estrategia_538, "Estratégia 538"), 
        (estrategia_539, "Estratégia 539"), (estrategia_540, "Estratégia 540"), (estrategia_541, "Estratégia 541"), (estrategia_542, "Estratégia 542"), 
        (estrategia_543, "Estratégia 543"), (estrategia_544, "Estratégia 544"), (estrategia_545, "Estratégia 545"), (estrategia_546, "Estratégia 546"), 
        (estrategia_547, "Estratégia 547"), (estrategia_548, "Estratégia 548"), (estrategia_549, "Estratégia 549"), (estrategia_550, "Estratégia 550"),         (estrategia_551, "Estratégia 551"), (estrategia_552, "Estratégia 552"), (estrategia_553, "Estratégia 553"), (estrategia_554, "Estratégia 554"), 
        (estrategia_555, "Estratégia 555"), (estrategia_556, "Estratégia 556"), (estrategia_557, "Estratégia 557"), (estrategia_558, "Estratégia 558"), 
        (estrategia_559, "Estratégia 559"), (estrategia_560, "Estratégia 560"), (estrategia_561, "Estratégia 561"), (estrategia_562, "Estratégia 562"), 
        (estrategia_563, "Estratégia 563"), (estrategia_564, "Estratégia 564"), (estrategia_565, "Estratégia 565"), (estrategia_566, "Estratégia 566"), 
        (estrategia_567, "Estratégia 567"), (estrategia_568, "Estratégia 568"), (estrategia_569, "Estratégia 569"), (estrategia_570, "Estratégia 570"), 
        (estrategia_571, "Estratégia 571"), (estrategia_572, "Estratégia 572"), (estrategia_573, "Estratégia 573"), (estrategia_574, "Estratégia 574"), 
        (estrategia_575, "Estratégia 575"), (estrategia_576, "Estratégia 576"), (estrategia_577, "Estratégia 577"), (estrategia_578, "Estratégia 578"), 
        (estrategia_579, "Estratégia 579"), (estrategia_580, "Estratégia 580"), (estrategia_581, "Estratégia 581"), (estrategia_582, "Estratégia 582"), 
        (estrategia_583, "Estratégia 583"), (estrategia_584, "Estratégia 584"), (estrategia_585, "Estratégia 585"), (estrategia_586, "Estratégia 586"), 
        (estrategia_587, "Estratégia 587"), (estrategia_588, "Estratégia 588"), (estrategia_589, "Estratégia 589"), (estrategia_590, "Estratégia 590"), 
        (estrategia_591, "Estratégia 591"), (estrategia_592, "Estratégia 592"), (estrategia_593, "Estratégia 593"), (estrategia_594, "Estratégia 594"), 
        (estrategia_595, "Estratégia 595"), (estrategia_596, "Estratégia 596"), (estrategia_597, "Estratégia 597"), (estrategia_598, "Estratégia 598"), 
        (estrategia_599, "Estratégia 599"), (estrategia_600, "Estratégia 600"), (estrategia_601, "Estratégia 601"), (estrategia_602, "Estratégia 602"), 
        (estrategia_603, "Estratégia 603"), (estrategia_604, "Estratégia 604"), (estrategia_605, "Estratégia 605"), (estrategia_606, "Estratégia 606"), 
        (estrategia_607, "Estratégia 607"), (estrategia_608, "Estratégia 608"), (estrategia_609, "Estratégia 609"), (estrategia_610, "Estratégia 610"), 
        (estrategia_611, "Estratégia 611"), (estrategia_612, "Estratégia 612"), (estrategia_613, "Estratégia 613"), (estrategia_614, "Estratégia 614"), 
        (estrategia_615, "Estratégia 615"), (estrategia_616, "Estratégia 616"), (estrategia_617, "Estratégia 617"), (estrategia_618, "Estratégia 618"), 
        (estrategia_619, "Estratégia 619"), (estrategia_620, "Estratégia 620"), (estrategia_621, "Estratégia 621"), (estrategia_622, "Estratégia 622"),         (estrategia_623, "Estratégia 623"), (estrategia_624, "Estratégia 624"), (estrategia_625, "Estratégia 625"), (estrategia_626, "Estratégia 626"), 
        (estrategia_627, "Estratégia 627"), (estrategia_628, "Estratégia 628"), (estrategia_629, "Estratégia 629"), (estrategia_630, "Estratégia 630"), 
        (estrategia_631, "Estratégia 631"), (estrategia_632, "Estratégia 632"), (estrategia_633, "Estratégia 633"), (estrategia_634, "Estratégia 634"), 
        (estrategia_635, "Estratégia 635"), (estrategia_636, "Estratégia 636"), (estrategia_637, "Estratégia 637"), (estrategia_638, "Estratégia 638"), 
        (estrategia_639, "Estratégia 639"), (estrategia_640, "Estratégia 640"), (estrategia_641, "Estratégia 641"), (estrategia_642, "Estratégia 642"), 
        (estrategia_643, "Estratégia 643"), (estrategia_644, "Estratégia 644"), (estrategia_645, "Estratégia 645"), (estrategia_646, "Estratégia 646"), 
        (estrategia_647, "Estratégia 647"), (estrategia_648, "Estratégia 648"), (estrategia_649, "Estratégia 649"), (estrategia_650, "Estratégia 650"), 
        (estrategia_651, "Estratégia 651"), (estrategia_652, "Estratégia 652"), (estrategia_653, "Estratégia 653"), (estrategia_654, "Estratégia 654"), 
        (estrategia_655, "Estratégia 655"), (estrategia_656, "Estratégia 656"), (estrategia_657, "Estratégia 657"), (estrategia_658, "Estratégia 658"), 
        (estrategia_659, "Estratégia 659"), (estrategia_660, "Estratégia 660"), (estrategia_661, "Estratégia 661"), (estrategia_662, "Estratégia 662"), 
        (estrategia_663, "Estratégia 663"), (estrategia_664, "Estratégia 664"), (estrategia_665, "Estratégia 665"), (estrategia_666, "Estratégia 666"), 
        (estrategia_667, "Estratégia 667"), (estrategia_668, "Estratégia 668"), (estrategia_669, "Estratégia 669"), (estrategia_670, "Estratégia 670"), 
        (estrategia_671, "Estratégia 671"), (estrategia_672, "Estratégia 672"), (estrategia_673, "Estratégia 673"), (estrategia_674, "Estratégia 674"), 
        (estrategia_675, "Estratégia 675"), (estrategia_676, "Estratégia 676"), (estrategia_677, "Estratégia 677"), (estrategia_678, "Estratégia 678"), 
        (estrategia_679, "Estratégia 679"), (estrategia_680, "Estratégia 680"), (estrategia_681, "Estratégia 681"), (estrategia_682, "Estratégia 682"), 
        (estrategia_683, "Estratégia 683"), (estrategia_684, "Estratégia 684"), (estrategia_685, "Estratégia 685"), (estrategia_686, "Estratégia 686"), 
        (estrategia_687, "Estratégia 687"), (estrategia_688, "Estratégia 688"), (estrategia_689, "Estratégia 689"), (estrategia_690, "Estratégia 690"), 
        (estrategia_691, "Estratégia 691"), (estrategia_692, "Estratégia 692"), (estrategia_693, "Estratégia 693"), (estrategia_694, "Estratégia 694"), (estrategia_695, "Estratégia 695"), (estrategia_696, "Estratégia 696"), (estrategia_697, "Estratégia 697"), (estrategia_698, "Estratégia 698"), 
        (estrategia_699, "Estratégia 699"), (estrategia_700, "Estratégia 700"), (estrategia_701, "Estratégia 701"), (estrategia_702, "Estratégia 702"), 
        (estrategia_703, "Estratégia 703"), (estrategia_704, "Estratégia 704"), (estrategia_705, "Estratégia 705"), (estrategia_706, "Estratégia 706"), 
        (estrategia_707, "Estratégia 707"), (estrategia_708, "Estratégia 708"), (estrategia_709, "Estratégia 709"), (estrategia_710, "Estratégia 710"), 
        (estrategia_711, "Estratégia 711"), (estrategia_712, "Estratégia 712"), (estrategia_713, "Estratégia 713"), (estrategia_714, "Estratégia 714"), 
        (estrategia_715, "Estratégia 715"), (estrategia_716, "Estratégia 716"), (estrategia_717, "Estratégia 717"), (estrategia_718, "Estratégia 718"), 
        (estrategia_719, "Estratégia 719"), (estrategia_720, "Estratégia 720"), (estrategia_721, "Estratégia 721"), (estrategia_722, "Estratégia 722"), 
        (estrategia_723, "Estratégia 723"), (estrategia_724, "Estratégia 724"), (estrategia_725, "Estratégia 725"), (estrategia_726, "Estratégia 726"), 
        (estrategia_727, "Estratégia 727"), (estrategia_728, "Estratégia 728"), (estrategia_729, "Estratégia 729"), (estrategia_730, "Estratégia 730"), 
        (estrategia_731, "Estratégia 731"), (estrategia_732, "Estratégia 732"), (estrategia_733, "Estratégia 733"), (estrategia_734, "Estratégia 734"), 
        (estrategia_735, "Estratégia 735"), (estrategia_736, "Estratégia 736"), (estrategia_737, "Estratégia 737"), (estrategia_738, "Estratégia 738"), 
        (estrategia_739, "Estratégia 739"), (estrategia_740, "Estratégia 740"), (estrategia_741, "Estratégia 741"), (estrategia_742, "Estratégia 742"), 
        (estrategia_743, "Estratégia 743"), (estrategia_744, "Estratégia 744"), (estrategia_745, "Estratégia 745"), (estrategia_746, "Estratégia 746"), 
        (estrategia_747, "Estratégia 747"), (estrategia_748, "Estratégia 748"), (estrategia_749, "Estratégia 749"), (estrategia_750, "Estratégia 750"), 
        (estrategia_751, "Estratégia 751"), (estrategia_752, "Estratégia 752"), (estrategia_753, "Estratégia 753"), (estrategia_754, "Estratégia 754"), 
        (estrategia_755, "Estratégia 755"), (estrategia_756, "Estratégia 756"), (estrategia_757, "Estratégia 757"), (estrategia_758, "Estratégia 758"), 
        (estrategia_759, "Estratégia 759"), (estrategia_760, "Estratégia 760"), (estrategia_761, "Estratégia 761"), (estrategia_762, "Estratégia 762"), 
        (estrategia_763, "Estratégia 763"), (estrategia_764, "Estratégia 764"), (estrategia_765, "Estratégia 765"), (estrategia_766, "Estratégia 766"), (estrategia_767, "Estratégia 767"), (estrategia_768, "Estratégia 768"), (estrategia_769, "Estratégia 769"), (estrategia_770, "Estratégia 770"), 
        (estrategia_771, "Estratégia 771"), (estrategia_772, "Estratégia 772"), (estrategia_773, "Estratégia 773"), (estrategia_774, "Estratégia 774"), 
        (estrategia_775, "Estratégia 775"), (estrategia_776, "Estratégia 776"), (estrategia_777, "Estratégia 777"), (estrategia_778, "Estratégia 778"), 
        (estrategia_779, "Estratégia 779"), (estrategia_780, "Estratégia 780"), (estrategia_781, "Estratégia 781"), (estrategia_782, "Estratégia 782"), 
        (estrategia_783, "Estratégia 783"), (estrategia_784, "Estratégia 784"), (estrategia_785, "Estratégia 785"), (estrategia_786, "Estratégia 786"), 
        (estrategia_787, "Estratégia 787"), (estrategia_788, "Estratégia 788"), (estrategia_789, "Estratégia 789"), (estrategia_790, "Estratégia 790"), 
        (estrategia_791, "Estratégia 791"), (estrategia_792, "Estratégia 792"), (estrategia_793, "Estratégia 793"), (estrategia_794, "Estratégia 794"), 
        (estrategia_795, "Estratégia 795"), (estrategia_796, "Estratégia 796"), (estrategia_797, "Estratégia 797"), (estrategia_798, "Estratégia 798"), 
        (estrategia_799, "Estratégia 799"), (estrategia_800, "Estratégia 800"), (estrategia_801, "Estratégia 801"), (estrategia_802, "Estratégia 802"), 
        (estrategia_803, "Estratégia 803"), (estrategia_804, "Estratégia 804"), (estrategia_805, "Estratégia 805"), (estrategia_806, "Estratégia 806"), 
        (estrategia_807, "Estratégia 807"), (estrategia_808, "Estratégia 808"), (estrategia_809, "Estratégia 809"), (estrategia_810, "Estratégia 810"), 
        (estrategia_811, "Estratégia 811"), (estrategia_812, "Estratégia 812"), (estrategia_813, "Estratégia 813"), (estrategia_814, "Estratégia 814"), 
        (estrategia_815, "Estratégia 815"), (estrategia_816, "Estratégia 816"), (estrategia_817, "Estratégia 817"), (estrategia_818, "Estratégia 818"), 
        (estrategia_819, "Estratégia 819"), (estrategia_820, "Estratégia 820"), (estrategia_821, "Estratégia 821"), (estrategia_822, "Estratégia 822"), 
        (estrategia_823, "Estratégia 823"), (estrategia_824, "Estratégia 824"), (estrategia_825, "Estratégia 825"), (estrategia_826, "Estratégia 826"), 
        (estrategia_827, "Estratégia 827"), (estrategia_828, "Estratégia 828"), (estrategia_829, "Estratégia 829"), (estrategia_830, "Estratégia 830"), 
        (estrategia_831, "Estratégia 831"), (estrategia_832, "Estratégia 832"), (estrategia_833, "Estratégia 833"), (estrategia_834, "Estratégia 834"), 
        (estrategia_835, "Estratégia 835"), (estrategia_836, "Estratégia 836"), (estrategia_837, "Estratégia 837"), (estrategia_838, "Estratégia 838"),         (estrategia_839, "Estratégia 839"), (estrategia_840, "Estratégia 840"), (estrategia_841, "Estratégia 841"), (estrategia_842, "Estratégia 842"),
        (estrategia_843, "Estratégia 843"), (estrategia_844, "Estratégia 844"), (estrategia_845, "Estratégia 845"), (estrategia_846, "Estratégia 846"),
        (estrategia_847, "Estratégia 847"), (estrategia_848, "Estratégia 848"), (estrategia_849, "Estratégia 849"), (estrategia_850, "Estratégia 850"),
        (estrategia_851, "Estratégia 851"), (estrategia_852, "Estratégia 852"), (estrategia_853, "Estratégia 853"), (estrategia_854, "Estratégia 854"),
        (estrategia_855, "Estratégia 855"), (estrategia_856, "Estratégia 856"), (estrategia_857, "Estratégia 857"), (estrategia_858, "Estratégia 858"),
        (estrategia_859, "Estratégia 859"), (estrategia_860, "Estratégia 860"), (estrategia_861, "Estratégia 861"), (estrategia_862, "Estratégia 862"),
        (estrategia_863, "Estratégia 863"), (estrategia_864, "Estratégia 864"), (estrategia_865, "Estratégia 865"), (estrategia_866, "Estratégia 866"),
        (estrategia_867, "Estratégia 867"), (estrategia_868, "Estratégia 868"), (estrategia_869, "Estratégia 869"), (estrategia_870, "Estratégia 870"),
        (estrategia_871, "Estratégia 871"), (estrategia_872, "Estratégia 872"), (estrategia_873, "Estratégia 873"), (estrategia_874, "Estratégia 874"),
        (estrategia_875, "Estratégia 875"), (estrategia_876, "Estratégia 876"), (estrategia_877, "Estratégia 877"), (estrategia_878, "Estratégia 878"),
        (estrategia_879, "Estratégia 879"), (estrategia_880, "Estratégia 880"), (estrategia_881, "Estratégia 881"), (estrategia_882, "Estratégia 882"),
        (estrategia_883, "Estratégia 883"), (estrategia_884, "Estratégia 884"), (estrategia_885, "Estratégia 885"), (estrategia_886, "Estratégia 886"),
        (estrategia_887, "Estratégia 887"), (estrategia_888, "Estratégia 888"), (estrategia_889, "Estratégia 889"), (estrategia_890, "Estratégia 890"),
        (estrategia_891, "Estratégia 891"), (estrategia_892, "Estratégia 892"), (estrategia_893, "Estratégia 893"), (estrategia_894, "Estratégia 894"),
        (estrategia_895, "Estratégia 895"), (estrategia_896, "Estratégia 896"), (estrategia_897, "Estratégia 897"), (estrategia_898, "Estratégia 898"),
        (estrategia_899, "Estratégia 899"), (estrategia_900, "Estratégia 900"), (estrategia_901, "Estratégia 901"), (estrategia_902, "Estratégia 902"),
        (estrategia_903, "Estratégia 903"), (estrategia_904, "Estratégia 904"), (estrategia_905, "Estratégia 905"), (estrategia_906, "Estratégia 906"),
        (estrategia_907, "Estratégia 907"), (estrategia_908, "Estratégia 908"), (estrategia_909, "Estratégia 909"), (estrategia_910, "Estratégia 910"),
        (estrategia_911, "Estratégia 911"), (estrategia_912, "Estratégia 912"), (estrategia_913, "Estratégia 913"), (estrategia_914, "Estratégia 914"),
        (estrategia_915, "Estratégia 915"), (estrategia_916, "Estratégia 916"), (estrategia_917, "Estratégia 917"), (estrategia_918, "Estratégia 918"),
        (estrategia_919, "Estratégia 919"), (estrategia_920, "Estratégia 920"), (estrategia_921, "Estratégia 921"), (estrategia_922, "Estratégia 922"),
        (estrategia_923, "Estratégia 923"), (estrategia_924, "Estratégia 924"), (estrategia_925, "Estratégia 925"), (estrategia_926, "Estratégia 926"),
        (estrategia_927, "Estratégia 927"), (estrategia_928, "Estratégia 928"), (estrategia_929, "Estratégia 929"), (estrategia_930, "Estratégia 930"),
        (estrategia_931, "Estratégia 931"), (estrategia_932, "Estratégia 932"), (estrategia_933, "Estratégia 933"), (estrategia_934, "Estratégia 934"),
        (estrategia_935, "Estratégia 935"), (estrategia_936, "Estratégia 936"), (estrategia_937, "Estratégia 937"), (estrategia_938, "Estratégia 938"),
        (estrategia_939, "Estratégia 939"), (estrategia_940, "Estratégia 940"), (estrategia_941, "Estratégia 941"), (estrategia_942, "Estratégia 942"),
        (estrategia_943, "Estratégia 943"), (estrategia_944, "Estratégia 944"), (estrategia_945, "Estratégia 945"), (estrategia_946, "Estratégia 946"),
        (estrategia_947, "Estratégia 947"), (estrategia_948, "Estratégia 948"), (estrategia_949, "Estratégia 949"), (estrategia_950, "Estratégia 950"),
        (estrategia_951, "Estratégia 951"), (estrategia_952, "Estratégia 952"), (estrategia_953, "Estratégia 953"), (estrategia_954, "Estratégia 954"),
        (estrategia_955, "Estratégia 955"), (estrategia_956, "Estratégia 956"), (estrategia_957, "Estratégia 957"), (estrategia_958, "Estratégia 958"),
        (estrategia_959, "Estratégia 959"), (estrategia_960, "Estratégia 960"), (estrategia_961, "Estratégia 961"), (estrategia_962, "Estratégia 962"),
        (estrategia_963, "Estratégia 963"), (estrategia_964, "Estratégia 964"), (estrategia_965, "Estratégia 965"), (estrategia_966, "Estratégia 966"),
        (estrategia_967, "Estratégia 967"), (estrategia_968, "Estratégia 968"), (estrategia_969, "Estratégia 969"), (estrategia_970, "Estratégia 970"),
        (estrategia_971, "Estratégia 971"), (estrategia_972, "Estratégia 972"), (estrategia_973, "Estratégia 973"), (estrategia_974, "Estratégia 974"),
        (estrategia_975, "Estratégia 975"), (estrategia_976, "Estratégia 976"), (estrategia_977, "Estratégia 977"), (estrategia_978, "Estratégia 978"),
        (estrategia_979, "Estratégia 979"), (estrategia_980, "Estratégia 980"), (estrategia_981, "Estratégia 981"), (estrategia_982, "Estratégia 982"), (estrategia_983, "Estratégia 983"), (estrategia_984, "Estratégia 984"), (estrategia_985, "Estratégia 985"), (estrategia_986, "Estratégia 986"),
        (estrategia_987, "Estratégia 987"), (estrategia_988, "Estratégia 988"), (estrategia_989, "Estratégia 989"), (estrategia_990, "Estratégia 990"),
        (estrategia_991, "Estratégia 991"), (estrategia_992, "Estratégia 992"), (estrategia_993, "Estratégia 993"), (estrategia_994, "Estratégia 994"),
        (estrategia_995, "Estratégia 995"), (estrategia_996, "Estratégia 996"), (estrategia_997, "Estratégia 997"), (estrategia_998, "Estratégia 998"),
        (estrategia_999, "Estratégia 999"), (estrategia_1000, "Estratégia 1000"), (estrategia_1001, "Estratégia 1001"), (estrategia_1002, "Estratégia 1002"),
        (estrategia_1003, "Estratégia 1003"), (estrategia_1004, "Estratégia 1004"), (estrategia_1005, "Estratégia 1005"), (estrategia_1006, "Estratégia 1006"),
        (estrategia_1007, "Estratégia 1007"), (estrategia_1008, "Estratégia 1008"), (estrategia_1009, "Estratégia 1009"), (estrategia_1010, "Estratégia 1010"),
        (estrategia_1011, "Estratégia 1011"), (estrategia_1012, "Estratégia 1012"), (estrategia_1013, "Estratégia 1013"), (estrategia_1014, "Estratégia 1014"),
        (estrategia_1015, "Estratégia 1015"), (estrategia_1016, "Estratégia 1016"), (estrategia_1017, "Estratégia 1017"), (estrategia_1018, "Estratégia 1018"),
        (estrategia_1019, "Estratégia 1019"), (estrategia_1020, "Estratégia 1020"), (estrategia_1021, "Estratégia 1021"), (estrategia_1022, "Estratégia 1022"),
        (estrategia_1023, "Estratégia 1023"), (estrategia_1024, "Estratégia 1024"), (estrategia_1025, "Estratégia 1025"), (estrategia_1026, "Estratégia 1026"), (estrategia_1027, "Estratégia 1027"), (estrategia_1028, "Estratégia 1028"), (estrategia_1029, "Estratégia 1029"), (estrategia_1030, "Estratégia 1030"), (estrategia_1031, "Estratégia 1031"), (estrategia_1032, "Estratégia 1032"), (estrategia_1033, "Estratégia 1033"), (estrategia_1034, "Estratégia 1034"), (estrategia_1035, "Estratégia 1035"), (estrategia_1036, "Estratégia 1036"), (estrategia_1037, "Estratégia 1037"), (estrategia_1038, "Estratégia 1038"), 
        (estrategia_1039, "Estratégia 1039"), (estrategia_1040, "Estratégia 1040"), 
        (estrategia_1041, "Estratégia 1041"), (estrategia_1042, "Estratégia 1042"), (estrategia_1043, "Estratégia 1043"), (estrategia_1044, "Estratégia 1044"), (estrategia_1045, "Estratégia 1045"),
        (estrategia_1046, "Estratégia 1046"), (estrategia_1047, "Estratégia 1047"), (estrategia_1048, "Estratégia 1048"), (estrategia_1049, "Estratégia 1049"), (estrategia_1050, "Estratégia 1050"), (estrategia_1051, "Estratégia 1051"), (estrategia_1052, "Estratégia 1052"), (estrategia_1053, "Estratégia 1053"), (estrategia_1054, "Estratégia 1054"), (estrategia_1055, "Estratégia 1055"), (estrategia_1056, "Estratégia 1056"), (estrategia_1057, "Estratégia 1057"), (estrategia_1058, "Estratégia 1058"), (estrategia_1059, "Estratégia 1059"), (estrategia_1060, "Estratégia 1060"), (estrategia_1061, "Estratégia 1061"),
        (estrategia_1062, "Estratégia 1062"), (estrategia_1063, "Estratégia 1063"), (estrategia_1064, "Estratégia 1064"), (estrategia_1065, "Estratégia 1065"), (estrategia_1066, "Estratégia 1066"), (estrategia_1067, "Estratégia 1067"), (estrategia_1068, "Estratégia 1068"), (estrategia_1069, "Estratégia 1069"), (estrategia_1070, "Estratégia 1070"), (estrategia_1071, "Estratégia 1071"), (estrategia_1072, "Estratégia 1072"), (estrategia_1073, "Estratégia 1073"), (estrategia_1074, "Estratégia 1074"), (estrategia_1075, "Estratégia 1075"), (estrategia_1076, "Estratégia 1076"), (estrategia_1077, "Estratégia 1077"),
        (estrategia_1078, "Estratégia 1078"), (estrategia_1079, "Estratégia 1079"), (estrategia_1080, "Estratégia 1080"), (estrategia_1081, "Estratégia 1081"), (estrategia_1082, "Estratégia 1082"), (estrategia_1083, "Estratégia 1083"), (estrategia_1084, "Estratégia 1084"), (estrategia_1085, "Estratégia 1085"), (estrategia_1086, "Estratégia 1086"), (estrategia_1087, "Estratégia 1087"), (estrategia_1088, "Estratégia 1088"), (estrategia_1089, "Estratégia 1089"), (estrategia_1090, "Estratégia 1090"), (estrategia_1091, "Estratégia 1091"), (estrategia_1092, "Estratégia 1092"), (estrategia_1093, "Estratégia 1093"),
        (estrategia_1094, "Estratégia 1094"), (estrategia_1095, "Estratégia 1095"), (estrategia_1096, "Estratégia 1096"), (estrategia_1097, "Estratégia 1097"), (estrategia_1098, "Estratégia 1098"), (estrategia_1099, "Estratégia 1099"), (estrategia_1100, "Estratégia 1100"), (estrategia_1101, "Estratégia 1101"), (estrategia_1102, "Estratégia 1102"), (estrategia_1103, "Estratégia 1103"), (estrategia_1104, "Estratégia 1104"), (estrategia_1105, "Estratégia 1105"), (estrategia_1106, "Estratégia 1106"), (estrategia_1107, "Estratégia 1107"), (estrategia_1108, "Estratégia 1108"), (estrategia_1109, "Estratégia 1109"),
        (estrategia_1110, "Estratégia 1110"), (estrategia_1111, "Estratégia 1111"), (estrategia_1112, "Estratégia 1112"), (estrategia_1113, "Estratégia 1113"), (estrategia_1114, "Estratégia 1114"), (estrategia_1115, "Estratégia 1115"), (estrategia_1116, "Estratégia 1116"), (estrategia_1117, "Estratégia 1117"), (estrategia_1118, "Estratégia 1118"), (estrategia_1119, "Estratégia 1119"), (estrategia_1120, "Estratégia 1120"), (estrategia_1121, "Estratégia 1121"), (estrategia_1122, "Estratégia 1122"), (estrategia_1123, "Estratégia 1123"), (estrategia_1124, "Estratégia 1124"), (estrategia_1125, "Estratégia 1125"), 
        (estrategia_1126, "Estratégia 1126"), (estrategia_1127, "Estratégia 1127"), (estrategia_1128, "Estratégia 1128"), (estrategia_1129, "Estratégia 1129"), (estrategia_1130, "Estratégia 1130"), (estrategia_1131, "Estratégia 1131"), (estrategia_1132, "Estratégia 1132"), (estrategia_1133, "Estratégia 1133"), (estrategia_1134, "Estratégia 1134"), (estrategia_1135, "Estratégia 1135"), (estrategia_1136, "Estratégia 1136"), (estrategia_1137, "Estratégia 1137"), (estrategia_1138, "Estratégia 1138"), (estrategia_1139, "Estratégia 1139"), (estrategia_1140, "Estratégia 1140"), (estrategia_1141, "Estratégia 1141"), 
        (estrategia_1142, "Estratégia 1142"), (estrategia_1143, "Estratégia 1143"), (estrategia_1144, "Estratégia 1144"), (estrategia_1145, "Estratégia 1145"), (estrategia_1146, "Estratégia 1146"), (estrategia_1147, "Estratégia 1147"), (estrategia_1148, "Estratégia 1148"), (estrategia_1149, "Estratégia 1149"), (estrategia_1150, "Estratégia 1150"), (estrategia_1151, "Estratégia 1151"), (estrategia_1152, "Estratégia 1152"), (estrategia_1153, "Estratégia 1153"), (estrategia_1154, "Estratégia 1154"), (estrategia_1155, "Estratégia 1155"), (estrategia_1156, "Estratégia 1156"), (estrategia_1157, "Estratégia 1157"),
        (estrategia_1158, "Estratégia 1158"), (estrategia_1159, "Estratégia 1159"), (estrategia_1160, "Estratégia 1160"), (estrategia_1161, "Estratégia 1161"), (estrategia_1162, "Estratégia 1162"), (estrategia_1163, "Estratégia 1163"), (estrategia_1164, "Estratégia 1164"), (estrategia_1165, "Estratégia 1165"), (estrategia_1166, "Estratégia 1166"), (estrategia_1167, "Estratégia 1167"), (estrategia_1168, "Estratégia 1168"), (estrategia_1169, "Estratégia 1169"), (estrategia_1170, "Estratégia 1170"), (estrategia_1171, "Estratégia 1171"), (estrategia_1172, "Estratégia 1172"), (estrategia_1173, "Estratégia 1173"),
        (estrategia_1174, "Estratégia 1174"), (estrategia_1175, "Estratégia 1175"), (estrategia_1176, "Estratégia 1176"), (estrategia_1177, "Estratégia 1177"), (estrategia_1178, "Estratégia 1178"), (estrategia_1179, "Estratégia 1179"), (estrategia_1180, "Estratégia 1180"), (estrategia_1181, "Estratégia 1181"), (estrategia_1182, "Estratégia 1182"), (estrategia_1183, "Estratégia 1183"), (estrategia_1184, "Estratégia 1184"), (estrategia_1185, "Estratégia 1185"), (estrategia_1186, "Estratégia 1186"), (estrategia_1187, "Estratégia 1187"), (estrategia_1188, "Estratégia 1188"), (estrategia_1189, "Estratégia 1189"), 
        (estrategia_1190, "Estratégia 1190"), (estrategia_1191, "Estratégia 1191"), (estrategia_1192, "Estratégia 1192"), (estrategia_1193, "Estratégia 1193"), (estrategia_1194, "Estratégia 1194"), (estrategia_1195, "Estratégia 1195"), (estrategia_1196, "Estratégia 1196"), (estrategia_1197, "Estratégia 1197"), (estrategia_1198, "Estratégia 1198"), (estrategia_1199, "Estratégia 1199"), (estrategia_1200, "Estratégia 1200"), (estrategia_1201, "Estratégia 1201"), (estrategia_1202, "Estratégia 1202"), (estrategia_1203, "Estratégia 1203"), (estrategia_1204, "Estratégia 1204"), (estrategia_1205, "Estratégia 1205"),
        (estrategia_1206, "Estratégia 1206"), (estrategia_1207, "Estratégia 1207"), (estrategia_1208, "Estratégia 1208"), (estrategia_1209, "Estratégia 1209"), (estrategia_1210, "Estratégia 1210"), (estrategia_1211, "Estratégia 1211"), (estrategia_1212, "Estratégia 1212"), (estrategia_1213, "Estratégia 1213"), (estrategia_1214, "Estratégia 1214"), (estrategia_1215, "Estratégia 1215"), (estrategia_1216, "Estratégia 1216"), 
        (estrategia_1217, "Estratégia 1217"), (estrategia_1218, "Estratégia 1218"), (estrategia_1219, "Estratégia 1219"), (estrategia_1220, "Estratégia 1220"), (estrategia_1221, "Estratégia 1221"),
        (estrategia_1222, "Estratégia 1222"), (estrategia_1223, "Estratégia 1223"), (estrategia_1224, "Estratégia 1224"), (estrategia_1225, "Estratégia 1225"), (estrategia_1226, "Estratégia 1226"), (estrategia_1227, "Estratégia 1227"), (estrategia_1228, "Estratégia 1228"), (estrategia_1229, "Estratégia 1229"), (estrategia_1230, "Estratégia 1230"), (estrategia_1231, "Estratégia 1231"), (estrategia_1232, "Estratégia 1232"), 
        (estrategia_1233, "Estratégia 1233"), (estrategia_1234, "Estratégia 1234"), (estrategia_1235, "Estratégia 1235"), (estrategia_1236, "Estratégia 1236"), (estrategia_1237, "Estratégia 1237"), 
        (estrategia_1238, "Estratégia 1238"), (estrategia_1239, "Estratégia 1239"), (estrategia_1240, "Estratégia 1240"), (estrategia_1241, "Estratégia 1241"), (estrategia_1242, "Estratégia 1242"), (estrategia_1243, "Estratégia 1243"), (estrategia_1244, "Estratégia 1244"), (estrategia_1245, "Estratégia 1245"), (estrategia_1246, "Estratégia 1246"), (estrategia_1247, "Estratégia 1247"), (estrategia_1248, "Estratégia 1248"), (estrategia_1249, "Estratégia 1249"), (estrategia_1250, "Estratégia 1250"), (estrategia_1251, "Estratégia 1251"), (estrategia_1252, "Estratégia 1252"), (estrategia_1253, "Estratégia 1253"), 
        (estrategia_1254, "Estratégia 1254"), (estrategia_1255, "Estratégia 1255"), (estrategia_1256, "Estratégia 1256"), (estrategia_1257, "Estratégia 1257"), (estrategia_1258, "Estratégia 1258"), (estrategia_1259, "Estratégia 1259"), (estrategia_1260, "Estratégia 1260"), (estrategia_1261, "Estratégia 1261"), (estrategia_1262, "Estratégia 1262"), (estrategia_1263, "Estratégia 1263"), (estrategia_1264, "Estratégia 1264"), (estrategia_1265, "Estratégia 1265"), (estrategia_1266, "Estratégia 1266"), (estrategia_1267, "Estratégia 1267"), (estrategia_1268, "Estratégia 1268"), (estrategia_1269, "Estratégia 1269"),
        (estrategia_1270, "Estratégia 1270"), (estrategia_1271, "Estratégia 1271"), (estrategia_1272, "Estratégia 1272"), (estrategia_1273, "Estratégia 1273"), (estrategia_1274, "Estratégia 1274"), (estrategia_1275, "Estratégia 1275"), (estrategia_1276, "Estratégia 1276"), (estrategia_1277, "Estratégia 1277"), (estrategia_1278, "Estratégia 1278"), (estrategia_1279, "Estratégia 1279"), (estrategia_1280, "Estratégia 1280"), (estrategia_1281, "Estratégia 1281"), (estrategia_1282, "Estratégia 1282"), (estrategia_1283, "Estratégia 1283"), (estrategia_1284, "Estratégia 1284"), (estrategia_1285, "Estratégia 1285"), 
        (estrategia_1286, "Estratégia 1286"), (estrategia_1287, "Estratégia 1287"), (estrategia_1288, "Estratégia 1288"), (estrategia_1289, "Estratégia 1289"), (estrategia_1290, "Estratégia 1290"), (estrategia_1291, "Estratégia 1291"), (estrategia_1292, "Estratégia 1292"), (estrategia_1293, "Estratégia 1293"), (estrategia_1294, "Estratégia 1294"), (estrategia_1295, "Estratégia 1295"), (estrategia_1296, "Estratégia 1296"), (estrategia_1297, "Estratégia 1297"), (estrategia_1298, "Estratégia 1298"), (estrategia_1299, "Estratégia 1299"), (estrategia_1300, "Estratégia 1300"), (estrategia_1301, "Estratégia 1301"), 
        (estrategia_1302, "Estratégia 1302"), (estrategia_1303, "Estratégia 1303"), (estrategia_1304, "Estratégia 1304"), (estrategia_1305, "Estratégia 1305"), (estrategia_1306, "Estratégia 1306"), (estrategia_1307, "Estratégia 1307"), (estrategia_1308, "Estratégia 1308"), (estrategia_1309, "Estratégia 1309"), (estrategia_1310, "Estratégia 1310"), (estrategia_1311, "Estratégia 1311"), (estrategia_1312, "Estratégia 1312"), (estrategia_1313, "Estratégia 1313"), (estrategia_1314, "Estratégia 1314"), (estrategia_1315, "Estratégia 1315"), (estrategia_1316, "Estratégia 1316"), (estrategia_1317, "Estratégia 1317"), 
        (estrategia_1318, "Estratégia 1318"), (estrategia_1319, "Estratégia 1319"), (estrategia_1320, "Estratégia 1320"), (estrategia_1321, "Estratégia 1321"), (estrategia_1322, "Estratégia 1322"), (estrategia_1323, "Estratégia 1323"), (estrategia_1324, "Estratégia 1324"), (estrategia_1325, "Estratégia 1325"), (estrategia_1326, "Estratégia 1326"), (estrategia_1327, "Estratégia 1327"), (estrategia_1328, "Estratégia 1328"), (estrategia_1329, "Estratégia 1329"), (estrategia_1330, "Estratégia 1330"), (estrategia_1331, "Estratégia 1331"), (estrategia_1332, "Estratégia 1332"), (estrategia_1333, "Estratégia 1333"), 
        (estrategia_1334, "Estratégia 1334"), (estrategia_1335, "Estratégia 1335"), (estrategia_1336, "Estratégia 1336"), (estrategia_1337, "Estratégia 1337"), (estrategia_1338, "Estratégia 1338"), (estrategia_1339, "Estratégia 1339"), (estrategia_1340, "Estratégia 1340"), (estrategia_1341, "Estratégia 1341"), (estrategia_1342, "Estratégia 1342"), (estrategia_1343, "Estratégia 1343"), (estrategia_1344, "Estratégia 1344"), (estrategia_1345, "Estratégia 1345"), (estrategia_1346, "Estratégia 1346"), (estrategia_1347, "Estratégia 1347"), (estrategia_1348, "Estratégia 1348"), (estrategia_1349, "Estratégia 1349"), 
        (estrategia_1350, "Estratégia 1350"), (estrategia_1351, "Estratégia 1351"), (estrategia_1352, "Estratégia 1352"), (estrategia_1353, "Estratégia 1353"), (estrategia_1354, "Estratégia 1354"), (estrategia_1355, "Estratégia 1355"), (estrategia_1356, "Estratégia 1356"), (estrategia_1357, "Estratégia 1357"), (estrategia_1358, "Estratégia 1358"), (estrategia_1359, "Estratégia 1359"), (estrategia_1360, "Estratégia 1360"), (estrategia_1361, "Estratégia 1361"), (estrategia_1362, "Estratégia 1362"), (estrategia_1363, "Estratégia 1363"), (estrategia_1364, "Estratégia 1364"), (estrategia_1365, "Estratégia 1365"),
        (estrategia_1366, "Estratégia 1366"), (estrategia_1367, "Estratégia 1367"), (estrategia_1368, "Estratégia 1368"), (estrategia_1369, "Estratégia 1369"), (estrategia_1370, "Estratégia 1370"), (estrategia_1371, "Estratégia 1371"), (estrategia_1372, "Estratégia 1372"), (estrategia_1373, "Estratégia 1373"), (estrategia_1374, "Estratégia 1374"), (estrategia_1375, "Estratégia 1375"), (estrategia_1376, "Estratégia 1376"), (estrategia_1377, "Estratégia 1377"), (estrategia_1378, "Estratégia 1378"), (estrategia_1379, "Estratégia 1379"), (estrategia_1380, "Estratégia 1380"), (estrategia_1381, "Estratégia 1381"), 
        (estrategia_1382, "Estratégia 1382"), (estrategia_1383, "Estratégia 1383"), (estrategia_1384, "Estratégia 1384"), (estrategia_1385, "Estratégia 1385"), (estrategia_1386, "Estratégia 1386"), (estrategia_1387, "Estratégia 1387"), (estrategia_1388, "Estratégia 1388"), (estrategia_1389, "Estratégia 1389"), (estrategia_1390, "Estratégia 1390"), (estrategia_1391, "Estratégia 1391"), (estrategia_1392, "Estratégia 1392"), 
        (estrategia_1393, "Estratégia 1393"), (estrategia_1394, "Estratégia 1394"), (estrategia_1395, "Estratégia 1395"), (estrategia_1396, "Estratégia 1396"), (estrategia_1397, "Estratégia 1397"), (estrategia_1398, "Estratégia 1398"), (estrategia_1399, "Estratégia 1399"), (estrategia_1400, "Estratégia 1400"), (estrategia_1401, "Estratégia 1401"), (estrategia_1402, "Estratégia 1402"), (estrategia_1403, "Estratégia 1403"), 
        (estrategia_1404, "Estratégia 1404"), (estrategia_1405, "Estratégia 1405"), (estrategia_1406, "Estratégia 1406"), (estrategia_1407, "Estratégia 1407"), (estrategia_1408, "Estratégia 1408"), (estrategia_1409, "Estratégia 1409"), (estrategia_1410, "Estratégia 1410"), (estrategia_1411, "Estratégia 1411"), (estrategia_1412, "Estratégia 1412"), (estrategia_1413, "Estratégia 1413"), (estrategia_1414, "Estratégia 1414"), 
        (estrategia_1415, "Estratégia 1415"), (estrategia_1416, "Estratégia 1416"), (estrategia_1417, "Estratégia 1417"), (estrategia_1418, "Estratégia 1418"), (estrategia_1419, "Estratégia 1419"), (estrategia_1420, "Estratégia 1420"), (estrategia_1421, "Estratégia 1421"), (estrategia_1422, "Estratégia 1422"), (estrategia_1423, "Estratégia 1423"), (estrategia_1424, "Estratégia 1424"), (estrategia_1425, "Estratégia 1425"), 
        (estrategia_1426, "Estratégia 1426"), (estrategia_1427, "Estratégia 1427"), (estrategia_1428, "Estratégia 1428"), (estrategia_1429, "Estratégia 1429"), (estrategia_1430, "Estratégia 1430"), (estrategia_1431, "Estratégia 1431"), (estrategia_1432, "Estratégia 1432"), (estrategia_1433, "Estratégia 1433"), (estrategia_1434, "Estratégia 1434"), (estrategia_1435, "Estratégia 1435"), (estrategia_1436, "Estratégia 1436"), 
        (estrategia_1437, "Estratégia 1437"), (estrategia_1438, "Estratégia 1438"), (estrategia_1439, "Estratégia 1439"), (estrategia_1440, "Estratégia 1440"), (estrategia_1441, "Estratégia 1441"), (estrategia_1442, "Estratégia 1442"), (estrategia_1443, "Estratégia 1443"), (estrategia_1444, "Estratégia 1444"), (estrategia_1445, "Estratégia 1445"), (estrategia_1446, "Estratégia 1446"), (estrategia_1447, "Estratégia 1447"), 
        (estrategia_1448, "Estratégia 1448"), (estrategia_1449, "Estratégia 1449"), (estrategia_1450, "Estratégia 1450"), (estrategia_1451, "Estratégia 1451"), (estrategia_1452, "Estratégia 1452"), (estrategia_1453, "Estratégia 1453"), (estrategia_1454, "Estratégia 1454"), (estrategia_1455, "Estratégia 1455"), (estrategia_1456, "Estratégia 1456"), (estrategia_1457, "Estratégia 1457"), (estrategia_1458, "Estratégia 1458"), 
        (estrategia_1459, "Estratégia 1459"), (estrategia_1460, "Estratégia 1460"), (estrategia_1461, "Estratégia 1461"), (estrategia_1462, "Estratégia 1462"), (estrategia_1463, "Estratégia 1463"), (estrategia_1464, "Estratégia 1464"), (estrategia_1465, "Estratégia 1465"), (estrategia_1466, "Estratégia 1466"), (estrategia_1467, "Estratégia 1467"), (estrategia_1468, "Estratégia 1468"), (estrategia_1469, "Estratégia 1469"), 
        (estrategia_1470, "Estratégia 1470"), (estrategia_1471, "Estratégia 1471"), (estrategia_1472, "Estratégia 1472"), (estrategia_1473, "Estratégia 1473"), (estrategia_1474, "Estratégia 1474"), (estrategia_1475, "Estratégia 1475"), (estrategia_1476, "Estratégia 1476"), (estrategia_1477, "Estratégia 1477"), (estrategia_1478, "Estratégia 1478"), (estrategia_1479, "Estratégia 1479"), (estrategia_1480, "Estratégia 1480"), 
        (estrategia_1481, "Estratégia 1481"), (estrategia_1482, "Estratégia 1482"), (estrategia_1483, "Estratégia 1483"), (estrategia_1484, "Estratégia 1484"), (estrategia_1485, "Estratégia 1485"), (estrategia_1486, "Estratégia 1486"), (estrategia_1487, "Estratégia 1487"), (estrategia_1488, "Estratégia 1488"), (estrategia_1489, "Estratégia 1489"), (estrategia_1490, "Estratégia 1490"), (estrategia_1491, "Estratégia 1491"), 
        (estrategia_1492, "Estratégia 1492"), (estrategia_1493, "Estratégia 1493"), (estrategia_1494, "Estratégia 1494"), (estrategia_1495, "Estratégia 1495"), (estrategia_1496, "Estratégia 1496"), (estrategia_1497, "Estratégia 1497"), (estrategia_1498, "Estratégia 1498"), (estrategia_1499, "Estratégia 1499"), (estrategia_1500, "Estratégia 1500"), (estrategia_1501, "Estratégia 1501"), (estrategia_1502, "Estratégia 1502"), 
        (estrategia_1503, "Estratégia 1503"), (estrategia_1504, "Estratégia 1504"), (estrategia_1505, "Estratégia 1505"), (estrategia_1506, "Estratégia 1506"), (estrategia_1507, "Estratégia 1507"), (estrategia_1508, "Estratégia 1508"), (estrategia_1509, "Estratégia 1509"), (estrategia_1510, "Estratégia 1510"), (estrategia_1511, "Estratégia 1511"), (estrategia_1512, "Estratégia 1512"), (estrategia_1513, "Estratégia 1513"), 
        (estrategia_1514, "Estratégia 1514"), (estrategia_1515, "Estratégia 1515"), (estrategia_1516, "Estratégia 1516"), (estrategia_1517, "Estratégia 1517"), (estrategia_1518, "Estratégia 1518"), (estrategia_1519, "Estratégia 1519"), (estrategia_1520, "Estratégia 1520"), (estrategia_1521, "Estratégia 1521"), (estrategia_1522, "Estratégia 1522"), (estrategia_1523, "Estratégia 1523"), (estrategia_1524, "Estratégia 1524"), 
        (estrategia_1525, "Estratégia 1525"), (estrategia_1526, "Estratégia 1526"), (estrategia_1527, "Estratégia 1527"), (estrategia_1528, "Estratégia 1528"), (estrategia_1529, "Estratégia 1529"), (estrategia_1530, "Estratégia 1530"), (estrategia_1531, "Estratégia 1531"), (estrategia_1532, "Estratégia 1532"), (estrategia_1533, "Estratégia 1533"), (estrategia_1534, "Estratégia 1534"), (estrategia_1535, "Estratégia 1535"), 
        (estrategia_1536, "Estratégia 1536"), (estrategia_1537, "Estratégia 1537"), (estrategia_1538, "Estratégia 1538"), (estrategia_1539, "Estratégia 1539"), (estrategia_1540, "Estratégia 1540"), (estrategia_1541, "Estratégia 1541"), (estrategia_1542, "Estratégia 1542"), (estrategia_1543, "Estratégia 1543"), (estrategia_1544, "Estratégia 1544"), (estrategia_1545, "Estratégia 1545"), (estrategia_1546, "Estratégia 1546"), 
        (estrategia_1547, "Estratégia 1547"), (estrategia_1548, "Estratégia 1548"), (estrategia_1549, "Estratégia 1549"), (estrategia_1550, "Estratégia 1550"), (estrategia_1551, "Estratégia 1551"), (estrategia_1552, "Estratégia 1552"), (estrategia_1553, "Estratégia 1553"), (estrategia_1554, "Estratégia 1554"), (estrategia_1555, "Estratégia 1555"), (estrategia_1556, "Estratégia 1556"), (estrategia_1557, "Estratégia 1557"), 
        (estrategia_1558, "Estratégia 1558"), (estrategia_1559, "Estratégia 1559"), (estrategia_1560, "Estratégia 1560"), (estrategia_1561, "Estratégia 1561"), (estrategia_1562, "Estratégia 1562"), (estrategia_1563, "Estratégia 1563"), (estrategia_1564, "Estratégia 1564"), (estrategia_1565, "Estratégia 1565"), (estrategia_1566, "Estratégia 1566"), (estrategia_1567, "Estratégia 1567"), (estrategia_1568, "Estratégia 1568"), 
        (estrategia_1569, "Estratégia 1569"), (estrategia_1570, "Estratégia 1570"), (estrategia_1571, "Estratégia 1571"), (estrategia_1572, "Estratégia 1572"), (estrategia_1573, "Estratégia 1573"), (estrategia_1574, "Estratégia 1574"), (estrategia_1575, "Estratégia 1575"), (estrategia_1576, "Estratégia 1576"), (estrategia_1577, "Estratégia 1577"), (estrategia_1578, "Estratégia 1578"), (estrategia_1579, "Estratégia 1579"), 
        (estrategia_1580, "Estratégia 1580"), (estrategia_1581, "Estratégia 1581"), (estrategia_1582, "Estratégia 1582"), (estrategia_1583, "Estratégia 1583"), (estrategia_1584, "Estratégia 1584"), (estrategia_1585, "Estratégia 1585"), (estrategia_1586, "Estratégia 1586"), (estrategia_1587, "Estratégia 1587"), (estrategia_1588, "Estratégia 1588"), (estrategia_1589, "Estratégia 1589"), (estrategia_1590, "Estratégia 1590"), 
        (estrategia_1591, "Estratégia 1591"), (estrategia_1592, "Estratégia 1592"), (estrategia_1593, "Estratégia 1593"), (estrategia_1594, "Estratégia 1594"), (estrategia_1595, "Estratégia 1595"), (estrategia_1596, "Estratégia 1596"), (estrategia_1597, "Estratégia 1597"), (estrategia_1598, "Estratégia 1598"), (estrategia_1599, "Estratégia 1599"), (estrategia_1600, "Estratégia 1600")



    ]
# --- Fim das Funções ---


# --- Interface Streamlit ---
st.title("Estratégias - Back Home HT")

# --- Carregar Dados Históricos do GitHub ---
df_historico_original = load_data_from_github(GITHUB_RAW_URL)

# --- Processar Dados Históricos (se carregados com sucesso) ---
if df_historico_original is not None:
    st.header("Processamento da Base Histórica (do GitHub)")

    # Filtro de Ligas (Histórico)
    if 'League' in df_historico_original.columns:
        df_historico = df_historico_original[df_historico_original['League'].isin(APPROVED_LEAGUES)].copy()
        count_original = len(df_historico_original)
        count_filtered = len(df_historico)
        st.write(f"Filtrando por ligas aprovadas... {count_original} jogos originais -> {count_filtered} jogos nas ligas aprovadas.")
        if df_historico.empty and not df_historico_original.empty:
             st.warning("Nenhum jogo do histórico (GitHub) pertence às ligas aprovadas.")
    else:
        st.warning("Coluna 'League' não encontrada no arquivo histórico (GitHub). Filtro de ligas não aplicado.")
        df_historico = df_historico_original.copy() # Usar dados originais se não houver coluna 'League'

    if not df_historico.empty:
        # Executar Backtest e Análise
        try:
            # Certifique-se de que df_historico tenha as colunas necessárias antes de aplicar
            st.write("Aplicando estratégias e calculando variáveis...")
            estrategias = apply_strategies(df_historico.copy()) # Passa a cópia filtrada por liga
        except Exception as e:
            st.error(f"Erro ao pré-calcular variáveis ou aplicar estratégias no histórico: {e}")
            estrategias = []

        if estrategias:
            st.header("Resultados do Backtest (Ligas Filtradas)")
            backtest_results = []
            medias_results = []
            resultados = {} # Dicionário para armazenar {nome_estr: (dataframe_filtrado, aprovada_media)}

            progress_bar = st.progress(0, text="Executando backtest...")
            total_estrategias = len(estrategias)

            for i, (estrategia_func, estrategia_nome) in enumerate(estrategias):
                # Atualiza a barra de progresso
                progress_text = f"Executando backtest: {estrategia_nome} ({i+1}/{total_estrategias})"
                progress_bar.progress((i + 1) / total_estrategias, text=progress_text)

                # Roda o backtest principal
                # Passa df_historico (já filtrado por liga) para run_backtest
                backtest_result = run_backtest(df_historico.copy(), estrategia_func, estrategia_nome)

                # Roda a análise de médias apenas se o backtest retornou dados
                if backtest_result["Dataframe"] is not None and not backtest_result["Dataframe"].empty:
                     medias_result = check_moving_averages(backtest_result["Dataframe"].copy(), estrategia_nome)
                else:
                     # Define resultado padrão para médias se não houver jogos no backtest
                     medias_result = {
                        "Estratégia": estrategia_nome,
                        "Média 8": "N/A (0 jogos)",
                        "Média 40": "N/A (0 jogos)",
                        "Lucro Últimos 8": "N/A",
                        "Lucro Últimos 40": "N/A",
                        "Acima dos Limiares": False
                    }

                # Armazena os resultados
                backtest_results.append(backtest_result)
                medias_results.append(medias_result)
                # Guarda o dataframe do backtest e se foi aprovado nas médias
                resultados[estrategia_nome] = (backtest_result["Dataframe"], medias_result["Acima dos Limiares"])

            progress_bar.empty() # Limpa a barra de progresso

            # Exibir resultados consolidados
            with st.expander("📊 Resultados Consolidados do Backtest"):
                 st.subheader("Resumo do Desempenho por Estratégia")
                 df_summary = pd.DataFrame([r for r in backtest_results if r["Total de Jogos"] > 0]).drop(columns=["Dataframe"], errors='ignore')
                 if not df_summary.empty:
                     st.dataframe(df_summary)
                 else:
                     st.write("Nenhuma estratégia encontrou jogos correspondentes nos dados históricos filtrados.")

            with st.expander("📈 Análise das Médias e Lucros Recentes"):
                st.subheader("Detalhes das Médias e Lucros Recentes por Estratégia")
                df_medias = pd.DataFrame(medias_results)
                st.dataframe(df_medias)

            # --- Upload e Análise dos Jogos do Dia ---
            estrategias_aprovadas = [nome for nome, (_, acima) in resultados.items() if acima]

            if not estrategias_aprovadas:
                st.info("Nenhuma estratégia foi aprovada nos critérios de médias e lucros recentes para analisar os jogos do dia.")
            else:
                st.header("Upload dos Jogos do Dia")
                uploaded_daily = st.file_uploader(
                    "Faça upload da planilha com os jogos do dia (.xlsx ou .csv)",
                    type=["xlsx", "csv"],
                    key="daily_simple_csv"
                )

                if uploaded_daily is not None:
                    df_daily_original = load_dataframe_from_upload(uploaded_daily) # Usa a função correta para upload

                    if df_daily_original is not None:
                        # Filtro de Ligas (Jogos do Dia)
                        if 'League' in df_daily_original.columns:
                            df_daily = df_daily_original[df_daily_original['League'].isin(APPROVED_LEAGUES)].copy()
                            st.write(f"Filtrando jogos do dia por ligas aprovadas... {len(df_daily_original)} jogos originais -> {len(df_daily)} jogos nas ligas aprovadas.")
                            if df_daily.empty and not df_daily_original.empty:
                                 st.warning("Nenhum jogo do dia pertence às ligas aprovadas.")
                        else:
                            st.warning("Coluna 'League' não encontrada no arquivo de jogos do dia. Filtro de ligas não aplicado.")
                            df_daily = df_daily_original.copy()

                        if not df_daily.empty:
                            st.header("Jogos Aprovados para Hoje (Ligas Filtradas)")
                            jogos_aprovados_total = []
                            mapa_estrategias_diarias = {}

                            try:
                                st.write("Aplicando estratégias e calculando variáveis para os jogos do dia...")
                                estrategias_diarias_funcs = apply_strategies(df_daily.copy())
                                mapa_estrategias_diarias = {nome: func for func, nome in estrategias_diarias_funcs}
                            except Exception as e:
                                st.error(f"Erro ao pré-calcular variáveis ou aplicar estratégias nos jogos do dia: {e}")

                            if mapa_estrategias_diarias:
                                st.write(f"Analisando {len(estrategias_aprovadas)} estratégias aprovadas...")
                                for estrategia_nome in estrategias_aprovadas:
                                     if estrategia_nome in mapa_estrategias_diarias:
                                         estrategia_func_diaria = mapa_estrategias_diarias[estrategia_nome]
                                         jogos_aprovados = analyze_daily_games(df_daily.copy(), estrategia_func_diaria, estrategia_nome)
                                         if jogos_aprovados is not None and not jogos_aprovados.empty:
                                             # Adiciona coluna com nome da estratégia para referência
                                             jogos_aprovados['Estrategia'] = estrategia_nome
                                             jogos_aprovados_total.extend(jogos_aprovados.to_dict('records'))
                                     # else: # Não precisa informar se a estratégia não se aplica aos dados do dia
                                     #    st.info(f"Estratégia '{estrategia_nome}' não aplicável aos dados do dia.")


                                if jogos_aprovados_total:
                                    df_jogos_aprovados_final = pd.DataFrame(jogos_aprovados_total)

                                    # Define colunas para verificar duplicatas (incluindo Estrategia agora)
                                    cols_to_check_duplicates = ['Time', 'Home', 'Away', 'Estrategia']
                                    if 'League' in df_jogos_aprovados_final.columns:
                                        cols_to_check_duplicates.insert(1, 'League')

                                    # Remove duplicatas baseadas nas colunas existentes
                                    cols_exist_check = [col for col in cols_to_check_duplicates if col in df_jogos_aprovados_final.columns]
                                    if cols_exist_check:
                                        # Primeiro, remove duplicatas exatas (mesmo jogo, mesma estratégia)
                                        df_jogos_aprovados_final = df_jogos_aprovados_final.drop_duplicates(subset=cols_exist_check)

                                        # Agora, agrupa por jogo e lista as estratégias
                                        group_cols = [col for col in cols_exist_check if col != 'Estrategia']
                                        if group_cols: # Garante que temos colunas para agrupar
                                            df_jogos_agrupados = df_jogos_aprovados_final.groupby(group_cols)['Estrategia'].apply(lambda x: ', '.join(sorted(list(set(x))))).reset_index()
                                            st.header("🏆 Lista Unificada de Jogos Aprovados")
                                            st.dataframe(df_jogos_agrupados)
                                        else: # Caso muito raro: só tem a coluna 'Estrategia'
                                            st.header("🏆 Lista de Estratégias Aprovadas (sem detalhes do jogo)")
                                            st.dataframe(df_jogos_aprovados_final[['Estrategia']].drop_duplicates())

                                    else: # Caso muito raro: nenhuma coluna de identificação encontrada
                                         st.warning("Não foi possível identificar jogos unicamente para agrupar estratégias.")
                                         st.dataframe(df_jogos_aprovados_final) # Mostra o que tem


                                elif estrategias_aprovadas: # Tinha estratégias aprovadas, mas nenhuma encontrou jogos no dia
                                    st.write("Nenhum jogo do dia (nas ligas aprovadas) atende aos critérios das estratégias aprovadas.")
                            else:
                                 st.warning("Não foi possível aplicar estratégias aos jogos do dia devido a erro anterior no cálculo de variáveis.")

                        else:
                            st.info("Não há jogos do dia nas ligas aprovadas para analisar.")
                    # else: # Erro na leitura do upload diário (já tratado em load_dataframe_from_upload)
                    #    pass
                # else: # Nenhum uploaded_daily (nenhum arquivo carregado)
                #    pass
        else:
            st.warning("Não foi possível gerar as estratégias a partir dos dados históricos.")

    else:
        st.info("Não há dados históricos nas ligas aprovadas (do GitHub) para realizar o backtest.")

# else: # Erro ao carregar do GitHub (já tratado em load_data_from_github)
#     st.info("A aplicação não pode continuar sem os dados históricos.")
