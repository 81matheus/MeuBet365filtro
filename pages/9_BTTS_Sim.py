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
        original_cols = df.columns.tolist()
        df.columns = [str(col).strip().upper() for col in original_cols]

        # 2. Renomeia colunas comuns para um padrão interno
        rename_map = {'EQUIPA CASA': 'HOME', 'EQUIPA VISITANTE': 'AWAY'}
        df = df.rename(columns=rename_map)

        # 3. Lógica Inteligente para Detectar o Formato do Placar
        clean_ft_cols = ['RESULTADO FT CASA', 'RESULTADO FT FORA']
        
        if all(col in df.columns for col in clean_ft_cols):
            df = df.rename(columns={
                'RESULTADO HT CASA': 'GOALS_H_HT', 'RESULTADO HT FORA': 'GOALS_A_HT',
                'RESULTADO FT CASA': 'GOALS_H_FT', 'RESULTADO FT FORA': 'GOALS_A_FT'
            })
            if 'GOALS_H_HT' not in df.columns: df['GOALS_H_HT'] = 0
            if 'GOALS_A_HT' not in df.columns: df['GOALS_A_HT'] = 0
        else:
            score_col_name = next((col for col in df.columns if df[col].astype(str).str.match(r'^\d+-\d+(\s+\d+-\d+)?$').any()), None)
            if not score_col_name:
                st.error("Não foi possível encontrar colunas de placar. Formatos esperados: colunas separadas ('RESULTADO FT CASA', 'RESULTADO FT FORA') OU uma única coluna com texto de placar (ex: '1-0' ou '1-0 2-1').")
                return pd.DataFrame()

            def parse_combined_score(score_str):
                if not isinstance(score_str, str): return [0, 0, 0, 0]
                match = re.match(r'(\d+)-(\d+)\s+(\d+)-(\d+)', score_str)
                if match: return [int(g) for g in match.groups()]
                match_ft_only = re.match(r'(\d+)-(\d+)', score_str)
                if match_ft_only: return [0, 0, int(match_ft_only.group(1)), int(match_ft_only.group(2))]
                return [0, 0, 0, 0]

            scores = df[score_col_name].apply(parse_combined_score)
            df[['GOALS_H_HT', 'GOALS_A_HT', 'GOALS_H_FT', 'GOALS_A_FT']] = pd.DataFrame(scores.tolist(), index=df.index)

        # 4. Limpeza e conversão final das colunas
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

        # 5. DERIVAÇÃO DE MERCADOS
        df['TOTAL_GOALS_FT'] = df['GOALS_H_FT'] + df['GOALS_A_FT']
        df['TOTAL_GOALS_HT'] = df['GOALS_H_HT'] + df['GOALS_A_HT']
        df['GOALS_2T'] = df['TOTAL_GOALS_FT'] - df['TOTAL_GOALS_HT']
        df['CASA_VENCE_FT'] = df['GOALS_H_FT'] > df['GOALS_A_FT']
        df['EMPATE_FT'] = df['GOALS_H_FT'] == df['GOALS_A_FT']
        df['VISITANTE_VENCE_FT'] = df['GOALS_H_FT'] < df['GOALS_A_FT']
        df['CASA_VENCE_HT'] = df['GOALS_H_HT'] > df['GOALS_A_HT']
        df['VISITANTE_VENCE_HT'] = df['GOALS_H_HT'] < df['GOALS_A_HT']
        
        # Mercados de Gols
        for i in np.arange(0.5, 7.0, 1.0):
            df[f'Mais de {i}'] = df['TOTAL_GOALS_FT'] > i
            df[f'Menos de {i}'] = df['TOTAL_GOALS_FT'] < i
        df['Mais de 0,5 HT'] = df['TOTAL_GOALS_HT'] > 0.5
        df['Menos de 1,5 HT'] = df['TOTAL_GOALS_HT'] < 1.5

        # Cenários Específicos
        df['CASA_ABRIU_2x0_HT'] = (df['GOALS_H_HT'] == 2) & (df['GOALS_A_HT'] == 0)
        df['FORA_ABRIU_0x2_HT'] = (df['GOALS_H_HT'] == 0) & (df['GOALS_A_HT'] == 2)

        st.success("Planilha processada com sucesso!")
        return df
    except Exception as e:
        st.error(f"Ocorreu um erro crítico ao processar sua planilha: {e}. Verifique se o arquivo não está corrompido.")
        return pd.DataFrame()

# --- Funções de Análise ---
def analyze_correct_score_table(df):
    if df.empty: return pd.DataFrame()
    
    # Deriva a coluna de Placar Exato para a análise
    df['CS'] = df['GOALS_H_FT'].astype(str) + 'x' + df['GOALS_A_FT'].astype(str)
    
    cs_counts = df['CS'].value_counts().reset_index()
    cs_counts.columns = ['Placar Exato', 'Acertos']
    
    total_entries = len(df)
    cs_counts['Entradas'] = total_entries
    cs_counts['Taxa de Acerto (%)'] = (cs_counts['Acertos'] / total_entries) * 100
    
    return cs_counts[['Placar Exato', 'Entradas', 'Acertos', 'Taxa de Acerto (%)']].sort_values(by='Acertos', ascending=False)

def analyze_scenarios(df):
    scenarios = {}
    
    df_tied_ht = df[df['GOALS_H_HT'] == df['GOALS_A_HT']]
    if not df_tied_ht.empty:
        scenarios['tied_at_ht'] = {
            'total_cases': len(df_tied_ht),
            'home_win_rate': df_tied_ht['CASA_VENCE_FT'].mean() * 100,
            'away_win_rate': df_tied_ht['VISITANTE_VENCE_FT'].mean() * 100
        }

    df_tied_w_goals_ht = df[(df['GOALS_H_HT'] == df['GOALS_A_HT']) & (df['TOTAL_GOALS_HT'] > 0)]
    if not df_tied_w_goals_ht.empty:
        scenarios['tied_with_goals_at_ht'] = {
            'total_cases': len(df_tied_w_goals_ht),
            'over_05_2T_rate': (df_tied_w_goals_ht['GOALS_2T'] > 0.5).mean() * 100,
            'over_15_FT_rate': df_tied_w_goals_ht['Mais de 1,5'].mean() * 100,
            'under_45_FT_rate': df_tied_w_goals_ht['Menos de 4,5'].mean() * 100,
            'under_65_FT_rate': df_tied_w_goals_ht['Menos de 6,5'].mean() * 100,
        }

    home_losing_at_ht = df[df['GOALS_H_HT'] < df['GOALS_A_HT']]
    away_losing_at_ht = df[df['GOALS_H_HT'] > df['GOALS_A_HT']]
    scenarios['comebacks'] = {
        'home_comeback_rate': (home_losing_at_ht['GOALS_H_FT'] >= home_losing_at_ht['GOALS_A_FT']).mean() * 100 if not home_losing_at_ht.empty else 0,
        'home_total_cases': len(home_losing_at_ht),
        'away_comeback_rate': (away_losing_at_ht['GOALS_H_FT'] <= away_losing_at_ht['GOALS_A_FT']).mean() * 100 if not away_losing_at_ht.empty else 0,
        'away_total_cases': len(away_losing_at_ht)
    }

    df_casa_2x0 = df[df['CASA_ABRIU_2x0_HT']]
    if not df_casa_2x0.empty:
        scenarios['casa_2x0_lead'] = {
            'total_cases': len(df_casa_2x0),
            'final_win_rate': df_casa_2x0['CASA_VENCE_FT'].mean() * 100
        }
        
    df_fora_0x2 = df[df['FORA_ABRIU_0x2_HT']]
    if not df_fora_0x2.empty:
        scenarios['fora_0x2_lead'] = {
            'total_cases': len(df_fora_0x2),
            'final_win_rate': df_fora_0x2['VISITANTE_VENCE_FT'].mean() * 100
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
        
        st.subheader("🏠 Resultados Finais (FT)")
        col1, col2, col3 = st.columns(3)
        col1.metric("Vitórias equipa Casa", f"{filtered_df['CASA_VENCE_FT'].mean()*100:.2f}%")
        col2.metric("Empates", f"{filtered_df['EMPATE_FT'].mean()*100:.2f}%")
        col3.metric("Vitórias equipa Fora", f"{filtered_df['VISITANTE_VENCE_FT'].mean()*100:.2f}%")
        
        st.subheader("⏱️ Resultados ao Intervalo (HT)")
        col1, col2 = st.columns(2)
        col1.metric("Vitórias equipa Casa em HT", f"{filtered_df['CASA_VENCE_HT'].mean()*100:.2f}%")
        col2.metric("Vitórias equipa Fora em HT", f"{filtered_df['VISITANTE_VENCE_HT'].mean()*100:.2f}%")

        st.subheader("⚽ Mercados de Gols (Over/Under)")
        markets_to_display = [
            'Mais de 0,5 HT', 'Mais de 0,5 ft', 'Mais de 1,5', 'Mais de 2,5', 'Mais de 3,5',
            'Menos de 1,5 HT', 'Menos de 1,5', 'Menos de 2,5', 'Menos de 3,5', 'Menos de 4,5', 'Menos de 6,5'
        ]
        
        num_cols = 4
        cols = st.columns(num_cols)
        for i, market_name in enumerate(markets_to_display):
            if market_name in filtered_df.columns:
                rate = filtered_df[market_name].mean() * 100
                cols[i % num_cols].metric(market_name, f"{rate:.2f}%")
            
    with tab2:
        st.header("Análise de Cenários de Jogo")
        scenarios = analyze_scenarios(filtered_df)

        st.subheader("Cenário: Jogo Empatado no Intervalo (HT)")
        if 'tied_at_ht' in scenarios:
            scenario = scenarios['tied_at_ht']
            c1, c2, c3 = st.columns(3)
            c1.metric("Nº de Jogos Empatados no HT", f"{scenario['total_cases']}")
            c2.metric("% de Vitória da Casa no Final", f"{scenario['home_win_rate']:.2f}%", delta_color="off")
            c3.metric("% de Vitória do Visitante no Final", f"{scenario['away_win_rate']:.2f}%", delta_color="off")
        else: st.info("Não há jogos empatados no intervalo para analisar.")

        st.markdown("---")
        
        st.subheader("Cenário: Liderança Segura?")
        c1, c2 = st.columns(2)
        with c1:
            if 'casa_2x0_lead' in scenarios:
                scenario = scenarios['casa_2x0_lead']
                st.metric("Casa abriu 2x0 no HT", f"{scenario['total_cases']} vezes")
                st.metric("E ganhou o jogo FT", f"{scenario['final_win_rate']:.2f}%")
            else: st.info("Nenhum jogo onde a casa abriu 2-0 no HT.")
        with c2:
            if 'fora_0x2_lead' in scenarios:
                scenario = scenarios['fora_0x2_lead']
                st.metric("Fora abriu 0x2 no HT", f"{scenario['total_cases']} vezes")
                st.metric("E ganhou o jogo FT", f"{scenario['final_win_rate']:.2f}%")
            else: st.info("Nenhum jogo onde o visitante abriu 0-2 no HT.")
            
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
        st.header("Desempenho do Placar Exato (Correct Score)")
        cs_df = analyze_correct_score_table(filtered_df)
        if not cs_df.empty:
            st.dataframe(
                cs_df.style.format({'Taxa de Acerto (%)': '{:.2f}%'}).bar(subset=['Acertos'], color='#2e86de', align='zero'),
                use_container_width=True,
                height=500 
            )
        else:
            st.warning("Não foi possível gerar a tabela de placares.")
else:
    st.info("👋 Bem-vindo ao BetAnalyzer Pro! Por favor, carregue sua planilha na barra lateral para começar.")
