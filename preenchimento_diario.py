import os
import time

import pyautogui
from dotenv import load_dotenv
from coletar_downloads import coletar_downloads, coletar_manifesto, coletar_romaneios
from processar_relatorios import processar, processar_manifesto, BASE
from utils import configurar_log, dia_alvo, foto_do_erro, esperar_ate, janela_existe
import pygetwindow as gw

load_dotenv()
log = configurar_log()
dia_relatorio = dia_alvo()


SISTEMA_URL = os.getenv("SISTEMA_URL")
CPF_USUARIO = os.getenv("CPF_USUARIO_1")
LOGIN_USUARIO = os.getenv("LOGIN_USUARIO_1")
SENHA_USUARIO = os.getenv("SENHA_USUARIO_1")

# Títulos das janelas (anotados com descobrir_titulos.py)
TELA_LOGIN = "Login Sistema SSW"
TELA_MENU = "Menu Principal"
TELA_076 = "076 - Emissão Demonstrativo Coletas/Entregas"
TELA_156 = "156 - Fila de processamento em lotes"
TELA_200 = "200 - Relação de Manifestos Operacionais"
TELA_036 = "Romaneios"
DATA_STR = dia_relatorio.strftime("%d%m%y")   # ex.: 180926 -> SSW pula sozinho de campo

pyautogui.PAUSE = 0.5


def acessar_sistema():
    pyautogui.press("win")
    pyautogui.write("chrome")
    pyautogui.press("enter")
    esperar_ate("Google Chrome", timeout=60)
    time.sleep(1)                         # dá tempo da barra de endereço aceitar foco
    pyautogui.hotkey("ctrl", "l")         # garante que o cursor está na barra de endereço
    pyautogui.write(SISTEMA_URL)
    pyautogui.press("enter")
    esperar_ate(TELA_LOGIN, timeout=60)


def fazer_login():
    time.sleep(1.5)                  # título chega antes dos campos; dá tempo do foco cair em Usuário
    pyautogui.hotkey("shift", "tab") # Usuário -> CPF
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(CPF_USUARIO)     # SSW pula sozinho para Usuário
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(LOGIN_USUARIO)   # pula para Senha
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(SENHA_USUARIO)
    pyautogui.press("tab")
    pyautogui.press("enter")
    limite = time.time() + 60
    while time.time() < limite:
        if janela_existe(TELA_MENU):
            return
        time.sleep(0.5)
    raise RuntimeError("Login não avançou: verifique CPF/usuário/senha no .env ou o print em logs/")

def _titulo_janela_ativa():
    """Título da janela em primeiro plano ('' se nenhuma)."""
    try:
        janela = gw.getActiveWindow()
        return janela.title if janela else ""
    except Exception:
        return ""


def voltar_ao_menu(tentativas=10):
    """Fecha com ESC o que estiver na frente até o Menu Principal ficar ATIVO.
    Existir ao fundo não basta: precisa estar em primeiro plano."""
    for _ in range(tentativas):
        if TELA_MENU in _titulo_janela_ativa():
            return
        pyautogui.press("esc")      # só aperta Esc quando o menu NÃO é a janela ativa
        time.sleep(1)
    raise TimeoutError(
        f"Não voltei ao Menu Principal; janela ativa: {_titulo_janela_ativa()!r}"
    )

def abrir_opcao(codigo, titulo_esperado):
    """No menu, digita MTZ + código e espera a tela abrir."""
    time.sleep(1.5)                 # menu chega antes do foco cair no campo Opção
    log.info("Janela ativa: %s", _titulo_janela_ativa())
    pyautogui.hotkey("shift", "tab") # Opção -> Unidade
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write("MTZ")           # SSW pula sozinho para Opção após 3 letras
    pyautogui.write(str(codigo))
    pyautogui.press("tab")
    esperar_ate(titulo_esperado)


def acessar_opcao_relatorio():
    abrir_opcao(76, TELA_076)


def acessar_fila_processamento():
    voltar_ao_menu()
    abrir_opcao(156, TELA_156)


def extrair_unidade(unidade, reabrir=True):
    """Com a 076 recém-aberta (foco em Unidade): preenche, gera e, se ainda
    houver outra unidade, volta ao menu e reabre a 076 zerada."""
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(unidade)        # pula sozinho para a data inicial
    pyautogui.write(DATA_STR)       # pula sozinho para a data final
    pyautogui.write(DATA_STR)
    pyautogui.press("enter")        # gera -> tela de formato
    time.sleep(1.5)
    pyautogui.write("E")            # formato excel
    time.sleep(1.5)
    pyautogui.press("esc")          # fecha o formato -> formulário 076
    time.sleep(1)
    if reabrir:
        voltar_ao_menu()            # Escs com checagem de título até o menu
        abrir_opcao(76, TELA_076)   # 076 zerada: foco volta a nascer em Unidade
    log.info("Comandos da 076 enviados para %s", unidade)


def extrair_unidade_bhz():
    extrair_unidade("BHZ")


def extrair_unidade_spt():
    extrair_unidade("SPT")


def extrair_unidade_spo():
    extrair_unidade("SPO", reabrir=False)   # última: o próprio baixar_relatorios fecha


def extrair_manifesto():
    """Tela 200: período = dia alvo, unidade SPO, formato Excel.
    O CSV cai direto na Downloads (sem passar pela fila 156)."""
    voltar_ao_menu()                     # fecha a 076 que sobrou do SPO
    abrir_opcao(200, TELA_200)           # foco nasce no 1º campo do período
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(DATA_STR)            # pula sozinho para a 2ª data
    pyautogui.write(DATA_STR)            # pula sozinho para Unidade origem
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write("SPO")
    pyautogui.press("tab", presses=6)    # Unidade -> ... -> 'Tipo de arquivo'
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write("E")                 # troca o T pré-preenchido
    time.sleep(3)
    voltar_ao_menu()                     # fecha bolha de download / resultados até o menu
    log.info("Comandos da 200 enviados (SPO)")


def extrair_romaneios():
    """Tela 36: exporta a relação de romaneios do dia como .sswweb."""
    voltar_ao_menu()
    abrir_opcao(36, TELA_036)
    pyautogui.press("tab", presses=13)   # ir até o campo de para baixar como Excel
    pyautogui.write("S")                 # troca o N pré-preenchido 
    pyautogui.press("tab", presses=5)    # ir até o campo de período
    pyautogui.hotkey("ctrl", "a")
    pyautogui.write(DATA_STR)            # início do período
    pyautogui.write(DATA_STR)            # fim do período
    pyautogui.press("ENTER")
    inicio_download = time.time()
    time.sleep(3)
    voltar_ao_menu()
    coletar_romaneios(dia_relatorio, inicio_download)
    log.info("Romaneios da opção 36 baixados")


def organizar_manifesto():
    """Python assume: move o CSV baixado e mantém só as colunas do formato final."""
    caminho = coletar_manifesto(dia_relatorio)
    processar_manifesto(caminho, BASE / "saida" / dia_relatorio.strftime("%Y-%m-%d"))


def organizar_e_processar():
    """Python assume: move/renomeia os downloads e gera a consolidada."""
    pasta = coletar_downloads(dia_relatorio)
    processar(pasta, BASE / "saida" / dia_relatorio.strftime("%Y-%m-%d"))



def baixar_relatorios():
    acessar_fila_processamento()
    time.sleep(15)           # espera o SSW processar a fila (a tela não muda)
    pyautogui.press("tab")   # botão "atualizar"
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)
    pyautogui.press("tab", presses=11)
    time.sleep(0.5)
    pyautogui.press("enter")                 # baixa SPO
    pyautogui.press("tab")
    pyautogui.press("enter")                 # baixa SPT
    pyautogui.press("tab")
    pyautogui.press("enter")                 # baixa BHZ
    time.sleep(3)
    pyautogui.press("esc")
    pyautogui.press("esc")
    pyautogui.hotkey("alt", "f4")


def main():
    log.info("Rodando para o dia %s", dia_relatorio.strftime("%d/%m/%Y"))
    etapas = [
        ("acessar_sistema", acessar_sistema),
        ("fazer_login", fazer_login),
        ("extrair_romaneios", extrair_romaneios),
        ("acessar_opcao_relatorio", acessar_opcao_relatorio),
        ("extrair_unidade_bhz", extrair_unidade_bhz),
        ("extrair_unidade_spt", extrair_unidade_spt),
        ("extrair_unidade_spo", extrair_unidade_spo),
        ("extrair_manifesto", extrair_manifesto),
        ("baixar_relatorios", baixar_relatorios),
        ("organizar_e_processar", organizar_e_processar),
        ("organizar_manifesto", organizar_manifesto),
    
        
    ]
    for nome, funcao in etapas:
        log.info("INÍCIO %s", nome)
        try:
            funcao()
        except Exception:
            log.exception("FALHA em %s", nome)
            foto_do_erro(nome)
            break   # melhor parar do que continuar digitando às cegas
        log.info("FIM %s", nome)

if __name__ == "__main__":
    main()

