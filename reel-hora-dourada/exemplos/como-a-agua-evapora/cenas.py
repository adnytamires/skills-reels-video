"""Exemplo (tutorial, fundo claro): "Como a água evapora" — branco + azul, só texto na tela.

Mostra: personagem fixo definido uma vez (LIA), faixa clara embaixo para a legenda (mesa_frente),
objetos explicativos animados (partículas, sol, termômetro, cartões, nuvem) com camada() dentro de animar_.
Cada cena: desenhar_<nome>(k) -> Cena  (1 vez)   +   animar_<nome>(im, t, D, d)  (a cada quadro, opcional).
"""
from desenho import *
from flat import *

AZUL, AZUL_CLARO, AGUA = (47, 128, 237), (196, 222, 250), (92, 164, 242)
TINTA = (31, 42, 58)
FUNDO = (246, 248, 251)
LIA = dict(pele="media", cabelo="rabo", cor_cabelo=(58, 36, 30))
ROUPA = dict(roupa="camiseta", cor_roupa=AZUL)

def _fundo(c, chao=None):
    fundo_textura(c, (250, 251, 253), (238, 242, 247), linhas=False, ruido=0.012)
    if chao: c.ret(-10, chao, CW + 10, CH + 10, (226, 233, 241), contorno=False); c.ret(-10, chao, CW + 10, chao + 8, (210, 220, 232), contorno=False)

def _cena(): return Cena(clima="interior", ambiente=(1, 1, 1))

# ---------- 1. a pergunta: Lia pensando na poça
def desenhar_pergunta(k):
    c = _cena(); _fundo(c, 1900)
    balao_pensamento(c, 860, 700, 760, 520)
    c.elipse(860, 820, 250, 60, AGUA, contorno=False); c.elipse(820, 808, 150, 26, mistura(AGUA, (255, 255, 255), 0.35), contorno=False)   # poça
    busto(c, 520, 1250, 380, expressao="pensativo", olhar=(0.5, -0.5), **ROUPA, **LIA)
    mesa_frente(c, 1800, (232, 238, 245))
    return c
def animar_pergunta(im, t, D, d):
    sol(im, 1070, 600, 70, t)
    texto_grande(im, "?", 1250, 1100, 260, AZUL, alfa=clamp01((t - 0.4)/0.3))

# ---------- 2 e 3. a água vista de perto (partículas)
CX, CY0, LW, LH = 720, 1000, 1080, 760        # caixa de água: centro x, topo, largura, altura
def _caixa(c):
    c.ret(CX - LW/2 - 16, CY0 - 120, CX + LW/2 + 16, CY0 + LH + 16, (214, 226, 240), contorno=False, raio=40)
    c.ret(CX - LW/2, CY0 - 104, CX + LW/2, CY0 + LH, (252, 253, 255), contorno=False, raio=30)
    c.ret(CX - LW/2, CY0, CX + LW/2, CY0 + LH, AZUL_CLARO, contorno=False, raio=30); c.ret(CX - LW/2, CY0, CX + LW/2, CY0 + 40, AZUL_CLARO, contorno=False)
def desenhar_particulas(k):
    c = _cena(); _fundo(c); _caixa(c); return c
def desenhar_calor(k):
    c = _cena(); _fundo(c); _caixa(c); return c

def _bolinhas(im, t, vel, escapam=()):
    rnd = random.Random(7); pts = []
    for i in range(46):
        bx, by = rnd.uniform(CX - LW/2 + 60, CX + LW/2 - 60), rnd.uniform(CY0 + 60, CY0 + LH - 50); f1, f2 = rnd.uniform(1, 2.2), rnd.uniform(0, 6.28)
        x = bx + 24*vel*math.sin(t*f1*vel*2 + f2); y = by + 18*vel*math.cos(t*f1*vel*1.7 + f2*1.3); vapor = 0.0
        for (j, t0) in escapam:
            if i == j and t > t0:
                s = t - t0; x = lerp(x, CX - LW/2 + 120 + (j*97) % (LW - 240), clamp01(s*1.5)); y = CY0 + 30 - s*330; vapor = clamp01(s*1.2)
        pts.append((x, y, vapor))
    def des(d, T, k):
        for x, y, v in pts:
            cx, cy = T(x, y); r = 26*k
            cor = mistura(AZUL, (230, 240, 255), v*0.75); d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=cor + (int(255*(1 - 0.35*v)),))
            if v > 0: d.line([T(x, y + 40), T(x, y + 120)], fill=AZUL_CLARO + (int(200*(1 - v*0.6)),), width=int(8*k))
    camada(im, (0, 0, CW, CY0 + LH + 40), des)

def animar_particulas(im, t, D, d):
    _bolinhas(im, t, 0.6); texto_grande(im, "ÁGUA", CX, CY0 - 220, 96, AZUL, alfa=clamp01((t - 0.3)/0.4))
def animar_calor(im, t, D, d):
    sol(im, CX, 520, 120, t)
    _bolinhas(im, t, 0.6 + 0.9*clamp01(t/1.2), escapam=[(3, 1.2), (11, 1.6), (19, 2.0), (27, 2.3), (34, 2.7)])
    texto_grande(im, "VAPOR", CX + 360, CY0 - 250, 80, AZUL, alfa=clamp01((t - 2.0)/0.4))

# ---------- 4. sem ferver: termômetro
def desenhar_semferver(k):
    c = _cena(); _fundo(c, 1900)
    x, y0, y1 = 980, 360, 1560
    c.ret(x - 60, y0, x + 60, y1, (226, 234, 244), contorno=False, raio=60); c.elipse(x, y1 + 40, 110, 110, (226, 234, 244), contorno=False)
    c.ret(x - 26, y1 - 520, x + 26, y1 + 20, (235, 87, 87), contorno=False, raio=26); c.elipse(x, y1 + 40, 76, 76, (235, 87, 87), contorno=False)
    for i in range(6): c.ret(x - 110, y0 + 80 + i*180, x - 70, y0 + 92 + i*180, (180, 192, 208), contorno=False)
    c.texto(x - 380, y0 + 40, "100 °C", 70, (180, 192, 208), "titulo"); c.texto(x - 340, y1 - 560, "30 °C", 80, (235, 87, 87), "titulo")
    c.ret(330, 1500, 640, 1520, (210, 220, 232), contorno=False)
    c.forma([(370, 1240), (600, 1240), (580, 1500), (390, 1500)], (226, 236, 248), contorno=False)                   # copo
    c.forma([(380, 1320), (590, 1320), (580, 1490), (390, 1490)], AGUA, contorno=False)
    return c
def animar_semferver(im, t, D, d):
    def des(dd, T, k):
        for i in range(4):
            fase = (t*0.6 + i*0.25) % 1.0; x = 430 + i*40; y = 1290 - fase*520; a = int(200*math.sin(math.pi*fase))
            pts = [T(x + 22*math.sin(j*0.8 + t*2 + i), y - j*30) for j in range(8)]
            dd.line(pts, fill=AZUL_CLARO + (a,), width=int(14*k), joint="curve")
    camada(im, (300, 600, 720, 1320), des)

# ---------- 5. o que acelera: calor, vento, superfície
def desenhar_dicas(k):
    c = _cena(); _fundo(c)
    for i in range(3):
        y = 380 + i*470; c.ret(180, y, 1260, y + 400, (255, 255, 255), contorno=False, raio=40); c.ret(180, y, 196, y + 400, AZUL, contorno=False, raio=8)
    y = 380 + 470*2; c.traco([(330, y + 130), (640, y + 130)], (120, 130, 140), 5)   # varal
    for j, cc in enumerate((AZUL, (255, 196, 60), (235, 87, 87))):
        x0 = 350 + j*95; c.forma([(x0, y + 135), (x0 + 80, y + 135), (x0 + 75, y + 260), (x0 + 5, y + 260)], cc, contorno=False)
    return c
NOMES = ["CALOR", "VENTO", "SUPERFÍCIE"]
def animar_dicas(im, t, D, d):
    for i in range(3):
        a = clamp01((t - 0.3 - i*0.9)/0.35); y = 380 + i*470
        if a <= 0: continue
        if i == 0: sol(im, 440, y + 200, 90, t)
        if i == 1:
            def des(dd, T, k, a=a):
                for j in range(3):
                    yy = y + 120 + j*80; o = (t*300 + j*90) % 200
                    dd.line([T(330 + o, yy), T(520 + o, yy)], fill=AZUL + (int(255*a),), width=int(16*k))
                    dd.arc([*T(500 + o, yy - 50), *T(580 + o, yy + 10)], 270, 90, fill=AZUL + (int(255*a),), width=int(16*k)) if j == 1 else None
            camada(im, (300, y + 40, 800, y + 360), des)
        texto_grande(im, NOMES[i], 990, y + 200, 80, AZUL if i != 2 else TINTA, alfa=a)

# ---------- 6. o vapor sobe e vira nuvem
def desenhar_nuvem(k):
    c = _cena(); fundo_textura(c, (214, 232, 252), (246, 248, 251), linhas=False, ruido=0.01)
    c.ret(-10, 2050, CW + 10, CH + 10, (226, 233, 241), contorno=False)
    c.elipse(720, 2060, 330, 60, AGUA, contorno=False)
    return c
def animar_nuvem(im, t, D, d):
    s = 0.4 + 1.1*ease(clamp01((t - 0.6)/1.8)); nuvem(im, 720, 620, s, em_cena=False)
    def des(dd, T, k):
        for i in range(7):
            fase = (t*0.45 + i/7) % 1.0; x = 520 + i*65; y = 2000 - fase*1300; a = int(220*math.sin(math.pi*fase))
            dd.ellipse([*T(x - 18, y - 18), *T(x + 18, y + 18)], fill=AZUL_CLARO + (a,))
    camada(im, (400, 600, 1040, 2060), des)

# ---------- 7. fim: Lia feliz ao lado do varal
def desenhar_varal(k):
    c = _cena(); _fundo(c, 1900)
    c.ret(200, 420, 214, 1900, (150, 158, 168), contorno=False); c.ret(1226, 420, 1240, 1900, (150, 158, 168), contorno=False)
    c.traco([(207, 470), (720, 520), (1233, 470)], (120, 130, 140), 5, suave=True)
    for j, (xx, cc) in enumerate(((420, AZUL), (720, (255, 196, 60)), (1020, (235, 87, 87)))):
        yy = 470 + 50*math.sin(math.pi*(xx - 207)/1026)
        c.forma([(xx - 110, yy), (xx - 40, yy - 6), (xx + 40, yy - 6), (xx + 110, yy), (xx + 140, yy + 90), (xx + 80, yy + 110), (xx + 75, yy + 330), (xx - 75, yy + 330), (xx - 80, yy + 110), (xx - 140, yy + 90)], cc, contorno=False)
    busto(c, 720, 1220, 400, expressao="feliz", **ROUPA, **LIA)
    mesa_frente(c, 1800, (232, 238, 245))
    return c
def animar_varal(im, t, D, d): sol(im, 1240, 230, 80, t)
