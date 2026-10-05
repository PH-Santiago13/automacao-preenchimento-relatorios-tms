# utils.py
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import pyautogui
import pygetwindow as gw

PASTA_LOGS = Path(__file__).parent / "logs"
PASTA_LOGS.mkdir(exist_ok=True)


def configurar_log():
    """Grava tudo em logs/AAAA-MM-DD.log e também mostra na tela."""
    arquivo = PASTA_LOGS / f"{datetime.now():%Y-%m-%d}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(arquivo, encoding="utf-8"),
                  logging.StreamHandler()],
    )
    return logging.getLogger("rpa")


def dia_alvo(hoje=None):
    """Segunda-feira -> sexta (3 dias atrás). Nos outros dias -> ontem."""
    hoje = hoje or datetime.now()
    dias = 3 if hoje.weekday() == 0 else 1   # segunda = 0
    return hoje - timedelta(days=dias)


def foto_do_erro(nome_etapa):
    """Print da tela no momento da falha, salvo em logs/. Nunca levanta erro."""
    arquivo = PASTA_LOGS / f"erro_{nome_etapa}_{datetime.now():%Y%m%d_%H%M%S}.png"
    try:
        pyautogui.screenshot(str(arquivo))
        return arquivo
    except Exception as e:
        logging.getLogger("rpa").warning("Não consegui tirar o print: %s", e)
        return None


def esperar_ate(trecho_titulo, timeout=30, assentar=1.5):
    """Espera aparecer uma janela cujo título contenha `trecho_titulo`,
    depois aguarda `assentar` segundos para a página terminar de carregar
    (o título aparece antes dos campos receberem foco)."""
    limite = time.time() + timeout
    while time.time() < limite:
        for titulo in gw.getAllTitles():
            if trecho_titulo in titulo:
                time.sleep(assentar)
                return titulo
        time.sleep(0.5)
    raise TimeoutError(f"Janela '{trecho_titulo}' não apareceu em {timeout}s")

def janela_existe(trecho_titulo):
    return any(trecho_titulo in t for t in gw.getAllTitles())