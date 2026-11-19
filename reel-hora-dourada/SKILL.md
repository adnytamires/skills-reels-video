---
name: "reel-hora-dourada"
description: Estilo Hora Dourada. Cria Reels 9:16 de histórias e mini tutoriais no traço flat de vídeo explicativo, com personagens vetoriais sem contorno, cor chapada com uma sombra, olhos brancos com pupila e sobrancelhas grossas, legenda em caixa alta com a palavra em destaque e títulos animados, nas cores que a pessoa escolher. Use quando pedirem "Hora Dourada", um Reel/vídeo curto animado que conte uma história, um caso ou um tutorial explicativo com bonequinhos.
---

# Hora Dourada: histórias e tutoriais em traço flat

> **Kit de 3 estilos:** se a pessoa pedir um Reel sem dizer o estilo e também tiver as skills Tela Viva (tutorial na tela) e Modo 8-Bit (pixel art), pergunte primeiro qual dos três estilos ela quer.

Esta skill faz um Reel vertical (1080×1920, MP4, 24 quadros por segundo) que conta uma história ou ensina algo em cenas desenhadas por código. Responda no idioma da pessoa.

## O traço (é isto que nunca muda)
É o traço dos vídeos explicativos vetoriais. A dona da skill aprovou exatamente este resultado, então mantenha as regras:
- **Sem contorno:** as formas se separam só pela cor.
- **Cor chapada e UMA sombra de borda dura** num lado do rosto, do pescoço e da roupa.
- **Rosto:**
  - olhos: círculo branco grande, pupila preta e pontinho de brilho;
  - **sobrancelhas grossas em barra arredondada**, que fazem toda a expressão;
  - nariz e boca de traço simples, orelhas em meia-lua;
  - bochechas coradas quando sorri.
- **Acessórios:** cabelo chapado com um reflexo claro, óculos de armação grossa, boné com botão.
- **Objetos e ícones:** no mesmo traço, chapados, com uma sombra: notebook visto de costas com adesivos, sol, nuvem, cartões, termômetro, partículas.
- **Texto:**
  - legenda em **caixa alta grossa** (Montserrat), aparecendo palavra por palavra, com a palavra da vez na cor de destaque;
  - **títulos grandes** animados: vazados, cheios ou com brilho.
- **Movimento:** câmera lenta (aproximar, afastar ou deslizar), objetos animados (partículas, raios girando, vapor subindo, cartões entrando) e cortes secos.

**O que muda a cada vídeo é escolha da pessoa: as cores, a história e o clima.** Nunca assuma uma paleta.

Crie personagens e histórias **originais**. Se a pessoa mandar o vídeo de outro criador como referência, use só o traço, sem copiar personagens, roteiro ou bordões.

## Passo 1. Perguntar (uma mensagem só)
1. **História ou tutorial:** o que acontece, ou o que a pessoa quer ensinar, e o objetivo.
2. **Roteiro:** a pessoa já tem o texto, ou você escreve?
3. **Público e duração:** curto (20 a 30 s, padrão), médio (30 a 45 s) ou longo (45 a 60 s).
4. **Cores (pergunte SEMPRE):**
   - o que escolher: o fundo e a cor de destaque (palavras e detalhes);
   - sugestões:
     - branco + azul (aula, limpo);
     - azul-céu + amarelo (alegre, de dia);
     - azul-marinho + laranja (dramático);
     - verde + amarelo;
     - ou as cores da marca, em hex.
5. **Como contar (pergunte sempre):**
   - **só texto na tela** (a legenda mostra a narração, com música);
   - **a própria voz** (você entrega o texto, a pessoa grava e você sincroniza);
   - **voz de IA** (por exemplo, ElevenLabs; gasta créditos).
6. **Perfil (opcional):** o @ que aparece no fim.

Use a ferramenta de perguntas, se houver. Se a pessoa disser "faz do seu jeito", siga e diga o que escolheu, menos as cores, que sempre precisam de resposta, a não ser que ninguém esteja ali para responder.

## Passo 2. Roteiro (aprovar ANTES de desenhar)
Mostre uma tabela, com uma linha por cena: **o que aparece | texto/narração**. Peça o ok antes de escrever código. O desenho é a parte demorada.
- **Tamanho e ritmo:** de 5 a 8 cenas, de 3 a 6 s cada, com frases curtas (até umas 12 palavras por cena).
- **História:** comece com um gancho (pergunta ou situação) e termine com uma virada ou uma conclusão. Recursos que funcionam bem:
  - tela dividida (antes e depois, um e outro);
  - um lado perdendo a cor;
  - títulos grandes ("DIA 1", "SÓ UM", "POR QUÊ?").
- **Tutorial:** cada passo vira um objeto explicativo na tela (diagrama, ícone, cartão, seta, número, tela de app genérica), e a personagem aparece no começo e no fim.
- **Fatos:** confira antes de afirmar. Pesquise quando for algo que pode ter mudado, e diga à pessoa onde conferiu. Ciência estável dispensa pesquisa, mas precisa estar correta. Use nomes e dados fictícios e nada de promessas exageradas.

## Passo 3. O `roteiro.json`
```json
{
  "modo": "voz", "estilo_texto": "flat", "musica": "alegre",
  "marca": {"cor": "#2F80ED", "arroba": "@seuperfil"},
  "cor_texto": "#1F2A3A",
  "cenas_py": "cenas.py",
  "cenas": [
    {"cena": "pergunta", "narracao": "Para onde vai a água da poça?", "camera": {"mov": "aproximar", "foco": [720, 1200]}},
    {"cena": "dicas", "narracao": "Calor, vento e mais superfície aceleram.", "duracao": 4.8, "camera": {"mov": "parada", "zoom": [1.0, 1.0]}}
  ]
}
```

**Campos:**
- `modo`: sempre `"voz"`, e `estilo_texto`: sempre `"flat"`. A `narracao` de cada cena é a legenda; sem áudio, o vídeo fica "só texto na tela".
- `marca.cor`: a **cor de destaque** escolhida, usada na palavra da vez da legenda.
- `cor_texto`: a cor das outras palavras.
  - **fundo claro:** texto escuro (ex.: `#1F2A3A`); o motor tira a vinheta sozinho;
  - **fundo escuro:** não ponha o campo, e o texto sai claro.
- `musica`: `alegre`, `calma`, `misterio`, `tensa` ou `nenhuma`. Escolha pela história.
- `marca.arroba` (opcional): aparece no fim.
- **Campos de cada cena:**
  - `legenda: false`: tira a legenda da cena (use quando um título grande já diz a frase);
  - `duracao`: segundos; sem ela, a duração vem da narração;
  - `camera`:
    - `mov`: `aproximar`, `afastar`, `direita`, `esquerda`, `subir`, `descer` ou `parada`;
    - `foco`: `[x, y]` na tela de desenho (de 0 a 1440 e de 0 a 2560);
    - `zoom`: `[início, fim]`, entre 1.0 e 1.35;
  - `sons`: `tom`, `sino`, `papel`, `passos`, `porta`, `batida`, `vento` ou `caneta`, com `em` (fração da cena), `vezes` e `intervalo`.

## Passo 4. Desenhar as cenas (`cenas.py`)
Comece com `from desenho import *` e `from flat import *`. Para cada cena:
- `desenhar_<cena>(k)`: roda 1 vez. Crie `c = Cena(clima="interior", ambiente=(1, 1, 1))`, desenhe e **devolva `c`**. Guarde em `c.dados` o que a animação precisar.
- `animar_<cena>(im, t, D, d)` (opcional): roda a cada quadro, desenhando por cima em `im`, a tela inteira de 1440 × 2560, com `t` em segundos. Use `camada(im, caixa, desenhar)` para formas animadas com borda suave.

Modelos: `exemplos/como-a-agua-evapora/` (tutorial, fundo claro) e `exemplos/dois-amigos/` (história, fundo escuro com tela dividida). Copie a organização deles.

**Regras:**
- **Personagens fixos:** defina cada um uma vez no topo (`LIA = dict(pele=..., cabelo=..., ...)`) e reutilize, para a cara ser a mesma em todas as cenas.
- **Cores:** tudo vem da paleta escolhida, no fundo (`fundo_textura`) e nas roupas e objetos principais. Sol amarelo e outras cores "naturais" podem aparecer nos objetos.
- **Sem contorno:** em `c.ret`, `c.elipse` e `c.forma`, sempre use `contorno=False`.
- **Zona da legenda:** a legenda fica em y ≈ 1480 do vídeo, que é y ≈ 1950 da tela de desenho quando a câmera está aberta.
  - Com personagem, ponha uma **faixa embaixo** (`mesa_frente(c, 1800, cor)`) e a pessoa acima dela.
  - Nada importante (rosto, rótulo, título) pode ficar nessa faixa.
  - Títulos grandes vão na metade de cima.
- **Personagens só da cintura para cima** (`busto`), como nos vídeos de referência: atrás de um notebook, de uma faixa de mesa ou cortados pela borda. Para mostrar algo fora da cena, use um balão de pensamento, um ícone ou um objeto.
- **Telas de app:** sempre genéricas (`tela_app`), sem logos nem marcas reais.

**Kit:**
- **Personagem:** `busto(c, x, y, tam, roupa, cor_roupa, **rosto)`, com `(x, y)` no centro da cabeça e `tam` sendo a altura da cabeça (de 330 a 400).
  - `roupa`: `moletom`, `camiseta`, `camisa` ou `blazer`;
  - `pele`: `clara`, `media`, `morena`, `escura` ou RGB;
  - `cabelo`: `espetado`, `baguncado`, `curto`, `cacheado`, `longo`, `chanel`, `rabo`, `coque` ou `careca`, com `cor_cabelo`;
  - acessórios: `oculos`, `bone` (com `cor_bone` e `cor_botao`), `barba`, `brinco`;
  - `expressao`: `neutro`, `feliz`, `sorriso`, `bravo`, `determinado`, `triste`, `preocupado`, `surpreso`, `rindo` ou `pensativo`;
  - `olhar`: `(x, y)` de -1 a 1, para onde as pupilas olham;
  - `espelho=True`: vira o personagem.
- **Cenário e objetos:** `fundo_textura(c, cor_cima, cor_baixo, linhas, ruido)`, `mesa_frente(c, y, cor)`, `notebook_costas(c, x, y_topo, w, cor, adesivo)`, `janela_noite`, `balao_pensamento(c, x, y, w, h)`, `nuvem(c, x, y, s)`, `brilho(c, x, y, raio, cor)`. Do `desenho.py` vêm `notebook`, `celular` + `tela_app`, `papel`, `quadro_branco` + `escrever`, `mesa`, `janela` e `lampada_teto`.
- **Animação** (dentro de `animar_`):
  - `camada(im, (x0, y0, x1, y1), desenhar)`: desenha formas animadas com borda suave;
  - `sol(im, x, y, r, t)`: sol com raios girando;
  - `nuvem(im, ..., em_cena=False)`: nuvem que cresce;
  - `texto_grande(im, txt, x, y, tam, cor, contorno, brilho, alfa)`: título grande;
  - `linha_brilho(im, x, t)`: linha brilhante da tela dividida;
  - `apagar_lado(im, x0, x1, forca)`: tira a cor de um lado da tela;
  - `faiscas(im, t, n, area)`: faíscas subindo;
  - `escrever_animado(im, area, linhas, t)`: escrita à mão aparecendo;
  - `poeira`.
- **Ajudas:** `ease`, `lerp`, `clamp01`, `mistura`, `escurecer`, `CW`, `CH`.

Se a história pedir algo que o kit não tem (uma planta, um carro, um gráfico), desenhe com `c.forma(..., contorno=False, suave=True)`, `c.ret` e `c.elipse`, no mesmo traço: cor chapada, uma sombra de um lado, poucos detalhes.

## Passo 5. Quadros de prova
```bash
python3 <pasta-da-skill>/scripts/reel.py roteiro.json --out saida --preview 2,7,12,17
```

O comando mostra os tempos. Escolha um tempo do meio de cada cena, abra `saida/previa_grade.jpg` e confira:
- a legenda está legível e não cobre rosto nem rótulo;
- nada importante cortado na borda;
- títulos e rótulos sem colidir;
- as cores escolhidas pela pessoa estão aplicadas;
- o traço sem contorno, com uma sombra.

Ajuste e repita. Mostre a grade à pessoa e peça o ok.

## Passo 6. Gerar e entregar
```bash
python3 <pasta-da-skill>/scripts/reel.py roteiro.json --out saida --nome meu-reel
```

Leva de 2 a 4 minutos e gera `saida/meu-reel.mp4`, `guia-narracao.txt` e `tempos.txt`. Antes de entregar, olhe 4 ou 5 quadros do MP4. Entregue o vídeo com uma legenda para o post (gancho, resumo, chamada e 3 a 5 hashtags, com a fonte dos fatos).

**Para editar fora (CapCut etc.):** acrescente `--pecas`. O comando gera `saida/pecas/` com:
- cada cena em tela grande (1440×2560), **sem câmera e sem texto**;
- as imagens das cenas;
- `som.wav` e `frases.srt`;
- um `LEIA-ME.txt` com o passo a passo.

Compacte a pasta em .zip para entregar. Ofereça essa opção quando a pessoa disser que quer fazer o próprio jogo de câmera.

## Passo 7. A voz (se a pessoa escolher voz)
- **Voz de IA:** se houver ferramenta de voz conectada (como o ElevenLabs), avise que gasta créditos e peça o ok. Gere a narração com `guia-narracao.txt`. Se não der para trazer o áudio para cá, peça à pessoa para gerar e mandar o MP3. No plano gratuito do ElevenLabs, o uso é não comercial e com crédito, e as condições mudam (elevenlabs.io/pricing).
- **Própria voz:** a pessoa grava lendo o guia, um parágrafo por cena, e manda o arquivo.

Com o áudio:
```bash
python3 <pasta-da-skill>/scripts/reel.py roteiro.json --out saida --nome meu-reel --audio voz.mp3
```

Para sincronizar exato, use `"marcas_audio": [0, 4.1, 9.6, ...]`, com o segundo em que cada cena começa. Lembre a pessoa do rótulo de IA no Instagram quando houver voz de IA.

## Problemas comuns
- **"não encontrei o ffmpeg":** o script instala `imageio-ffmpeg` sozinho; se falhar, rode `pip install imageio-ffmpeg --break-system-packages`.
- **Fundo claro saindo acinzentado:** confira se `cor_texto` é escura (isso desliga a vinheta) e se o `ambiente` da `Cena` é `(1, 1, 1)`.
- **Legenda em cima do personagem:** suba o `busto` (y menor) e ponha `mesa_frente` mais alta, ou mude o `foco` da câmera.
- **Texto grande colidindo:** mude o `y` do `texto_grande` ou desligue a legenda da cena (`"legenda": false`).
- **Fontes:** Montserrat (títulos e legenda), Caveat (escrita à mão), Inter e Fraunces, todas com licença SIL Open Font, em `assets/fonts`.
