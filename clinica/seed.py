"""Cadastros e agenda de referência com dados integralmente sintéticos."""
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from .db import agora, consultar, inserir, transacao
from .fluxo import novo_agendamento


def carregar(senha):
    hash_senha = generate_password_hash(senha)
    with transacao(escrita=True) as cur:
        if consultar(cur, "SELECT id FROM clin.usuario WHERE login='recepcao'"):
            return
        unidade = inserir(cur, "unidade", ("nome",), ("Clínica Horizonte",))
        salas = [inserir(cur, "consultorio", ("unidade_id", "nome"), (unidade, f"Consultório {i:02d}"))
                 for i in (1, 2)]
        profissionais = [inserir(cur, "profissional", ("nome", "especialidade"), (nome, "Clínica geral"))
                         for nome in ("Dra. Luna Exemplo", "Dr. Caio Exemplo")]
        for login, perfil, profissional in (("recepcao", "recepcao", None),
                ("medico", "medico", profissionais[0]), ("medico2", "medico", profissionais[1])):
            inserir(cur, "usuario", ("login", "senha_hash", "perfil", "profissional_id"),
                   (login, hash_senha, perfil, profissional))
        hoje = agora().replace(hour=8, minute=0, second=0)
        for i, nome in enumerate(("Aline Exemplo", "Bruno Exemplo", "Clara Exemplo", "Davi Exemplo")):
            paciente = inserir(cur, "paciente", ("nome", "nascimento", "telefone"),
                               (nome, date(1985 + i * 4, 3, 15), f"1690000000{i}"))
            novo_agendamento(cur, paciente, profissionais[i // 3], salas[i // 3],
                             hoje + timedelta(minutes=15 * i), "primeira" if i % 2 == 0 else "retorno")
