@echo off

start /B python -m textual serve main.py


timeout /T 5 /NOBREAK >nul

start "" "http://localhost:8000"

