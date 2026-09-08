"""
Automação de preenchimento diário — TMS (RPA)

Extrai os relatórios diários de três unidades operacionais do sistema TMS
e consolida os dados na planilha de controle entregue aos gestores.

Reduz o tempo da tarefa de 6-7 horas para ~2 horas.
"""

import os
import time
from datetime import datetime, timedelta

import pyautogui
from dotenv import load_dotenv

load_dotenv()

# --- Configuração (via variáveis de ambiente, nunca hardcoded) ---
SISTEMA_URL = os.getenv("SISTEMA_URL")

CPF_USUARIO = os.getenv("CPF_USUARIO_1")
LOGIN_USUARIO = os.getenv("LOGIN_USUARIO_1")
SENHA_USUARIO = os.getenv("SENHA_USUARIO_1")

ontem = datetime.now() - timedelta(days=4)

pyautogui.PAUSE = 0.5


def acessar_sistema():
    """Abre o navegador e acessa o sistema TMS."""
    pyautogui.press("win")
    pyautogui.write("chrome")
    pyautogui.press("enter")
    time.sleep(2)
    pyautogui.write(SISTEMA_URL)
    pyautogui.press("enter")
    time.sleep(5)


def fazer_login():
    """Realiza o login no sistema com as credenciais do usuário."""
    pyautogui.hotkey("shift", "tab")
    pyautogui.write(CPF_USUARIO)
    pyautogui.write(LOGIN_USUARIO)
    pyautogui.write(SENHA_USUARIO)
    pyautogui.press("tab")
    pyautogui.press("enter")
    time.sleep(3)


def acessar_opcao_relatorio():
    """Preenche o campo 'Unidade' e a opção do relatório de extração."""
    pyautogui.hotkey("shift", "tab")
    time.sleep(1)
    pyautogui.write("MTZ")
    pyautogui.write("76")
    pyautogui.press("tab")
    time.sleep(5)


def extrair_unidade_bhz():
    """Extrai o relatório da unidade BHZ para o período informado."""
    pyautogui.write("BHZ")
    pyautogui.write(ontem.strftime("%d/%m"))
    pyautogui.press("tab")
    pyautogui.write(ontem.strftime("%d/%m"))
    pyautogui.press("enter")
    pyautogui.press("enter")
    pyautogui.write("E")
    time.sleep(1.5)
    pyautogui.press("esc")
    time.sleep(1.5)


def extrair_unidade_spt():
    """Extrai o relatório da unidade SPT."""
    pyautogui.press("up", presses=6)
    time.sleep(0.5)
    pyautogui.write("SPT")
    pyautogui.press("enter")
    pyautogui.press("enter")
    pyautogui.press("enter")
    pyautogui.press("enter")
    time.sleep(1.5)
    pyautogui.press("esc")
    time.sleep(1.75)


def extrair_unidade_spo_e_baixar():
    """Extrai o relatório da unidade SPO e baixa os arquivos gerados."""
    pyautogui.press("up", presses=5)
    time.sleep(0.5)
    pyautogui.write("SPO")
    pyautogui.press("enter")
    pyautogui.press("enter")
    pyautogui.press("enter")
    pyautogui.press("enter")
    time.sleep(1.5)
    pyautogui.press("1")
    time.sleep(15)
    pyautogui.press("tab")  # Clicar no botão "atualizar" para baixar
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.press("tab")
    pyautogui.press("tab", presses=10)
    time.sleep(0.5)
    pyautogui.press("enter")
    pyautogui.press("tab")
    pyautogui.press("enter")
    pyautogui.press("tab")
    pyautogui.press("enter")
    time.sleep(0.75)
    pyautogui.press("esc")
    pyautogui.press("esc")
    pyautogui.hotkey("alt", "f4")  # Fecha o navegador


def renomear_arquivos_baixados():
    """Renomeia os três arquivos baixados na pasta Downloads."""
    pyautogui.hotkey("win", "e")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(3)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(1)
    pyautogui.write("Downloads")
    pyautogui.press("enter")
    time.sleep(3)

    pyautogui.press("up", presses=5)
    pyautogui.press("down")
    time.sleep(0.5)
    pyautogui.press("F2")
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("delete")
    pyautogui.write("BHZ.csv")
    pyautogui.press("tab")
    pyautogui.press("enter")
    pyautogui.write("SPT.csv")
    pyautogui.press("delete", presses=15)
    pyautogui.press("tab")
    pyautogui.press("enter")
    pyautogui.write("SPO.csv")
    pyautogui.press("delete", presses=15)
    pyautogui.press("enter")
    pyautogui.press("enter")
    time.sleep(1)
    pyautogui.hotkey("alt", "f4")
    time.sleep(1)


def limpar_colunas_arquivo(nome_arquivo):
    """
    Abre um arquivo CSV extraído e remove as colunas que não interessam
    para a planilha de controle final.
    """
    pyautogui.hotkey("win", "e")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(3)
    pyautogui.hotkey("ctrl", "f")
    time.sleep(1)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.5)
    pyautogui.write(nome_arquivo)
    time.sleep(0.5)
    for _ in range(4):
        pyautogui.press("tab")
        time.sleep(0.5)
    pyautogui.press("down")
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(5)

    pyautogui.press("right", presses=2)
    time.sleep(0.75)
    pyautogui.hotkey("ctrl", "space")
    for _ in range(18):
        pyautogui.hotkey("ctrl", "-")
    time.sleep(0.5)
    pyautogui.press("right", presses=2)
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "space")
    for _ in range(3):
        pyautogui.hotkey("ctrl", "-")
    pyautogui.press("right")
    pyautogui.hotkey("ctrl", "space")
    for _ in range(3):
        pyautogui.hotkey("ctrl", "-")
    time.sleep(1.5)

    pyautogui.hotkey("ctrl", "b")
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.hotkey("alt", "f4")
    time.sleep(0.5)


def consolidar_na_planilha_controle():
    """
    Abre a planilha de controle (Produção de Agregados) e consolida os
    dados extraídos das unidades SPO e SPT.
    """
    pyautogui.hotkey("ctrl", "f")
    time.sleep(1)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.5)
    pyautogui.write("Producao_de_Agregados_SPO.xlsx")
    time.sleep(0.5)
    pyautogui.press("tab", presses=4)
    time.sleep(0.5)
    pyautogui.press("down")
    pyautogui.press("up")
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(5)
    pyautogui.press("F5")
    time.sleep(0.75)
    pyautogui.write("PREENCHIMENTO!$A$3")
    pyautogui.press("enter")
    pyautogui.hotkey("ctrl", "t")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "-")
    time.sleep(0.5)
    pyautogui.press("down")
    pyautogui.press("enter")
    pyautogui.press("F5")
    time.sleep(0.75)
    pyautogui.write("PREENCHIMENTO!$A$3")
    pyautogui.press("enter")

    for origem, destino_f5 in (("SPO.csv", "A3"), ("SPT.csv", None)):
        pyautogui.hotkey("alt", "tab")
        time.sleep(1)
        pyautogui.hotkey("ctrl", "f")
        time.sleep(1)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.5)
        pyautogui.write(origem)
        time.sleep(0.5)
        pyautogui.press("tab", presses=4)
        time.sleep(0.5)
        pyautogui.press("down")
        time.sleep(0.5)
        pyautogui.press("enter")
        time.sleep(5)
        pyautogui.press("F5")
        time.sleep(0.75)
        pyautogui.write("A1")
        pyautogui.press("enter")
        time.sleep(0.75)
        pyautogui.hotkey("shift", "space")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "-")
        time.sleep(0.5)

        pyautogui.press("F5")
        pyautogui.write("A1")
        pyautogui.press("enter")
        pyautogui.hotkey("ctrl", "t")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "x")
        time.sleep(1)

        pyautogui.hotkey("alt", "tab")
        time.sleep(1)

        if destino_f5:
            pyautogui.press("F5")
            pyautogui.write(destino_f5)
            pyautogui.press("enter")
        else:
            pyautogui.keyDown("ctrl")
            time.sleep(0.5)
            pyautogui.press("down")
            time.sleep(0.5)
            pyautogui.keyUp("ctrl")
            time.sleep(0.5)
            pyautogui.press("down")
            time.sleep(0.5)

        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "b")
        pyautogui.hotkey("alt", "tab")
        time.sleep(1)
        pyautogui.hotkey("alt", "f4")
        time.sleep(0.5)
        pyautogui.press("n")
        time.sleep(1)
        pyautogui.hotkey("alt", "tab")
        time.sleep(1)

    pyautogui.hotkey("alt", "f4")
    time.sleep(1)


def baixar_relatorio_manifesto():
    """
    Reabre o sistema e baixa o relatório de manifesto (código 200)
    para a unidade SPO, aplicando a limpeza de colunas final.
    """
    acessar_sistema()
    fazer_login()

    pyautogui.hotkey("shift", "tab")
    time.sleep(1)
    pyautogui.write("SPO")
    pyautogui.write("200")
    time.sleep(1.5)
    pyautogui.write(ontem.strftime("%d/%m"))
    pyautogui.press("tab")
    pyautogui.write(ontem.strftime("%d/%m"))
    pyautogui.press("enter")
    pyautogui.write("SPO")
    pyautogui.press("enter", presses=3)
    pyautogui.write("E")
    time.sleep(1)
    pyautogui.press("esc")
    time.sleep(2.5)
    pyautogui.press("esc")

    pyautogui.hotkey("win", "e")
    time.sleep(1)
    pyautogui.press("enter")
    time.sleep(3)
    pyautogui.hotkey("ctrl", "l")
    time.sleep(1)
    pyautogui.write("Downloads")
    pyautogui.press("enter")
    time.sleep(3)

    pyautogui.press("down")
    time.sleep(0.5)
    pyautogui.press("up")
    time.sleep(0.5)
    pyautogui.press("F2")
    time.sleep(1)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("delete")
    pyautogui.write("Manifesto.csv")
    pyautogui.press("enter", presses=2)
    time.sleep(1)

    time.sleep(2)
    pyautogui.hotkey("ctrl", "space")
    pyautogui.hotkey("ctrl", "-")
    pyautogui.press("right", presses=2)
    pyautogui.hotkey("ctrl", "space")
    for _ in range(6):
        pyautogui.hotkey("ctrl", "-")
    pyautogui.press("right")
    pyautogui.hotkey("ctrl", "space")
    for _ in range(4):
        pyautogui.hotkey("ctrl", "-")
    pyautogui.press("right")
    pyautogui.hotkey("ctrl", "space")
    for _ in range(15):
        pyautogui.hotkey("ctrl", "-")
    pyautogui.press("right")
    pyautogui.hotkey("ctrl", "space")
    for _ in range(21):
        pyautogui.hotkey("ctrl", "-")
    pyautogui.press("right")
    pyautogui.hotkey("ctrl", "space")
    for _ in range(15):
        pyautogui.hotkey("ctrl", "-")
    pyautogui.press("F5")
    time.sleep(0.75)
    pyautogui.write("A1")
    pyautogui.press("enter")
    pyautogui.hotkey("shift", "space")
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "-")
    time.sleep(0.5)


def main():
    acessar_sistema()
    fazer_login()
    acessar_opcao_relatorio()
    extrair_unidade_bhz()
    extrair_unidade_spt()
    extrair_unidade_spo_e_baixar()
    renomear_arquivos_baixados()

    for arquivo in ("SPO.csv", "SPT.csv", "BHZ.csv"):
        limpar_colunas_arquivo(arquivo)

    consolidar_na_planilha_controle()
    baixar_relatorio_manifesto()


if __name__ == "__main__":
    main()
