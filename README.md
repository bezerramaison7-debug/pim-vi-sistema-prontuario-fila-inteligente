# PIM VI · Prontuário eletrônico e fila inteligente

A Clínica Horizonte é uma clínica popular fictícia. A recepção cadastra pacientes e agenda consultas, o consultório chama senhas e registra atendimentos e a sala de espera exibe chamadas sem identificar pacientes. A aplicação usa Flask, SQL Server 2022 e documentos JSON. Três experimentos com dados sintéticos investigam espera, falta e lotação.

## Executar a demonstração

Requisitos: Python 3.12 e SQL Server 2022. O Compose abaixo é para máquina x86-64 com Docker e memória compatível com o SQL Server. Também é possível usar uma instância SQL Server existente, ajustando `SQL_HOST`, `SQL_PORT`, `SQL_USER`, `SQL_PASSWORD`, `SQL_ADMIN` e `SQL_ADMIN_PASSWORD`. Use uma base isolada e somente dados fictícios.

```bash
git clone https://github.com/bezerramaison7-debug/pim-vi-sistema-prontuario-fila-inteligente.git
cd pim-vi-sistema-prontuario-fila-inteligente
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` para definir uma senha forte para o SQL Server, outra para os usuários sintéticos e um segredo de sessão aleatório com pelo menos 24 caracteres. Em Bash:

```bash
set -a
source .env
set +a
docker compose up -d
docker compose logs -f sqlserver
```

Ao aparecer “SQL Server is now ready for client connections”, saia dos logs com Ctrl+C e execute:

```bash
python -m flask --app clinica init-db
python -m flask --app clinica seed-demo
python -m flask --app clinica run
```

Abra <http://127.0.0.1:5000>. No PowerShell, ative com `.\.venv\Scripts\Activate.ps1` e defina as três variáveis por `$env:NOME="valor"`. Com SQL Server local, dispense o Compose. Use login SQL dedicado em ambientes compartilhados. O script [03_permissoes.sql](sql/03_permissoes.sql) dá permissões da aplicação a um login existente, e a conta administrativa fica reservada para instalação e testes em base isolada. Os documentos ficam em `instance/documentos/`, configurável por `DOC_DIR`.

## Avaliar os fluxos

1. Acesse como **recepcao** com a senha que você definiu em `DEMO_PASSWORD`. Cadastre um paciente, agende em um horário livre múltiplo de 15 minutos, use os registros de hoje e confirme chegadas.
2. Use **Ordem de chegada** para Aline e **Prioridade administrativa** para Bruno. Em janela anônima, abra [/sala-de-espera](http://127.0.0.1:5000/sala-de-espera).
3. Em outra janela, entre como **medico** com a mesma senha de demonstração. Chame a próxima senha. A de Bruno aparece no monitor com seu consultório. Inicie o atendimento, escreva um resumo e uma nota sintética e conclua.
4. Em **Buscar histórico**, pesquise “Bruno”, abra o registro e confira a nota. O usuário **medico2** não tem vínculo com Bruno. Na sessão da recepção, abra **Indicadores**.
5. Para consultar ou reconciliar documentos de demonstração: `python -m flask --app clinica documentos --tipo auditoria`. A opção `--entidade-id` filtra pelo identificador associado ao evento. Seu resultado padrão exibe somente a contagem.

O feed público responde somente com senhas chamadas, consultórios e medidas agregadas. O monitor consulta o feed a cada cinco segundos e mostra indisponibilidade enquanto tenta reconectar. A referência de espera do monitor é operacional, calculada pela fila atual multiplicada pela duração média recente, com 15 minutos de referência quando ainda não há histórico de duração. Os modelos do notebook são experimentais e separados da operação. A triagem é administrativa e não classifica gravidade.

## Reproduzir testes e análise

```bash
TESTE_SQL_SERVER=1 python -m unittest discover -s tests -v
python -m pip install -r requirements-test.txt
python -m playwright install chromium
EVIDENCIAS=/tmp/pim-vi-evidencias python tests/navegador.py
```

A suíte de integração cria e elimina um banco descartável. O teste de navegador usa uma base de demonstração recém-semeada, exige que o servidor esteja rodando e altera essa base. Se o navegador for fornecido pelo sistema, use `CHROMIUM_PATH`. Para repetir a demonstração sem perder dados preexistentes, selecione um novo nome de base por `SQL_DATABASE`, inicialize e semeie. `/saude` verifica a conexão e a disponibilidade do esquema.

```bash
python -m pip install -r requirements-ml.txt
cd ml
jupyter lab pim_vi.ipynb
```

Execute as células em ordem. O caderno regenera o [CSV sintético](ml/atendimentos.csv), produz a análise exploratória e salva [métricas e previsões](ml/resultados/). Consulte o [dicionário do CSV](ml/dicionario.md).

## Dossiê de avaliação

| Disciplina | Material |
|---|---|
| Engenharia de Software Ágil | [Backlog e sprints](docs/backlog.csv), [Kanban e qualidade](docs/engenharia.md), [plano e resultados de teste](docs/testes.md) |
| Banco de Dados e NoSQL | [Diagrama ER](docs/er.png), [dicionário dos dados e JSON](docs/banco.md), [DDL](sql/01_schema.sql), [DML](sql/02_exemplos.sql) |
| UX e UI Design | [Protótipo navegável](docs/prototipo.html), [wireframes](docs/wireframes.png), [roteiro de observação e avaliação](docs/usabilidade.md), [capturas e logs](docs/evidencias/) |
| Machine Learning e Análise de Dados | [Caderno executado](ml/pim_vi.ipynb), [dados e simulador](ml/), [resultados](ml/resultados/) |

Para navegar no protótipo de baixa fidelidade, baixe `docs/prototipo.html` e abra-o no navegador. O relatório acadêmico com paginação, fundamentação e evidências é entregue em PDF e Word. Os [três percursos de usabilidade simulados](docs/usabilidade.md) foram executados em sessões independentes de navegador. O ambiente é acadêmico e de instância única. A validação operacional deve contemplar TLS, perfis e retenção institucionais, backups e testes de carga e recuperação.
