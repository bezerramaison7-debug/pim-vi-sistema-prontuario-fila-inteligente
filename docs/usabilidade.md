# Avaliação de usabilidade

A pesquisa exploratória usou cenários fictícios. Paciente, recepção e médico representam necessidades distintas: reconhecer a senha, operar sob interrupções e consultar o histórico com autorização. O [protótipo de baixa fidelidade](prototipo.html) permite navegar por login, cadastro, agenda, monitor, consultório e histórico. Os registros reais de Chromium estão indicados em [evidências](evidencias/).

## Inspeção técnica e revisões

| Dificuldade observada na inspeção do fluxo | Ajuste | Reteste técnico |
|---|---|---|
| Recuperar o prontuário concluído exigia conhecer um código que o médico raramente tem ao abrir a tela. | Substituição por busca prefixada por nome com filtro por vínculo. | Roteiro do navegador localiza Bruno pelo nome após concluir. |
| A referência de espera poderia ser interpretada como previsão individual. | Texto foi alterado para “Referência para escoar a fila atual”, com unidade e uma sala como referência. | Monitor apresenta contexto, estado de conexão e chamada na viewport móvel. |
| A agenda contém várias marcações e ações repetidas. | Ações agrupadas dentro de cada registro, com estado textual e navegação por foco visível. | Capturas e verificação de largura registradas no roteiro. |

## Três percursos simulados

Executados no Chromium em sessões isoladas, com banco SQL Server recém-semeado. Usuários 1, 2 e 3 designam papéis automatizados. A rodada verifica comportamentos observáveis da interface.

| Usuário | Papel | Resultado | Ponto observado |
|---|---|---|---|
| 1 | Paciente | Encontrou a senha e o Consultório 01 no painel móvel sem recarregar. | Antes da chamada, via apenas a contagem agregada da fila. |
| 2 | Recepção | Cadastrou, confirmou horário livre e registrou a chegada. | O conflito de horário exibiu erro útil, mas apagou a seleção do paciente e voltou ao horário padrão. |
| 3 | Médico | Chamou a senha, concluiu o atendimento e encontrou a nota no histórico. | Uma busca só pelo sobrenome não retornou resultados. O primeiro nome retornou a consulta. |

O [log](evidencias/usabilidade/execucao.txt) e as [capturas por papel](evidencias/usabilidade/) registram essa execução. O tempo registrado é a latência de atualização do painel. Tempos de leitura, comentários e pedidos de ajuda exigiriam participantes reais.

Melhorias propostas: preservar os dados preenchidos em caso de conflito, esclarecer a busca por prefixo e avaliar uma forma de informar a espera individual sem expor a identidade da pessoa.

### Reproduzir

Com base recém-semeada, aplicação em execução e Playwright instalado, execute `python tests/usabilidade_simulada.py`. O script altera a base de demonstração e lê `DEMO_PASSWORD` do ambiente. Pode-se configurar o endereço e o destino das evidências por `APP_URL` e `EVIDENCIAS`.
