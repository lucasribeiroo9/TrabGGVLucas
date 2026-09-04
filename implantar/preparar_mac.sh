#!/bin/zsh
# Prepara um Mac para ser servidor do escritório: nunca dorme, volta sozinho
# depois de queda de energia e não desliga o disco.
#
#     sudo zsh implantar/preparar_mac.sh
#
# Pede senha de administrador — são ajustes de sistema, não do projeto.
#
# Se esta máquina JÁ é o servidor do previdenciário (porta 8770), não há nada a
# refazer aqui: os ajustes são da máquina, não do sistema. Rodar de novo não
# quebra nada, mas o nome da máquina será reescrito — veja a linha do
# ComputerName antes.
set -e
[ "$(id -u)" = "0" ] || { echo "✗ rode com sudo"; exit 1; }

echo "→ energia: sem dormir, sem desligar disco, volta após queda de luz"
pmset -a sleep 0 disksleep 0 displaysleep 15 womp 1 autorestart 1 powernap 0

echo "→ desliga a suspensão por inatividade do sistema"
systemsetup -setcomputersleep Never >/dev/null 2>&1 || true

echo "→ liga o acesso remoto por SSH (para manutenção sem ir até a máquina)"
systemsetup -setremotelogin on >/dev/null 2>&1 || true

# Só nomeia se ainda não houver nome de servidor: numa máquina que já serve o
# previdenciário, reescrever o nome quebraria quem acessa por ele.
atual=$(scutil --get ComputerName 2>/dev/null || echo "")
if [[ "$atual" == *"servidor"* ]]; then
  echo "→ nome da máquina já é '$atual' — mantido"
else
  echo "→ nome da máquina na rede: ggv-servidor"
  scutil --set ComputerName "ggv-servidor"
  scutil --set LocalHostName "ggv-servidor"
  scutil --set HostName "ggv-servidor"
fi

echo
echo "✓ pronto. Confira com:  pmset -g custom"
echo "  Falta na interface (não dá para script):"
echo "   · Ajustes › Usuários › Opções de início: ligar início automático de sessão"
echo "     (só faz sentido com FileVault DESLIGADO — ver INSTALACAO.md)"
echo "   · Ajustes › Geral › Compartilhamento: ligar Compartilhamento de Tela"
echo
echo "  Depois:  cp implantar/com.ggvtrab.portal.plist ~/Library/LaunchAgents/"
echo "           (trocar SEU_USUARIO e o segredo dentro do arquivo)"
echo "           launchctl load -w ~/Library/LaunchAgents/com.ggvtrab.portal.plist"
