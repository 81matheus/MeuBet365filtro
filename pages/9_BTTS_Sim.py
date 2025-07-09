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
    Processa a planilha do usuário, adaptando-se a diferentes formatos de dados (colunas de placar separadas ou combinadas).
    """
    try:
        # 1. Normaliza cabeçalhos para maiúsculas e sem espaços
        df.columns = [str(col).strip().upper() for col in df.columns]

        # 2. Renomeia colunas comuns para um padrão interno
        rename_map = {'EQUIPA CASA': 'HOME', 'EQUIPA VISITANTE': 'AWAY'}
        df = df.rename(columns=rename_map)

        # --- LÓGICA INTELIGENTE PARA DETECTAR O FORMATO DO PLACAR ---
        clean_ft_cols = ['RESULTADO FT CASA', 'RESULTADO FT FORA']
        
        # CENÁRIO A: Colunas de placar já estão limpas e separadas
        if all(col in df.columns for col in clean_ft_cols):
            st.info("Formato de planilha com colunas de placar separadas detectado. Processando...")
            # Renomeia para o padrão interno
            df = df.rename(columns={
                'RESULTADO HT CASA': 'GOALS_H_HT', 'RESULTADO HT FORA': 'GOALS_A_HT',
                'RESULTADO FT CASA': 'GOALS_H_FT', 'RESULTADO FT FORA': 'GOALS_A_FT'
            })
            # Garante que, se as colunas de HT não existirem, elas sejam criadas com 0
            if 'GOALS_H_HT' not in df.columns: df['GOALS_H_HT'] = 0
            if 'GOALS_A_HT' not in df.columns: df['GOALS_A_HT'] = 0

        # CENÁRIO B: Procura por uma coluna de placar combinado (formato "bagunçado")
        else:
            st.info("Tentando encontrar uma coluna de placar combinado (ex: '1-0 2-1')...")
            score_col_name = next((col for col in df.columns if df[col].astype(str).str.match(r'^\d+-\d+(\s+\d+-\d+)?$').any()), None)
            
            if not score_col_name:
                st.error("Não foi possível encontrar colunas de placar. Formatos esperados: colunas separadas ('RESULTADO FT CASA', 'RESULTADO FT FORA') OU uma única coluna com texto de placar (ex: '1-0' ou '1-0 2-1').")
                return pd.DataFrame()

            def parse_combined_score(score_str):
                if not isinstance(score_str, str): return [np.nan] * 4
                match = re.match(r'(\d+)-(\d+)\s+(\d+)-(\d+)', score_str)
                if match: return [int(g) for g in match.groups()]
                match_ft_only = re.match(r'(\d+)-(\d+)', score_str)
                if match_ft_only: return [0, 0, int(match_ft_only.group(1)), int(match_ft_only.group(2))]
                return [0, 0, 0, 0]

            scores = df[score_col_name].apply(parse_combined_score)
            df[['GOALS_H_HT', 'GOALS_A_HT', 'GOALS_H_FT', 'GOALS_A_FT']] = pd.DataFrame(scores.tolist(), index=df.index)

        # 3. Limpeza e conversão final das colunas
        for col in ['HOME', 'AWAY', 'LIGA']:
            if col not in df.columns: df[col] = 'N/A'
        
        for col in ['GOALS_H_HT', 'GOALS_A_HT', 'GOALS_H_FT', 'GOALS_A_FT']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        def robust_date_parser(date_val):
            if isinstance(date_val, (int, float)):
                try: return pd.to_datetime('1899-12-30') + pd.to_timedelta(date_val, 'D')
                except: return pd.NaT
            try: return pd.to_datetime(date_val, dayfirst=True, errors='coerce')
            except (ValueError, TypeError): return pd.NaT
        df['DATE'] = df['DATA'].apply(robust_date_parser)
        df = df.dropna(subset=['DATE']).sort_values(by='DATE').reset_index(drop=True)

        # 4. DERIVAÇÃO DE MERCADOS (a partir dos dados já limpos)
        df['TOTAL_GOALS_FT'] = df['GOALS_H_FT'] + df['GOALS_A_FT']
        df['TOTAL_GOALS_HT'] = df['GOALS_H_HT'] + df['GOALS_A_HT']
        df['GOALS_2T'] = df['TOTAL_GOALS_FT'] - df['TOTAL_GOALS_HT']
        df['CASA'] = np.where(df['GOALS_H_FT'] > df['GOALS_A_FT'], 'SIM', 'NÃO')
        df['EMPATE'] = np.where(df['GOALS_H_FT'] == df['GOALS_A_FT'], 'SIM', 'NÃO')
        df['VISITANTE'] = np.where(df['GOALS_H_FT'] < df['GOALS_A_FT'], 'SIM', 'NÃO')
        
        # Mercados de Gols
        df['Mais de 0,5 HT'] = np.where(df['TOTAL_GOALS_HT'] > 0.5, 'SIM', 'NÃO')
        df['Menos de 1,5 HT'] = np.where(df['TOTAL_GOALS_HT'] < 1.5, 'SIM', 'NÃO')
        df['Mais de 0,5 ft'] = np.where(df['TOTAL_GOALS_FT'] > 0.5, 'SIM', 'NÃO')
        df['Mais de 1,5'] = np.where(df['TOTAL_GOALS_FT'] > 1.5, 'SIM', 'NÃO')
        df['Menos de 1,5'] = np.where(df['TOTAL_GOALS_FT'] < 1.5, 'SIM', 'NÃO')
        df['Mais de 2,5'] = np.where(df['TOTAL_GOALS_FT'] > 2.5, 'SIM', 'NÃO')
        df['Menos de 2,5'] = np.where(df['TOTAL_GOALS_FT'] < 2.5, 'SIM', 'NÃO')
        df['Mais de 3,5'] = np.where(df['TOTAL_GOALS_FT'] > 3.5, 'SIM', 'NÃO')
        df['Menos de 3,5'] = np.where(df['TOTAL_GOALS_FT'] < 3.5, 'SIM', 'NÃO')
        df['Menos de 4,5'] = np.where(df['TOTAL_GOALS_FT'] < 4.5, 'SIM', 'NÃO')
        df['Menos de 6,5'] = np.where(df['TOTAL_GOALS_FT'] < 6.5, 'SIM', 'NÃO')

        st.success("Planilha processada com sucesso!")
        return df
    except Exception as e:
        st.error(f"Ocorreu um erro crítico ao processar sua planilha: {e}. Verifique se o arquivo não está corrompido.")
        return pd.DataFrame()

# --- Funções de Análise (mesmas da versão anterior) ---
def create_correct_score_matrix(df):
    if df.empty: return None
    cs_crosstab = pd.crosstab(df['GOALS_H_FT'], df['GOALS_A_FT'])
    max_val = max(cs_crosstab.index.max(), cs_crosstab.columns.max(), 4)
    all_indices = np.arange(0, max_val + 1)
    cs_crosstab = cs_crosstab.reindex(index=all_indices, columns=all_indices, fill_value=0)
    fig = px.imshow(cs_crosstab, text_auto=True, aspect="auto", color_continuous_scale='Blues',
                    labels=dict(x="Gols Visitante", y="Gols Casa", color="Nº de Jogos"))
    fig.update_layout(title_text='Mapa de Calor de Placares Exatos (Correct Score)', title_x=0.5)
    return fig

def analyze_scenarios(df):
    scenarios = {}
    
    # Cenário 1: Jogo Empatado no HT
    df_tied_ht = df[df['GOALS_H_HT'] == df['GOALS_A_HT']]
    total_tied_ht = len(df_tied_ht)
    if total_tied_ht > 0:
        scenarios['tied_at_ht'] = {
            'total_cases': total_tied_ht,
            'home_win_rate': (df_tied_ht['CASA'] == 'SIM').mean() * 100,
            'away_win_rate': (df_tied_ht['VISITANTE'] == 'SIM').mean() * 100
        }

    # Cenário 2: Jogo Empatado COM GOLS no HT
    df_tied_w_goals_ht = df[(df['GOALS_H_HT'] == df['GOALS_A_HT']) & (df['TOTAL_GOALS_HT'] > 0)]
    total_tied_w_goals_ht = len(df_tied_w_goals_ht)
    if total_tied_w_goals_ht > 0:
        scenarios['tied_with_goals_at_ht'] = {
            'total_cases': total_tied_w_goals_ht,
            'over_05_2T_rate': (df_tied_w_goals_ht['GOALS_2T'] > 0.5).mean() * 100,
            'over_15_FT_rate': (df_tied_w_goals_ht['TOTAL_GOALS_FT'] > 1.5).mean() * 100,
            'under_25_2T_rate': (df_tied_w_goals_ht['GOALS_2T'] < 2.5).mean() * 100,
            'under_45_FT_rate': (df_tied_w_goals_ht['TOTAL_GOALS_FT'] < 4.5).mean() * 100,
            'under_65_FT_rate': (df_tied_w_goals_ht['TOTAL_GOALS_FT'] < 6.5).mean() * 100,
        }

    # Cenário 3: Comebacks
    home_losing_at_ht = df[df['GOALS_H_HT'] < df['GOALS_A_HT']]
    away_losing_at_ht = df[df['GOALS_H_HT'] > df['GOALS_A_HT']]
    scenarios['comebacks'] = {
        'home_comeback_rate': (home_losing_at_ht['GOALS_H_FT'] >= home_losing_at_ht['GOALS_A_FT']).mean() * 100 if not home_losing_at_ht.empty else 0,
        'home_total_cases': len(home_losing_at_ht),
        'away_comeback_rate': (away_losing_at_ht['GOALS_H_FT'] <= away_losing_at_ht['GOALS_A_FT']).mean() * 100 if not away_losing_at_ht.empty else 0,
        'away_total_cases': len(away_losing_at_ht)
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
        markets_to_display = [
            'Vitórias equipa Casa', 'Empates', 'Vitórias equipa Fora',
            'Mais de 0,5 HT', 'Mais de 0,5 ft', 'Mais de 1,5', 'Mais de 2,5', 'Mais de 3,5',
            'Menos de 1,5 HT', 'Menos de 1,5', 'Menos de 2,5', 'Menos de 3,5', 'Menos de 4,5', 'Menos de 6,5'
        ]
        
        column_map = {
            'Vitórias equipa Casa': 'CASA', 'Empates': 'EMPATE', 'Vitórias equipa Fora': 'VISITANTE'
        }

        col1, col2, col3 = st.columns(3)
        cols = [col1, col2, col3]
        
        for i, market_name in enumerate(markets_to_display):
            df_col_name = column_map.get(market_name, market_name)
            
            if df_col_name in filtered_df.columns:
                rate = (filtered_df[df_col_name] == 'SIM').mean() * 100
                cols[i % 3].metric(market_name, f"{rate:.2f}%")
            
    with tab2:
        st.header("Análise de Cenários de Jogo")
        scenarios = analyze_scenarios(filtered_df)

        st.subheader("Cenário: Jogo Empatado no Intervalo (HT)")
        if 'tied_at_ht' in scenarios:
            scenario = scenarios['tied_at_ht']
            c1, c2, c3 = st.columns(3)
            c1.metric("Nº de Jogos Empatados no HT", f"{scenario['total_cases']}")
            c2.metric("% de Vitória da Casa no Final", f"{scenario['home_win_rate']:.2f}%")
            c3.metric("% de Vitória do Visitante no Final", f"{scenario['away_win_rate']:.2f}%")
        else:
            st.info("Não há jogos empatados no intervalo para analisar.")

        st.markdown("---")
        
        st.subheader("Cenário: Jogo Empatado COM GOLS no Intervalo (1x1, 2x2, etc.)")
        if 'tied_with_goals_at_ht' in scenarios:
            scenario = scenarios['tied_with_goals_at_ht']
            st.info(f"Análise baseada em **{scenario['total_cases']}** jogos que estavam empatados com gols no HT.")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("2º Tempo > 0.5 Gols", f"{scenario['over_05_2T_rate']:.2f}%", help="Percentagem de jogos que tiveram pelo menos 1 gol no 2º tempo.")
            c2.metric("Jogo > 1.5 Gols (Total)", f"{scenario['over_15_FT_rate']:.2f}%", help="Percentagem de jogos que terminaram com 2 ou mais gols no total.")
            c3.metric("2º Tempo < 2.5 Gols", f"{scenario['under_25_2T_rate']:.2f}%", help="Percentagem de jogos que tiveram menos de 3 gols no 2º tempo.")
            
            c4, c5 = st.columns(2)
            c4.metric("Jogo < 4.5 Gols (Total)", f"{scenario['under_45_FT_rate']:.2f}%", help="Percentagem de jogos que terminaram com menos de 5 gols no total.")
            c5.metric("Jogo < 6.5 Gols (Total)", f"{scenario['under_65_FT_rate']:.2f}%", help="Percentagem de jogos que terminaram com menos de 7 gols no total.")
        else:
            st.info("Não há jogos empatados com gols no intervalo para analisar.")
            
        st.markdown("---")
        
        st.subheader("Análise de 'Comebacks' (Viradas)")
        scenario = scenarios['comebacks']
        c1, c2 = st.columns(2)
        c1.metric(
            "Taxa de Comeback da CASA", f"{scenario['home_comeback_rate']:.2f}%",
            help=f"Das {scenario['home_total_cases']} vezes que a casa estava perdendo no HT, ela evitou a derrota (empatou ou venceu)."
        )
        c2.metric(
            "Taxa de Comeback do VISITANTE", f"{scenario['away_comeback_rate']:.2f}%",
            help=f"Das {scenario['away_total_cases']} vezes que o visitante estava perdendo no HT, ele evitou a derrota."
        )

    with tab3:
        st.header("Análise de Placar Exato (Correct Score)")
        fig = create_correct_score_matrix(filtered_df)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Não foi possível gerar a matriz de placares.")
else:
    st.info("👋 Bem-vindo ao BetAnalyzer Pro! Por favor, carregue sua planilha na barra lateral para começar.")
