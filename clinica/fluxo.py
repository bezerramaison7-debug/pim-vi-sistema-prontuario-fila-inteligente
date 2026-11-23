"""Regras de agenda, ordenação e transições da fila."""
from datetime import date, datetime, timedelta
from secrets import token_hex

from .db import agora, consultar, documento, inserir

AGENDA = """
SELECT a.id, a.inicio, a.status, a.modalidade, p.nome AS paciente,
       d.nome AS profissional, c.nome AS sala, a.paciente_id, a.profissional_id,
       a.consultorio_id, f.senha, f.status AS fila, f.chegada, f.ordem
FROM clin.agendamento a
JOIN clin.paciente p ON p.id=a.paciente_id
JOIN clin.profissional d ON d.id=a.profissional_id
JOIN clin.consultorio c ON c.id=a.consultorio_id
LEFT JOIN clin.fila f ON f.agendamento_id=a.id
"""

TRANSICOES = {
    "iniciar": ("chamado", "em_atendimento", "inicio_atend"),
    "concluir": ("em_atendimento", "concluido", "fim"),
}


class Regra(ValueError):
    """Violação de regra de atendimento."""


def periodo(dia):
    return date.fromisoformat(dia), date.fromisoformat(dia) + timedelta(days=1)


def horario(valor):
    try:
        instante = datetime.fromisoformat(valor)
    except ValueError:
        raise Regra("Informe data e hora válidas.") from None
    if instante.tzinfo or instante.minute % 15 or instante.second or instante.microsecond:
        raise Regra("Use um horário local múltiplo de 15 minutos.")
    return instante


def novo_agendamento(cursor, paciente, profissional, sala, quando, modalidade):
    if modalidade not in ("primeira", "retorno", "encaixe"):
        raise Regra("Selecione uma modalidade válida.")
    for tabela, chave in (("paciente", paciente), ("profissional", profissional), ("consultorio", sala)):
        if not consultar(cursor, f"SELECT id FROM clin.{tabela} WHERE id=%s", (chave,)):
            raise Regra("Selecione paciente, profissional e consultório cadastrados.")
    if consultar(cursor, """
        SELECT id FROM clin.agendamento WHERE inicio=%s AND status<>'cancelado'
        AND (paciente_id=%s OR profissional_id=%s OR consultorio_id=%s)
    """, (quando, paciente, profissional, sala)):
        raise Regra("Horário ocupado para o paciente, profissional ou consultório.")
    return inserir(cursor, "agendamento", ("paciente_id", "profissional_id", "consultorio_id",
                   "inicio", "modalidade"), (paciente, profissional, sala, quando, modalidade))


def evento(cursor, entidade_id, usuario, acao):
    documento(cursor, "auditoria", entidade_id, {"usuario_id": usuario, "acao": acao})


def recepcao(cursor, agendamento, acao, usuario, prioridade=0):
    if agendamento["status"] != "marcado" or agendamento["fila"]:
        raise Regra("Esta marcação já recebeu uma atualização.")
    instante = agora()
    if acao == "chegada":
        if agendamento["inicio"].date() != instante.date() or prioridade not in (0, 1):
            raise Regra("O check-in requer agendamento de hoje e triagem administrativa válida.")
        senha = "F" + token_hex(4).upper()
        cursor.execute("""INSERT clin.fila(agendamento_id,senha,chegada,ordem,status)
            VALUES (%s,%s,%s,%s,'aguardando')""", (agendamento["id"], senha, instante, prioridade))
        mensagem = f"Chegada confirmada. Senha {senha}."
    elif acao in ("falta", "cancelado"):
        if acao == "falta" and agendamento["inicio"] + timedelta(minutes=15) > instante:
            raise Regra("A falta pode ser registrada a partir de 15 minutos após o horário.")
        cursor.execute("UPDATE clin.agendamento SET status=%s WHERE id=%s", (acao, agendamento["id"]))
        mensagem = "Falta registrada." if acao == "falta" else "Agendamento cancelado."
    else:
        raise Regra("Ação indisponível.")
    evento(cursor, agendamento["id"], usuario, acao)
    return mensagem


def chamar(cursor, profissional, usuario):
    # Fila prioritária administrativa, seguida por ordem de chegada e identificador.
    linhas = consultar(cursor, """
        SELECT TOP(1) f.agendamento_id, a.consultorio_id
        FROM clin.fila f JOIN clin.agendamento a ON a.id=f.agendamento_id
        WHERE a.profissional_id=%s AND f.status='aguardando'
        AND NOT EXISTS (
            SELECT 1 FROM clin.fila x JOIN clin.agendamento y ON y.id=x.agendamento_id
            WHERE x.status IN ('chamado','em_atendimento')
              AND (y.profissional_id=a.profissional_id OR y.consultorio_id=a.consultorio_id))
        ORDER BY f.ordem DESC, f.chegada, f.agendamento_id
    """, (profissional,))
    if not linhas:
        raise Regra("Nenhuma senha disponível. Confira o atendimento em andamento.")
    agendamento = linhas[0]["agendamento_id"]
    cursor.execute("UPDATE clin.fila SET status='chamado',chamada=%s WHERE agendamento_id=%s",
                   (agora(), agendamento))
    evento(cursor, agendamento, usuario, "chamada")
    return agendamento


def atender(cursor, agendamento, acao, usuario, resumo="", nota=""):
    esperado, destino, coluna = TRANSICOES[acao]
    if agendamento["fila"] != esperado:
        raise Regra("A sequência do atendimento precisa ser respeitada.")
    id_ag = agendamento["id"]
    instante = agora()
    if acao == "concluir":
        if not resumo or len(resumo) > 500 or len(nota) > 3000:
            raise Regra("Informe um resumo de até 500 caracteres. A nota aceita até 3.000.")
        cursor.execute("INSERT clin.atendimento VALUES (%s,%s,%s,%s)", (id_ag, usuario, instante, resumo))
        cursor.execute("UPDATE clin.agendamento SET status='realizado' WHERE id=%s", (id_ag,))
        if nota:
            documento(cursor, "nota", id_ag, {"usuario_id": usuario, "texto": nota})
    cursor.execute(f"UPDATE clin.fila SET status=%s,{coluna}=%s WHERE agendamento_id=%s",
                   (destino, instante, id_ag))
    evento(cursor, id_ag, usuario, acao)
