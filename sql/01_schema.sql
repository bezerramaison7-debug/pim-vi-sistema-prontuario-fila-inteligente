-- Instalado no banco configurado pela CLI. Compatível com SQL Server 2022.
CREATE SCHEMA clin AUTHORIZATION dbo;
GO
CREATE TABLE clin.unidade (
    id int IDENTITY PRIMARY KEY,
    nome nvarchar(100) NOT NULL UNIQUE
);
CREATE TABLE clin.consultorio (
    id int IDENTITY PRIMARY KEY,
    unidade_id int NOT NULL REFERENCES clin.unidade(id),
    nome nvarchar(60) NOT NULL,
    UNIQUE(unidade_id, nome)
);
CREATE TABLE clin.profissional (
    id int IDENTITY PRIMARY KEY,
    nome nvarchar(120) NOT NULL,
    especialidade nvarchar(80) NOT NULL
);
CREATE TABLE clin.usuario (
    id int IDENTITY PRIMARY KEY,
    login nvarchar(80) NOT NULL UNIQUE,
    senha_hash nvarchar(255) NOT NULL,
    perfil varchar(12) NOT NULL CHECK (perfil IN ('recepcao','medico')),
    profissional_id int NULL REFERENCES clin.profissional(id),
    CHECK ((perfil='medico' AND profissional_id IS NOT NULL)
        OR (perfil='recepcao' AND profissional_id IS NULL))
);
CREATE UNIQUE INDEX ux_usuario_profissional ON clin.usuario(profissional_id)
WHERE profissional_id IS NOT NULL;
CREATE TABLE clin.paciente (
    id int IDENTITY PRIMARY KEY,
    nome nvarchar(120) NOT NULL,
    nascimento date NOT NULL,
    telefone varchar(16) NOT NULL
);
CREATE TABLE clin.agendamento (
    id int IDENTITY PRIMARY KEY,
    paciente_id int NOT NULL REFERENCES clin.paciente(id),
    profissional_id int NOT NULL REFERENCES clin.profissional(id),
    consultorio_id int NOT NULL REFERENCES clin.consultorio(id),
    inicio datetime2(0) NOT NULL,
    modalidade varchar(12) NOT NULL CHECK (modalidade IN ('primeira','retorno','encaixe')),
    status varchar(12) NOT NULL DEFAULT 'marcado' CHECK (status IN ('marcado','falta','cancelado','realizado')),
    CHECK (DATEPART(minute, inicio) IN (0,15,30,45) AND DATEPART(second, inicio)=0)
);
-- A agenda usa slots fixos de 15 minutos. Cancelar libera o slot.
CREATE UNIQUE INDEX ux_ag_prof ON clin.agendamento(profissional_id, inicio) WHERE status <> 'cancelado';
CREATE UNIQUE INDEX ux_ag_sala ON clin.agendamento(consultorio_id, inicio) WHERE status <> 'cancelado';
CREATE UNIQUE INDEX ux_ag_paciente ON clin.agendamento(paciente_id, inicio) WHERE status <> 'cancelado';
CREATE INDEX ix_ag_dia ON clin.agendamento(inicio, status) INCLUDE (profissional_id, consultorio_id, paciente_id);
CREATE INDEX ix_ag_historico ON clin.agendamento(paciente_id, inicio DESC);
CREATE INDEX ix_paciente_nome ON clin.paciente(nome, nascimento);
CREATE TABLE clin.fila (
    agendamento_id int PRIMARY KEY REFERENCES clin.agendamento(id),
    senha char(9) NOT NULL UNIQUE,
    chegada datetime2(0) NOT NULL,
    ordem smallint NOT NULL CHECK (ordem IN (0,1)),
    status varchar(14) NOT NULL CHECK (status IN ('aguardando','chamado','em_atendimento','concluido')),
    chamada datetime2(0) NULL,
    inicio_atend datetime2(0) NULL,
    fim datetime2(0) NULL,
    CHECK (chamada IS NULL OR chamada >= chegada),
    CHECK (inicio_atend IS NULL OR inicio_atend >= chamada),
    CHECK (fim IS NULL OR fim >= inicio_atend)
);
CREATE INDEX ix_fila_ordem ON clin.fila(status, ordem DESC, chegada, agendamento_id);
CREATE TABLE clin.atendimento (
    agendamento_id int PRIMARY KEY REFERENCES clin.agendamento(id),
    autor_id int NOT NULL REFERENCES clin.usuario(id),
    registrado_em datetime2(0) NOT NULL,
    resumo nvarchar(500) NOT NULL
);
CREATE TABLE clin.documento_pendente (
    id char(32) PRIMARY KEY,
    tipo varchar(16) NOT NULL CHECK (tipo IN ('auditoria','nota')),
    entidade_id int NOT NULL,
    criado_em datetime2(0) NOT NULL,
    conteudo nvarchar(max) NOT NULL CHECK (ISJSON(conteudo)=1)
);
CREATE INDEX ix_documento ON clin.documento_pendente(tipo, entidade_id, criado_em);
GO
