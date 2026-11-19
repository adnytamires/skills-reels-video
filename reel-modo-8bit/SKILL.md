---
name: "reel-modo-8bit"
description: "Estilo Modo 8-Bit. Cria Reels 9:16 em pixel art de tela cheia, com cara de videogame (fases, barra de progresso, sons 8 bits) e frases passando por cima do desenho, na cor da marca da pessoa. Use quando pedirem \"Modo 8-Bit\" ou um Reel/vídeo curto em pixel art, estilo jogo retrô ou 8 bits."
---

# Modo 8-Bit: Reel em pixel art (tela cheia)

> **Kit de 3 estilos:** se a pessoa pedir um Reel sem dizer o estilo e também tiver as skills Tela Viva (tutorial na tela) e Hora Dourada (bonequinhos flat para histórias e tutoriais), pergunte primeiro qual dos três estilos ela quer.

Esta skill transforma um tema num Reel vertical (1080×1920, 30 fps, MP4) em **pixel art de tela cheia**:
- **O desenho ocupa a tela toda:** cenário, personagens e objetos têm o mesmo tamanho de "quadradinho".
- **Topo:** "FASE 2/6" com uma barra de progresso de jogo e, ao lado do número da fase, o título em letras de videogame.
- **Frases por cima do desenho:** as palavras aparecem conforme são ditas, com contorno escuro, e a palavra do momento fica em amarelo.
- **Plaquinhas de jogo:** etiquetas como "+1 XP", "~3 HORAS" ou "SEM DADOS SIGILOSOS".
- **Som:** uma trilha de 8 bits e efeitos (moeda, pulo, quebra, sucesso) compostos pelo próprio script, sem música de terceiros.
- **Marca da pessoa:** a cor dela em toda a paleta e o @ no fim.

O vídeo é montado por código (Python + ffmpeg). Não usa gerador de vídeo por IA. Responda no idioma da pessoa (normalmente português).

## Passo 1. Perguntar o que falta (uma mensagem só)
Pergunte de uma vez apenas o que a pessoa ainda não disse:
1. **Tema e objetivo:** sobre o que é o vídeo e o que quem assiste deve aprender ou sentir?
2. **Roteiro:** ela já tem o texto, ou você escreve? Se ela tiver, use o texto dela e só ajuste o tamanho.
3. **Marca:** cor principal em hex (ex.: `#7C3AED`) e o @ do perfil. Sem resposta, use `#7C3AED` e `@seuperfil`, e avise.
4. **Voz:**
   - ela grava a própria voz;
   - usa uma voz de IA (por exemplo, ElevenLabs);
   - ou fica sem voz, só com música e frases na tela.

   Isso não muda o vídeo agora, só o passo 6.

Se a pessoa disser "faz do seu jeito", siga com os padrões e diga quais usou.

## Passo 2. Escrever o roteiro (roteiro.json)
**Estrutura que funciona (de 5 a 10 cenas, de 30 a 60 s):**
- **Cena 1, gancho** (selo `?` ou `!`): uma pergunta ou situação que a pessoa reconhece. Aparece como "INÍCIO".
- **Cenas numeradas** (selos `1`, `2`, `3`...): uma ideia por cena. Cada uma vira uma **fase** ("FASE 2/6"), e a barra enche.
- **Cena final** (selo `ok`): chamada ("Salva", "Me segue", "Comenta PALAVRA"). Aparece como "FIM" e mostra o @ automaticamente.

**Regras de conteúdo:**
- Título com até 3 palavras curtas, de preferência. Destaque 1 ou 2 com `*asteriscos*`.
- Narração com cerca de 2,4 palavras por segundo. Frases curtas, uma ideia por frase.
- **Confira os fatos antes** (pesquise na web, se puder): números, prazos, nomes técnicos, funcionalidades de ferramentas. Diga à pessoa o que conferiu e onde. Se não der para conferir, avise e deixe a afirmação mais genérica.
- Use dados, nomes e empresas fictícios ("Pessoa A", "Fornecedor"). Nunca use dados reais de clientes.
- Sem promessas exageradas.

**Formato:**
```json
{
  "marca": {"cor": "#7C3AED", "arroba": "@seuperfil"},
  "palavras_por_segundo": 2.4,
  "cenas_py": "cenas.py",
  "cenas": [
    {"selo": "?", "titulo": "Como um *ovo nasce?*", "narracao": "...", "arte": "gancho",
     "etiquetas": [{"texto": "1  DENTRO DA GALINHA", "x": 135, "y": 150, "cor": "marca", "em": 0.5}],
     "sons": [{"tipo": "toque", "em": 0.5}]}
  ]
}
```

**Campos das cenas:**
- `arte`: nome da função de desenho em `cenas.py` (o motor chama `arte_<nome>`).
- `etiquetas`: plaquinhas que aparecem durante a cena.
  - `x` e `y` estão nas coordenadas de TEXTO (270×480); `x` é o centro da plaquinha.
  - `cor` pode ser `marca`, `ouro`, `vermelho`, `verde` ou `escura`.
  - `em` e `ate` são frações da cena (0 a 1).
- `sons`: `moeda`, `pulo`, `sucesso`, `alerta`, `quebra`, `toque` (com `em`) e `digitar` (com `em` e `ate`). A troca de fase já tem um som próprio.
- `duracao` (opcional): sem ela, a duração vem da narração.
- `marca.arroba_y` (opcional): altura do @ na cena final, em coordenadas de texto (padrão 300). Mude se ele cobrir o desenho.

## Passo 3. Desenhar as cenas (cenas.py)
Para cada cena, escreva `arte_<nome>(a, t, D)`. Se precisar de texto que muda (contador, por exemplo), escreva também `textos_<nome>(x, t, D)`. `t` são os segundos desde o início da cena e `D` é a duração da cena. Comece o arquivo com `from pixelkit import *`. Use `exemplos/ovo/cenas.py` e `exemplos/tutorial/cenas.py` como modelo.

**Regras de desenho (o que deixa o estilo certo):**
- **Desenhe tudo na camada `a`** (108×192 quadradinhos; cada um vira 10×10 px). **Nunca amplie** sprites nem desenhe objetos em outra escala: todos os elementos precisam ter o mesmo tamanho de pixel.
- **Tela cheia sempre:** cada cena começa com um cenário que cobre tudo: `a.ceu(t=t)`, `a.noite(t=t)`, `a.escritorio(t)`, `a.listras(c1, c2)` ou um fundo próprio com `a.d.rectangle([0, 0, AW, AH], fill=...)`. Nada de "janelinha" no meio.
- **Zonas (coordenadas da arte):**
  - até y=46 fica sob o título;
  - o desenho principal fica entre y=48 e y=126;
  - a legenda passa por volta de y=128 a 146;
  - abaixo de y=146 fica a área da interface do Instagram: só cenário, nada importante.
- **Movimento sempre:** algo se mexe em toda cena, como piscar (`piscar(t)`), balançar, crescer com `ease(...)`, aparecer aos poucos ou confete.
- **Só desenhos originais:** nada de personagens conhecidos, logos, marcas ou telas reais de ferramentas. Janelas e apps são genéricos.
- **Texto vai na camada `x`** (270×480): para converter da arte para o texto, multiplique por 2,5.

**Kit da camada de arte (`a`):**
- **Básicos:** `a.d` (ImageDraw para desenhar à mão), `a.px`, `a.ret`, `a.caixa` (contorno + sombra dura), `a.elipse`, `a.linha`, `a.seta`, `a.brilho`, `a.confete(t)`, `a.imagem`.
- **Sprites:** `a.sprite(SPRITE, x, y, cores={...}, espelhar=False)`.
  - Prontos: `GALINHA`, `GALINHA_SENTADA`, `PINTINHO`, `PINTINHO_PISCA`, `PESSOA`, `PESSOA_PISCA`, `CORACAO`, `ESTRELA`, `MOEDA`.
  - Na `PESSOA`, troque o cabelo e a pele com `cores={"H": CABELO[i], "S": PELE[i]}`. A roupa sai na cor da marca.
  - Para criar um sprite novo, faça uma lista de linhas, uma letra por pixel: K contorno, W branco, C cor da marca, E escura, L clara; outras cores entram por `cores=`.
- **Cenários:** `a.ceu`, `a.noite`, `a.escritorio` (mesa com tampo em y=118), `a.listras`, `a.nuvem`.
- **Objetos:**
  - escritório e conversa: `a.computador` (retorna a área da tela), `a.celular`, `a.balao` (balão de conversa), `a.linhas_texto` (texto falso, com `revelar` de 0 a 1 para o efeito de digitação), `a.documento`, `a.checklist`, `a.envelope`, `a.calendario`, `a.relogio`, `a.lampada`, `a.xicara`, `a.pilha_papel`;
  - do exemplo do ovo: `a.ovo`, `a.gema`, `a.ninho`.
- **Ajudas:** `ease`, `lerp`, `clamp01`, `piscar`, `mixc`, cores (`INK`, `BRANCO`, `OURO`, `VERMELHO`, `VERDE`, `AZUL`, `CINZA`...) e `a.tema` (`.cor`, `.escura`, `.clara`, `.suave`, `.fundo`).

**Kit da camada de texto (`x`):**
- `x.texto(x, y, "TEXTO", cor, tam=8, centro=False)`: sai com contorno escuro. `tam` 8, 12 ou 16 na fonte de jogo; para texto corrido, use `tipo="legenda"`.
- `x.etiqueta(x, y, "TEXTO", "marca")`: plaquinha.
- Maiúsculas acentuadas (Á, Ã, Ê...) já saem certas.

## Passo 4. Quadros de prova
```bash
python3 <pasta-da-skill>/scripts/reel_pixel.py roteiro.json --out saida --preview 2,8,14,20,26
```

Use um tempo do fim de cada cena (os tempos aparecem na saída) e abra `saida/previa_grade.jpg`. Confira:
- todos os desenhos com o mesmo tamanho de pixel;
- nada importante embaixo do título ou da legenda;
- etiquetas sem sobreposição e dentro da tela;
- tela cheia em todas as cenas.

Ajuste e repita, se precisar. Depois mostre a grade e o roteiro (cena, o que aparece, narração) e pergunte se pode gerar o vídeo.

## Passo 5. Gerar o vídeo
```bash
python3 <pasta-da-skill>/scripts/reel_pixel.py roteiro.json --out saida --nome meu-reel
```

O comando gera:
- `saida/meu-reel-sem-voz.mp4`, com trilha e efeitos de 8 bits;
- `saida/guia-narracao.txt`, só com o texto falado, um parágrafo por cena;
- `saida/tempos.txt`, com o início e o fim de cada cena.

Antes de entregar, olhe 4 a 6 quadros do MP4 com o ffmpeg. Entregue o vídeo, o guia de narração e uma **legenda para o post**: gancho, resumo em tópicos, chamada e 3 a 5 hashtags. Se o vídeo citar fatos, ponha a fonte na legenda.

## Passo 6. A voz
Explique as opções à pessoa e siga a que ela escolher:
- **Gravar a própria voz** (grátis e mais pessoal):
  - grave no celular, em lugar silencioso, lendo o `guia-narracao.txt` com calma;
  - um parágrafo por cena, com uma pausa curta entre eles;
  - mande o arquivo na conversa.
- **Voz de IA (ElevenLabs ou parecido):**
  - cole o guia de narração, escolha uma voz em português, gere e baixe o MP3;
  - **cuidado com as regras do plano:** no plano gratuito do ElevenLabs, o uso é só **não comercial** e com crédito ao ElevenLabs;
  - perfil de empresa, venda ou cliente pede plano pago;
  - essas condições mudam: peça para a pessoa conferir em elevenlabs.io/pricing antes de publicar.
- **Sem voz:** o vídeo já funciona só com a música e as frases na tela.

Quando o áudio chegar:
```bash
python3 <pasta-da-skill>/scripts/reel_pixel.py roteiro.json --out saida --nome meu-reel --audio /caminho/voz.mp3
```

- Sem marcas de tempo, as cenas se espalham pelo áudio, na proporção das palavras de cada cena.
- Para sincronizar com precisão, coloque no JSON `"marcas_audio": [0, 6.4, 12.1, ...]`, com o segundo em que cada cena começa na gravação.
- O resultado é `meu-reel-com-voz.mp4`, com a trilha mais baixa sob a voz.

**Lembrete ao entregar:** se houver voz ou imagem gerada por IA, a pessoa deve marcar o rótulo de IA ao postar.

## Problemas comuns
- **"não encontrei o ffmpeg":** o script instala `imageio-ffmpeg` pelo pip sozinho. Se falhar, rode `pip install imageio-ffmpeg --break-system-packages`.
- **"cenas.py não tem a função arte_X":** o nome em `"arte"` precisa bater com `def arte_X(a, t, D)`.
- **Mascote:** não ponha mascote por padrão. Só se a pessoa pedir e mandar um PNG: aí use `"mascote": "arquivo.png"` em `marca`, e ele é pixelizado e fica no canto de baixo.
- **Legenda rápida demais:** aumente `duracao` ou corte palavras da narração.
- **Fontes:** Press Start 2P e Pixelify Sans (licença SIL Open Font, arquivos em `assets/fonts`).