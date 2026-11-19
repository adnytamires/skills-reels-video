---
name: "reel-tela-viva"
description: "Estilo Tela Viva. Cria Reels animados 9:16 no estilo \"tutorial na tela\" (janelas genéricas sendo usadas, passos numerados, legenda palavra por palavra) com a cor e o @ da pessoa. Use quando pedirem \"Tela Viva\" ou um Reel/vídeo curto tutorial mostrando telas e apps sendo usados."
---

# Tela Viva: Reel tutorial animado

> **Kit de 3 estilos:** se a pessoa pedir um Reel sem dizer o estilo e também tiver as skills Modo 8-Bit (pixel art) e Hora Dourada (bonequinhos flat para histórias e tutoriais), pergunte primeiro qual dos três estilos ela quer.

Esta skill transforma um tema num Reel vertical (1080×1920, 30 fps, MP4) no estilo **tutorial na tela**:
- no topo, uma barra de progresso e o número do passo ao lado de um título curto;
- no centro, janelas genéricas e sem marca que "funcionam" (texto sendo digitado, resposta aparecendo, marca-texto, tarja sobre dado sigiloso);
- embaixo, uma legenda palavra por palavra: a palavra falada fica na cor da marca;
- no fim, um cartão "Me segue".

O vídeo é montado por código (Python + ffmpeg). Não usa gerador de vídeo por IA. Um Reel de 40 s fica pronto em menos de 1 minuto.

Responda sempre no idioma da pessoa (normalmente português).

## Passo 1. Entender o pedido (uma pergunta só, com tudo o que faltar)
Pergunte de uma vez apenas o que a pessoa ainda não disse:
1. **Tema:** o que quem assiste vai aprender ou testar? Se ela já trouxe o texto da narração, use o texto dela.
2. **Marca:** cor principal em hex (ex.: `#7C3AED`) e o @ do perfil. Sem resposta, use roxo `#7C3AED` e `@seuperfil`, e avise.

Se a pessoa disser "faz do seu jeito", não pergunte: siga com os padrões e diga quais usou.

## Passo 2. Escrever o roteiro
Monte um arquivo `roteiro.json` (formato abaixo; modelo pronto em `exemplos/roteiro-exemplo.json`).

**Estrutura que funciona (de 5 a 8 cenas, de 30 a 60 s):**
1. **Gancho** (selo `!`): uma situação que a pessoa reconhece, em até 10 palavras na narração.
2. **Passos numerados** (selos `1`, `2`, `3`...): uma ação por cena, com a janela mostrando a ação.
3. **Cuidado** (pode ser um dos passos): conferir o resultado e não colar dados sigilosos.
4. **Chamada** (selo `✓`): por exemplo, "Prompt na legenda" com um post-it (`nota`).
5. **Final** (`"tipo": "final"`): "Me segue para mais...".

**Regras de conteúdo:**
- Títulos com até 6 palavras. Destaque de 1 a 2 palavras com `*asteriscos*`.
- Narração: cerca de 2,3 palavras por segundo. A duração de cada cena sai da narração.
- Use dados, nomes e empresas **fictícios** ("Pessoa A", "Fornecedor") e marque `"exemplo": true` nas cenas com dados.
- Não ponha nomes, logos ou telas de ferramentas reais. As janelas são genéricas ("assistente de IA", "planilha", "caixa de entrada").
- Não invente funcionalidades, fórmulas, números ou resultados. Se o roteiro citar um recurso de uma ferramenta, confira numa fonte oficial (pesquise na web, se puder) e diga à pessoa o que conferiu. Se não puder conferir, avise.
- Sem promessas exageradas ("economize 10 horas", "nunca mais").

## Passo 3. Quadros de prova antes do vídeo
Rode a prévia com um tempo do meio de cada cena (os tempos aparecem no início da saída):

```bash
python3 <pasta-da-skill>/scripts/reel.py roteiro.json --out saida --preview 3,10,18,25,32
```

Abra `saida/previa_grade.jpg` e confira:
- nenhum texto saindo da janela;
- nenhum título com mais de 2 linhas;
- marca-texto e tarjas nos lugares certos.

Ajuste o JSON e repita, se precisar. Depois mostre à pessoa a grade e o roteiro numa tabela (cena, o que aparece, narração, tempo) e pergunte se pode gerar o vídeo.

## Passo 4. Gerar o vídeo
```bash
python3 <pasta-da-skill>/scripts/reel.py roteiro.json --out saida --nome meu-reel
```

O comando gera:
- `saida/meu-reel-sem-voz.mp4`, com uma trilha calma e sons de digitação criados pelo próprio script (sem música de terceiros);
- `saida/guia-narracao.txt`, só com o texto falado, um parágrafo por cena;
- `saida/tempos.txt`, com o início e o fim de cada cena.

Use `--sem-musica` para gerar o vídeo sem a trilha.

**Entregue à pessoa:**
- o vídeo;
- o guia de narração e os tempos;
- uma legenda para o post (gancho, passo a passo, prompt completo se houver, "Exemplo ilustrativo." e 3 a 5 hashtags).

Antes de enviar, olhe 4 ou 5 quadros do MP4 final (extraia com ffmpeg).

## Passo 5. A voz (quando a pessoa mandar o áudio)
A pessoa grava a narração seguindo o guia (no celular mesmo, ou com uma voz de IA, se ela preferir). Quando ela enviar o arquivo:

```bash
python3 <pasta-da-skill>/scripts/reel.py roteiro.json --out saida --nome meu-reel --audio /caminho/voz.m4a
```

- Sem marcas de tempo, o script espalha as cenas pelo tamanho do áudio, na proporção de palavras de cada cena.
- Para sincronizar com precisão, coloque no JSON `"marcas_audio": [0, 7.8, 15.2, ...]`, com o segundo em que cada cena começa na gravação. A pessoa pode dizer esses tempos, ou você pode ouvir o arquivo, se tiver uma ferramenta de transcrição com tempo por palavra.
- O resultado é `saida/meu-reel-com-voz.mp4`, com a trilha mais baixa sob a voz.

Outra opção: a pessoa coloca a voz por conta própria num editor de vídeo (CapCut, InShot, o editor do Instagram) usando o vídeo sem voz.

**Lembrete ao entregar:** se houver voz, imagem ou vídeo gerados por IA, a pessoa deve marcar o rótulo de IA ao postar.

## Formato do roteiro.json
```json
{
  "marca": {"cor": "#7C3AED", "arroba": "@seuperfil", "bio": "frase curta do perfil"},
  "palavras_por_segundo": 2.3,
  "cenas": [
    {"selo": "!", "titulo": "Caixa de entrada *lotada?*", "narracao": "...", "exemplo": false,
     "duracao": 6.5,
     "janela": {"tipo": "lista", "...": "..."},
     "nota": {"texto": "Prompt na legenda ↓", "sub": "Salve", "em": 0.4},
     "pilula": {"texto": "dá para desligar", "em": 0.3, "y": 0.4}}
  ]
}
```
- `duracao` é opcional: sem ela, a duração vem da narração.
- O cartão final mostra a inicial do @. Não ponha mascote, a não ser que a pessoa peça.
- `nota` (post-it) e `pilula` (etiqueta flutuante) são opcionais. O valor de `em` é a fração da cena em que eles aparecem (0 a 1).
- A cor é escurecida automaticamente se o texto ficar difícil de ler sobre o branco.

**Marcações nos textos das janelas:** `[[trecho]]` vira marca-texto que aparece durante a cena; `{{trecho}}` vira uma tarja preta que cobre o trecho (dado sigiloso).

| `tipo` | Para quê | Campos |
|---|---|---|
| `lista` | caixa de entrada, lista de tarefas, arquivos | `titulo`, `itens` ([remetente, assunto, prévia]), `nao_lidas` (índices), `destaque` (índice), `tremer`, `destaque_em` |
| `texto` | conversa, anotações, documento | `titulo`, `resumo` ({`titulo`, `linhas`}), `resumo_animado`, `mensagens` ([{`autor`, `texto`}]), `marcar_em`, `tarjar_em`, `etiquetas` (pílulas com ✓), `etiquetas_em` |
| `chat` | assistente de IA (janela escura) | `titulo`, `prompt` (digitado), `resposta` (lista de linhas; opcional), `caracteres_por_segundo` |
| `escrever` | responder e-mail ou mensagem | `titulo`, `texto` (digitado), `botao` |
| `planilha` | tabela simples | `titulo`, `colunas`, `linhas`, `coluna_destaque`, `formula` (opcional: só fórmulas conferidas), `revelar_ultima` |
| `cartao` | novidade, regra ou resumo em destaque | `selo`, `titulo` (aceita `*destaque*`), `texto`, `fonte` (de onde veio a informação) |
| `final` | cartão "Me segue" | `bio`, `botao`, `clique_em` |

## Problemas comuns
- **"não encontrei o ffmpeg":** o script tenta instalar `imageio-ffmpeg` pelo pip sozinho. Se não der, rode `pip install imageio-ffmpeg` (com `--break-system-packages`, se for preciso).
- **Texto cortado ou fora da janela:** encurte o texto, divida em duas mensagens ou use menos itens na lista (cabem cerca de 5 linhas).
- **Legenda muito rápida:** aumente `duracao` da cena ou corte palavras da narração.
- **Fontes:** Inter e JetBrains Mono (licença SIL Open Font, arquivos em `assets/fonts`).