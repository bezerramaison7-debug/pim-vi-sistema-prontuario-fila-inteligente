# Engenharia e qualidade

**Visão.** A Clínica Horizonte é uma unidade fictícia. Uma agenda compartilhada organiza marcações, o check-in dá origem à fila, e o registro clínico é reservado ao consultório. A solução atende uma unidade de demonstração e admite múltiplos consultórios. Seus objetivos são reduzir conflitos de horário, dar visibilidade à chamada e preservar rastreabilidade do prontuário.

**Planejamento.** Sprint 1 entrega cadastro, segurança básica e integridade da agenda. Sprint 2 entrega o ciclo de atendimento e a projeção JSON. Sprint 3 integra indicadores, avaliação de interface e análise preditiva. Os sprints representam a decomposição do trabalho em incrementos, sem alegação de reuniões com uma equipe. Em cada revisão, os itens são conferidos contra o backlog e a demonstração é executada em banco isolado. A definição de concluído exige implementação, teste do critério de aceite, documentação e evidência proporcional.

## Kanban

| Coluna | Itens |
|---|---|
| A fazer | Sem cartões adicionais nesta entrega |
| Em andamento | Sem cartões em execução na versão registrada |
| Em validação | US12, sessão com colegas |
| Concluído | US01–US11 |

## Responsabilidades

| Atividade | Responsável | Aprovador | Consultado / informado |
|---|---|---|---|
| Escopo e critérios de aceite | Autor do projeto | Autor, no papel acadêmico de responsável pelo produto | Recepção e médico como papéis simulados |
| Código, banco e ML | Autor do projeto | Autor, após verificação | Avaliador recebe repositório e evidências |
| Validação dos fluxos | Autor para roteiros técnicos | Autor para verificação técnica | Avaliador recebe registros |
| Observação com colegas | Autor, como moderador | Autor, após consolidar achados | Colegas, como participantes, ainda a convidar |

## Metas verificáveis

| Aspecto | Critério de aceite para o protótipo |
|---|---|
| Segurança | Proibição de leitura e escrita sem vínculo, sessão expirada, CSRF e ausência de nomes na resposta pública. |
| Eficiência | p95 abaixo de 500 ms em 40 leituras sequenciais locais; propagação no monitor em até 7,2 s no cenário do teste. |
| Capacidade de interação | Teclado, mensagens de status, rótulos e ausência de rolagem horizontal em 360, 768 e 1280 px. |
| Confiabilidade | Concorrência na chamada tem um vencedor; projeção JSON removida é reconciliada; saúde responde 503 quando o banco falha. |
| Disponibilidade | Indicador de indisponibilidade e retomada no monitor. Meta operacional de 99% no horário de serviço é uma hipótese a validar com infraestrutura real. |

Os atributos foram usados como referência de qualidade do produto (ISO/IEC 25010:2023) e os critérios de interface foram inspirados em WCAG 2.2. O escopo da verificação local não equivale a uma certificação, auditoria clínica ou teste de escala.
