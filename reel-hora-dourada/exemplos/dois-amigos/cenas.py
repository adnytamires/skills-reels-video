"""Exemplo (história, fundo escuro): "Dois amigos" — azul-marinho + laranja.

Mostra: tela dividida com linha brilhante, um lado perdendo a cor (apagar_lado), faíscas,
títulos grandes vazados ou com brilho (texto_grande) e a faixa de mesa embaixo para a legenda.
"""
from desenho import *
from flat import *

RAFA = dict(pele="clara", cabelo="espetado", cor_cabelo=(40, 38, 42), oculos=True)
DAVI = dict(pele="morena", bone=True, cor_bone=(34, 34, 38), cor_botao=(240, 110, 30), cabelo="curto", cor_cabelo=(30, 26, 26))
LARANJA = (240, 116, 34)

def _metade_escura(c, x0, x1):
    for i in range(50): c.ret(x0, CH*i/50, x1, CH*(i + 1)/50 + 2, mistura((30, 36, 50), (22, 26, 38), i/49), contorno=False)
def _metade_quente(c, x0, x1):
    for i in range(50): c.ret(x0, CH*i/50, x1, CH*(i + 1)/50 + 2, mistura((46, 26, 20), (156, 66, 24), (i/49)**1.5), contorno=False)

# 1. o Rafa sozinho, à noite
def desenhar_rafa(k):
    c = Cena(clima="noite", ambiente=(1, 1, 1)); fundo_textura(c, (28, 34, 48), (20, 24, 36))
    janela_noite(c, 760, 120, 560, 640)
    busto(c, 720, 1260, 400, roupa="moletom", cor_roupa=(94, 108, 130), expressao="pensativo", olhar=(0.3, -0.2), **RAFA)
    notebook_costas(c, 720, 1680, 780); mesa_frente(c, 1900)
    return c

# 2. tela dividida: mesmo dia, mesma ideia
def desenhar_dupla(k):
    c = Cena(clima="noite", ambiente=(1, 1, 1)); fundo_textura(c, (28, 34, 48), (20, 24, 36)); _metade_quente(c, CW/2, CW + 10)
    busto(c, 360, 1340, 330, roupa="moletom", cor_roupa=(94, 108, 130), expressao="neutro", **RAFA)
    busto(c, 1080, 1340, 330, roupa="camiseta", cor_roupa=LARANJA, expressao="sorriso", **DAVI)
    notebook_costas(c, 360, 1680, 640); notebook_costas(c, 1080, 1680, 640, seed=3); mesa_frente(c, 1900)
    return c
def animar_dupla(im, t, D, d):
    linha_brilho(im, CW/2, t); texto_grande(im, "DIA 1", CW/2, 560, 330, (230, 226, 220), contorno=True, alfa=clamp01((t - 0.3)/0.5))

# 3. meses depois: um travado (sem cor), o outro com clientes (brilho e faíscas)
def desenhar_depois(k):
    c = Cena(clima="noite", ambiente=(1, 1, 1)); fundo_textura(c, (28, 34, 48), (20, 24, 36)); _metade_quente(c, CW/2, CW + 10)
    busto(c, 360, 1340, 330, roupa="moletom", cor_roupa=(94, 108, 130), expressao="triste", olhar=(-0.2, 0.3), **RAFA)
    busto(c, 1080, 1340, 330, roupa="camiseta", cor_roupa=LARANJA, expressao="feliz", **DAVI)
    notebook_costas(c, 360, 1680, 640); notebook_costas(c, 1080, 1680, 640, seed=3); mesa_frente(c, 1900)
    return c
def animar_depois(im, t, D, d):
    apagar_lado(im, 0, CW/2, clamp01((t - 0.4)/0.8)); faiscas(im, t, 26, (CW/2 + 20, 300, CW, 2300))
    linha_brilho(im, CW/2, t); texto_grande(im, "SÓ UM", CW/2, 520, 300, (246, 244, 240), alfa=clamp01((t - 0.6)/0.4))

# 4. a pergunta
def desenhar_pergunta(k):
    c = Cena(clima="noite", ambiente=(1, 1, 1)); fundo_textura(c, (24, 22, 26), (14, 14, 18)); return c
def animar_pergunta(im, t, D, d):
    texto_grande(im, "POR", CW/2, 1060, 300, (246, 244, 240), alfa=clamp01(t/0.3))
    texto_grande(im, "QUÊ?", CW/2, 1360, 330, (240, 116, 34), brilho=True, alfa=clamp01((t - 0.35)/0.3))
