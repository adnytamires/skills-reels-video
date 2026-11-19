#!/usr/bin/env python3
"""Motor do Reel: monta as cenas desenhadas (cenas.py), move a câmera devagar, anima a luz das velas,
põe legenda ou frases na tela e compõe o som ambiente.

Uso:
  python3 reel.py roteiro.json --out PASTA --preview 2,8,14     # quadros de prova (segundos)
  python3 reel.py roteiro.json --out PASTA --nome meu-reel      # vídeo (sem voz)
  python3 reel.py roteiro.json --out PASTA --audio voz.mp3      # com a narração gravada
  (--sem-trilha tira a música)
  python3 reel.py roteiro.json --out PASTA --pecas              # também entrega as peças para editar (CapCut etc.)
"""
import argparse, importlib.util, json, math, os, random, shutil, subprocess, sys, time, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from desenho import *  # noqa
import desenho as D

QPS = 24          # quadros por segundo (ritmo de cinema)
SR = 44100

def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if exe: return exe
    try: import imageio_ffmpeg
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "imageio-ffmpeg"], check=False); import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

class Prep:
    """o que desenhar_<cena>(k) recebe: k.cor (RGB da marca), k.seed"""
    def __init__(s, cor, seed): s.cor, s.seed = cor, seed

# ------------------------------------------------------------------ câmera
def camera_de(spec, D_):
    """devolve f(t) -> (cx, cy, largura_visivel) em unidades de tela"""
    cam = spec.get("camera", {}) if isinstance(spec.get("camera"), dict) else {"mov": spec.get("camera", "aproximar")}
    mov = cam.get("mov", "aproximar"); fx, fy = cam.get("foco", [CW/2, CH/2]); z0, z1 = cam.get("zoom", [1.0, 1.0])
    if "de" in cam and "para" in cam:
        a, b = cam["de"], cam["para"]
    else:
        zz = {"aproximar": (1.0, 1.14), "afastar": (1.14, 1.0), "parada": (1.05, 1.05)}.get(mov, (1.18, 1.18))
        if [z0, z1] != [1.0, 1.0]: zz = (z0, z1)
        dx = {"direita": 140, "esquerda": -140}.get(mov, 0); dy = {"descer": 220, "subir": -220}.get(mov, 0)
        a = [fx - dx, fy - dy, zz[0]]; b = [fx + dx, fy + dy, zz[1]]
    def f(t):
        k = ease(t/max(D_, 0.01)) if cam.get("suave", True) else clamp01(t/max(D_, 0.01))
        k = 0.15 + 0.85*k if mov != "parada" else k
        cx, cy, z = (lerp(a[i], b[i], k) for i in range(3)); vw = CW/max(z, 1.0); vh = vw*H/W
        return min(max(cx, vw/2), CW - vw/2), min(max(cy, vh/2), CH - vh/2), vw
    return f

# ------------------------------------------------------------------ textos na tela
def _linhas(d, palavras, f, larg):
    linhas, ln, w = [], [], 0
    for p in palavras:
        ww = d.textlength(p + " ", font=f)
        if ln and w + ww > larg: linhas.append(ln); ln, w = [], 0
        ln.append(p); w += ww
    linhas.append(ln); return linhas

def legenda(im, palavras, atual, cor_destaque, y=1380, estilo="padrao", cor_texto=(246, 244, 240)):
    """legenda palavra por palavra (modo voz): branca, palavra atual na cor de destaque.
    estilo "flat": letras grossas em caixa alta, sem contorno, com sombra suave (vídeos explicativos)"""
    if estilo == "flat":
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = fonte("titulo", 58); sp = d.textlength("  ", font=f)
        vis = [p.upper().strip("*").rstrip(".,;:") for p in palavras[:atual + 1]]; larg = sum(d.textlength(p, font=f) for p in vis) + sp*(len(vis) - 1)
        x = (W - larg)/2; sombra = Image.new("RGBA", im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sombra)
        for k, p in enumerate(vis):
            claro = sum(cor_texto) > 380
            ds.text((x, y + 5), p, font=f, fill=(0, 0, 0, 170) if claro else (255, 255, 255, 200)); d.text((x, y), p, font=f, fill=cor_destaque if k == atual else cor_texto)
            x += d.textlength(p, font=f) + sp
        im.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(6))); im.alpha_composite(lay); return
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = fonte("legenda", 54)
    linhas = _linhas(d, palavras, f, 880); k = 0
    for li, ln in enumerate(linhas):
        x = (W - d.textlength(" ".join(ln), font=f))/2
        for p in ln:
            if k <= atual:
                d.text((x, y + li*72), p, font=f, fill=cor_destaque if k == atual else (255, 255, 255), stroke_width=6, stroke_fill=(10, 10, 14, 220))
            x += d.textlength(p + " ", font=f); k += 1
    im.alpha_composite(lay)

def frase(im, txt, alfa, cor_destaque, y=1360, tam=62):
    """frase curta na tela (modo texto). *palavra* sai na cor de destaque"""
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = fonte("serif", tam)
    palavras = txt.split(); marc, limpas, dentro = [], [], False
    for p in palavras:           # *uma ou mais palavras* saem na cor de destaque
        abre = p.startswith("*"); fecha = p.rstrip(".,!?:;").endswith("*")
        marc.append(dentro or abre); dentro = (dentro or abre) and not fecha; limpas.append(p.replace("*", ""))
    linhas = _linhas(d, limpas, f, 900); k = 0
    sombra = Image.new("RGBA", im.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sombra)
    for li, ln in enumerate(linhas):
        x = (W - d.textlength(" ".join(ln), font=f))/2; yy = y + li*int(tam*1.3)
        ds.text((x, yy + 4), " ".join(ln), font=f, fill=(0, 0, 0, 200))
        for p in ln:
            d.text((x, yy), p, font=f, fill=(cor_destaque if marc[k] else (250, 246, 236)) + (255,), stroke_width=5, stroke_fill=(30, 22, 22, 235))
            x += d.textlength(p + " ", font=f); k += 1
    sombra = sombra.filter(ImageFilter.GaussianBlur(8))
    a = np.asarray(sombra, np.float32); a[..., 3] *= alfa; im.alpha_composite(Image.fromarray(a.astype(np.uint8)))
    a = np.asarray(lay, np.float32); a[..., 3] *= alfa; im.alpha_composite(Image.fromarray(a.astype(np.uint8)))

def titulo(im, txt, alfa, y=820):
    lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay); f = fonte("serif", 92)
    for li, ln in enumerate(txt.split("|")):
        d.text((W/2, y + li*110), ln, font=f, fill=(246, 240, 228, 255), anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 160))
    a = np.asarray(lay, np.float32); a[..., 3] *= alfa; im.alpha_composite(Image.fromarray(a.astype(np.uint8)))

def tempos_palavras(palavras, D_):
    if not palavras: return np.array([])
    pesos = [len(p) + 3 + (7 if p.endswith("...") else 5 if p[-1] in ".?!" else 3 if p[-1] in ",:;" else 0) for p in palavras]
    a, b = 0.15, max(0.8, D_ - 0.35)
    return np.cumsum([0] + pesos[:-1])/sum(pesos)*(b - a) + a

def grupos(palavras, n=7):
    gs, g = [], []
    for p in palavras:
        g.append(p)
        if len(g) >= n or p[-1] in ".?!:": gs.append(g); g = []
    if g:
        if gs and len(g) <= 2: gs[-1] += g
        else: gs.append(g)
    return gs

# ------------------------------------------------------------------ cena
class Quadro:
    def __init__(s, spec, D_, mod, marca, seed, cache, modo, legenda_on):
        s.s, s.D, s.mod, s.marca, s.seed, s.cache, s.modo, s.leg = spec, D_, mod, marca, seed, cache, modo, legenda_on
        s.nome = spec["cena"]; s.cam = camera_de(spec, D_)
        s.f_des = getattr(mod, "desenhar_" + s.nome, None); s.f_anim = getattr(mod, "animar_" + s.nome, None)
        if not s.f_des: sys.exit(f"ERRO: cenas.py não tem desenhar_{s.nome}")
        s.palavras = (spec.get("narracao") or "").split(); s.tw = tempos_palavras(s.palavras, D_); s.estilo_txt = "padrao"
        s.gs = grupos(s.palavras)
    def preparar(s):
        if s.nome not in s.cache:
            t0 = time.time(); c = s.f_des(Prep(s.marca["cor_rgb"], s.seed))
            if not isinstance(c, D.Cena): sys.exit(f"ERRO: desenhar_{s.nome} precisa devolver a Cena (c)")
            base, trem, chamas = c.iluminar()
            s.cache[s.nome] = dict(base=base, trem=trem, chamas=chamas, dados=c.dados)
            print(f"  cena '{s.nome}' desenhada em {time.time() - t0:.1f}s", flush=True)
        return s.cache[s.nome]
    def quadro(s, t, ultimo=False, bruto=False):
        P = s.preparar(); x = P["base"]
        if P["trem"]:
            k = 1 + 0.09*math.sin(t*7.3 + s.seed) + 0.05*math.sin(t*17.1) + random.Random(int(t*12) + s.seed).uniform(-0.04, 0.04)
            x = x + sum(tr for tr in P["trem"])*k
        x = x*1.3/(1 + 0.3*x)*0.975        # curva suave: o branco continua branco, o brilho forte não estoura
        im = Image.fromarray((np.clip(x, 0, 1)*255).astype(np.uint8)).convert("RGBA")
        for i, ch in enumerate(P["chamas"]): desenhar_chama(im, ch, t, seed=i + s.seed)
        if s.f_anim: s.f_anim(im, t, s.D, P["dados"])
        if bruto: return im        # tela inteira, sem câmera e sem texto (peça para edição)
        cx, cy, vw = s.cam(t); vh = vw*H/W
        im = im.crop((int(cx - vw/2), int(cy - vh/2), int(cx - vw/2 + vw), int(cy - vh/2 + vh))).resize((W, H), Image.BILINEAR)
        cor = s.marca["destaque"]
        if s.s.get("titulo"):
            a = clamp01(t/0.6)*clamp01((min(s.D, 3.2) - t)/0.6); titulo(im, s.s["titulo"], a) if a > 0 else None
        if s.modo == "texto" and s.s.get("texto"):
            a = clamp01((t - 0.3)/0.5)*clamp01((s.D - 0.2 - t)/0.5)
            if a > 0: frase(im, s.s["texto"], a, cor)
        if s.modo == "voz" and s.leg and s.s.get("legenda", True) and len(s.tw):
            cur = int(np.searchsorted(s.tw, t, side="right")) - 1
            if cur >= 0:
                acc = 0
                for g in s.gs:
                    if cur < acc + len(g): legenda(im, g, cur - acc, cor, 1480 if s.estilo_txt == "flat" else 1380, s.estilo_txt, s.cor_texto); break
                    acc += len(g)
        if ultimo and s.marca.get("arroba"):
            a = clamp01((t - 0.5)/0.6)
            if a > 0:
                lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).text((W/2, 1560), s.marca["arroba"], font=fonte("legenda", 44), fill=(246, 240, 228, int(230*a)), anchor="mm")
                im.alpha_composite(lay)
        return im

# ------------------------------------------------------------------ acabamento do quadro (vinheta e grão)
_VIN = None; VINHETA = 0.42; _GRAO = [np.random.default_rng(k).normal(0, 1.4, (H, W, 1)).astype(np.float32) for k in range(4)]
def acabar(im, n):
    """vinheta e um grão de filme leve (muda a cada 3 quadros, para o arquivo não ficar pesado)"""
    global _VIN
    if _VIN is None:
        yy, xx = np.mgrid[0:H, 0:W]; r = np.sqrt(((xx - W/2)/(W/2))**2 + ((yy - H/2)/(H/2))**2)
        _VIN = (1 - VINHETA*np.clip(r - 0.5, 0, 1)**1.3)[..., None].astype(np.float32)
    a = np.asarray(im.convert("RGB"), np.float32)*_VIN
    a += _GRAO[(n // 3) % 4]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

# ------------------------------------------------------------------ som
def _env(L, ataque=0.005, queda=4.0):
    t = np.arange(L)/SR; return np.minimum(1, t/ataque)*np.exp(-t*queda)
def _ruido(L, seed, suav=1):
    r = np.random.default_rng(seed).standard_normal(L)
    return np.convolve(r, np.ones(suav)/suav, "same") if suav > 1 else r
def _nota(f, dur, decai=3.0, brilho=1.5):
    t = np.arange(int(dur*SR))/SR; x = sum(np.sin(2*np.pi*f*k*t)*np.exp(-t*decai*k*0.7)/k**brilho for k in range(1, 6))
    return x*np.minimum(1, t/0.006)
def _eco(x, atraso=0.23, ganho=0.28):
    d = int(atraso*SR); y = x.copy(); y[d:] += x[:-d]*ganho; y[2*d:] += x[:-2*d]*ganho*0.5; return y
def musica(tipo, total):
    """trilha gerada que acompanha a história: alegre, calma, tensa, misterio ou nenhuma"""
    n = int(total*SR); out = np.zeros(n + 4*SR)
    if tipo in (None, "nenhuma"): return out[:n]
    def add(at, x, v):
        a = int(at*SR); m = min(len(x), len(out) - a)
        if m > 0: out[a:a + m] += x[:m]*v
    hz = lambda m: 440*2**((m - 69)/12)
    if tipo == "alegre":   # dedilhado claro em dó maior, baixo nos tempos e chocalho leve
        bpm = 104; b = 60/bpm; acordes = [[60, 64, 67, 72], [55, 59, 62, 67], [57, 60, 64, 69], [53, 57, 60, 65]]
        padrao = [0, 1, 2, 3, 2, 1, 2, 3]; k = 0; t = 0.0
        while t < total:
            ac = acordes[(k//8) % 4]
            add(t, _nota(hz(ac[padrao[k % 8]] + 12), b*1.6, 4.0, 1.8), 0.075)
            if k % 4 == 0: add(t, _nota(hz(ac[0] - 12), b*2.5, 2.2, 2.2), 0.11)
            if k % 2 == 1: L = int(0.05*SR); add(t, np.random.default_rng(k).standard_normal(L)*np.exp(-np.arange(L)/SR*80), 0.025)
            t += b/2; k += 1
    elif tipo == "calma":  # acordes lentos de piano
        b = 60/68; acordes = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 65]]; t = 0.0; k = 0
        while t < total:
            for i, m in enumerate(acordes[k % 4]): add(t + i*0.06, _nota(hz(m), b*4.5, 0.9, 2.0), 0.06)
            add(t + b*2, _nota(hz(acordes[k % 4][2] + 12), b*2, 1.4, 2.0), 0.04); t += b*4; k += 1
    elif tipo == "misterio":   # arpejo menor espaçado
        b = 60/80; ac = [57, 60, 64, 71, 64, 60]; t = 0.0; k = 0
        while t < total: add(t, _nota(hz(ac[k % 6] + (12 if k % 12 > 5 else 0)), b*2, 1.6, 1.8), 0.065); t += b; k += 1
    else:   # tensa: grave contínuo com pulsos
        tt = np.arange(n)/SR
        out[:n] += (0.05*np.sin(2*np.pi*55*tt) + 0.03*np.sin(2*np.pi*82.4*tt))*(0.7 + 0.3*np.sin(2*np.pi*0.1*tt))
        for at in np.arange(0, total, 60/90*2): add(at, _nota(55, 0.6, 5, 2.5), 0.12)
    out = _eco(out)[:n]; tt = np.arange(n)/SR
    return out*np.minimum(1, tt/1.0)*np.clip((total - tt)/1.8, 0, 1)
def estalos_vela(total):
    n = int(total*SR); out = np.zeros(n + SR); rng = np.random.default_rng(5)
    for at in np.cumsum(rng.exponential(0.6, int(total*3))):
        if at >= total: break
        a = int(at*SR); L = int(0.02*SR); out[a:a + L] += _ruido(L, int(at*1000))*_env(L, 0.001, 200)*0.05
    return out[:n]
def efeitos(total, cenas, starts, durs):
    n = int(total*SR) + 3*SR; out = np.zeros(n)
    def add(at, s):
        a = max(0, int(at*SR)); out[a:a + len(s)] += s[:max(0, n - a)]
    def tom(at):
        L = int(2.2*SR); t = np.arange(L)/SR; add(at, np.sin(2*np.pi*(48 - 8*t)*t)*_env(L, 0.02, 1.6)*0.35)
    def porta(at):
        L = int(0.9*SR); t = np.arange(L)/SR; add(at, (np.sin(2*np.pi*70*t)*0.4 + _ruido(L, 3, 8)*0.25)*_env(L, 0.002, 6))
        for k in range(5): add(at + 0.08 + k*0.07, _ruido(int(0.05*SR), 10 + k)*_env(int(0.05*SR), 0.001, 60)*0.12)
    def batida(at):
        for k in range(3):
            L = int(0.25*SR); t = np.arange(L)/SR; add(at + k*0.32, (np.sin(2*np.pi*120*t) + _ruido(L, 20 + k, 4)*0.5)*_env(L, 0.001, 22)*0.3)
    def passos(at):
        for k in range(6):
            L = int(0.18*SR); add(at + k*0.45, _ruido(L, 30 + k, 12)*_env(L, 0.002, 26)*0.35)
    def caneta(at):
        for k in range(4):
            L = int(0.35*SR); t = np.arange(L)/SR; add(at + k*0.42, _ruido(L, 40 + k, 3)*(0.5 + 0.5*np.sin(2*np.pi*18*t))*_env(L, 0.02, 4)*0.09)
    def papel(at):
        L = int(0.3*SR); add(at, _ruido(L, 50, 6)*_env(L, 0.01, 10)*0.08)
    def vento(at):
        L = int(4*SR); t = np.arange(L)/SR; add(at, _ruido(L, 60, 40)*np.sin(np.pi*t/4)**2*0.25)
    def sino(at):
        L = int(2.5*SR); t = np.arange(L)/SR; add(at, (np.sin(2*np.pi*660*t) + 0.4*np.sin(2*np.pi*1320*t))*_env(L, 0.005, 1.8)*0.07)
    F = dict(tom=tom, porta=porta, batida=batida, passos=passos, caneta=caneta, papel=papel, vento=vento, sino=sino)
    for c, s0, D_ in zip(cenas, starts, durs):
        for e in c.get("sons", []):
            fn = F.get(e.get("tipo"))
            if fn:
                for k in range(int(e.get("vezes", 1))): fn(s0 + D_*float(e.get("em", 0.2)) + k*float(e.get("intervalo", 0.5)))
    return out[:int(total*SR)]
def ler_audio(ff, path, pasta):
    wav = os.path.join(pasta, "_narracao.wav")
    subprocess.run([ff, "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", str(SR), wav], check=True)
    with wave.open(wav) as w: x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64)/32768
    os.remove(wav); return x

# ------------------------------------------------------------------ principal
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("roteiro"); ap.add_argument("--out", default="saida"); ap.add_argument("--preview")
    ap.add_argument("--audio"); ap.add_argument("--sem-trilha", action="store_true"); ap.add_argument("--nome", default="reel")
    ap.add_argument("--pecas", action="store_true", help="entrega também cenas soltas, imagens, som e legenda .srt para editar")
    a = ap.parse_args()
    spec = json.load(open(a.roteiro, encoding="utf-8")); base = os.path.dirname(os.path.abspath(a.roteiro)); os.makedirs(a.out, exist_ok=True)
    marca = dict(spec.get("marca", {})); marca["cor_rgb"] = hex2rgb(marca.get("cor", "#F2B44C"))
    marca["destaque"] = mistura(marca["cor_rgb"], (255, 255, 255), 0.25) if not spec.get("cor_texto") else marca["cor_rgb"]
    modo = spec.get("modo", "voz"); leg = spec.get("legenda", True)
    global VINHETA
    if spec.get("cor_texto") and sum(hex2rgb(spec["cor_texto"])) < 380: VINHETA = 0.08     # fundo claro: quase sem vinheta
    VINHETA = float(spec.get("vinheta", VINHETA))
    if modo not in ("voz", "texto"): sys.exit('ERRO: "modo" deve ser "voz" ou "texto"')
    cp = os.path.join(base, spec.get("cenas_py", "cenas.py"))
    sp = importlib.util.spec_from_file_location("cenas_usuario", cp); mod = importlib.util.module_from_spec(sp); sp.loader.exec_module(mod)
    cenas = spec["cenas"]; wps = float(spec.get("palavras_por_segundo", 2.3))
    def dur(c):
        if c.get("duracao"): return float(c["duracao"])
        if modo == "voz": return max(3.0, len((c.get("narracao") or "").split())/wps + 0.7)
        return max(3.2, len((c.get("texto") or "").split())/2.2 + 1.6)
    durs = [dur(c) for c in cenas]
    ff = ffmpeg_bin() if (a.audio or not a.preview) else None; voz = None
    if a.audio:
        voz = ler_audio(ff, a.audio, a.out); L = len(voz)/SR; marks = spec.get("marcas_audio")
        if marks and len(marks) == len(cenas):
            ends = [float(m) for m in marks[1:]] + [L + 0.8]; durs = [max(1.0, e - float(s)) for s, e in zip(marks, ends)]
        else:
            k = (L + 0.8)/sum(durs); durs = [d*k for d in durs]
    starts = list(np.cumsum([0] + durs[:-1])); total = sum(durs); cache = {}
    objs = [Quadro(c, d, mod, marca, i + 1, cache, modo, leg) for i, (c, d) in enumerate(zip(cenas, durs))]
    for o in objs:
        o.estilo_txt = spec.get("estilo_texto", "padrao"); o.cor_texto = hex2rgb(spec["cor_texto"]) if spec.get("cor_texto") else (246, 244, 240)
        if o.estilo_txt == "flat": o.gs = grupos(o.palavras, 3)
    with open(os.path.join(a.out, "tempos.txt"), "w", encoding="utf-8") as f:
        for i, (c, s, d) in enumerate(zip(cenas, starts, durs)): f.write(f"Cena {i + 1}: {s:5.1f}s a {s + d:5.1f}s · {c['cena']} · {c.get('texto') or c.get('narracao') or ''}\n")
        f.write(f"Total: {total:.1f}s\n")
    with open(os.path.join(a.out, "guia-narracao.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(c.get("narracao") or c.get("texto") or "" for c in cenas) + "\n")
    print(open(os.path.join(a.out, "tempos.txt"), encoding="utf-8").read(), flush=True)
    if a.preview:
        ims = []
        for ts in [float(v) for v in a.preview.split(",")]:
            i = max(k for k in range(len(starts)) if starts[k] <= ts)
            im = acabar(objs[i].quadro(min(ts - starts[i], durs[i] - 0.01), i == len(objs) - 1), 0); im.save(os.path.join(a.out, f"previa_{ts:05.1f}s.png")); ims.append(im)
        cols = min(4, len(ims)); rows = math.ceil(len(ims)/cols); g = Image.new("RGB", (cols*432, rows*768), "white")
        for k, im in enumerate(ims): g.paste(im.resize((432, 768), Image.LANCZOS), ((k % cols)*432, (k//cols)*768))
        g.save(os.path.join(a.out, "previa_grade.jpg"), quality=90); print("Prévia salva em", a.out); return
    vid = os.path.join(a.out, "_video.mp4")
    p = subprocess.Popen([ff, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(QPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", vid], stdin=subprocess.PIPE)
    nq = 0; fade_in, fade_out = 0.6, 0.8
    for i, o in enumerate(objs):
        f0 = int(round(starts[i]*QPS)); f1 = int(round((starts[i] + durs[i])*QPS))
        trans = cenas[i].get("transicao", "corte")
        for fr in range(f1 - f0):
            t = fr/QPS; T = starts[i] + t; im = acabar(o.quadro(t, i == len(objs) - 1), nq)
            k = min(1.0, T/fade_in, (total - T)/fade_out)
            if trans == "preto": k = min(k, t/0.45)
            if i + 1 < len(objs) and cenas[i + 1].get("transicao") == "preto": k = min(k, (durs[i] - t)/0.45)
            if k < 1: im = Image.fromarray((np.asarray(im, np.float32)*max(0, k)).astype(np.uint8))
            p.stdin.write(im.tobytes()); nq += 1
        print(f"cena {i + 1}/{len(objs)} pronta", flush=True)
    p.stdin.close()
    if p.wait() != 0: sys.exit("ERRO ao gerar o vídeo")
    mix = efeitos(total, cenas, starts, durs)
    if any(o.preparar()["chamas"] for o in objs): mix = mix + estalos_vela(total)
    if not a.sem_trilha: mix = mix + musica(spec.get("musica", "calma"), total)*(0.45 if voz is not None else 1.0)
    if voz is not None: m = min(len(mix), len(voz)); mix[:m] += voz[:m]
    pk = np.max(np.abs(mix)) if len(mix) else 0
    if pk > 0.89: mix *= 0.89/pk
    wav = os.path.join(a.out, "_som.wav")
    with wave.open(wav, "w") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1)*32767).astype(np.int16).tobytes())
    final = os.path.join(a.out, a.nome + ("-com-voz" if voz is not None else "") + ".mp4")
    subprocess.run([ff, "-v", "error", "-y", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", final[:-4] + ".tmp.mp4"], check=True)
    os.replace(final[:-4] + ".tmp.mp4", final)
    if a.pecas: pecas(a, ff, objs, cenas, starts, durs, wav)
    for x in (vid, wav): os.remove(x)
    print("PRONTO:", final, f"({total:.1f}s)")

def _srt_t(t):
    h, r = divmod(t, 3600); m, r = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{int(r):02d},{int((r - int(r))*1000):03d}"

def pecas(a, ff, objs, cenas, starts, durs, wav):
    """peças para editar fora: cena_NN.mp4 (tela inteira 1440x2560, sem câmera e sem texto), cena_NN.png,
    som.wav (música + efeitos + voz) e frases.srt (legenda com os tempos de cada cena)"""
    pasta = os.path.join(a.out, "pecas"); os.makedirs(pasta, exist_ok=True)
    for i, o in enumerate(objs):
        arq = os.path.join(pasta, f"cena_{i + 1:02d}.mp4")
        p = subprocess.Popen([ff, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CW}x{CH}", "-framerate", str(QPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", arq], stdin=subprocess.PIPE)
        for fr in range(int(round(durs[i]*QPS))):
            im = o.quadro(fr/QPS, bruto=True).convert("RGB")
            if fr == 0: im.save(os.path.join(pasta, f"cena_{i + 1:02d}.png"))
            p.stdin.write(im.tobytes())
        p.stdin.close(); p.wait()
    shutil.copy(wav, os.path.join(pasta, "som.wav"))
    with open(os.path.join(pasta, "frases.srt"), "w", encoding="utf-8") as f:
        k = 1
        for c, s0, d in zip(cenas, starts, durs):
            txt = (c.get("texto") or c.get("narracao") or "").replace("*", "").strip()
            if txt: f.write(f"{k}\n{_srt_t(s0 + 0.3)} --> {_srt_t(s0 + d - 0.2)}\n{txt}\n\n"); k += 1
    with open(os.path.join(pasta, "LEIA-ME.txt"), "w", encoding="utf-8") as f:
        f.write("Peças para editar no CapCut (ou outro editor)\n\n"
                "cena_01.mp4, cena_02.mp4...  cada cena em tela inteira (1440x2560), SEM câmera e SEM texto.\n"
                "   Coloque em ordem num projeto 9:16 e use zoom/posição com keyframes para fazer o seu jogo de câmera.\n"
                "   Como a imagem é maior que o Reel (1080x1920), dá para aproximar sem perder qualidade.\n"
                "cena_01.png...  a mesma cena como imagem (capa, miniatura, ajustes).\n"
                "som.wav  música + efeitos (+ voz, se houver), já no tempo das cenas.\n"
                "frases.srt  as frases com os tempos; no CapCut: Texto > Legendas > Importar.\n\n"
                "Tempo de cada cena:\n" + "".join(f"  cena {i + 1}: {s0:.1f}s a {s0 + d:.1f}s\n" for i, (s0, d) in enumerate(zip(starts, durs))))
    print("Peças para edição em", pasta)

if __name__ == "__main__":
    main()
