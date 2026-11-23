# Evidências executadas em 23 de novembro de 2026

Base sintética no SQL Server 2022 (16.0.4250.1), com aplicação Flask executada localmente em HTTP. Seis testes aprovados. O percurso Chromium 150.0.7871.100 usou sessões independentes de recepção, consultório e monitor público. Seus passos e resultados são reproduzíveis a partir de `tests/`.

- [Resultado da suíte unitária e de integração](testes-sql.txt)
- [Resultado do roteiro de navegador](teste-navegador.txt)
- [Login](01-login.jpg), [cadastro](02-cadastro.jpg) e [agenda com chegadas](03-recepcao.jpg)
- [Painel móvel mostrando a senha chamada](04-monitor-mobile.jpg) e [fila do consultório](05-consultorio.jpg)
- [Histórico com nota JSON recuperada](06-historico.jpg) e [indicadores](07-indicadores.jpg)

A propagação até o DOM do painel levou 4,94 s nessa execução. A API teve p95 de 4,5 ms em 40 leituras locais sequenciais. A consulta e reconstrução documental no fim da demonstração retornaram nove eventos de auditoria e uma nota. As capturas mostram estados sucessivos do mesmo fluxo com o mesmo token de demonstração. A avaliação com colegas tem um [roteiro separado](../usabilidade.md).

- [Rodada complementar de usabilidade simulada](usabilidade/) e [roteiro](../usabilidade.md)
