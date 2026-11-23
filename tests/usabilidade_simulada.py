"""Percursos de usabilidade por papéis simulados com SQL Server e navegador reais."""
import os
from pathlib import Path
from time import perf_counter

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("APP_URL", "http://127.0.0.1:5000")
SAIDA = Path(os.getenv("EVIDENCIAS", "docs/evidencias/usabilidade"))
PACIENTE = "Marina Nogueira Demo"
NOTA = "Nota de demonstração para localizar o registro na busca."
SAIDA.mkdir(parents=True, exist_ok=True)


def entrar(pagina, papel):
    pagina.goto(BASE + "/entrar")
    pagina.get_by_label("Usuário", exact=True).fill(papel)
    pagina.get_by_label("Senha", exact=True).fill(os.environ["DEMO_PASSWORD"])
    pagina.get_by_role("button", name="Entrar", exact=True).click()


def capturar(pagina, nome):
    pagina.screenshot(path=SAIDA / f"{nome}.jpg", quality=84)


with sync_playwright() as pw:
    navegador = pw.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
    print(f"Chromium {navegador.version} | Dados sintéticos e três papéis automatizados.", flush=True)

    # Usuário 1 inicia a sessão pública antes da chegada e aguarda a chamada.
    paciente = navegador.new_page(viewport={"width":390,"height":844}, is_mobile=True, has_touch=True)
    paciente.goto(BASE + "/entrar")
    paciente.get_by_role("link", name="Sala de espera", exact=True).click()
    expect(paciente.get_by_role("heading", name="Sala de espera")).to_be_visible()
    expect(paciente.get_by_text("Nenhuma senha chamada no momento.")).to_be_visible()

    # Usuário 2 cadastra, tenta um horário ocupado e conclui em um horário livre.
    recepcao = navegador.new_page(viewport={"width":1280,"height":900})
    entrar(recepcao, "recepcao")
    recepcao.get_by_role("link", name="Pacientes", exact=True).click()
    recepcao.get_by_label("Nome completo").fill(PACIENTE)
    recepcao.get_by_label("Data de nascimento").fill("1991-05-14")
    recepcao.get_by_label("Telefone com DDD").fill("16900009992")
    recepcao.get_by_role("button", name="Cadastrar paciente").click()
    expect(recepcao.get_by_role("status")).to_have_text("Paciente cadastrado.")
    recepcao.get_by_role("link", name="Recepção", exact=True).click()
    campo_paciente = recepcao.locator('select[name="paciente"]')
    opcao = campo_paciente.locator("option").filter(has_text=PACIENTE)
    identificador = opcao.get_attribute("value")
    horario = recepcao.get_by_label("Data e horário", exact=False)
    dia = horario.input_value().split("T")[0]
    campo_paciente.select_option(identificador)
    recepcao.locator('select[name="profissional"]').select_option(label="Dra. Luna Exemplo")
    recepcao.locator('select[name="sala"]').select_option(label="Consultório 01")
    horario.fill(f"{dia}T08:00")
    recepcao.get_by_role("button", name="Agendar consulta").click()
    expect(recepcao.get_by_role("alert")).to_contain_text("Horário ocupado")
    expect(campo_paciente).to_have_value("")
    expect(horario).to_have_value(f"{dia}T09:00")
    campo_paciente.select_option(identificador)
    recepcao.locator('select[name="profissional"]').select_option(label="Dra. Luna Exemplo")
    recepcao.locator('select[name="sala"]').select_option(label="Consultório 01")
    horario.fill(f"{dia}T09:15")
    recepcao.get_by_role("button", name="Agendar consulta").click()
    expect(recepcao.get_by_role("status")).to_have_text("Consulta agendada.")
    linha = recepcao.get_by_role("article", name=PACIENTE)
    linha.get_by_role("button", name="Confirmar chegada").click()
    expect(linha.get_by_text("Aguardando", exact=True)).to_be_visible()
    senha = linha.locator(".token").inner_text()
    linha.scroll_into_view_if_needed()
    capturar(recepcao, "usuario-2-recepcao")
    print("Usuário 2 | Recepção | CONCLUÍDO | Cadastro, agendamento às 09:15 e check-in confirmados.", flush=True)
    print("Observação U2: às 08:00 o conflito foi informado. O formulário voltou a 09:00 e perdeu a seleção do paciente.", flush=True)

    # Usuário 3 chama; Usuário 1 verifica a atualização sem recarregar.
    expect(paciente.locator("#total")).to_have_text("1", timeout=7200)
    expect(paciente.get_by_text(senha, exact=True)).to_have_count(0)
    medico = navegador.new_page(viewport={"width":1280,"height":900})
    entrar(medico, "medico")
    inicio = perf_counter()
    medico.get_by_role("button", name="Chamar próxima senha").click()
    chamada = paciente.locator(".call").filter(has_text=senha)
    expect(chamada.get_by_text("Consultório 01", exact=True)).to_be_visible(timeout=7200)
    segundos = perf_counter() - inicio
    expect(paciente.get_by_text(PACIENTE, exact=True)).to_have_count(0)
    assert paciente.evaluate("document.documentElement.scrollWidth <= innerWidth")
    capturar(paciente, "usuario-1-paciente")
    print("Usuário 1 | Paciente | CONCLUÍDO | Senha localizada no celular e vinculada ao Consultório 01.", flush=True)
    print(f"Observação U1: antes da chamada havia apenas contagem agregada. Chamada exibida em {segundos:.2f} s após o clique no consultório.", flush=True)

    # Usuário 3 termina e recupera o registro com a busca pelo início do nome.
    registro = medico.get_by_role("article", name=PACIENTE)
    registro.get_by_role("button", name="Iniciar atendimento").click()
    registro.get_by_label("Resumo do atendimento").fill("Atendimento de demonstração concluído.")
    registro.get_by_label("Nota clínica opcional").fill(NOTA)
    registro.get_by_role("button", name="Concluir atendimento").click()
    expect(medico.get_by_role("status")).to_have_text("Atendimento concluído e registrado.")
    busca = medico.get_by_label("Nome do paciente", exact=True)
    acao = medico.get_by_role("button", name="Consultar histórico", exact=True)
    busca.fill("Nogueira")
    acao.click()
    expect(medico.get_by_text("Nenhum paciente encontrado no seu histórico.")).to_be_visible()
    busca.fill("Marina")
    acao.click()
    medico.get_by_role("link", name=PACIENTE, exact=False).click()
    expect(medico.get_by_role("heading", name="Histórico clínico")).to_be_visible()
    expect(medico.get_by_text(NOTA, exact=True)).to_be_visible()
    capturar(medico, "usuario-3-medico")
    print("Usuário 3 | Médico | CONCLUÍDO | Chamada, registro e recuperação da nota no histórico.", flush=True)
    print("Observação U3: sobrenome isolado não trouxe resultado; a busca “Marina” encontrou o registro.", flush=True)
    navegador.close()
