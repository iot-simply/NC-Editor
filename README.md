# NC-Editor

**Editor für NC-Programme (`.mpf`, `.nc`) mit Suche, einstellbarer
Farbhervorhebung und Erkennung von Hand-Änderungen – komplett offline.**

Gedacht für den Werkstattrechner: Die Programme kommen aus SolidCAM
(SolidWorks), werden am Rechner noch einmal durchgesehen und an einzelnen
Stellen von Hand angepasst. Genau diese Hand-Anpassungen hebt der Editor
dauerhaft hervor – auch Wochen später und auch dann, wenn zwischendurch ein
anderes Programm die Datei geöffnet hat.

- Version: **2.1**
- Lizenz: **MIT** – Copyright (c) 2026 Christopher Schmick,
  [iot-simply.com](https://iot-simply.com)
- Keine Internetverbindung nötig, es werden keine Daten übertragen.
- Läuft unter **Windows 10 und 11** und kann dort als Standardprogramm für
  `.mpf` und `.nc` eingetragen werden.

---

## Inhalt

- [Funktionen](#funktionen)
- [Installation](#installation)
- [Als Standardprogramm eintragen](#als-standardprogramm-eintragen)
- [Bedienung](#bedienung)
- [Suche](#suche)
- [Was beim Speichern passiert](#was-beim-speichern-passiert)
- [Hand-Änderungen](#hand-änderungen)
- [Farben](#farben)
- [Steuerungsdialekte](#steuerungsdialekte)
- [Tastenkürzel](#tastenkürzel)
- [Wo liegen die Einstellungen](#wo-liegen-die-einstellungen)
- [Originale aufräumen](#originale-aufräumen)
- [Einschränkungen](#einschränkungen)
- [SmartScreen-Hinweis](#smartscreen-hinweis)
- [Lizenz](#lizenz)

---

## Funktionen

- **Reiter** für mehrere geöffnete Programme, wie in Notepad++. Dateien
  lassen sich auch **aus dem Explorer ins Fenster ziehen**, einzeln oder
  mehrere auf einmal. Ein **Doppelklick** auf eine NC-Datei öffnet ebenfalls
  einen neuen Reiter im schon laufenden Fenster.
- **Zeilennummern** mit farbigen Randmarken für geänderte, eingefügte und
  gelöschte Zeilen.
- **Farbhervorhebung nach G-Befehlen**: G0 Eilgang, G1/G2/G3 Bahnbewegung,
  G40–G42 Werkzeugkorrektur, G54–G59 Nullpunkt, M-Befehle, Koordinaten,
  Vorschub, Drehzahl, Werkzeug, Zyklen, Variablen, Kommentare – 22 Klassen,
  **alle Farben frei einstellbar**, je ein Satz für helles und dunkles Design.
- **Suchleiste dauerhaft oben**, dazu eine **Trefferspalte rechts**: jede Zeile,
  in der der Suchbegriff vorkommt, steht dort mit Zeilennummer und Inhalt und
  springt beim Anklicken an die Stelle.
- **Ersetzen** einzeln oder gesamt, wahlweise mit regulärem Ausdruck.
- **Speichern unter** als Knopf oben rechts, ohne Umweg über das Menü. Die
  Dateiart des offenen Programms ist dabei vorgewählt - ein `.nc`-Programm
  landet nicht versehentlich als `.mpf`.
- **Stärkere Hervorhebung von Hand-Änderungen** gegenüber dem
  SolidCAM-Original.
- **Gliederung** mit den SolidCAM-Jobs (`GROUP_BEGIN`), den Zyklen darin, den
  Werkzeugwechseln und allen Hand-Änderungen – alles anklickbar. Bei
  ISO-Programmen wird der Klartext neben dem Werkzeug übernommen, aus
  `M06 T24 ( MESSERKOPF D=63.0)` wird also `T24 - MESSERKOPF D=63.0`.
- **Steuerungsdialekte** SINUMERIK, Fanuc/ISO und Heidenhain, Erkennung am
  Dateiinhalt.
- Datei-Eigenheiten bleiben erhalten: **Zeilenenden** (CRLF/LF) und
  **Zeichensatz** (ANSI/UTF-8) werden so geschrieben, wie sie gelesen wurden.
  Auf Wunsch wird beim Speichern eine Sicherungskopie `.bak` angelegt.
  Siehe [Was beim Speichern passiert](#was-beim-speichern-passiert).

---

## Installation

### Fertige Programmdatei (empfohlen)

`NC-Editor.exe` herunterladen und in einen beliebigen Ordner legen, zum
Beispiel `C:\Programme\NC-Editor\`. Python ist dafür **nicht** nötig.
Die exe wird vom Release-Workflow auf einem Windows-Rechner gebaut.

### Aus dem Quelltext

Python 3.9 oder neuer von [python.org](https://www.python.org/downloads/)
installieren (Haken bei *Add Python to PATH*). Dann:

```
python -m pip install pillow
python ncedit.py
```

Oder per Doppelklick auf `start_nc_editor.bat`.

### Selbst eine exe bauen

```
build_exe.bat
```

Ergebnis: `dist\NC-Editor.exe`.

---

## Als Standardprogramm eintragen

Im Programm: **Extras → Als Standardprogramm für .mpf und .nc anmelden**.
Von der Kommandozeile geht auch `NC-Editor.exe --registrieren`.

Dabei wird der Editor für `.mpf`, `.nc` und `.spf` im Benutzerzweig der
Registrierung angemeldet (`HKEY_CURRENT_USER`). **Administratorrechte sind
nicht nötig**, und bestehende Zuordnungen werden nicht überschrieben.

Windows 10 und 11 lassen aus Sicherheitsgründen nicht zu, dass ein Programm
sich selbst zum Standardprogramm macht. Die letzte Bestätigung machen Sie
deshalb einmalig selbst – der Editor bietet nach dem Anmelden an, die
passende Windows-Seite direkt zu öffnen:

- Rechtsklick auf eine `.mpf`-Datei → *Öffnen mit* → *Andere App auswählen*
  → **NC-Editor** → Haken bei *Immer diese App verwenden*, **oder**
- *Einstellungen* → *Apps* → *Standard-Apps* → NC-Editor.

Rückgängig machen: **Extras → Anmeldung entfernen** bzw.
`NC-Editor.exe --abmelden`.

### Ein Fenster statt vieler

Windows startet bei jedem Doppelklick ein neues Programm. Der Editor erkennt,
dass schon ein Fenster offen ist, reicht die Datei dorthin weiter und beendet
sich sofort - die Datei erscheint als neuer Reiter, das Fenster kommt nach
vorn. Antwortet das laufende Fenster nicht innerhalb von vier Sekunden,
öffnet sich doch ein eigenes, damit ein Doppelklick nie ins Leere läuft.

Wer bewusst mehrere Fenster nebeneinander braucht, schaltet das unter
**Extras → Dateien im selben Fenster öffnen** ab; die Änderung gilt ab dem
nächsten Start.

---

## Bedienung

Das Fenster ist dreigeteilt:

| Bereich | Inhalt |
| --- | --- |
| links | Gliederung: Jobs und Zyklen, Werkzeuge, Hand-Änderungen |
| Mitte | Das NC-Programm mit Zeilennummern und Farbhervorhebung |
| rechts | Trefferliste der Suche |

Heißen mehrere geöffnete Programme gleich - in der Werkstatt oft schlicht
`1` oder `2` -, zeigt der Reiter zusätzlich den Ordner an, etwa
`1.MPF - Deckel 1001`. Der Mauszeiger auf dem Reiter zeigt den
vollständigen Pfad, und im Fenstertitel steht er ohnehin.

Gliederung und Trefferliste lassen sich über das Menü **Ansicht** abschalten,
ebenso die Zeilennummern. Die Spaltenbreiten sind mit der
Maus verschiebbar.

In der Fußzeile steht der Hinweis, dass die Verwendung auf eigene Gefahr
geschieht. Herkunft, Lizenz, Webseite und der vollständige Haftungsausschluss
stehen unter **Info** unten rechts.

Unten in der Statusleiste stehen Zeile und Spalte, die Satznummer der
aktuellen Zeile, Zeilenzahl, erkannter Dialekt, Zeichensatz, Zeilenenden und
die Anzahl der Hand-Änderungen. Rechts daneben lassen sich Steuerung und
Design umschalten.

---

## Suche

Das Suchfeld ist immer sichtbar. Während der Eingabe werden alle Treffer im
Text eingefärbt und **rechts in der Trefferspalte aufgelistet** – mit
Zeilennummer und Zeileninhalt. Ein Klick auf einen Eintrag springt an die
Stelle. Zeilen, die zugleich eine Hand-Änderung enthalten, sind in der
Trefferliste farbig hinterlegt.

- `Enter` bzw. `F3` springt zum nächsten Treffer, `Umschalt+F3` zurück.
- **Groß/klein**, **Ganzes Wort** und **Regulärer Ausdruck** sind
  kombinierbar.
- `Strg+H` öffnet die Ersetzen-Zeile. *Alle ersetzen* fragt vorher nach, wie
  viele Treffer geändert werden.
- `Strg+G` springt zu einer Zeilennummer, `Strg+Umschalt+G` zu einer
  **Satznummer** (`N1240`) – bequemer, wenn die Steuerung einen Satz meldet.

Bei sehr großen Programmen werden höchstens 20000 Treffer markiert und 4000
in der Liste angezeigt.

---

## Was beim Speichern passiert

Der Editor schreibt die Datei **Byte für Byte so zurück, wie er sie gelesen
hat** – nur die Zeilen, die Sie tatsächlich geändert haben, sind anders.
Nichts wird stillschweigend vereinheitlicht:

| Eigenheit | Verhalten |
| --- | --- |
| Zeilenenden | CRLF bleibt CRLF, LF bleibt LF |
| Zeichensatz | ANSI bleibt ANSI, UTF-8 bleibt UTF-8 (mit BOM, falls vorhanden) |
| Schluss der Datei | Ein fehlender Zeilenumbruch am Ende wird **nicht** ergänzt – wichtig für Fanuc-Programme, die mit `%` enden |
| Tabulatoren | bleiben Tabulatoren, werden nicht in Leerzeichen umgesetzt |
| Leerzeichen am Zeilenende | bleiben stehen |
| Leerzeilen | bleiben erhalten, auch mehrere am Schluss |

Das gilt für **Speichern** wie für **Speichern unter**: Haben Sie nichts
geändert, ist die geschriebene Datei mit dem Original identisch; haben Sie
etwas geändert, ist sie das Original mit genau dieser Änderung. Die
Quelldatei bleibt beim Speichern unter unberührt.

Die farbliche Hervorhebung der Hand-Änderungen ist dabei **nur im Editor
sichtbar**. In die NC-Datei wird nie ein Marker, Kommentar oder sonstiges
Zeichen geschrieben - der Vergleichsstand liegt getrennt davon in
`%APPDATA%\NC-Editor\originale`. Die Steuerung bekommt also genau das zu
sehen, was Sie geschrieben haben, und nichts weiter.

Geschrieben wird über eine temporäre Datei, die anschließend in einem
Schritt an ihren Platz gesetzt wird. Fällt der Rechner mitten im Speichern
aus, bleibt also entweder der alte oder der neue Stand stehen – nie eine halbe
Datei. Ist *Sicherungskopie* eingeschaltet (Voreinstellung), liegt der Stand
davor zusätzlich als `.bak` daneben; beim Speichern unter einem neuen Namen
entsteht keine `.bak`, weil es nichts zu sichern gibt.

Nachprüfbar ist das mit dem mitgelieferten Test, der bei jedem Bau der exe
mitläuft:

```
python tests/speichern_test.py
```

Er legt Programme mit allen oben genannten Eigenheiten an, lässt sie durch
den Editor laufen und vergleicht die Bytes.

---

## Hand-Änderungen

Beim **ersten Öffnen** legt der Editor eine Kopie des Programms als *Original*
ab – das ist der Stand, wie SolidCAM ihn ausgegeben hat. Die Kopie liegt in
`%APPDATA%\NC-Editor\originale` und verändert die NC-Datei selbst nicht.

Jede spätere Abweichung gilt als Hand-Änderung:

- **geänderte Zeile**: farbig hinterlegt, orange Randmarke
- **eingefügte Zeile**: farbig hinterlegt, grüne Randmarke
- **gelöschte Zeilen**: rotes Dreieck an der Lücke

Die Markierung bleibt nach dem Speichern und nach dem Schließen erhalten und
greift auch, wenn die Datei zwischendurch in einem anderen Editor geändert
wurde. **Speichern unter** einem neuen Namen setzt dagegen neu an: Der
geschriebene Stand wird das Original der neuen Datei, die Markierungen fangen
dort von vorn an. Wer unter neuem Namen speichert, gibt damit einen neuen
Ausgangsstand frei. `F8` springt zur nächsten Hand-Änderung, `Umschalt+F8` zurück; in der
Gliederung sind alle Hand-Änderungen aufgelistet.

Wie stark hervorgehoben wird, ist einstellbar (*Farben und Schrift*):
nur Randmarke, Randmarke und Farbe, oder zusätzlich fett.

### Wenn das Programm neu aus SolidCAM kommt

Das erkennt der Editor selbst. Er merkt sich Größe und Zeitmarke der Datei;
hat ein anderes Programm sie seitdem geschrieben - typisch der Postprozessor -,
dann ist das ein **neuer Ausgangsstand und keine Hand-Änderung**. Der neue
Stand wird als Original übernommen, oben erscheint kurz ein Hinweis, und es
ist nichts fälschlich hervorgehoben.

War das Programm dabei schon geöffnet, **lädt der Editor es neu**, damit nie
eine veraltete Fassung auf dem Schirm steht. Gibt es noch nicht gespeicherte
eigene Änderungen, wird vorher gefragt. Von Hand lässt sich der Stand
jederzeit mit `F5` neu laden.

Wer lieber streng vergleicht und jede Abweichung sehen will, schaltet das
unter **Original → Neu ausgegebene Programme als neues Original übernehmen**
ab. Dann greift wie bisher **Original → Aktuellen Stand als Original
übernehmen**, um den neuen Post-Lauf zum Vergleichsstand zu machen.

Soll gegen eine bestimmte Datei verglichen werden – etwa gegen den frisch
geposteten Stand in einem anderen Ordner –, geht das über **Original →
Original aus Datei wählen**.

---

## Farben

**Extras → Farben und Schrift** öffnet die Farbeinstellung. Jede der 22
Syntaxklassen hat eine Farbe sowie die Schalter *fett* und *kursiv*, daneben
steht ein Beispiel in der echten Editorschrift. Änderungen wirken sofort.
Dazu kommen die Editorfarben (Hintergrund, Auswahl, aktuelle Zeile,
Zeilennummern, Hand-Änderungen, Suchtreffer), Schriftart und Schriftgröße.

Helles und dunkles Design haben **je einen eigenen Farbsatz**. Umgeschaltet
wird rechts unten in der Statusleiste. Das dunkle Design erfasst auch die
Menüleiste, die Fenster des Programms und - unter Windows 10 ab Fassung 1809
sowie unter Windows 11 - die Titelleiste des Fensters. Die Meldungsfenster von
Windows (etwa die Rückfrage beim Schließen) zeichnet das Betriebssystem
selbst und bleiben hell. Farbsätze lassen sich als Datei
exportieren und auf anderen Rechnern wieder einlesen.

### Woher die Voreinstellung kommt

Einen veröffentlichten Farbstandard für NC-Editoren gibt es nicht. CIMCO
Edit, UltraEdit, Notepad++ und die VS-Code-Erweiterungen lassen die Farben
alle frei einstellen und liefern unterschiedliche Voreinstellungen; in
VS Code und Sublime Text richten sie sich sogar nach dem gerade aktiven
Farbschema des Editors. Einig sind sich die Werkzeuge nur bei den
*Klassen* – Kommentare, Satznummern, G- und M-Befehle, Koordinaten,
Technologiewerte – und bei wenigen Festlegungen: Kommentare grün, Satznummern
blass, sicherheitsrelevante Befehle in Signalfarben.

Die Voreinstellung hier folgt diesem gemeinsamen Nenner:

| Klasse | Farbe (hell) | Grund |
| --- | --- | --- |
| Kommentar | grün, kursiv | in praktisch jedem Editor so |
| Satznummer | blassgrau | tritt zurück, stört den Blick auf die Technik nicht |
| G0 Eilgang | orange, fett | fällt auf, weil im Eilgang nichts im Weg stehen darf |
| G1/G2/G3 | blau, fett | die eigentliche Bearbeitung |
| G40–G42 | violett, fett | Korrektur an und aus ist eine häufige Fehlerquelle |
| G54–G59 | dunkelblau, fett | Nullpunkt – vor dem Start immer zu prüfen |
| übrige G | stahlblau | gleiche Farbfamilie, aber zurückhaltend |
| M0/M1/M2/M6/M30 | rot, fett | Halt und Werkzeugwechsel |
| übrige M | magenta | Hilfsfunktionen |
| Koordinaten | petrol | die Zahlen, auf die man am häufigsten schaut |
| Vorschub / Drehzahl | gold / oliv | Technologiewerte |
| Werkzeug T D H | bernstein, fett | Werkzeugaufruf |
| Zyklen | violett, fett | CYCLE81, CYCLE800 … |

Alles davon ist nur ein Vorschlag und lässt sich in zwei Klicks ändern.

---

## Steuerungsdialekte

Der Dialekt wird am Dateiinhalt erkannt und unten rechts angezeigt. Er lässt
sich dort auch fest vorgeben.

| Dialekt | Erkannt an | Besonderheiten |
| --- | --- | --- |
| **SINUMERIK** | `%_N_…_MPF`, `CYCLE…`, `MSG(`, `R1=`, `GOTOF` | Kommentar nur `;` – runde Klammern sind **kein** Kommentar, `R`-Parameter, `CR=`, Konstanten wie `_ROUGH` |
| **Fanuc / ISO** | `O1234`, `(Kommentar)`, `G43 H`, `M98` | Klammern sind Kommentar, `#100`-Makros, Bohrzyklen G73–G89 als Zyklus eingefärbt |
| **Heidenhain** | `BEGIN PGM`, `L X+…`, `TOOL CALL` | Satznummer am Zeilenanfang, `R0/RL/RR` als Korrektur, `Q`-Parameter |

Für SolidCAM-Programme mit `.mpf` trifft die Erkennung in aller Regel
SINUMERIK.

---

## Tastenkürzel

| Taste | Wirkung |
| --- | --- |
| `Strg+O` / `Strg+S` | Öffnen / Speichern |
| `Strg+Umschalt+S` | Speichern unter |
| `Strg+N` / `Strg+W` | Neues Programm / Reiter schließen |
| `Strg+Tab` | Nächster Reiter |
| `Strg+F` | In das Suchfeld springen |
| `F3` / `Umschalt+F3` | Nächster / voriger Treffer |
| `Strg+H` | Ersetzen |
| `Strg+G` | Gehe zu Zeile |
| `Strg+Umschalt+G` | Gehe zu Satznummer |
| `F5` | Datei neu von der Platte laden |
| `F8` / `Umschalt+F8` | Nächste / vorige Hand-Änderung |
| `Strg+Z` / `Strg+Y` | Rückgängig / Wiederholen |
| `Strg++` / `Strg+-` / `Strg+0` | Schrift größer / kleiner / zurücksetzen |

---

## Wo liegen die Einstellungen

```
%APPDATA%\NC-Editor\einstellungen.json     Farben, Schrift, Fenster, Optionen
%APPDATA%\NC-Editor\originale\             Kopien der SolidCAM-Originale
```

Unter Linux und macOS liegt beides in `~/.nc-editor`. Das Menü
**Extras → Einstellungsordner öffnen** führt direkt dorthin.

---

## Originale aufräumen

Zu jedem geöffneten Programm liegt eine Kopie des Originalstandes in
`%APPDATA%\NC-Editor\originale`. Damit der Ordner über die Jahre nicht
vollläuft, räumt der Editor **beim Beenden** selbsttätig auf. Entfernt wird:

- was zu einer NC-Datei gehört, die es auf der Platte nicht mehr gibt,
- was seit **90 Tagen** nicht mehr geöffnet wurde,
- alles über **400 Originale** hinaus, älteste zuerst.

Die **gerade geöffneten Programme bleiben immer erhalten**. Unter
`Original` - `Originale aufräumen` steht, wie viele Originale abgelegt sind
und wie viel Platz sie brauchen; dort lassen sich Aufbewahrungszeit und
Obergrenze ändern, das Aufräumen von Hand auslösen, die Automatik
abschalten oder alle Originale auf einmal löschen.

Zur Größenordnung: Ein Programm mit 4000 Sätzen belegt rund 130 KB, 400
Originale also etwa 50 MB.

---

## Einschränkungen

- Der Editor **prüft keine NC-Syntax** und rechnet keine Bahnen nach. Er färbt
  ein, sucht und vergleicht – mehr nicht.
- Es gibt **keine grafische Simulation** der Werkzeugbahn.
- Wird ein Programm zum ersten Mal geöffnet, **nachdem** es bereits von Hand
  geändert wurde, gilt dieser Stand als Original. Für diesen Fall gibt es
  *Original aus Datei wählen*.
- Sehr große Programme über 200000 Zeilen werden nicht mehr gegen das
  Original verglichen; Einfärbung und Suche arbeiten weiter.
- Das Hineinziehen von Dateien braucht die Bibliothek `tkinterdnd2`. In der
  fertigen `NC-Editor.exe` ist sie enthalten. Wer aus dem Quelltext startet
  und sie nicht installiert hat, kann Dateien weiterhin über
  `Datei` - `Öffnen` wählen; alles Übrige ist unverändert.
- Prüfen Sie geänderte NC-Programme vor dem Einsatz an der Maschine im
  Einzelschritt und mit Probelauf.

---

## SmartScreen-Hinweis

`NC-Editor.exe` ist nicht signiert. Windows meldet beim ersten Start
SmartScreen. Über *Weitere Informationen* und *Trotzdem ausführen*
bestätigen.

---

## Kontakt

Fehler, Wünsche und Fragen am besten als Issue in diesem Repository — so
haben auch andere etwas davon. Sonst: [iot-simply.com](https://iot-simply.com),
info@iot-simply.com

---

## Lizenz und Marken

Der NC-Editor steht unter der **MIT-Lizenz** – siehe [LICENSE](LICENSE). Frei
nutzbar, veränderbar und weitergebbar, ohne Gewährleistung.

Verwendet werden tkinterdnd2 und tkDnD (Dateien hineinziehen) sowie Pillow
(Logo); in der `.exe` sind zusätzlich Python und Tcl/Tk enthalten. Alle
Einzelheiten stehen in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Die **vollständigen** Lizenztexte sind im Programm eingebettet und lassen
sich jederzeit anzeigen – Schaltfläche **Lizenzen** unten rechts oder
`ncedit.py --lizenzen`. Im Fenster lässt sich der Text über
**Als Datei speichern** ablegen, um ihn mit dem Programm weiterzugeben.

**Marken:** SINUMERIK, FANUC, Haas, HEIDENHAIN, SolidCAM, SOLIDWORKS und
Windows sind Marken ihrer jeweiligen Inhaber. Es besteht keine Verbindung zu
diesen Herstellern; die Namen werden nur genannt, um die unterstützten
Dateien und Steuerungsdialekte zu beschreiben. Die vollständige Aufstellung
steht im Lizenzfenster unter **Marken**.
