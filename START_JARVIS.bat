@echo off
title J.A.R.V.I.S. SYSTEM BOOT
echo [1/3] Starting Unlimited Local AI Engine (Ollama)...
start "" ollama serve

echo [2/3] Starting Hybrid Cloud/Local Router (LiteLLM)...
start "LiteLLM Router" cmd /k "cd /d B:\JARVIS && set LITELLM_DANGEROUSLY_PERMIT_WEAK_OR_UNSET_MASTER_KEY=true && venv\Scripts\litellm.exe --config config.yaml --port 4000"

timeout /t 5 >nul

echo [3/3] Launching J.A.R.V.I.S. Server and Ultron HUD...
start "JARVIS Core" cmd /k "cd /d B:\JARVIS && venv\Scripts\python.exe jarvis_server.py"
timeout /t 3 >nul
start chrome --app=http://localhost:8000