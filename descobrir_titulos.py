# descobrir_titulos.py
import time
import pygetwindow as gw

print("Navegue pelas telas. Vou anotar os títulos por 3 minutos.")
vistos = set()
fim = time.time() + 180
while time.time() < fim:
    for titulo in gw.getAllTitles():
        if titulo.strip() and titulo not in vistos:
            vistos.add(titulo)
            print(titulo)
    time.sleep(5)
ativo = gw.getActiveWindow()
if ativo:
    print("ATIVA ->", ativo.title)


