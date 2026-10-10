"""Bot do Telegram que abre sessões do Claude Code no PC (Windows) com Remote Control.

Pelo Telegram você escolhe (ou cria) um projeto da sua pasta de projetos; o bot abre
uma janela VISÍVEL do Windows Terminal na pasta rodando `claude --remote-control <projeto>`.
A sessão aparece no app do Claude (aba Code) para continuar pelo celular, e a janela
fica aberta no PC para continuar dali quando você voltar.

Segurança: só responde aos chats pareados (allowed_chat_ids). Mensagens de qualquer
outro chat são ignoradas e registradas no log. Token, chats e resumos ficam em
%USERPROFILE%/.claude-telegram-bot/config.json, fora de qualquer repositório.

Uso:
  python claude-telegram-bot.py --configurar   # token + pasta de projetos
  python claude-telegram-bot.py --parear       # mostra um código; mande /parear CODIGO no bot
  python claude-telegram-bot.py --listar       # testa a listagem de projetos no terminal
  python claude-telegram-bot.py --json         # a mesma lista em JSON (usada pelo proj.ps1)
  python claude-telegram-bot.py --resumo NOME texto   # grava o resumo de um projeto
  python claude-telegram-bot.py                # roda o bot (a tarefa do Windows usa pythonw.exe)

Instalação no logon do Windows: .\\install.ps1 -Instalar
Sem dependências: só a biblioteca padrão do Python 3.10+.
"""
from __future__ import annotations

import base64
import getpass
import json
import logging
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_DIR = Path.home() / ".claude-telegram-bot"
CONFIG = CONFIG_DIR / "config.json"
LOG = CONFIG_DIR / "bot.log"
LOCK_PORT = 47392  # porta local usada só como trava de instância única
PAREAMENTO_MIN = 10
MAX_RESUMO = 90
VAZIO = "(sem descrição)"
NOME_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

AJUDA = (
    "Sessões do Claude Code no PC\n\n"
    "/proj — lista os projetos (toque para abrir)\n"
    "/proj nome — abre direto (aceita parte do nome)\n"
    "/novo nome resumo opcional — cria a pasta (+ git init) e abre\n"
    "/resumo nome texto — grava o resumo exibido no /proj\n"
    "/ajuda — esta mensagem\n\n"
    "A sessão abre numa janela visível no PC com Remote Control. "
    "No app do Claude, aba Code, ela aparece com o nome do projeto."
)

log = logging.getLogger("claude-telegram-bot")


# ---------------------------------------------------------------- config
def carregar_config() -> dict:
    if not CONFIG.is_file():
        return {}
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def salvar_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def raiz_projetos(cfg: dict) -> Path:
    return Path(cfg.get("projects_root") or Path.home() / "projetos")


# ---------------------------------------------------------------- telegram
class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}/"

    def chamar(self, metodo: str, http_timeout: int = 30, **params):
        dados = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(
            self.base + metodo, data=dados, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=http_timeout) as resp:
            corpo = json.loads(resp.read().decode("utf-8"))
        if not corpo.get("ok"):
            raise RuntimeError(f"{metodo}: {corpo}")
        return corpo["result"]

    def enviar(self, chat_id: int, texto: str, **extra) -> None:
        if len(texto) > 4000:  # limite do Telegram é 4096
            texto = texto[:3990] + "\n…"
        self.chamar("sendMessage", chat_id=chat_id, text=texto, **extra)


# ---------------------------------------------------------------- resumos
def _limpar(texto: str) -> str:
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)  # links markdown
    texto = re.sub(r"[*_`]", "", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _primeira_frase(texto: str) -> str:
    m = re.search(r"(?<=[a-zà-ú0-9)\"])(\.\s|:\s|\s—\s|;\s)", texto)
    return texto[: m.start()] if m else texto


def _encurtar(texto: str) -> str:
    texto = texto.rstrip(" .")
    if len(texto) <= MAX_RESUMO:
        return texto
    return texto[: MAX_RESUMO - 1].rsplit(" ", 1)[0] + "…"


def _do_readme(pasta: Path) -> str | None:
    """Primeiro parágrafo de texto do README (pula título, badges, imagens, código)."""
    readme = next((p for p in (pasta / "README.md", pasta / "readme.md") if p.is_file()), None)
    if not readme:
        return None
    paragrafo: list[str] = []
    em_codigo = False
    for linha in readme.read_text(encoding="utf-8", errors="replace").splitlines():
        s = linha.strip()
        if s.startswith("```"):
            em_codigo = not em_codigo
            continue
        if em_codigo:
            continue
        if not s:
            if paragrafo:
                break
            continue
        if s.startswith(("#", "!", "<", ">", "|", "[!", "---")) or re.fullmatch(r"\[[^\]]*\]\([^)]*\)", s.strip("*_")):
            if paragrafo:
                break
            continue
        paragrafo.append(s)
    return (_primeira_frase(_limpar(" ".join(paragrafo))) or None) if paragrafo else None


def resumo(cfg: dict, pasta: Path) -> str:
    """Resumo gravado com /resumo; senão o README; senão '(sem descrição)'."""
    texto = cfg.get("summaries", {}).get(pasta.name) or _do_readme(pasta)
    return _encurtar(texto) if texto else VAZIO


# ---------------------------------------------------------------- projetos
def projetos(cfg: dict) -> list[dict]:
    raiz = raiz_projetos(cfg)
    if not raiz.is_dir():
        return []
    pastas = sorted(
        (p for p in raiz.iterdir() if p.is_dir() and not p.name.startswith(".")),
        key=lambda p: p.name.lower(),
    )
    return [{"name": p.name, "path": str(p), "summary": resumo(cfg, p)} for p in pastas]


def achar_projeto(cfg: dict, termo: str) -> tuple[dict | None, list[dict]]:
    """Nome exato, senão parcial. Devolve (único, candidatos)."""
    todos = projetos(cfg)
    exato = [p for p in todos if p["name"].lower() == termo.lower()]
    if exato:
        return exato[0], exato
    parcial = [p for p in todos if termo.lower() in p["name"].lower()]
    return (parcial[0] if len(parcial) == 1 else None), parcial


def _ps(texto: str) -> str:
    return texto.replace("'", "''")


def abrir_sessao(projeto: dict) -> None:
    """Abre uma janela nova (Windows Terminal, se houver) com o claude em Remote Control."""
    nome, caminho = projeto["name"], projeto["path"]
    script = (
        f"Set-Location -LiteralPath '{_ps(caminho)}'; "
        f"$Host.UI.RawUI.WindowTitle = '{_ps(nome)} (remote)'; "
        f"claude --remote-control '{_ps(nome)}'"
    )
    # base64: o wt trata ";" e aspas como sintaxe própria; o -EncodedCommand passa intacto
    codificado = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    powershell = ["powershell.exe", "-NoExit", "-ExecutionPolicy", "Bypass", "-EncodedCommand", codificado]
    if shutil.which("wt.exe"):
        cmd = ["wt.exe", "-w", "new", "new-tab", "--title", f"{nome} (remote)", "-d", caminho, *powershell]
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:  # sem Windows Terminal: console clássico do PowerShell
        cmd = powershell
        flags = subprocess.CREATE_NEW_CONSOLE | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(cmd, cwd=caminho, creationflags=flags, close_fds=True)
    log.info("sessão aberta: %s", caminho)


def criar_projeto(cfg: dict, nome: str, resumo_txt: str) -> Path:
    pasta = raiz_projetos(cfg) / nome
    pasta.mkdir(parents=True)
    if cfg.get("git_init", True) and shutil.which("git"):
        subprocess.run(
            ["git", "init", "-b", "main", "--quiet", str(pasta)],
            check=False, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    if resumo_txt:
        cfg.setdefault("summaries", {})[nome] = resumo_txt
        salvar_config(cfg)
    log.info("projeto criado: %s", pasta)
    return pasta


# ---------------------------------------------------------------- comandos
def teclado_projetos(lista: list[dict]) -> dict:
    botoes = [{"text": p["name"], "callback_data": f"o:{p['name']}"[:64]} for p in lista]
    return {"inline_keyboard": [botoes[i : i + 2] for i in range(0, len(botoes), 2)]}


def texto_lista(lista: list[dict]) -> str:
    linhas = [f"• {p['name']} — {p['summary']}" for p in lista]
    return "Projetos (toque para abrir com Remote Control):\n\n" + "\n".join(linhas)


def abrir(tg: Telegram, chat: int, projeto: dict) -> None:
    try:
        abrir_sessao(projeto)
    except Exception as e:  # noqa: BLE001 — devolve o erro ao usuário
        log.exception("falha ao abrir %s", projeto["name"])
        tg.enviar(chat, f"Falhou ao abrir {projeto['name']}: {e}")
        return
    tg.enviar(
        chat,
        f"Abrindo {projeto['name']} no PC.\n"
        f"Em uns 10 s a sessão \"{projeto['name']}\" aparece no app do Claude → Code.",
    )


def cmd_proj(tg: Telegram, cfg: dict, chat: int, arg: str) -> None:
    if not arg:
        lista = projetos(cfg)
        if not lista:
            tg.enviar(chat, f"Nenhum projeto em {raiz_projetos(cfg)}. Crie um com /novo nome.")
            return
        tg.enviar(chat, texto_lista(lista), reply_markup=teclado_projetos(lista))
        return
    unico, candidatos = achar_projeto(cfg, arg)
    if unico:
        abrir(tg, chat, unico)
    elif candidatos:
        tg.enviar(chat, texto_lista(candidatos), reply_markup=teclado_projetos(candidatos))
    else:
        tg.enviar(chat, f"Nenhum projeto casa com '{arg}'. Use /proj para ver todos ou /novo {arg}.")


def cmd_novo(tg: Telegram, cfg: dict, chat: int, arg: str) -> None:
    partes = arg.split(maxsplit=1)
    if not partes:
        tg.enviar(chat, "Uso: /novo nome resumo opcional\nEx.: /novo gastos controle de gastos da casa")
        return
    nome, resumo_txt = partes[0], (partes[1] if len(partes) > 1 else "")
    if not NOME_VALIDO.match(nome):
        tg.enviar(chat, "Nome inválido: use letras, números, . _ - (sem espaço).")
        return
    if (raiz_projetos(cfg) / nome).exists():
        tg.enviar(chat, f"{nome} já existe. Use /proj {nome}.")
        return
    try:
        criar_projeto(cfg, nome, resumo_txt)
    except OSError as e:
        tg.enviar(chat, f"Não consegui criar {nome}: {e}")
        return
    unico, _ = achar_projeto(cfg, nome)
    abrir(tg, chat, unico)


def cmd_resumo(tg: Telegram, cfg: dict, chat: int, arg: str) -> None:
    partes = arg.split(maxsplit=1)
    if len(partes) < 2:
        tg.enviar(chat, "Uso: /resumo nome texto do resumo")
        return
    unico, candidatos = achar_projeto(cfg, partes[0])
    if not unico:
        nomes = ", ".join(p["name"] for p in candidatos) or "nenhum"
        tg.enviar(chat, f"Projeto ambíguo ou inexistente ({nomes}).")
        return
    texto = re.sub(r"\s+", " ", partes[1]).strip()
    cfg.setdefault("summaries", {})[unico["name"]] = texto
    salvar_config(cfg)
    tg.enviar(chat, f"Resumo de {unico['name']} gravado: {texto}")


COMANDOS = {"proj": cmd_proj, "abrir": cmd_proj, "novo": cmd_novo, "resumo": cmd_resumo}


def tratar(tg: Telegram, cfg: dict, upd: dict) -> None:
    permitidos = set(cfg.get("allowed_chat_ids", []))

    if "callback_query" in upd:
        cq = upd["callback_query"]
        chat = cq["message"]["chat"]["id"]
        tg.chamar("answerCallbackQuery", callback_query_id=cq["id"])
        if chat not in permitidos:
            log.warning("callback de chat não autorizado: %s", chat)
            return
        dado = cq.get("data", "")
        if dado.startswith("o:"):
            unico, _ = achar_projeto(cfg, dado[2:])
            if unico and unico["name"] == dado[2:]:
                abrir(tg, chat, unico)
        return

    msg = upd.get("message") or {}
    texto = (msg.get("text") or "").strip()
    chat = (msg.get("chat") or {}).get("id")
    if not texto or chat is None:
        return

    if chat not in permitidos:
        codigo = cfg.get("pairing_code")
        valido = codigo and time.time() < cfg.get("pairing_expires", 0)
        if valido and texto.split()[:2] == ["/parear", codigo]:
            cfg.setdefault("allowed_chat_ids", []).append(chat)
            cfg.pop("pairing_code", None)
            cfg.pop("pairing_expires", None)
            salvar_config(cfg)
            log.info("chat pareado: %s", chat)
            tg.enviar(chat, "Pareado! Este chat agora controla o PC.\n\n" + AJUDA)
        else:
            log.warning("mensagem ignorada de chat não autorizado %s: %r", chat, texto[:80])
        return

    if not texto.startswith("/"):
        tg.enviar(chat, AJUDA)
        return
    cabeca, _, arg = texto.partition(" ")
    fn = COMANDOS.get(cabeca[1:].split("@")[0].lower())
    if fn:
        fn(tg, cfg, chat, arg.strip())
    else:
        tg.enviar(chat, AJUDA)


# ---------------------------------------------------------------- loop
def rodar() -> None:
    cfg = carregar_config()
    if not cfg.get("token"):
        sys.exit(f"Sem token. Rode: python {Path(__file__).name} --configurar")

    trava = socket.socket()
    try:
        trava.bind(("127.0.0.1", LOCK_PORT))
    except OSError:
        log.info("outra instância já está rodando; saindo")
        return

    tg = Telegram(cfg["token"])
    try:
        tg.chamar(
            "setMyCommands",
            commands=[
                {"command": "proj", "description": "Listar/abrir projeto com Remote Control"},
                {"command": "novo", "description": "Criar projeto: /novo nome resumo"},
                {"command": "resumo", "description": "Gravar resumo: /resumo nome texto"},
                {"command": "ajuda", "description": "Como usar"},
            ],
        )
    except Exception:  # noqa: BLE001 — sem rede no boot; segue para o loop com retry
        log.warning("setMyCommands falhou (sem rede?)")

    log.info("bot iniciado; pasta %s; chats permitidos: %s", raiz_projetos(cfg), cfg.get("allowed_chat_ids", []))
    offset, espera = None, 5
    while True:
        try:
            params = {"timeout": 50, "allowed_updates": ["message", "callback_query"]}
            if offset is not None:
                params["offset"] = offset
            # timeout HTTP maior que o long polling, senão a conexão cai antes da resposta
            updates = tg.chamar("getUpdates", http_timeout=60, **params)
            espera = 5
            for upd in updates:
                offset = upd["update_id"] + 1
                cfg = carregar_config()  # pega pareamentos feitos por --parear
                try:
                    tratar(tg, cfg, upd)
                except Exception:  # noqa: BLE001 — um update ruim não derruba o bot
                    log.exception("erro tratando update %s", upd.get("update_id"))
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            log.warning("rede: %s — tentando de novo em %ss", e, espera)
            time.sleep(espera)
            espera = min(espera * 2, 300)
        except Exception:  # noqa: BLE001
            log.exception("erro no loop")
            time.sleep(espera)
            espera = min(espera * 2, 300)


def configurar() -> None:
    cfg = carregar_config()
    token = getpass.getpass("Token do bot (do @BotFather, não aparece ao digitar; Enter = manter): ").strip()
    if token:
        me = Telegram(token).chamar("getMe")
        cfg["token"] = token
        print(f"Token ok: @{me['username']}")
    elif not cfg.get("token"):
        sys.exit("Cancelado: sem token.")

    atual = raiz_projetos(cfg)
    pasta = input(f"Pasta dos projetos [{atual}]: ").strip().strip('"') or str(atual)
    if not Path(pasta).is_dir():
        sys.exit(f"Pasta não existe: {pasta}")
    cfg["projects_root"] = str(Path(pasta).resolve())
    salvar_config(cfg)
    print(f"Gravado em {CONFIG}")


def parear() -> None:
    cfg = carregar_config()
    if not cfg.get("token"):
        sys.exit("Configure o token primeiro: --configurar")
    cfg["pairing_code"] = f"{secrets.randbelow(10**6):06d}"
    cfg["pairing_expires"] = time.time() + PAREAMENTO_MIN * 60
    salvar_config(cfg)
    print(f"No Telegram, mande para o bot:  /parear {cfg['pairing_code']}")
    print(f"(o bot precisa estar rodando; o código vale {PAREAMENTO_MIN} minutos e uma vez só)")


def listar(como_json: bool) -> None:
    cfg = carregar_config()
    if como_json:  # usado pelo proj.ps1
        print(json.dumps({"root": str(raiz_projetos(cfg)), "projects": projetos(cfg)}, ensure_ascii=False))
        return
    print(f"Pasta: {raiz_projetos(cfg)}")
    for p in projetos(cfg):
        print(f"  {p['name']:<24} {p['summary']}")


def gravar_resumo(nome: str, texto: str) -> None:
    cfg = carregar_config()
    if not (raiz_projetos(cfg) / nome).is_dir():
        sys.exit(f"Projeto não encontrado: {nome}")
    texto = re.sub(r"\s+", " ", texto).strip()
    if not texto:
        sys.exit("Resumo vazio.")
    cfg.setdefault("summaries", {})[nome] = texto
    salvar_config(cfg)
    print(f"{nome}: {texto}")


def main() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG, level=logging.INFO, encoding="utf-8",
        format="%(asctime)s %(levelname)s %(message)s",
    )
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")
    if "--configurar" in sys.argv:
        configurar()
    elif "--parear" in sys.argv:
        parear()
    elif "--listar" in sys.argv or "--json" in sys.argv:
        listar("--json" in sys.argv)
    elif len(sys.argv) >= 4 and sys.argv[1] == "--resumo":
        gravar_resumo(sys.argv[2], " ".join(sys.argv[3:]))
    else:
        rodar()


if __name__ == "__main__":
    main()
