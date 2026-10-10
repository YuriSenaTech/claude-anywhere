# claude-anywhere

**Use Claude Code on your own PC from anywhere, no VPS needed.** From Telegram you open a session on your computer, in any project, and drive it from the Claude mobile app.

[Versão em português →](README.md)

```
Telegram: /proj my-app ──► bot on your PC ──► opens Windows Terminal in <projects>\my-app
                                              └─ claude --remote-control my-app
Claude app → Code → "my-app"  ◄────────────── the same session, on your phone
```

## The problem

Claude Code's **Remote Control** lets you continue from your phone a session running on your PC, but the session has to be **started on the PC first**. If you're out and want to start working on a different project, you're stuck.

The usual workarounds are costly or fiddly:

| Alternative | Downside |
| :--- | :--- |
| **VPS** running Claude Code | Monthly bill, a server to maintain, code and credentials off your machine, an environment that isn't yours. |
| **SSH** into the PC (Tailscale/VPN + phone terminal) | Network setup, and typing in a terminal on a phone keyboard. |
| **Cloud sessions** (Claude Code on the web) | Run in a remote environment from the repository, not on your PC with your tools, local files and settings. |

## The solution

A Telegram bot running on **your own PC** that starts the session for you:

- `/proj` lists your projects with a one-line summary each; one tap opens it.
- The session starts with Remote Control and shows up in the Claude app (**Code** tab) in about 10 seconds.
- The terminal window stays **visible on the PC**: back home, you pick up the same session at the keyboard.
- `/novo` creates a project (folder + `git init`) and opens it.
- `proj` in PowerShell gives you the same menu while at the PC.

**Zero infrastructure cost**: no server, no open port, no paid service. The bot long-polls Telegram and runs as a Windows scheduled task. Three scripts, Python standard library only.

## Quick start

Requires Windows 10/11, Python 3.10+, a logged-in Claude Code and a Telegram account.

```powershell
git clone https://github.com/YuriSenaTech/claude-anywhere $env:USERPROFILE\claude-anywhere
cd $env:USERPROFILE\claude-anywhere
python claude-telegram-bot.py --configurar   # @BotFather token + projects folder
.\install.ps1 -Instalar                      # start the bot at Windows logon
python claude-telegram-bot.py --parear       # send /parear CODE to the bot
```

The full guides are in Portuguese: [installation](docs/INSTALACAO.md) and [usage](docs/USO.md). The bot's commands and messages are in Portuguese too.

## Security

- The bot **only obeys paired chats**, using a 6-digit code generated on the PC, valid once for 10 minutes. Messages from any other chat are ignored and logged.
- The token lives in `%USERPROFILE%\.claude-telegram-bot\`, outside the repository.
- The bot only **starts** the session. Everything Claude does afterwards still goes through Claude Code's permission prompts, which you approve in the app.

## Limitations

- The PC must be **on, with your user logged in**.
- Windows only (Windows Terminal, PowerShell, Task Scheduler).

## License

[MIT](LICENSE)
