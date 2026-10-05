"""Fechamento de dezena e pagamento de agregados no SSW (RPA)."""

import logging
import os
import re
import shutil
import time
import calendar
import zipfile
import unicodedata
import ctypes
from decimal import Decimal
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pyautogui
import pygetwindow as gw
from dotenv import load_dotenv

from utils import configurar_log, foto_do_erro, janela_existe, esperar_ate


BASE = Path(__file__).resolve().parent
ABA_PRODUCAO = "BASE_DE_DADO"
PASTA_DOWNLOADS = Path.home() / "Downloads"

load_dotenv(BASE / ".env")
SISTEMA_URL = os.getenv("SISTEMA_URL")
PLANILHA_PRODUCAO = Path(os.getenv("PLANILHA_PRODUCAO", ""))
CPF_USUARIO = os.getenv("CPF_USUARIO_1")
LOGIN_USUARIO = os.getenv("LOGIN_USUARIO_1")
SENHA_USUARIO = os.getenv("SENHA_USUARIO_1")

TELA_LOGIN = "Login Sistema SSW"
TELA_MENU = "Menu Principal"
TELA_076 = "076 - Emissão Demonstrativo Coletas/Entregas"
TELA_156 = "156 - Fila de processamento em lotes"
TELA_413 = "413 - Produção de Veículos"
pyautogui.PAUSE = 0.5
log = configurar_log()


def periodo_fechado(hoje=None):
    """Retorna a última dezena integralmente encerrada (datas inclusivas)."""
    hoje = hoje or date.today()
    ultimo_dia_mes = calendar.monthrange(hoje.year, hoje.month)[1]
    if hoje.day == ultimo_dia_mes and hoje.day >= 21:
        return date(hoje.year, hoje.month, 21), date(hoje.year, hoje.month, ultimo_dia_mes)
    if hoje.day >= 21:
        return date(hoje.year, hoje.month, 11), date(hoje.year, hoje.month, 20)
    if hoje.day >= 11:
        return date(hoje.year, hoje.month, 1), date(hoje.year, hoje.month, 10)
    ultimo_dia = date(hoje.year, hoje.month, 1) - timedelta(days=1)
    return date(ultimo_dia.year, ultimo_dia.month, 21), ultimo_dia


def _normalizar_coluna(nome):
    texto = unicodedata.normalize("NFKD", str(nome).strip().casefold())
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return " ".join(texto.split())


def carregar_pagamentos(inicio, fim):
    """Soma o campo PAGO por placa para agregados na janela da dezena."""
    if not PLANILHA_PRODUCAO.is_file():
        raise FileNotFoundError(
            f"Planilha de produção não encontrada: {PLANILHA_PRODUCAO!s}. "
            "Defina PLANILHA_PRODUCAO no .env com o caminho completo do arquivo."
        )
    dados = pd.read_excel(PLANILHA_PRODUCAO, sheet_name=ABA_PRODUCAO, header=7)
    dados.columns = [_normalizar_coluna(c) for c in dados.columns]
    necessarias = {"data", "placa", "tipo veic.", "agregado", "valor veiculo"}
    faltantes = necessarias - set(dados.columns)
    if faltantes:
        raise ValueError(f"Colunas ausentes na aba {ABA_PRODUCAO}: {sorted(faltantes)}")

    datas = dados["data"]
    if pd.api.types.is_numeric_dtype(datas):
        dados["data"] = pd.to_datetime(
            pd.to_numeric(datas, errors="coerce"), unit="D", origin="1899-12-30", errors="coerce"
        ).dt.date
    else:
        dados["data"] = pd.to_datetime(datas, errors="coerce", dayfirst=True).dt.date
    dados["placa"] = dados["placa"].astype("string").str.strip().str.upper()
    agregado = dados["agregado"].astype("string").str.strip().str.upper()
    dados["valor veiculo"] = pd.to_numeric(dados["valor veiculo"], errors="coerce")
    dentro_periodo = dados["data"].between(inicio, fim)
    filtro = dentro_periodo & agregado.isin({"SIM", "S", "1", "TRUE"})
    selecionados = dados.loc[filtro, ["placa", "tipo veic.", "valor veiculo"]].dropna(
        subset=["placa", "valor veiculo"]
    )
    selecionados = selecionados[selecionados["placa"].ne("")]
    if selecionados.empty:
        raise ValueError(
            f"Não encontrei pagamentos de agregados entre {inicio:%d/%m/%Y} e {fim:%d/%m/%Y}"
        )
    tipos_por_placa = selecionados.groupby("placa")["tipo veic."].agg(
        lambda valores: valores.dropna().astype(str).str.strip().iloc[-1]
        if not valores.dropna().empty else ""
    )
    resultado = selecionados.groupby("placa", as_index=False)["valor veiculo"].sum()
    resultado["Tipo"] = resultado["placa"].map(tipos_por_placa)
    resultado = resultado.rename(columns={"placa": "Placa", "valor veiculo": "Valor"})
    resultado = resultado.sort_values("Placa").reset_index(drop=True)
    log.info("Planilha: %d agregados com pagamento no período", len(resultado))
    return resultado


def _titulo_janela_ativa():
    try:
        janela = gw.getActiveWindow()
        return janela.title if janela else ""
    except Exception:
        return ""


def voltar_ao_menu(tentativas=10):
    for _ in range(tentativas):
        if TELA_MENU in _titulo_janela_ativa():
            return
        pyautogui.press("esc")
        time.sleep(1)
    raise TimeoutError(f"Não voltei ao Menu Principal; janela ativa: {_titulo_janela_ativa()!r}")


def ativar_janela_esperada(trecho_titulo, timeout=10):
    """Traz a tela SSW esperada para frente e falha se ela não ficar ativa."""
    limite = time.time() + timeout
    while time.time() < limite:
        for janela in gw.getAllWindows():
            if trecho_titulo not in janela.title:
                continue
            try:
                if janela.isMinimized:
                    janela.restore()
                janela.activate()
                time.sleep(0.5)
            except Exception as erro:
                log.warning("Não consegui ativar a janela %r: %s", janela.title, erro)
            ativa = _titulo_janela_ativa()
            if trecho_titulo in ativa:
                log.info("Tela esperada ativa: %s", ativa)
                return
        time.sleep(0.25)
    raise TimeoutError(
        f"A janela esperada '{trecho_titulo}' não ficou ativa; "
        f"janela ativa: {_titulo_janela_ativa()!r}"
    )


def abrir_opcao(codigo, titulo_esperado=None, filial="MTZ"):
    time.sleep(1.5)
    pyautogui.hotkey("shift", "tab")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(filial)
    pyautogui.write(str(codigo))
    pyautogui.press("tab")
    if titulo_esperado:
        esperar_ate(titulo_esperado, timeout=60)
    else:
        time.sleep(2)
    log.info("Opção %s aberta; janela ativa: %s", codigo, _titulo_janela_ativa())


def acessar_sistema():
    if not SISTEMA_URL:
        raise RuntimeError("SISTEMA_URL não foi configurada no .env")
    pyautogui.press("win")
    pyautogui.write("chrome")
    pyautogui.press("enter")
    esperar_ate("Google Chrome", timeout=60)
    time.sleep(1)
    pyautogui.hotkey("ctrl", "l")
    pyautogui.write(SISTEMA_URL)
    pyautogui.press("enter")
    esperar_ate(TELA_LOGIN, timeout=60)


def fazer_login():
    if not all((CPF_USUARIO, LOGIN_USUARIO, SENHA_USUARIO)):
        raise RuntimeError("Credenciais CPF_USUARIO_1, LOGIN_USUARIO_1 e SENHA_USUARIO_1 devem estar no .env")
    time.sleep(1.5)
    pyautogui.hotkey("shift", "tab")
    for valor in (CPF_USUARIO, LOGIN_USUARIO, SENHA_USUARIO):
        pyautogui.hotkey("ctrl", "a")
        pyautogui.write(valor)
    pyautogui.press("tab")
    pyautogui.press("enter")
    limite = time.time() + 60
    while time.time() < limite:
        if janela_existe(TELA_MENU):
            return
        time.sleep(0.5)
    raise RuntimeError("Login não avançou; confira as credenciais e o print salvo em logs/")


def _datas_ssw(inicio, fim):
    return inicio.strftime("%d%m%y"), fim.strftime("%d%m%y")


def conferir_producao_por_veiculo(tabela, inicio, fim):
    """Solicita o relatório 076 para cada placa e unidade, reabrindo a tela."""
    di, df = _datas_ssw(inicio, fim)
    for indice, linha in tabela.iterrows():
        placa = str(linha["Placa"])
        for unidade in ("SPO", "SPT", "BHZ"):
            voltar_ao_menu()
            abrir_opcao(76, TELA_076)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.write(unidade)
            # A tela 076 avança sozinha entre Unidade, datas e Veículo.
            # Não enviar Tab nem Enter entre esses campos.
            pyautogui.write(di)
            pyautogui.write(df)
            pyautogui.write(placa)
            pyautogui.press("enter")
            time.sleep(1.5)
            pyautogui.write("E")
            time.sleep(1.5)
            pyautogui.press("esc")
            time.sleep(1)
            log.info(
                "Relatório 076 solicitado: unidade %s, placa %s (%d/%d)",
                unidade, placa, indice + 1, len(tabela),
            )
            voltar_ao_menu()


def extrair_relatorio_producao_veiculos(tabela, inicio, fim):
    di, df = _datas_ssw(inicio, fim)
    veiculos = tabela[~tabela["Tipo"].astype("string").str.strip().str.casefold().eq("cavalo")]
    log.info("Opção 413: %d veículo(s), excluídos %d Cavalo(s)", len(veiculos), len(tabela) - len(veiculos))

    for numero, (_, linha) in enumerate(veiculos.iterrows(), start=1):
        placa = str(linha["Placa"])
        voltar_ao_menu()
        abrir_opcao(413, TELA_413)
        ativar_janela_esperada(TELA_413)

        pyautogui.press("tab", presses=5)  # início do período de emissão
        pyautogui.hotkey("ctrl", "a")
        pyautogui.write(di)
        # O SSW avança sozinho para a data final.
        pyautogui.hotkey("ctrl", "a")
        pyautogui.write(df)
        pyautogui.press("tab", presses=2)  # campos Unidade e Placa
        pyautogui.write(placa)
        pyautogui.press("tab", presses=5)  # ação Produção de veículos

        # Não enviar Enter se o foco tiver saído da 413.
        ativar_janela_esperada(TELA_413)
        log.info("Solicitando 413 para placa %s (%d/%d)", placa, numero, len(veiculos))
        pyautogui.press("enter")
        time.sleep(2)

        # O SSW confirma a fila pelo atalho "7. OK".
        pyautogui.press("7")
        time.sleep(1)
        voltar_ao_menu()
        log.info("Relatório 413 solicitado para %s; retorno ao menu confirmado", placa)


def _pasta_saida_periodo(inicio, fim):
    return BASE / "saida" / "fechamento_dezena" / f"{inicio:%Y-%m-%d}_{fim:%Y-%m-%d}"


def gerar_documento_km(capturas, inicio, fim, destino):
    """Monta um PDF com resumo das somas e uma captura por veículo."""
    if not capturas:
        raise ValueError("Nenhuma captura de KM foi registrada para montar o documento")
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfgen import canvas
    except ImportError as erro:
        raise RuntimeError("Instale reportlab para gerar o documento PDF das capturas de KM") from erro

    destino.mkdir(parents=True, exist_ok=True)
    arquivo_pdf = destino / f"KMs_Agregados_{inicio:%Y%m%d}_{fim:%Y%m%d}.pdf"
    largura_pagina, altura_pagina = landscape(A4)
    margem = 24
    pdf = canvas.Canvas(str(arquivo_pdf), pagesize=(largura_pagina, altura_pagina))

    # Primeira página: tabela simples com o total lido em cada placa.
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(margem, altura_pagina - margem - 16, "Resumo de KMs percorridos por placa")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(margem, altura_pagina - margem - 34,
                   f"Periodo: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}")
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(margem, altura_pagina - margem - 62, "Placa")
    pdf.drawString(margem + 220, altura_pagina - margem - 62, "Leituras")
    pdf.drawString(margem + 330, altura_pagina - margem - 62, "Soma percorrida (km)")
    y_resumo = altura_pagina - margem - 80
    pdf.setFont("Helvetica", 9)
    for numero, (placa, _, distancias) in enumerate(capturas, start=1):
        if y_resumo < margem + 20:
            pdf.showPage()
            y_resumo = altura_pagina - margem - 24
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(margem, y_resumo, "Resumo de KMs percorridos por placa (continuação)")
            y_resumo -= 24
            pdf.setFont("Helvetica", 9)
        soma = sum(distancias, Decimal("0"))
        soma_formatada = format(soma.normalize(), "f").replace(".", ",")
        pdf.drawString(margem, y_resumo, placa)
        pdf.drawString(margem + 220, y_resumo, str(len(distancias)))
        pdf.drawString(margem + 330, y_resumo, f"{soma_formatada} km")
        y_resumo -= 15
    pdf.showPage()

    for numero, (placa, imagem_path, distancias) in enumerate(capturas, start=1):
        soma = sum(distancias, Decimal("0"))
        soma_formatada = format(soma.normalize(), "f").replace(".", ",")
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(margem, altura_pagina - margem - 14, f"KMs do veiculo - placa {placa}")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(
            margem,
            altura_pagina - margem - 29,
            f"Periodo do fechamento: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y}",
        )
        pdf.drawString(margem, altura_pagina - margem - 42,
                       f"Soma dos {len(distancias)} valores em Percorridos: {soma_formatada} km")

        imagem = ImageReader(str(imagem_path))
        largura_imagem, altura_imagem = imagem.getSize()
        max_largura = largura_pagina - 2 * margem
        max_altura = altura_pagina - 2 * margem - 48
        escala = min(max_largura / largura_imagem, max_altura / altura_imagem)
        largura_render = largura_imagem * escala
        altura_render = altura_imagem * escala
        x = (largura_pagina - largura_render) / 2
        y = margem + 16 + (max_altura - altura_render) / 2
        pdf.drawImage(imagem, x, y, width=largura_render, height=altura_render)
        pdf.setFont("Helvetica", 8)
        pdf.drawRightString(largura_pagina - margem, 12, f"Pagina {numero} de {len(capturas)}")
        pdf.showPage()

    pdf.save()
    log.info("Documento de KM criado com resumo e %d captura(s): %s", len(capturas), arquivo_pdf)
    return arquivo_pdf


def copiar_texto_da_pagina():
    """Copia o texto selecionável da página SSW pelo clipboard do Windows."""
    import win32clipboard

    janela = gw.getActiveWindow()
    if janela:
        # Foca uma área vazia da página para Ctrl+A selecionar o documento,
        # em vez de selecionar somente o conteúdo de um campo de formulário.
        x = janela.left + max(20, int(janela.width * 0.88))
        y = janela.top + max(80, int(janela.height * 0.72))
        pyautogui.click(x, y)
        time.sleep(0.2)

    user32 = ctypes.windll.user32
    sequencia_antes = user32.GetClipboardSequenceNumber()
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "c")
    limite = time.time() + 5
    while time.time() < limite:
        if user32.GetClipboardSequenceNumber() != sequencia_antes:
            break
        time.sleep(0.1)
    else:
        raise TimeoutError("A página da opção 93 não copiou texto para o clipboard")

    win32clipboard.OpenClipboard()
    try:
        texto = win32clipboard.GetClipboardData(13)  # CF_UNICODETEXT
    finally:
        win32clipboard.CloseClipboard()
    return texto if isinstance(texto, str) else str(texto)


def ler_percorridos(texto):
    """Extrai valores escritos como 'NNN Km' e devolve os números em km."""
    valores = re.findall(r"\b(\d+(?:[.,]\d+)?)\s*km\b", texto, flags=re.IGNORECASE)
    distancias = [Decimal(valor.replace(",", ".")) for valor in valores]
    if not distancias:
        amostra = " ".join(texto.split())[:500]
        raise ValueError(
            "Não encontrei valores no campo 'Percorridos' da opção 93. "
            f"Texto copiado para diagnóstico: {amostra!r}"
        )
    return distancias


def extrair_km_opcao_93(tabela, inicio, fim):
    """Consulta opção 93, captura cada placa não Cavalo e cria um PDF consolidado."""
    di, _ = _datas_ssw(inicio, fim)
    veiculos = tabela[~tabela["Tipo"].astype("string").str.strip().str.casefold().eq("cavalo")]
    pasta_saida = _pasta_saida_periodo(inicio, fim)
    pasta_imagens = pasta_saida / "capturas_km"
    pasta_imagens.mkdir(parents=True, exist_ok=True)
    capturas = []
    log.info("Opção 93: %d veículo(s), excluídos %d Cavalo(s)", len(veiculos), len(tabela) - len(veiculos))

    for numero, (_, linha) in enumerate(veiculos.iterrows(), start=1):
        placa = str(linha["Placa"])
        voltar_ao_menu()
        abrir_opcao(93, filial="SPO")
        time.sleep(1)
        # O formulário avança automaticamente: após a placa e a data, a tela de KMs abre sozinha.
        pyautogui.write(placa)
        pyautogui.write(di)
        time.sleep(3)

        nome_seguro = "".join(c for c in placa if c.isalnum())
        caminho_imagem = pasta_imagens / f"{numero:03d}_{nome_seguro}_KM.png"
        pyautogui.screenshot().save(str(caminho_imagem))
        distancias = ler_percorridos(copiar_texto_da_pagina())
        soma = sum(distancias, Decimal("0"))
        capturas.append((placa, caminho_imagem, distancias))
        log.info(
            "Opção 93: placa %s, valores Percorridos=%s km, soma=%s km (%d/%d)",
            placa,
            "+".join(format(valor.normalize(), "f") for valor in distancias),
            format(soma.normalize(), "f"),
            numero,
            len(veiculos),
        )
        voltar_ao_menu()

    return gerar_documento_km(capturas, inicio, fim, pasta_saida)


def extrair_relatorio_manifestos(tabela, inicio, fim):
    di, df = _datas_ssw(inicio, fim)
    voltar_ao_menu()
    abrir_opcao(200)
    pyautogui.write(di)
    pyautogui.press("tab")
    pyautogui.write(df)
    pyautogui.press("enter")
    pyautogui.write("SPO")
    pyautogui.press("enter")
    for indice, linha in tabela.iterrows():
        placa = str(linha["Placa"])
        pyautogui.write(placa)
        time.sleep(1.75)
        pyautogui.press("enter")
        pyautogui.press("tab")
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("esc")
        time.sleep(2.5)
        pyautogui.press("up", presses=4)
        log.info("Opção 200 enviada para %s (%d/%d)", placa, indice + 1, len(tabela))
    pyautogui.press("esc")


def gerar_os_pagamento(tabela, inicio, fim):
    voltar_ao_menu()
    abrir_opcao(118, filial="SPO")
    legenda1 = (
        "Pagamento por prestacao de servico referente a dezena "
    )
    legenda2 = (    
        f"{inicio:%d/%m/%Y} A {fim:%d/%m/%Y}"
    )
    veiculos = tabela[~tabela["Tipo"].astype("string").str.strip().str.casefold().eq("cavalo")]
    log.info("Opção 118: %d veículo(s), excluídos %d Cavalo(s)", len(veiculos), len(tabela) - len(veiculos))
    for indice, linha in veiculos.iterrows():
        placa = str(linha["Placa"])
        valor = f"{float(linha['Valor']):.2f}".replace(".", ",")
        pyautogui.write(placa)
        time.sleep(1.5)
        pyautogui.write(valor)
        time.sleep(1.5)
        pyautogui.press("enter", presses=2)
        time.sleep(2)
        pyautogui.write(legenda1)
        pyautogui.press("tab")
        pyautogui.write(legenda2)
        pyautogui.press("tab", presses=3)
        pyautogui.press("enter")
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(10)
        log.info("O.S. submetida para placa %s, valor %s (%d/%d)", placa, valor, indice + 1, len(veiculos))
    pyautogui.press("esc")


def _snapshot_downloads():
    PASTA_DOWNLOADS.mkdir(parents=True, exist_ok=True)
    return {p.name: p.stat().st_mtime_ns for p in PASTA_DOWNLOADS.iterdir() if p.is_file()}


def coletar_arquivos_novos(snapshot, inicio_execucao, inicio, fim, timeout=180):
    destino = _pasta_saida_periodo(inicio, fim)
    destino.mkdir(parents=True, exist_ok=True)
    limite = time.time() + timeout
    ultima_mudanca = time.time()
    assinatura_anterior = None
    while time.time() < limite:
        temporarios = list(PASTA_DOWNLOADS.glob("*.crdownload"))
        novos = [p for p in PASTA_DOWNLOADS.iterdir() if p.is_file() and
                 (p.name not in snapshot or p.stat().st_mtime_ns != snapshot[p.name]) and
                 p.suffix.lower() != ".crdownload" and p.stat().st_mtime >= inicio_execucao - 2]
        assinatura = tuple(sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in novos))
        if assinatura != assinatura_anterior:
            assinatura_anterior = assinatura
            ultima_mudanca = time.time()
        if novos and not temporarios and time.time() - ultima_mudanca >= 15:
            break
        time.sleep(2)
    if list(PASTA_DOWNLOADS.glob("*.crdownload")):
        raise TimeoutError("Há downloads ainda em andamento na pasta Downloads")
    arquivos = [p for p in PASTA_DOWNLOADS.iterdir() if p.is_file() and
                (p.name not in snapshot or p.stat().st_mtime_ns != snapshot[p.name]) and
                p.suffix.lower() != ".crdownload" and p.stat().st_mtime >= inicio_execucao - 2]
    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo novo foi baixado durante o fechamento")
    arquivos_coletados = []
    for arquivo in sorted(arquivos, key=lambda p: p.stat().st_mtime):
        alvo = destino / arquivo.name
        if alvo.exists():
            alvo = destino / f"{arquivo.stem}_{datetime.now():%H%M%S}{arquivo.suffix}"
        shutil.move(str(arquivo), str(alvo))
        arquivos_coletados.append(alvo)
        log.info("Download coletado: %s", alvo)
    return destino, arquivos_coletados


def compactar_fechamento(arquivos_200, arquivo_km, pasta_saida, inicio, fim):
    """Cria ZIP com os relatórios da opção 200 e o PDF consolidado da opção 93."""
    arquivos = list(arquivos_200)
    if arquivo_km is not None:
        arquivos.append(arquivo_km)
    arquivos = [Path(arquivo) for arquivo in arquivos if Path(arquivo).is_file()]
    if not arquivos:
        raise FileNotFoundError("Não encontrei relatórios da opção 200 nem o PDF da opção 93 para compactar")

    arquivo_zip = pasta_saida / f"Fechamento_Agregados_{inicio:%Y%m%d}_{fim:%Y%m%d}.zip"
    with zipfile.ZipFile(arquivo_zip, "w", compression=zipfile.ZIP_DEFLATED) as pacote:
        for arquivo in arquivos:
            pacote.write(arquivo, arcname=arquivo.name)
    log.info("ZIP do fechamento criado com %d arquivo(s): %s", len(arquivos), arquivo_zip)
    return arquivo_zip


def main():
    etapa_atual = "inicializacao"
    try:
        inicio, fim = periodo_fechado()
        log.info("Fechamento da dezena %s a %s", inicio.strftime("%d/%m/%Y"), fim.strftime("%d/%m/%Y"))
        etapa_atual = "carregar_pagamentos"
        tabela = carregar_pagamentos(inicio, fim)
        inicio_execucao = time.time()
        snapshot = _snapshot_downloads()
        etapas = [
            ("acessar_sistema", acessar_sistema),
            ("fazer_login", fazer_login),
            ("conferir_producao_por_veiculo", lambda: conferir_producao_por_veiculo(tabela, inicio, fim)),
            ("extrair_relatorio_producao_veiculos", lambda: extrair_relatorio_producao_veiculos(tabela, inicio, fim)),
            ("extrair_km_opcao_93", lambda: extrair_km_opcao_93(tabela, inicio, fim)),
            ("extrair_relatorio_manifestos", lambda: extrair_relatorio_manifestos(tabela, inicio, fim)),
            ("gerar_os_pagamento", lambda: gerar_os_pagamento(tabela, inicio, fim)),
        ]
        arquivo_km = None
        for nome, funcao in etapas:
            etapa_atual = nome
            log.info("INÍCIO %s", nome)
            resultado = funcao()
            if nome == "extrair_km_opcao_93":
                arquivo_km = resultado
            log.info("FIM %s", nome)
        etapa_atual = "fechar_sistema"
        voltar_ao_menu()
        pyautogui.hotkey("alt", "f4")
        etapa_atual = "coletar_arquivos"
        pasta_saida, arquivos_200 = coletar_arquivos_novos(snapshot, inicio_execucao, inicio, fim)
        etapa_atual = "compactar_fechamento"
        compactar_fechamento(arquivos_200, arquivo_km, pasta_saida, inicio, fim)
    except BaseException:
        log.exception("FALHA/INTERRUPÇÃO em %s", etapa_atual)
        foto_do_erro(etapa_atual)
        raise


if __name__ == "__main__":
    main()
