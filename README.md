# claude-anywhere

**Use o Claude Code do seu PC de qualquer lugar, sem VPS.** Pelo Telegram você abre uma sessão no seu computador, em qualquer projeto, e comanda pelo app do Claude no celular.

[English version →](README.en.md)

```
Telegram: /proj meu-app ──► bot no seu PC ──► abre o Windows Terminal em <projetos>\meu-app
                                              └─ claude --remote-control meu-app
App do Claude → Code → "meu-app"  ◄────────── a mesma sessão, no celular
```

## O problema

O **Remote Control** do Claude Code permite continuar pelo celular uma sessão que está rodando no PC. Mas a sessão precisa **já ter sido aberta no PC** antes de você sair. Se você está na rua e quer começar a trabalhar em outro projeto, não tem como.

As alternativas comuns custam caro ou dão trabalho:

| Alternativa | O que pesa |
| :--- | :--- |
| **VPS** com o Claude Code | Mensalidade, servidor para manter, código e credenciais fora da sua máquina, ambiente diferente do seu. |
| **SSH** no PC (Tailscale/VPN + terminal no celular) | Configuração de rede, e usar um terminal pelo teclado do celular. |
| **Sessões na nuvem** (Claude Code na web) | Rodam num ambiente remoto a partir do repositório, não no seu PC com suas ferramentas, arquivos locais e configurações. |

## A solução

Um bot do Telegram, rodando no **seu próprio PC**, que abre a sessão por você:

- `/proj` lista seus projetos com um resumo de cada um; um toque abre.
- A sessão abre com Remote Control e aparece no app do Claude (aba **Code**) em uns 10 segundos.
- A janela do terminal fica **visível no PC**: quando você voltar, continua a mesma sessão no teclado.
- `/novo` cria um projeto (pasta + `git init`) e já abre.
- O `proj` no PowerShell traz o mesmo menu para quando você está no PC.

**Custo zero de infraestrutura**: nada de servidor, porta aberta ou serviço pago. O bot busca as mensagens no Telegram (long polling) e roda como tarefa do Windows. São três scripts, só com a biblioteca padrão do Python.

## Começo rápido

Precisa de Windows 10/11, Python 3.10+, Claude Code logado e uma conta no Telegram.

```powershell
git clone https://github.com/YuriSenaTech/claude-anywhere $env:USERPROFILE\claude-anywhere
cd $env:USERPROFILE\claude-anywhere
python claude-telegram-bot.py --configurar   # token do @BotFather + pasta dos projetos
.\install.ps1 -Instalar                      # sobe o bot no logon do Windows
python claude-telegram-bot.py --parear       # mande /parear CODIGO para o bot
```

Passo a passo completo, com criação do bot e solução de problemas: **[Guia de instalação](docs/INSTALACAO.md)**.
Todos os comandos do bot e do `proj`: **[Guia de uso](docs/USO.md)**.

## Segurança

- O bot **só obedece a chats pareados**, com um código de 6 dígitos gerado no PC, válido por 10 minutos e uma vez só. As mensagens de qualquer outro chat são ignoradas e ficam registradas no log.
- O token fica em `%USERPROFILE%\.claude-telegram-bot\`, fora do repositório.
- O bot só **abre** a sessão. Tudo o que o Claude fizer depois continua passando pelas permissões do Claude Code, que você aprova no app.

## Limites

- O PC precisa estar **ligado e com seu usuário logado**.
- Só Windows (Windows Terminal, PowerShell, Agendador de Tarefas).

## Arquivos

| Arquivo | Papel |
| :--- | :--- |
| [`claude-telegram-bot.py`](claude-telegram-bot.py) | O bot: comandos, pareamento, abertura da sessão. |
| [`install.ps1`](install.ps1) | Instala, reinicia, para e mostra o status da tarefa no Windows. |
| [`proj.ps1`](proj.ps1) | Comando `proj` para o PowerShell, com a mesma lista e os mesmos resumos do bot. |

## Licença

[MIT](LICENSE)
