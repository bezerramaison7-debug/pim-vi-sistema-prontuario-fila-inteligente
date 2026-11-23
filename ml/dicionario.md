# Dicionário do CSV sintético

Uma linha representa uma marcação. O identificador do bloco é seu início no horário local. Sem pessoas reais, identificadores clínicos ou conteúdo de prontuário. Os quatro blocos diários têm a mesma definição durante o experimento. Para lotação conserva-se uma linha por bloco antes de treinar.

| Coluna | Tipo | Significado e disponibilidade |
|---|---|---|
| bloco_inicio | data/hora ISO | início do bloco; usado para agrupar e separar no tempo |
| tipo | categoria | primeira, retorno ou encaixe; conhecido na marcação |
| turno | categoria | manhã ou tarde; conhecido na marcação |
| dia_semana | categoria | dia do bloco; conhecido na marcação |
| antecedencia_dias | inteiro | dias entre marcação e consulta |
| faltas_previas | numérico, opcional | histórico sintético já conhecido na marcação; vazio em cerca de 6% por construção |
| fila_chegada | numérico, opcional | quantidade à frente no check-in; vazio para faltas |
| marcacoes_bloco | inteiro | agenda disponível no início do bloco |
| pendentes_inicio | inteiro | remanescentes já visíveis no início do bloco |
| capacidade_bloco | inteiro | capacidade planejada no início do bloco |
| no_show | alvo binário | 1 se a pessoa faltou, medido após o horário |
| espera_min | alvo decimal | da chegada ao início do atendimento; sem alvo para faltas |
| lotacao | alvo binário | 1 se comparecimentos mais pendências excederam a capacidade do bloco; só conhecido depois |

No sistema, agendamento e fila fornecem modalidade e eventos de início/chegada. Antecedência, histórico, snapshots dos blocos e capacidade foram gerados pelo simulador. O CSV é um cenário experimental alinhado ao domínio, não uma extração operacional.
