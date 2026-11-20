@echo off
REM Startet den NC-Editor direkt aus dem Quelltext (ohne exe zu bauen).
cd /d "%~dp0"
start "" pythonw ncedit.py %*
