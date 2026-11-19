"""Kit de desenho em pixel art para o motor reel_pixel.py.

Duas camadas por quadro:
  ARTE  : 108 x 192 "quadradinhos" (cada um vira 10x10 px no vídeo). Tudo o que é desenho vai aqui,
          para todos os elementos terem o MESMO tamanho de pixel.
  TEXTO : 270 x 480 (cada ponto vira 4x4 px). Títulos, etiquetas e legendas, com contorno escuro.

Zonas seguras (coordenadas da ARTE): o topo até y=46 fica sob o título; a legenda ocupa y=128 a 146;
abaixo de y=146 é área da interface do Instagram (só cenário). Ponha o desenho principal entre y=48 e y=126.
Em coordenadas de TEXTO, multiplique por 2,5 (ex.: arte y=60 -> texto y=150).
"""
import math, os, random
from PIL import Image, ImageDraw, ImageFont

AW, AH, AS = 108, 192, 10
TW, TH, TS = 270, 480, 4
W, H = 1080, 1920
FONTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")

def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def ease(x): x = clamp01(x); return 1 - (1 - x) ** 3
def lerp(a, b, t): return a + (b - a) * t
def mixc(a, b, t): return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))
def hex2rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def piscar(t, periodo=3.0): return (t % periodo) < 0.12

def _lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])
def contraste(a, b):
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

# ------------------------------------------------------------------ cores
INK = (15, 15, 18); BRANCO = (255, 255, 255); OURO = (250, 204, 21); OUROE = (161, 98, 7)
VERMELHO = (220, 50, 50); LARANJA = (245, 140, 30); VERDE = (90, 190, 110); AZUL = (70, 130, 230)
CINZA = (200, 192, 182); CINZAE = (110, 104, 120)
CEU1 = (186, 214, 255); CEU2 = (214, 232, 255); GRAMA = (120, 190, 90); GRAMAE = (80, 150, 60)
NOITE1 = (34, 24, 58); NOITE2 = (52, 36, 84)
PELE = [(255, 214, 180), (224, 172, 128), (176, 120, 80), (120, 78, 50)]
CABELO = [(60, 40, 30), (20, 20, 24), (170, 110, 50), (230, 190, 90)]

class Tema:
    """Paleta derivada da cor da marca."""
    def __init__(self, cor="#7C3AED"):
        c = hex2rgb(cor) if isinstance(cor, str) else cor
        # o destaque precisa ler bem com contorno preto e o bloco precisa ler texto branco
        while contraste(c, BRANCO) < 3.0:
            c = mixc(c, (0, 0, 0), 0.08)
        self.cor = c
        self.escura = mixc(c, (0, 0, 0), 0.6)
        self.clara = mixc(c, BRANCO, 0.62)   # palavras de destaque no título
        self.suave = mixc(c, BRANCO, 0.85)
        self.fundo = mixc(c, BRANCO, 0.93)

# ------------------------------------------------------------------ sprites prontos (originais)
# Letras: K contorno, W branco, G cinza, R vermelho, O laranja, Y amarelo, D amarelo escuro,
# H cabelo, S pele, C cor da marca, E cor escura da marca, P calça, L lilás claro (cor clara da marca)
GALINHA = [
    "...............R.R......", "..............RRRRR.....", ".............KKKKKKK....", "............KWWWWWWWK...",
    "............KWWWWKWWKOO.", "............KWWWWWWWKOOO", "..KK........KWWWWWWWRK..", ".KWWK.......KWWWWWWRRK..",
    ".KWWWK.....KWWWWWWWRK...", ".KWWWWKKKKKWWWWWWWWK....", ".KWWWWWWWWWWWWWWWWWK....", "..KWWWGGGGGGWWWWWWWK....",
    "..KWWWGWWWWWGWWWWWK.....", "..KWWWWGGGGGWWWWWWK.....", "...KWWWWWWWWWWWWWGK.....", "....KGWWWWWWWWWWGK......",
    ".....KKGGGGGGGGKK.......", ".......KKKKKKKK.........", "........O....O..........", ".......OOO..OOO.........",
]
GALINHA_SENTADA = GALINHA[:18]
PINTINHO = [
    "......KKKK....", ".....KYYYYK...", "....KYYYKYYK..", "....KYYYYYYKOO", "....KYYYYYYKO.", "..KKKYYYYYK...",
    ".KYYYYYYYYYK..", "KYYYKKYYYYYYK.", "KYYYYYKYYYYYK.", "KYYYYYYYYYYDK.", ".KDYYYYYYYDDK.", "..KKDDDDDDKK..",
    "...KKKKKKKK...", "....O....O....", "...OO...OO....",
]
PINTINHO_PISCA = PINTINHO[:2] + ["....KYYYYYYK..", "....KYYYKKYKOO"] + PINTINHO[4:]
PESSOA = [
    "....KKKKKK....", "...KHHHHHHK...", "..KHHHHHHHHK..", "..KHSSSSSSHK..", "..KSSKSSKSSK..", "..KSSSSSSSSK..",
    "...KSSKKSSK...", "....KSSSSK....", "...KKCCCCKK...", "..KCCCCCCCCK..", ".KCCKCCCCKCCK.", ".KCCKCCCCKCCK.",
    ".KSSKCCCCKSSK.", "..KK.KCCK.KK..", "....KPPPPK....", "....KPPKPPK...", "....KPPKPPK...", "....KPPKPPK...",
    "...KKKK.KKKK..",
]
PESSOA_PISCA = PESSOA[:4] + ["..KSSSSSSSSK.."] + PESSOA[5:]
CORACAO = [".KK.KK.", "KRRKRRK", "KRRRRRK", ".KRRRK.", "..KRK..", "...K..."]
ESTRELA = ["...K...", "..KYK..", "KKKYKKK", "KYYYYYK", ".KYYYK.", ".KYKYK.", "KK...KK"]
MOEDA = [".KKKK.", "KYYYDK", "KYDYDK", "KYDYDK", "KYYDDK", ".KKKK."]

class Arte:
    """Camada de desenho (108x192). Use a.d para desenhar à mão (ImageDraw) ou os atalhos abaixo."""
    def __init__(self, tema, fundo=CEU2):
        self.tema = tema
        self.img = Image.new("RGB", (AW, AH), fundo)
        self.d = ImageDraw.Draw(self.img)
        t = tema
        self.cores = {"K": INK, "W": BRANCO, "G": CINZA, "R": VERMELHO, "O": LARANJA, "Y": (255, 214, 64),
                      "D": (214, 160, 20), "H": CABELO[0], "S": PELE[0], "C": t.cor, "E": t.escura, "P": (60, 70, 110),
                      "L": t.clara}

    # ---- básicos
    def px(self, x, y, cor): self.d.point((x, y), fill=cor)
    def ret(self, x0, y0, x1, y1, cor, contorno=None):
        if contorno: self.d.rectangle([x0 - 1, y0 - 1, x1 + 1, y1 + 1], fill=contorno)
        self.d.rectangle([x0, y0, x1, y1], fill=cor)
    def caixa(self, x0, y0, x1, y1, cor, sombra=True):
        """retângulo com contorno preto e sombra dura (estilo botão/janela de jogo)"""
        if sombra: self.d.rectangle([x0 + 2, y0 + 2, x1 + 2, y1 + 2], fill=self.tema.escura)
        self.d.rectangle([x0 - 1, y0 - 1, x1 + 1, y1 + 1], fill=INK)
        self.d.rectangle([x0, y0, x1, y1], fill=cor)
    def elipse(self, cx, cy, rx, ry, cor, contorno=INK):
        if contorno: self.d.ellipse([cx - rx - 1, cy - ry - 1, cx + rx + 1, cy + ry + 1], fill=contorno)
        self.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=cor)
    def linha(self, pts, cor): self.d.line(pts, fill=cor)
    def sprite(self, spr, x, y, cores=None, espelhar=False):
        cs = dict(self.cores); cs.update(cores or {})
        for j, row in enumerate(spr):
            for i, c in enumerate(row[::-1] if espelhar else row):
                if c in cs: self.d.point((int(x) + i, int(y) + j), fill=cs[c])
    def imagem(self, im, x, y): self.img.paste(im, (int(x), int(y)), im)
    def brilho(self, x, y, cor=OURO):
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)): self.d.point((x + dx, y + dy), fill=cor)
    def confete(self, t, n=16, y0=46, altura=80, seed=3):
        rnd = random.Random(seed)
        for i in range(n):
            x = rnd.randint(4, AW - 4); y = y0 + int((t * 30 + rnd.randint(0, altura)) % altura)
            self.d.point((x, y), fill=[self.tema.cor, OURO, VERMELHO, VERDE][i % 4])

    # ---- cenários (tela cheia)
    def ceu(self, chao=128, t=0.0, nuvens=True):
        self.d.rectangle([0, 0, AW, 60], fill=CEU1); self.d.rectangle([0, 60, AW, AH], fill=CEU2)
        self.d.rectangle([0, chao, AW, AH], fill=GRAMA); self.d.line([0, chao, AW, chao], fill=GRAMAE)
        rnd = random.Random(5)
        for _ in range(40): self.d.point((rnd.randint(0, AW), rnd.randint(chao + 2, AH)), fill=GRAMAE)
        if nuvens:
            self.nuvem(int(10 + t * 2) % 130 - 12, 52); self.nuvem(int(78 - t * 1.5) % 130 - 12, 60)
    def nuvem(self, x, y):
        self.d.rectangle([x + 2, y, x + 9, y + 3], fill=BRANCO); self.d.rectangle([x, y + 2, x + 12, y + 5], fill=BRANCO)
        self.d.line([x, y + 5, x + 12, y + 5], fill=(200, 216, 240))
    def noite(self, chao=130, t=0.0, cor_chao=(60, 44, 40)):
        for y in range(AH): self.d.line([0, y, AW, y], fill=NOITE1 if (y // 4) % 2 else NOITE2)
        rnd = random.Random(9)
        for _ in range(18):
            x, y = rnd.randint(0, AW), rnd.randint(46, 100)
            if int(t * 3 + x) % 5: self.d.point((x, y), fill=(200, 190, 255))
        self.d.rectangle([0, chao, AW, AH], fill=cor_chao)
    def listras(self, c1, c2, passo=6):
        for y in range(AH): self.d.line([0, y, AW, y], fill=c1 if (y // passo) % 2 else c2)
    def escritorio(self, t=0.0):
        """parede na cor suave da marca, janela, quadro e mesa de trabalho (tampo em y=118)"""
        tm = self.tema
        self.d.rectangle([0, 0, AW, AH], fill=tm.fundo)
        for x in range(0, AW, 6): self.d.line([x, 0, x, 117], fill=tm.suave)
        self.caixa(70, 54, 98, 76, CEU1, sombra=False)                      # janela
        self.d.line([84, 54, 84, 76], fill=INK); self.d.line([70, 65, 98, 65], fill=INK)
        self.nuvem(72 + int(t * 2) % 20, 58)
        self.d.rectangle([0, 118, AW, AH], fill=(150, 104, 70))              # mesa
        self.d.line([0, 118, AW, 118], fill=INK); self.d.rectangle([0, 119, AW, 121], fill=(186, 134, 92))
        for x in range(0, AW, 14): self.d.line([x, 124, x + 8, 124], fill=(130, 88, 58))

    # ---- objetos prontos
    def computador(self, x, y, cor_tela=None, w=46, h=32):
        """monitor com tela (x,y = canto da tela). Retorna (x0,y0,x1,y1) da tela para desenhar dentro."""
        tela = cor_tela or (28, 24, 40)
        self.caixa(x - 2, y - 2, x + w + 2, y + h + 2, (60, 60, 72))
        self.d.rectangle([x, y, x + w, y + h], fill=tela)
        self.d.rectangle([x + w // 2 - 3, y + h + 3, x + w // 2 + 3, y + h + 7], fill=(60, 60, 72))
        self.d.rectangle([x + w // 2 - 9, y + h + 7, x + w // 2 + 9, y + h + 8], fill=INK)
        return (x, y, x + w, y + h)
    def celular(self, x, y, w=22, h=40, cor_tela=BRANCO):
        self.caixa(x - 2, y - 3, x + w + 2, y + h + 3, INK)
        self.d.rectangle([x, y, x + w, y + h], fill=cor_tela)
        self.d.line([x + w // 2 - 2, y - 2, x + w // 2 + 2, y - 2], fill=CINZAE)
        return (x, y, x + w, y + h)
    def linhas_texto(self, x, y, larguras, cor=CINZAE, passo=3, revelar=1.0):
        """linhas fininhas imitando texto; revelar 0..1 mostra aos poucos (digitação)"""
        total = sum(larguras); vis = total * clamp01(revelar)
        for i, wd in enumerate(larguras):
            if vis <= 0: break
            ww = int(min(wd, vis)); vis -= wd
            if ww > 0: self.d.line([x, y + i * passo, x + ww, y + i * passo], fill=cor)
    def balao(self, x, y, w, h, cor=BRANCO, lado="esq"):
        """balão de conversa (chat)"""
        self.caixa(x, y, x + w, y + h, cor, sombra=False)
        if lado == "esq": self.d.polygon([(x + 2, y + h + 1), (x + 6, y + h + 1), (x + 1, y + h + 4)], fill=INK)
        else: self.d.polygon([(x + w - 6, y + h + 1), (x + w - 2, y + h + 1), (x + w - 1, y + h + 4)], fill=INK)
    def documento(self, x, y, w=26, h=34, revelar=1.0):
        self.caixa(x, y, x + w, y + h, BRANCO)
        self.d.polygon([(x + w - 6, y), (x + w, y), (x + w, y + 6)], fill=self.tema.suave)
        self.linhas_texto(x + 3, y + 5, [w - 10, w - 6, w - 8, w - 12, w - 7, w - 9, w - 14][: (h - 6) // 4], passo=4, revelar=revelar)
    def checklist(self, x, y, itens=4, marcados=0, w=34):
        self.caixa(x, y, x + w, y + itens * 8 + 4, BRANCO)
        for i in range(itens):
            yy = y + 3 + i * 8
            self.d.rectangle([x + 3, yy, x + 7, yy + 4], fill=BRANCO, outline=INK)
            if i < marcados:
                self.d.line([x + 3, yy + 2, x + 5, yy + 4, x + 9, yy - 1], fill=VERDE)
            self.d.line([x + 11, yy + 2, x + w - 4 - (i * 3) % 8, yy + 2], fill=CINZAE)
    def envelope(self, x, y, w=24, h=16):
        self.caixa(x, y, x + w, y + h, BRANCO)
        self.d.line([x, y, x + w // 2, y + h // 2, x + w, y], fill=INK)
    def calendario(self, x, y, dia="", w=22, h=22):
        self.caixa(x, y, x + w, y + h, BRANCO)
        self.d.rectangle([x, y, x + w, y + 5], fill=VERMELHO)
        for i in range(3):
            for j in range(4): self.d.point((x + 3 + j * 5, y + 9 + i * 4), fill=CINZAE)
    def relogio(self, cx, cy, r=8, t=0.0, velocidade=1.0):
        self.elipse(cx, cy, r, r, BRANCO)
        a = t * velocidade * 2 * math.pi
        self.d.line([cx, cy, cx + int((r - 2) * math.sin(a)), cy - int((r - 2) * math.cos(a))], fill=INK)
        self.d.line([cx, cy, cx + int((r - 4) * math.sin(a / 12)), cy - int((r - 4) * math.cos(a / 12))], fill=VERMELHO)
    def lampada(self, cx, cy, acesa=True):
        self.elipse(cx, cy, 6, 6, OURO if acesa else CINZA)
        self.d.rectangle([cx - 3, cy + 6, cx + 3, cy + 10], fill=CINZAE)
        if acesa:
            for a in range(0, 360, 45):
                ra = math.radians(a); self.d.point((cx + int(10 * math.cos(ra)), cy + int(10 * math.sin(ra))), fill=OURO)
    def xicara(self, x, y):
        self.caixa(x, y, x + 8, y + 8, BRANCO, sombra=False)
        self.d.rectangle([x + 9, y + 2, x + 11, y + 5], outline=INK)
    def pilha_papel(self, x, y, n=5, w=24):
        for i in range(n):
            self.caixa(x + (i % 2), y - i * 3, x + w + (i % 2), y - i * 3 + 2, BRANCO, sombra=False)
    def seta(self, x0, y0, x1, y1, cor=None):
        cor = cor or self.tema.cor
        self.d.line([x0, y0, x1, y1], fill=cor, width=2)
        a = math.atan2(y1 - y0, x1 - x0)
        for s in (-1, 1):
            self.d.line([x1, y1, x1 - int(4 * math.cos(a + s * 0.6)), y1 - int(4 * math.sin(a + s * 0.6))], fill=cor, width=2)
    # ---- ovo e afins (usados no exemplo do ovo, servem para outros temas)
    def ovo(self, cx, cy, rx, ry, cor=(240, 222, 196), contorno=(150, 112, 74)):
        self.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=contorno)
        self.d.ellipse([cx - rx + 1, cy - ry + 1, cx + rx - 1, cy + ry - 1], fill=(214, 190, 158))
        self.d.ellipse([cx - rx + 1, cy - ry + 1, cx + rx - 2, cy + ry - 2], fill=cor)
        self.d.point((cx - rx // 2, cy - ry // 2), fill=BRANCO)
    def gema(self, cx, cy, r):
        self.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(190, 104, 10))
        self.d.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=(255, 176, 32))
        if r >= 3: self.d.point((cx - r // 2, cy - r // 2), fill=(255, 226, 130))
    def ninho(self, cx, y, wd=30):
        self.d.ellipse([cx - wd // 2, y - 3, cx + wd // 2, y + 5], fill=(140, 100, 40))
        self.d.ellipse([cx - wd // 2 + 1, y - 3, cx + wd // 2 - 1, y + 3], fill=(214, 170, 80))
        rnd = random.Random(cx + y)
        for _ in range(wd // 2):
            a = rnd.randint(-wd // 2 + 2, wd // 2 - 4); b = rnd.randint(-2, 2)
            self.d.line([cx + a, y + b, cx + a + 2, y + b + rnd.choice([-1, 0, 1])], fill=(140, 100, 40))

# ------------------------------------------------------------------ mascote a partir de um PNG
def pixelizar_mascote(caminho, tam=18, cores=6):
    """Transforma um PNG (fundo transparente) num sprite pixel art com contorno, cabendo em tam x tam."""
    im = Image.open(caminho).convert("RGBA")
    bb = im.getbbox()
    if bb: im = im.crop(bb)
    im.thumbnail((tam - 2, tam - 2), Image.BOX)
    a = im.split()[3].point(lambda v: 255 if v > 110 else 0)
    rgb = im.convert("RGB").quantize(colors=cores, method=Image.MEDIANCUT).convert("RGB")
    sp = Image.new("RGBA", (im.width + 2, im.height + 2), (0, 0, 0, 0))
    sp.paste(rgb, (1, 1), a)
    mask = sp.split()[3]
    out = Image.new("RGBA", sp.size, (0, 0, 0, 0))
    px = mask.load()
    for y in range(sp.height):
        for x in range(sp.width):
            if px[x, y] == 0 and any(0 <= x + dx < sp.width and 0 <= y + dy < sp.height and px[x + dx, y + dy]
                                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), INK + (255,))
    out.alpha_composite(sp)
    return out

# ------------------------------------------------------------------ camada de texto
ACC = {"Á": ("A", "ac"), "É": ("E", "ac"), "Í": ("I", "ac"), "Ó": ("O", "ac"), "Ú": ("U", "ac"),
       "Â": ("A", "ci"), "Ê": ("E", "ci"), "Ô": ("O", "ci"), "Ã": ("A", "ti"), "Õ": ("O", "ti")}
_f = {}
def fonte(nome, n):
    k = (nome, n)
    if k not in _f:
        arq = "PressStart2P-Regular.ttf" if nome == "jogo" else "PixelifySans-Bold.ttf"
        _f[k] = ImageFont.truetype(os.path.join(FONTS, arq), n, layout_engine=ImageFont.Layout.BASIC)
    return _f[k]

class Textos:
    """Camada de texto (270x480). Tudo sai com contorno escuro, para ler sobre qualquer desenho."""
    def __init__(self, tema):
        self.tema = tema
        self.img = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img); self.d.fontmode = "1"

    def _raw(self, xy, s, f, fill):
        d = self.d
        if "PressStart" not in f.path or not any(c in ACC for c in s):
            d.text(xy, s, font=f, fill=fill); return
        # a fonte de videogame espreme maiúsculas acentuadas: desenha a letra e o acento à parte
        x, y = xy; u = max(1, round(f.size / 8))
        for c in s:
            if c in ACC:
                base, kind = ACC[c]; d.text((x, y), base, font=f, fill=fill)
                cx, ay = x + f.size // 2 - u, y - 3 * u
                if kind == "ac":
                    d.rectangle([cx + u, ay, cx + 2 * u - 1, ay + u - 1], fill=fill); d.rectangle([cx, ay + u, cx + u - 1, ay + 2 * u - 1], fill=fill)
                elif kind == "ci":
                    d.rectangle([cx, ay, cx + u - 1, ay + u - 1], fill=fill)
                    d.rectangle([cx - u, ay + u, cx - 1, ay + 2 * u - 1], fill=fill); d.rectangle([cx + u, ay + u, cx + 2 * u - 1, ay + 2 * u - 1], fill=fill)
                else:
                    for k, dy in enumerate([1, 0, 1, 0]):
                        d.rectangle([cx - u + k * u, ay + dy * u, cx + k * u - 1, ay + dy * u + u - 1], fill=fill)
            else:
                d.text((x, y), c, font=f, fill=fill)
            x += f.getlength(c)

    def largura(self, s, tipo="jogo", tam=8): return fonte(tipo, tam).getlength(s)

    def texto(self, x, y, s, cor=BRANCO, tam=8, tipo="jogo", centro=False, contorno=INK):
        f = fonte(tipo, tam)
        if centro: x = int(x - f.getlength(s) / 2)
        if contorno:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy: self._raw((x + dx, y + dy), s, f, contorno)
            self._raw((x + 1, y + 2), s, f, contorno)
        self._raw((x, y), s, f, cor)

    def etiqueta(self, x, y, s, cor="marca", centro=True):
        """plaquinha de jogo. cor: 'marca', 'ouro', 'vermelho', 'verde', 'escura' ou (r,g,b)"""
        fill, fg = {"marca": (self.tema.cor, BRANCO), "ouro": (OURO, INK), "vermelho": (VERMELHO, BRANCO),
                    "verde": ((40, 150, 80), BRANCO), "escura": (self.tema.escura, BRANCO)}.get(cor, (cor, BRANCO)) \
            if isinstance(cor, str) else (cor, BRANCO)
        f = fonte("jogo", 8); wd = int(f.getlength(s)) + 12
        if centro: x = int(x - wd / 2)
        x = max(4, min(x, TW - 6 - wd))
        d = self.d
        d.rectangle([x - 1, y - 1, x + wd + 1, y + 14], fill=INK); d.rectangle([x + 2, y + 2, x + wd + 2, y + 16], fill=INK)
        d.rectangle([x, y, x + wd, y + 13], fill=fill)
        self._raw((x + 6, y + 3), s, f, fg)
        return wd
