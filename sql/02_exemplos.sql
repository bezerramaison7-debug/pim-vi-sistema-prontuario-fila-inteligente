-- Execute na base PIMVI após "flask seed-demo". A demonstração é revertida.
SET XACT_ABORT ON;
BEGIN TRANSACTION;
INSERT clin.paciente(nome,nascimento,telefone)
VALUES (N'Paciente Demonstração SQL','1988-07-15','16900000009');
SELECT id,nome,nascimento FROM clin.paciente WHERE nome LIKE N'Paciente%';
DECLARE @dia date=CONVERT(date, SYSDATETIME());
DECLARE @profissional int=(SELECT MIN(id) FROM clin.profissional);
SELECT a.inicio,a.status,p.nome
FROM clin.agendamento a JOIN clin.paciente p ON p.id=a.paciente_id
WHERE a.inicio>=@dia AND a.inicio<DATEADD(day,1,@dia) AND a.profissional_id=@profissional
ORDER BY a.inicio;
SELECT a.consultorio_id,f.senha,f.chegada,f.ordem
FROM clin.fila f JOIN clin.agendamento a ON a.id=f.agendamento_id
WHERE f.status='aguardando'
ORDER BY a.consultorio_id,f.ordem DESC,f.chegada,f.agendamento_id;
SELECT a.status,COUNT(*) AS total,AVG(CONVERT(float,DATEDIFF(second,f.chegada,f.inicio_atend))/60) AS espera_min
FROM clin.agendamento a LEFT JOIN clin.fila f ON f.agendamento_id=a.id
WHERE a.inicio>=@dia AND a.inicio<DATEADD(day,1,@dia)
GROUP BY a.status;
ROLLBACK TRANSACTION;
