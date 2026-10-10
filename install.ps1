# Instala/controla o claude-telegram-bot.py no Agendador de Tarefas do Windows.
# O bot sobe no logon do usuario, sem janela (pythonw.exe), e reinicia se cair.
#
#   .\install.ps1 -Instalar      registra a tarefa e ja inicia
#   .\install.ps1 -Status        estado da tarefa + ultimas linhas do log (padrao)
#   .\install.ps1 -Reiniciar     para e inicia de novo (ex.: depois de atualizar o script)
#   .\install.ps1 -Parar
#   .\install.ps1 -Desinstalar
param(
    [switch]$Instalar,
    [switch]$Status,
    [switch]$Reiniciar,
    [switch]$Parar,
    [switch]$Desinstalar
)

$ErrorActionPreference = 'Stop'
$Tarefa = 'ClaudeTelegramBot'
$Bot = Join-Path $PSScriptRoot 'claude-telegram-bot.py'
$ConfigDir = Join-Path $env:USERPROFILE '.claude-telegram-bot'
$Log = Join-Path $ConfigDir 'bot.log'

function Get-Pythonw {
    $py = (Get-Command python -ErrorAction SilentlyContinue).Source
    # o atalho da Microsoft Store (WindowsApps) nao tem pythonw ao lado
    if (-not $py -or $py -like '*WindowsApps*') {
        $py = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue |
              Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
    }
    if (-not $py) { throw 'python.exe nao encontrado. Instale o Python 3.10+ (python.org).' }
    $pyw = Join-Path (Split-Path $py) 'pythonw.exe'
    if (-not (Test-Path $pyw)) { throw "pythonw.exe nao encontrado ao lado de $py" }
    return $pyw
}

function Get-BotProcess {
    @(Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" |
      Where-Object { $_.CommandLine -like '*claude-telegram-bot.py*' })
}

function Stop-Bot {
    Stop-ScheduledTask -TaskName $Tarefa -ErrorAction SilentlyContinue
    # o pythonw iniciado pela tarefa pode sobreviver ao Stop: encerra pelo caminho do script
    Get-BotProcess | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
}

if ($Instalar) {
    if (-not (Test-Path (Join-Path $ConfigDir 'config.json'))) {
        Write-Host "Sem configuracao ainda. Rode antes: python `"$Bot`" --configurar" -ForegroundColor Yellow
        return
    }
    $pyw = Get-Pythonw
    $acao = New-ScheduledTaskAction -Execute $pyw -Argument "`"$Bot`"" -WorkingDirectory $PSScriptRoot
    $gatilho = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $config = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
        -MultipleInstances IgnoreNew -StartWhenAvailable
    # Interactive: roda na sessao do usuario logado, para as janelas do terminal aparecerem
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $Tarefa -Action $acao -Trigger $gatilho -Settings $config `
        -Principal $principal -Description 'Bot do Telegram: abre sessoes do Claude Code com Remote Control' -Force | Out-Null
    Start-ScheduledTask -TaskName $Tarefa
    Write-Host "Tarefa '$Tarefa' instalada e iniciada ($pyw)." -ForegroundColor Green
    Write-Host "Se ainda nao pareou: python `"$Bot`" --parear" -ForegroundColor DarkGray
    return
}

if ($Reiniciar) { Stop-Bot; Start-ScheduledTask -TaskName $Tarefa; Write-Host 'Reiniciado.' -ForegroundColor Green; return }
if ($Parar) { Stop-Bot; Write-Host 'Parado.' -ForegroundColor Yellow; return }

if ($Desinstalar) {
    Stop-Bot
    Unregister-ScheduledTask -TaskName $Tarefa -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Tarefa '$Tarefa' removida (config e log em $ConfigDir ficam)." -ForegroundColor Yellow
    return
}

# padrao: -Status
$t = Get-ScheduledTask -TaskName $Tarefa -ErrorAction SilentlyContinue
if (-not $t) { Write-Host "Tarefa '$Tarefa' nao instalada. Use -Instalar." -ForegroundColor Yellow }
else {
    $info = Get-ScheduledTaskInfo -TaskName $Tarefa
    Write-Host ("Tarefa: {0} | ultima execucao: {1} | resultado: {2}" -f $t.State, $info.LastRunTime, $info.LastTaskResult)
}
$proc = Get-BotProcess
Write-Host ("Processo do bot: {0}" -f $(if ($proc) { "rodando (PID $($proc[0].ProcessId))" } else { 'parado' }))
if (Test-Path $Log) { Write-Host "--- $Log"; Get-Content $Log -Tail 10 -Encoding UTF8 }
