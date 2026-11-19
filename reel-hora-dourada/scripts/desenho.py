"""Base de desenho: a Cena (tela de desenho, luzes e brilho), cenários e objetos simples.
Os personagens e os elementos do traço flat ficam em flat.py.

Como funciona:
  1. Crie c = Cena(...). Tudo é desenhado em CORES CHAPADAS (sem luz) na tela de desenho,
     em unidades de tela: CW x CH = 1440 x 2560 (1,33x o vídeo, para a câmera ter espaço).
  2. Acrescente luzes com c.luz_ponto(...), c.luz_area(...). Velas, telas e janelas já criam a
     luz delas.
  3. O motor (reel.py) chama c.iluminar(): luz ambiente fria multiplicada pelas cores +
     luzes quentes somadas. As luzes com tremer=True oscilam a cada desenho.
Coordenadas: x para a direita, y para baixo, em unidades de tela (0..1440, 0..2560).
"""
import math, os, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920          # vídeo final
CW, CH = 1440, 2560        # tela de desenho
SS = 2                     # desenhado em 2x e reduzido (bordas suaves)
LINHA = (46, 34, 34)
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")

def clamp01(x): return max(0.0, min(1.0, float(x)))
def lerp(a, b, t): return a + (b - a)*t
def ease(x): x = clamp01(x); return 0.5 - 0.5*math.cos(math.pi*x)
def hex2rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def mistura(a, b, t): return tuple(int(lerp(x, y, t)) for x, y in zip(a, b))
def escurecer(c, k): return tuple(int(v*k) for v in c)

_f = {}
def fonte(tipo, n):
    arq = {"mao": "Caveat.ttf", "mao2": "PatrickHand-Regular.ttf", "legenda": "Inter-ExtraBold.ttf", "serif": "Fraunces-Bold.ttf",
           "titulo": "Montserrat.ttf", "titulo_fino": "Montserrat.ttf"}[tipo]
    if (tipo, n) not in _f:
        f = ImageFont.truetype(os.path.join(FONTS, arq), n)
        peso = {"mao": 600, "titulo": 900, "titulo_fino": 300}.get(tipo)
        if peso:
            try: f.set_variation_by_axes([peso])
            except Exception: pass
        _f[(tipo, n)] = f
    return _f[(tipo, n)]

def suavizar(pts, n=8, fechada=True):
    """curva Catmull-Rom pelos pontos de controle (deixa as formas arredondadas, como desenho à mão)"""
    P = list(pts); m = len(P); out = []
    rng = range(m) if fechada else range(m - 1)
    for i in rng:
        p0, p1, p2, p3 = P[(i - 1) % m] if (fechada or i > 0) else P[0], P[i], P[(i + 1) % m], P[(i + 2) % m] if (fechada or i + 2 < m) else P[-1]
        for k in range(n):
            t = k/n; t2, t3 = t*t, t*t*t
            out.append(tuple(0.5*((2*p1[j]) + (-p0[j] + p2[j])*t + (2*p0[j] - 5*p1[j] + 4*p2[j] - p3[j])*t2 + (-p0[j] + 3*p1[j] - 3*p2[j] + p3[j])*t3) for j in (0, 1)))
    if not fechada: out.append(P[-1])
    return out

# ------------------------------------------------------------------ a cena
# clima da cena: luz geral, sol (sombra projetada: deslocamento x e y por unidade de altura) e cor das sombras
CLIMAS = {
    "dia":      dict(ambiente=(1.0, 1.0, 1.0), sol=(0.55, 0.22), mult=(0.66, 0.69, 0.84)),
    "tarde":    dict(ambiente=(1.02, 0.92, 0.78), sol=(-0.95, 0.2), mult=(0.58, 0.55, 0.72)),
    "nublado":  dict(ambiente=(0.88, 0.9, 0.94), sol=None, mult=(0.75, 0.77, 0.85)),
    "interior": dict(ambiente=(0.94, 0.91, 0.86), sol=None, mult=(0.72, 0.72, 0.8)),
    "noite":    dict(ambiente=(0.26, 0.29, 0.38), sol=None, mult=(0.6, 0.62, 0.75)),
}

class Cena:
    def __init__(s, fundo=(200, 200, 204), ambiente=None, clima="dia", sol=None):
        """clima: "dia", "tarde" (pôr do sol dourado, sombras longas), "nublado", "interior" ou "noite".
        ambiente (opcional) troca a luz geral (r, g, b) de 0 a 1; sol (opcional) troca a direção das sombras no chão."""
        cl = CLIMAS[clima]
        s.alb = Image.new("RGBA", (CW*SS, CH*SS), tuple(fundo) + (255,)); s.d = ImageDraw.Draw(s.alb)
        s.emis = Image.new("RGBA", (CW*SS, CH*SS), (0, 0, 0, 0)); s.de = ImageDraw.Draw(s.emis)
        s.luzes, s.chamas, s.dados, s.clima = [], [], {}, clima
        s.ambiente = np.array(ambiente or cl["ambiente"], np.float32)
        s.dados["_sol"] = sol if sol is not None else cl["sol"]; s.dados["_mult_sombra"] = cl["mult"]

    # --- pincéis (coordenadas de tela) ---
    def forma(s, pts, cor, contorno=True, larg=2.2, suave=False, emissivo=False):
        if suave: pts = suavizar(pts)
        d = s.de if emissivo else s.d; P = [(x*SS, y*SS) for x, y in pts]
        if not emissivo: s.de.polygon(P, fill=(0, 0, 0, 0))          # o que fica na frente tapa o brilho de trás
        d.polygon(P, fill=tuple(cor), outline=LINHA if contorno else None, width=int(larg*SS) if contorno else 0)
    def elipse(s, cx, cy, rx, ry, cor, contorno=True, larg=2.2, emissivo=False):
        d = s.de if emissivo else s.d; B = [(cx - rx)*SS, (cy - ry)*SS, (cx + rx)*SS, (cy + ry)*SS]
        if not emissivo: s.de.ellipse(B, fill=(0, 0, 0, 0))
        d.ellipse(B, fill=tuple(cor), outline=LINHA if contorno else None, width=int(larg*SS) if contorno else 0)
    def ret(s, x0, y0, x1, y1, cor, contorno=True, larg=2.2, raio=0, emissivo=False):
        d = s.de if emissivo else s.d; B = [x0*SS, y0*SS, x1*SS, y1*SS]
        if not emissivo: s.de.rounded_rectangle(B, raio*SS, fill=(0, 0, 0, 0))
        d.rounded_rectangle(B, raio*SS, fill=tuple(cor), outline=LINHA if contorno else None, width=int(larg*SS) if contorno else 0)
    def traco(s, pts, cor=LINHA, larg=2.2, suave=False, emissivo=False):
        if suave: pts = suavizar(pts, fechada=False)
        (s.de if emissivo else s.d).line([(x*SS, y*SS) for x, y in pts], fill=tuple(cor), width=max(1, int(larg*SS)), joint="curve")
    def texto(s, x, y, txt, tam=60, cor=(40, 40, 60), tipo="mao", ancora="la", emissivo=False):
        (s.de if emissivo else s.d).text((x*SS, y*SS), txt, font=fonte(tipo, int(tam*SS)), fill=tuple(cor), anchor=ancora)
    def sombra(s, cx, cy, rx, ry, forca=0.45):
        """sombra de contato no chão (escurece o que já foi desenhado)"""
        m = Image.new("L", s.alb.size, 0); ImageDraw.Draw(m).ellipse([(cx - rx)*SS, (cy - ry)*SS, (cx + rx)*SS, (cy + ry)*SS], fill=int(255*forca))
        m = m.filter(ImageFilter.GaussianBlur(ry*SS*0.5)); escuro = Image.new("RGBA", s.alb.size, (10, 10, 16, 255))
        s.alb = Image.composite(escuro, s.alb, m); s.d = ImageDraw.Draw(s.alb)

    # --- luzes ---
    def luz_ponto(s, x, y, raio=260, cor=(255, 170, 90), forca=1.6, tremer=False, achatar=1.0):
        """luz quente que cai com a distância. achatar < 1 espalha mais na horizontal (luz no chão)."""
        s.luzes.append(dict(tipo="ponto", x=x, y=y, raio=raio, cor=np.array(cor, np.float32)/255, forca=forca, tremer=tremer, achatar=achatar))
    def luz_area(s, x0, y0, x1, y1, raio=300, cor=(200, 220, 255), forca=0.8):
        """luz suave de uma área (lâmpada de teto, janela, tela grande)"""
        s.luzes.append(dict(tipo="area", ret=(x0, y0, x1, y1), raio=raio, cor=np.array(cor, np.float32)/255, forca=forca, tremer=False))

    # --- render (o motor chama) ---
    def iluminar(s):
        """devolve (base, partes_que_tremem, emissivo): arrays float32 CH x CW x 3"""
        alb = np.asarray(s.alb.convert("RGB").resize((CW, CH), Image.LANCZOS), np.float32)/255
        yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float32)
        L = np.broadcast_to(s.ambiente, alb.shape).copy(); tremem = []; s.claro = float(s.ambiente.mean())
        fator = 1.0 if s.claro < 0.6 else 0.18     # cena clara: luzes pontuais só realçam
        for l in s.luzes:
            if l["tipo"] == "ponto":
                d2 = ((xx - l["x"])*l["achatar"])**2 + (yy - l["y"])**2
                I = l["forca"]/(1 + d2/(l["raio"]**2))
            else:
                x0, y0, x1, y1 = l["ret"]; dx = np.maximum(np.maximum(x0 - xx, 0), xx - x1); dy = np.maximum(np.maximum(y0 - yy, 0), yy - y1)
                I = l["forca"]*np.exp(-(dx**2 + dy**2)/(l["raio"]**2))
            contrib = I[..., None]*l["cor"]*fator
            if l["tremer"]: tremem.append(alb*contrib)
            else: L += contrib
        e = s.emis.resize((CW, CH), Image.LANCZOS); ea = np.asarray(e, np.float32)/255
        emis = ea[..., :3]*ea[..., 3:4]
        brilho = np.asarray(Image.fromarray((np.clip(emis, 0, 1)*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(28)), np.float32)/255
        base = alb*L*(1 - ea[..., 3:4]) + emis + brilho*(0.55 if s.claro < 0.6 else 0.08)
        return base, tremem, s.chamas

# ------------------------------------------------------------------ cenário
def piso(c, y, cor=(58, 62, 72), polido=True):
    """chão do y até embaixo; polido=True faz o reflexo das luzes no chão"""
    c.ret(-10, y, CW + 10, CH + 10, cor, contorno=False); c.dados["piso"] = (y, polido)
def parede(c, y0, y1, cor=(64, 70, 82), rodape=True, paineis=0):
    c.ret(-10, y0, CW + 10, y1, cor, contorno=False)
    if rodape: c.ret(-10, y1 - 26, CW + 10, y1, escurecer(cor, 0.75), contorno=False); c.traco([(-10, y1), (CW + 10, y1)], escurecer(cor, 0.45), 3)
    for i in range(1, paineis + 1): c.traco([(CW*i/(paineis + 1), y0), (CW*i/(paineis + 1), y1 - 26)], escurecer(cor, 0.82), 3)
def canto(c, x, y_teto, y_chao, cor_esq=(60, 66, 78), cor_dir=(70, 76, 88)):
    """duas paredes se encontrando num canto (dá profundidade)"""
    c.forma([(-10, y_teto - 200), (x, y_teto), (x, y_chao), (-10, y_chao + 260)], cor_esq, contorno=False)
    c.forma([(x, y_teto), (CW + 10, y_teto - 120), (CW + 10, y_chao + 160), (x, y_chao)], cor_dir, contorno=False)
    c.traco([(x, y_teto), (x, y_chao)], escurecer(cor_esq, 0.6), 3)
def lampada_teto(c, x, y, larg=420, acesa=True, forca=0.7):
    c.ret(x - larg/2 - 14, y - 10, x + larg/2 + 14, y + 26, (70, 72, 80), larg=1.6)
    if acesa:
        c.ret(x - larg/2, y - 2, x + larg/2, y + 16, (235, 242, 255), contorno=False, emissivo=True); c.luz_area(x - larg/2, y, x + larg/2, y + 20, 520, (190, 210, 255), forca)
def janela(c, x, y, w, h, noite=True, lua=True, forca=0.5):
    c.ret(x - 12, y - 12, x + w + 12, y + h + 12, (54, 50, 56), larg=2)
    cor = (40, 58, 96) if noite else (190, 214, 236)
    c.ret(x, y, x + w, y + h, cor, contorno=False, emissivo=True)
    if noite and lua: c.elipse(x + w*0.7, y + h*0.28, w*0.09, w*0.09, (226, 232, 250), contorno=False, emissivo=True)
    c.ret(x + w/2 - 5, y, x + w/2 + 5, y + h, (54, 50, 56), contorno=False); c.ret(x, y + h/2 - 5, x + w, y + h/2 + 5, (54, 50, 56), contorno=False)
    c.luz_area(x, y, x + w, y + h, 420, (130, 160, 230) if noite else (230, 236, 255), forca)
def porta_dupla(c, x, y, w=420, h=720, cor=(40, 42, 48), corrente=True, mao_no_vidro=False):
    """porta de duas folhas com barra antipânico; corrente=True põe corrente e cadeado"""
    c.ret(x - 16, y - 16, x + w + 16, y + h, escurecer(cor, 0.7), larg=2)
    for k in range(2):
        x0 = x + k*w/2; c.ret(x0 + 4, y, x0 + w/2 - 4, y + h, cor, larg=2)
        c.ret(x0 + w*0.12, y + h*0.1, x0 + w*0.38, y + h*0.38, (30, 36, 44), larg=2); c.ret(x0 + w*0.12, y + h*0.1, x0 + w*0.38, y + h*0.38, (60, 70, 84), contorno=False, emissivo=False)
    c.ret(x + w*0.06, y + h*0.52, x + w*0.94, y + h*0.56, (88, 90, 98), larg=2)
    if corrente:
        cx = x + w/2
        for i in range(-6, 7):
            a = i*0.42; px = cx + i*22; py = y + h*0.545 + 18*math.cos(i/6*math.pi/2)
            c.elipse(px, py, 14 if i % 2 else 9, 9 if i % 2 else 14, (96, 98, 104), larg=1.6)
        c.ret(cx - 26, y + h*0.6, cx + 26, y + h*0.6 + 52, (110, 104, 92), raio=6); c.traco([(cx - 14, y + h*0.6), (cx - 14, y + h*0.57), (cx + 14, y + h*0.57), (cx + 14, y + h*0.6)], (110, 104, 92), 5)
    if mao_no_vidro:
        hx, hy = x + w*0.25, y + h*0.24
        c.elipse(hx, hy + 18, 26, 30, (150, 150, 150), contorno=False)
        for i, (dx, comp) in enumerate([(-24, 40), (-9, 52), (6, 54), (20, 46), (34, 28)]):
            c.ret(hx + dx - 6, hy + 10 - comp, hx + dx + 6, hy + 14, (150, 150, 150), contorno=False, raio=6)
def quadro_branco(c, x, y, w=620, h=820, pe=True):
    """quadro branco de pé. Devolve o retângulo útil para escrever (x0, y0, x1, y1)."""
    if pe:
        for px in (x + 40, x + w - 40): c.ret(px - 8, y + h, px + 8, y + h + 260, (80, 84, 92), larg=1.6)
        c.ret(x + 20, y + h + 250, x + w - 20, y + h + 266, (80, 84, 92), larg=1.6)
    c.ret(x - 14, y - 14, x + w + 14, y + h + 14, (150, 154, 162), larg=2.2)
    c.ret(x, y, x + w, y + h, (236, 238, 240), contorno=False)
    c.ret(x + w*0.6, y + h + 2, x + w*0.85, y + h + 18, (120, 124, 132), larg=1.4)
    return (x + 36, y + 36, x + w - 30, y + h - 30)
def escrever(c, area, linhas, tam=70, cor=(46, 50, 78), entrelinha=1.25):
    """escreve à mão numa área (quadro, papel). linhas: lista de str; '- ' no começo vira item recuado"""
    x0, y0, x1, y1 = area; y = y0
    for ln in linhas:
        rec = 40 if ln.startswith("- ") else 0; t = tam*0.8 if rec else tam
        c.texto(x0 + rec, y, ln, t, cor, "mao"); y += t*entrelinha
def cadeiras(c, y, fileiras=3, cor=(40, 46, 60), x0=-60, x1=CW + 60, prof=0.82):
    """fileiras de poltronas de auditório vistas de trás (a da frente é a maior, embaixo)"""
    for f in range(fileiras - 1, -1, -1):
        k = prof**f; yy = y - f*170*k; largura = 230*k; n = int((x1 - x0)/largura) + 2
        for i in range(n):
            cx = x0 + i*largura + (f % 2)*largura/2
            c.ret(cx - largura*0.44, yy - 190*k, cx + largura*0.44, yy, escurecer(cor, 0.9 + 0.1*(1 - k)), larg=2, raio=26*k)
            c.ret(cx - largura*0.38, yy - 175*k, cx + largura*0.38, yy - 60*k, mistura(cor, (90, 100, 120), 0.18), contorno=False, raio=18*k)
def colchonetes(c, x, y, n=5, passo=(110, 70), w=230, h=120, cor=(92, 94, 100)):
    """colchonetes/sacos de dormir enrolados em fila diagonal"""
    for i in range(n - 1, -1, -1):
        cx, cy = x + i*passo[0], y + i*passo[1]
        c.ret(cx - w/2, cy - h/2, cx + w/2, cy + h/2, cor, raio=h/2.2)
        c.ret(cx - w*0.35, cy - h*0.35, cx + w*0.3, cy + h*0.1, escurecer(cor, 0.6), raio=12, larg=1.6)
        c.traco([(cx - w/2 + 20, cy + h*0.3), (cx + w/2 - 20, cy + h*0.3)], escurecer(cor, 0.7), 2)
def mesa(c, x0, x1, y, cor=(96, 72, 58), altura=320, espessura=34):
    c.ret(x0, y, x1, y + espessura, cor, larg=2.2)
    for px in (x0 + 40, x1 - 60): c.ret(px, y + espessura, px + 26, y + espessura + altura, escurecer(cor, 0.8), larg=2)
def celular(c, x, y, w=230, h=440, tela=None, aceso=True):
    """celular em pé; tela: imagem PIL (use tela_app) colada na tela, que brilha"""
    c.ret(x, y, x + w, y + h, (28, 28, 34), raio=30, larg=2.4)
    if aceso:
        c.ret(x + 12, y + 14, x + w - 12, y + h - 14, (236, 240, 248), contorno=False, raio=20, emissivo=True)
        if tela is not None: c.emis.alpha_composite(tela.convert("RGBA").resize((int((w - 24)*SS), int((h - 28)*SS))), (int((x + 12)*SS), int((y + 14)*SS)))
        c.luz_ponto(x + w/2, y + h/2, raio=w*1.2, cor=(190, 210, 255), forca=0.8)
    else: c.ret(x + 12, y + 14, x + w - 12, y + h - 14, (40, 44, 56), contorno=False, raio=20)
def notebook(c, x, y, w=560, tela=None):
    """notebook aberto sobre uma mesa em y (base). tela: imagem PIL (tela_app)"""
    h = w*0.62
    c.forma([(x - 30, y), (x + w + 30, y), (x + w, y - 26), (x, y - 26)], (70, 74, 84), larg=2)
    c.ret(x, y - 26 - h, x + w, y - 26, (40, 42, 50), raio=14, larg=2.2)
    c.ret(x + 18, y - 26 - h + 18, x + w - 18, y - 44, (226, 232, 244), contorno=False, emissivo=True, raio=6)
    if tela is not None: c.emis.alpha_composite(tela.convert("RGBA").resize((int((w - 36)*SS), int((h - 36)*SS))), (int((x + 18)*SS), int((y - 26 - h + 18)*SS)))
    c.luz_ponto(x + w/2, y - h/2, raio=w*0.9, cor=(180, 205, 255), forca=0.9)
def tela_app(linhas, w=400, h=760, cor_destaque=(90, 120, 220), letra=0.06):
    """tela genérica de app (sem logo): lista de balões. linhas: [('eu'|'outro', 'texto'), ...].
    letra: tamanho do texto em fração da largura (diminua se os balões não couberem na tela)"""
    im = Image.new("RGBA", (w, h), (240, 242, 246, 255)); d = ImageDraw.Draw(im); f = fonte("legenda", int(w*letra)); y = int(h*0.06)
    d.rectangle([0, 0, w, int(h*0.04)], fill=(220, 224, 232))
    lh = int(w*letra*1.25)
    for quem, txt in linhas:
        eu = quem == "eu"; partes, ln = [], ""
        for p in txt.split():
            if ln and d.textlength(ln + " " + p, font=f) > w*0.72 - 40: partes.append(ln); ln = p
            else: ln = (ln + " " + p).strip()
        partes.append(ln); tw = max(d.textlength(x, font=f) for x in partes) + 40; bh = int(w*0.035) + lh*len(partes)
        x0 = w - tw - 20 if eu else 20
        d.rounded_rectangle([x0, y, x0 + tw, y + bh], 18, fill=cor_destaque if eu else (255, 255, 255))
        for i, x in enumerate(partes): d.text((x0 + 20, y + int(w*0.0175) + lh*i + lh/2), x, font=f, fill=(255, 255, 255) if eu else (40, 44, 56), anchor="lm")
        y += bh + int(h*0.03)
    return im
def papel(c, x, y, w=420, h=560, giro=0, linhas=None, tam=48):
    """folha de papel (pode ter texto escrito à mão)"""
    pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    if giro:
        cx, cy = x + w/2, y + h/2; a = math.radians(giro)
        pts = [(cx + (px - cx)*math.cos(a) - (py - cy)*math.sin(a), cy + (px - cx)*math.sin(a) + (py - cy)*math.cos(a)) for px, py in pts]
    c.forma(pts, (238, 232, 216), larg=1.8)
    if linhas: escrever(c, (x + 30, y + 30, x + w - 20, y + h - 20), linhas, tam, (60, 56, 80))

# ------------------------------------------------------------------ cenários de dia (traço da referência)
def textura(c, x0, y0, x1, y1, forca=0.08, escala=22, seed=1, manchas=0):
    """textura de pintura (granulado e manchas) numa área: dá cara de cenário pintado à mão"""
    w, h = int((x1 - x0)*SS), int((y1 - y0)*SS)
    if w <= 0 or h <= 0: return
    rng = np.random.default_rng(seed)
    n = rng.normal(0, 1, (max(2, h//escala), max(2, w//escala))).astype(np.float32)
    n = np.asarray(Image.fromarray(((n.clip(-3, 3) + 3)/6*255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32)/255 - 0.5
    n += (rng.normal(0, 1, (h, w)).astype(np.float32))*0.12
    reg = s_ = c.alb.crop((int(x0*SS), int(y0*SS), int(x0*SS) + w, int(y0*SS) + h)); a = np.asarray(reg, np.float32)
    a[..., :3] *= (1 + forca*n)[..., None]
    if manchas:
        lay = Image.new("L", (w, h), 0); dl = ImageDraw.Draw(lay)
        for _ in range(manchas):
            mx, my, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(20, 120)*SS
            dl.ellipse([mx - r, my - r*0.6, mx + r, my + r*0.6], fill=int(rng.uniform(20, 60)))
        m = np.asarray(lay.filter(ImageFilter.GaussianBlur(14*SS)), np.float32)/255
        a[..., :3] *= (1 - 0.5*m)[..., None]
    c.alb.paste(Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA"), (int(x0*SS), int(y0*SS))); c.d = ImageDraw.Draw(c.alb)

def ceu(c, y1, cor_alto=None, cor_baixo=None, nuvens=6, seed=3):
    """céu de y=0 até y1, com nuvens de anime (brancas, base azulada). Cores pelo clima da cena."""
    cl = c.clima
    if cor_alto is None: cor_alto, cor_baixo = {"tarde": ((112, 120, 168), (250, 196, 140)), "noite": ((16, 22, 50), (52, 60, 100)),
                                                 "nublado": ((168, 178, 192), (214, 218, 222))}.get(cl, ((92, 150, 214), (196, 224, 240)))
    for i in range(40):
        y0_ = y1*i/40; c.ret(-10, y0_, CW + 10, y1*(i + 1)/40 + 2, mistura(cor_alto, cor_baixo, (i/39)**1.4), contorno=False)
    rnd = random.Random(seed)
    branco = (255, 244, 230) if cl == "tarde" else (250, 252, 255); base = (232, 168, 150) if cl == "tarde" else (186, 206, 232)
    for _ in range(nuvens if cl != "noite" else 0):
        cx, cy, L = rnd.uniform(-100, CW + 100), rnd.uniform(y1*0.12, y1*0.8), rnd.uniform(220, 460)
        bolas = [(cx + rnd.uniform(-L/2, L/2), cy - rnd.uniform(0, L*0.22), rnd.uniform(L*0.12, L*0.24)) for _ in range(7)]
        for bx, by, r in bolas: c.elipse(bx, by + r*0.25, r, r*0.8, base, contorno=False)
        for bx, by, r in bolas: c.elipse(bx - r*0.08, by, r*0.92, r*0.72, branco, contorno=False)
        c.ret(cx - L/2 - 20, cy + 6, cx + L/2 + 20, cy + 40, base, contorno=False, raio=16)

def cidade_longe(c, y, cor=None, seed=5, altura=260):
    """prédios e casas ao longe, claros e enevoados (dão profundidade ao céu)"""
    rnd = random.Random(seed); cor = cor or {"tarde": (214, 170, 140), "noite": (44, 50, 80)}.get(c.clima, (196, 206, 214)); x = -40
    while x < CW + 40:
        w = rnd.uniform(60, 170); h = rnd.uniform(0.3, 1.0)*altura; tom = mistura(cor, (255, 255, 255), rnd.uniform(0, 0.15))
        c.ret(x, y - h, x + w, y + 4, tom, contorno=False)
        if rnd.random() < 0.3: c.forma([(x - 6, y - h), (x + w/2, y - h - w*0.3), (x + w + 6, y - h)], escurecer(tom, 0.9), contorno=False)
        for jy in range(int(h//40)):
            for jx in range(int(w//36)):
                if rnd.random() < 0.6: c.ret(x + 10 + jx*36, y - h + 14 + jy*40, x + 24 + jx*36, y - h + 32 + jy*40, escurecer(tom, 0.86), contorno=False)
        x += w + rnd.uniform(-10, 14)

def telhado_metal(c, y0, cor=(170, 172, 176), fuga=(720, -900)):
    """chão de telhado de metal ondulado em perspectiva, do y0 até embaixo"""
    c.ret(-10, y0, CW + 10, CH + 10, cor, contorno=False)
    fx, fy = fuga
    for i in range(-30, 31):
        xb = CW/2 + i*120; xt = lerp(fx, xb, (y0 - fy)/(CH - fy))
        c.traco([(xt, y0), (xb, CH + 10)], escurecer(cor, 0.82), 3.2); c.traco([(xt + 6, y0), (xb + 26, CH + 10)], mistura(cor, (255, 255, 255), 0.35), 2.0)
    textura(c, 0, y0, CW, CH, 0.1, 30, seed=11, manchas=8)
    c.traco([(-10, y0), (CW + 10, y0)], escurecer(cor, 0.7), 3)

def parede_reboco(c, x0, y0, x1, y1, cor=(222, 196, 150), rodape=True, seed=7):
    """parede pintada com reboco gasto (manchas e textura), como as fachadas da referência"""
    c.ret(x0, y0, x1, y1, cor, contorno=False)
    if rodape: c.ret(x0, y1 - 120, x1, y1, escurecer(cor, 0.88), contorno=False); c.traco([(x0, y1 - 120), (x1, y1 - 120)], escurecer(cor, 0.7), 2)
    textura(c, x0, y0, x1, y1, 0.12, 26, seed=seed, manchas=10)
def calcada(c, y0, cor=(196, 186, 168), lajota=150):
    """calçada de lajotas em perspectiva, do y0 até embaixo"""
    c.ret(-10, y0, CW + 10, CH + 10, cor, contorno=False); y, k = y0, 0.35
    while y < CH:
        h = lajota*k; c.traco([(-10, y), (CW + 10, y)], escurecer(cor, 0.82), 2)
        for i in range(-10, 20): c.traco([(CW/2 + (i - 0.5*(int(y) % 2))*lajota*k*2.2, y), (CW/2 + (i - 0.5*(int(y) % 2))*lajota*k*2.2, y + h)], escurecer(cor, 0.85), 2)
        y += h; k *= 1.25
    textura(c, 0, y0, CW, CH, 0.08, 20, seed=13, manchas=6)
def sombra_sol(c, pts, forca=None):
    """sombra de borda dura (de um prédio, toldo, árvore) sobre o que já foi desenhado"""
    m = Image.new("L", c.alb.size, 0); ImageDraw.Draw(m).polygon([(x*SS, y*SS) for x, y in pts], fill=255)
    a = np.asarray(c.alb, np.float32); k = np.array(forca or c.dados.get("_mult_sombra", (0.66, 0.69, 0.84)), np.float32)
    mm = (np.asarray(m, np.float32)/255)[..., None]; a[..., :3] = a[..., :3]*(1 - mm) + a[..., :3]*k*mm
    c.alb = Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA"); c.d = ImageDraw.Draw(c.alb)
def caderno(c, x, y, w=420, h=320, giro=-6, desenho=None):
    """caderno de espiral aberto (segurado nas mãos). desenho(c, area) desenha dentro da folha"""
    a = math.radians(giro); cx, cy = x, y
    R = lambda px, py: (cx + px*math.cos(a) - py*math.sin(a), cy + px*math.sin(a) + py*math.cos(a))
    c.forma([R(-w/2, -h/2), R(w/2, -h/2), R(w/2, h/2), R(-w/2, h/2)], (240, 232, 214), larg=2)
    for i in range(10): px, py = R(-w/2 + 4, -h/2 + 20 + i*(h - 40)/9); c.elipse(px, py, 9, 6, (120, 120, 126), larg=1.2)
    if desenho: desenho(c, R, w, h)

# ------------------------------------------------------------------ luzes com chama
def vela(c, x, y, s=1.0, forca=1.7, raio=300, reflexo=None):
    """vela no chão ou na mesa (y = base). Cria a luz quente que treme e a chama animada.
    reflexo: True para o brilho comprido no chão polido (padrão: segue piso(polido=...))."""
    w, h = 34*s, 70*s
    c.ret(x - w/2, y - h, x + w/2, y, (236, 226, 200), larg=1.8, raio=5*s)
    c.elipse(x, y - h, w/2, w*0.18, (250, 242, 222), larg=1.4)
    c.traco([(x, y - h), (x, y - h - 10*s)], (40, 30, 26), 2.4)
    c.luz_ponto(x, y - h - 30*s, raio=raio*s, forca=forca, tremer=True, achatar=0.75)
    if reflexo is None: reflexo = c.dados.get("piso", (0, False))[1] and y > c.dados.get("piso", (CH, False))[0]
    c.chamas.append(dict(x=x, y=y - h - 10*s, s=s, reflexo=reflexo, base=y))

def desenhar_chama(im, ch, t, seed=0):
    """chama de vela animada (o motor desenha a cada quadro, por cima da cena iluminada)"""
    s = ch["s"]; x, y = ch["x"], ch["y"]; rnd = random.Random(int(t*12)*31 + seed)
    oscila = 1 + 0.12*math.sin(t*13 + seed) + rnd.uniform(-0.06, 0.06); inc = rnd.uniform(-3, 3)*s
    lay = Image.new("RGBA", (int(260*s), int(380*s)), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); cx, cy = 130*s, 330*s
    halo = Image.new("RGBA", lay.size, (0, 0, 0, 0)); ImageDraw.Draw(halo).ellipse([cx - 70*s, cy - 140*s*oscila, cx + 70*s, cy + 20*s], fill=(255, 170, 80, 70))
    lay.alpha_composite(halo.filter(ImageFilter.GaussianBlur(26*s)))
    for k, (cor, esc) in enumerate([((255, 150, 60, 255), 1.0), ((255, 210, 120, 255), 0.72), ((255, 248, 220, 255), 0.42)]):
        hh, ww = 64*s*oscila*esc, 15*s*esc
        d.polygon(suavizar([(cx, cy - hh), (cx + ww + inc*0.3, cy - hh*0.35), (cx + ww*0.8, cy + ww*0.4), (cx - ww*0.8, cy + ww*0.4), (cx - ww + inc*0.3, cy - hh*0.35)], 6), fill=cor)
    lay = lay.filter(ImageFilter.GaussianBlur(1.6*s))
    if ch.get("reflexo"):
        r = Image.new("RGBA", im.size, (0, 0, 0, 0)); dr = ImageDraw.Draw(r); b = ch["base"]
        dr.rectangle([x - 7*s, b + 14*s, x + 7*s, b + 260*s], fill=(255, 176, 96, int(90*oscila)))
        im.alpha_composite(r.filter(ImageFilter.GaussianBlur(9*s)))
    im.alpha_composite(lay, (int(x - cx), int(y - cy + 10*s)))

# ------------------------------------------------------------------ animação 2D (use dentro de animar_<cena>)
def escrever_animado(im, area, linhas, t, inicio=0.3, vel=14, tam=70, cor=(46, 50, 78), entrelinha=1.25, luz=0.85):
    """escreve à mão aos poucos (letra por letra) numa área da tela de desenho, como no quadro branco.
    vel = letras por segundo. luz < 1 escurece a tinta para combinar com a cena escura."""
    n = int(max(0.0, t - inicio)*vel)
    if n <= 0: return
    d = ImageDraw.Draw(im); x0, y0, x1, y1 = area; y = y0; cor = escurecer(cor, luz)
    for ln in linhas:
        rec = 40 if ln.startswith("- ") else 0; tt = tam*0.8 if rec else tam
        d.text((x0 + rec, y), ln[:n], font=fonte("mao", int(tt)), fill=cor)
        n -= len(ln)
        if n <= 0: break
        y += tt*entrelinha

def piscar_luz(im, x0, y0, x1, y1, t, ritmo=1.0, cor=(255, 255, 255), forca=60):
    """clarão que pisca numa área (lâmpada falhando, tela piscando)"""
    a = max(0.0, math.sin(t*ritmo*17)*math.sin(t*ritmo*5.3))
    if a <= 0.2: return
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).rectangle([x0, y0, x1, y1], fill=tuple(cor) + (int(forca*a),))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(40)))

def poeira(im, t, n=40, area=(0, 0, CW, CH), cor=(255, 220, 170), seed=1):
    """partículas de poeira flutuando devagar na luz"""
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); rnd = random.Random(seed)
    for i in range(n):
        x = area[0] + (rnd.uniform(0, 1)*(area[2] - area[0]) + 18*math.sin(t*0.5 + i)) % (area[2] - area[0])
        y = area[3] - ((rnd.uniform(0, 1)*(area[3] - area[1]) + t*14*rnd.uniform(0.5, 1.5)) % (area[3] - area[1]))
        r = rnd.uniform(1.5, 3.5); d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(cor) + (int(90 + 60*math.sin(t*2 + i)),))
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1)))
