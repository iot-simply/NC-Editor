# Hinweise zu Fremdkomponenten und Marken

Der NC-Editor selbst steht unter der MIT-Lizenz (siehe [LICENSE](LICENSE)).
Darüber hinaus werden folgende Komponenten genutzt bzw. mitgeliefert:

| Komponente | Verwendung | Lizenz |
|---|---|---|
| [tkinterdnd2](https://github.com/Eliav2/tkinterdnd2) | Dateien aus dem Explorer in das Fenster ziehen. Copyright (c) 2020 Philippe Gagné | MIT |
| [tkDnD](https://github.com/petasis/tkdnd) | Tk-Erweiterung, auf der tkinterdnd2 aufsetzt. Copyright George Petasis, NCSR „Demokritos" | BSD-artig (Tcl-Stil) |
| [Pillow](https://python-pillow.org/) | Logoanzeige in der Oberfläche, Programmsymbol beim Anmelden unter Windows | MIT-CMU (HPND) |
| [Python](https://www.python.org/) | Laufzeitumgebung; in der `.exe` mitgeliefert | PSF License |
| [Tcl/Tk](https://www.tcl.tk/) | Grafische Oberfläche über `tkinter`; in der `.exe` mitgeliefert | Tcl/Tk License (BSD-artig) |
| [PyInstaller](https://pyinstaller.org/) | Nur zum Bau der `.exe`; der mitgelieferte Bootloader steht unter einer eigenen Ausnahme-Regelung | GPL 2.0 mit Bootloader-Ausnahme |

Pillow und tkinterdnd2 sind **optional**: Fehlen sie, läuft das Programm
weiter – ohne Drag and Drop bzw. mit einfacherer Logoanzeige. In der
fertigen `NC-Editor.exe` sind beide enthalten.

## Vollständige Lizenztexte

Die **vollständigen** Lizenztexte aller hier genannten Komponenten sind
unverändert in `ncedit.py` eingebettet (Konstante `LIZENZEN_Z_B64`) und
lassen sich jederzeit anzeigen:

```bash
python ncedit.py --lizenzen
```

In der grafischen Oberfläche: Schaltfläche **„Lizenzen"** unten rechts. Dort
lässt sich der Text auch als Datei speichern, um ihn weiterzugeben.

## Marken

Der NC-Editor ist ein eigenständiges Programm. Es besteht **keine Verbindung**
zu den Herstellern der unterstützten Steuerungen und Programme; der Editor
wird von ihnen weder herausgegeben noch unterstützt, geprüft oder freigegeben.

Die Namen werden ausschließlich genannt, um zu beschreiben, mit welchen
Dateien und Steuerungsdialekten der Editor umgehen kann:

| Name | Inhaber |
|---|---|
| SINUMERIK, SIMATIC, Siemens | Siemens AG |
| FANUC | FANUC Corporation |
| Haas | Haas Automation, Inc. |
| HEIDENHAIN, TNC, Klartext | DR. JOHANNES HEIDENHAIN GmbH |
| SolidCAM | SolidCAM Ltd. |
| SOLIDWORKS | Dassault Systèmes SolidWorks Corporation |
| Windows, Microsoft, Segoe UI | Microsoft Corporation |
| Python | Python Software Foundation |
| Notepad++ | Don Ho |

Weitere genannte Namen können Marken ihrer jeweiligen Inhaber sein, auch wenn
sie hier nicht eigens aufgeführt sind. Aus dem Fehlen eines Hinweises lässt
sich nicht schließen, dass ein Name frei verwendbar wäre.

Es werden **keine** Programmteile, Bibliotheken oder Dateien dieser Hersteller
mitgeliefert. Der Editor liest und schreibt NC-Programme als reinen Text.

## Ihre NC-Programme

An den Programmen, die Sie mit dem Editor öffnen, ändern und speichern,
erwirbt niemand Rechte – sie bleiben vollständig Ihr Eigentum. Der Editor
arbeitet ausschließlich auf Ihrem Rechner und überträgt nichts ins Internet.

## Hinweis zu PyInstaller

PyInstaller wird ausschließlich zum Bauen der eigenständigen `NC-Editor.exe`
verwendet und ist kein Bestandteil des Quelltextes. Die Bootloader-Ausnahme
der PyInstaller-Lizenz erlaubt ausdrücklich, damit erzeugte Programme unter
beliebiger Lizenz weiterzugeben – der NC-Editor bleibt also auch als `.exe`
MIT-lizenziert.
