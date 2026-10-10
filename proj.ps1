# --- proj: menu dos seus projetos no PowerShell, abrindo o claude na pasta ---
# Carregue no seu perfil do PowerShell (notepad $PROFILE):
#   . "$env:USERPROFILE\claude-anywhere\proj.ps1"
#
#   proj                      menu numerado com resumo de cada projeto (0 = novo)
#   proj meu-app              entra direto (casa nome exato ou parcial)
#   proj meu-app -Remoto      abre o claude com Remote Control (continua pelo celular)
#   proj meu-app -SemClaude   so entra na pasta
#   proj meu-app -Resumo "..." grava o resumo exibido no menu e no /proj do bot
#
# Usa a mesma configuracao do bot (pasta dos projetos e resumos) via claude-telegram-bot.py.
# Sem Python ou sem config: usa $env:USERPROFILE\projetos e mostra o menu sem resumos.

$script:ProjBot = Join-Path $PSScriptRoot 'claude-telegram-bot.py'

# Chama o bot com saida UTF-8 (sem isso os acentos chegam quebrados)
function Invoke-ProjBot {
    param([string[]]$Argumentos)
    if (-not (Get-Command python -ErrorAction SilentlyContinue) -or -not (Test-Path $script:ProjBot)) { return $null }
    $enc = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        return & python $script:ProjBot @Argumentos 2>$null
    } finally {
        [Console]::OutputEncoding = $enc
    }
}

# { root; projects = [{name, path, summary}] }
function Get-ProjDados {
    $json = Invoke-ProjBot @('--json')
    if ($LASTEXITCODE -eq 0 -and $json) {
        try { return ($json -join "`n") | ConvertFrom-Json } catch { }
    }
    $root = Join-Path $env:USERPROFILE 'projetos'
    $lista = @(Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue |
               Where-Object { $_.Name -notmatch '^\.' } | Sort-Object Name |
               ForEach-Object { [pscustomobject]@{ name = $_.Name; path = $_.FullName; summary = '' } })
    return [pscustomobject]@{ root = $root; projects = $lista }
}

function Set-ProjetoResumo {
    param([string]$Nome, [string]$Resumo)
    if ([string]::IsNullOrWhiteSpace($Resumo)) { return }
    $saida = Invoke-ProjBot @('--resumo', $Nome, $Resumo)
    if ($LASTEXITCODE -eq 0) { Write-Host "   resumo gravado: $saida" -ForegroundColor DarkGray }
    else { Write-Host '   nao foi possivel gravar o resumo (Python e config do bot ok?)' -ForegroundColor Yellow }
}

# Entra na pasta e abre o claude (a menos que -SemClaude). -Remoto liga o Remote Control.
function Enter-Projeto {
    param([string]$Path, [switch]$SemClaude, [switch]$Remoto)
    Set-Location -LiteralPath $Path
    Write-Host "-> $Path" -ForegroundColor Green
    if ($SemClaude) { return }
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Write-Host "Comando 'claude' nao encontrado no PATH." -ForegroundColor Red
        return
    }
    if ($Remoto) {
        $nome = Split-Path $Path -Leaf
        $Host.UI.RawUI.WindowTitle = "$nome (remote)"
        claude --remote-control $nome
    } else {
        claude
    }
}

function New-Projeto {
    param([string]$Root, [string]$Nome, [string]$Resumo, [switch]$SemClaude, [switch]$Remoto)

    if ([string]::IsNullOrWhiteSpace($Nome)) { $Nome = "$(Read-Host 'Nome do novo projeto')".Trim() }
    if ([string]::IsNullOrWhiteSpace($Nome)) { Write-Host 'Cancelado.' -ForegroundColor DarkGray; return }
    if ($Nome -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') {
        Write-Host "Nome invalido: '$Nome' (use letras, numeros, . _ -)" -ForegroundColor Red
        return
    }
    $dir = Join-Path $Root $Nome
    if (Test-Path $dir) { Write-Host "Ja existe: $dir (use 'proj $Nome')" -ForegroundColor Yellow; return }
    if (-not $Resumo) { $Resumo = "$(Read-Host 'Resumo em uma frase (Enter = pular)')".Trim() }

    New-Item -ItemType Directory -Path $dir | Out-Null
    Write-Host "Pasta criada: $dir" -ForegroundColor Green
    if (Get-Command git -ErrorAction SilentlyContinue) {
        git -C $dir init -b main --quiet
        Write-Host '   git init (main)' -ForegroundColor DarkGray
    }
    Set-ProjetoResumo $Nome $Resumo
    Enter-Projeto $dir -SemClaude:$SemClaude -Remoto:$Remoto
}

function proj {
    [CmdletBinding()]
    param(
        [Parameter(Position = 0)]
        [string]$Nome,
        [switch]$SemClaude,
        [switch]$Remoto,
        [string]$Resumo
    )

    $dados = Get-ProjDados
    if (-not (Test-Path $dados.root)) {
        Write-Host "Pasta de projetos nao encontrada: $($dados.root) (rode o --configurar do bot)" -ForegroundColor Red
        return
    }
    $lista = @($dados.projects)

    # Com argumento: tenta casar direto
    if ($Nome) {
        $exato = @($lista | Where-Object { $_.name -eq $Nome })
        # @(...) em volta: o if desembrulha array de 1 item e o .Count de PSCustomObject falha no PS 5.1
        $match = @(if ($exato) { $exato } else { $lista | Where-Object { $_.name -like "*$Nome*" } })
        if ($match.Count -eq 1) {
            if ($PSBoundParameters.ContainsKey('Resumo')) { Set-ProjetoResumo $match[0].name $Resumo; return }
            Enter-Projeto $match[0].path -SemClaude:$SemClaude -Remoto:$Remoto
            return
        }
        if ($match.Count -eq 0) {
            Write-Host "Nenhum projeto casa com '$Nome'." -ForegroundColor Yellow
        } else {
            Write-Host "Varios projetos casam com '$Nome':" -ForegroundColor Yellow
            $lista = $match
        }
    }

    # Menu numerado com resumo
    $largura = ($lista | ForEach-Object { $_.name.Length } | Measure-Object -Maximum).Maximum
    $maxResumo = [Math]::Max(20, $Host.UI.RawUI.WindowSize.Width - $largura - 9)

    Write-Host ''
    Write-Host "Projetos em $($dados.root)" -ForegroundColor Cyan
    Write-Host '  0. + novo projeto' -ForegroundColor Magenta
    for ($i = 0; $i -lt $lista.Count; $i++) {
        Write-Host ('{0,3}. {1}' -f ($i + 1), $lista[$i].name.PadRight($largura)) -NoNewline
        $r = $lista[$i].summary
        if ($r) {
            if ($r.Length -gt $maxResumo) { $r = $r.Substring(0, $maxResumo - 1) + [char]0x2026 }
            Write-Host "  $r" -ForegroundColor DarkGray
        } else {
            Write-Host ''
        }
    }
    Write-Host '  (Enter vazio = cancelar - numero seguido de r = Remote Control, ex.: 5r)' -ForegroundColor DarkGray
    Write-Host ''

    $escolha = "$(Read-Host 'Qual projeto? (numero ou nome)')".Trim()
    if ([string]::IsNullOrWhiteSpace($escolha)) { Write-Host 'Cancelado.' -ForegroundColor DarkGray; return }

    # sufixo "r" (ex.: 5r) = abrir com Remote Control
    if ($escolha -match '^(\d+)\s*r$') { $escolha = $Matches[1]; $Remoto = $true }

    if ($escolha -eq '0') { New-Projeto -Root $dados.root -SemClaude:$SemClaude -Remoto:$Remoto; return }

    $alvo = $null
    if ($escolha -match '^\d+$') {
        $idx = [int]$escolha - 1
        if ($idx -ge 0 -and $idx -lt $lista.Count) { $alvo = $lista[$idx] }
    } else {
        $alvo = $lista | Where-Object { $_.name -eq $escolha } | Select-Object -First 1
        if (-not $alvo) { $alvo = $lista | Where-Object { $_.name -like "*$escolha*" } | Select-Object -First 1 }
    }
    if (-not $alvo) { Write-Host "Opcao invalida: $escolha" -ForegroundColor Red; return }

    Enter-Projeto $alvo.path -SemClaude:$SemClaude -Remoto:$Remoto
}

# Autocomplete com TAB: proj <TAB> percorre os projetos
Register-ArgumentCompleter -CommandName proj -ParameterName Nome -ScriptBlock {
    param($cmd, $param, $wordToComplete)
    (Get-ProjDados).projects | Where-Object { $_.name -like "$wordToComplete*" } |
        ForEach-Object { [System.Management.Automation.CompletionResult]::new($_.name, $_.name, 'ParameterValue', $_.path) }
}
