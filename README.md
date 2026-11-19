# Skills de Reels animados (kit de 3 estilos)

Três skills para o Claude que criam **Reels verticais (1080×1920, MP4)** montados por código (Python + ffmpeg), sem gerador de vídeo por IA. Cada uma tem um estilo visual diferente e usa a cor e o @ da marca de quem pede.

| Skill | Estilo | Indicada para |
|---|---|---|
| [`reel-tela-viva`](reel-tela-viva/) | Tutorial na tela: janelas genéricas sendo usadas, passos numerados, legenda palavra por palavra | Mostrar um passo a passo em telas e apps |
| [`reel-modo-8bit`](reel-modo-8bit/) | Pixel art de tela cheia com cara de videogame: fases, barra de progresso, sons 8 bits | Conteúdo leve e divertido, estilo jogo retrô |
| [`reel-hora-dourada`](reel-hora-dourada/) | Traço flat de vídeo explicativo, com bonequinhos vetoriais e títulos animados | Contar uma história, um caso ou um mini tutorial |

## Como instalar uma skill no Claude

1. Baixe este repositório (botão verde **Code → Download ZIP**) e descompacte.
2. Compacte em `.zip` **a pasta da skill** que você quer (por exemplo, a pasta `reel-tela-viva` inteira).
3. No Claude, abra as configurações de Skills e faça o upload desse `.zip`.
4. Peça no chat, por exemplo: *"Faz um Reel no estilo Tela Viva sobre como organizar a caixa de e-mail"*.

## Estrutura de cada skill

```
reel-xxx/
├── SKILL.md        ← instruções que o Claude segue (o "cérebro" da skill)
├── scripts/        ← código Python que desenha e monta o vídeo
├── exemplos/       ← roteiros de exemplo prontos para testar
└── assets/fonts/   ← fontes usadas (licença livre OFL, arquivos de licença incluídos)
```

## Requisitos (o ambiente do Claude já costuma ter)

- Python 3 com a biblioteca Pillow
- ffmpeg

## Como validar / dar feedback

1. Instale a skill e peça um Reel com um tema real do seu dia a dia.
2. Confira: o vídeo abre? A legenda acompanha? As cores da marca foram aplicadas? O tempo ficou entre 30 e 60 s?
3. Registre o que achou em **Issues** (aba no topo desta página → *New issue*), dizendo qual skill testou, o pedido que fez e o que deu certo ou errado.

## Licenças

- Fontes: SIL Open Font License (OFL); os textos das licenças estão em `assets/fonts/` de cada skill.
- Código e textos das skills: ainda sem licença de uso definida (por padrão, todos os direitos ficam com a autora). Para permitir que outras pessoas reutilizem e adaptem, adicione um arquivo `LICENSE` (por exemplo, MIT).
