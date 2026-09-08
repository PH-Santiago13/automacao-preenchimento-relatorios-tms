"""
Automação de fechamento de dezena — TMS (RPA)

Para cada veículo cadastrado em `Placas.csv`, extrai os relatórios de
produção, manifestos e pagamento por prestação de serviço do período,
conferindo os valores e gerando as Ordens de Serviço (O.S.) de pagamento
aos agregados.
"""

import os
import time
from datetime import datetime, timedelta

import pandas
import pyautogui
from dotenv import load_dotenv

load_dotenv()

# --- Configuração (via variáveis de ambiente, nunca hardcoded) ---
SISTEMA_URL = os.getenv("SISTEMA_URL")

CPF_USUARIO = os.getenv("CPF_USUARIO_1")
LOGIN_USUARIO = os.getenv("LOGIN_USUARIO_1")
SENHA_USUARIO = os.getenv("SENHA_USUARIO_1")

# Período da dezena a ser fechada (formato DDMM)
PERIODO_INICIO = "2108"
PERIODO_FIM = "3108"

ARQUIVO_PLACAS = "Placas.csv"

pyautogui.PAUSE = 0.5


def carregar_placas():
    """Carrega a lista de veículos (placas) e valores a processar."""
    return pandas.read_csv(ARQUIVO_PLACAS, sep=";")


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
    time.sleep(2)


def acessar_opcao_relatorio():
    """Preenche o campo 'Unidade' e a opção do relatório de extração."""
    pyautogui.hotkey("shift", "tab")
    time.sleep(1)
    pyautogui.write("MTZ")
    pyautogui.write("76")
    pyautogui.press("tab")
    time.sleep(3)


def conferir_producao_por_veiculo(tabela):
    """
    Para cada veículo, confere a produção nas três unidades operacionais
    (SPO, SPT, BHZ) no período informado.
    """
    for linha in tabela.index:
        placa = tabela.loc[linha, "Placa"]

        # Unidade SPO
        pyautogui.write("SPO")
        pyautogui.write(str(PERIODO_INICIO))
        pyautogui.press("tab")
        pyautogui.write(str(PERIODO_FIM))
        pyautogui.press("enter")
        pyautogui.write(placa)
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("7")
        time.sleep(1)
        pyautogui.press("up", presses=4)
        time.sleep(1)

        # Unidade SPT
        pyautogui.press("up")
        time.sleep(0.5)
        pyautogui.write("SPT")
        pyautogui.press("enter")
        pyautogui.press("enter")
        pyautogui.press("enter")
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("7")
        time.sleep(1)
        pyautogui.press("up", presses=5)
        time.sleep(1)

        # Unidade BHZ
        pyautogui.write("BHZ")
        pyautogui.press("enter")
        pyautogui.press("enter")
        pyautogui.press("enter")
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("7")
        time.sleep(1)
        pyautogui.press("up", presses=5)

    pyautogui.press("esc")


def extrair_relatorio_producao_veiculos(tabela):
    """Extrai o relatório 413 - Produção de Veículos para cada placa."""
    time.sleep(1.2)
    pyautogui.hotkey("shift", "tab")
    pyautogui.write("SPO")
    time.sleep(1)
    pyautogui.write("413")
    pyautogui.press("tab")
    time.sleep(3)
    pyautogui.press("enter")
    pyautogui.press("enter")
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.write(str(PERIODO_INICIO))
    pyautogui.press("tab")
    pyautogui.write(str(PERIODO_FIM))
    pyautogui.press("enter")
    pyautogui.press("enter")
    time.sleep(0.5)

    for linha in tabela.index:
        placa = tabela.loc[linha, "Placa"]
        pyautogui.write(placa)
        time.sleep(1)
        pyautogui.press("enter")
        pyautogui.press("enter")
        pyautogui.press("enter")
        time.sleep(1.5)
        pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("esc")
        time.sleep(1.2)
        pyautogui.press("up", presses=7)

    pyautogui.press("esc")
    pyautogui.press("esc")


def extrair_relatorio_manifestos(tabela):
    """Extrai o relatório 200 - Relação de Manifestos para cada placa."""
    time.sleep(1.5)
    pyautogui.hotkey("shift", "tab")
    time.sleep(1)
    pyautogui.write("SPO")
    pyautogui.write("200")
    time.sleep(1.5)
    pyautogui.write(str(PERIODO_INICIO))
    pyautogui.press("tab")
    pyautogui.write(str(PERIODO_FIM))
    pyautogui.press("enter")
    pyautogui.write("SPO")
    pyautogui.press("enter")

    for linha in tabela.index:
        placa = tabela.loc[linha, "Placa"]
        pyautogui.write(placa)
        time.sleep(1.75)
        pyautogui.press("enter")
        pyautogui.press("tab")
        pyautogui.press("enter")
        time.sleep(1)
        pyautogui.press("esc")
        time.sleep(2.5)
        pyautogui.press("up", presses=4)

    pyautogui.press("esc")


def gerar_os_pagamento(tabela):
    """
    Gera as Ordens de Serviço (O.S.) de pagamento por prestação de
    serviço (relatório 118) para cada veículo, com o valor já conferido.
    """
    time.sleep(1.5)
    pyautogui.hotkey("shift", "tab")
    time.sleep(1)
    pyautogui.write("SPO")
    pyautogui.write("118")
    time.sleep(1.5)

    for linha in tabela.index:
        placa = tabela.loc[linha, "Placa"]
        pyautogui.write(placa)
        time.sleep(1.75)
        valor = str(tabela.loc[linha, "Valor"])
        pyautogui.write(valor)
        time.sleep(1.75)
        pyautogui.press("enter")
        pyautogui.press("enter")
        time.sleep(2)
        pyautogui.write(
            f"Pagamento por prestacao de servico referente a dezena "
            f"de {PERIODO_INICIO} A {PERIODO_FIM}"
        )
        pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.press("tab")
        pyautogui.press("enter")
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(10)

    pyautogui.press("esc")


def main():
    tabela = carregar_placas()

    acessar_sistema()
    fazer_login()
    acessar_opcao_relatorio()

    conferir_producao_por_veiculo(tabela)
    extrair_relatorio_producao_veiculos(tabela)
    extrair_relatorio_manifestos(tabela)
    gerar_os_pagamento(tabela)


if __name__ == "__main__":
    main()
