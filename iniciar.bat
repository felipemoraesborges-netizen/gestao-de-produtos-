@echo off
title Gestão de Produtos - Precificação & NF-e
cd /d "%~dp0"
echo =========================================================
echo   Iniciando Gestao de Produtos (FastAPI + React)...
echo =========================================================
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe run_app.py
) else (
    python run_app.py
)
pause
