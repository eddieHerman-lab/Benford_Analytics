

# Benford Analytics: Ferramenta para Análise e Detecção de Anomalias pela Lei de Benford

## Descrição do Projeto

Este projeto é uma aplicação web interativa desenvolvida em Python com Streamlit para analisar conjuntos de dados numéricos utilizando a Lei de Benford (Lei do Primeiro Dígito). A ferramenta calcula a distribuição observada dos primeiros dígitos, compara-a com a distribuição esperada pela Lei de Benford e realiza testes estatísticos (Chi-Quadrado) e calcula métricas de desvio (MAD e SAD) para identificar potenciais anomalias nos dados que possam indicar erros, características não-Benfordianas, ou (em alguns contextos) manipulação.

## Funcionalidades

- Carregamento de arquivos nos formatos CSV, Excel (.xlsx, .xls) e ODS (.ods).
- Identificação automática de colunas numéricas e opção de seleção para análise.
- Opções de pré-processamento (pular linhas, remover vazios/colunas).
- Filtros de dados (ignorar zeros, ignorar negativos).
- Cálculo da distribuição observada dos primeiros dígitos (1-9).
- Comparação visual da distribuição observada com a distribuição esperada pela Lei de Benford através de gráfico interativo.
- Cálculo e exibição da Estatística Chi-Quadrado e p-valor para avaliar a significância estatística do desvio.
- Cálculo e exibição do Mean Absolute Deviation (MAD) e Sum of Absolute Differences (SAD) como métricas da magnitude do desvio prático.
- **Conclusão nuançada da análise** baseada na combinação do p-valor e do MAD para diferenciar desvios estatísticos pequenos de anomalias de alta suspeita.
- Detalhamento das frequências e diferenças por dígito em formato tabular.
- Geração e download de um relatório PDF com os resultados da análise.
- Aba "Sobre a Lei de Benford" com explicação conceitual, fórmula, aplicações e limitações da lei.

## Aplicação da Lei de Benford

A Lei de Benford postula que em muitos conjuntos de dados numéricos do mundo real (como dados financeiros, populações, etc. que cobrem várias ordens de magnitude), a frequência do primeiro dígito não é uniforme, sendo o dígito 1 o mais frequente (~30.1%) e os dígitos maiores menos frequentes. Desvios significativos desta distribuição podem ser indicadores de dados anômalos que merecem investigação.

Este projeto utiliza:
- **Teste Qui-Quadrado (Chi²):** Para avaliar a diferença global entre a distribuição observada e a esperada. Um p-valor baixo (< 0.05) indica um desvio estatisticamente significativo.
- **Mean Absolute Deviation (MAD):** Calcula a média das diferenças absolutas nas frequências percentuais. Fornece uma medida da *magnitude* prática do desvio, sendo útil para interpretar resultados em amostras grandes.
- **Sum of Absolute Differences (SAD):** A soma total das diferenças absolutas.
- **Visualização:** Gráficos comparativos são essenciais para identificar padrões de desvio.

A combinação dessas métricas permite uma interpretação mais rica do que apenas o p-valor isolado, ajudando a diferenciar desvios naturais em amostras grandes de anomalias que levantam maior suspeita.

## Como Rodar Localmente

Para rodar este projeto em sua máquina:

1. Clone o repositório:
   ```bash
   git clone [https://github.com/SeuNomeDeUsuario/NomeDoSeuRepositorio.git](https://github.com/SeuNomeDeUsuario/NomeDoSeuRepositorio.git)
   cd NomeDoSeuRepositorio
