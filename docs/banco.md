# Banco relacional e documentos

O [diagrama ER](er.png) representa a relação entre unidade, consultório, agenda e atendimento. Linhas contínuas representam chaves estrangeiras. Linhas tracejadas representam referências documentais, tipadas pela ação ou pelo tipo de evento. Cada marcação pode ter, no máximo, uma fila e um atendimento. O identificador da unidade é recuperado pelo consultório. Os nomes de paciente e profissional são recuperados por junção e não se repetem na agenda. O banco da demonstração contém uma unidade.

## Dicionário relacional

| Tabela | Colunas e restrições principais |
|---|---|
| unidade | `id int` PK identity; `nome nvarchar(100)` único. |
| consultorio | `id int` PK; `unidade_id int` FK; `nome nvarchar(60)` único por unidade. |
| profissional | `id int` PK; `nome nvarchar(120)`; `especialidade nvarchar(80)`. |
| usuario | `id int` PK; `login nvarchar(80)` único; `senha_hash nvarchar(255)`; `perfil varchar(12)`; `profissional_id int` opcional, único se preenchido e obrigatório para médico. |
| paciente | `id int` PK; `nome nvarchar(120)`; `nascimento date`; `telefone varchar(16)`. |
| agendamento | `id int` PK; três FKs int (`paciente_id`, `profissional_id`, `consultorio_id`); `inicio datetime2(0)` múltiplo de 15 min; `modalidade varchar(12)`; `status varchar(12)`. |
| fila | `agendamento_id int` PK/FK; `senha char(9)` única; `ordem smallint` 0 ou 1; `status varchar(14)`; `chegada`, `chamada`, `inicio_atend`, `fim` em `datetime2(0)`. Somente os três últimos admitem ausência. |
| atendimento | `agendamento_id int` PK/FK; `autor_id int` FK; `registrado_em datetime2(0)`; `resumo nvarchar(500)`. |
| documento_pendente | `id char(32)` PK; `tipo varchar(16)`; `entidade_id int` referência lógica; `criado_em datetime2(0)`; `conteudo nvarchar(max)` com `ISJSON=1`. |

## Normalização e índice

Campos relacionais são atômicos, dependem da chave completa e não repetem atributos determinados por outra entidade. Consultório determina a unidade. A agenda referencia profissional e consultório porque um profissional pode atender em salas diferentes em horários diferentes. As reposições de agenda são permitidas após cancelamento por índices únicos filtrados. O índice de fila apoia a seleção por estado, ordem e instante. A demonstração mantém estado operacional atual na fila e estado da marcação na agenda, com transições distintas e conclusão atômica. A carga de apresentação recupera nomes via chave, sem uma tabela clínica desnormalizada. O envelope JSON repete os metadados do índice da caixa de saída por decisão de projeção.

## Documentos de exemplo

```json
{
  "schema": 1,
  "id": "43c7c019a3ff4e479714756a9d3cf781",
  "tipo": "nota",
  "entidade_id": 2,
  "criado_em": "2026-11-23T10:04:00",
  "usuario_id": 2,
  "texto": "Observação sintética."
}
```

Uma nota associa a entidade ao número do agendamento. A auditoria usa o mesmo envelope, com `acao` no lugar de `texto`. Para `leitura_historico`, a entidade é o paciente. Para eventos de transição, é a marcação. A área web de histórico filtra notas por marcação e vínculo profissional. A CLI pode consultar e reconstruir a projeção `flask --app clinica documentos --tipo auditoria --entidade-id 2`. A saída mantém a contagem, e os arquivos reconstruídos podem ser consultados em ambiente isolado. Por exemplo, com jq:

```bash
jq -s 'map(select(.acao=="leitura_historico" and .entidade_id==2))' \
  instance/documentos/auditoria/*.json
```

Inserir a caixa de saída na mesma transação que o atendimento evita que o registro clínico confirme sem o evento associado. A projeção grava um arquivo temporário e usa troca de nome atômica. Uma leitura posterior recria arquivos ausentes pelo identificador, sem duplicar documentos. Limites do protótipo: pouca escala, arquivo local, sem assinatura digital ou versionamento de retificações, e sem replicação do armazenamento documental.
