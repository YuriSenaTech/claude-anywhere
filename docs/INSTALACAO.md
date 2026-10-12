# Guia de instalação

Uns 10 minutos, uma vez só. No fim, você manda `/proj` no Telegram e uma sessão do Claude Code abre no seu PC.

[← Voltar ao README](../README.md) · [Guia de uso →](USO.md)

## 1. Confira os requisitos

| Requisito | Como conferir |
| :--- | :--- |
| Windows 10 ou 11 | — |
| **Python 3.10+** do [python.org](https://www.python.org/downloads/) (o da Microsoft Store não traz o `pythonw.exe`, que roda o bot sem janela) | `python --version` |
| **Claude Code** instalado e logado na **mesma conta** do app do Claude no celular | `claude --version` |
| **Remote Control** funcionando na sua conta | Rode `claude --remote-control teste` numa pasta qualquer: a sessão "teste" tem que aparecer no app do Claude → **Code**. |
| **Windows Terminal** (recomendado; sem ele, abre no console do PowerShell) | `wt --version` |
| **Git** (opcional, para o `/novo` rodar `git init`) | `git --version` |

Se o teste do Remote Control não funcionar, resolva isso antes: o bot só automatiza a abertura da sessão.

## 2. Baixe o projeto num lugar fixo

```powershell
git clone https://github.com/YuriSenaTech/claude-anywhere $env:USERPROFILE\claude-anywhere
cd $env:USERPROFILE\claude-anywhere
```

Pode ser qualquer pasta, desde que fique fixa: a tarefa do Windows aponta para ela. Se movê-la depois, rode o passo 5 de novo. O exemplo usa a sua pasta de usuário (`C:\Users\<você>\claude-anywhere`), que sempre existe; o `git clone` cria a pasta final sozinho.

Sem Git? No GitHub, clique em **Code → Download ZIP** e extraia o conteúdo para essa mesma pasta (os arquivos `.py` e `.ps1` têm que ficar direto nela, não numa subpasta).

## 3. Crie o bot no Telegram

1. No Telegram, abra o **@BotFather** e mande `/newbot`.
2. Escolha um nome (ex.: "Meu Claude") e um usuário terminado em `bot` (ex.: `meu_claude_pc_bot`).
3. Copie o **token** que ele devolve (algo como `123456789:AAH...`).

> O token é a chave do bot. Não cole em chat, issue nem commit. Se vazar, mande `/revoke` no @BotFather e refaça o passo 4.

Opcional: `/setuserpic` e `/setdescription` no @BotFather para dar foto e descrição ao bot.

## 4. Configure

```powershell
python claude-telegram-bot.py --configurar
```

Ele pergunta duas coisas:

1. **O token**: não aparece ao digitar. O script valida o token no Telegram e mostra o @ do bot.
2. **A pasta dos projetos**: a pasta cujas subpastas são seus projetos (ex.: `C:\projetos`). O padrão é `%USERPROFILE%\projetos`.

Tudo fica em `%USERPROFILE%\.claude-telegram-bot\config.json`, fora do repositório. Para conferir o que o bot vai listar:

```powershell
python claude-telegram-bot.py --listar
```

## 5. Instale a tarefa do Windows

```powershell
.\install.ps1 -Instalar
```

Isso registra a tarefa **ClaudeTelegramBot**, que sobe o bot sem janela quando você entra no Windows e o reinicia se ele cair. A tarefa já começa a rodar na hora.

Se o PowerShell bloquear o script por política de execução:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Instalar
```

Confira com `.\install.ps1 -Status`: tem que mostrar "Processo do bot: rodando".

## 6. Pareie o seu Telegram

Sem pareamento, o bot ignora todo mundo, inclusive você.

```powershell
python claude-telegram-bot.py --parear
```

Ele mostra um código de 6 dígitos. No Telegram, abra o seu bot e mande:

```
/parear 123456
```

O bot responde "Pareado!". O código vale **10 minutos** e uma vez só. Para liberar outro celular ou um grupo, repita este passo nele.

## 7. Teste

1. No Telegram, mande `/proj` e toque num projeto.
2. No PC, uma janela do terminal abre na pasta do projeto rodando o `claude`.
3. Em uns 10 segundos, a sessão aparece no app do Claude → **Code** com o nome do projeto.

> **Não apareceu?** Sem o passo abaixo, **projeto novo não abre pelo celular**. Olhe a janela no PC. Se ela mostra *"Quick safety check: Is this a project you created or one you trust?"*, é a pergunta de confiança que o Claude Code faz na **primeira vez** em cada pasta. Escolha **Yes, I trust this folder** e a sessão aparece no app. Pelo celular não dá para responder, então antes de sair de casa abra cada projeto uma vez no PC (`proj nome`, ou `claude` dentro da pasta) e confirme. Detalhes em [Pasta nova: a pergunta de confiança](USO.md#pasta-nova-a-pergunta-de-confiança).

Pronto. Os comandos estão no [Guia de uso](USO.md).

## 8. (Opcional) Comando `proj` no PowerShell

Para ter no PC o mesmo menu de projetos do bot, adicione ao seu perfil do PowerShell (`notepad $PROFILE`):

```powershell
. "$env:USERPROFILE\claude-anywhere\proj.ps1"
```

Abra um terminal novo e digite `proj`.

## Atualizar

```powershell
cd $env:USERPROFILE\claude-anywhere
git pull
.\install.ps1 -Reiniciar
```

## Desinstalar

```powershell
.\install.ps1 -Desinstalar                              # remove a tarefa
Remove-Item -Recurse $env:USERPROFILE\.claude-telegram-bot   # apaga token, chats pareados e log
```

Depois, apague o bot no @BotFather (`/deletebot`) e tire a linha do `proj.ps1` do seu `$PROFILE`, se tiver colocado.

## Problemas na instalação

| Sintoma | O que fazer |
| :--- | :--- |
| `--configurar` dá erro 401/404 | Token errado ou revogado. Copie de novo do @BotFather. |
| `-Instalar` diz "pythonw.exe nao encontrado" | Instale o Python do python.org (não o da Microsoft Store) e rode de novo. |
| `-Instalar` diz "Sem configuracao ainda" | Faça o passo 4 antes. |
| `/parear` não responde nada | O bot não está rodando (`.\install.ps1 -Status`) ou o código expirou: rode `--parear` de novo. |
| Mais problemas | Veja [Problemas comuns no Guia de uso](USO.md#problemas-comuns). |
