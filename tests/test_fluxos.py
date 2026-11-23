"""Verificação unitária e integração com um banco SQL Server descartável."""
import os
import re
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from clinica import create_app
from clinica.db import agora, conectar, consultar, documentos, migrar, transacao
from clinica.fluxo import Regra, horario, novo_agendamento
from clinica.seed import carregar

SENHA = "Teste_Demo_Exclusivo_72!"
CSRF = re.compile(rb'name="csrf" value="([^"]+)"')


def token(client, path):
    return CSRF.search(client.get(path).data)[1].decode()


def login(app, nome):
    client = app.test_client()
    r = client.post("/entrar", data={"csrf": token(client, "/entrar"), "login": nome, "senha": SENHA})
    assert r.status_code == 302
    return client


def post(client, destino, referencia, **params):
    return client.post(destino, data={"csrf":token(client, referencia), **params}, follow_redirects=True)


class TesteUnitario(unittest.TestCase):
    def test_01_validacao_horario(self):
        self.assertEqual(horario("2026-11-23T14:15"), datetime(2026, 11, 23, 14, 15))
        for entrada in ("", "2026-11-23T14:09", "2026-11-23T14:15Z", "2026-11-23T14:15:01"):
            with self.subTest(entrada=entrada), self.assertRaises(Regra):
                horario(entrada)


@unittest.skipUnless(os.getenv("TESTE_SQL_SERVER") == "1", "Execute com TESTE_SQL_SERVER=1 e SQL Server ativo.")
class TesteSql(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.banco = "PimTeste_" + uuid4().hex[:12]
        cls.pasta = tempfile.TemporaryDirectory()
        cls.app = create_app({"TESTING": True, "SECRET_KEY": uuid4().hex,
                              "SQL_DATABASE": cls.banco, "DOC_DIR": cls.pasta.name})
        cls.addClassCleanup(cls.pasta.cleanup)
        cls.addClassCleanup(cls.apagar_banco)
        with cls.app.app_context():
            migrar()
            migrar()
            carregar(SENHA)
            carregar(SENHA)
            with transacao() as cur:
                print("\nMotor SQL Server:", consultar(cur, "SELECT CAST(SERVERPROPERTY('ProductVersion') AS varchar(50)) AS v")[0]["v"], flush=True)

    @classmethod
    def apagar_banco(cls):
        with cls.app.app_context():
            conn = conectar("master", admin=True, autocommit=True)
            try:
                conn.cursor().execute(f"IF DB_ID('{cls.banco}') IS NOT NULL BEGIN "
                    f"ALTER DATABASE [{cls.banco}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE [{cls.banco}]; END")
            finally:
                conn.close()

    def test_02_acesso_autenticacao_csrf(self):
        cliente = self.app.test_client()
        self.assertEqual(cliente.get("/recepcao").status_code, 302)
        self.assertEqual(cliente.post("/entrar", data={}).status_code, 400)
        r = cliente.post("/entrar", data={"csrf":token(cliente,"/entrar"), "login":"recepcao","senha":"invalida"})
        self.assertEqual(r.status_code, 401)
        rec = login(self.app, "recepcao")
        self.assertEqual(rec.get("/consultorio").status_code, 403)
        self.assertEqual(rec.get("/consultorio/historico/1").status_code, 403)
        self.assertEqual(rec.get("/recepcao").headers["Cache-Control"], "no-store")
        self.assertEqual(rec.get("/recepcao?dia=9999-12-31").status_code, 400)
        self.assertEqual(rec.post("/recepcao/1/chegada", data={"csrf": "☃"}).status_code, 400)
        self.assertIn("Acesso da equipe".encode(), post(rec, "/sair", "/recepcao").data)
        self.assertEqual(rec.get("/recepcao").status_code, 302)

    def test_03_agenda_conflitos_e_cancelamento(self):
        rec = login(self.app, "recepcao")
        r = post(rec, "/recepcao/pacientes", "/recepcao/pacientes", nome="Elisa Exemplo",
                 nascimento="1999-01-08", telefone="(16) 90000-0088")
        self.assertIn("Paciente cadastrado.".encode(), r.data)
        self.assertNotIn("Davi Exemplo".encode(), rec.get("/recepcao/pacientes?q=Elisa").data)
        dia = agora().date() + timedelta(days=1)
        dados = dict(paciente=5, profissional=1, sala=1, inicio=f"{dia}T09:00", modalidade="retorno")
        self.assertIn("Consulta agendada.".encode(), post(rec,"/recepcao","/recepcao",**dados).data)
        self.assertIn("Horário ocupado".encode(), post(rec,"/recepcao","/recepcao",**dados).data)
        with self.app.app_context(), transacao() as cur:
            id_ag = consultar(cur, "SELECT id FROM clin.agendamento WHERE paciente_id=5")[0]["id"]
        self.assertIn("Agendamento cancelado".encode(), post(rec,f"/recepcao/{id_ag}/cancelado","/recepcao").data)
        self.assertIn("Consulta agendada.".encode(), post(rec,"/recepcao","/recepcao",**dados).data)

    def test_04_fila_concorrencia_e_prontuario(self):
        rec = login(self.app, "recepcao")
        publico = self.app.test_client()
        self.assertIn(b"Chegada confirmada", post(rec,"/recepcao/1/chegada","/recepcao",prioridade=0).data)
        self.assertIn(b"Chegada confirmada", post(rec,"/recepcao/2/chegada","/recepcao",prioridade=1).data)
        self.assertIn(b"j\xc3\xa1 recebeu", post(rec,"/recepcao/2/chegada","/recepcao",prioridade=1).data)
        with self.app.app_context(), transacao() as cur:
            chave = consultar(cur, "SELECT senha FROM clin.fila WHERE agendamento_id=2")[0]["senha"]
        medico = login(self.app,"medico")
        self.assertIn("sequência".encode(), post(medico,"/consultorio/2/concluir","/consultorio",resumo="Teste").data)
        def acionar(_):
            client = login(self.app,"medico")
            return post(client,"/consultorio/chamar","/consultorio").data
        with ThreadPoolExecutor(max_workers=2) as pool:
            respostas = list(pool.map(acionar, range(2)))
        self.assertEqual(sum(b"Senha publicada" in r for r in respostas), 1)
        self.assertEqual(sum("Nenhuma senha disponível".encode() in r for r in respostas), 1)
        j = publico.get("/api/fila").get_json()
        self.assertEqual(j["chamadas"], [{"senha":chave, "sala":"Consultório 01"}])
        self.assertEqual(j["aguardando"], 1)
        self.assertEqual(login(self.app,"medico2").get("/consultorio/historico/2").status_code,403)
        self.assertIn(b"Consulta iniciada", post(medico,"/consultorio/2/iniciar","/consultorio").data)
        self.assertEqual(publico.get("/api/fila").get_json()["chamadas"], [])
        self.assertIn("Informe um resumo".encode(), post(medico,"/consultorio/2/concluir","/consultorio").data)
        self.assertIn("Atendimento concluído".encode(), post(medico,"/consultorio/2/concluir","/consultorio",
                                                           resumo="Resumo sintético.", nota="Nota sintética separada.").data)
        self.assertIn("Bruno Exemplo".encode(), medico.get("/consultorio?historico=Bruno").data)
        self.assertIn("Nota sintética separada.".encode(), medico.get("/consultorio/historico/2").data)
        with self.app.app_context():
            notas = documentos("nota",2)
            self.assertEqual(len(notas),1)
            arquivo = Path(self.pasta.name)/"nota"/(notas[0]["id"]+".json")
            arquivo.unlink()
            self.assertEqual(notas, documentos("nota",2))
            self.assertTrue(arquivo.exists())
            eventos = documentos("auditoria", 2)
            self.assertIn("leitura_historico", {e["acao"] for e in eventos})
            self.assertTrue(all("texto" not in e for e in eventos))
        self.assertIn(b"Realizados",rec.get("/indicadores").data)

    def test_05_faltas_e_dml(self):
        rec = login(self.app, "recepcao")
        agora_local = agora()
        ontem = (agora_local - timedelta(days=1)).replace(hour=7,minute=0,second=0)
        futuro = (agora_local + timedelta(days=1)).replace(hour=11,minute=0,second=0)
        with self.app.app_context(), transacao(escrita=True) as cur:
            passado = novo_agendamento(cur, 3, 2, 2, ontem, "retorno")
            futuro_id = novo_agendamento(cur, 3, 2, 2, futuro, "retorno")
        self.assertIn(b"Falta registrada",post(rec,f"/recepcao/{passado}/falta","/recepcao").data)
        self.assertIn(b"15 minutos",post(rec,f"/recepcao/{futuro_id}/falta","/recepcao").data)
        with self.app.app_context():
            conn = conectar(autocommit=True)
            try:
                cur=conn.cursor()
                cur.execute(Path("sql/02_exemplos.sql").read_text())
                while cur.nextset():
                    if cur.description:
                        cur.fetchall()
                self.assertEqual(consultar(cur,"SELECT COUNT(*) AS n FROM clin.paciente WHERE nome=%s", ("Paciente Demonstração SQL",))[0]["n"],0)
            finally:
                conn.close()

    def test_06_latencia_local_e_contrato_publico(self):
        client = self.app.test_client()
        amostras = []
        for _ in range(40):
            inicio = perf_counter()
            resp = client.get("/api/fila")
            amostras.append((perf_counter()-inicio)*1000)
            self.assertEqual(resp.status_code,200)
            dados = resp.get_json()
            self.assertEqual(set(dados), {"chamadas","aguardando","referencia_min"})
            self.assertTrue(all(set(linha) == {"senha","sala"} for linha in dados["chamadas"]))
        self.assertEqual(client.get("/saude").get_json(), {"status":"ok"})
        p95 = sorted(amostras)[37]
        print(f"\nAPI /api/fila: 40 leituras, p95={p95:.1f} ms, ambiente local de demonstração.", flush=True)
        self.assertLess(p95,500)


if __name__ == "__main__":
    unittest.main()
