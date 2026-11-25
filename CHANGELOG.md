# Änderungen

## 2.2

Vier Fehler aus dem Werkstattbetrieb.

- **Die rechte Maustaste öffnet jetzt ein Menü im Editor** mit
  Ausschneiden, Kopieren, Einfügen, Alles markieren, Rückgängig und
  „Gehe zu Zeile". Ist etwas markiert, steht dort zusätzlich „Suchen nach
  …" mit dem markierten Text. Bisher gab es für die Maus überhaupt keinen
  Weg zum Kopieren - wer die Tastenkürzel nicht kannte, kam nicht an den
  Text. Ein Klick außerhalb der Markierung setzt die Schreibmarke mit,
  innerhalb bleibt die Markierung stehen.
- **Keine falschen Hand-Markierungen mehr nach einem neuen
  Postprozessor-Lauf.** Ob ein anderes Programm die Datei geschrieben hat,
  wurde bisher an Größe und Zeitmarke festgemacht. Auf Netzlaufwerken ist
  die Zeitmarke oft nur sekundengenau, und ein neu ausgegebenes Programm
  kann zufällig genauso lang sein wie das vorige - dann galt die neue
  Ausgabe als alter Stand, und jede abweichende Zeile wurde als
  Hand-Änderung angezeigt. Jetzt entscheidet eine Prüfsumme des
  Dateiinhalts, die sich nicht verwechseln lässt.
- **Ablagen aus Fassung 1.x führen nicht mehr dazu, dass alles markiert
  wird.** Fehlten die Zustandsangaben, blieb das alte Original stehen und
  wurde gegen ein völlig anderes Programm verglichen. Jetzt entscheidet in
  diesem Fall der Umfang der Abweichung: einzelne Zeilen bleiben als
  Hand-Änderung markiert, weicht fast alles ab, gilt der neue Stand als
  Original.
- **Die Gliederung folgt den Änderungen.** Bisher blieb sie nach einer
  Änderung stehen: ein von Hand eingefügter Werkzeugwechsel tauchte nicht
  auf, und „Hand-Änderungen" zählte weiter den Stand beim Öffnen.
- **Strg+A markiert alles und Strg+Y wiederholt.** Beide standen im Menü,
  taten aber etwas anderes, weil Tk diese Tasten selbst belegt - Strg+A
  sprang an den Zeilenanfang, Strg+Y fügte die Zwischenablage ein. Im
  Suchfeld markiert Strg+A weiterhin nur das Feld.

Der mitgelieferte Test prüft diese Fälle ab jetzt bei jedem Bau mit
(Abschnitte 10 bis 12).

## 2.1

- **Umlaute werden richtig geschrieben.** Oberfläche, Menüs, Meldungen,
  Lizenztexte und Dokumentation verwenden ä, ö, ü und ß statt ae, oe, ue
  und ss. Die wörtlichen Lizenztexte der Fremdkomponenten bleiben
  unverändert.
- **Das Logo steht nicht mehr über dem Programm.** Die Kopfzeile mit dem
  Typenschild ist entfallen; der Arbeitsbereich ist dadurch rund 80 Pixel
  höher. Logo, Webseite und Copyright stehen jetzt im Info-Fenster, das
  dafür das Typenschild als Kopf trägt.
- **Hinweis auf eigene Gefahr.** In der Fußzeile steht dauerhaft in Rot
  „Verwendung auf eigene Gefahr - Programme vor dem Einsatz im
  Einzelschritt prüfen"; im Info-Fenster steht der vollständige Hinweis
  samt Haftungsausschluss in einem abgesetzten Kasten.
- Die Fußzeile ist entsprechend schlank: nur noch Name, Fassung, Lizenzen
  und Info.

## 2.0

In der Werkstatt heißen die Programme oft nur `1` oder `2`; beschrieben ist
der Ordner, nicht die Datei. Dadurch sind mehrere gleichnamige Programme
gleichzeitig offen:

- **Reiter mit gleichem Dateinamen zeigen jetzt den Ordner dazu**, zum
  Beispiel `1.MPF - Deckel 1001`. Reicht ein Ordner nicht zur
  Unterscheidung, kommt die nächste Ebene hinzu (`1.MPF - KW47/Deckel
  1001`). Eindeutige Namen bleiben kurz wie bisher.
- **Der Mauszeiger auf einem Reiter zeigt den vollständigen Pfad.**
- **Im Fenstertitel steht der volle Pfad** statt nur des Dateinamens.

Geprüft wurde auch, dass dabei nichts durcheinandergerät: Originale,
Inhalte und Hand-Änderungen bleiben je Ordner getrennt - das steckt jetzt
als Abschnitt 9 im Dateitreue-Test.

## 1.9

Zwei Fehler im Zusammenspiel mit SolidCAM, gemeldet aus der Werkstatt.

- **Ein neuer Lauf des Postprozessors galt als Hand-Änderung.** Wer ein
  Programm aus SolidCAM heraus öffnete, es dort änderte und erneut ausgab,
  bekam den neuen Stand komplett als "von Hand geändert" angezeigt - an
  einem Beispiel 577 Zeilen, allein durch geänderte Drehzahlen und
  Vorschübe. Schon ein neuer Zeitstempel im Kopf reichte für eine
  falsche Markierung. Der Editor merkt sich jetzt Größe und Zeitmarke der
  Datei. Hat ein anderes Programm sie seitdem geschrieben, ist das ein neuer
  Ausgangsstand und keine Hand-Änderung; er wird übernommen und oben kurz
  angezeigt. Abschaltbar unter `Original` - `Neu ausgegebene Programme als
  neues Original übernehmen`.
- **Der Editor zeigte den alten Stand weiter.** War das Programm schon
  geöffnet und SolidCAM gab es neu aus, wurde beim erneuten Öffnen nur der
  Reiter gewählt - der Inhalt blieb der alte. Geprüft wurde dann eine
  andere Fassung als die, die an die Maschine ging. Der Editor lädt die
  Datei jetzt neu, wenn sie sich auf der Platte geändert hat. Gibt es noch
  nicht gespeicherte eigene Änderungen, wird vorher gefragt.
- Neu: **Datei** - **Neu laden** (`F5`), um den Stand von der Platte zu holen.
- Eigene Hand-Änderungen werden unverändert erkannt und überstehen
  Speichern und erneutes Öffnen - dafür gibt es jetzt einen festen Test.

## 1.8

- **Speichern unter** wählt die Dateiart des offenen Programms vor: Bei einer
  `.nc`-Datei steht *NC-Programm (*.nc)* oben, bei `.mpf` das *SINUMERIK
  Hauptprogramm (*.mpf)*, bei `.h` der *Heidenhain Klartext*. Bisher war immer
  `.mpf` vorgegeben, sodass ein NC-Programm versehentlich als `.mpf` landen
  konnte. Groß- und Kleinschreibung der Endung spielt keine Rolle (`.NC` wie
  `.nc`).
- Bei einem noch nicht gespeicherten Programm entscheidet der erkannte
  Dialekt: SINUMERIK `.mpf`, Heidenhain `.h`, sonst `.nc`.
- Der Dialog beginnt jetzt im Ordner der offenen Datei statt im zuletzt
  benutzten.

## 1.7

- **Doppelklick im Explorer öffnet jetzt einen neuen Reiter** statt jedes Mal
  ein weiteres Fenster. Windows startet beim Doppelklick immer ein neues
  Programm; der Editor erkennt nun, dass schon ein Fenster läuft, reicht die
  Datei dorthin weiter und beendet sich sofort. Das Fenster kommt dabei nach
  vorn. Dasselbe gilt, wenn mehrere Dateien auf einmal geöffnet werden.
- Antwortet das laufende Fenster nicht innerhalb von vier Sekunden, öffnet
  sich doch ein eigenes - ein Doppelklick läuft nie ins Leere.
- Abschaltbar unter `Extras` - `Dateien im selben Fenster öffnen`, falls
  bewusst mehrere Fenster nebeneinander gebraucht werden.

## 1.6

Im dunklen Design blieben mehrere Bereiche hell, weil Windows sie selbst
zeichnet und sich dabei nicht an das Thema des Programms hält:

- Die **Menüleiste** (Datei, Bearbeiten, Suchen ...) ist jetzt eine eigene,
  mitgefärbte Leiste. Eine an das Fenster gehängte Tk-Menüleiste ist unter
  Windows eine echte Windows-Menüleiste und lässt sich nicht einfärben.
  Die Menüs öffnen sich wie bisher per Mausklick, zusätzlich mit
  `Alt+D`, `Alt+B`, `Alt+S`, `Alt+A`, `Alt+O`, `Alt+E` und `Alt+H`.
- Die **Titelleiste des Fensters** wird unter Windows 10 (ab 1809) und
  Windows 11 dunkel gesetzt. Auf älteren Fassungen bleibt sie hell, daran
  lässt sich von außen nichts ändern.
- Die **aufgeklappten Listen** der Felder *Steuerung* und *Design* folgen
  jetzt den Farben; sie sind intern Listboxen und hängen nicht am Thema.
- **Gehe zu Zeile** und **Gehe zu Satznummer** haben ein eigenes
  Eingabefenster im Design des Programms statt des hellen Standardfensters.

Im hellen Design sieht alles aus wie vorher.

## 1.5

- **Lizenzfenster** wie beim Laserprogramm: Die vollständigen Lizenztexte
  sind jetzt im Programm eingebettet - eigene MIT-Lizenz, Markenhinweise und
  die Lizenzen aller mitgelieferten Fremdkomponenten (tkinterdnd2, tkDnD,
  Pillow, Python, Tcl, Tk, PyInstaller), rund 2100 Zeilen. Mit Auswahlfeld
  zum Springen zwischen den Abschnitten und einem Knopf, der alles als
  Textdatei ablegt. So lässt sich das Programm sauber weitergeben.
- **Marken** sind ausdrücklich benannt: SINUMERIK, FANUC, Haas, HEIDENHAIN,
  SolidCAM, SOLIDWORKS, Windows und weitere gehören ihren Inhabern, es
  besteht keine Verbindung zu diesen Herstellern. Dazu der Hinweis, dass die
  bearbeiteten NC-Programme vollständig Eigentum des Anwenders bleiben.
- **Info-Fenster** nennt jetzt Lizenz, verwendete Komponenten, Marken, ob
  Drag and Drop verfügbar ist, und die Ablageorte.
- **Info** und **Lizenzen** stehen zusätzlich unten rechts in der
  Fußleiste, nicht mehr nur im Menü `Hilfe`.
- Neue Datei `THIRD_PARTY_NOTICES.md` im Projekt.

## 1.4

- **Ersetzen** steht wieder links bei der Suche, direkt hinter den Pfeilen.
  Neben *Speichern unter* war es missverständlich - es las sich, als solle
  die Datei ersetzt werden. Eine senkrechte Trennlinie trennt jetzt die
  Suche von dem, was die Datei betrifft.

- Die Kommandozeilenbefehle (`--version`, `--lizenzen`, `--registrieren`,
  `--abmelden`) **stürzten in der gebauten exe ab**. Eine mit `--noconsole`
  gebaute Anwendung hat unter Windows kein `sys.stdout` - PyInstaller setzt
  es auf `None`, und jede Ausgabe löste dort eine Ausnahme aus, für die der
  Bootloader ein Fehlerfenster zeigt. Alle Ausgaben laufen jetzt über eine
  Funktion, die das abfängt. Über das Menü `Extras` war die Anmeldung
  nie betroffen.
- Fehler aus Bedienvorgängen beenden das Programm nicht mehr und landen in
  `fehler.log` im Einstellungsordner.

Dazu, nur den Bau betreffend:

- Die gebaute `NC-Editor.exe` wird beim Bauen mit `--selbsttest` gestartet.
  Dabei entsteht wirklich ein Fenster, es wird eingefärbt und gesucht. Der
  bisherige Kurztest rief nur `--icon-export` auf und endete, bevor Tkinter
  überhaupt anlief.
- Die Release-Hinweise nennen jetzt **Größe und SHA-256** der exe, dazu den
  PowerShell-Befehl zum Nachprüfen. Ein unvollständiger Download meldet
  sich beim Start mit `Could not load PyInstaller's embedded PKG archive` -
  mit der Prüfsumme ist das in zehn Sekunden geklärt.

## 1.3

- Knopf **Speichern unter** oben rechts in der Suchleiste - ohne Umweg
  über das Menü.
- **Dateien hineinziehen**: `.mpf`, `.nc` und die übrigen NC-Endungen
  lassen sich aus dem Explorer in das Fenster ziehen und öffnen sich
  sofort, auch mehrere auf einmal. Bei einer fremden Dateiendung wird
  vorher gefragt.
- **Originale werden aufgeräumt**, damit der Ablageordner über die Jahre
  nicht vollläuft: Beim Beenden fliegt raus, wozu es die NC-Datei nicht mehr
  gibt und was seit 90 Tagen nicht mehr geöffnet wurde; dazu gibt es eine
  Obergrenze von 400 Originalen. Die gerade geöffneten Programme bleiben
  immer erhalten. Einstellbar und von Hand auslösbar unter
  `Original` - `Originale aufräumen`, mit Platzanzeige und der Möglichkeit,
  alle Originale zu löschen.
- Der Link **iot-simply.com** in der Fußleiste **funktioniert jetzt**. In
  der gebauten exe passierte beim Klick nichts: Der Browser wurde über
  `__import__("webbrowser")` geholt, und diese dynamische Form erzeugt keinen
  IMPORT_NAME im Bytecode - PyInstaller hat das Modul deshalb nie
  mitverpackt, der Klick lief in einen unsichtbaren ImportError. Jetzt wird
  unter Windows `os.startfile` benutzt, mit `webbrowser` als Rückfall.
- Die Suchoptionen stehen zusätzlich im Menü `Suchen`, damit sie auch bei
  schmalem Fenster erreichbar sind.

## 1.2

- **Speichern unter** einem neuen Namen setzt den geschriebenen Stand als
  Original der neuen Datei: Wer unter neuem Namen speichert, gibt damit einen
  neuen Ausgangsstand frei. Beim Speichern unter demselben Namen bleiben die
  Hand-Markierungen erhalten.
- Der Test weist jetzt ausdrücklich nach, dass die Markierung von
  Hand-Änderungen **nie** in die NC-Datei geschrieben wird. Sie lebt
  ausschließlich in der getrennten Ablage unter
  `%APPDATA%\NC-Editor\originale`.

## 1.1

- Neuer Test `tests/speichern_test.py`, der byteweise nachweist, dass
  gespeicherte Dateien dem Original entsprechen - mit und ohne abschließenden
  Zeilenumbruch, mit LF und CRLF, in UTF-8 und ANSI, mit Tabulatoren,
  Leerzeilen und Leerzeichen am Zeilenende. Der Test läuft jetzt bei jedem
  Bau der exe mit.

## 1.0

Erste Fassung.

- Editor für NC-Programme mit Reitern für mehrere geöffnete Dateien
- Farbhervorhebung nach G-Befehlen, Dialekte SINUMERIK, Fanuc/ISO und
  Heidenhain, Erkennung am Dateiinhalt
- Alle Farben einstellbar, je ein Satz für helles und dunkles Design,
  Export und Import als Datei
- Suchleiste dauerhaft sichtbar, Trefferspalte rechts mit allen Fundstellen
  zum Anklicken, Ersetzen einzeln und gesamt
- Stärkere Hervorhebung von Zeilen, die gegenüber dem SolidCAM-Original
  von Hand geändert wurden, mit Randmarken in der Zeilennummernspalte
- Gliederung mit SolidCAM-Jobs, Zyklen, Werkzeugwechseln und Hand-Änderungen;
  bei ISO-Programmen werden Werkzeugwechsel wie "M06 T24 (MESSERKOPF D=63.0)"
  samt Klartext und die Bohrzyklen G73-G89 erkannt
- Anmeldung als Programm für .mpf, .nc und .spf unter Windows 10 und 11
