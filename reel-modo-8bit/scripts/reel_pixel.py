#!/usr/bin/env python3
"""Reel em pixel art, tela cheia, com frases por cima.

Uso:
  python3 reel_pixel.py roteiro.json --out PASTA --preview 2,8,15   # quadros de prova
  python3 reel_pixel.py roteiro.json --out PASTA --nome meu-reel     # vídeo sem voz
  python3 reel_pixel.py roteiro.json --out PASTA --audio voz.mp3     # com a narração
  (--sem-musica tira a trilha de 8 bits)

O roteiro.json aponta para um cenas.py (na mesma pasta) com uma função arte_<nome>(a, t, D) por cena
e, se quiser, textos_<nome>(x, t, D). Veja o SKILL.md e a pasta exemplos/.
"""
import argparse, importlib.util, json, math, os, re, shutil, subprocess, sys, wave
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from pixelkit import *  # noqa

FPS = 30

# ------------------------------------------------------------------ util
def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if exe: return exe
    try:
        import imageio_ffmpeg
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "imageio-ffmpeg"], check=False)
        import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()

def parse_titulo(s):
    out = []
    for parte in re.split(r"(\*[^*]+\*)", s or ""):
        em = parte.startswith("*") and parte.endswith("*") and len(parte) > 2
        for w in (parte[1:-1] if em else parte).split():
            out.append((w.upper(), em))
    return out

# ------------------------------------------------------------------ legenda
def cap_groups(nar):
    f = fonte("legenda", 16); groups, cur = [], []
    def fits(ws):
        x, lines = 0, 1
        for p in ws:
            ww = f.getlength(p + " ")
            if x + ww - f.getlength(" ") > 236: lines += 1; x = 0
            x += ww
        return lines <= 2
    for wd in (nar or "").split():
        if cur and not fits(cur + [wd]): groups.append(cur); cur = []
        cur.append(wd)
        if wd[-1:] in ".!?:" and len(cur) >= 3: groups.append(cur); cur = []
    if cur:
        if groups and len(cur) <= 1 and fits(groups[-1] + cur): groups[-1] += cur
        else: groups.append(cur)
    return groups

def word_times(groups, D):
    ws = [wd for g in groups for wd in g]
    if not ws: return []
    wt = []
    for wd in ws:
        k = len(wd) + 3
        if wd.endswith("..."): k += 7
        elif wd[-1:] in ".!?": k += 5
        elif wd[-1:] in ",:;": k += 3
        wt.append(k)
    a, b = 0.15, max(0.6, D - 0.35); out, t = [], a
    for k in wt: out.append(t); t += (b - a) * k / sum(wt)
    return out

def draw_caption(x, words, cur):
    """as palavras aparecem conforme são ditas; a última fica em amarelo"""
    f = fonte("legenda", 16); lines, line, w = [], [], 0
    for p in words:
        ww = f.getlength(p + " ")
        if line and w + ww - f.getlength(" ") > 236: lines.append(line); line, w = [], 0
        line.append(p); w += ww
    lines.append(line)
    y0 = 326 if len(lines) == 2 else 335
    k = 0
    for li, ln in enumerate(lines):
        lw = f.getlength(" ".join(ln)); xx = (TW - lw) / 2
        for p in ln:
            if k <= cur: x.texto(int(xx), y0 + li * 20, p, OURO if k == cur else BRANCO, 16, "legenda")
            xx += f.getlength(p + " "); k += 1

# ------------------------------------------------------------------ cabeçalho
def draw_header(x, tema, info, t):
    lab, n, N = info
    x.texto(14, 64, lab, BRANCO, 8)
    d = x.d; bx = 100
    d.rectangle([bx - 2, 62, 256, 73], fill=INK)
    N = max(1, N); seg = (156 - 2) / N
    for i in range(N):
        x0 = bx + int(i * seg) + 1; x1 = bx + int((i + 1) * seg) - 1
        if i == n - 1 and lab.startswith("FASE"):
            k = ease(t / 0.5)
            d.rectangle([x0, 64, x1, 71], fill=(60, 56, 70)); d.rectangle([x0, 64, x0 + int((x1 - x0) * k), 71], fill=tema.cor)
            continue
        d.rectangle([x0, 64, x1, 71], fill=tema.cor if i < n else (60, 56, 70))
        if i < n: d.line([x0, 64, x1, 64], fill=tema.clara)

def draw_badge_title(x, tema, selo, titulo, t):
    d = x.d
    cx, cy = 26, 96 - (2 if 0.05 < t < 0.2 else 0)
    d.rectangle([cx - 10, cy - 13, cx + 10, cy + 13], fill=INK); d.rectangle([cx - 13, cy - 10, cx + 13, cy + 10], fill=INK)
    d.rectangle([cx - 8, cy - 11, cx + 8, cy + 11], fill=tema.cor); d.rectangle([cx - 11, cy - 8, cx + 11, cy + 8], fill=tema.cor)
    d.rectangle([cx - 8, cy - 9, cx - 5, cy - 6], fill=tema.clara)
    if selo in ("ok", "✓", "check"): d.line([cx - 6, cy, cx - 2, cy + 5, cx + 6, cy - 5], fill=BRANCO, width=3)
    else: x._raw((cx - 7 if len(selo) == 1 else cx - 11, cy - 7 if len(selo) == 1 else cy - 4), selo, fonte("jogo", 16 if len(selo) == 1 else 8), BRANCO)
    f = fonte("jogo", 12); xx, y = 46, 88
    if sum(f.getlength(w + " ") for w, _ in titulo) <= 216: y = 96
    for w, em in titulo:
        ww = f.getlength(w + " ")
        if xx + ww - f.getlength(" ") > 262: xx = 46; y += 17
        x.texto(int(xx), y, w, tema.clara if em else BRANCO, 12)
        xx += ww

# ------------------------------------------------------------------ cena
class Cena:
    def __init__(self, spec, i, info, D, tema, mod, mascote):
        self.s, self.i, self.info, self.D, self.tema, self.mod, self.mascote = spec, i, info, D, tema, mod, mascote
        self.titulo = parse_titulo(spec.get("titulo", ""))
        self.groups = cap_groups(spec.get("narracao", ""))
        self.wt = word_times(self.groups, D)
        nome = spec.get("arte")
        self.f_arte = getattr(mod, "arte_" + nome, None) if nome else None
        if nome and not self.f_arte: sys.exit(f"ERRO: cenas.py não tem a função arte_{nome}")
        self.f_txt = getattr(mod, "textos_" + nome, None) if nome else None

    def frame(self, t):
        a = Arte(self.tema)
        if self.f_arte: self.f_arte(a, t, self.D)
        else: a.ceu(t=t)
        if self.mascote is not None:
            j = 1 if int(t * 2) % 2 else 0
            jump = int(3 * math.sin(math.pi * clamp01(t / 0.35))) if t < 0.35 else 0
            a.imagem(self.mascote, 4, 164 - self.mascote.height - jump + j)
        big = a.img.resize((W, H), Image.NEAREST)
        x = Textos(self.tema)
        draw_header(x, self.tema, self.info, t)
        draw_badge_title(x, self.tema, str(self.s.get("selo", "")), self.titulo, t)
        for e in self.s.get("etiquetas", []):
            if self.D * float(e.get("em", 0)) <= t <= self.D * float(e.get("ate", 1.01)):
                x.etiqueta(int(e.get("x", 135)), int(e.get("y", 150)), e["texto"], e.get("cor", "marca"), e.get("centro", True))
        if self.f_txt: self.f_txt(x, t, self.D)
        arroba = self.s.get("_arroba")
        if arroba and str(self.s.get("selo", "")) in ("ok", "✓", "check"):
            x.texto(135, int(self.s.get("_arroba_y", 300)), arroba, BRANCO, 8, centro=True)
        cur = -1
        for k, s in enumerate(self.wt):
            if t >= s: cur = k
        if cur >= 0:
            acc = 0
            for g in self.groups:
                if cur < acc + len(g): draw_caption(x, g, cur - acc); break
                acc += len(g)
        tl = x.img.resize((W, H), Image.NEAREST)
        big.paste(tl, (0, 0), tl)
        return big

# ------------------------------------------------------------------ som 8 bits (composição própria)
SR = 44100
def _sq(f, n, duty=0.5): t = np.arange(n) / SR; return np.where((t * f) % 1 < duty, 1.0, -1.0)
def _tri(f, n): t = np.arange(n) / SR; return 2 * np.abs(2 * ((t * f) % 1) - 1) - 1
def _note(m): return 440 * 2 ** ((m - 69) / 12)

def trilha(total):
    n = int(total * SR) + SR; out = np.zeros(n); step = 60 / 112 / 2
    mel = [72, 76, 79, 76, 74, 77, 81, 77, 72, 76, 79, 84, 79, 76, 74, 71]; bass = [48, 48, 45, 45, 41, 41, 43, 43]
    i, t = 0, 0.0
    while t < total:
        a = int(t * SR); L = int(step * 0.8 * SR)
        if a + L < n:
            out[a:a + L] += 0.035 * _sq(_note(mel[i % 16]), L, 0.25) * np.exp(-np.arange(L) / (L * 0.5))
            if i % 2 == 0:
                LB = int(step * 1.8 * SR)
                if a + LB < n: out[a:a + LB] += 0.05 * _tri(_note(bass[(i // 2) % 8]), LB) * np.exp(-np.arange(LB) / LB)
        i += 1; t += step
    out *= np.minimum(1, np.arange(n) / SR) * np.clip((total - np.arange(n) / SR) / 1.2, 0, 1)
    return out[: int(total * SR)]

def efeitos(total, cenas, starts, durs):
    n = int(total * SR) + SR; out = np.zeros(n)
    def blip(at, notas, dur=0.06, vol=0.07):
        for k, m in enumerate(notas):
            a = int((at + k * dur) * SR); L = int(dur * SR)
            if 0 <= a and a + L < n: out[a:a + L] += vol * _sq(_note(m), L) * np.linspace(1, 0.2, L)
    def ruido(at, dur=0.05, vol=0.12):
        a = int(at * SR); L = int(dur * SR)
        if 0 <= a and a + L < n: out[a:a + L] += vol * np.random.default_rng(int(at * 100)).standard_normal(L) * np.exp(-np.arange(L) / (L / 5))
    SONS = {"moeda": lambda at: blip(at, [84, 91], 0.07), "pulo": lambda at: blip(at, [67, 74, 79], 0.04),
            "sucesso": lambda at: blip(at, [72, 76, 79, 84, 88], 0.06), "alerta": lambda at: blip(at, [79, 72, 79, 72], 0.07, 0.06),
            "quebra": lambda at: [ruido(at + k * 0.18) for k in range(4)], "toque": lambda at: blip(at, [88], 0.05, 0.05)}
    for c, s, D in zip(cenas, starts, durs):
        if s > 0: blip(s, [76, 79, 84], 0.05, 0.06)
        for e in c.get("sons", []):
            fn = SONS.get(e.get("tipo"))
            if fn: fn(s + D * float(e.get("em", 0.5)))
            if e.get("tipo") == "digitar":
                a0, a1 = s + D * float(e.get("em", 0.1)), s + D * float(e.get("ate", 0.6))
                for at in np.arange(a0, a1, 0.11): ruido(at, 0.012, 0.03)
    return out[: int(total * SR)]

def ler_audio(ff, path, pasta):
    wav = os.path.join(pasta, "_narracao.wav")
    subprocess.run([ff, "-v", "error", "-y", "-i", path, "-ac", "1", "-ar", str(SR), wav], check=True)
    with wave.open(wav) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
    os.remove(wav); return x

# ------------------------------------------------------------------ principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("roteiro"); ap.add_argument("--out", default="saida_reel"); ap.add_argument("--preview")
    ap.add_argument("--audio"); ap.add_argument("--sem-musica", action="store_true"); ap.add_argument("--nome", default="reel-pixel")
    a = ap.parse_args()
    spec = json.load(open(a.roteiro, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(a.roteiro))
    os.makedirs(a.out, exist_ok=True)
    marca = spec.get("marca", {})
    tema = Tema(marca.get("cor", "#7C3AED"))
    # cenas.py
    cp = os.path.join(base, spec.get("cenas_py", "cenas.py"))
    if os.path.exists(cp):
        sp = importlib.util.spec_from_file_location("cenas_usuario", cp); mod = importlib.util.module_from_spec(sp); sp.loader.exec_module(mod)
    else:
        mod = type(sys)("vazio")
    # mascote
    mascote = None
    if marca.get("mascote_sprite"):
        cores = {k: tuple(v) if isinstance(v, list) else hex2rgb(v) for k, v in marca.get("mascote_cores", {}).items()}
        tmp = Arte(tema); cs = dict(tmp.cores); cs.update(cores)
        spr = marca["mascote_sprite"]
        mascote = Image.new("RGBA", (len(spr[0]), len(spr)), (0, 0, 0, 0))
        for j, row in enumerate(spr):
            for i, ch in enumerate(row):
                if ch in cs: mascote.putpixel((i, j), cs[ch] + (255,))
    elif marca.get("mascote"):
        mp = marca["mascote"] if os.path.isabs(marca["mascote"]) else os.path.join(base, marca["mascote"])
        if os.path.exists(mp): mascote = pixelizar_mascote(mp, int(marca.get("mascote_tamanho", 18)))
        else: print("AVISO: mascote não encontrado:", mp)
    # tempos
    cenas = spec["cenas"]; wps = float(spec.get("palavras_por_segundo", 2.4))
    durs = [float(c["duracao"]) if c.get("duracao") else max(3.2, len(c.get("narracao", "").split()) / wps + 0.8) for c in cenas]
    voz = None; ff = None
    if a.audio or not a.preview: ff = ffmpeg_bin()
    if a.audio:
        voz = ler_audio(ff, a.audio, a.out); L = len(voz) / SR
        marks = spec.get("marcas_audio")
        if marks and len(marks) == len(cenas):
            ends = [float(m) for m in marks[1:]] + [L + 0.6]
            durs = [max(1.0, e - float(s)) for s, e in zip(marks, ends)]
        else:
            k = (L + 0.6) / sum(durs); durs = [d * k for d in durs]
    starts = list(np.cumsum([0] + durs[:-1])); total = sum(durs)
    # rótulos das fases
    num = [i for i, c in enumerate(cenas) if str(c.get("selo", "")).isdigit()]
    N = len(num) or 1; infos = []
    for i, c in enumerate(cenas):
        if i in num: infos.append((f"FASE {num.index(i) + 1}/{N}", num.index(i) + 1, N))
        elif not num or i < num[0]: infos.append((c.get("rotulo", "INÍCIO"), 0, N))
        else: infos.append((c.get("rotulo", "FIM"), N, N))
    for c in cenas: c["_arroba"] = marca.get("arroba", ""); c["_arroba_y"] = marca.get("arroba_y", 300)
    objs = [Cena(c, i, infos[i], D, tema, mod, mascote) for i, (c, D) in enumerate(zip(cenas, durs))]
    with open(os.path.join(a.out, "tempos.txt"), "w", encoding="utf-8") as f:
        for i, (c, s, D) in enumerate(zip(cenas, starts, durs)):
            f.write(f"Cena {i + 1}: {s:5.1f}s a {s + D:5.1f}s · {c.get('titulo', '').replace('*', '')}\n")
        f.write(f"Total: {total:.1f}s\n")
    with open(os.path.join(a.out, "guia-narracao.txt"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(c.get("narracao", "") for c in cenas) + "\n")
    print(open(os.path.join(a.out, "tempos.txt"), encoding="utf-8").read())
    if a.preview:
        ims = []
        for ts in [float(v) for v in a.preview.split(",")]:
            i = max(k for k in range(len(starts)) if starts[k] <= ts)
            im = objs[i].frame(min(ts - starts[i], durs[i] - 0.01)); ims.append(im)
            im.save(os.path.join(a.out, f"previa_{ts:05.1f}s.png"))
        cols = min(5, len(ims)); rows = math.ceil(len(ims) / cols)
        g = Image.new("RGB", (cols * 432, rows * 768), "white")
        for k, im in enumerate(ims): g.paste(im.resize((432, 768), Image.LANCZOS), ((k % cols) * 432, (k // cols) * 768))
        g.save(os.path.join(a.out, "previa_grade.jpg"), quality=90); print("Prévia salva em", a.out); return
    # vídeo: um arquivo por cena, transição em blocos dentro do arquivo
    rnd = np.random.default_rng(7).random((H // 40 + 1, W // 40 + 1))
    parts, prev = [], None
    for i, sc in enumerate(objs):
        nfr = int(round((starts[i] + durs[i]) * FPS)) - int(round(starts[i] * FPS))
        tmp = os.path.join(a.out, f"_c{i:02d}.tmp.mp4"); fin = os.path.join(a.out, f"_c{i:02d}.mp4")
        p = subprocess.Popen([ff, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        last = None
        for fr in range(nfr):
            t = fr / FPS; im = sc.frame(t)
            if prev is not None and t < 0.3:
                mask = (rnd < t / 0.3).repeat(40, 0).repeat(40, 1)[:H, :W]
                im = Image.fromarray(np.where(mask[..., None], np.asarray(im), np.asarray(prev)).astype(np.uint8))
            p.stdin.write(im.tobytes()); last = im
        p.stdin.close()
        if p.wait() != 0: sys.exit(f"ERRO na cena {i + 1}")
        os.replace(tmp, fin); parts.append(fin); prev = last; print(f"cena {i + 1}/{len(objs)} pronta", flush=True)
    lst = os.path.join(a.out, "_lista.txt")
    with open(lst, "w") as f:
        for pth in parts: f.write(f"file '{os.path.abspath(pth)}'\n")
    vid = os.path.join(a.out, "_video.mp4")
    subprocess.run([ff, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", vid], check=True)
    n = int(total * SR); mix = efeitos(total, cenas, starts, durs)
    if not a.sem_musica: mix = mix + trilha(total) * (0.45 if voz is not None else 1.0)
    if voz is not None: m = min(n, len(voz)); mix[:m] += voz[:m]
    pk = np.max(np.abs(mix)) if n else 0
    if pk > 0.89: mix *= 0.89 / pk
    wav = os.path.join(a.out, "_som.wav")
    with wave.open(wav, "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
    final = os.path.join(a.out, a.nome + ("-com-voz" if voz is not None else "-sem-voz") + ".mp4")
    subprocess.run([ff, "-v", "error", "-y", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-movflags", "+faststart", final[:-4] + ".tmp.mp4"], check=True)
    os.replace(final[:-4] + ".tmp.mp4", final)
    for pth in parts + [lst, vid, wav]:
        if os.path.exists(pth): os.remove(pth)
    print("PRONTO:", final, f"({total:.1f}s)")

if __name__ == "__main__":
    main()
