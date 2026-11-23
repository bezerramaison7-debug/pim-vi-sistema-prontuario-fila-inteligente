"""Aplicação de demonstração acadêmica do PIM VI."""
import hmac
import os
import re
import secrets
from datetime import date, timedelta
from functools import wraps
from pathlib import Path

import click
import pymssql
from flask import (
    Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import agora, consultar, documentos, inserir, migrar, transacao
from .fluxo import AGENDA, TRANSICOES, Regra, atender, chamar, evento, horario, novo_agendamento, periodo, recepcao


def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("APP_SECRET"),
        SQL_HOST=os.getenv("SQL_HOST", "127.0.0.1"),
        SQL_PORT=os.getenv("SQL_PORT", "1433"),
        SQL_DATABASE=os.getenv("SQL_DATABASE", "PIMVI"),
        SQL_USER=os.getenv("SQL_USER", "sa"),
        SQL_PASSWORD=os.getenv("SQL_PASSWORD", ""),
        SQL_ADMIN=os.getenv("SQL_ADMIN", "sa"),
        SQL_ADMIN_PASSWORD=os.getenv("SQL_ADMIN_PASSWORD", os.getenv("SQL_PASSWORD", "")),
        DOC_DIR=os.getenv("DOC_DIR", str(Path(app.instance_path) / "documentos")),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(minutes=30), MAX_CONTENT_LENGTH=32_768,
    )
    if config:
        app.config.update(config)
    if len(app.config["SECRET_KEY"] or "") < 24:
        raise RuntimeError("Defina APP_SECRET com pelo menos 24 caracteres aleatórios.")
    hash_rejeicao = generate_password_hash(secrets.token_hex(18))

    def exige(perfil):
        def decorator(func):
            @wraps(func)
            def endpoint(*args, **kwargs):
                if not g.usuario:
                    return redirect(url_for("entrar"))
                if g.usuario["perfil"] != perfil:
                    abort(403)
                return func(*args, **kwargs)
            return endpoint
        return decorator

    @app.before_request
    def sessao():
        g.usuario = None
        if request.method == "POST":
            esperado = session.get("csrf", "")
            recebido = request.form.get("csrf", "")
            if not esperado or not recebido.isascii() or not hmac.compare_digest(esperado, recebido):
                abort(400)
        if "uid" in session and request.endpoint not in {"static", "monitor", "status_fila", "saude"}:
            with transacao() as cur:
                rows = consultar(cur, "SELECT id,login,perfil,profissional_id FROM clin.usuario WHERE id=%s",
                                 (session["uid"],))
            if rows:
                g.usuario = rows[0]

    @app.context_processor
    def contexto():
        def csrf():
            if "csrf" not in session:
                session["csrf"] = secrets.token_urlsafe(32)
            return session["csrf"]
        return {"csrf": csrf, "hoje": agora().date().isoformat(),
                "estados": {"marcado": "Marcado", "falta": "Falta", "realizado": "Realizado",
                            "cancelado": "Cancelado", "aguardando": "Aguardando", "chamado": "Chamado",
                            "em_atendimento": "Em atendimento", "concluido": "Concluído"}}

    @app.after_request
    def cabecalhos(resp):
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return resp

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(413)
    def erro_http(erro):
        mensagens = {400: "Revise os dados ou recarregue a página e tente novamente.",
                     403: "Seu perfil não tem acesso a esta operação.",
                     404: "O registro solicitado não foi encontrado.",
                     413: "O conteúdo enviado ultrapassou o limite desta operação."}
        return render_template("erro.html", mensagem=mensagens[erro.code]), erro.code

    @app.errorhandler(pymssql.Error)
    @app.errorhandler(OSError)
    def indisponivel(erro):
        app.logger.error("Falha de armazenamento: %s", type(erro).__name__)
        if request.endpoint in {"saude", "status_fila"}:
            return jsonify(status="indisponivel"), 503
        return render_template("erro.html", mensagem="Serviço temporariamente indisponível. Tente novamente."), 503

    @app.get("/saude")
    def saude():
        with transacao() as cur:
            consultar(cur, "SELECT TOP(1) id FROM clin.unidade")
        return jsonify(status="ok")

    @app.get("/")
    def index():
        if g.usuario:
            return redirect(url_for("agenda" if g.usuario["perfil"] == "recepcao" else "painel"))
        return redirect(url_for("entrar"))

    @app.route("/entrar", methods=["GET", "POST"])
    def entrar():
        if request.method == "POST":
            login = request.form.get("login", "").strip()[:80]
            senha = request.form.get("senha", "")[:256]
            with transacao() as cur:
                rows = consultar(cur, "SELECT id,senha_hash FROM clin.usuario WHERE login=%s", (login,))
            hash_senha = rows[0]["senha_hash"] if rows else hash_rejeicao
            if check_password_hash(hash_senha, senha) and rows:
                session.clear()
                session.permanent = True
                session["uid"] = rows[0]["id"]
                return redirect(url_for("index"))
            flash("Usuário ou senha inválidos.", "erro")
            return render_template("login.html"), 401
        return render_template("login.html")

    @app.post("/sair")
    def sair():
        session.clear()
        return redirect(url_for("entrar"))

    def executar(acao, destino, **dados):
        try:
            with transacao(escrita=True) as cur:
                mensagem = acao(cur)
            flash(mensagem, "ok")
        except Regra as erro:
            flash(str(erro), "erro")
        return redirect(url_for(destino, **dados), code=303)

    @app.route("/recepcao/pacientes", methods=["GET", "POST"])
    @exige("recepcao")
    def pacientes():
        if request.method == "POST":
            def cadastrar(cur):
                nome = request.form.get("nome", "").strip()
                telefone = re.sub(r"[ ()-]", "", request.form.get("telefone", ""))
                try:
                    nascimento = date.fromisoformat(request.form.get("nascimento", ""))
                except ValueError:
                    raise Regra("Informe a data de nascimento.") from None
                if not (3 <= len(nome) <= 120 and date(1900, 1, 1) <= nascimento <= agora().date()
                        and re.fullmatch(r"[0-9]{10,11}", telefone)):
                    raise Regra("Revise nome, nascimento e telefone com DDD.")
                inserir(cur, "paciente", ("nome", "nascimento", "telefone"), (nome, nascimento, telefone))
                return "Paciente cadastrado."
            return executar(cadastrar, "pacientes")
        busca = request.args.get("q", "").strip()[:100]
        prefixo = busca.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]")
        with transacao() as cur:
            registros = consultar(cur, """
                SELECT TOP(50) id,nome,nascimento,telefone FROM clin.paciente
                WHERE nome LIKE %s ORDER BY nome,id
            """, (prefixo + "%",))
        return render_template("pacientes.html", pacientes=registros, busca=busca)

    @app.route("/recepcao", methods=["GET", "POST"])
    @exige("recepcao")
    def agenda():
        if request.method == "POST":
            instante = request.form.get("inicio", "")
            def marcar(cur):
                datahora = horario(instante)
                if datahora < agora() - timedelta(days=1) or datahora > agora() + timedelta(days=365):
                    raise Regra("Selecione um horário dentro da janela de agendamento.")
                novo_agendamento(cur, request.form.get("paciente", type=int),
                                 request.form.get("profissional", type=int), request.form.get("sala", type=int),
                                 datahora, request.form.get("modalidade"))
                return "Consulta agendada."
            try:
                dia_destino = horario(instante).date().isoformat()
            except Regra:
                dia_destino = agora().date().isoformat()
            return executar(marcar, "agenda", dia=dia_destino)
        dia = request.args.get("dia") or agora().date().isoformat()
        try:
            janela = periodo(dia)
        except (ValueError, OverflowError):
            abort(400)
        with transacao() as cur:
            registros = consultar(cur, AGENDA + " WHERE a.inicio >= %s AND a.inicio < %s ORDER BY a.inicio,a.id", janela)
            pessoas = consultar(cur, "SELECT id,nome,nascimento FROM clin.paciente ORDER BY nome,id")
            medicos = consultar(cur, "SELECT id,nome FROM clin.profissional ORDER BY nome")
            salas = consultar(cur, "SELECT id,nome FROM clin.consultorio ORDER BY nome")
        return render_template("agenda.html", registros=registros, pacientes=pessoas, medicos=medicos,
                               salas=salas, dia=dia)

    def obter_agenda(cur, ag_id):
        rows = consultar(cur, AGENDA + " WHERE a.id=%s", (ag_id,))
        if not rows:
            abort(404)
        return rows[0]

    @app.post("/recepcao/<int:ag_id>/<acao>")
    @exige("recepcao")
    def chegada(ag_id, acao):
        def mudar(cur):
            return recepcao(cur, obter_agenda(cur, ag_id), acao, g.usuario["id"],
                           request.form.get("prioridade", 0, type=int))
        return executar(mudar, "agenda")

    @app.get("/indicadores")
    @exige("recepcao")
    def indicadores():
        dia = request.args.get("dia") or agora().date().isoformat()
        try:
            janela = periodo(dia)
        except (ValueError, OverflowError):
            abort(400)
        with transacao() as cur:
            dados = consultar(cur, """
                SELECT COUNT(*) AS total, COUNT(CASE WHEN a.status='falta' THEN 1 END) AS faltas,
                  COUNT(CASE WHEN a.status='realizado' THEN 1 END) AS realizados,
                  COUNT(CASE WHEN f.status='aguardando' THEN 1 END) AS aguardando,
                  AVG(CONVERT(float,DATEDIFF(second,f.chegada,f.inicio_atend))/60.0) AS espera
                FROM clin.agendamento a LEFT JOIN clin.fila f ON f.agendamento_id=a.id
                WHERE a.inicio >= %s AND a.inicio < %s AND a.status<>'cancelado'
            """, janela)[0]
        return render_template("indicadores.html", dados=dados, dia=dia)

    @app.get("/consultorio")
    @exige("medico")
    def painel():
        busca = request.args.get("historico", "").strip()[:100]
        filtro = busca.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]")
        with transacao() as cur:
            registros = consultar(cur, AGENDA + """
                WHERE a.profissional_id=%s AND f.status IN ('aguardando','chamado','em_atendimento')
                ORDER BY CASE f.status WHEN 'em_atendimento' THEN 0 WHEN 'chamado' THEN 1 ELSE 2 END,
                  f.ordem DESC,f.chegada,a.id
            """, (g.usuario["profissional_id"],))
            resultados = consultar(cur, """
                SELECT TOP(30) p.id, p.nome, p.nascimento FROM clin.paciente p
                WHERE p.nome LIKE %s AND EXISTS (
                    SELECT 1 FROM clin.agendamento a JOIN clin.fila f ON f.agendamento_id=a.id
                    WHERE a.paciente_id=p.id AND a.profissional_id=%s
                      AND f.status IN ('chamado','em_atendimento','concluido')
                ) ORDER BY p.nome,p.id
            """, (filtro + "%", g.usuario["profissional_id"])) if busca else []
        return render_template("painel.html", registros=registros, busca=busca, resultados=resultados)

    @app.post("/consultorio/chamar")
    @exige("medico")
    def proximo():
        def chamar_proximo(cur):
            chamar(cur, g.usuario["profissional_id"], g.usuario["id"])
            return "Senha publicada no monitor."
        return executar(chamar_proximo, "painel")

    @app.post("/consultorio/<int:ag_id>/<acao>")
    @exige("medico")
    def consulta(ag_id, acao):
        if acao not in TRANSICOES:
            abort(404)
        def mudar(cur):
            registro = obter_agenda(cur, ag_id)
            if registro["profissional_id"] != g.usuario["profissional_id"]:
                abort(403)
            atender(cur, registro, acao, g.usuario["id"], request.form.get("resumo", "").strip(),
                    request.form.get("nota", "").strip())
            return "Consulta iniciada." if acao == "iniciar" else "Atendimento concluído e registrado."
        return executar(mudar, "painel")

    @app.get("/consultorio/historico/<int:paciente_id>")
    @exige("medico")
    def historico(paciente_id):
        with transacao(escrita=True) as cur:
            rows = consultar(cur, """
                SELECT p.nome FROM clin.paciente p WHERE p.id=%s AND EXISTS (
                    SELECT 1 FROM clin.agendamento a JOIN clin.fila f ON f.agendamento_id=a.id
                    WHERE a.paciente_id=p.id AND a.profissional_id=%s
                      AND f.status IN ('chamado','em_atendimento','concluido'))
            """, (paciente_id, g.usuario["profissional_id"]))
            if not rows:
                abort(403)
            registros = consultar(cur, """
                SELECT t.agendamento_id,t.resumo,t.registrado_em,d.nome AS profissional
                FROM clin.atendimento t JOIN clin.agendamento a ON a.id=t.agendamento_id
                JOIN clin.profissional d ON d.id=a.profissional_id
                WHERE a.paciente_id=%s ORDER BY t.registrado_em DESC,t.agendamento_id DESC
            """, (paciente_id,))
            evento(cur, paciente_id, g.usuario["id"], "leitura_historico")
        for registro in registros:
            registro["notas"] = documentos("nota", registro["agendamento_id"])
        return render_template("historico.html", paciente=rows[0], registros=registros)

    @app.get("/sala-de-espera")
    def monitor():
        return render_template("monitor.html")

    @app.get("/api/fila")
    def status_fila():
        with transacao() as cur:
            dados = consultar(cur, """
                SELECT f.senha, c.nome AS sala FROM clin.fila f
                JOIN clin.agendamento a ON a.id=f.agendamento_id
                JOIN clin.consultorio c ON c.id=a.consultorio_id
                WHERE f.status='chamado' ORDER BY f.chamada DESC,f.agendamento_id DESC
            """)
            aguardando = consultar(cur, """
                SELECT AVG(CONVERT(float,DATEDIFF(second,inicio_atend,fim))/60)
                  AS duracao FROM clin.fila WHERE fim >= %s
            """, (agora() - timedelta(days=7),))[0]
            fila = consultar(cur, "SELECT COUNT(*) AS total FROM clin.fila WHERE status='aguardando'")[0]["total"]
        # Faixa operacional aproximada baseada no volume e na duração histórica, sem uso em triagem.
        duracao = max(1, aguardando["duracao"] or 15)
        return jsonify(chamadas=dados, aguardando=fila, referencia_min=round(fila * duracao))

    @app.cli.command("init-db")
    def init_db():
        migrar()
        click.echo("Esquema SQL Server aplicado.")

    @app.cli.command("seed-demo")
    def seed_demo():
        senha = os.getenv("DEMO_PASSWORD", "")
        if len(senha) < 12:
            raise click.ClickException("Defina DEMO_PASSWORD com pelo menos 12 caracteres.")
        from .seed import carregar
        carregar(senha)
        click.echo("Base sintética preparada. Usuários: recepcao, medico, medico2.")

    @app.cli.command("documentos")
    @click.option("--tipo", type=click.Choice(["nota", "auditoria"]), required=True)
    @click.option("--entidade-id", type=int)
    def projetar_documentos(tipo, entidade_id):
        registros = documentos(tipo, entidade_id)
        click.echo(f"{len(registros)} documentos reconciliados ({tipo}).")

    return app
