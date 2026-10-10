# Guia de uso

[← Voltar ao README](../README.md) · [← Guia de instalação](INSTALACAO.md)

## O fluxo

1. Fora de casa, mande `/proj` para o bot no Telegram e toque no projeto.
2. O bot abre uma janela no PC rodando `claude --remote-control <projeto>` na pasta do projeto.
3. Em uns 10 segundos, abra o app do Claude → **Code**: a sessão aparece com o nome do projeto. Trabalhe por ali. Toda permissão que o Claude pedir aparece no app para você aprovar.
4. De volta ao PC, a janela está aberta: continue a mesma sessão pelo teclado.

## Comandos do bot

| Comando | O que faz |
| :--- | :--- |
| `/proj` | Lista os projetos com um resumo de cada um, com um botão por projeto. Toque para abrir. |
| `/proj meu-app` | Abre direto. Aceita parte do nome (`/proj meu`); se vários casarem, mostra só os candidatos. |
| `/novo nome resumo opcional` | Cria a pasta do projeto (com `git init`), grava o resumo e abre a sessão. Ex.: `/novo gastos controle de gastos da casa` |
| `/resumo nome texto` | Grava ou troca o resumo que aparece no `/proj`. Ex.: `/resumo gastos app de controle de gastos` |
| `/ajuda` | Mostra os comandos. |

Os comandos também aparecem no menu `/` do Telegram.

**Nome no `/novo`**: letras, números, `.`, `_` e `-`, sem espaço, começando por letra ou número.

**De onde vem o resumo de cada projeto**, nesta ordem:
1. o que você gravou com `/resumo`, `/novo` ou `proj -Resumo`;
2. o primeiro parágrafo de texto do `README.md` do projeto (pula título, badges e imagens);
3. "(sem descrição)".

## Comando `proj` no PowerShell

Depois do [passo 8 da instalação](INSTALACAO.md#8-opcional-comando-proj-no-powershell), o mesmo menu existe no PC:

| Comando | O que faz |
| :--- | :--- |
| `proj` | Menu numerado com o resumo de cada projeto. `0` cria um novo. |
| `proj meu-app` | Entra na pasta e abre o `claude`. Aceita parte do nome. |
| `proj meu-app -Remoto` | Abre com Remote Control, para começar no PC e continuar na rua. |
| `5r` no menu | O mesmo que `-Remoto`, para o projeto 5. |
| `proj meu-app -Resumo "texto"` | Grava o resumo (o mesmo que o bot mostra). |
| `proj meu-app -SemClaude` | Só entra na pasta. |
| `proj <TAB>` | Completa o nome do projeto. |

O `proj` lê a pasta e os resumos da mesma configuração do bot.

## Configuração

Arquivo `%USERPROFILE%\.claude-telegram-bot\config.json`:

| Chave | Padrão | Para quê |
| :--- | :--- | :--- |
| `token` | — | Token do @BotFather (gravado pelo `--configurar`). |
| `projects_root` | `%USERPROFILE%\projetos` | Pasta cujas subpastas são os projetos. Pastas começando com `.` ficam de fora. |
| `allowed_chat_ids` | `[]` | Chats pareados. Só eles controlam o bot. |
| `summaries` | `{}` | Resumos dos projetos. |
| `git_init` | `true` | `false` para o `/novo` não rodar `git init`. |

Depois de editar o arquivo à mão, rode `.\install.ps1 -Reiniciar`.

## Linha de comando do bot

| Comando (`python claude-telegram-bot.py ...`) | Para quê |
| :--- | :--- |
| `--configurar` | Troca o token e/ou a pasta dos projetos (Enter mantém o token atual). |
| `--parear` | Gera um código para liberar mais um chat. |
| `--listar` | Mostra no terminal o que o `/proj` vai listar. |
| `--resumo NOME texto` | Grava o resumo de um projeto. |
| *(sem opção)* | Roda o bot em primeiro plano (útil para depurar; pare a tarefa antes com `-Parar`). |

## Manutenção

| Comando | Para quê |
| :--- | :--- |
| `.\install.ps1 -Status` | A tarefa está rodando? Mostra também as últimas linhas do log. |
| `.\install.ps1 -Reiniciar` | Depois de atualizar o código, trocar o token ou editar a config. |
| `.\install.ps1 -Parar` | Desliga o bot até o próximo logon (ou até `-Reiniciar`). |
| `.\install.ps1 -Desinstalar` | Remove a tarefa (config e log ficam). |

- **Log**: `%USERPROFILE%\.claude-telegram-bot\bot.log`. Aberturas de sessão, pareamentos e mensagens de chats não autorizados ficam registrados nele.
- **Trocar o token** (ex.: vazou): `/revoke` no @BotFather, depois `--configurar` e `-Reiniciar`.
- **Tirar o acesso de um chat**: remova o id de `allowed_chat_ids` no `config.json` e rode `-Reiniciar`.

## Problemas comuns

| Sintoma | Causa provável / o que fazer |
| :--- | :--- |
| O bot não responde nada | PC desligado, ou nenhum usuário logado (a tarefa roda na sua sessão do Windows). Se o PC está ligado: `.\install.ps1 -Status`. |
| Não responde só a você | Seu chat não está pareado (o log mostra "mensagem ignorada"). Rode `--parear`. |
| "Abrindo..." mas a sessão não aparece no app | Olhe a janela no PC. O `claude` precisa estar logado na mesma conta do app e com Remote Control disponível. |
| A janela abre e fecha, ou "claude não encontrado" | O `claude` não está no PATH da sua sessão do Windows. Abra um terminal novo e teste `claude --version`. |
| `/proj` diz que não há projetos | `projects_root` aponta para a pasta errada. Rode `--configurar` e `-Reiniciar`. |
| Respostas em dobro | Não acontece: uma trava local impede duas instâncias do bot. |

## Limites

- Só funciona com o PC **ligado e logado**; o bot não liga o computador.
- Cada `/proj` abre uma **janela nova**: abrir o mesmo projeto duas vezes cria duas sessões.
- Lista só as subpastas diretas de `projects_root`.

## Personalizar

O bot é um arquivo só, com as partes separadas por comentário:

- **Comando do Claude**: `abrir_sessao()` monta `claude --remote-control '<nome>'`. Troque ali para passar outras flags.
- **Novo comando**: crie `cmd_x(tg, cfg, chat, arg)`, registre em `COMANDOS` e em `setMyCommands` (em `rodar()`) e descreva em `AJUDA`.
- **Criação de projeto**: `criar_projeto()` cria a pasta e roda `git init`. É o lugar para copiar um template, criar um `CLAUDE.md` etc.
