"""Roteiro de aceitação em Chromium via HTTP. Execute sobre uma base demo recém-criada."""
import os
from pathlib import Path
from time import perf_counter

from playwright.sync_api import expect, sync_playwright

BASE = os.getenv("APP_URL", "http://127.0.0.1:5000")
SAIDA = Path(os.getenv("EVIDENCIAS", "docs/evidencias"))
SAIDA.mkdir(parents=True, exist_ok=True)


def entrar(pagina, usuario):
    pagina.goto(BASE + "/entrar")
    pagina.get_by_label("Usuário", exact=True).fill(usuario)
    pagina.get_by_label("Senha", exact=True).fill(os.environ["DEMO_PASSWORD"])
    pagina.get_by_role("button", name="Entrar", exact=True).click()


def capturar(pagina, nome):
    pagina.screenshot(path=SAIDA / f"{nome}.jpg", quality=86)


with sync_playwright() as playwright:
    navegador = playwright.chromium.launch(executable_path=os.getenv("CHROMIUM_PATH"))
    print("Chromium:", navegador.version)
    recepcao = navegador.new_page(viewport={"width": 1280, "height": 900})
    erros_js = []
    recepcao.on("pageerror", lambda erro: erros_js.append(str(erro)))
    recepcao.goto(BASE + "/entrar")
    recepcao.keyboard.press("Tab")
    expect(recepcao.get_by_role("link", name="Ir ao conteúdo")).to_be_focused()
    recepcao.keyboard.press("Enter")
    expect(recepcao.locator("#principal")).to_be_focused()
    capturar(recepcao, "01-login")
    entrar(recepcao, "recepcao")
    expect(recepcao.get_by_role("heading", name="Recepção")).to_be_visible()
    recepcao.get_by_role("link", name="Pacientes", exact=True).click()
    recepcao.get_by_label("Nome completo").fill("Elisa Exemplo")
    recepcao.get_by_label("Data de nascimento").fill("1992-06-15")
    recepcao.get_by_label("Telefone com DDD").fill("16900000088")
    recepcao.get_by_role("button", name="Cadastrar paciente").click()
    expect(recepcao.get_by_role("status")).to_have_text("Paciente cadastrado.")
    capturar(recepcao, "02-cadastro")
    recepcao.get_by_role("link", name="Recepção", exact=True).click()
    paciente = recepcao.locator('select[name="paciente"]')
    paciente.select_option(label="Elisa Exemplo · 15/06/1992 · #5")
    recepcao.get_by_role("button", name="Agendar consulta").click()
    expect(recepcao.get_by_role("status")).to_have_text("Consulta agendada.")
    for nome, prioridade in (("Aline Exemplo", "0"), ("Bruno Exemplo", "1")):
        linha = recepcao.get_by_role("article", name=nome)
        linha.get_by_label("Triagem administrativa").select_option(prioridade)
        linha.get_by_role("button", name="Confirmar chegada").click()
        expect(linha.get_by_text("Aguardando", exact=True)).to_be_visible()
    senha = recepcao.get_by_role("article", name="Bruno Exemplo").locator(".token").inner_text()
    capturar(recepcao, "03-recepcao")

    monitor = navegador.new_page(viewport={"width": 390, "height": 830}, is_mobile=True, has_touch=True)
    monitor.on("pageerror", lambda erro: erros_js.append(str(erro)))
    monitor.goto(BASE + "/sala-de-espera")
    expect(monitor.locator("#total")).to_have_text("2")
    medico = navegador.new_page(viewport={"width": 1280, "height": 900})
    entrar(medico, "medico")
    inicio = perf_counter()
    medico.get_by_role("button", name="Chamar próxima senha").click()
    linha = medico.get_by_role("article", name="Bruno Exemplo")
    expect(linha.get_by_text("Chamado", exact=True)).to_be_visible()
    expect(monitor.get_by_text(senha, exact=True)).to_be_visible(timeout=7200)
    print(f"Propagação da chamada até o DOM do monitor: {perf_counter()-inicio:.2f} s.")
    expect(monitor.get_by_text("Consultório 01")).to_be_visible()
    assert "Bruno Exemplo" not in monitor.locator("body").inner_text()
    assert monitor.evaluate("document.documentElement.scrollWidth === innerWidth")
    capturar(monitor, "04-monitor-mobile")
    capturar(medico, "05-consultorio")
    linha.get_by_role("button", name="Iniciar atendimento").click()
    linha.get_by_label("Resumo do atendimento").fill("Retorno de demonstração registrado com dados sintéticos.")
    linha.get_by_label("Nota clínica opcional").fill("Observação de teste do módulo documental.")
    linha.get_by_role("button", name="Concluir atendimento").click()
    expect(medico.get_by_role("status")).to_have_text("Atendimento concluído e registrado.")
    medico.get_by_label("Nome do paciente").fill("Bruno")
    medico.get_by_role("button", name="Consultar histórico").click()
    medico.get_by_role("link", name="Bruno Exemplo", exact=False).click()
    expect(medico.get_by_text("Observação de teste do módulo documental.")).to_be_visible()
    capturar(medico, "06-historico")
    recepcao.get_by_role("link", name="Indicadores").click()
    expect(recepcao.get_by_role("heading", name="Indicadores da clínica")).to_be_visible()
    capturar(recepcao, "07-indicadores")

    # Percorre as telas fundamentais em larguras distintas, com autenticação real.
    for largura in (360, 768, 1280):
        for pagina, rotas in ((recepcao, ("/recepcao", "/recepcao/pacientes", "/indicadores")),
                             (medico, ("/consultorio", "/consultorio/historico/2")),
                             (monitor, ("/sala-de-espera", "/entrar"))):
            pagina.set_viewport_size({"width": largura, "height": 850})
            for rota in rotas:
                assert pagina.goto(BASE + rota).status == 200
                assert pagina.evaluate("document.documentElement.scrollWidth <= innerWidth"), (largura, rota)
    assert not erros_js, erros_js
    print("Aprovado: teclado, cadastro, agenda, prioridade, monitor, consulta, nota, histórico e indicadores.")
    print("Aprovado: 7 rotas em 360, 768 e 1280 px sem transbordamento horizontal.")
    navegador.close()
