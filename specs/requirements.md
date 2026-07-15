# Requisitos do Sistema

## Requisitos Funcionais

1. O sistema deve permitir o upload de documentos em formato PDF para uma pasta `./input`.
2. Deve ser possível iniciar uma pipeline que processe todos os PDFs presentes em `./input` e os converta para HTML usando o SDK Python do Docling localmente integrado no backend, fornecendo o progresso e o status da conversão página por página em tempo real.
3. Os arquivos HTML gerados devem ser traduzidos para outro idioma utilizando o modelo `translategemma:4b` que está disponível no Ollama instalado localmente. A tradução deve ser feita de forma eficiente, aproveitando a GPU disponível.
4. A tradução deve ser executada localmente, aproveitando a GPU NVIDIA GeForce 4060 (8GB VRAM).
5. Após a tradução, os arquivos devem ser convertidos para os formatos Word (.docx) e PDF.
6. A aplicação deve oferecer uma interface frontend em Vue.js onde o usuário possa:
   * Enviar PDFs para `./input`.
   * Iniciar e monitorar o progresso da pipeline.
   * Baixar os arquivos resultantes (HTML, traduzidos, Word e PDF).
7. Os arquivos processados devem ser armazenados em uma pasta `./output` organizada por tipo de arquivo e data de processamento.
8. Deve haver um painel grande de logs no frontend (LogsPanel.vue) integrado ao layout principal (App.vue) que:
   * Exiba cada arquivo PDF em processamento de forma individual, detalhando suas três etapas de execução (Conversão HTML, Tradução e Exportação).
   * Utilize uma barra de progresso visual para indicar o progresso e o estado atual de cada etapa (Pendente, Em Execução, Concluída ou Falha).
   * Monitore e exiba a duração de cada etapa em segundos, atualizada em tempo real enquanto estiver ativa.
   * Apresente uma seção expansível ou área de histórico contendo as mensagens brutas do pipeline com seus respectivos timestamps.
9. O sistema deve permitir que o usuário cancele/pare uma pipeline ativa a qualquer momento:
   * A interface do usuário no frontend deve expor um botão visível para parar ou cancelar a execução da pipeline atual.
   * O backend deve interromper cooperativamente a execução de novas etapas no pipeline do job correspondente e definir seu status final como `cancelled` (cancelado).


## Requisitos Não Funcionais

1. O backend deve ser escrito em Python 3.10+ com tipagem estática.
2. Deve usar `uv` para gerenciamento de dependências e execução.
3. O frontend deve ser implementado com Vue.js, utilizando práticas modernas.
4. O processamento de documentos deve ser eficiente e tirar proveito de GPU para tradução.
5. O sistema deve ser executável localmente em ambiente Linux.
6. O código deve seguir boas práticas de modularidade e ser documentado com docstrings no estilo Google.
7. Toda comunicação entre frontend e backend deve ser segura e resiliente (HTTPS ou similar, se aplicável).

