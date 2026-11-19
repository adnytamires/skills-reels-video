"""Exemplo do nicho de produtividade: resumir uma conversa longa de e-mail com IA."""
import math
from pixelkit import *

def arte_gancho(a, t, D):
    a.escritorio(t)
    x0, y0, x1, y1 = a.computador(30, 76, cor_tela=BRANCO)
    n = min(7, int(t * 3))                      # e-mails chegando
    for i in range(n): a.linhas_texto(x0 + 3, y0 + 3 + i * 4, [40], cor=a.tema.cor if i == n - 1 else CINZAE)
    for i in range(3):                          # envelopes voando
        k = ((t * 0.7 + i * 0.33) % 1)
        a.envelope(int(lerp(-20, 100, k)), int(58 + 10 * math.sin(k * 6 + i)), 12, 8)
    a.sprite(PESSOA_PISCA if piscar(t) else PESSOA, 6, 99, cores={"H": CABELO[1], "S": PELE[1]})
def textos_gancho(x, t, D):
    if t > 0.8: x.etiqueta(135, 150, f"{min(23, int(t * 6)):02d} RESPOSTAS", "vermelho")

def arte_cola(a, t, D):
    a.escritorio(t)
    x0, y0, x1, y1 = a.computador(20, 60, w=66, h=50)
    k = clamp01((t - 0.3) / (D * 0.5))
    a.balao(x1 - 40, y0 + 4, 36, 14, a.tema.cor, lado="dir")
    a.linhas_texto(x1 - 37, y0 + 8, [30, 26, 18], cor=BRANCO, revelar=k)
    if k >= 1:
        kk = clamp01((t - 0.3 - D * 0.5) / 1.0)
        a.balao(x0 + 3, y0 + 24, 44, 20, BRANCO)
        a.linhas_texto(x0 + 6, y0 + 28, [36, 30, 34, 20], cor=CINZAE, revelar=kk)
    a.xicara(90, 110)

def arte_confere(a, t, D):
    a.escritorio(t)
    a.documento(14, 62, 38, 50, revelar=1)
    m = int(clamp01((t - 0.4) / (D * 0.6)) * 3.99)
    a.checklist(60, 70, itens=3, marcados=m, w=36)
    if m >= 3: a.brilho(98, 66); a.brilho(56, 64)
def textos_confere(x, t, D):
    m = int(clamp01((t - 0.4) / (D * 0.6)) * 3.99)
    for i, s in enumerate(["DATAS", "PEDIDOS", "QUEM FAZ"][:m]):
        x.etiqueta([52, 135, 222][i], 300, s, "ouro" if i == m - 1 else "marca")

def arte_fim(a, t, D):
    a.ceu(t=t)
    a.sprite(PESSOA_PISCA if piscar(t, 2.4) else PESSOA, 20, 109 - int(2 * abs(math.sin(t * 5))), cores={"H": CABELO[1], "S": PELE[1]})
    a.sprite(CORACAO, 40, 100 - int(t * 6) % 12)
    a.sprite(ESTRELA, 70, 84)
