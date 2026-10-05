"""Lê os .sswweb das 3 unidades, junta tudo e gera 1 linha por placa
(coletas e entregas em colunas separadas)."""
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

log = logging.getLogger("rpa")

UNIDADES = ["BHZ", "SPT", "SPO"]          # ordem em que você pede no SSW
TIPOS_VALIDOS = {"C": "coleta", "E": "entrega"}
COLUNAS_USADAS = ["PLACA", "TIPO BAIXA", "DATA BAIXA", "CTRC",
                  "SET", "PESO CALCULO", "VLR FRETE"]
PADRAO_PLACA = r"^[A-Z]{3}\d[A-Z0-9]\d{2}$"   # cobre AAA1234 e AAA1B23 (Mercosul)
BASE = Path(__file__).parent      # pasta onde ESTE arquivo mora, não onde o terminal está

load_dotenv(BASE / ".env")   # este módulo é importado antes do load_dotenv() do script principal
ARQUIVO_PLACAS = Path(os.getenv("ARQUIVO_PLACAS", BASE / "dados_placas.xlsx"))


def carregar_placas():
    """Lê a lista da filial: Placa -> MOTORISTA."""
    lista = pd.read_excel(ARQUIVO_PLACAS, sheet_name="Planilha1", dtype=str)
    lista["Placa"] = lista["Placa"].str.strip().str.upper()
    lista["MOTORISTA"] = lista["MOTORISTA"].str.strip()
    duplicadas = lista[lista["Placa"].duplicated()]["Placa"].tolist()
    if duplicadas:
        log.warning("Placas repetidas em dados_placas.xlsx: %s", duplicadas)
    return lista.drop_duplicates("Placa").set_index("Placa")["MOTORISTA"]


def numero_br(serie):
    """Transforma '1.234,56' em 1234.56 (número de verdade)."""
    limpo = serie.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(limpo, errors="coerce")


def ler_relatorio(caminho, unidade):
    """Lê um .sswweb (texto separado por ';', acentuação latin-1)."""
    if not caminho.exists():
        # Faltou uma unidade? Melhor parar do que somar só 2 das 3 sem avisar.
        raise FileNotFoundError(f"Não achei o relatório de {unidade}: {caminho}")
    df = pd.read_csv(caminho, sep=";", encoding="latin-1", dtype=str,
                     usecols=COLUNAS_USADAS)
    for coluna in df.columns:
        df[coluna] = df[coluna].str.strip()      # tira os espaços de preenchimento
    df["UNIDADE"] = unidade
    log.info("%s: %d linhas lidas", unidade, len(df))
    return df


def separar_problemas(df, motoristas):
    """Converte tipos e separa as linhas boas das que precisam de revisão."""
    df = df.copy()
    df["PLACA"] = df["PLACA"].str.upper()
    df["TIPO BAIXA"] = df["TIPO BAIXA"].str.upper()
    df["PESO CALCULO"] = numero_br(df["PESO CALCULO"])
    df["VLR FRETE"] = numero_br(df["VLR FRETE"])

    placa = df["PLACA"].fillna("")
    condicoes = [
        placa == "",
        ~placa.str.match(PADRAO_PLACA),
        ~placa.isin(motoristas.index),
        ~df["TIPO BAIXA"].isin(list(TIPOS_VALIDOS)),
        df["PESO CALCULO"].isna() | df["VLR FRETE"].isna(),
    ]
    motivos = [
        "placa vazia",
        "placa fora do formato",
        "placa fora da lista",
        "tipo de baixa diferente de C/E",
        "peso ou valor ilegível",
    ]
    df["MOTIVO"] = np.select(condicoes, motivos, default="")
    boas = df[df["MOTIVO"] == ""].drop(columns="MOTIVO")
    problemas = df[df["MOTIVO"] != ""]
    return boas, problemas


def rota_da_placa(serie_set):
    """SET mais frequente da placa (regra provisória, ver conversa)."""
    return serie_set.mode().iloc[0]


def agregar_por_placa(df, motoristas):
    """Uma linha por placa: coletas e entregas lado a lado."""
    soma = (df.groupby(["PLACA", "TIPO BAIXA"])
              .agg(valor=("VLR FRETE", "sum"),
                   qtde=("CTRC", "count"),
                   peso=("PESO CALCULO", "sum"))
              .unstack("TIPO BAIXA", fill_value=0))
    # garante as duas colunas (C e E) mesmo que um dia não tenha nenhuma entrega
    soma = soma.reindex(columns=pd.MultiIndex.from_product(
        [["valor", "qtde", "peso"], ["C", "E"]]), fill_value=0)

    rotas = df.groupby("PLACA")["SET"].agg(rota_da_placa)
    ambiguas = df.groupby("PLACA")["SET"].nunique()
    for placa in ambiguas[ambiguas > 1].index:
        log.warning("Placa %s tem %d setores diferentes; usei o mais frequente (%s)",
                    placa, ambiguas[placa], rotas[placa])

    final = pd.DataFrame({
        "Placa": soma.index,
        "Motorista": motoristas.reindex(soma.index).values,                   
        "Rota": rotas.reindex(soma.index).values,
        "VALOR coletas": soma[("valor", "C")].values,
        "QTDE Coletas": soma[("qtde", "C")].values,
        "Peso coleta": soma[("peso", "C")].values,
        "VALOR entregas": soma[("valor", "E")].values,
        "QTDE Entregas": soma[("qtde", "E")].values,
        "Peso entregas": soma[("peso", "E")].values,
    })
    return final.round(2)


def processar(pasta_entrada, pasta_saida):
    pasta_entrada, pasta_saida = Path(pasta_entrada), Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    motoristas = carregar_placas()                      # <- lê dados_placas.xlsx uma vez só

    juntos = pd.concat(
        [ler_relatorio(pasta_entrada / f"{u}.sswweb", u) for u in UNIDADES],
        ignore_index=True)
    boas, problemas = separar_problemas(juntos, motoristas)   # <- passa a lista adiante
    log.info("Total: %d linhas | boas: %d | para revisão: %d",
             len(juntos), len(boas), len(problemas))

    final = agregar_por_placa(boas, motoristas)               # <- e aqui também
    romaneios = processar_romaneios(
        pasta_entrada / "ROMANEIOS.sswweb", final["Placa"].tolist())
    final = final.merge(romaneios, how="left", left_on="Placa", right_on="PLACA")
    final = final.drop(columns="PLACA")
    colunas_romaneio = ["MOTORISTA", "CIDADE_ENTREGA", "BAIRRO"]
    final[colunas_romaneio] = final[colunas_romaneio].fillna("")
    opcoes = dict(sep=";", decimal=",", index=False, encoding="utf-8-sig")
    final.to_csv(pasta_saida / "producao_consolidada.csv", **opcoes)
    if len(problemas):
        problemas.to_csv(pasta_saida / "revisao.csv", **opcoes)
        log.warning("Linhas para revisão salvas em revisao.csv")
    log.info("Gerado producao_consolidada.csv com %d placas", len(final))
    return final



COLUNAS_MANIFESTO = ["NUM_MANIF", "DEST_MANIF", "PLACA_CAVALO",
                     "PESO CALCULO (KG)", "FRETE-R$", "SITUACAO"]

def _normar(nome):
    """'PESO_CALCULO (KG)' e 'PESO CALCULO (KG)' caem no mesmo lugar."""
    return " ".join(nome.upper().replace("_", " ").split())

def _linha_do_cabecalho(caminho, marcador="NUM_MANIF"):
    """Relatórios SSW vêm com linhas de título antes do cabeçalho.
    Devolve o índice (0-based) da linha que contém o marcador."""
    marcador = _normar(marcador)
    with open(caminho, encoding="latin-1") as f:
        for i, linha in enumerate(f):
            celulas = [_normar(c.strip().strip('"')) for c in linha.split(";")]
            if marcador in celulas:
                return i
    raise ValueError(f"Cabeçalho do manifesto não encontrado: procurei '{marcador}' no arquivo todo")

def processar_manifesto(caminho_csv, pasta_saida):
    """Manifesto (200): mantém só as colunas do formato final."""
    pasta_saida = Path(pasta_saida)
    pasta_saida.mkdir(parents=True, exist_ok=True)
    caminho_csv = Path(caminho_csv)
    if not caminho_csv.exists():
        raise FileNotFoundError(f"Não achei o manifesto: {caminho_csv}")

    cabecalho = _linha_do_cabecalho(caminho_csv)
    df = pd.read_csv(caminho_csv, sep=";", encoding="latin-1", dtype=str, header=cabecalho)
    if df.shape[1] == 1:                    # separador não era ';' — tenta vírgula
        df = pd.read_csv(caminho_csv, sep=",", encoding="latin-1", dtype=str, header=cabecalho)
    df.columns = [c.strip() for c in df.columns]

    mapa = {_normar(c): c for c in df.columns}
    faltando = [c for c in COLUNAS_MANIFESTO if _normar(c) not in mapa]
    if faltando:
        raise ValueError(
            f"Manifesto sem as colunas esperadas: {faltando}; encontrei: {list(df.columns)}")
    df = df[[mapa[_normar(c)] for c in COLUNAS_MANIFESTO]]
    df.columns = COLUNAS_MANIFESTO

    for coluna in df.columns:
        df[coluna] = df[coluna].str.strip()
    destino = pasta_saida / "manifesto.csv"
    df.to_csv(destino, sep=";", index=False, encoding="utf-8-sig")
    log.info("Manifesto tratado: %d linhas -> %s", len(df), destino)
    return destino


COLUNAS_ROMANEIO = ["PLACA", "MOTORISTA", "CIDADE_ENTREGA", "BAIRRO"]


def processar_romaneios(caminho, placas_validas):
    """Lê do relatório 36 os dados de entrega das placas aprovadas."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Não achei o relatório de romaneios: {caminho}")

    cabecalho = _linha_do_cabecalho(caminho, "ROMANEIO")
    colunas_necessarias = {_normar(c) for c in COLUNAS_ROMANEIO}
    df = pd.read_csv(
        caminho, sep=";", encoding="latin-1", dtype=str, header=cabecalho,
        usecols=lambda coluna: _normar(coluna) in colunas_necessarias,
    )
    mapa = {_normar(c): c for c in df.columns}
    faltando = [c for c in COLUNAS_ROMANEIO if _normar(c) not in mapa]
    if faltando:
        raise ValueError(
            f"Relatório 36 sem as colunas esperadas: {faltando}; "
            f"encontrei: {list(df.columns)}"
        )
    df = df[[mapa[_normar(c)] for c in COLUNAS_ROMANEIO]].copy()
    df.columns = COLUNAS_ROMANEIO
    for coluna in COLUNAS_ROMANEIO:
        df[coluna] = df[coluna].fillna("").str.strip()
    df["PLACA"] = df["PLACA"].str.upper()
    df = df[
        df["PLACA"].str.match(PADRAO_PLACA, na=False)
        & df["PLACA"].isin(placas_validas)
    ]

    def valores_unicos(serie):
        valores = dict.fromkeys(valor for valor in serie if valor)
        return " / ".join(valores)

    return (df.groupby("PLACA", sort=False)[COLUNAS_ROMANEIO[1:]]
              .agg(valores_unicos)
              .reset_index())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s | %(levelname)s | %(message)s")
    entrada = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "entrada_teste"
    processar(entrada, BASE / "saida_teste")