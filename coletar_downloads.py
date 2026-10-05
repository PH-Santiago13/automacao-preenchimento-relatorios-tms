"""Pega os 3 .sswweb mais novos da pasta Downloads, move para
entrada/AAAA-MM-DD/ e renomeia por unidade, seguindo a ordem de download."""
import logging
import shutil
import time
from pathlib import Path

log = logging.getLogger("rpa")

PASTA_DOWNLOADS = Path.home() / "Downloads"   # pasta Downloads do usuário atual
BASE = Path(__file__).parent

# Na tela 076 os relatórios são PEDIDOS na ordem BHZ > SPT > SPO (ver UNIDADES em
# processar_relatorios.py). Na fila 156 o mais recente fica em cima, então o robô
# BAIXA na ordem inversa: SPO > SPT > BHZ. Esta lista é a ordem de DOWNLOAD.
ORDEM_DOWNLOAD = ["SPO", "SPT", "BHZ"]


def coletar_downloads(dia_relatorio):
    """Move e renomeia os 3 relatórios. Devolve a pasta de entrada."""
    destino = BASE / "entrada" / dia_relatorio.strftime("%Y-%m-%d")
    destino.mkdir(parents=True, exist_ok=True)

    if list(PASTA_DOWNLOADS.glob("*.crdownload")):
        raise RuntimeError("Ainda há download em andamento (.crdownload) na Downloads")

    arquivos = sorted(PASTA_DOWNLOADS.glob("*.sswweb"),
                      key=lambda p: p.stat().st_mtime)   # mais antigo primeiro
    if len(arquivos) < 3:
        raise FileNotFoundError(
            f"Esperava 3 .sswweb na Downloads e achei {len(arquivos)}: {[a.name for a in arquivos]}")
    if len(arquivos) > 3:
        log.warning("Há %d .sswweb na Downloads; usando só os 3 mais recentes", len(arquivos))

    tres = arquivos[-3:]                       # os 3 últimos = os 3 baixados agora
    for arquivo, unidade in zip(tres, ORDEM_DOWNLOAD):
        novo = destino / f"{unidade}.sswweb"
        shutil.move(str(arquivo), str(novo))
        log.info("%s  ->  %s", arquivo.name, novo)
    return destino

def coletar_manifesto(dia_relatorio, timeout=60):
    """Acha o .CSV do manifesto na Downloads (o mais novo) e move para
    entrada/AAAA-MM-DD/MANIFESTO.csv. Baixando ainda? O arquivo só conta
    quando vira .csv de verdade, então .crdownload não engana a função."""
    destino = BASE / "entrada" / dia_relatorio.strftime("%Y-%m-%d")
    destino.mkdir(parents=True, exist_ok=True)

    limite = time.time() + timeout
    csvs = []
    while time.time() < limite:
        csvs = [p for p in PASTA_DOWNLOADS.iterdir()
                if p.is_file() and p.suffix.lower() == ".csv"]
        if csvs:
            break
        time.sleep(2)
    if not csvs:
        raise FileNotFoundError(
            f"Nenhum .csv do manifesto apareceu na Downloads em {timeout}s")

    csvs.sort(key=lambda p: p.stat().st_mtime)
    if len(csvs) > 1:
        log.warning("Há %d .csv na Downloads; usando o mais novo (%s)",
                    len(csvs), csvs[-1].name)
    novo = destino / "MANIFESTO.csv"
    shutil.move(str(csvs[-1]), str(novo))
    log.info("%s  ->  %s", csvs[-1].name, novo)
    return novo


def coletar_romaneios(dia_relatorio, iniciado_em, timeout=90):
    """Move para a pasta do dia o .sswweb novo da opção 36.

    A opção 36 baixa direto na pasta Downloads. O horário evita recolher um
    arquivo deixado por uma execução anterior; o cabeçalho confirma que é o
    relatório de romaneios antes de movê-lo.
    """
    destino = BASE / "entrada" / dia_relatorio.strftime("%Y-%m-%d")
    destino.mkdir(parents=True, exist_ok=True)

    limite = time.time() + timeout
    while time.time() < limite:
        if not list(PASTA_DOWNLOADS.glob("*.crdownload")):
            candidatos = sorted(
                (p for p in PASTA_DOWNLOADS.glob("*.sswweb")
                 if p.stat().st_mtime >= iniciado_em - 2),
                key=lambda p: p.stat().st_mtime,
            )
            for arquivo in reversed(candidatos):
                with open(arquivo, encoding="latin-1") as fonte:
                    cabecalho = next(
                        (linha for linha in fonte if "CIDADE_ENTREGA" in linha.upper()),
                        "",
                    )
                if "ROMANEIO" in cabecalho.upper() and "BAIRRO" in cabecalho.upper():
                    novo = destino / "ROMANEIOS.sswweb"
                    shutil.move(str(arquivo), str(novo))
                    log.info("%s  ->  %s", arquivo.name, novo)
                    return novo
        time.sleep(2)

    raise FileNotFoundError(
        f"Não apareceu um novo .sswweb da opção 36 em {timeout}s; "
        "confirme se o relatório foi exportado no formato Excel"
    )