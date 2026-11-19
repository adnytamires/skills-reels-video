"""Kit FLAT: personagens vetoriais de vídeo explicativo (traço da referência).

Regras do traço:
- sem contorno: as formas se separam pela cor;
- cor chapada + UMA sombra de borda dura num lado (rosto, pescoço, roupa);
- olhos: círculo branco grande, pupila preta, pontinho de brilho;
- sobrancelhas grossas em barra arredondada (fazem a expressão);
- nariz e boca de traço simples; orelhas em meia-lua; bochecha corada quando sorri;
- cabelo chapado (espetado, liso, cacheado...), óculos de armação grossa, boné com botão.
Use com a Cena de desenho.py: os personagens e objetos são desenhados direto nela.
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from desenho import Cena, CW, CH, SS, mistura, escurecer, suavizar, fonte, clamp01, lerp, ease, hex2rgb  # noqa

PELE = {"clara": (240, 205, 170), "media": (214, 166, 124), "morena": (172, 112, 72), "escura": (120, 76, 50)}
def _sombra_de(cor, k=0.86): return tuple(int(v*k) for v in cor)

class Folha:
    """camada local de um personagem: unidades = altura da cabeça, origem no centro da cabeça, y para baixo"""
    def __init__(s, c, x, y, u, larg=3.2, cima=1.2, baixo=3.0, espelho=False):
        s.c, s.x, s.y, s.u, s.esp = c, x, y, u, espelho
        s.ox, s.oy = larg/2, cima; s.w, s.h = larg, cima + baixo
        s.im = Image.new("RGBA", (int(s.w*u*SS), int(s.h*u*SS)), (0, 0, 0, 0))
    def M(s, pts): return [(((-px if s.esp else px) + s.ox)*s.u*SS, (py + s.oy)*s.u*SS) for px, py in pts]
    def mascara(s, desenhar):
        m = Image.new("L", s.im.size, 0); desenhar(ImageDraw.Draw(m)); return m
    def pinta(s, m, cor): s.im.paste(Image.new("RGBA", s.im.size, tuple(cor) + (255,)), (0, 0), m)
    # formas -> máscara
    def f_forma(s, pts, suave=True):
        P = s.M(suavizar(pts, 8) if suave else pts); return s.mascara(lambda d: d.polygon(P, fill=255))
    def f_elipse(s, cx, cy, rx, ry):
        (x0, y0), (x1, y1) = s.M([(cx - rx, cy - ry), (cx + rx, cy + ry)]); x0, x1 = min(x0, x1), max(x0, x1)
        return s.mascara(lambda d: d.ellipse([x0, y0, x1, y1], fill=255))
    def f_linha(s, pts, larg, suave=True):
        P = s.M(suavizar(pts, 6, fechada=False) if suave and len(pts) > 2 else pts); w = int(larg*s.u*SS)
        def d_(d):
            d.line(P, fill=255, width=w, joint="curve")
            for px, py in (P[0], P[-1]): d.ellipse([px - w/2, py - w/2, px + w/2, py + w/2], fill=255)
        return s.mascara(d_)
    # atalhos que pintam
    def forma(s, pts, cor, suave=True, sombra=None):
        m = s.f_forma(pts, suave); s.pinta(m, cor)
        if sombra is not None: s.pinta(_inter(m, sombra), _sombra_de(cor))
        return m
    def elipse(s, cx, cy, rx, ry, cor, sombra=None):
        m = s.f_elipse(cx, cy, rx, ry); s.pinta(m, cor)
        if sombra is not None: s.pinta(_inter(m, sombra), _sombra_de(cor))
        return m
    def linha(s, pts, larg, cor, suave=True): m = s.f_linha(pts, larg, suave); s.pinta(m, cor); return m
    def colar(s):
        ox, oy = int((s.x - s.ox*s.u)*SS), int((s.y - s.oy*s.u)*SS)
        s.c.alb.alpha_composite(s.im, (ox, oy)); s.c.d = ImageDraw.Draw(s.c.alb)
        buraco = Image.new("RGBA", s.im.size, (0, 0, 0, 0)); fundo = s.c.emis.crop((ox, oy, ox + s.im.width, oy + s.im.height))
        s.c.emis.paste(Image.composite(buraco, fundo, s.im.getchannel("A")), (ox, oy)); s.c.de = ImageDraw.Draw(s.c.emis)

def _inter(a, b): return Image.fromarray(np.minimum(np.asarray(a), np.asarray(b)))

def _lado_sombra(f, lado=1, corte=0.16):
    """máscara do lado da sombra (borda dura levemente curva)"""
    return f.f_forma([(corte, -2.0), (corte - 0.05, -0.3), (corte + 0.02, 0.2), (corte - 0.06, 0.7), (corte + 0.1, 1.4), (corte + 0.2, 4.0), (3.0, 4.0), (3.0, -2.0)], suave=True)

# ------------------------------------------------------------------ rosto
def _olho(f, x, y, r, olhar=(0.0, 0.0), fechado=False, pele=(0, 0, 0)):
    if fechado:   # olho fechado sorrindo: arco
        f.linha([(x - r*0.8, y + r*0.15), (x, y - r*0.45), (x + r*0.8, y + r*0.15)], r*0.32, (34, 26, 26)); return
    f.elipse(x, y, r, r*1.04, (252, 252, 250))
    px, py = x + olhar[0]*r*0.35, y + olhar[1]*r*0.3
    f.elipse(px, py, r*0.5, r*0.52, (26, 22, 24))
    f.elipse(px + r*0.2, py - r*0.22, r*0.16, r*0.16, (255, 255, 255))

def _sobrancelha(f, x, y, comp, esp, ang, cor):
    a = math.radians(ang); dx, dy = math.cos(a)*comp/2, math.sin(a)*comp/2
    f.linha([(x - dx, y - dy), (x + dx, y + dy)], esp, cor, suave=False)

EXPR = {   # (ângulo da sobrancelha interna, altura, boca)
    "neutro": (0, 0.0, "reta"), "feliz": (-6, -0.03, "sorriso"), "sorriso": (-4, -0.02, "sorriso"), "bravo": (16, 0.03, "reta"),
    "determinado": (11, 0.02, "reta"), "triste": (-14, -0.01, "triste"), "preocupado": (-12, -0.02, "reta"), "surpreso": (-4, -0.08, "o"),
    "rindo": (-8, -0.05, "aberta"), "pensativo": (6, 0.0, "lado")}

def cabeca(f, pele="clara", cabelo="espetado", cor_cabelo=(44, 40, 44), oculos=False, bone=None, cor_bone=(40, 40, 46), cor_botao=(240, 110, 30),
           expressao="neutro", olhar=(0.0, 0.0), barba=False, brinco=False, corado=None, lado=1):
    pele = PELE.get(pele, pele) if isinstance(pele, str) else pele
    sh = _lado_sombra(f, lado) if lado else None; ang, alt, boca = EXPR.get(expressao, EXPR["neutro"])
    if cabelo == "rabo":   # rabo de cavalo saindo atrás da cabeça
        f.forma([(0.3, -0.42), (0.62, -0.5), (0.82, -0.3), (0.8, 0.1), (0.66, 0.42), (0.6, 0.1), (0.5, -0.2)], escurecer(cor_cabelo, 0.88))
    if cabelo in ("longo", "chanel"):
        fim = 0.62 if cabelo == "chanel" else 1.35
        f.forma([(-0.52, -0.2), (-0.5, -0.5), (0, -0.62), (0.5, -0.5), (0.52, -0.2), (0.56, fim), (0.3, fim + 0.04), (-0.3, fim + 0.04), (-0.56, fim)], escurecer(cor_cabelo, 0.85))
    for sx in (-1, 1):   # orelhas
        f.elipse(sx*0.46, 0.04, 0.085, 0.11, pele, sombra=sh); f.elipse(sx*0.47, 0.05, 0.04, 0.06, _sombra_de(pele, 0.8))
        if brinco: f.elipse(sx*0.47, 0.16, 0.022, 0.022, (240, 210, 90))
    rosto = [(0, -0.5), (0.36, -0.45), (0.46, -0.2), (0.47, 0.08), (0.38, 0.34), (0.2, 0.47), (0, 0.5), (-0.2, 0.47), (-0.38, 0.34), (-0.47, 0.08), (-0.46, -0.2), (-0.36, -0.45)]
    mr = f.forma(rosto, pele, sombra=sh)
    if barba: f.pinta(_inter(mr, f.f_forma([(-0.5, 0.05), (-0.36, 0.42), (0, 0.56), (0.36, 0.42), (0.5, 0.05), (0.3, 0.26), (0.0, 0.33), (-0.3, 0.26)])), escurecer(cor_cabelo, 1.0))
    ey = -0.02 + alt*0.5; r = 0.105
    fechado = expressao in ("feliz", "rindo")
    for sx in (-1, 1): _olho(f, sx*0.2, ey, r, olhar, fechado)
    if oculos:
        for sx in (-1, 1):
            (x0, y0), (x1, y1) = f.M([(sx*0.2 - 0.17, ey - 0.13), (sx*0.2 + 0.17, ey + 0.13)]); x0, x1 = min(x0, x1), max(x0, x1)
            m = f.mascara(lambda d: d.rounded_rectangle([x0, y0, x1, y1], int(0.07*f.u*SS), outline=255, width=int(0.045*f.u*SS))); f.pinta(m, (24, 22, 24))
        f.linha([(-0.04, ey - 0.02), (0.04, ey - 0.02)], 0.04, (24, 22, 24), suave=False)
        for sx in (-1, 1): f.linha([(sx*0.37, ey - 0.05), (sx*0.46, ey - 0.08)], 0.035, (24, 22, 24), suave=False)
    by = ey - (0.2 if oculos else 0.17) + alt
    for sx in (-1, 1): _sobrancelha(f, sx*0.2, by, 0.24, 0.065, -sx*ang if not (expressao == "pensativo" and sx < 0) else 0, escurecer(cor_cabelo, 0.7) if cor_cabelo[0] > 90 else (28, 24, 26))
    f.linha([(0.01, 0.07), (0.05, 0.17), (0.0, 0.2)], 0.028, _sombra_de(pele, 0.72))          # nariz
    corado = corado if corado is not None else boca in ("sorriso", "aberta")
    if corado:
        for sx in (-1, 1): f.elipse(sx*0.28, 0.2, 0.07, 0.045, mistura(pele, (240, 120, 90), 0.35))
    bc = (74, 34, 30)
    if boca == "reta": f.linha([(-0.09, 0.31), (0.09, 0.31)], 0.035, bc, suave=False); f.linha([(-0.05, 0.345), (0.05, 0.345)], 0.02, _sombra_de(pele, 0.82), suave=False)
    elif boca == "sorriso": f.linha([(-0.16, 0.25), (-0.08, 0.32), (0.0, 0.34), (0.08, 0.32), (0.16, 0.25)], 0.04, bc)
    elif boca == "triste": f.linha([(-0.1, 0.34), (0.0, 0.3), (0.1, 0.34)], 0.035, bc)
    elif boca == "o": f.elipse(0, 0.32, 0.05, 0.065, bc)
    elif boca == "aberta":
        f.forma([(-0.16, 0.25), (0.16, 0.25), (0.1, 0.37), (0, 0.4), (-0.1, 0.37)], bc); f.forma([(-0.07, 0.35), (0.07, 0.35), (0.04, 0.39), (-0.04, 0.39)], (220, 100, 100))
    elif boca == "lado": f.linha([(-0.02, 0.31), (0.12, 0.29)], 0.035, bc, suave=False)
    _cabelo(f, cabelo, cor_cabelo, bone)
    if bone: _bone(f, cor_bone, cor_botao)
    return mr

def _cabelo(f, estilo, cor, bone):
    claro = mistura(cor, (255, 255, 255), 0.12)
    if estilo == "careca": return
    if bone:   # com boné só aparecem as costeletas
        for sx in (-1, 1): f.forma([(sx*0.46, -0.24), (sx*0.47, 0.0), (sx*0.42, 0.0), (sx*0.4, -0.22)], cor, suave=False)
        return
    if estilo in ("espetado", "baguncado"):
        bolhas = [(-0.44, -0.2, 0.13), (-0.4, -0.4, 0.15), (-0.24, -0.54, 0.16), (-0.04, -0.6, 0.17), (0.16, -0.57, 0.16), (0.33, -0.47, 0.15), (0.44, -0.28, 0.13)]
        for bx, by, r in bolhas: f.elipse(bx, by, r, r*0.92, cor)
        f.forma([(-0.5, -0.02), (-0.52, -0.3), (-0.3, -0.5), (0.0, -0.56), (0.3, -0.5), (0.52, -0.3), (0.5, -0.04), (0.42, -0.2), (0.24, -0.28), (0.1, -0.24), (-0.06, -0.3), (-0.2, -0.24), (-0.36, -0.28), (-0.44, -0.14)], cor)
        if estilo == "espetado":   # topete: duas pontas pequenas para cima
            f.forma([(-0.1, -0.62), (-0.04, -0.82), (0.04, -0.64), (0.12, -0.78), (0.16, -0.6)], cor, suave=False)
        for bx, by in ((-0.22, -0.56), (0.08, -0.62), (0.3, -0.5)): f.elipse(bx, by, 0.06, 0.03, claro)
    elif estilo in ("curto", "liso"):
        f.forma([(-0.5, -0.02), (-0.5, -0.36), (-0.3, -0.58), (0.05, -0.64), (0.36, -0.56), (0.51, -0.34), (0.5, -0.04), (0.42, -0.24), (0.2, -0.32), (-0.1, -0.3), (-0.36, -0.24), (-0.44, -0.12)], cor)
        f.forma([(-0.16, -0.56), (0.12, -0.6), (0.18, -0.52), (-0.1, -0.48)], claro)
    elif estilo == "cacheado":
        for i in range(13):
            a = math.pi*(1.0 + i/12); f.elipse(0.5*math.cos(a), -0.2 + 0.46*math.sin(a), 0.13, 0.13, cor)
        f.forma([(-0.48, -0.1), (-0.3, -0.4), (0.3, -0.4), (0.48, -0.1), (0.3, -0.25), (-0.3, -0.25)], cor)
    elif estilo == "rabo":   # cabelo preso: liso por cima, sem mechas descendo
        f.forma([(-0.5, -0.04), (-0.5, -0.36), (-0.3, -0.58), (0.05, -0.64), (0.36, -0.56), (0.51, -0.34), (0.5, -0.06), (0.44, -0.24), (0.22, -0.34), (-0.05, -0.3), (-0.3, -0.36), (-0.44, -0.16)], cor)
        f.forma([(-0.18, -0.56), (0.1, -0.6), (0.16, -0.52), (-0.12, -0.48)], claro)
        f.elipse(0.42, -0.42, 0.07, 0.06, (240, 110, 30) if False else escurecer(cor, 0.7))
    elif estilo in ("longo", "chanel"):
        f.forma([(-0.54, 0.25), (-0.52, -0.32), (-0.3, -0.58), (0.05, -0.64), (0.36, -0.56), (0.52, -0.32), (0.54, 0.25), (0.44, 0.1), (0.42, -0.2), (0.2, -0.3), (-0.05, -0.36), (-0.3, -0.26), (-0.43, -0.1), (-0.44, 0.12)], cor)
        f.forma([(-0.2, -0.56), (0.1, -0.6), (0.16, -0.5), (-0.14, -0.46)], claro)
        if estilo == "rabo": f.elipse(0.0, -0.66, 0.14, 0.1, cor)
    elif estilo == "coque":
        f.elipse(0.0, -0.7, 0.17, 0.14, cor)
        f.forma([(-0.5, -0.02), (-0.5, -0.36), (-0.3, -0.58), (0.05, -0.62), (0.36, -0.56), (0.51, -0.34), (0.5, -0.04), (0.38, -0.3), (0.0, -0.38), (-0.4, -0.28)], cor)

def _bone(f, cor, botao):
    claro = mistura(cor, (255, 255, 255), 0.1)
    f.forma([(-0.5, -0.16), (-0.52, -0.42), (-0.36, -0.64), (0.0, -0.72), (0.36, -0.64), (0.52, -0.42), (0.5, -0.16)], cor)
    for sx in (-1, 1): f.linha([(sx*0.04, -0.7), (sx*0.2, -0.22)], 0.016, escurecer(cor, 0.78))
    f.forma([(-0.24, -0.62), (0.06, -0.68), (0.16, -0.6), (-0.14, -0.54)], claro)
    f.forma([(-0.5, -0.26), (-0.2, -0.32), (0.2, -0.32), (0.5, -0.26), (0.48, -0.16), (0.2, -0.2), (-0.2, -0.2), (-0.48, -0.16)], escurecer(cor, 0.82))   # aba curva
    f.elipse(0.0, -0.73, 0.05, 0.035, botao)

# ------------------------------------------------------------------ corpo (busto)
def _tronco(f, roupa, cor, pele, lado, cor2=None):
    sh = _lado_sombra(f, lado, 0.22) if lado else None
    f.forma([(-0.12, 0.3), (0.12, 0.3), (0.13, 0.72), (-0.13, 0.72)], _sombra_de(pele, 0.88), suave=False)          # pescoço
    f.pinta(_inter(f.f_forma([(-0.12, 0.3), (0.12, 0.3), (0.13, 0.72), (-0.13, 0.72)], False), f.f_forma([(-0.2, 0.3), (0.2, 0.3), (0.2, 0.46), (-0.2, 0.42)])), _sombra_de(pele, 0.72))
    corpo = [(-0.36, 0.64), (0.36, 0.64), (0.58, 0.76), (0.72, 0.98), (0.8, 2.6), (-0.8, 2.6), (-0.72, 0.98), (-0.58, 0.76)]
    f.forma(corpo, cor, sombra=sh)
    if roupa == "moletom":
        capuz = escurecer(cor, 0.88)
        f.forma([(-0.38, 0.56), (-0.18, 0.66), (0.18, 0.66), (0.38, 0.56), (0.46, 0.72), (0.28, 0.86), (0.0, 0.9), (-0.28, 0.86), (-0.46, 0.72)], capuz)
        f.forma([(-0.2, 0.66), (0.2, 0.66), (0.14, 0.76), (-0.14, 0.76)], _sombra_de(cor, 0.7))
        for sx in (-1, 1): f.linha([(sx*0.1, 0.84), (sx*0.11, 1.12)], 0.028, (236, 236, 240), suave=False); f.elipse(sx*0.11, 1.14, 0.022, 0.03, (210, 210, 216))
    elif roupa == "camiseta":
        f.forma([(-0.22, 0.6), (0.22, 0.6), (0.26, 0.66), (0.0, 0.76), (-0.26, 0.66)], escurecer(cor, 0.82))
        f.forma([(-0.17, 0.6), (0.17, 0.6), (0.0, 0.7)], _sombra_de(pele, 0.88))
    elif roupa == "camisa":
        for sx in (-1, 1): f.forma([(0, 0.7), (sx*0.2, 0.6), (sx*0.26, 0.82)], mistura(cor, (255, 255, 255), 0.25), suave=False)
        for i in range(4): f.elipse(0.0, 0.92 + i*0.22, 0.02, 0.02, escurecer(cor, 0.7))
    elif roupa == "blazer":
        f.forma([(-0.16, 0.62), (0.16, 0.62), (0.0, 1.2)], cor2 or (236, 236, 240), suave=False)
        for sx in (-1, 1): f.forma([(sx*0.16, 0.62), (sx*0.34, 0.66), (sx*0.12, 1.2), (sx*0.02, 1.2)], escurecer(cor, 0.85), suave=False)

def busto(c, x, y, tam=300, roupa="moletom", cor_roupa=(92, 106, 128), espelho=False, lado=1, **rosto):
    """personagem da cintura para cima (como atrás de um notebook). (x, y) = centro da cabeça; tam = altura da cabeça.
    roupa: "moletom", "camiseta", "camisa", "blazer". Opções de rosto: pele, cabelo, cor_cabelo, oculos, bone, cor_bone,
    cor_botao, expressao, olhar=(x, y), barba, brinco, corado."""
    f = Folha(c, x, y, tam, 2.4, 1.0, 2.7, espelho)
    pele = rosto.get("pele", "clara"); pele = PELE.get(pele, pele) if isinstance(pele, str) else pele
    _tronco(f, roupa, cor_roupa, pele, lado)
    cabeca(f, lado=lado, **rosto)
    f.colar(); return f

# ------------------------------------------------------------------ objetos e fundos
def notebook_costas(c, x, y, w=620, cor=(46, 46, 50), adesivo=(240, 110, 30), seed=1):
    """notebook visto por trás (tampa), com adesivo redondo de raio e um adesivo retangular. (x, y) = topo central"""
    h = w*0.62; rnd = random.Random(seed)
    c.ret(x - w/2, y, x + w/2, y + h, cor, contorno=False, raio=w*0.03)
    c.ret(x - w/2, y, x + w/2, y + h*0.035, mistura(cor, (255, 255, 255), 0.12), contorno=False, raio=w*0.02)
    c.elipse(x, y + h*0.42, w*0.035, w*0.035, mistura(cor, (255, 255, 255), 0.06), contorno=False)
    for _ in range(4):
        a, b = rnd.uniform(-0.4, 0.4)*w, rnd.uniform(0.15, 0.8)*h; c.traco([(x + a, y + b), (x + a + w*0.08, y + b - w*0.02)], mistura(cor, (255, 255, 255), 0.08), 2)
    ax, ay, r = x + w*0.3, y + h*0.22, w*0.085
    c.elipse(ax, ay, r, r, (250, 250, 248), contorno=False); c.elipse(ax, ay, r*0.86, r*0.86, adesivo, contorno=False)
    c.forma([(ax + r*0.12, ay - r*0.6), (ax - r*0.32, ay + r*0.08), (ax - r*0.02, ay + r*0.08), (ax - r*0.14, ay + r*0.62), (ax + r*0.32, ay - r*0.1), (ax + r*0.02, ay - r*0.1)], (255, 255, 255), contorno=False)
    sx, sy = x - w*0.3, y + h*0.62
    c.forma([(sx - w*0.08, sy), (sx + w*0.08, sy - w*0.025), (sx + w*0.09, sy + w*0.025), (sx - w*0.07, sy + w*0.05)], (176, 172, 164), contorno=False)

def fundo_textura(c, cor_cima, cor_baixo, linhas=True, ruido=0.05, seed=2):
    """fundo chapado em degradê com granulado e linhas finas horizontais (como tela de vídeo)"""
    for i in range(60): c.ret(-10, CH*i/60, CW + 10, CH*(i + 1)/60 + 2, mistura(cor_cima, cor_baixo, i/59), contorno=False)
    a = np.asarray(c.alb, np.float32); rng = np.random.default_rng(seed)
    a[..., :3] *= (1 + rng.normal(0, ruido, a.shape[:2]).astype(np.float32))[..., None]
    if linhas: a[::8*SS, :, :3] *= 0.9
    c.alb = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA"); c.d = ImageDraw.Draw(c.alb)

def brilho(c, x, y, raio, cor, forca=0.6):
    """brilho colorido (luz quente atrás do personagem)"""
    c.elipse(x, y, raio*0.2, raio*0.2, cor, contorno=False, emissivo=True)
    c.luz_ponto(x, y, raio=raio, cor=cor, forca=forca)

def janela_noite(c, x, y, w, h, cor=(40, 50, 70)):
    """janela escura com lua (cantinho de cena)"""
    c.ret(x, y, x + w, y + h, escurecer(cor, 0.85), contorno=False)
    for i in (1, 2):
        c.ret(x + w*i/3 - 3, y, x + w*i/3 + 3, y + h, mistura(cor, (255, 255, 255), 0.08), contorno=False)
    c.ret(x, y + h/2 - 3, x + w, y + h/2 + 3, mistura(cor, (255, 255, 255), 0.08), contorno=False)
    mx, my, r = x + w*0.72, y + h*0.25, w*0.07
    c.elipse(mx, my, r, r, (236, 238, 230), contorno=False, emissivo=True); c.elipse(mx + r*0.45, my - r*0.2, r*0.85, r*0.85, escurecer(cor, 0.85), contorno=False)


# ------------------------------------------------------------------ animação 2D (use dentro de animar_<cena>)
def texto_grande(im, txt, x, y, tam=220, cor=(246, 244, 240), contorno=False, brilho=False, alfa=1.0, peso="titulo"):
    """título grande de vídeo explicativo (coordenadas da tela de desenho 1440 x 2560).
    contorno=True: só a borda (como "DIA 1"); brilho=True: brilho em volta (como o "0" laranja)."""
    if alfa <= 0: return
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = fonte(peso, int(tam))
    if contorno: d.text((x, y), txt, font=f, fill=(0, 0, 0, 0), stroke_width=max(2, int(tam*0.018)), stroke_fill=tuple(cor) + (int(255*alfa),), anchor="mm")
    else: d.text((x, y), txt, font=f, fill=tuple(cor) + (int(255*alfa),), anchor="mm")
    if brilho: im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(tam*0.12)))
    im.alpha_composite(lay)

def faiscas(im, t, n=30, area=(0, 0, CW, CH), cor=(255, 140, 50), seed=1):
    """faíscas/brasas subindo devagar (luz quente)"""
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); rnd = random.Random(seed); x0, y0, x1, y1 = area
    for i in range(n):
        x = x0 + (rnd.uniform(0, 1)*(x1 - x0) + 25*math.sin(t*0.8 + i)) % (x1 - x0); y = y1 - ((rnd.uniform(0, 1)*(y1 - y0) + t*rnd.uniform(40, 110)) % (y1 - y0))
        r = rnd.uniform(3, 9); a = int(140 + 100*math.sin(t*3 + i))
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(cor) + (max(0, a),))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5)))

def linha_brilho(im, x, t, cor=(255, 140, 50), larg=8):
    """linha vertical brilhante (divide a tela em duas), pulsando"""
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); k = 0.75 + 0.25*math.sin(t*4)
    d.rectangle([x - larg*3, 0, x + larg*3, CH], fill=tuple(cor) + (int(90*k),)); im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(26)))
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).rectangle([x - larg/2, 0, x + larg/2, CH], fill=mistura(cor, (255, 255, 255), 0.4) + (255,)); im.alpha_composite(lay)

def apagar_lado(im, x0, x1, forca=1.0):
    """tira a cor de um lado da tela (personagem que "ficou para trás")"""
    if forca <= 0: return
    reg = im.crop((int(x0), 0, int(x1), im.height)); a = np.asarray(reg, np.float32); g = a[..., :3].mean(2, keepdims=True)*0.7
    a[..., :3] = a[..., :3]*(1 - forca) + g*forca; im.paste(Image.fromarray(a.astype(np.uint8), "RGBA"), (int(x0), 0))

def mesa_frente(c, y, cor=(26, 28, 36)):
    """faixa de mesa na frente (embaixo da tela): é onde fica a legenda nos vídeos explicativos"""
    c.ret(-10, y, CW + 10, CH + 10, cor, contorno=False); c.ret(-10, y, CW + 10, y + 10, mistura(cor, (255, 255, 255), 0.1), contorno=False)

def camada(im, bbox, desenhar, escala=2):
    """desenha formas animadas com borda suave numa região da tela: desenhar(d, T), em que T(x, y) converte
    coordenadas da tela de desenho para a camada (use T em todos os pontos)"""
    x0, y0, x1, y1 = [int(v) for v in bbox]; x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(im.width, x1), min(im.height, y1)
    if x1 <= x0 or y1 <= y0: return
    lay = Image.new("RGBA", ((x1 - x0)*escala, (y1 - y0)*escala), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    T = lambda x, y: ((x - x0)*escala, (y - y0)*escala)
    desenhar(d, T, escala); im.alpha_composite(lay.resize((x1 - x0, y1 - y0), Image.LANCZOS), (x0, y0))

def sol(im, x, y, r, t, cor=(255, 196, 60)):
    """sol chapado com raios girando devagar"""
    def des(d, T, k):
        for i in range(12):
            a = t*0.4 + i*math.pi/6; p1 = T(x + math.cos(a)*r*1.25, y + math.sin(a)*r*1.25); p2 = T(x + math.cos(a)*r*1.6, y + math.sin(a)*r*1.6)
            d.line([p1, p2], fill=cor, width=int(r*0.12*k))
        cx, cy = T(x, y); d.ellipse([cx - r*k, cy - r*k, cx + r*k, cy + r*k], fill=cor)
        d.ellipse([cx - r*0.7*k, cy - r*0.75*k, cx + r*0.2*k, cy - r*0.05*k], fill=mistura(cor, (255, 255, 255), 0.35))
    camada(im, (x - r*1.8, y - r*1.8, x + r*1.8, y + r*1.8), des)

def nuvem(c_ou_im, x, y, s=1.0, cor=(255, 255, 255), sombra=(214, 228, 244), em_cena=True):
    """nuvem chapada (círculos) com a base levemente sombreada"""
    bolas = [(-0.55, 0.1, 0.32), (-0.2, -0.18, 0.42), (0.25, -0.1, 0.38), (0.6, 0.12, 0.28)]
    if em_cena:
        c = c_ou_im
        for bx, by, r in bolas: c.elipse(x + bx*200*s, y + by*200*s + 18*s, r*200*s, r*200*s, sombra, contorno=False)
        c.ret(x - 170*s, y + 40*s, x + 170*s, y + 82*s, sombra, contorno=False, raio=30*s)
        for bx, by, r in bolas: c.elipse(x + bx*200*s, y + by*200*s, r*200*s, r*200*s, cor, contorno=False)
        c.ret(x - 170*s, y + 20*s, x + 170*s, y + 64*s, cor, contorno=False, raio=30*s)
    else:
        im = c_ou_im
        def des(d, T, k):
            for (bx, by, r), cc in [(b_, sombra) for b_ in bolas] + [(b_, cor) for b_ in bolas]:
                cx, cy = T(x + bx*200*s, y + by*200*s + (18*s if cc == sombra else 0)); rr = r*200*s*k
                d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=cc)
        camada(im, (x - 260*s, y - 200*s, x + 260*s, y + 160*s), des)

def balao_pensamento(c, x, y, w, h, cor=(255, 255, 255), borda=(214, 224, 236)):
    """balão de pensamento (nuvem) com bolinhas descendo até a cabeça em (x, y + h/2 + ...)"""
    c.ret(x - w/2 - 8, y - h/2 - 8, x + w/2 + 8, y + h/2 + 8, borda, contorno=False, raio=min(w, h)*0.42)
    c.ret(x - w/2, y - h/2, x + w/2, y + h/2, cor, contorno=False, raio=min(w, h)*0.4)
    for i, r in enumerate((34, 24, 15)): c.elipse(x - w*0.18 - i*40, y + h/2 + 50 + i*58, r + 6, r + 6, borda, contorno=False); c.elipse(x - w*0.18 - i*40, y + h/2 + 50 + i*58, r, r, cor, contorno=False)
