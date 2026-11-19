#!/usr/bin/env python3
"""Reel tutorial animado: transforma um roteiro (JSON) num Reel 9:16 (1080x1920, 30 fps).

Uso:
  python3 reel.py roteiro.json --out PASTA                    # vídeo completo
  python3 reel.py roteiro.json --out PASTA --preview 1,8.5,20 # só quadros de prova (PNG + grade)
  python3 reel.py roteiro.json --out PASTA --audio voz.mp3    # sincroniza com a narração gravada
  python3 reel.py roteiro.json --out PASTA --sem-musica

Precisa de: Python 3, Pillow, numpy e ffmpeg (se não houver ffmpeg, instala imageio-ffmpeg pelo pip).
Marcações nos textos:
  *palavra*   no título: palavra na cor da marca
  [[trecho]]  nas janelas: marca-texto que aparece durante a cena
  {{trecho}}  nas janelas: tarja preta que cobre o trecho (dado sigiloso)
"""
import argparse, json, math, os, re, shutil, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")

# ------------------------------------------------------------------ util
def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "imageio-ffmpeg"],
                       check=False)
        try:
            import imageio_ffmpeg
        except ImportError:
            sys.exit("ERRO: não encontrei o ffmpeg e não consegui instalar o imageio-ffmpeg.")
    return imageio_ffmpeg.get_ffmpeg_exe()

def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))

def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = c
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)

def clamp01(x):
    return 0.0 if x < 0 else 1.0 if x > 1 else x

def ease(x):
    x = clamp01(x)
    return 1 - (1 - x) ** 3

def pop(x):  # 0->1 com leve passada (efeito "pop")
    x = clamp01(x)
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

_fcache = {}
def F(name, size):
    k = (name, size)
    if k not in _fcache:
        _fcache[k] = ImageFont.truetype(os.path.join(FONTS, name), size)
    return _fcache[k]

_lcache = {}
def tw(font, text):
    k = (id(font), text)
    if k not in _lcache:
        _lcache[k] = font.getlength(text)
    return _lcache[k]

# ------------------------------------------------------------------ texto com marcações
TOKEN_RE = re.compile(r"(\[\[.*?\]\]|\{\{.*?\}\}|\*[^*]+\*)")

def tokens(text):
    """Divide em palavras com marcação: None, 'hl' (marca-texto), 'tj' (tarja), 'em' (cor)."""
    out = []
    glue = False  # o trecho anterior terminou sem espaço (ex.: "[[prazo]]." ou "c/{{X}}")
    for part in TOKEN_RE.split(text or ""):
        if not part:
            continue
        starts_glued = glue and not part[:1].isspace()
        glue = not part[-1:].isspace()
        flag = None
        if part.startswith("[[") and part.endswith("]]"):
            flag, part = "hl", part[2:-2]
        elif part.startswith("{{") and part.endswith("}}"):
            flag, part = "tj", part[2:-2]
        elif part.startswith("*") and part.endswith("*") and len(part) > 2:
            flag, part = "em", part[1:-1]
        ws = part.split()
        if ws and starts_glued and out:
            pw, pf = out[-1]
            out[-1] = (pw + ws[0], pf if pf in ("hl", "tj") else flag)
            ws = ws[1:]
        for w in ws:
            out.append((w, flag))
    return out

def plain(text):
    return " ".join(w for w, _ in tokens(text))

def layout(toks, font, maxw):
    lines, cur, x = [], [], 0.0
    sp = tw(font, " ")
    for w, f in toks:
        ww = tw(font, w)
        if cur and x + ww > maxw:
            lines.append(cur)
            cur, x = [], 0.0
        cur.append([x, w, f, ww])
        x += ww + sp
    if cur:
        lines.append(cur)
    return lines

def draw_rich(d, x, y, lines, font, lh, color, reveal=None, hl=0.0, tj=0.0, hlcol=(221, 214, 254),
              hlborder=None, emcol=None, tjcol=(15, 15, 18)):
    """Desenha linhas já quebradas. reveal = nº de caracteres visíveis (efeito digitação).
    Marca-texto (hl) e tarja (tj) cobrem trechos contínuos, mesmo com várias palavras."""
    left = 10 ** 9 if reveal is None else reveal
    asc = font.getmetrics()[0]
    cursor = None
    for li, line in enumerate(lines):
        yy = y + li * lh
        # quantos caracteres desta linha estão visíveis
        vis_words, budget = [], left
        for (ox, w, f, ww) in line:
            if budget <= 0:
                break
            vis_words.append(w[:budget])
            budget -= len(w) + 1
        full = [vw == lw[1] for vw, lw in zip(vis_words, line)]
        # faixas contínuas de hl / tj (só palavras inteiras já digitadas)
        runs, k = [], 0
        while k < len(vis_words):
            f = line[k][2]
            if f in ("hl", "tj") and full[k]:
                a = k
                while k + 1 < len(vis_words) and line[k + 1][2] == f and full[k + 1]:
                    k += 1
                runs.append((f, line[a][0], line[k][0] + line[k][3]))
            k += 1
        for f, x0, x1 in runs:
            if f == "hl" and hl > 0:
                pad = 6
                ex = x + x0 - pad + (x1 - x0 + 2 * pad) * ease(hl)
                d.rounded_rectangle([x + x0 - pad, yy - 4, ex, yy + asc + 10], 6, fill=hlcol,
                                    outline=hlborder, width=2 if hlborder else 0)
        for (ox, w, f, ww), vis in zip(line, vis_words):
            col = emcol if (f == "em" and emcol) else color
            d.text((x + ox, yy), vis, font=font, fill=col)
            cursor = (x + ox + (tw(font, vis) if vis != w else ww), yy)
        for f, x0, x1 in runs:
            if f == "tj" and tj > 0:
                d.rectangle([x + x0 - 4, yy - 2, x + x0 - 4 + (x1 - x0 + 8) * ease(tj), yy + asc + 8], fill=tjcol)
        left = budget
        if left <= 0:
            return cursor
    return cursor

def total_chars(toks):
    return sum(len(w) + 1 for w, _ in toks)

# ------------------------------------------------------------------ roteiro e tempos
def word_weight(w):
    k = len(w) + 3
    if w.endswith("..."):
        k += 7
    elif w[-1:] in ".!?":
        k += 5
    elif w[-1:] in ",;:":
        k += 2
    return k

def caption_groups(narr):
    words = narr.split()
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 6 or (w[-1:] in ".!?" and len(cur) >= 2):
            groups.append(cur)
            cur = []
    if cur:
        if groups and len(cur) == 1:
            groups[-1].extend(cur)
        else:
            groups.append(cur)
    return groups

def plan_times(spec, audio_len=None):
    wps = float(spec.get("palavras_por_segundo", 2.3))
    durs = []
    for c in spec["cenas"]:
        n = len(c.get("narracao", "").split())
        durs.append(float(c["duracao"]) if c.get("duracao") else max(3.0, n / wps + 0.9))
    if audio_len:
        marks = spec.get("marcas_audio")
        if marks and len(marks) == len(durs):
            starts = [float(m) for m in marks]
            ends = starts[1:] + [audio_len + 0.6]
            durs = [max(1.0, e - s) for s, e in zip(starts, ends)]
        else:
            k = (audio_len + 0.6) / sum(durs)
            durs = [d * k for d in durs]
    starts, t = [], 0.0
    for d in durs:
        starts.append(t)
        t += d
    return durs, starts

# ------------------------------------------------------------------ desenho
class Theme:
    def __init__(self, brand):
        cor = hex2rgb(brand.get("cor", "#7C3AED"))
        white = (255, 255, 255)
        # garante leitura do texto colorido sobre branco
        while contrast(cor, white) < 4.5:
            cor = mix(cor, (0, 0, 0), 0.08)
        self.cor = cor
        self.escura = mix(cor, (0, 0, 0), 0.45)
        self.clara = mix(cor, white, 0.80)      # marca-texto
        self.tint = mix(cor, white, 0.93)       # fundos suaves
        self.futura = mix(cor, white, 0.72)     # palavras ainda não ditas
        self.ink = (15, 15, 18)
        self.cinza = (120, 116, 132)
        self.linha = (228, 225, 236)
        self.bg = white
        self.dark = (24, 20, 33)
        self.dark2 = (36, 31, 50)
        self.claro_dark = mix(cor, white, 0.45)  # destaque sobre fundo escuro

WX0, WX1, WY0, WY1 = 56, 1024, 560, 1272  # área da janela
HEAD = 58

def window_frame(d, th, title, dark=False, y0=WY0, y1=WY1):
    bg = th.dark if dark else th.bg
    hd = th.dark2 if dark else th.tint
    d.rounded_rectangle([WX0, y0, WX1, y1], 22, fill=bg, outline=th.ink, width=3)
    d.rounded_rectangle([WX0 + 3, y0 + 3, WX1 - 3, y0 + HEAD], 19, fill=hd)
    d.rectangle([WX0 + 3, y0 + HEAD - 18, WX1 - 3, y0 + HEAD], fill=hd)
    d.line([WX0 + 3, y0 + HEAD, WX1 - 3, y0 + HEAD], fill=th.ink if not dark else th.dark2, width=2)
    for i in range(3):
        cx = WX0 + 30 + i * 22
        d.ellipse([cx - 7, y0 + 22, cx + 7, y0 + 36], fill=mix(th.cor, (255, 255, 255), 0.55))
    if title:
        d.text((WX0 + 108, y0 + 16), title, font=F("Inter-Bold.ttf", 25),
               fill=th.claro_dark if dark else th.escura)

def check(d, x, y, s, col, w=5):
    d.line([(x, y + s * 0.55), (x + s * 0.38, y + s * 0.9), (x + s, y + s * 0.1)], fill=col, width=w, joint="curve")

def pill(d, x, y, text, font, fill, fg, outline=None, padx=22, pady=12, ow=3, icon=False):
    w = tw(font, text) + 2 * padx + (34 if icon else 0)
    a = font.getmetrics()[0]
    h = a + 2 * pady
    d.rounded_rectangle([x, y, x + w, y + h], h // 2, fill=fill, outline=outline, width=ow if outline else 0)
    tx = x + padx
    if icon:
        check(d, x + padx, y + pady + 4, a * 0.62, fg, 4)
        tx += 34
    d.text((tx, y + pady - 2), text, font=font, fill=fg)
    return w, h

def paste_scaled(img, layer, cx, cy, s):
    if s <= 0.01:
        return
    w, h = layer.size
    nw, nh = max(1, int(w * s)), max(1, int(h * s))
    l2 = layer.resize((nw, nh), Image.BILINEAR)
    img.alpha_composite(l2, (int(cx - nw / 2), int(cy - nh / 2)))

# ---------------- janelas
def win_lista(img, d, th, j, t, D):
    window_frame(d, th, j.get("titulo", "caixa de entrada"))
    itens = j.get("itens", [])
    nao = set(j.get("nao_lidas", list(range(len(itens)))))
    dest = j.get("destaque")
    t_dest = float(j.get("destaque_em", 0.25)) * D
    rh = int(j.get("altura_linha", 96))
    y = WY0 + HEAD + 14
    fb, fr = F("Inter-Bold.ttf", 29), F("Inter-Medium.ttf", 29)
    for i, it in enumerate(itens):
        a = ease((t - 0.1 - i * 0.07) / 0.3)
        if a <= 0 or y + rh > WY1 - 6:
            break
        rem, ass, prev = (list(it) + ["", "", ""])[:3]
        dx = 0
        if dest == i and j.get("tremer") and t < t_dest:
            dx = int(5 * math.sin(t * 40))
        if dest == i and t >= t_dest:
            k = ease((t - t_dest) / 0.3)
            d.rounded_rectangle([WX0 + 10, y - 4, WX1 - 10, y + rh - 10], 10, fill=mix(th.bg, th.clara, k),
                                outline=th.cor if k > 0.5 else None, width=3)
        yy = y + (1 - a) * 18
        bold = i in nao
        if bold:
            d.ellipse([WX0 + 26 + dx, yy + 14, WX0 + 38 + dx, yy + 26], fill=th.cor)
        rl = layout(tokens(rem), fb if bold else fr, 240)[:2]
        draw_rich(d, WX0 + 52 + dx, yy + 6, rl, fb if bold else fr, 34, th.ink)
        x = WX0 + 320 + dx
        d.text((x, yy + 6), ass, font=fb if bold else fr, fill=th.ink)
        x += tw(fb if bold else fr, ass) + 10
        if prev and x < WX1 - 40:
            s = "— " + prev
            while s and x + tw(fr, s) > WX1 - 24:
                s = s[:-1]
            d.text((x, yy + 6), s, font=fr, fill=th.cinza)
        d.line([WX0 + 24, y + rh - 8, WX1 - 24, y + rh - 8], fill=th.linha, width=2)
        y += rh

def win_texto(img, d, th, j, t, D):
    window_frame(d, th, j.get("titulo", ""))
    y = WY0 + HEAD + 24
    hl = clamp01((t - float(j.get("marcar_em", 0.35)) * D) / 0.5)
    tj = clamp01((t - float(j.get("tarjar_em", 0.4)) * D) / 0.4)
    r = j.get("resumo")
    if r:
        a = ease((t - 0.15 * D) / 0.4) if j.get("resumo_animado", True) else 1
        if a > 0:
            lines = r.get("linhas", [])
            h = 76 + 52 * len(lines)
            yy = y - (1 - a) * 30
            d.rounded_rectangle([WX0 + 22, yy, WX1 - 22, yy + h], 16, fill=th.tint, outline=th.cor, width=3)
            d.text((WX0 + 46, yy + 18), r.get("titulo", "RESUMO"), font=F("Inter-ExtraBold.ttf", 24), fill=th.cor)
            for i, ln in enumerate(lines):
                k = ease((t - 0.15 * D - 0.25 - i * 0.18) / 0.3)
                if k <= 0:
                    continue
                d.ellipse([WX0 + 48, yy + 72 + i * 52, WX0 + 62, yy + 86 + i * 52], fill=th.cor)
                d.text((WX0 + 76, yy + 60 + i * 52), ln, font=F("Inter-Medium.ttf", 30), fill=th.ink)
            y += h + 22
    fa, ft = F("Inter-ExtraBold.ttf", 24), F("Inter-Medium.ttf", 32)
    for m in j.get("mensagens", []):
        if y > WY1 - 60:
            break
        if m.get("autor"):
            d.text((WX0 + 40, y), m["autor"], font=fa, fill=th.escura)
            y += 36
        lines = layout(tokens(m.get("texto", "")), ft, WX1 - WX0 - 90)
        draw_rich(d, WX0 + 40, y, lines, ft, 46, th.ink, hl=hl, tj=tj, hlcol=th.tint, hlborder=th.cor)
        y += 46 * len(lines) + 26
        d.line([WX0 + 30, y - 10, WX1 - 30, y - 10], fill=th.linha, width=2)
    # etiquetas que "pulam" no rodapé da janela
    et = j.get("etiquetas", [])
    t0 = float(j.get("etiquetas_em", 0.55)) * D
    x = WX0 + 24
    for i, e in enumerate(et):
        k = pop((t - t0 - i * 0.35) / 0.35)
        if k <= 0:
            continue
        f = F("Inter-ExtraBold.ttf", 25)
        lay = Image.new("RGBA", (int(tw(f, e) + 120), 70), (0, 0, 0, 0))
        w, h = pill(ImageDraw.Draw(lay), 4, 4, e, f, th.cor, (255, 255, 255), outline=th.escura, icon=True)
        paste_scaled(img, lay.crop((0, 0, int(w) + 8, int(h) + 8)), x + w / 2, WY1 - 46, k)
        x += w + 18

def win_chat(img, d, th, j, t, D):
    window_frame(d, th, j.get("titulo", "assistente de IA"), dark=True)
    fp = F("JetBrainsMono-Medium.ttf", 30)
    toks = tokens(j.get("prompt", ""))
    lines = layout(toks, fp, WX1 - WX0 - 110)
    n = total_chars(toks)
    t_ini = 0.25
    cps = float(j.get("caracteres_por_segundo", 0))
    t_fim = min(D * 0.62, t_ini + n / cps) if cps else D * 0.55
    rev = int(n * clamp01((t - t_ini) / max(0.3, t_fim - t_ini)))
    resp = j.get("resposta", [])
    lh = 44
    box_h = len(lines) * lh + 40
    sent = resp and t > t_fim + 0.35
    if not sent:
        by0 = WY1 - 30 - box_h
        d.rounded_rectangle([WX0 + 26, by0, WX1 - 26, WY1 - 30], 16, fill=th.dark2, outline=th.claro_dark, width=2)
        hl = clamp01((t - t_fim - 0.2) / 0.5) if not resp else 0
        cur = draw_rich(d, WX0 + 50, by0 + 20, lines, fp, lh, (240, 238, 248), reveal=rev, hl=hl,
                        hlcol=mix(th.cor, th.dark, 0.35))
        if rev < n and int(t * 2.5) % 2 == 0:
            cx, cy = cur if cur else (WX0 + 50, by0 + 20)
            d.rectangle([cx + 3, cy + 2, cx + 6, cy + 32], fill=th.claro_dark)
    else:
        k = ease((t - t_fim - 0.35) / 0.3)
        fs = F("Inter-Medium.ttf", 27)
        small = layout(toks, fs, 620)
        bh = len(small) * 36 + 32
        y0 = WY0 + HEAD + 26 - (1 - k) * 20
        d.rounded_rectangle([WX1 - 700, y0, WX1 - 26, y0 + bh], 18, fill=th.cor)
        draw_rich(d, WX1 - 680, y0 + 14, small, fs, 36, (255, 255, 255))
        y = y0 + bh + 26
        fr = F("Inter-Medium.ttf", 30)
        for i, ln in enumerate(resp):
            kk = ease((t - t_fim - 0.8 - i * 0.45) / 0.35)
            if kk <= 0 or y > WY1 - 50:
                break
            ll = layout(tokens(ln), fr, WX1 - WX0 - 140)
            hgt = len(ll) * 42 + 26
            d.rounded_rectangle([WX0 + 26, y, WX1 - 90, y + hgt], 16, fill=th.dark2)
            draw_rich(d, WX0 + 48, y + 12, ll, fr, 42, (240, 238, 248), hl=1.0, hlcol=mix(th.cor, th.dark, 0.35))
            y += hgt + 14

def win_escrever(img, d, th, j, t, D):
    window_frame(d, th, j.get("titulo", "nova mensagem"))
    ft = F("Inter-Medium.ttf", 30)
    toks = tokens(j.get("texto", ""))
    lines = layout(toks, ft, WX1 - WX0 - 100)
    n = total_chars(toks)
    t_fim = D * 0.7
    rev = int(n * clamp01((t - 0.3) / (t_fim - 0.3)))
    cur = draw_rich(d, WX0 + 46, WY0 + HEAD + 34, lines, ft, 46, th.ink, reveal=rev,
                    hl=clamp01((t - t_fim) / 0.5), hlcol=th.clara)
    if rev < n and int(t * 2.5) % 2 == 0:
        cx, cy = cur if cur else (WX0 + 46, WY0 + HEAD + 34)
        d.rectangle([cx + 3, cy + 2, cx + 6, cy + 36], fill=th.cor)
    k = 1 + 0.08 * math.sin(max(0, t - t_fim) * 8) * (1 if t > t_fim else 0)
    f = F("Inter-ExtraBold.ttf", 28)
    lab = j.get("botao", "Enviar")
    lay = Image.new("RGBA", (int(tw(f, lab) + 80), 80), (0, 0, 0, 0))
    w, h = pill(ImageDraw.Draw(lay), 4, 4, lab, f, th.cor, (255, 255, 255), outline=th.escura)
    paste_scaled(img, lay.crop((0, 0, int(w) + 8, int(h) + 8)), WX0 + 40 + w / 2, WY1 - 60, k)

def win_cartao(img, d, th, j, t, D):
    if j.get("fundo_lista"):
        win_lista(img, d, th, j["fundo_lista"], D, D)
    k = pop((t - 0.2) / 0.45)
    if k <= 0:
        return
    cw = 820
    ft = F("Inter-Black.ttf", 44)
    fx = F("Inter-Medium.ttf", 27)
    tl = layout(tokens(j.get("titulo", "")), ft, cw - 80)
    xl = layout(tokens(j.get("texto", "")), fx, cw - 80)
    h = 40 + (80 if j.get("selo") else 0) + len(tl) * 54 + 16 + len(xl) * 38 + (56 if j.get("fonte") else 20) + 20
    lay = Image.new("RGBA", (cw + 30, int(h) + 30), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([14, 14, cw + 14, h + 14], 24, fill=th.escura)
    ld.rounded_rectangle([0, 0, cw, h], 24, fill=th.bg, outline=th.ink, width=3)
    y = 36
    if j.get("selo"):
        pill(ld, 40, y, j["selo"], F("Inter-ExtraBold.ttf", 26), th.cor, (255, 255, 255), padx=20, pady=10)
        y += 80
    draw_rich(ld, 40, y, tl, ft, 54, th.ink, emcol=th.cor)
    y += len(tl) * 54 + 16
    draw_rich(ld, 40, y, xl, fx, 38, th.cinza)
    y += len(xl) * 38 + 16
    if j.get("fonte"):
        ld.text((40, y), j["fonte"], font=F("Inter-Medium.ttf", 21), fill=th.cinza)
    paste_scaled(img, lay, (WX0 + WX1) / 2 + 8, (WY0 + WY1) / 2, k)

def win_planilha(img, d, th, j, t, D):
    window_frame(d, th, j.get("titulo", "planilha"))
    cols = j.get("colunas", [])
    rows = j.get("linhas", [])
    fb, fr, fm = F("Inter-ExtraBold.ttf", 28), F("Inter-Medium.ttf", 29), F("JetBrainsMono-Medium.ttf", 28)
    # barra de fórmula
    y = WY0 + HEAD + 18
    fo = j.get("formula", "")
    if not fo:
        y -= 80
    else:
        d.rounded_rectangle([WX0 + 24, y, WX1 - 24, y + 56], 10, fill=th.tint, outline=th.linha, width=2)
    t_fim = D * (0.5 if fo else 0.3)
    if fo:
        d.text((WX0 + 40, y + 12), "fx", font=F("Inter-ExtraBold.ttf", 26), fill=th.cor)
        rev = int(len(fo) * clamp01((t - 0.3) / (t_fim - 0.3)))
        d.text((WX0 + 90, y + 13), fo[:rev], font=fm, fill=th.ink)
        if rev < len(fo) and int(t * 2.5) % 2 == 0:
            cx = WX0 + 90 + tw(fm, fo[:rev])
            d.rectangle([cx + 3, y + 12, cx + 6, y + 44], fill=th.cor)
    y += 80
    nc = max(1, len(cols))
    cw = (WX1 - WX0 - 48) / nc
    rh = 74
    dc = j.get("coluna_destaque")
    rev_last = j.get("revelar_ultima", True)
    kcol = clamp01((t - t_fim) / 0.4)
    if dc is not None and kcol > 0:
        d.rectangle([WX0 + 24 + dc * cw, y, WX0 + 24 + (dc + 1) * cw, y + rh * (len(rows) + 1)],
                    fill=mix(th.bg, th.clara, kcol))
    for ci, c in enumerate(cols):
        d.text((WX0 + 36 + ci * cw, y + 20), c, font=fb, fill=th.escura)
    d.line([WX0 + 24, y + rh, WX1 - 24, y + rh], fill=th.ink, width=2)
    for ri, r in enumerate(rows):
        yy = y + rh * (ri + 1)
        for ci, v in enumerate(r):
            last = ci == len(r) - 1
            if last and rev_last:
                kk = ease((t - t_fim - 0.2 - ri * 0.15) / 0.3)
                if kk <= 0:
                    continue
            d.text((WX0 + 36 + ci * cw, yy + 20), str(v), font=fr, fill=th.ink)
        d.line([WX0 + 24, yy + rh, WX1 - 24, yy + rh], fill=th.linha, width=2)
    for ci in range(1, nc):
        d.line([WX0 + 24 + ci * cw, y, WX0 + 24 + ci * cw, y + rh * (len(rows) + 1)], fill=th.linha, width=2)

def win_final(img, d, th, j, t, D, brand, mascote):
    k = pop((t - 0.1) / 0.45)
    if k <= 0:
        return
    cw, ch = 820, 520
    lay = Image.new("RGBA", (cw + 30, ch + 30), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rounded_rectangle([14, 14, cw + 14, ch + 14], 28, fill=th.escura)
    ld.rounded_rectangle([0, 0, cw, ch], 28, fill=th.bg, outline=th.ink, width=3)
    cx = cw // 2
    ld.ellipse([cx - 90, 40, cx + 90, 220], fill=th.tint, outline=th.cor, width=5)
    if mascote is not None:
        m = mascote.copy()
        m.thumbnail((140, 140))
        lay.alpha_composite(m, (cx - m.width // 2, 130 - m.height // 2))
    else:
        ini = (brand.get("nome") or brand.get("arroba", "@?").lstrip("@") or "?")[0].upper()
        f = F("Inter-Black.ttf", 90)
        ld.text((cx - tw(f, ini) / 2, 72), ini, font=f, fill=th.cor)
    ar = brand.get("arroba", "@seuperfil")
    f1 = F("Inter-Black.ttf", 46)
    ld.text((cx - tw(f1, ar) / 2, 246), ar, font=f1, fill=th.ink)
    bio = j.get("bio", brand.get("bio", ""))
    if bio:
        f2 = F("Inter-Medium.ttf", 27)
        bl = layout(tokens(bio), f2, cw - 120)[:2]
        for i, line in enumerate(bl):
            s = " ".join(w for _, w, _, _ in line)
            ld.text((cx - tw(f2, s) / 2, 312 + i * 36), s, font=f2, fill=th.cinza)
    t_click = float(j.get("clique_em", 0.45)) * D
    done = t >= t_click
    f3 = F("Inter-ExtraBold.ttf", 34)
    lab = "Seguindo" if done else j.get("botao", "Seguir")
    bw = tw(f3, lab) + 120 + (40 if done else 0)
    bx, by = cx - bw / 2, 410
    if done:
        ld.rounded_rectangle([bx, by, bx + bw, by + 76], 38, fill=th.bg, outline=th.cor, width=4)
        check(ld, bx + 50, by + 24, 28, th.cor, 5)
        ld.text((bx + 96, by + 16), lab, font=f3, fill=th.cor)
    else:
        ld.rounded_rectangle([bx, by, bx + bw, by + 76], 38, fill=th.cor)
        ld.text((bx + 60, by + 16), lab, font=f3, fill=(255, 255, 255))
    ox, oy = (WX0 + WX1) / 2 - cw / 2, (WY0 + WY1) / 2 - ch / 2
    paste_scaled(img, lay, (WX0 + WX1) / 2 + 8, (WY0 + WY1) / 2, k)
    # toque no botão
    dt = t - t_click
    if -0.6 < dt < 0.6:
        px, py = ox + cx + bw / 2 - 20, oy + by + 62
        if dt < 0:
            px += -dt * 260
            py += -dt * 200
        d.ellipse([px - 26, py - 26, px + 26, py + 26], fill=mix(th.cor, (255, 255, 255), 0.5),
                  outline=th.escura, width=3)
        if dt > 0:
            r = 26 + dt * 120
            d.ellipse([px - r, py - r, px + r, py + r], outline=th.cor, width=4)

# ---------------- extras de cena
def extra_nota(img, th, n, t, D):
    k = pop((t - float(n.get("em", 0.3)) * D) / 0.4)
    if k <= 0:
        return
    f1, f2 = F("Inter-Black.ttf", 40), F("Inter-ExtraBold.ttf", 24)
    tl = layout(tokens(n.get("texto", "")), f1, 330)
    h = 50 + len(tl) * 48 + (40 if n.get("sub") else 0)
    lay = Image.new("RGBA", (420, int(h) + 30), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lay)
    ld.rectangle([14, 14, 404, h + 14], fill=th.escura)
    ld.rectangle([0, 0, 390, h], fill=th.clara, outline=th.ink, width=3)
    draw_rich(ld, 28, 26, tl, f1, 48, th.ink)
    if n.get("sub"):
        ld.text((28, 26 + len(tl) * 48 + 4), n["sub"], font=f2, fill=th.escura)
    lay = lay.rotate(4, expand=True, resample=Image.BICUBIC)
    paste_scaled(img, lay, WX1 - 190, WY1 - 120, k)

def extra_pilula(img, th, p, t, D):
    k = pop((t - float(p.get("em", 0.3)) * D) / 0.35)
    if k <= 0:
        return
    f = F("Inter-ExtraBold.ttf", 27)
    lay = Image.new("RGBA", (int(tw(f, p["texto"]) + 80), 80), (0, 0, 0, 0))
    w, h = pill(ImageDraw.Draw(lay), 4, 4, p["texto"], f, th.cor, (255, 255, 255), outline=th.escura)
    y = WY0 + (WY1 - WY0) * float(p.get("y", 0.35))
    paste_scaled(img, lay.crop((0, 0, int(w) + 8, int(h) + 8)), (WX0 + WX1) / 2, y, k)

# ---------------- moldura da cena
def draw_header(img, d, th, sc, i, n, t):
    # barra de progresso
    seg = (WX1 - WX0 - (n - 1) * 12) / n
    for s in range(n):
        x0 = WX0 + s * (seg + 12)
        col = th.cor if s <= i else th.linha
        d.rounded_rectangle([x0, 262, x0 + seg, 272], 5, fill=col)
    # selo
    a = ease(t / 0.3)
    selo = str(sc.get("selo", i + 1))
    cx, cy, r = WX0 + 44, 360, 42
    d.ellipse([cx - r + 4, cy - r + 6, cx + r + 4, cy + r + 6], fill=th.escura)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=th.cor, outline=th.escura, width=4)
    if selo in ("✓", "ok", "check"):
        check(d, cx - 18, cy - 16, 36, (255, 255, 255), 7)
    else:
        f = F("Inter-Black.ttf", 46 if len(selo) < 3 else 30)
        d.text((cx - tw(f, selo) / 2, cy - 30), selo, font=f, fill=(255, 255, 255))
    # título
    toks = tokens(sc.get("titulo", ""))
    for size in (64, 58, 52, 46):
        ft = F("Inter-Black.ttf", size)
        lines = layout(toks, ft, WX1 - (cx + r + 26))
        if len(lines) <= 2:
            break
    lh = int(size * 1.02)
    ty = cy - (len(lines) * lh) / 2 - 4 + (1 - a) * 16
    draw_rich(d, cx + r + 24, ty, lines, ft, lh, th.ink, emcol=th.cor)
    if sc.get("exemplo"):
        f = F("Inter-ExtraBold.ttf", 19)
        s = "EXEMPLO ILUSTRATIVO"
        x = WX1 - 4 - sum(tw(f, c) + 2 for c in s)
        for c in s:
            d.text((x, 520), c, font=f, fill=th.cinza)
            x += tw(f, c) + 2

def draw_caption(d, th, groups, times, t):
    """times: lista de (inicio, fim) por palavra, no tempo da cena."""
    if not groups:
        return
    idx = 0
    flat = [w for g in groups for w in g]
    cur = -1
    for k, (a, b) in enumerate(times):
        if t >= a:
            cur = k
    if cur < 0:
        return
    # grupo atual
    acc = 0
    for gi, g in enumerate(groups):
        if cur < acc + len(g):
            idx = gi
            break
        acc += len(g)
    g = groups[idx]
    f = F("Inter-ExtraBold.ttf", 56)
    lines = layout([(w, None) for w in g], f, 880)
    y0 = 1352 - (len(lines) * 68) / 2
    k = acc
    for li, line in enumerate(lines):
        lw = line[-1][0] + line[-1][3]
        x0 = (W - lw) / 2
        for (ox, w, _, ww) in line:
            col = th.cor if k == cur else (th.ink if k < cur else th.futura)
            d.text((x0 + ox, y0 + li * 68), w, font=f, fill=col)
            k += 1

def word_times(groups, D):
    words = [w for g in groups for w in g]
    if not words:
        return []
    a, b = 0.15, max(0.6, D - 0.35)
    ws = [word_weight(w) for w in words]
    tot = sum(ws)
    out, t = [], a
    for w in ws:
        dt = (b - a) * w / tot
        out.append((t, t + dt))
        t += dt
    return out

# ------------------------------------------------------------------ cena -> quadro
class Scene:
    def __init__(self, sc, i, n, D, th, brand, mascote):
        self.sc, self.i, self.n, self.D, self.th, self.brand, self.mascote = sc, i, n, D, th, brand, mascote
        self.groups = caption_groups(sc.get("narracao", ""))
        self.times = word_times(self.groups, D)

    def frame(self, t):
        th, sc = self.th, self.sc
        img = Image.new("RGBA", (W, H), th.bg + (255,))
        d = ImageDraw.Draw(img)
        draw_header(img, d, th, sc, self.i, self.n, t)
        j = sc.get("janela", {"tipo": "cartao"})
        tipo = j.get("tipo", "cartao")
        fn = {"lista": win_lista, "texto": win_texto, "chat": win_chat, "escrever": win_escrever,
              "cartao": win_cartao, "planilha": win_planilha}.get(tipo)
        if tipo == "final":
            win_final(img, d, th, j, t, self.D, self.brand, self.mascote)
        elif fn:
            fn(img, d, th, j, t, self.D)
        else:
            raise SystemExit(f"Tipo de janela desconhecido: {tipo}")
        if sc.get("nota"):
            extra_nota(img, th, sc["nota"], t, self.D)
        if sc.get("pilula"):
            extra_pilula(img, th, sc["pilula"], t, self.D)
        draw_caption(d, th, self.groups, self.times, t)
        if self.mascote is not None:
            m = self.mascote
            bob = 6 * math.sin(t * 2.4)
            img.alpha_composite(m, (64, int(1518 - m.height / 2 + bob)))
        return img.convert("RGB")

# ------------------------------------------------------------------ áudio
SR = 44100

def synth_music(total, starts, typing):
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    chords = [[261.63, 329.63, 392.0], [220.0, 261.63, 329.63], [174.61, 220.0, 261.63], [196.0, 246.94, 293.66]]
    seg = 4.0
    for ci in range(int(total / seg) + 1):
        a, b = ci * seg, min(total, ci * seg + seg + 0.6)
        ia, ib = int(a * SR), int(b * SR)
        if ia >= n:
            break
        tt = t[ia:ib] - a
        env = np.minimum(1, tt / 0.8) * np.minimum(1, np.maximum(0, (b - a - tt)) / 0.8)
        for f in chords[ci % 4]:
            out[ia:ib] += env * (0.5 * np.sin(2 * np.pi * f * tt) + 0.12 * np.sin(4 * np.pi * f * tt))
    out *= 0.045
    out *= np.minimum(1, t / 1.5) * np.minimum(1, (total - t) / 1.5)
    for s in starts[1:]:
        i0 = int(s * SR)
        L = int(0.09 * SR)
        if i0 + L < n:
            tt = np.arange(L) / SR
            f = 880 - 2200 * tt
            out[i0:i0 + L] += 0.10 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 40)
    rng = np.random.default_rng(1)
    for s in typing:
        i0 = int(s * SR)
        L = int(0.012 * SR)
        if i0 + L < n:
            out[i0:i0 + L] += 0.03 * rng.standard_normal(L) * np.exp(-np.arange(L) / (L / 4))
    return out

def read_audio(ff, path, workdir):
    wav = os.path.join(workdir, "_narracao.wav")
    subprocess.run([ff, "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", str(SR), wav], check=True)
    with wave.open(wav) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    return data

def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())

def typing_moments(spec, durs, starts):
    out = []
    for sc, D, s in zip(spec["cenas"], durs, starts):
        j = sc.get("janela", {})
        if j.get("tipo") in ("chat", "escrever", "planilha"):
            a, b = s + 0.3, s + D * (0.55 if j["tipo"] != "escrever" else 0.7)
            out += list(np.arange(a, b, 0.11))
    return out

# ------------------------------------------------------------------ principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro")
    ap.add_argument("--out", default="saida_reel")
    ap.add_argument("--preview", help="tempos em segundos, separados por vírgula")
    ap.add_argument("--audio", help="narração gravada (mp3, m4a, wav...)")
    ap.add_argument("--sem-musica", action="store_true")
    ap.add_argument("--nome", default="reel")
    a = ap.parse_args()

    spec = json.load(open(a.roteiro, encoding="utf-8"))
    os.makedirs(a.out, exist_ok=True)
    brand = spec.get("marca", {})
    th = Theme(brand)
    mascote = None
    mp = brand.get("mascote")
    if mp:
        if not os.path.isabs(mp):
            mp = os.path.join(os.path.dirname(os.path.abspath(a.roteiro)), mp)
        if os.path.exists(mp):
            mascote = Image.open(mp).convert("RGBA")
            mascote.thumbnail((140, 140))
        else:
            print(f"AVISO: mascote não encontrado em {mp}; seguindo sem ele.")

    ff = None
    voice = None
    if a.audio or not a.preview:
        ff = ffmpeg_bin()
    if a.audio:
        voice = read_audio(ff, a.audio, a.out)
    durs, starts = plan_times(spec, len(voice) / SR if voice is not None else None)
    total = sum(durs)
    scenes = [Scene(sc, i, len(spec["cenas"]), D, th, brand, mascote) for i, (sc, D) in enumerate(zip(spec["cenas"], durs))]

    # tempos e guia de narração
    with open(os.path.join(a.out, "tempos.txt"), "w", encoding="utf-8") as f:
        for i, (sc, s, D) in enumerate(zip(spec["cenas"], starts, durs)):
            f.write(f"Cena {i + 1}: {s:5.1f}s a {s + D:5.1f}s ({D:.1f}s) · {plain(sc.get('titulo', ''))}\n")
        f.write(f"Total: {total:.1f}s\n")
    with open(os.path.join(a.out, "guia-narracao.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(sc.get("narracao", "") for sc in spec["cenas"]) + "\n")
    print(open(os.path.join(a.out, "tempos.txt"), encoding="utf-8").read())

    if a.preview:
        ims = []
        for ts in [float(x) for x in a.preview.split(",")]:
            i = max(k for k in range(len(starts)) if starts[k] <= ts)
            im = scenes[i].frame(ts - starts[i])
            p = os.path.join(a.out, f"previa_{ts:05.1f}s.png")
            im.save(p)
            ims.append(im)
        cols = min(4, len(ims))
        rows = math.ceil(len(ims) / cols)
        g = Image.new("RGB", (cols * 360, rows * 640), "white")
        for k, im in enumerate(ims):
            g.paste(im.resize((360, 640)), ((k % cols) * 360, (k // cols) * 640))
        g.save(os.path.join(a.out, "previa_grade.jpg"), quality=88)
        print("Prévia salva em", a.out)
        return

    # render: um arquivo por cena, com a transição dentro do arquivo
    parts = []
    prev_last = None
    for i, scn in enumerate(scenes):
        nfr = int(round((starts[i] + durs[i]) * FPS)) - int(round(starts[i] * FPS))
        tmp = os.path.join(a.out, f"_cena{i:02d}.tmp.mp4")
        fin = os.path.join(a.out, f"_cena{i:02d}.mp4")
        p = subprocess.Popen([ff, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                              "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                              "-pix_fmt", "yuv420p", "-r", str(FPS), tmp], stdin=subprocess.PIPE)
        last = None
        for fr in range(nfr):
            t = fr / FPS
            im = scn.frame(t)
            if prev_last is not None and t < 0.25:
                im = Image.blend(prev_last, im, ease(t / 0.25))
            p.stdin.write(im.tobytes())
            last = im
        p.stdin.close()
        if p.wait() != 0:
            sys.exit(f"ERRO ao gerar a cena {i + 1}")
        os.replace(tmp, fin)
        parts.append(fin)
        prev_last = last
        print(f"cena {i + 1}/{len(scenes)} pronta", flush=True)

    lst = os.path.join(a.out, "_lista.txt")
    with open(lst, "w") as f:
        for pth in parts:
            f.write(f"file '{os.path.abspath(pth)}'\n")
    video = os.path.join(a.out, "_video.mp4")
    subprocess.run([ff, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video], check=True)

    n = int(total * SR)
    mixw = np.zeros(n)
    if not a.sem_musica:
        mixw += synth_music(total, starts, typing_moments(spec, durs, starts)) * (0.45 if voice is not None else 1.0)
    if voice is not None:
        m = min(n, len(voice))
        mixw[:m] += voice[:m]
    peak = np.max(np.abs(mixw)) if n else 0
    if peak > 0.89:
        mixw *= 0.89 / peak
    nome = a.nome + ("-com-voz" if voice is not None else "-sem-voz")
    final = os.path.join(a.out, nome + ".mp4")
    tmpf = final[:-4] + ".tmp.mp4"
    if peak > 0:
        wav = os.path.join(a.out, "_mix.wav")
        write_wav(wav, mixw)
        subprocess.run([ff, "-v", "error", "-y", "-i", video, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmpf], check=True)
    else:
        subprocess.run([ff, "-v", "error", "-y", "-i", video, "-c", "copy", "-movflags", "+faststart", tmpf], check=True)
    os.replace(tmpf, final)
    for pth in parts + [lst, video, os.path.join(a.out, "_mix.wav"), os.path.join(a.out, "_narracao.wav")]:
        if os.path.exists(pth):
            os.remove(pth)
    print("PRONTO:", final, f"({total:.1f}s)")

if __name__ == "__main__":
    main()
