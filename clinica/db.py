"""Conexões, transações SQL Server e projeção documental de instância única."""
import json
import os
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import pymssql
from flask import current_app

ROOT = Path(__file__).resolve().parents[1]


def agora():
    return datetime.now(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None, microsecond=0)


def conectar(database=None, admin=False, autocommit=False):
    cfg = current_app.config
    return pymssql.connect(
        server=cfg["SQL_HOST"], port=cfg["SQL_PORT"],
        user=cfg["SQL_ADMIN"] if admin else cfg["SQL_USER"],
        password=cfg["SQL_ADMIN_PASSWORD"] if admin else cfg["SQL_PASSWORD"],
        database=database or cfg["SQL_DATABASE"], as_dict=True,
        charset="UTF-8", login_timeout=5, timeout=8, autocommit=autocommit,
        appname="PIMVI",
    )


def consultar(cursor, sql, params=()):
    cursor.execute(sql, params)
    return cursor.fetchall()


@contextmanager
def transacao(escrita=False, admin=False):
    conn = conectar(admin=admin)
    try:
        cursor = conn.cursor()
        if escrita:
            # Serializa as escritas do protótipo, inclusive duas chamadas simultâneas.
            cursor.execute("""
                DECLARE @resultado int;
                EXEC @resultado=sp_getapplock @Resource='clinica-mutations',
                    @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=5000;
                IF @resultado < 0 THROW 50001, 'Escrita ocupada', 1;
            """)
        yield cursor
        conn.commit()
    finally:
        conn.close()


def inserir(cursor, tabela, colunas, valores):
    # Tabela e colunas são constantes internas; os valores são parametrizados.
    marcas = ", ".join(["%s"] * len(valores))
    sql = f"INSERT clin.{tabela} ({', '.join(colunas)}) OUTPUT INSERTED.id VALUES ({marcas})"
    return consultar(cursor, sql, valores)[0]["id"]


def documento(cursor, tipo, entidade_id, dados):
    chave = uuid4().hex
    stamp = agora()
    registro = {"schema": 1, "id": chave, "tipo": tipo, "entidade_id": entidade_id,
                "criado_em": stamp.isoformat(), **dados}
    cursor.execute(
        "INSERT clin.documento_pendente VALUES (%s,%s,%s,%s,%s)",
        (chave, tipo, entidade_id, stamp, json.dumps(registro, ensure_ascii=False)),
    )


def documentos(tipo, entidade_id=None):
    """Reconcilia a projeção JSON a partir dos eventos confirmados e consulta seus documentos."""
    sql = "SELECT id,conteudo FROM clin.documento_pendente WHERE tipo=%s"
    params = (tipo,)
    if entidade_id is not None:
        sql += " AND entidade_id=%s"
        params += (entidade_id,)
    with transacao() as cursor:
        registros = consultar(cursor, sql + " ORDER BY criado_em,id", params)
    pasta = Path(current_app.config["DOC_DIR"]) / tipo
    pasta.mkdir(parents=True, exist_ok=True, mode=0o700)
    resultado = []
    for row in registros:
        destino = pasta / (row["id"] + ".json")
        if not destino.exists():
            fd, temporario = tempfile.mkstemp(dir=pasta)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
                    arquivo.write(row["conteudo"])
                os.replace(temporario, destino)
            finally:
                Path(temporario).unlink(missing_ok=True)
        resultado.append(json.loads(destino.read_text(encoding="utf-8")))
    return resultado


def migrar():
    banco = current_app.config["SQL_DATABASE"]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,62}", banco):
        raise ValueError("Nome de banco inválido.")
    conn = conectar("master", admin=True, autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(f"IF DB_ID(%s) IS NULL CREATE DATABASE [{banco}];", (banco,))
    finally:
        conn.close()
    with transacao(escrita=True, admin=True) as cursor:
        cursor.execute("IF SCHEMA_ID('clin') IS NOT NULL SELECT 1 AS instalado ELSE SELECT 0 AS instalado")
        if cursor.fetchone()["instalado"]:
            return
        script = (ROOT / "sql/01_schema.sql").read_text()
        for lote in re.split(r"^GO\s*$", script, flags=re.M):
            if lote.strip():
                cursor.execute(lote)
