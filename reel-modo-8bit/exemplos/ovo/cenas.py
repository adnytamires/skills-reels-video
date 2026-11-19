"""Exemplo: como um ovo nasce. Cada cena tem arte_<nome>(a, t, D) e, se precisar, textos_<nome>(x, t, D).
a = camada de desenho (108x192), x = camada de texto (270x480), t = segundos desde o início da cena, D = duração."""
import math, random
from pixelkit import *

TECIDO, TECIDOE, TUBO, TUBOE = (236, 150, 166), (204, 104, 128), (255, 196, 206), (176, 70, 100)

def tubo(a, t):
    """'dentro da galinha': fundo rosado e o oviduto atravessando a tela"""
    d = a.d
    d.rectangle([0, 0, AW, AH], fill=TECIDO)
    rnd = random.Random(2); off = int(t * 6)
    for _ in range(70): d.point(((rnd.randint(0, AW) - off) % AW, rnd.randint(0, AH)), fill=TECIDOE)
    for x in range(AW + 1):
        yc = 92 + int(6 * math.sin((x + t * 10) / 14))
        d.line([x, yc - 26, x, yc + 26], fill=TUBO); d.point((x, yc - 27), fill=TUBOE); d.point((x, yc + 27), fill=TUBOE)
    for k in range(10):
        x = (k * 13 - int(t * 14)) % (AW + 10) - 5; yc = 92 + int(6 * math.sin((x + t * 10) / 14))
        d.line([x, yc - 24, x + 2, yc - 24], fill=(255, 220, 228)); d.line([x + 5, yc + 23, x + 7, yc + 23], fill=(240, 170, 186))

def centro_tubo(t, cx=54): return 92 + int(6 * math.sin((cx + t * 10) / 14))

# 1 ------------------------------------------------------------------
def arte_gancho(a, t, D):
    a.ceu(t=t); a.ninho(34, 124, 34)
    a.sprite(GALINHA_SENTADA, 20, 104 + (1 if int(t * 4) % 2 else 0))
    if t > 0.3: a.ovo(82, 110 - int(3 * abs(math.sin(t * 4))), 9, 12)
def textos_gancho(x, t, D):
    if t > D * 0.3: x.texto(196, 212, "?", x.tema.clara, 16)

# 2 ------------------------------------------------------------------
def arte_gema(a, t, D):
    tubo(a, t)
    for (px, py, r) in [(16, 62, 4), (24, 58, 3), (30, 64, 5), (20, 70, 3), (11, 68, 2), (27, 72, 2)]: a.gema(px, py, r)
    fx, fy = 46, 84
    a.d.polygon([(fx - 12, fy - 10), (fx + 12, fy - 10), (fx + 4, fy), (fx - 4, fy)], fill=TUBOE)
    a.d.polygon([(fx - 10, fy - 9), (fx + 10, fy - 9), (fx + 3, fy - 1), (fx - 3, fy - 1)], fill=TUBO)
    k = clamp01((t - 0.6) / 1.3)
    if k < 1:
        a.gema(int(lerp(34, fx, ease(k))), int(lerp(64, fy - 6, k * k)), 6)
    else:
        kk = clamp01((t - 1.9) / 1.4); gx = int(lerp(fx, 64, ease(kk))); yc = 92 + int(6 * math.sin((gx + t * 10) / 14))
        a.gema(gx, yc if kk > 0.3 else int(lerp(fy - 6, yc, kk / 0.3)), 6)
        if kk < 0.4: a.brilho(fx + 9, fy - 12); a.brilho(fx - 10, fy - 14)

# 3 ------------------------------------------------------------------
def arte_clara(a, t, D):
    tubo(a, t); cx, cy = 54, centro_tubo(t)
    n = int(1 + 4 * clamp01((t - 0.4) / (D * 0.6)))
    for i in range(n, 0, -1):
        r = 6 + i * 3
        a.d.ellipse([cx - r, cy - r + 1, cx + r, cy + r - 1], fill=mixc(BRANCO, (214, 222, 240), i / 5), outline=(176, 188, 214))
    a.gema(cx, cy, 6)

# 4 ------------------------------------------------------------------
def arte_membranas(a, t, D):
    tubo(a, t); cx, cy = 54, centro_tubo(t)
    k = ease((t - 0.3) / (D * 0.5)); rx, ry = 15, int(lerp(15, 20, k))
    a.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(240, 244, 250))
    for m in range(2):
        kk = clamp01((t - 0.5 - m * 0.6) / (D * 0.45))
        if kk > 0:
            o = 1 + m * 2
            a.d.arc([cx - rx - o, cy - ry - o, cx + rx + o, cy + ry + o], -90, -90 + 360 * kk, fill=a.tema.cor if m == 0 else a.tema.escura)
    a.gema(cx, cy + 1, 6)

# 5 ------------------------------------------------------------------
def arte_casca(a, t, D):
    tubo(a, t); cx, cy = 54, centro_tubo(t); rx, ry = 15, 20
    th = clamp01((t - 0.4) / (D * 0.75)); shell = mixc((232, 236, 246), (240, 222, 196), th)
    a.d.ellipse([cx - rx - 2, cy - ry - 2, cx + rx + 2, cy + ry + 2], fill=mixc((176, 188, 214), (150, 112, 74), th))
    a.d.ellipse([cx - rx - 1, cy - ry - 1, cx + rx + 1, cy + ry + 1], fill=shell)
    if th < 0.95:
        a.d.ellipse([cx - rx + 2, cy - ry + 2, cx + rx - 2, cy + ry - 2], fill=mixc((240, 244, 250), shell, th)); a.gema(cx, cy + 1, 6)
    else:
        a.px(cx - 8, cy - 10, BRANCO); a.px(cx - 8, cy - 9, BRANCO)
    rnd = random.Random(int(t * 10))
    for _ in range(8): a.px(cx + rnd.randint(-24, 24), cy - 30 + int((t * 30 + rnd.randint(0, 30)) % 30), BRANCO)
def textos_casca(x, t, D):
    hrs = int(20 * clamp01((t - 0.3) / (D * 0.75)))
    x.etiqueta(135, 160, f"{hrs:02d}/20 HORAS", "ouro")

# 6 ------------------------------------------------------------------
def arte_sai(a, t, D):
    a.ceu(t=t); a.ninho(40, 124, 36)
    k = clamp01((t - 0.6) / 0.8); lift = int(4 * math.sin(math.pi * min(1, k * 1.2))) if k < 1 else 0
    a.sprite(GALINHA_SENTADA, 26, 104 - lift)
    if k > 0.5:
        a.ovo(30, int(lerp(116, 120, ease((k - 0.5) * 2))), 4, 5)
        if k >= 1: a.brilho(22, 112); a.brilho(38, 110)

# 7 ------------------------------------------------------------------
def arte_calor(a, t, D):
    a.noite(t=t); a.ninho(44, 128, 40)
    k = clamp01((t - 0.3) / (D * 0.8)); cx, cy = 44, 110; d = a.d
    d.ellipse([cx - 13, cy - 17, cx + 13, cy + 17], fill=(255, 190, 110)); d.ellipse([cx - 12, cy - 16, cx + 12, cy + 16], fill=(255, 226, 170))
    d.ellipse([cx - 8, cy - 12, cx + 8, cy + 12], fill=(255, 206, 140))
    er = int(1 + 6 * k)
    for ang in range(0, 360, 60):
        ra = math.radians(ang + 10)
        d.line([cx, cy + 3, cx + int((er + 5) * math.cos(ra)), cy + 3 + int((er + 4) * math.sin(ra))], fill=(214, 100, 70))
    d.ellipse([cx - er, cy + 3 - er, cx + er, cy + 3 + er], fill=(150, 64, 36))
    for i in range(4):
        for j in range(4): a.px(30 + i * 9 + int(1.5 * math.sin(t * 3 + i + j)), 84 - j * 5 - int(t * 10 + i * 3) % 5, (255, 150, 80))
    tx, ty = 82, 64
    d.rectangle([tx - 1, ty - 1, tx + 4, ty + 46], fill=INK); d.rectangle([tx, ty, tx + 3, ty + 45], fill=BRANCO)
    d.ellipse([tx - 3, ty + 42, tx + 6, ty + 51], fill=INK); d.ellipse([tx - 2, ty + 43, tx + 5, ty + 50], fill=VERMELHO)
    d.rectangle([tx + 1, ty + 16, tx + 2, ty + 45], fill=VERMELHO)
def textos_calor(x, t, D):
    day = 1 + int(20 * clamp01((t - 0.3) / (D * 0.8)))
    x.etiqueta(96, 140, f"DIA {day:02d}/21", "marca"); x.texto(182, 146, "37–38°C", OURO)

# 8 ------------------------------------------------------------------
def arte_respira(a, t, D):
    a.listras((250, 236, 214), (246, 228, 202)); d = a.d
    cx, cy, rx, ry = 54, 96, 36, 46
    d.ellipse([cx - rx - 1, cy - ry - 1, cx + rx + 1, cy + ry + 1], fill=(150, 112, 74)); d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(240, 222, 196))
    d.ellipse([cx - rx + 3, cy - ry + 3, cx + rx - 3, cy + ry - 3], fill=(255, 246, 228))
    air = cy - ry + 18
    d.chord([cx - rx + 3, cy - ry + 3, cx + rx - 3, cy - ry + 36], 180, 360, fill=(206, 230, 250)); d.line([cx - 26, air, cx + 26, air], fill=(110, 150, 196))
    k = ease((t - 0.6) / 1.2)
    a.sprite(PINTINHO_PISCA if piscar(t) or k < 1 else PINTINHO, cx - 7, cy + 6 - int(12 * k))
    if k >= 1:
        for i in range(3): a.px(cx + 8 + i * 2, air - 2 - int((t * 10 + i * 4) % 12), (110, 150, 196))
        a.brilho(cx + 12, air - 4)
def textos_respira(x, t, D):
    x.texto(135, 152, "BOLSA DE AR", (40, 80, 130), 8, centro=True, contorno=BRANCO)

# 9 ------------------------------------------------------------------
def arte_nasceu(a, t, D):
    a.ceu(t=t); a.ninho(54, 126, 44); d = a.d
    cx, cy, rx, ry = 54, 106, 13, 17
    kc = clamp01((t - 0.3) / (D * 0.45)); ko = clamp01((t - D * 0.62) / 0.5)
    if ko <= 0:
        wob = (1 if int(t * 12) % 2 else -1) if 0.3 < t and int(t * 2) % 2 == 0 else 0
        a.ovo(cx + wob, cy, rx, ry)
        pts = [(cx - rx, cy - 2), (cx - rx + 4, cy + 1), (cx - rx + 7, cy - 3), (cx - rx + 11, cy), (cx - rx + 15, cy - 3), (cx - rx + 19, cy + 1), (cx - rx + 23, cy - 3), (cx + rx, cy - 1)]
        n = int(1 + (len(pts) - 1) * kc)
        if n >= 2: d.line([(px + wob, py) for px, py in pts[:n]], fill=INK)
    else:
        a.sprite(PINTINHO_PISCA if piscar(t, 1.8) else PINTINHO, cx - 7, cy - 10 - int(12 * ease(ko)))
        d.chord([cx - rx - 1, cy - ry - 1, cx + rx + 1, cy + ry + 1], 0, 180, fill=(150, 112, 74)); d.chord([cx - rx, cy - ry, cx + rx, cy + ry], 0, 180, fill=(240, 222, 196))
        for i in range(0, 2 * rx, 4): d.polygon([(cx - rx + i, cy), (cx - rx + i + 2, cy - 3), (cx - rx + i + 4, cy)], fill=(240, 222, 196))
        lx = cx + 10 + int(18 * ease(ko)); ly = cy - 18 - int(14 * math.sin(math.pi * ko))
        d.chord([lx - 9, ly - 6, lx + 9, ly + 12], 180, 360, fill=(150, 112, 74)); d.chord([lx - 8, ly - 5, lx + 8, ly + 11], 180, 360, fill=(240, 222, 196))
        if ko >= 1: a.confete(t)
def textos_nasceu(x, t, D):
    if t > D * 0.62 + 0.5: x.etiqueta(135, 150, "NASCEU!", "ouro")

# 10 -----------------------------------------------------------------
def arte_fim(a, t, D):
    a.ceu(t=t)
    a.sprite(PINTINHO_PISCA if piscar(t, 2.2) else PINTINHO, 14, 112 - int(3 * abs(math.sin(t * 5))))
    k = ease((t - 0.3) / 0.4); bx, by = 64, int(80 + (1 - k) * 10); d = a.d
    d.polygon([(bx, by), (bx + 18, by), (bx + 18, by + 26), (bx + 9, by + 19), (bx, by + 26)], fill=a.tema.escura)
    d.polygon([(bx + 1, by + 1), (bx + 17, by + 1), (bx + 17, by + 24), (bx + 9, by + 17), (bx + 1, by + 24)], fill=a.tema.cor)
    d.line([bx + 2, by + 2, bx + 16, by + 2], fill=a.tema.clara)
