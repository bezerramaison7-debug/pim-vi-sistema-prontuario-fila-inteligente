# Avaliação de usabilidade

A pesquisa exploratória usou cenários fictícios. Paciente, recepção e médico representam necessidades distintas: reconhecer a senha, operar sob interrupções e consultar o histórico com autorização. O [protótipo de baixa fidelidade](prototipo.html) permite navegar por login, cadastro, agenda, monitor, consultório e histórico. Os registros reais de Chromium estão indicados em [evidências](evidencias/).

## Inspeção técnica e revisões

| Dificuldade observada na inspeção do fluxo | Ajuste | Reteste técnico |
|---|---|---|
| Recuperar o prontuário concluído exigia conhecer um código que o médico raramente tem ao abrir a tela. | Substituição por busca prefixada por nome com filtro por vínculo. | Roteiro do navegador localiza Bruno pelo nome após concluir. |
| A referência de espera poderia ser interpretada como previsão individual. | Texto foi alterado para “Referência para escoar a fila atual”, com unidade e uma sala como referência. | Monitor apresenta contexto, estado de conexão e chamada na viewport móvel. |
| A agenda contém várias marcações e ações repetidas. | Ações agrupadas dentro de cada registro, com estado textual e navegação por foco visível. | Capturas e verificação de largura registradas no roteiro. |

## Ciclo moderado com colegas

Preparação: base recém-semeada, papel sorteado e conta de demonstração correspondente. Orientação: executar o cenário sem receber os nomes dos botões. Moderador registra conclusão independente, passos errados, ajuda solicitada e comentários da pessoa. Use um código de participante, sem nome real na planilha. Proposta de aceite: as três tarefas principais concluídas, registrar cada interrupção e repetir o roteiro afetado após o ajuste.

| Papel simulado | Tarefa e sucesso observável | Tempo | Ajuda | Achados |
|---|---|---|---|---|
| Paciente | Identificar se a senha dada foi chamada e qual a sala. | Pendente | Pendente | Pendente |
| Recepcionista | Cadastrar, agendar e registrar chegada, comunicando a senha. | Pendente | Pendente | Pendente |
| Médico | Chamar, iniciar, concluir e recuperar a nota pelo nome. | Pendente | Pendente | Pendente |

Perguntas finais: “Em que momento houve dúvida?”, “Que informação esperava encontrar?” e “O que mudou quando a tela atualizou?”. Priorize falhas que impeçam a conclusão da tarefa e repita com um cenário equivalente. A inspeção automatizada cobre o fluxo e aspectos técnicos. O ciclo com colegas permanece aberto.
