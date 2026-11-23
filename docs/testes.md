# Plano de verificação e validação

Ambiente de integração: Python 3.12, Flask e SQL Server 2022, com base descartável e dados sintéticos. A suíte usa `unittest`; o roteiro de aceitação usa Playwright/Chromium contra o servidor HTTP. A validação analítica executa as células do notebook. O plano prevê verificação de regras, integração das tecnologias e aceitação por fluxo. A coluna observada aponta o arquivo de evidência.

| Caso | Cenário e ação | Resultado esperado | Observado |
|---|---|---|---|
| T01 | Entradas válidas e inválidas de horário | Aceitar múltiplo de 15 minutos em horário local | Log SQL |
| T02 | Sessão ausente, token inválido, senha errada e acesso de outro perfil | Redirecionar ou recusar com 400, 401 ou 403 | Log SQL |
| T03 | Cadastrar, buscar, marcar, repetir slot, cancelar e reagendar | Persistência e bloqueio do conflito; slot reutilizável | Log SQL |
| T04 | Duas chegadas, prioridade, chamadas simultâneas, conclusão e auditoria | Uma chamada aceita; histórico e JSON disponíveis; ausência de dados pessoais no feed | Log SQL |
| T05 | Registrar falta antiga, testar falta antecipada e executar DML | Primeira aceita; antecipada bloqueada; script consulta e reverte inserção | Log SQL |
| T06 | 40 acessos ao feed público e saúde da base | Contrato mínimo; p95 menor que 500 ms no cenário | Log SQL |
| TB | Executar a jornada integrada em Chromium e verificar três larguras | Cadastro, chamada e nota confirmados; foco e largura dentro do limite | Log de navegador e capturas |
| TM | Executar notebook e verificar saídas | CSV, figuras, 12 linhas de comparação, previsões e seleção salvas | Artefatos de ML |
| TU | Observar colegas nos papéis simulados | Registro de dificuldades, ajustes e reteste | Pendente |

Evidências em [evidencias/](evidencias/). As capturas são do protótipo em execução com dados sintéticos. As métricas de desempenho descrevem o ambiente local. A validação de carga, a recuperação de falha de infraestrutura e as políticas institucionais de acesso e retenção ficam fora da demonstração.
