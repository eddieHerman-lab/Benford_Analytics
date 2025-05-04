from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

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
