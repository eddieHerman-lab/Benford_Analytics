import re
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from scipy.stats import chisquare

# Configuração da página
st.set_page_config(page_title="Benford Analytics", layout="wide",
                   initial_sidebar_state="expanded")


# Função para extrair o primeiro dígito com tratamento robusto
def extract_first_digit(x):
    """
    Extrai o primeiro dígito significativo de um número com normalização robusta.
    Trata vários formatos, incluindo moedas e valores formatados.
    """
    if pd.isna(x):  # Tratar NaN explicitamente
        return None

    try:
        # Converter para string primeiro para tratar formatos especiais
        # Usar str(x) para garantir que funciona com qualquer tipo (número, string, etc.)
        x_str = str(x)

        # Remover caracteres não numéricos (exceto ponto e vírgula e sinal negativo)
        # Funciona para formatos como "R$ 1.234,56" ou "$1,234.56"
        # Adicionado tratamento para sinal negativo
        x_clean = re.sub(r'[^\d.,\-]', '', x_str)

        # Normalizar separadores (considerando formatos internacionais)
        if ',' in x_clean and '.' in x_clean:
            # Formato brasileiro: 1.234,56 -> remove '.', substitui ',' por '.'
            if x_clean.find(',') > x_clean.find('.'):
                x_clean = x_clean.replace('.', '').replace(',', '.')
            # Formato americano: 1,234.56 -> remove ','
            else:
                x_clean = x_clean.replace(',', '')
        # Vírgula como separador decimal e sem ponto (ex: "123,45")
        elif ',' in x_clean and '.' not in x_clean:
            x_clean = x_clean.replace(',', '.')

        # Tentar converter para float
        x_float = float(x_clean)

        # Lidar com zeros e negativos após a conversão para float
        if x_float == 0:
            return None

        # Garantir que trabalhamos com o valor absoluto para o primeiro dígito
        x_abs = abs(x_float)

        # Normalizar para obter o primeiro dígito significativo
        # Trata casos como 0.00123 -> 1.23 ou 123.45 -> 1.23
        if x_abs < 1:
            while x_abs < 1:
                x_abs *= 10
        elif x_abs >= 10:
            while x_abs >= 10:
                x_abs /= 10

        # O primeiro dígito é a parte inteira
        first_digit = int(x_abs)

        # Deve estar entre 1 e 9. Se for 0 (acontece com números muito pequenos tipo 0.000...)
        # a normalização já deveria ter tratado, mas como segurança...
        if first_digit == 0:
            # Isso não deve acontecer com a normalização acima, mas é um fallback
            return None  # Ou retornar 1 se assumirmos que 0.0...1 deve começar com 1?

        return first_digit

    except (ValueError, TypeError, AttributeError):
        # Captura erros de conversão ou atributos inesperados
        return None


# Função para normalizar os dados
def normalize_dataframe(df):
    """
    Prepara o DataFrame para análise, normalizando valores e detectando colunas numéricas.
    """
    # Criar uma cópia para evitar modificar o original
    df_clean = df.copy()

    # Lista para armazenar colunas potencialmente numéricas após conversão
    potential_numeric_cols = []

    # Verificar cada coluna
    for col in df_clean.columns:
        # Se já é numérica, adicionar à lista e continuar
        if pd.api.types.is_numeric_dtype(df_clean[col]):
            potential_numeric_cols.append(col)
            continue

        # Se coluna de objeto (comum para strings)
        if pd.api.types.is_object_dtype(df_clean[col]) or pd.api.types.is_string_dtype(df_clean[col]):
            # Tentar converter valores formatados em números usando a lógica do extract_first_digit
            try:
                # Criar uma nova coluna com a tentativa de conversão para float
                # Reutilizamos a lógica de limpeza do extract_first_digit para a conversão
                df_clean[f"{col}_numeric"] = df_clean[col].apply(
                    lambda x: None if pd.isna(x) or str(x).strip() == ''
                    else re.sub(r'[^\d.,\-+]', '', str(x).replace(',', '.'))  # Apply basic cleaning
                )

                # Tentativa final de converter para float, com errors='coerce' para transformar falhas em NaN
                df_clean[f"{col}_numeric"] = pd.to_numeric(
                    df_clean[f"{col}_numeric"], errors='coerce'
                )

                # Verificar se a nova coluna numérica tem valores válidos (não todos NaN)
                if not df_clean[f"{col}_numeric"].isna().all():
                    # Verificar quantos valores foram convertidos com sucesso
                    successfully_converted = df_clean[f"{col}_numeric"].notna().sum()
                    original_non_na = df_clean[col].notna().sum()

                    # Heurística: se uma fração razoável dos valores originais não nulos foi convertida
                    # Isso é um indicador de que a coluna *poderia* ser numérica
                    if original_non_na > 0 and successfully_converted / original_non_na > 0.5:  # Ajuste este limiar se necessário
                        potential_numeric_cols.append(f"{col}_numeric")
                        st.info(
                            f"A coluna '{col}' foi tratada e identificada como potencialmente numérica ('{col}_numeric').")
                    else:
                        # Se a conversão falhou para a maioria, remover a coluna temporária
                        df_clean = df_clean.drop(columns=[f"{col}_numeric"])
                        # st.info(f"Coluna '{col}' não parece ser numérica após tratamento.") # Opcional, pode poluir o log
                else:
                    # Se todos os valores resultaram em NaN após a conversão, remover a coluna temporária
                    df_clean = df_clean.drop(columns=[f"{col}_numeric"])
                    # st.info(f"Coluna '{col}' não parece ser numérica após tratamento.") # Opcional

            except Exception as e:
                # Capturar e reportar erros durante o processo de conversão de uma coluna específica
                st.warning(f"Erro inesperado ao tentar converter coluna '{col}': {str(e)}")
                # Garantir que a coluna temporária seja removida em caso de erro
                if f"{col}_numeric" in df_clean.columns:
                    df_clean = df_clean.drop(columns=[f"{col}_numeric"])

    # Remover colunas temporárias que foram criadas mas não identificadas como numéricas (segurança)
    cols_to_drop_temp = [c for c in df_clean.columns if c.endswith('_numeric') and c not in potential_numeric_cols]
    df_clean = df_clean.drop(columns=cols_to_drop_temp)

    return df_clean, potential_numeric_cols


# Função para criar o PDF
def create_pdf(observed_counts, benford_dist, chi2, p_value, total_count, column_name, mad, sad):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    styles = getSampleStyleSheet()
    # Estilos básicos
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    # Adicionar ou modificar estilos para a conclusão, se desejar cores/ênfase
    h3_style = styles['Heading3']  # Estilo para subtítulos menores

    # Título e informações
    elements.append(Paragraph("Relatório de Análise pela Lei de Benford", title_style))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Coluna analisada: {column_name}", subtitle_style))
    elements.append(Paragraph(f"Total de registros analisados: {total_count}", normal_style))  # Clarify 'analisados'
    elements.append(Spacer(1, 12))

    # Resultados do teste e métricas de desvio
    elements.append(Paragraph("Resultados da Análise Estatística:", subtitle_style))
    elements.append(Paragraph(f"Estatística Chi²: {chi2:.4f}", normal_style))
    elements.append(Paragraph(f"Valor-p: {p_value:.4f}", normal_style))
    # Adicionamos MAD e SAD
    elements.append(Paragraph(f"Mean Absolute Deviation (MAD): {mad * 100:.2f}%", normal_style))
    elements.append(Paragraph(f"Sum of Absolute Differences (SAD): {sad * 100:.2f}%", normal_style))

    # Conclusão baseada na nova lógica (similar ao Streamlit)
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Conclusão da Análise:", subtitle_style))

    # Use os mesmos limiares definidos na lógica do Streamlit
    mad_threshold_strict = 0.010
    mad_threshold_moderate = 0.005

    if p_value < 0.05:
        if mad >= mad_threshold_strict:
            conclusion_text = "ALTA SUSPEITA DE ANOMALIA/MANIPULAÇÃO 🚨: Desvio estatisticamente significativo (p < {:.4f}) E tamanho médio do desvio (MAD = {:.2f}%) considerado alto.".format(
                0.05, mad * 100)
            elements.append(Paragraph(conclusion_text, h3_style))  # Usando H3 para destacar
        elif mad >= mad_threshold_moderate:
            conclusion_text = "SUSPEITA MODERADA DE ANOMALIA 🤔: Desvio estatisticamente significativo (p < {:.4f}), mas tamanho médio do desvio (MAD = {:.2f}%) moderado. Recomenda-se investigação e análise contextual.".format(
                0.05, mad * 100)
            elements.append(Paragraph(conclusion_text, h3_style))  # Usando H3
        else:
            conclusion_text = "DESVIO ESTATÍSTICO (BAIXA SUSPEITA) 📉: Desvio estatisticamente significativo (p < {:.4f}), mas tamanho médio do desvio (MAD = {:.2f}%) baixo. Isso pode ocorrer naturalmente em amostras grandes. Recomenda-se inspeção visual e contexto.".format(
                0.05, mad * 100)
            elements.append(Paragraph(conclusion_text, normal_style))  # Estilo normal
    else:
        conclusion_text = "CONFORME ESPERADO ✅: Os dados seguem a Lei de Benford conforme esperado (p >= {:.4f}). Não há evidência estatística forte de anomalias nos primeiros dígitos.".format(
            0.05)
        elements.append(Paragraph(conclusion_text, normal_style))  # Estilo normal

    elements.append(Spacer(1, 12))

    # Tabela detalhada
    data = [["Dígito", "Contagem", "Observado (%)", "Esperado (%)", "Diferença (%)"]]

    # Garantir que os dados da tabela estejam na ordem correta e completos (dígitos 1-9)
    for d in range(1, 10):
        obs_count = observed_counts.get(d, 0)
        # Calcular porcentagens e diferenças com base no total_count passado (registros válidos)
        obs_pct = (obs_count / total_count) * 100 if total_count > 0 else 0
        # A distribuição de Benford (benford_dist) já deve ser as proporções (ex: 0.301)
        benford_pct = benford_dist[d - 1] * 100
        diff = obs_pct - benford_pct

        data.append([
            str(d),
            f"{obs_count:,.0f}",  # Formatando contagem
            f"{obs_pct:.2f}%",
            f"{benford_pct:.2f}%",
            f"{diff:+.2f}%"
        ])

    # Criar e estilizar a tabela
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Cor para as linhas de dados
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    elements.append(table)
    elements.append(Spacer(1, 12))

    # Informações sobre a Lei de Benford (existente)
    elements.append(Paragraph("Sobre a Lei de Benford:", subtitle_style))
    elements.append(Paragraph("""
    A Lei de Benford (também conhecida como Lei do Primeiro Dígito) é um fenômeno matemático
    que descreve a distribuição de frequência do primeiro dígito em muitos conjuntos de dados do mundo real.
    De acordo com esta lei, o dígito 1 aparece como o primeiro dígito em cerca
    de 30% dos casos, enquanto dígitos maiores aparecem com frequência cada vez menor.

    Um desvio significativo desta distribuição pode indicar dados manipulados ou anômalos.
    O teste estatístico aplicado (chi-quadrado) ajuda a quantificar o grau de conformidade
    dos dados com a distribuição esperada pela Lei de Benford.
    As métricas MAD (Mean Absolute Deviation) e SAD (Sum of Absolute Differences) fornecem
    uma medida do tamanho total do desvio em relação à distribuição esperada.
    """, normal_style))  # Adicionada menção a MAD/SAD

    # Gerar o PDF
    doc.build(elements)
    return buffer


# Interface do usuário em abas
tab1, tab2 = st.tabs(["Análise de Benford", "Sobre a Lei de Benford"])

with tab1:
    st.title("📊 Análise de Benford para Detecção de Anomalias")

    # Upload do arquivo
    uploaded_file = st.file_uploader("Carregue seu arquivo (CSV ou Excel)",
                                     type=["csv", "xlsx", "xls", "ods"])

    if uploaded_file is not None:
        # Processar o arquivo
        try:
            # Obter a extensão do arquivo
            file_extension = uploaded_file.name.split('.')[-1].lower()

            df = None  # Inicializa df como None

            # Lógica para ler diferentes tipos de arquivo
            if file_extension == 'csv':
                # Tentar diferentes encodings para CSV (seu código existente)
                encodings = ['utf-8', 'latin-1', 'ISO-8859-1', 'cp1252']
                for encoding in encodings:
                    try:
                        uploaded_file.seek(0)  # Volta o ponteiro para o início para cada tentativa
                        df = pd.read_csv(uploaded_file, encoding=encoding)
                        # --- INSERIR WORKAROUND DA CÓPIA AQUI (CSV) ---
                        df = pd.DataFrame(df.values, columns=df.columns, index=df.index)
                        st.success(f"Arquivo CSV lido com codificação {encoding}")
                        break
                    except Exception:
                        continue

                if df is None or df.empty:
                    st.error("Não foi possível ler o arquivo CSV. Tente converter para Excel ou um encoding diferente.")
                    st.stop()

            # Lógica para ler arquivos Excel (.xlsx, .xls)
            elif file_extension in ['xlsx', 'xls']:
                try:
                    # Para Excel, tentamos múltiplos engines para compatibilidade
                    excel_engines = ['openpyxl', 'xlrd', 'pyxlsb']  # Ordem de preferência
                    read_success = False

                    for engine_name in excel_engines:
                        try:
                            uploaded_file.seek(0)
                            xls = pd.ExcelFile(uploaded_file, engine=engine_name)
                            sheet_name = st.selectbox("Selecione a planilha:", xls.sheet_names)
                            df = pd.read_excel(uploaded_file, sheet_name=sheet_name, engine=engine_name)

                            # Aplicar workaround de cópia
                            df = pd.DataFrame(df.values, columns=df.columns, index=df.index)
                            st.success(f"Arquivo Excel lido com engine '{engine_name}'.")
                            read_success = True
                            break  # Sai do loop se conseguir ler
                        except ImportError:
                            # Ignora se o engine não está instalado, tenta o próximo
                            continue
                        except Exception as e:
                            # Captura outros erros de leitura para este engine e tenta o próximo
                            continue

                    if not read_success or df is None or df.empty:
                        st.error("Não foi possível ler o arquivo Excel com nenhum engine disponível.")
                        st.stop()

                except Exception as e_xl:
                    st.error(f"Erro ao processar arquivo Excel: {e_xl}")
                    st.stop()

            # Lógica para ler arquivos ODS (.ods)
            elif file_extension == 'ods':
                try:
                    uploaded_file.seek(0)
                    # Tente ler diretamente
                    df = pd.read_excel(uploaded_file, engine='odf')

                    # Se chegou aqui, a leitura foi bem-sucedida
                    # Aplicar workaround de cópia
                    df = pd.DataFrame(df.values, columns=df.columns, index=df.index)
                    st.success("Arquivo ODS lido com sucesso.")

                except ImportError:
                    st.error("""
                       Para ler arquivos ODS (.ods), por favor instale a biblioteca `odfpy`.
                       Abra seu terminal e execute:
                       `pip install odfpy`
                       Reinicie o aplicativo Streamlit após a instalação.
                       """)
                    st.stop()  # Para a execução se a biblioteca não estiver instalada

                except Exception as e_ods:
                    st.error(f"Não foi possível ler o arquivo ODS: {e_ods}")
                    st.stop()

            else:
                st.error(f"Formato de arquivo não suportado: .{file_extension}. Formatos aceitos: csv, xlsx, xls, ods")
                st.stop()

            # Mostrar dados
            st.subheader("Visualização do Arquivo")
            st.dataframe(df.head())

            # Opções avançadas de preprocessamento
            with st.expander("Opções Avançadas de Preprocessamento"):
                skip_rows = st.number_input("Pular linhas iniciais", 0, 100, 0,
                                            help="Número de linhas a ignorar no início do arquivo.")
                if skip_rows > 0 and len(df) > skip_rows:
                    df = df.iloc[skip_rows:].reset_index(drop=True)
                    st.write(f"Ignoradas {skip_rows} linhas iniciais.")

                # Opção para remover linhas com valores nulos em *todas* as colunas
                if st.checkbox("Remover linhas completamente vazias"):
                    old_len = len(df)
                    df = df.dropna(how='all')
                    st.write(f"Removidas {old_len - len(df)} linhas vazias.")

                # Opção para remover colunas específicas
                if st.checkbox("Remover colunas selecionadas"):
                    cols_to_drop = st.multiselect("Selecione colunas para remover:", df.columns,
                                                  help="Selecione as colunas que não devem ser consideradas na análise ou pré-processamento.")
                    if cols_to_drop:
                        df = df.drop(columns=cols_to_drop)
                        st.write(f"Removidas {len(cols_to_drop)} colunas.")

            # Normalização dos dados
            st.subheader("Seleção da Coluna para Análise")
            with st.spinner("Identificando colunas numéricas..."):
                df_clean, potential_numeric_cols = normalize_dataframe(df)  # Usar o df_clean retornado

            if not potential_numeric_cols:
                st.error("Nenhuma coluna identificada como numérica no arquivo!")
                st.info(
                    "Dica: A ferramenta tenta converter colunas de texto com números e formatos monetários, mas pode não reconhecer todos os formatos. Verifique se a coluna de interesse contém dados numéricos válidos.")
                st.stop()  # Parar a execução se não houver colunas numéricas

            # Seleção de coluna e análise
            col = st.selectbox("Selecione a coluna para análise:", potential_numeric_cols)

            # Opções de análise
            with st.expander("Opções de Análise"):
                remove_zeros = st.checkbox("Ignorar valores iguais a zero", value=True,
                                           help="A Lei de Benford se aplica a números positivos e significativos. Zeros geralmente não são incluídos.")
                remove_negatives = st.checkbox("Ignorar valores negativos", value=False,
                                               help="A Lei de Benford tradicionalmente considera o valor absoluto. Marque esta opção para ignorar valores negativos.")
                # Futuramente: opção para usar valor absoluto?

            # Botão para iniciar análise
            if st.button("📊 Iniciar Análise de Benford"):
                with st.spinner("Analisando dados..."):
                    # Preparar dados para análise - usar df_clean que contém colunas numéricas tratadas
                    analysis_data_series = df_clean[col].copy()

                    # Aplicar filtros conforme opções
                    if remove_zeros:
                        analysis_data_series = analysis_data_series[analysis_data_series != 0]
                    if remove_negatives:
                        analysis_data_series = analysis_data_series[analysis_data_series > 0]
                    # Se não remover negativos, talvez usar abs()? Decidi não forçar abs() por padrão,
                    # deixando como opção ou mantendo o filtro de negativos. A função extract_first_digit já usa abs().

                    # Extrair primeiros dígitos usando a função robusta
                    # Aplicar extract_first_digit apenas aos valores não-NaN
                    first_digits = analysis_data_series.dropna().apply(extract_first_digit).dropna()

                    if len(first_digits) < 100:  # Um número razoável de dados para análise significativa
                        st.error(
                            f"Dados insuficientes para análise de Benford após filtragem ({len(first_digits)} registros válidos). Recomenda-se pelo menos ~100 registros.")
                        st.stop()  # Parar se não houver dados suficientes

                    # Mostrar estatísticas básicas
                    st.subheader("Estatísticas Básicas")
                    stats_col1, stats_col2, stats_col3 = st.columns(3)
                    stats_col1.metric("Total de registros na coluna",
                                      f"{len(df_clean[col]):,}")  # Total na coluna antes de filtrar
                    stats_col2.metric("Registros válidos para análise",
                                      f"{len(first_digits):,}")  # Registros após filtros e extração bem sucedida
                    stats_col3.metric("Registros ignorados/inválidos",
                                      f"{len(df_clean[col]) - len(first_digits):,}")  # Diferença

                    # Contagem de dígitos observados
                    observed = first_digits.value_counts().sort_index()

                    # Garantir que todos os dígitos de 1 a 9 estejam representados (com contagem 0 se não apareceram)
                    for d in range(1, 10):
                        if d not in observed.index:
                            observed[d] = 0
                    observed = observed.sort_index()

                    # Verificar se há dados válidos para os dígitos 1-9 (total_observed)
                    total_observed = observed.sum()
                    if total_observed == 0:  # Redundante se já checamos len(first_digits) > 0, mas boa prática
                        st.error("Não foram encontrados dígitos válidos (1-9) para análise após a extração!")
                        st.stop()

                    # Distribuição esperada de Benford (em proporções)
                    benford_proportions = np.log10(1 + 1 / np.arange(1, 10))
                    expected_counts = benford_proportions * total_observed

                    # Teste chi-quadrado - Usar apenas dígitos com frequências esperadas > 0
                    # O teste chi-quadrado padrão do scipy (chisquare) lida bem com zeros observados,
                    # mas espera frequências esperadas > 0. Scipy recomenda exp > 5 para um bom ajuste.
                    # Vamos filtrar exp > 0 para evitar erros, mas alertar sobre baixa contagem esperada.
                    valid_digits_for_chi2 = [d for d in range(1, 10) if
                                             expected_counts[d - 1] > 0]  # Todos os dígitos 1-9 terão exp > 0
                    valid_obs_for_chi2 = [observed.get(d, 0) for d in valid_digits_for_chi2]
                    valid_exp_for_chi2 = [expected_counts[d - 1] for d in valid_digits_for_chi2]

                    # Alerta se frequências esperadas são baixas para alguns dígitos (compromete o teste Chi²)
                    low_expected_count_digits = [d for d in range(1, 10) if
                                                 expected_counts[d - 1] < 5 and expected_counts[d - 1] > 0]
                    if low_expected_count_digits:
                        st.warning(f"""
                         Atenção: As frequências esperadas para os dígitos {low_expected_count_digits} são menores que 5.
                         O teste Chi-Quadrado pode não ser preciso nessas condições.
                         """)

                    if len(valid_obs_for_chi2) < 2:  # Mínimo de 2 categorias para o teste Chi²
                        chi2 = float('nan')
                        p = float('nan')
                        st.warning(
                            "Dados insuficientes com frequência esperada > 0 para realizar o teste estatístico Chi-Quadrado.")
                    else:
                        try:
                            chi2, p = chisquare(valid_obs_for_chi2, valid_exp_for_chi2)
                        except Exception as e:
                            st.error(f"Erro ao calcular o teste Chi-Quadrado: {str(e)}")
                            chi2 = float('nan')
                            p = float('nan')

                    # Calcular métricas de diferença
                    # MAD (Mean Absolute Deviation) - média dos desvios absolutos
                    observed_proportions = observed / total_observed
                    abs_diff = np.zeros(9)
                    for i in range(1, 10):
                        obs_prop = observed_proportions.get(i, 0)
                        benford_prop = benford_proportions[i - 1]
                        abs_diff[i - 1] = abs(obs_prop - benford_prop)

                    # Calcular MAD (Mean Absolute Deviation - Desvio Absoluto Médio)
                    mad = np.mean(abs_diff)

                    # Calcular SAD (Sum of Absolute Differences - Soma das Diferenças Absolutas)
                    sad = np.sum(abs_diff)

                    # Definir limiares para MAD (baseados na literatura)
                    mad_threshold_close = 0.0015  # Aproximadamente conforme
                    mad_threshold_acceptable = 0.005  # Marginalmente conforme
                    mad_threshold_suspect = 0.010  # Não conforme / suspeito
                    mad_threshold_critical = 0.015  # Altamente suspeito

                    # Exibir resultados estatísticos
                    st.subheader("Resultados Estatísticos")

                    stat_cols = st.columns([1, 1, 1, 1])
                    stat_cols[0].metric("Estatística Chi²", f"{chi2:.4f}" if not np.isnan(chi2) else "N/A")
                    stat_cols[1].metric("Valor-p", f"{p:.4f}" if not np.isnan(p) else "N/A")
                    stat_cols[2].metric("MAD", f"{mad * 100:.2f}%" if not np.isnan(mad) else "N/A")
                    stat_cols[3].metric("SAD", f"{sad * 100:.2f}%" if not np.isnan(sad) else "N/A")

                    # Interpretação dos resultados
                    st.subheader("Interpretação dos Resultados")

                    # Classificar o resultado com base no valor-p e MAD
                    if not np.isnan(p) and not np.isnan(mad):
                        if p < 0.05:  # Estatisticamente significativo
                            if mad >= mad_threshold_suspect:
                                st.error(
                                    "🚨 **ALTA SUSPEITA DE ANOMALIA/MANIPULAÇÃO**: Desvio estatisticamente significativo (p < 0.05) E tamanho médio do desvio (MAD) considerado alto.")
                            elif mad >= mad_threshold_acceptable:
                                st.warning(
                                    "🤔 **SUSPEITA MODERADA DE ANOMALIA**: Desvio estatisticamente significativo (p < 0.05), mas tamanho médio do desvio (MAD) moderado. Recomenda-se investigação e análise contextual.")
                            else:
                                st.info(
                                    "📉 **DESVIO ESTATÍSTICO (BAIXA SUSPEITA)**: Desvio estatisticamente significativo (p < 0.05), mas tamanho médio do desvio (MAD) baixo. Isso pode ocorrer naturalmente em amostras grandes. Recomenda-se inspeção visual e contexto.")
                        else:
                            st.success(
                                "✅ **CONFORME ESPERADO**: Os dados seguem a Lei de Benford conforme esperado (p >= 0.05). Não há evidência estatística forte de anomalias nos primeiros dígitos.")
                    else:
                        st.warning(
                            "⚠️ Não foi possível realizar uma interpretação completa devido a limitações nos dados.")

                    # Exibição de contexto
                    st.info("""
                            **Interpretação do MAD (Mean Absolute Deviation)**:
                            - < 0.0015: Forte conformidade com Benford
                            - 0.0015-0.005: Conformidade aceitável
                            - 0.005-0.010: Conformidade marginal, possível anomalia
                            - 0.010-0.015: Não conforme, suspeita moderada
                            - > 0.015: Forte suspeita de anomalia

                            **Interpretação do valor-p**:
                            Um valor-p < 0.05 indica um desvio estatisticamente significativo da distribuição de Benford.
                            """)

                    # Visualização: Gráfico de barras
                    st.subheader("Visualização Comparativa")

                    # Preparação dos dados para visualização
                    viz_data = pd.DataFrame({
                        'Dígito': range(1, 10),
                        'Observado (%)': [observed_proportions.get(d, 0) * 100 for d in range(1, 10)],
                        'Esperado (%)': benford_proportions * 100
                    })

                    # Criar o gráfico de barras
                    fig = px.bar(viz_data, x='Dígito', y=['Observado (%)', 'Esperado (%)'],
                                 barmode='group', title='Distribuição dos Primeiros Dígitos',
                                 labels={'value': 'Porcentagem (%)', 'variable': 'Distribuição'},
                                 color_discrete_sequence=['#5D69B1', '#52BCA3'])

                    # Adicionar linha horizontal para p-value
                    if not np.isnan(p):
                        fig.add_annotation(
                            xref="paper", yref="paper",
                            x=0.5, y=1.05,
                            text=f"Valor-p: {p:.4f} | MAD: {mad * 100:.2f}%",
                            showarrow=False,
                            font=dict(size=14)
                        )

                    st.plotly_chart(fig, use_container_width=True)

                    # Visualização: Linha de discrepância
                    st.subheader("Gráfico de Discrepância")

                    # Calcular diferenças
                    diff_data = pd.DataFrame({
                        'Dígito': range(1, 10),
                        'Diferença (Obs - Esp) %': [(observed_proportions.get(d, 0) - benford_proportions[d - 1]) * 100
                                                    for d in range(1, 10)]
                    })

                    # Criar gráfico de linha/área para destacar discrepâncias
                    fig_diff = go.Figure()

                    # Adicionar linha zero como referência
                    fig_diff.add_trace(go.Scatter(
                        x=list(range(1, 10)),
                        y=[0] * 9,
                        mode='lines',
                        line=dict(color='black', dash='dash'),
                        name='Referência'
                    ))

                    # Adicionar barras de diferença
                    fig_diff.add_trace(go.Bar(
                        x=diff_data['Dígito'],
                        y=diff_data['Diferença (Obs - Esp) %'],
                        marker_color=['red' if diff < 0 else 'green' for diff in diff_data['Diferença (Obs - Esp) %']],
                        name='Discrepância'
                    ))

                    fig_diff.update_layout(
                        title='Discrepância entre Distribuição Observada e Lei de Benford',
                        xaxis_title='Primeiro Dígito',
                        yaxis_title='Diferença (Pontos Percentuais)',
                        xaxis=dict(tickmode='linear', tick0=1, dtick=1)
                    )

                    st.plotly_chart(fig_diff, use_container_width=True)

                    # Tabela detalhada
                    st.subheader("Tabela Detalhada")

                    # Criar tabela de resultados
                    result_table = pd.DataFrame({
                        'Dígito': range(1, 10),
                        'Contagem': [observed.get(d, 0) for d in range(1, 10)],
                        'Observado (%)': [observed_proportions.get(d, 0) * 100 for d in range(1, 10)],
                        'Esperado (%)': benford_proportions * 100,
                        'Diferença (p.p.)': [(observed_proportions.get(d, 0) - benford_proportions[d - 1]) * 100 for d
                                             in range(1, 10)]
                    })

                    # Formatação da tabela
                    result_table['Contagem'] = result_table['Contagem'].map('{:,.0f}'.format)
                    result_table['Observado (%)'] = result_table['Observado (%)'].map('{:.2f}%'.format)
                    result_table['Esperado (%)'] = result_table['Esperado (%)'].map('{:.2f}%'.format)
                    result_table['Diferença (p.p.)'] = result_table['Diferença (p.p.)'].map('{:+.2f}'.format)

                    st.dataframe(result_table, hide_index=True)

                    # Gerar PDF do relatório
                    st.subheader("Exportar Relatório")

                    # Crie um dicionário para mapear índices para contagens observadas
                    observed_counts_dict = {d: observed.get(d, 0) for d in range(1, 10)}

                    # Gerar PDF
                    pdf_buffer = create_pdf(
                        observed_counts=observed_counts_dict,
                        benford_dist=benford_proportions,
                        chi2=chi2,
                        p_value=p,
                        total_count=total_observed,
                        column_name=col,
                        mad=mad,
                        sad=sad
                    )

                    # Botão para download do PDF
                    st.download_button(
                        label="📥 Baixar Relatório PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=f"relatorio_benford_{col}.pdf",
                        mime="application/pdf"
                    )
        except Exception as analysis_error:
            st.error(f"Erro durante a análise: {analysis_error}")

    with tab2:
        st.title("📚 Sobre a Lei de Benford")

        st.markdown("""
            ## O que é a Lei de Benford?

            A **Lei de Benford**, também conhecida como Lei do Primeiro Dígito, é um fenômeno matemático que descreve a distribuição não uniforme dos primeiros dígitos em muitos conjuntos de dados do mundo real.

            Ao contrário do que se poderia esperar intuitivamente (que cada dígito de 1 a 9 teria igual probabilidade de ocorrência), a Lei de Benford prevê que:

            | Primeiro Dígito | Probabilidade |
            |-----------------|---------------|
            | 1               | 30.1%         |
            | 2               | 17.6%         |
            | 3               | 12.5%         |
            | 4               | 9.7%          |
            | 5               | 7.9%          |
            | 6               | 6.7%          |
            | 7               | 5.8%          |
            | 8               | 5.1%          |
            | 9               | 4.6%          |

            ### Aplicações Práticas

            A Lei de Benford é amplamente utilizada em:

            - **Auditoria financeira**: Identificação de fraudes contábeis
            - **Análise de dados eleitorais**: Detecção de possíveis manipulações
            - **Validação de modelos científicos**: Verificação da naturalidade dos dados
            - **Análise econômica**: Verificação da consistência de indicadores econômicos
            - **Investigações fiscais**: Identificação de declarações fiscais suspeitas

            ### Como funciona a análise?

            A análise pela Lei de Benford compara a distribuição dos primeiros dígitos de um conjunto de dados com a distribuição teórica esperada. Se houver desvios significativos, isso pode indicar:

            1. **Manipulação intencional**: Fraude, falsificação ou fabricação de dados
            2. **Erros sistemáticos**: Problemas na coleta ou processamento dos dados
            3. **Anomalias naturais**: Efeitos de políticas, regras ou limites aplicados aos dados
            4. **Características específicas do domínio**: Alguns conjuntos de dados naturalmente não seguem a Lei de Benford

            ### Limitações

            - Não é aplicável a conjuntos pequenos de dados (geralmente n < 100)
            - Números atribuídos (como códigos postais ou números de telefone) não seguem a lei
            - Números com limites mínimos ou máximos definidos podem apresentar desvios
            - Nem todos os conjuntos de dados naturais seguem a Lei de Benford

            ### Métricas de Análise

            Esta ferramenta utiliza as seguintes métricas:

            - **Teste Chi-Quadrado (χ²)**: Avalia estatisticamente a significância dos desvios
            - **Valor-p**: Indica a probabilidade de observar desvios tão extremos quanto os observados, assumindo que a Lei de Benford é verdadeira
            - **MAD (Mean Absolute Deviation)**: Média dos desvios absolutos entre frequências observadas e esperadas
            - **SAD (Sum of Absolute Differences)**: Soma total dos desvios absolutos

            ### Interpretação dos Resultados

            - **Valor-p < 0.05**: Indica desvio estatisticamente significativo da Lei de Benford
            - **MAD > 0.015**: Forte indício de anomalias
            - **MAD entre 0.010 e 0.015**: Suspeita moderada de anomalias
            - **MAD entre 0.005 e 0.010**: Conformidade marginal, requer análise contextual
            - **MAD < 0.005**: Boa conformidade com a Lei de Benford
            """)

        # Adicionar visualização da distribuição de Benford
        st.subheader("Visualização da Lei de Benford")

        # Criar dados para visualização
        benford_data = pd.DataFrame({
            'Dígito': range(1, 10),
            'Probabilidade (%)': np.log10(1 + 1 / np.arange(1, 10)) * 100
        })

        # Gráfico da Lei de Benford
        fig_benford = px.bar(benford_data, x='Dígito', y='Probabilidade (%)',
                             title='Distribuição de Benford (Lei do Primeiro Dígito)',
                             labels={'Probabilidade (%)': 'Frequência Esperada (%)'},
                             color_discrete_sequence=['#52BCA3'])

        fig_benford.update_layout(
            xaxis=dict(tickmode='linear', tick0=1, dtick=1),
            yaxis=dict(range=[0, 35])
        )

        st.plotly_chart(fig_benford, use_container_width=True)

        st.info("""
            **Fórmula da Lei de Benford**: 

            A probabilidade de um número em um conjunto de dados começar com o dígito d (onde d = 1, 2, ..., 9) é:

            P(d) = log₁₀(1 + 1/d)

            Por exemplo, a probabilidade do primeiro dígito ser 1 é:
            P(1) = log₁₀(1 + 1/1) = log₁₀(2) ≈ 0.301 ou 30.1%
            """)

        st.markdown("""
            ### Referências e Leituras Adicionais

            1. Benford, F. (1938). The law of anomalous numbers. Proceedings of the American Philosophical Society, 78(4), 551-572.

            2. Nigrini, M. J. (2012). Benford's Law: Applications for forensic accounting, auditing, and fraud detection. John Wiley & Sons.

            3. Durtschi, C., Hillison, W., & Pacini, C. (2004). The effective use of Benford's law to assist in detecting fraud in accounting data. Journal of Forensic Accounting, 5(1), 17-34.

            4. Drake, P. D., & Nigrini, M. J. (2000). Computer assisted analytical procedures using Benford's Law. Journal of Accounting Education, 18(2), 127-146.
            """)

    # Nota de rodapé
    st.markdown("---")
    st.markdown(
        "**Benford Analytics** © 2025 | Ferramenta desenvolvida para análise de dados por meio da Lei de Benford")
    st.caption(
        "Versão 1.0.0 | Esta ferramenta é destinada
