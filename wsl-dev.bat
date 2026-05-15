@echo off
:: Double-click this to enter the WSL2 dev environment
echo Opening FX Regime Lab dev shell in WSL2...
wsl -d Ubuntu-24.04 -- bash -c "export PATH='/root/.local/bin:\$PATH' && cd /root/fx-regime-lab && exec bash"
