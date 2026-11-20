@echo off
REM Erstellt NC-Editor.exe (eigenstaendig, kein Python auf dem Zielrechner noetig)
REM Voraussetzung: Python 3.9+ installiert (python.org, Haken bei "Add to PATH")
REM Das iot-simply-Logo ist im Programm eingebaut und wird auch als Programmsymbol verwendet.
cd /d "%~dp0"
python -m pip install --upgrade pip
python -m pip install pillow tkinterdnd2 pyinstaller
python ncedit.py --icon-export ncedit_icon.png
python -m PyInstaller --onefile --noconsole --name NC-Editor --icon ncedit_icon.png ^
    --hidden-import PIL.ImageTk --hidden-import PIL.ImageDraw ^
    --hidden-import webbrowser --collect-all tkinterdnd2 ncedit.py
del ncedit_icon.png
echo.
echo Fertig: dist\NC-Editor.exe
echo.
echo Danach einmalig als Programm fuer .mpf und .nc anmelden:
echo   dist\NC-Editor.exe --registrieren
pause
