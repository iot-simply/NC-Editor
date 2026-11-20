#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NC-Editor - Editor für NC-Programme (.mpf, .nc) mit Suche und Farbhervorhebung.

Für Werkstattrechner: läuft offline, ohne Installation, ohne Dienste.
Die Farbhervorhebung richtet sich nach den G-Befehlen und ist vollständig
einstellbar. Zeilen, die von Hand gegenüber dem SolidCAM-Original geändert
wurden, werden deutlich stärker hervorgehoben.

Copyright (c) 2026 Christopher Schmick, iot-simply.com
Open Source unter der MIT-Lizenz. Der vollständige Lizenztext, die Lizenzen
der mitgelieferten Fremdkomponenten und die Markenhinweise stehen im Programm
(Schaltfläche "Lizenzen" unten rechts) und unter  ncedit.py --lizenzen.
Ohne Gewährleistung - geänderte NC-Programme vor dem Einsatz an der Maschine
im Einzelschritt und mit Probelauf prüfen.

SINUMERIK, FANUC, Haas, HEIDENHAIN, SolidCAM, SOLIDWORKS und Windows sind
Marken ihrer jeweiligen Inhaber. Es besteht keine Verbindung zu diesen
Herstellern; die Namen werden nur genannt, um die unterstützten Dateien und
Steuerungsdialekte zu beschreiben.

Aufruf:
  ncedit.py [datei.mpf]        Oberfläche, wahlweise mit Datei
  ncedit.py --registrieren     Windows: Programm für .mpf/.nc anmelden
  ncedit.py --abmelden         Windows: Anmeldung wieder entfernen
  ncedit.py --selbsttest       Prüfen, ob das Programm startet
  ncedit.py --lizenzen         Lizenztexte ausgeben
  ncedit.py --version          Version ausgeben
"""

import os
import re
import sys

VERSION = "2.1"
APP_NAME = "NC-Editor"
APP_AUTHOR = "Christopher Schmick"
APP_URL = "https://iot-simply.com"
APP_YEAR = "2026"
DATEI_ENDUNGEN = (".mpf", ".nc", ".spf", ".tap", ".cnc", ".ngc", ".h", ".iso")
HAUPT_ENDUNGEN = (".mpf", ".nc")

# Dateiarten für die Auswahl im Speichern-Dialog (Endung, Bezeichnung)
NC_DATEIARTEN = (
    (".mpf", "SINUMERIK Hauptprogramm"),
    (".nc", "NC-Programm"),
    (".spf", "SINUMERIK Unterprogramm"),
    (".tap", "NC-Programm (tap)"),
    (".cnc", "NC-Programm (cnc)"),
    (".ngc", "NC-Programm (ngc)"),
    (".h", "Heidenhain Klartext"),
    (".iso", "NC-Programm (iso)"),
)


def speicher_dateiarten(endung):
    """Dateiarten für "Speichern unter", die passende zuerst.

    Die erste Art in der Liste ist im Dialog vorgewählt. Wer ein .nc-Programm
    offen hat, soll nicht versehentlich als .mpf speichern.
    """
    endung = (endung or "").lower()
    bekannt = [e for e, _b in NC_DATEIARTEN]
    liste = [(b, "*" + e) for e, b in NC_DATEIARTEN if e == endung]
    liste += [(b, "*" + e) for e, b in NC_DATEIARTEN if e != endung]
    if endung and endung not in bekannt:
        liste.insert(0, ("Datei %s" % endung, "*" + endung))
    liste.append(("Alle Dateien", "*.*"))
    return liste


def ausgeben(text, fehler=False):
    """Schreibt auf die Konsole, soweit es überhaupt eine gibt.

    Eine mit --noconsole gebaute exe hat unter Windows kein sys.stdout -
    PyInstaller setzt es dort auf None. Ein sys.stdout.write löst dann eine
    Ausnahme aus, und der Bootloader zeigt dafür ein Fehlerfenster. Auf einem
    Bauserver wartet man darauf vergeblich, der Bau bleibt hängen.
    """
    strom = sys.stderr if fehler else sys.stdout
    try:
        if strom is not None:
            strom.write(text)
            strom.flush()
    except Exception:
        pass


def fehler_protokollieren(text):
    """Hängt einen Fehler an %APPDATA%\\NC-Editor\\fehler.log an."""
    import time

    try:
        pfad = os.path.join(daten_verzeichnis(), "fehler.log")
        if os.path.isfile(pfad) and os.path.getsize(pfad) > 512 * 1024:
            os.replace(pfad, pfad + ".alt")
        with open(pfad, "a", encoding="utf-8") as fh:
            fh.write("\n==== %s  %s %s ====\n%s"
                     % (time.strftime("%d.%m.%Y %H:%M:%S"), APP_NAME, VERSION, text))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Teil 1: Dialekte und Zerlegung der NC-Sätze
# ---------------------------------------------------------------------------
#
# Unterstützt werden drei Dialekte. "auto" erkennt den Dialekt am Inhalt.
#   sinumerik  Siemens SINUMERIK 840D/828D - Kommentar ";", Zyklen CYCLE...,
#              R-Parameter, Klammern sind KEIN Kommentar.
#   iso        Fanuc/Haas/ISO - Kommentar "(...)" und ";", O-Programmnummer,
#              Makrovariablen #100, Bohrzyklen G73...G89.
#   heidenhain Klartext (TNC) - Satznummer am Zeilenanfang, L/C/CR-Sätze,
#              Q-Parameter, Kommentar ";".

DIALEKT_NAMEN = (
    ("auto", "Automatisch erkennen"),
    ("sinumerik", "Siemens SINUMERIK"),
    ("iso", "Fanuc / Haas (ISO)"),
    ("heidenhain", "Heidenhain Klartext"),
)

SINU_SCHLUESSEL = frozenset("""
IF ELSE ENDIF WHILE ENDWHILE FOR ENDFOR TO REPEAT REPEATB ENDLABEL LOOP ENDLOOP
GOTO GOTOF GOTOB GOTOC CASE DEFAULT DEF REAL INT BOOL CHAR STRING AXIS FRAME
PROC ENDPROC EXTERN RET SETMS STOPRE NEWCONF SBLOF SBLON MSG
TRANS ATRANS ROT AROT AROTS ROTS SCALE ASCALE MIRROR AMIRROR OFFN
TRAFOOF TRAORI TRANSMIT TRACYL CUT2D CUT2DF CUT3DC CUT3DF CFTCP CFC CFIN
SOFT BRISK DRIVE FFWON FFWOF COMPCAD COMPCURV COMPOF COMPON ORIWKS ORIMKS
SPOS SPOSA WAITP WAITM WAITS WAITE MEAS MEAW SETAL DELAYFSTON DELAYFSTOF
TOFFL TOFFR TOFF LIMS FGROUP FGREF SUPA SPI ISAXIS ACC OVR OVRA
NOT AND OR XOR B_AND B_OR B_NOT MOD DIV TRUE FALSE
SIN COS TAN ASIN ACOS ATAN2 SQRT POT ABS TRUNC ROUND ROUNDUP LN EXP MINVAL MAXVAL
STRLEN SUBSTR TOUPPER TOLOWER NUMBER ISNUMBER AXNAME AXSTRING INDEX
DITE DITS PUTFTOC SETINT DISABLE ENABLE CLEARM SETM GETSELT NEWT DELT
RND RNDM CHF CHR ANG INVERS CPROT NPROT WALIMON WALIMOF
STARTFIFO STOPFIFO FIFOCTRL PRESETON INIT CALL PCALL MCALL
GROUP_BEGIN GROUP_END WORKPIECE SETTRANS CORRTRAFO
""".split())

ISO_SCHLUESSEL = frozenset("""
IF THEN GOTO WHILE DO END EQ NE GT LT GE LE AND OR XOR MOD
SIN COS TAN ASIN ACOS ATAN SQRT ABS ROUND FIX FUP LN EXP ADP BIN BCD
POPEN PCLOS DPRNT BPRNT SETVN CALL MACRO SUB RETURN
""".split())

HH_SCHLUESSEL = frozenset("""
BEGIN END PGM MM INCH BLK FORM TOOL DEF CALL AXIS SET STOP SEQ SEL TABLE
PATTERN FUNCTION MODE PROG DATUM PRESET RESET TURN MOVE STAY TRANS ROT
FN FK PLANE SPATIAL VECTOR EULER POINTS AXIAL PROJECTED RELATIV POLAR
LBL REP MAX MIN TCH PROBE CONTOUR CYCLE DECLARE STRING SUBSTR TOCHAR
SQL SYSSTR SYSREAD RETURN CONT DIST TIME PITCH DEPTH
""".split())

HH_BAHN = frozenset("L LP C CC CR CT CTP CP LN APPR APPRLT APPRLN APPRCT APPRLCT "
                    "DEP DEPLT DEPLN DEPCT DEPLCT".split())
HH_KORR = frozenset(("R0", "RL", "RR", "RND", "CHF"))
HH_ZYKLUS = frozenset(("CYCL", "CYCLE", "PATTERN"))

# Zyklusnamen: CYCLE81..CYCLE899, POCKET1..4, SLOT1/2, HOLES1/2, dazu die von
# SolidCAM/ShopMill erzeugten E_... und F_... Unterprogramme.
_MARKE_RE = re.compile(r"^\s*(?:N\d+\s+)?([A-Za-z_]\w*)\s*:")
_SPRUNG = frozenset(("GOTOF", "GOTOB", "GOTOC", "GOTO", "CALL", "PCALL", "REPEAT",
                     "REPEATB", "LBL"))

_ZYKLUS_RE = re.compile(r"^(?:CYCLE\d*|POCKET\d*|SLOT\d*|HOLES\d*|LONGHOLE|"
                        r"CONTPRON|CONTDCON|CONTPRON|EXECUTE|E_[A-Z_0-9]+|F_[A-Z_0-9]+|"
                        r"DRILLING|BORING|TAPPING|MILLING|CUTTING)$")

# SINUMERIK-Konstanten beginnen mit Unterstrich, z. B. _OFF, _ROUGH, _FINISH
_KONSTANTE_RE = re.compile(r"^_[A-Z0-9_]+$")

# Zerleger. Zwei Fassungen, weil runde Klammern nur im ISO-Dialekt Kommentar
# sind - bei SINUMERIK wäre MSG("Text") sonst falsch eingefärbt.
_MUSTER_GEMEINSAM = r"""
      (?P<sem>;[^\n]*)
    | (?P<txt>"[^"\n]*"?|'[^'\n]*'?)
    | (?P<proz>%[^\n]*)
    | (?P<sys>\$[A-Za-z_][A-Za-z_0-9\[\]\.]*)
    | (?P<makro>\#\s*\d+|\#\[)
    | (?P<adr>[A-Za-z])(?:\s*=\s*|\s*)(?P<wert>[-+]?(?:\d+(?:\.\d*)?|\.\d+))
    | (?P<wort>[A-Za-z_][A-Za-z_0-9]*)
    | (?P<zahl>[-+]?(?:\d+(?:\.\d*)?|\.\d+))
"""
_RE_ISO = re.compile(r"(?P<kl>\([^)\n]*\)?)|" + _MUSTER_GEMEINSAM, re.VERBOSE)
_RE_SONST = re.compile(_MUSTER_GEMEINSAM, re.VERBOSE)

# G-Befehle, die eine eigene Farbe bekommen
_G_BAHN = frozenset((1, 2, 3, 5, 6, 33, 34, 35, 331, 332))
_G_ZYKLUS_ISO = frozenset((73, 74, 76, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89))


def _ist_nullpunkt(i):
    """G54..G59 (ISO) bzw. G500..G599 (SINUMERIK) und G53/G153 (unterdrückt)."""
    return 54 <= i <= 59 or 500 <= i <= 599 or i in (53, 153, 507)


def _adress_klasse(buchstabe, wert, dialekt):
    """Ordnet ein Adresswort (z. B. G1, X120.5, M30) einer Farbklasse zu."""
    try:
        zahl = int(float(wert)) if wert is not None else -1
    except (TypeError, ValueError):
        zahl = -1

    if buchstabe == "G":
        if zahl == 0:
            return "g_eilgang"
        if zahl in _G_BAHN:
            return "g_bahn"
        if zahl in (40, 41, 42):
            return "g_wkzkorr"
        if _ist_nullpunkt(zahl):
            return "g_nullpunkt"
        if dialekt == "iso" and zahl in _G_ZYKLUS_ISO:
            return "zyklus"
        return "g_sonstig"
    if buchstabe == "M":
        if zahl in (0, 1, 2, 6, 17, 30, 60):
            return "m_wichtig"
        return "m_code"
    if buchstabe == "N":
        return "satznummer"
    if buchstabe in "XYZ":
        return "koordinate"
    if buchstabe in "ABCUVW":
        return "drehachse"
    if buchstabe in "IJK":
        return "kreis"
    if buchstabe == "R":
        # SINUMERIK: R1 ist ein Rechenparameter. Heidenhain: R0/RL/RR ist die
        # Radiuskorrektur. ISO: R ist Kreisradius bzw. Rückzugsebene.
        if dialekt == "sinumerik":
            return "variable"
        return "g_wkzkorr" if dialekt == "heidenhain" else "kreis"
    if buchstabe == "F":
        return "vorschub"
    if buchstabe == "S":
        return "drehzahl"
    if buchstabe in "TDH":
        return "werkzeug"
    if buchstabe == "Q":
        if dialekt == "heidenhain":
            return "variable"
        return "kreis" if dialekt == "iso" else "zahl"
    if buchstabe == "P" and dialekt == "iso":
        return "kreis"
    if buchstabe == "O" and dialekt == "iso":
        return "programm"
    if buchstabe == "L" and dialekt == "heidenhain":
        return "g_bahn"
    return "zahl"


def _wort_klasse(wort, dialekt):
    """Ordnet ein Wort ohne Zahl (z. B. CYCLE81, GOTOF, FMAX) einer Farbklasse zu."""
    w = wort.upper()
    if dialekt == "heidenhain":
        if w in HH_BAHN:
            return "g_bahn"
        if w in HH_KORR:
            return "g_wkzkorr"
        if w in HH_ZYKLUS:
            return "zyklus"
        if w in ("FMAX", "FAUTO", "FZ", "FU"):
            return "vorschub"
        if w in HH_SCHLUESSEL:
            return "schluessel"
    elif dialekt == "sinumerik":
        if _KONSTANTE_RE.match(w):
            return "variable"
        if _ZYKLUS_RE.match(w):
            return "zyklus"
        if w in ("CR", "AR"):
            return "kreis"
        if w in SINU_SCHLUESSEL:
            return "schluessel"
    else:
        if w in ISO_SCHLUESSEL:
            return "schluessel"
    if len(w) == 1:
        return _adress_klasse(w, None, dialekt)
    return None


def zerlege(zeile, dialekt):
    """Zerlegt einen NC-Satz in (Anfang, Ende, Farbklasse).

    Liefert nur Abschnitte, die eingefärbt werden - alles Übrige bleibt in
    der normalen Textfarbe.
    """
    muster = _RE_ISO if dialekt == "iso" else _RE_SONST
    treffer = []
    erster = True
    # Sprungmarke am Satzanfang, z. B. "MARKE1:" oder "N10 ENDE:"
    marke = _MARKE_RE.match(zeile)
    marke_ende = marke.end(1) if marke else -1
    sprung = False
    for m in muster.finditer(zeile):
        g = m.groupdict()
        klasse = None
        if g.get("kl") is not None or g["sem"] is not None:
            klasse = "kommentar"
        elif g["txt"] is not None:
            klasse = "text"
        elif g["proz"] is not None:
            klasse = "programm"
        elif g["sys"] is not None or g["makro"] is not None:
            klasse = "variable"
        elif g["adr"] is not None:
            klasse = _adress_klasse(g["adr"].upper(), g["wert"], dialekt)
        elif g["wort"] is not None:
            klasse = _wort_klasse(g["wort"], dialekt)
        elif g["zahl"] is not None:
            # Heidenhain: die Zahl am Satzanfang ist die Satznummer.
            klasse = "satznummer" if (erster and dialekt == "heidenhain") else "zahl"
        if klasse == "schluessel" and g["wort"].upper() in _SPRUNG:
            sprung = True
        elif klasse is None and sprung and g["wort"] is not None:
            klasse = "marke"          # Sprungziel hinter GOTOF/CALL
            sprung = False
        elif g["wort"] is None:
            sprung = False
        if m.end() == marke_ende and g["wort"] is not None:
            klasse = "marke"          # Sprungmarke am Satzanfang
        erster = False
        if klasse:
            # Wert hinter "CR=" o. ä. in derselben Farbe wie die Adresse
            if (treffer and klasse == "zahl"
                    and treffer[-1][2] in ("kreis", "koordinate", "drehachse",
                                           "vorschub", "drehzahl", "werkzeug")
                    and zeile[treffer[-1][1]:m.start()].strip() == "="):
                a, _b, k = treffer.pop()
                treffer.append((a, m.end(), k))
                continue
            treffer.append((m.start(), m.end(), klasse))
    return treffer


def dialekt_erkennen(zeilen, pfad=""):
    """Erkennt den Dialekt am Dateiinhalt; Dateiendung entscheidet im Zweifel."""
    probe = "\n".join(zeilen[:400]).upper()
    if "BEGIN PGM" in probe or re.search(r"^\s*\d+\s+(?:L|TOOL CALL|CYCL DEF|LBL)\b",
                                         probe, re.M):
        return "heidenhain"
    punkte_s = 0
    for zeichen, gewicht in (("%_N_", 3), ("_MPF", 3), ("CYCLE8", 2), ("GOTOF", 2),
                             ("MSG(", 2), ("TRANS ", 1), ("STOPRE", 2), ("MCALL", 2),
                             ("DEF REAL", 2), ("G500", 2), ("SUPA", 1)):
        if zeichen in probe:
            punkte_s += gewicht
    if re.search(r"^\s*(?:N\d+\s+)?R\d+\s*=", probe, re.M):
        punkte_s += 2
    punkte_i = 0
    for zeichen, gewicht in (("G43", 2), ("G28", 1), ("M98", 2), ("M99", 2), ("#1", 1)):
        if zeichen in probe:
            punkte_i += gewicht
    if re.search(r"^\s*O\d{3,}", probe, re.M):
        punkte_i += 3
    if re.search(r"^\s*\(", probe, re.M):
        punkte_i += 2
    if punkte_s > punkte_i:
        return "sinumerik"
    if punkte_i > punkte_s:
        return "iso"
    return "sinumerik" if pfad.lower().endswith((".mpf", ".spf")) else "iso"


# ---------------------------------------------------------------------------
# Teil 2: Farben
# ---------------------------------------------------------------------------
#
# Am Markt gibt es keinen veröffentlichten Farbstandard: CIMCO Edit,
# UltraEdit, Notepad++ und die VS-Code-Erweiterungen lassen die Farben alle
# frei einstellen. Einig sind sich die Werkzeuge nur bei den Klassen und bei
# wenigen Festlegungen - Kommentare grün, Satznummern blass, Eilgang und
# Programmhalt in Signalfarben. Die Voreinstellung unten folgt diesem
# gemeinsamen Nenner und ordnet die G-Befehle in einer Blaufamilie, damit die
# sicherheitsrelevanten Befehle (G0, G40-G42, M0/M30) herausstechen.

# (Schlüssel, Anzeigename, Gruppe, Beispiel)
SYNTAX_KLASSEN = (
    ("kommentar",   "Kommentar",                     "Struktur",  "; Bohren D10.2"),
    ("programm",    "Programmkopf und -name",        "Struktur",  "%_N_DECKEL_MPF"),
    ("satznummer",  "Satznummer",                    "Struktur",  "N120"),
    ("marke",       "Sprungmarke und Sprungziel",    "Struktur",  "MARKE1:"),
    ("text",        "Zeichenkette",                  "Struktur",  '"FRAESER_D8"'),
    ("g_eilgang",   "G0 Eilgang",                    "G-Befehle", "G0"),
    ("g_bahn",      "G1/G2/G3 Bahnbewegung",         "G-Befehle", "G1 G2 G3"),
    ("g_wkzkorr",   "G40-G42 Werkzeugkorrektur",     "G-Befehle", "G41 G40"),
    ("g_nullpunkt", "G54-G59 Nullpunktverschiebung", "G-Befehle", "G54"),
    ("g_sonstig",   "Übrige G-Befehle",             "G-Befehle", "G17 G90 G64"),
    ("m_wichtig",   "M0/M1/M2/M6/M30 Halt, Wechsel", "M-Befehle", "M6 M30"),
    ("m_code",      "Übrige M-Befehle",             "M-Befehle", "M3 M7 M161"),
    ("koordinate",  "Koordinaten X Y Z",             "Adressen",  "X120.5"),
    ("drehachse",   "Dreh- und Zusatzachsen",        "Adressen",  "A0 B90 C45"),
    ("kreis",       "Kreis- und Zyklusparameter",    "Adressen",  "I5 J0 CR=12.5"),
    ("vorschub",    "Vorschub F",                    "Adressen",  "F250"),
    ("drehzahl",    "Drehzahl S",                    "Adressen",  "S4500"),
    ("werkzeug",    "Werkzeug T D H",                "Adressen",  "T5 D1"),
    ("zyklus",      "Zyklen",                        "Befehle",   "CYCLE81 CYCLE800"),
    ("schluessel",  "Schlüsselwörter",             "Befehle",   "IF GOTOF MSG"),
    ("variable",    "Variablen und Parameter",       "Befehle",   "R3 #100 $AA_IM"),
    ("zahl",        "Übrige Zahlen",                "Befehle",   "650"),
)

# Oberflächenfarben des Editors (nicht Syntax)
EDITOR_FARBEN = (
    ("editor_bg",     "Hintergrund"),
    ("editor_fg",     "Normaler Text"),
    ("editor_sel",    "Auswahl"),
    ("cursor",        "Schreibmarke"),
    ("zeile_bg",      "Aktuelle Zeile"),
    ("gutter_bg",     "Zeilennummern, Hintergrund"),
    ("gutter_fg",     "Zeilennummern, Schrift"),
    ("gutter_linie",  "Trennlinie"),
    ("hand_bg",       "Von Hand geändert, Hintergrund"),
    ("hand_balken",   "Von Hand geändert, Markierung"),
    ("hand_neu",      "Von Hand eingefügt, Markierung"),
    ("hand_weg",      "Gelöscht, Markierung"),
    ("treffer_bg",    "Suchtreffer"),
    ("treffer_akt",   "Aktueller Suchtreffer"),
)

FARBEN_HELL = {
    "kommentar": ("#2E7D32", 0, 1), "programm": ("#37474F", 1, 0),
    "satznummer": ("#9AA3AD", 0, 0), "marke": ("#B45309", 1, 0),
    "text": ("#8A5A00", 0, 0),
    "g_eilgang": ("#E8590C", 1, 0), "g_bahn": ("#1565C0", 1, 0),
    "g_wkzkorr": ("#7B1FA2", 1, 0), "g_nullpunkt": ("#0D47A1", 1, 0),
    "g_sonstig": ("#5A7D99", 0, 0),
    "m_wichtig": ("#C62828", 1, 0), "m_code": ("#A21B72", 0, 0),
    "koordinate": ("#0E7490", 0, 0), "drehachse": ("#1A8CA8", 0, 0),
    "kreis": ("#6D4C41", 0, 0), "vorschub": ("#8A6D00", 0, 0),
    "drehzahl": ("#4D7C0F", 0, 0), "werkzeug": ("#B45309", 1, 0),
    "zyklus": ("#5B21B6", 1, 0), "schluessel": ("#4338CA", 1, 0),
    "variable": ("#00796B", 0, 0), "zahl": ("#1E2830", 0, 0),
    "editor_bg": "#FFFFFF", "editor_fg": "#1E2830", "editor_sel": "#BBD5EC",
    "cursor": "#1E2830", "zeile_bg": "#F2F6FA",
    "gutter_bg": "#EDF0F3", "gutter_fg": "#8C99A6", "gutter_linie": "#C3CAD1",
    "hand_bg": "#FFF2CC", "hand_balken": "#E8A33D", "hand_neu": "#2E9E5B",
    "hand_weg": "#C62828", "treffer_bg": "#FFE9A3", "treffer_akt": "#FFBE2E",
}

FARBEN_DUNKEL = {
    "kommentar": ("#6FB36F", 0, 1), "programm": ("#AEBECD", 1, 0),
    "satznummer": ("#5F6B78", 0, 0), "marke": ("#E0A458", 1, 0),
    "text": ("#D2A15A", 0, 0),
    "g_eilgang": ("#FF8A4C", 1, 0), "g_bahn": ("#5FC8FD", 1, 0),
    "g_wkzkorr": ("#C792EA", 1, 0), "g_nullpunkt": ("#3F8FD6", 1, 0),
    "g_sonstig": ("#7E9CB5", 0, 0),
    "m_wichtig": ("#FF6B6B", 1, 0), "m_code": ("#F178B6", 0, 0),
    "koordinate": ("#4DD0E1", 0, 0), "drehachse": ("#80DEEA", 0, 0),
    "kreis": ("#BCAAA4", 0, 0), "vorschub": ("#D4B55F", 0, 0),
    "drehzahl": ("#A3C644", 0, 0), "werkzeug": ("#FFB74D", 1, 0),
    "zyklus": ("#B39DFF", 1, 0), "schluessel": ("#8C9EFF", 1, 0),
    "variable": ("#4DB6AC", 0, 0), "zahl": ("#D7DEE6", 0, 0),
    "editor_bg": "#141C26", "editor_fg": "#D7DEE6", "editor_sel": "#2F5574",
    "cursor": "#E8EAF0", "zeile_bg": "#1B2430",
    "gutter_bg": "#111921", "gutter_fg": "#5F6B78", "gutter_linie": "#2A3643",
    "hand_bg": "#3B2F12", "hand_balken": "#E8A33D", "hand_neu": "#3FBF74",
    "hand_weg": "#FF6B6B", "treffer_bg": "#4A431F", "treffer_akt": "#8A6D1F",
}

# Farben der Oberfläche außerhalb des Editors - hell wie beim Laserprogramm
THEMEN = {
    "hell": {
        "bg": "#E8EBEE", "panel": "#F6F7F8", "ink": "#1E2830", "muted": "#5E6973",
        "line": "#C3CAD1", "accent": "#1C74AE", "accent_hi": "#2687C6",
        "brand": "#5FC8FD", "plate_hi": "#1B2839", "plate_lo": "#0C1321",
        "plate_edge": "#33465E", "knopf": "#DDE2E6", "knopf_hi": "#CFD6DC",
        "knopf_ab": "#C3CAD1", "feld": "#FFFFFF",
        "reiter": "#D7DDE2", "reiter_aktiv": "#F6F7F8", "reiter_rand": "#C3CAD1",
    },
    "dunkel": {
        "bg": "#1B2430", "panel": "#222D3A", "ink": "#D7DEE6", "muted": "#8A97A5",
        "line": "#33414F", "accent": "#2687C6", "accent_hi": "#3C9EDC",
        "brand": "#5FC8FD", "plate_hi": "#1B2839", "plate_lo": "#0C1321",
        "plate_edge": "#33465E", "knopf": "#2C3A49", "knopf_hi": "#38485A",
        "knopf_ab": "#44566B", "feld": "#141C26",
        "reiter": "#1F2935", "reiter_aktiv": "#222D3A", "reiter_rand": "#33414F",
    },
}

STANDARD_FARBEN = {"hell": FARBEN_HELL, "dunkel": FARBEN_DUNKEL}


def farben_standard(design):
    """Liefert eine änderbare Kopie der Voreinstellung."""
    quelle = STANDARD_FARBEN.get(design, FARBEN_HELL)
    return {k: (list(v) if isinstance(v, tuple) else v) for k, v in quelle.items()}


def farbe_von(farben, schluessel, design):
    """Farbwert eines Eintrags, mit Rückfall auf die Voreinstellung."""
    wert = farben.get(schluessel)
    if wert is None:
        wert = STANDARD_FARBEN.get(design, FARBEN_HELL).get(schluessel, "#000000")
    return wert[0] if isinstance(wert, (list, tuple)) else wert


def stil_von(farben, schluessel, design):
    """(Farbe, fett, kursiv) einer Syntaxklasse."""
    wert = farben.get(schluessel)
    if not isinstance(wert, (list, tuple)):
        wert = STANDARD_FARBEN.get(design, FARBEN_HELL).get(schluessel, ("#000000", 0, 0))
    if not isinstance(wert, (list, tuple)):
        return (wert, 0, 0)
    farbe = wert[0]
    fett = bool(wert[1]) if len(wert) > 1 else False
    kursiv = bool(wert[2]) if len(wert) > 2 else False
    return (farbe, fett, kursiv)


# ---------------------------------------------------------------------------
# Teil 3: Einstellungen
# ---------------------------------------------------------------------------

def daten_verzeichnis():
    """%APPDATA%\\NC-Editor unter Windows, sonst ~/.nc-editor."""
    basis = os.environ.get("APPDATA")
    if basis:
        ordner = os.path.join(basis, APP_NAME)
    else:
        ordner = os.path.join(os.path.expanduser("~"), ".nc-editor")
    try:
        os.makedirs(ordner, exist_ok=True)
    except OSError:
        ordner = os.path.expanduser("~")
    return ordner


def einstellungen_pfad():
    return os.path.join(daten_verzeichnis(), "einstellungen.json")


VORGABEN = {
    "design": "hell",
    "fenster": "1180x780",
    "schrift": "",            # leer = automatisch (Consolas bzw. DejaVu Sans Mono)
    "schriftgroesse": 11,
    "tabbreite": 4,
    "gliederung_anzeigen": True,
    "trefferliste_anzeigen": True,
    "zeilennummern": True,
    "aktive_zeile": True,
    "hand_staerke": "normal",   # dezent | normal | stark
    "hand_erkennen": True,
    "dialekt": "auto",
    "suche_grossklein": False,
    "suche_ganzes_wort": False,
    "suche_regex": False,
    "zuletzt": [],
    "letzter_ordner": "",
    "sicherungskopie": True,
    "einzelnes_fenster": True,
    "original_bei_neuausgabe": True,
    "aufraeumen_beim_beenden": True,
    "aufbewahrung_tage": 90,
    "originale_hoechstzahl": 400,
    "farben": {},             # {"hell": {...}, "dunkel": {...}}
}


def einstellungen_laden():
    import json
    d = dict(VORGABEN)
    d["farben"] = {}
    d["zuletzt"] = []
    try:
        with open(einstellungen_pfad(), "r", encoding="utf-8") as fh:
            gelesen = json.load(fh)
        if isinstance(gelesen, dict):
            for k, v in gelesen.items():
                if k in VORGABEN:
                    d[k] = v
    except Exception:
        pass
    if not isinstance(d.get("farben"), dict):
        d["farben"] = {}
    for design in ("hell", "dunkel"):
        eigen = d["farben"].get(design)
        voll = farben_standard(design)
        if isinstance(eigen, dict):
            voll.update(eigen)
        d["farben"][design] = voll
    if d.get("design") not in THEMEN:
        d["design"] = "hell"
    return d


def einstellungen_speichern(d):
    import json
    try:
        with open(einstellungen_pfad(), "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Teil 4: Originale und Erkennung von Hand-Änderungen
# ---------------------------------------------------------------------------
#
# Beim ersten Öffnen wird eine Kopie des Programms als "Original" abgelegt -
# das ist der Stand, wie SolidCAM ihn ausgegeben hat. Jede spätere Abweichung
# gilt als Hand-Änderung und wird stärker hervorgehoben. Die Kopien liegen
# in %APPDATA%\NC-Editor\originale und verändern die NC-Datei selbst nicht.

MAX_DIFF_ZEILEN = 200000      # darüber wird nicht mehr verglichen


def _original_ordner():
    ordner = os.path.join(daten_verzeichnis(), "originale")
    try:
        os.makedirs(ordner, exist_ok=True)
    except OSError:
        pass
    return ordner


def _schluessel(pfad):
    import hashlib
    norm = os.path.normcase(os.path.abspath(pfad))
    return hashlib.sha1(norm.encode("utf-8", "replace")).hexdigest()[:16]


def _verzeichnis_laden():
    import json
    try:
        with open(os.path.join(_original_ordner(), "verzeichnis.json"),
                  "r", encoding="utf-8") as fh:
            d = json.load(fh)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _verzeichnis_speichern(d):
    import json
    try:
        with open(os.path.join(_original_ordner(), "verzeichnis.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=1, ensure_ascii=False)
    except Exception:
        pass


def datei_stand(pfad):
    """Größe und Zeitmarke einer Datei - woran sich ein neuer Lauf erkennen lässt."""
    try:
        angaben = os.stat(pfad)
    except OSError:
        return None
    return {"groesse": angaben.st_size, "mtime": round(angaben.st_mtime, 3)}


def stand_gleich(a, b):
    """True, wenn die Datei seitdem unverändert ist."""
    if not a or not b:
        return False
    if a.get("groesse") != b.get("groesse"):
        return False
    try:
        return abs(float(a.get("mtime", 0)) - float(b.get("mtime", 0))) < 0.002
    except (TypeError, ValueError):
        return False


def original_laden(pfad):
    """Zeilen des hinterlegten Originals oder None."""
    datei = os.path.join(_original_ordner(), _schluessel(pfad) + ".txt")
    try:
        with open(datei, "r", encoding="utf-8", errors="replace", newline="") as fh:
            inhalt = fh.read()
    except Exception:
        return None
    try:
        os.utime(datei, None)       # Zeitstempel = zuletzt gebraucht
    except OSError:
        pass
    return inhalt.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def original_setzen(pfad, zeilen):
    """Legt den aktuellen Stand als Original ab."""
    import time
    datei = os.path.join(_original_ordner(), _schluessel(pfad) + ".txt")
    try:
        with open(datei, "w", encoding="utf-8", newline="") as fh:
            fh.write("\n".join(zeilen))
    except Exception:
        return False
    d = _verzeichnis_laden()
    eintrag = {
        "quelle": os.path.abspath(pfad),
        "gesetzt": time.strftime("%d.%m.%Y %H:%M"),
        "zeilen": len(zeilen),
    }
    # Zustand der NC-Datei festhalten. Weicht er später ab, hat ein anderes
    # Programm sie neu geschrieben - meist der Postprozessor.
    eintrag.update(datei_stand(pfad) or {})
    d[_schluessel(pfad)] = eintrag
    _verzeichnis_speichern(d)
    return True


def original_stand_merken(pfad):
    """Hält fest, dass die Datei in ihrem jetzigen Zustand von uns stammt."""
    d = _verzeichnis_laden()
    eintrag = d.get(_schluessel(pfad))
    if not eintrag:
        return False
    stand = datei_stand(pfad)
    if not stand:
        return False
    eintrag.update(stand)
    d[_schluessel(pfad)] = eintrag
    _verzeichnis_speichern(d)
    return True


def original_info(pfad):
    return _verzeichnis_laden().get(_schluessel(pfad))


def original_entfernen(pfad):
    datei = os.path.join(_original_ordner(), _schluessel(pfad) + ".txt")
    try:
        os.remove(datei)
    except OSError:
        pass
    d = _verzeichnis_laden()
    if d.pop(_schluessel(pfad), None) is not None:
        _verzeichnis_speichern(d)


class Einzelinstanz(object):
    """Sorgt dafür, dass alle Programme in einem Fenster landen.

    Windows startet beim Doppelklick auf eine Datei jedes Mal ein neues
    Programm. Das erste Programm hält eine Sperrdatei und schaut regelmäßig
    in einen Ablageordner. Jedes weitere Programm legt den Dateinamen dort ab
    und beendet sich sofort - die Datei erscheint dann als neuer Reiter im
    schon offenen Fenster.

    Die Sperre hängt am geöffneten Dateigriff: Stürzt das Programm ab, gibt
    das Betriebssystem sie von selbst frei, es bleibt nichts hängen.
    """

    def __init__(self):
        self.griff = None
        self.fuehrend = False

    def _sperrdatei(self):
        return os.path.join(daten_verzeichnis(), "instanz.lock")

    def ablage(self):
        ordner = os.path.join(daten_verzeichnis(), "anfragen")
        try:
            os.makedirs(ordner, exist_ok=True)
        except OSError:
            pass
        return ordner

    def uebernehmen(self):
        """True, wenn dieses Programm das führende Fenster wird."""
        try:
            self.griff = os.open(self._sperrdatei(), os.O_CREAT | os.O_RDWR)
        except OSError:
            self.fuehrend = True          # im Zweifel ein eigenes Fenster
            return True
        try:
            if sys.platform.startswith("win"):
                import msvcrt

                msvcrt.locking(self.griff, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.griff, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:
            self.fuehrend = True          # ohne Sperrmöglichkeit eigenes Fenster
            return True
        except Exception:
            self.freigeben()
            return False
        self.fuehrend = True
        # Liegengebliebene Anfragen von früher wegräumen: Sie können nicht
        # mehr aktuell sein, denn bis eben lief kein Fenster.
        ordner = self.ablage()
        try:
            for name in os.listdir(ordner):
                try:
                    os.remove(os.path.join(ordner, name))
                except OSError:
                    pass
        except OSError:
            pass
        return True

    def anfrage_stellen(self, dateien, warten=4.0):
        """Reicht die Dateien an das laufende Fenster weiter.

        Liefert False, wenn sich dort nichts tut - dann öffnet der Aufrufer
        doch ein eigenes Fenster, damit ein Doppelklick nie ins Leere geht.
        """
        import time

        ordner = self.ablage()
        ziel = os.path.join(ordner, "%015d-%d.txt"
                            % (int(time.time() * 1000), os.getpid()))
        inhalt = "\n".join(os.path.abspath(d) for d in dateien)
        try:
            zwischen = ziel + ".tmp"
            with open(zwischen, "w", encoding="utf-8") as fh:
                fh.write(inhalt)
            os.replace(zwischen, ziel)    # erst vollständig, dann sichtbar
        except OSError:
            return False
        ende = time.time() + warten
        while time.time() < ende:
            if not os.path.exists(ziel):
                return True               # wurde abgeholt
            time.sleep(0.15)
        try:
            os.remove(ziel)
        except OSError:
            pass
        return False

    def abholen(self):
        """Liefert die Dateien, die andere Programme abgelegt haben."""
        dateien = []
        gab_anfrage = False
        ordner = self.ablage()
        try:
            namen = sorted(n for n in os.listdir(ordner) if n.endswith(".txt"))
        except OSError:
            return (dateien, gab_anfrage)
        for name in namen:
            pfad = os.path.join(ordner, name)
            try:
                with open(pfad, "r", encoding="utf-8") as fh:
                    inhalt = fh.read()
                os.remove(pfad)
            except OSError:
                continue
            gab_anfrage = True
            dateien.extend(z.strip() for z in inhalt.split("\n") if z.strip())
        return (dateien, gab_anfrage)

    def freigeben(self):
        if self.griff is None:
            return
        try:
            if sys.platform.startswith("win"):
                import msvcrt

                os.lseek(self.griff, 0, os.SEEK_SET)
                msvcrt.locking(self.griff, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.griff, fcntl.LOCK_UN)
        except Exception:
            pass
        try:
            os.close(self.griff)
        except OSError:
            pass
        self.griff = None


def originale_aufraeumen(tage=90, hoechstzahl=400, nur_pruefen=False, schonen=()):
    """Entfernt abgelegte Originale, die nicht mehr gebraucht werden.

    Weg kommen Kopien, deren NC-Datei es nicht mehr gibt, Kopien ohne
    Verzeichniseintrag und solche, die seit `tage` Tagen nicht mehr geöffnet
    wurden. Bleiben danach mehr als `hoechstzahl` übrig, fallen zusätzlich
    die am längsten unbenutzten weg. `schonen` nennt Pfade, die auf jeden
    Fall bleiben - das sind die gerade geöffneten Programme.

    Mit nur_pruefen=True wird nichts gelöscht, nur gezählt.
    Liefert (entfernt, freigegebene Bytes, verbleibend, verbleibende Bytes).
    """
    import time

    ordner = _original_ordner()
    verzeichnis = _verzeichnis_laden()
    geschont = {_schluessel(p) for p in schonen if p}
    grenze = time.time() - max(1, int(tage or 1)) * 86400
    eintraege = []
    try:
        dateien = [d for d in os.listdir(ordner) if d.endswith(".txt")]
    except OSError:
        return (0, 0, 0, 0)
    for name in dateien:
        schluessel = name[:-4]
        datei = os.path.join(ordner, name)
        try:
            benutzt = os.path.getmtime(datei)
            groesse = os.path.getsize(datei)
        except OSError:
            continue
        info = verzeichnis.get(schluessel)
        quelle = (info or {}).get("quelle", "")
        eintraege.append((benutzt, schluessel, datei, groesse, quelle, info is not None))

    weg, bleiben = [], []
    for eintrag in eintraege:
        benutzt, schluessel, _datei, _groesse, quelle, bekannt = eintrag
        if schluessel in geschont:
            bleiben.append(eintrag)
        elif not bekannt or not quelle:
            weg.append(eintrag)                       # verwaiste Kopie
        elif not os.path.isfile(quelle):
            weg.append(eintrag)                       # NC-Datei gibt es nicht mehr
        elif benutzt < grenze:
            weg.append(eintrag)                       # lange nicht gebraucht
        else:
            bleiben.append(eintrag)
    bleiben.sort(key=lambda e: e[0], reverse=True)
    if hoechstzahl and len(bleiben) > int(hoechstzahl):
        zuviel = [e for e in bleiben[int(hoechstzahl):] if e[1] not in geschont]
        bleiben = [e for e in bleiben if e not in zuviel]
        weg.extend(zuviel)

    frei = sum(e[3] for e in weg)
    if not nur_pruefen and weg:
        for _b, schluessel, datei, _g, _q, _bekannt in weg:
            try:
                os.remove(datei)
            except OSError:
                pass
            verzeichnis.pop(schluessel, None)
        _verzeichnis_speichern(verzeichnis)
    return (len(weg), frei, len(bleiben), sum(e[3] for e in bleiben))


def originale_alle_loeschen(schonen=()):
    """Löscht alle abgelegten Originale bis auf die gerade geöffneten."""
    ordner = _original_ordner()
    verzeichnis = _verzeichnis_laden()
    geschont = {_schluessel(p) for p in schonen if p}
    anzahl = frei = 0
    try:
        dateien = [d for d in os.listdir(ordner) if d.endswith(".txt")]
    except OSError:
        return (0, 0)
    for name in dateien:
        schluessel = name[:-4]
        if schluessel in geschont:
            continue
        datei = os.path.join(ordner, name)
        try:
            frei += os.path.getsize(datei)
            os.remove(datei)
            anzahl += 1
        except OSError:
            continue
        verzeichnis.pop(schluessel, None)
    _verzeichnis_speichern(verzeichnis)
    return (anzahl, frei)


def groesse_lesbar(bytes_):
    if bytes_ >= 1024 * 1024:
        return "%.1f MB" % (bytes_ / (1024.0 * 1024.0))
    if bytes_ >= 1024:
        return "%.0f KB" % (bytes_ / 1024.0)
    return "%d Bytes" % bytes_


def hand_aenderungen(original, aktuell):
    """Vergleicht Original und aktuellen Stand.

    Liefert (zeilen, gelöscht):
      zeilen    {Zeilennummer (ab 1): "g" geändert | "n" eingefügt}
      gelöscht {Zeilennummer: Anzahl der oberhalb dieser Zeile entfernten Zeilen}
    """
    import difflib
    if original is None:
        return {}, {}
    if len(original) > MAX_DIFF_ZEILEN or len(aktuell) > MAX_DIFF_ZEILEN:
        return {}, {}
    zeilen = {}
    geloescht = {}
    vergleich = difflib.SequenceMatcher(None, original, aktuell, autojunk=False)
    for art, i1, i2, j1, j2 in vergleich.get_opcodes():
        if art == "equal":
            continue
        if art == "replace":
            for j in range(j1, j2):
                zeilen[j + 1] = "g"
            # Wurden dabei mehr Zeilen entfernt als neu geschrieben, bekommt
            # die Lücke unterhalb des geänderten Blocks eine Löschmarke.
            fehlend = (i2 - i1) - (j2 - j1)
            if fehlend > 0:
                stelle = min(max(1, j2 + 1), max(1, len(aktuell)))
                geloescht[stelle] = geloescht.get(stelle, 0) + fehlend
        elif art == "insert":
            for j in range(j1, j2):
                zeilen[j + 1] = "n"
        elif art == "delete":
            # Marke sitzt auf der Lücke oberhalb dieser Zeile
            stelle = min(max(1, j1 + 1), max(1, len(aktuell)))
            geloescht[stelle] = geloescht.get(stelle, 0) + (i2 - i1)
    return zeilen, geloescht


# ---------------------------------------------------------------------------
# Teil 5: Oberfläche - Logo, Typenschild, Farbgebung
# ---------------------------------------------------------------------------
#
# Logo und Programmsymbol sind eingebaut (wie bei ezd2lbrn), damit das
# Programm als einzelne Datei weitergegeben werden kann. Eine Datei
# "logo.png" neben dem Programm hat Vorrang.

LOGO_PNG_B64 = (
    "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"
    "RU5ErkJggg=="
)
ICON_PNG_B64 = (
    "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"
)


def ui_schriften():
    """(Text, fett, Überschrift, Festbreite) passend zum Betriebssystem."""
    if sys.platform.startswith("win"):
        return (("Segoe UI", 10), ("Segoe UI Semibold", 10),
                ("Segoe UI Semibold", 20), ("Consolas", 11))
    return (("DejaVu Sans", 10), ("DejaVu Sans", 10, "bold"),
            ("DejaVu Sans", 18, "bold"), ("DejaVu Sans Mono", 10))


def editor_schrift(einst):
    """Festbreitenschrift des Editors aus den Einstellungen."""
    name = (einst.get("schrift") or "").strip()
    if not name:
        name = "Consolas" if sys.platform.startswith("win") else "DejaVu Sans Mono"
    try:
        groesse = int(einst.get("schriftgroesse") or 11)
    except (TypeError, ValueError):
        groesse = 11
    return (name, max(6, min(40, groesse)))


def link_oeffnen(adresse):
    """Öffnet eine Internetadresse im Standardbrowser.

    Unter Windows über os.startfile - das klappt auch in der gebauten exe.
    webbrowser wird mit einer normalen import-Anweisung geholt und nicht über
    __import__("webbrowser"): die dynamische Form erzeugt keinen IMPORT_NAME im
    Bytecode, PyInstaller findet das Modul dann nicht und verpackt es nicht mit.
    In der exe lief der Klick deshalb früher ins Leere.
    """
    try:
        if sys.platform.startswith("win"):
            os.startfile(adresse)                      # noqa: S606
            return True
    except Exception:
        pass
    try:
        import webbrowser

        return bool(webbrowser.open(adresse))
    except Exception:
        return False


def asset_pfad(namen):
    """Sucht Dateien neben dem Programm (auch in der .exe)."""
    ordner = []
    if getattr(sys, "_MEIPASS", None):
        ordner.append(sys._MEIPASS)
    if getattr(sys, "frozen", False):
        ordner.append(os.path.dirname(sys.executable))
    ordner.append(os.path.dirname(os.path.abspath(__file__)))
    for d in ordner:
        for name in namen:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return None


LOGO_NAMEN = ("logo.png", "iot-simply.png", "iot_simply.png", "iotsimply.png")


def logo_laden(tk, master, hoehe, symbol=False):
    """Logo: logo.png neben dem Programm hat Vorrang, sonst das eingebaute."""
    import base64
    from io import BytesIO

    p = None if symbol else asset_pfad(LOGO_NAMEN)
    roh = None
    if not p:
        roh = base64.b64decode("".join(ICON_PNG_B64 if symbol else LOGO_PNG_B64))
    try:
        from PIL import Image, ImageTk

        im = Image.open(p if p else BytesIO(roh)).convert("RGBA")
        b = max(1, int(im.width * hoehe / float(im.height)))
        return ImageTk.PhotoImage(im.resize((b, hoehe), Image.LANCZOS), master=master)
    except Exception:
        pass
    try:
        bild = (tk.PhotoImage(file=p, master=master) if p else
                tk.PhotoImage(data=base64.b64encode(roh).decode(), master=master))
        f = max(1, int(round(bild.height() / float(hoehe))))
        return bild.subsample(f, f) if f > 1 else bild
    except Exception:
        return None


def typenschild(cv, logo, titel, untertitel, design):
    """Kopfbereich im Stil eines eloxierten Typenschilds (wie ezd2lbrn)."""
    import math

    T = THEMEN[design]
    f_text, _fett, f_titel, _mono = ui_schriften()
    cv.delete("all")
    b = max(cv.winfo_width(), 300)
    h = int(cv["height"])
    x0, y0, x1, y1 = 10, 6, b - 10, h - 4
    if x1 <= x0 or y1 <= y0:
        return
    hell = [int(T["plate_hi"][i:i + 2], 16) for i in (1, 3, 5)]
    dunkel = [int(T["plate_lo"][i:i + 2], 16) for i in (1, 3, 5)]
    for y in range(y0, y1):                      # gebürstetes Aluminium
        t = (y - y0) / float(max(1, y1 - y0))
        t = 0.5 - 0.5 * math.cos(t * math.pi)
        c = [int(hell[k] + (dunkel[k] - hell[k]) * t) + (3 if y % 3 == 0 else 0)
             for k in range(3)]
        cv.create_line(x0, y, x1, y, fill="#%02x%02x%02x" % tuple(min(255, v) for v in c))
    cv.create_rectangle(x0, y0, x1, y1, outline=T["plate_edge"])
    cv.create_line(x0 + 1, y0 + 1, x1 - 1, y0 + 1, fill="#3A4D66")
    for rx, ry in ((x0 + 12, y0 + 12), (x1 - 12, y0 + 12),
                   (x0 + 12, y1 - 12), (x1 - 12, y1 - 12)):
        cv.create_oval(rx - 4, ry - 4, rx + 4, ry + 4, fill="#26364A", outline="#3E5470")
        cv.create_oval(rx - 2, ry - 2, rx + 1, ry + 1, fill="#5D7590", outline="")
    tx = x0 + 28
    if logo is not None:
        cv.create_image(tx, (y0 + y1) // 2, image=logo, anchor="w")
        tx += logo.width() + 16
        cv.create_line(tx - 8, y0 + 14, tx - 8, y1 - 14, fill="#2F4157")
    ty = (y0 + y1) // 2 - 9
    cv.create_text(tx, ty, text=titel, anchor="w", font=f_titel, fill="#E8EAF0")
    cv.create_text(tx, ty + 22, text=untertitel, anchor="w", font=f_text, fill="#9FB2C8")


def titelleiste_faerben(win, design):
    """Färbt die Titelleiste des Fensters passend zum Design.

    Die Titelleiste zeichnet Windows selbst, nicht Tk - im dunklen Design
    bliebe sie sonst weiß. Ab Windows 10 (1809) und unter Windows 11 lässt
    sie sich über DwmSetWindowAttribute umstellen. Auf allen anderen
    Systemen passiert nichts.
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes

        win.update_idletasks()
        fenster = win.winfo_id()
        eltern = ctypes.windll.user32.GetParent(fenster)
        ziel = eltern if eltern else fenster
        wert = ctypes.c_int(1 if design == "dunkel" else 0)
        for merkmal in (20, 19):      # DWMWA_USE_IMMERSIVE_DARK_MODE, ältere Nummer
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ziel, merkmal, ctypes.byref(wert), ctypes.sizeof(wert)) == 0:
                # Rahmen neu zeichnen lassen, sonst wirkt es erst beim nächsten Mal
                # SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED
                ctypes.windll.user32.SetWindowPos(
                    ziel, 0, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0020)
                return True
    except Exception:
        pass
    return False


def thema_anwenden(win, ttk, design):
    """Setzt das ttk-Thema für helles oder dunkles Design."""
    T = THEMEN[design]
    f_text, f_fett, _f_titel, _mono = ui_schriften()
    st = ttk.Style(win)
    try:
        st.theme_use("clam")
    except Exception:
        pass
    win.configure(bg=T["bg"])
    st.configure(".", background=T["bg"], foreground=T["ink"], font=f_text,
                 bordercolor=T["line"], lightcolor=T["panel"], darkcolor=T["line"],
                 troughcolor=T["bg"], focuscolor=T["accent"])
    st.configure("TFrame", background=T["bg"])
    st.configure("Panel.TFrame", background=T["panel"])
    st.configure("Leiste.TFrame", background=T["bg"])
    st.configure("TLabel", background=T["bg"], foreground=T["ink"])
    st.configure("Panel.TLabel", background=T["panel"], foreground=T["ink"])
    st.configure("Muted.TLabel", background=T["bg"], foreground=T["muted"])
    st.configure("Foot.TLabel", background=T["bg"], foreground=T["muted"])
    st.configure("Warn.TLabel", background=T["bg"],
                 foreground="#B3261E" if design == "hell" else "#FF9B93")
    st.configure("Section.TLabel", background=T["bg"], foreground=T["accent"], font=f_fett)
    st.configure("TLabelframe", background=T["bg"], bordercolor=T["line"],
                 relief="solid", borderwidth=1)
    st.configure("TLabelframe.Label", background=T["bg"], foreground=T["accent"], font=f_fett)
    st.configure("TCheckbutton", background=T["bg"], foreground=T["ink"])
    st.map("TCheckbutton", background=[("active", T["bg"])],
           indicatorcolor=[("selected", T["accent"]), ("!selected", T["feld"])])
    st.configure("TRadiobutton", background=T["bg"], foreground=T["ink"])
    st.map("TRadiobutton", background=[("active", T["bg"])],
           indicatorcolor=[("selected", T["accent"]), ("!selected", T["feld"])])
    st.configure("TEntry", fieldbackground=T["feld"], foreground=T["ink"],
                 bordercolor=T["line"], insertcolor=T["ink"], padding=3)
    st.map("TEntry", fieldbackground=[("disabled", T["bg"])],
           foreground=[("disabled", T["muted"])])
    st.configure("TCombobox", fieldbackground=T["feld"], foreground=T["ink"],
                 background=T["knopf"], arrowcolor=T["ink"], padding=2)
    st.map("TCombobox", fieldbackground=[("readonly", T["feld"]), ("disabled", T["bg"])],
           foreground=[("readonly", T["ink"])],
           selectbackground=[("readonly", T["feld"])],
           selectforeground=[("readonly", T["ink"])])
    st.configure("TButton", background=T["knopf"], foreground=T["ink"], padding=(10, 4))
    st.map("TButton", background=[("active", T["knopf_hi"]), ("pressed", T["knopf_ab"])])
    st.configure("Werkzeug.TButton", background=T["bg"], foreground=T["ink"],
                 borderwidth=1, padding=(8, 3))
    st.map("Werkzeug.TButton", background=[("active", T["knopf_hi"]),
                                           ("pressed", T["knopf_ab"])])
    st.configure("Accent.TButton", background=T["accent"], foreground="white",
                 font=f_fett, padding=(16, 5), bordercolor=T["accent"])
    st.map("Accent.TButton", background=[("active", T["accent_hi"]),
                                         ("pressed", T["accent"])],
           foreground=[("disabled", "#DDE6EA")])
    st.configure("Link.TButton", background=T["bg"], foreground=T["accent"],
                 borderwidth=0, padding=(4, 0))
    st.map("Link.TButton", background=[("active", T["bg"])],
           foreground=[("active", T["accent_hi"])])
    st.configure("Treeview", background=T["feld"], fieldbackground=T["feld"],
                 foreground=T["ink"], rowheight=20, bordercolor=T["line"])
    st.configure("Treeview.Heading", background=T["knopf"], foreground=T["ink"], font=f_fett)
    st.map("Treeview", background=[("selected", T["accent"])],
           foreground=[("selected", "white")])
    st.configure("TPanedwindow", background=T["bg"])
    st.configure("Sash", sashthickness=6, gripcount=0, background=T["line"])
    st.configure("TScrollbar", background=T["knopf"], troughcolor=T["bg"],
                 bordercolor=T["line"], arrowcolor=T["ink"])
    st.map("TScrollbar", background=[("active", T["knopf_hi"])])
    st.configure("TSeparator", background=T["line"])
    # Eigene Menüleiste: Die Menüleiste von Windows lässt sich nicht
    # einfärben, deshalb baut das Programm sie selbst aus ttk-Bedienelementen.
    # Die aufgeklappte Liste eines Klappfeldes ist eine Listbox und folgt dem
    # ttk-Thema nicht; ihre Farben kommen aus der Optionsdatenbank.
    for schluessel, wert in (("*TCombobox*Listbox.background", T["feld"]),
                             ("*TCombobox*Listbox.foreground", T["ink"]),
                             ("*TCombobox*Listbox.selectBackground", T["accent"]),
                             ("*TCombobox*Listbox.selectForeground", "white")):
        try:
            win.option_add(schluessel, wert)
        except Exception:
            pass
    st.configure("Menueleiste.TFrame", background=T["panel"])
    try:
        st.layout("Menue.TMenubutton", [
            ("Menubutton.border", {"sticky": "nswe", "children": [
                ("Menubutton.focus", {"sticky": "nswe", "children": [
                    ("Menubutton.padding", {"sticky": "nswe", "children": [
                        ("Menubutton.label", {"sticky": ""})]})]})]})])
    except Exception:
        pass
    st.configure("Menue.TMenubutton", background=T["panel"], foreground=T["ink"],
                 borderwidth=0, relief="flat", padding=(11, 5), font=f_text)
    st.map("Menue.TMenubutton",
           background=[("active", T["knopf_hi"]), ("pressed", T["knopf_ab"])],
           foreground=[("active", T["ink"])])
    return st


# ---------------------------------------------------------------------------
# Teil 6: Ein geöffnetes NC-Programm
# ---------------------------------------------------------------------------

SYNTAX_SCHLUESSEL = tuple(k for k, _n, _g, _b in SYNTAX_KLASSEN)


class Dokument(object):
    """Ein Programm im Editor: Textfeld, Zeilennummern, Einfärbung, Vergleich."""

    def __init__(self, app, eltern, pfad=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.app = app
        self.pfad = pfad
        self.codierung = "utf-8"
        self.bom = False
        self.zeilenende = "\r\n" if sys.platform.startswith("win") else "\n"
        self.gespeichert = True
        self.dialekt = "sinumerik"
        self.original = None
        self.stand = None             # Zustand der Datei, wie wir sie kennen
        self.neu_uebernommen = False  # Original stammt aus einem neuen Lauf
        self.hand = {}
        self.hand_weg = {}
        self.treffer = []             # [(zeile, spalte, länge, text)]
        self.treffer_nr = -1
        self._auftrag = None
        self._diff_auftrag = None
        self._letzte_zeile = 0

        self.rahmen = ttk.Frame(eltern)
        self.nummern = tk.Canvas(self.rahmen, width=54, highlightthickness=0, bd=0)
        self.nummern.pack(side="left", fill="y")
        self.hsb = ttk.Scrollbar(self.rahmen, orient="horizontal")
        self.hsb.pack(side="bottom", fill="x")
        self.vsb = ttk.Scrollbar(self.rahmen, orient="vertical")
        self.vsb.pack(side="right", fill="y")
        self.text = tk.Text(self.rahmen, wrap="none", undo=True, maxundo=-1,
                            autoseparators=True, bd=0, relief="flat",
                            highlightthickness=0, padx=6, pady=2, tabs="2c")
        self.text.pack(side="left", fill="both", expand=True)
        app.dnd_registrieren(self.text)
        app.dnd_registrieren(self.nummern)
        self.vsb.configure(command=self._scroll_y)
        self.hsb.configure(command=self.text.xview)
        self.text.configure(yscrollcommand=self._y_gesetzt, xscrollcommand=self.hsb.set)

        for ereignis in ("<KeyRelease>", "<<Paste>>", "<<Cut>>", "<<Undo>>", "<<Redo>>"):
            self.text.bind(ereignis, self._inhalt_geaendert, add="+")
        for ereignis in ("<Button-1>", "<ButtonRelease-1>", "<KeyRelease>",
                         "<<Selection>>"):
            self.text.bind(ereignis, lambda e: self.app.status_aktualisieren(), add="+")
        self.text.bind("<Configure>", lambda e: self.anzeige_auffrischen(), add="+")
        self.text.bind("<MouseWheel>", self._rad)
        self.text.bind("<Button-4>", self._rad)
        self.text.bind("<Button-5>", self._rad)
        self.nummern.bind("<MouseWheel>", self._rad)
        self.nummern.bind("<Button-4>", self._rad)
        self.nummern.bind("<Button-5>", self._rad)
        self.nummern.bind("<Button-1>", self._nummer_geklickt)

    # -- Grunddaten ---------------------------------------------------------

    def name(self):
        return os.path.basename(self.pfad) if self.pfad else "Neues Programm"

    def titel(self):
        return ("* " if not self.gespeichert else "") + self.name()

    def zeilen_anzahl(self):
        return int(self.text.index("end-1c").split(".")[0])

    def inhalt(self):
        return self.text.get("1.0", "end-1c")

    def zeilen(self):
        return self.inhalt().split("\n")

    # -- Laden und Speichern ------------------------------------------------

    def laden(self, pfad):
        with open(pfad, "rb") as fh:
            roh = fh.read()
        self.bom = roh.startswith(b"\xef\xbb\xbf")
        inhalt = None
        for codierung in ("utf-8-sig", "utf-8"):
            try:
                inhalt = roh.decode(codierung)
                self.codierung = "utf-8"
                break
            except UnicodeDecodeError:
                continue
        if inhalt is None:                      # Werkstattdateien sind oft ANSI
            inhalt = roh.decode("cp1252", "replace")
            self.codierung = "cp1252"
        if b"\r\n" in roh:
            self.zeilenende = "\r\n"
        elif b"\r" in roh:
            self.zeilenende = "\r"
        else:
            self.zeilenende = "\n"
        inhalt = inhalt.replace("\r\n", "\n").replace("\r", "\n")

        self.pfad = pfad
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", inhalt)
        self.text.mark_set("insert", "1.0")
        self.text.edit_reset()
        self.text.edit_modified(False)
        self.gespeichert = True
        self.dialekt_festlegen()
        self.original_pruefen()
        self.anzeige_auffrischen()
        return True

    def speichern(self, pfad=None):
        import tempfile
        ziel = pfad or self.pfad
        if not ziel:
            return False
        vorheriger_pfad = self.pfad
        inhalt = self.inhalt()
        daten = inhalt.replace("\n", self.zeilenende)
        roh = daten.encode(self.codierung, "replace")
        if self.bom and self.codierung == "utf-8":
            roh = b"\xef\xbb\xbf" + roh
        ordner = os.path.dirname(os.path.abspath(ziel)) or "."
        if self.app.einst.get("sicherungskopie", True) and os.path.isfile(ziel):
            try:
                import shutil
                shutil.copy2(ziel, ziel + ".bak")
            except Exception:
                pass
        griff, zwischen = tempfile.mkstemp(dir=ordner, prefix=".nce", suffix=".tmp")
        try:
            with os.fdopen(griff, "wb") as fh:
                fh.write(roh)
            os.replace(zwischen, ziel)          # ersetzt die Datei in einem Schritt
        except Exception:
            try:
                os.remove(zwischen)
            except OSError:
                pass
            raise
        self.pfad = ziel
        self.gespeichert = True
        self.text.edit_modified(False)
        if self.app.einst.get("hand_erkennen", True):
            # Speichern unter einem anderen Namen heißt: das hier ist der neue
            # Ausgangsstand. Der geschriebene Inhalt wird das Original der neuen
            # Datei, die Hand-Markierungen fangen dort von vorn an. Beim
            # Speichern unter demselben Namen bleibt das Original bestehen,
            # damit die Markierungen erhalten bleiben.
            unter_neuem_namen = (
                vorheriger_pfad is None
                or os.path.normcase(os.path.abspath(vorheriger_pfad))
                != os.path.normcase(os.path.abspath(ziel)))
            if unter_neuem_namen or original_laden(ziel) is None:
                original_setzen(ziel, self.zeilen())
                self.original = self.zeilen()
            else:
                # Eigenes Speichern darf später nicht als fremder Lauf gelten
                original_stand_merken(ziel)
        self.stand = datei_stand(ziel)
        self.diff_aktualisieren(sofort=True)
        return True

    # -- Dialekt und Original ----------------------------------------------

    def dialekt_festlegen(self, erzwungen=None):
        wahl = erzwungen or self.app.einst.get("dialekt", "auto")
        if wahl == "auto":
            self.dialekt = dialekt_erkennen(self.zeilen()[:400], self.pfad or "")
        else:
            self.dialekt = wahl

    def original_pruefen(self):
        """Legt beim ersten Öffnen das Original an, sonst wird verglichen.

        Hat ein anderes Programm die Datei seit dem letzten Mal neu
        geschrieben - typisch der Postprozessor von SolidCAM -, dann ist das
        ein neuer Ausgangsstand und keine Hand-Änderung. Er wird übernommen,
        sofern die Einstellung das zulässt.
        """
        self.stand = datei_stand(self.pfad) if self.pfad else None
        self.neu_uebernommen = False
        if not self.pfad or not self.app.einst.get("hand_erkennen", True):
            self.original = None
            self.hand, self.hand_weg = {}, {}
            return
        angaben = original_info(self.pfad) or {}
        self.original = original_laden(self.pfad)
        if self.original is None:
            original_setzen(self.pfad, self.zeilen())
            self.original = self.zeilen()
        else:
            frueher = {"groesse": angaben.get("groesse"), "mtime": angaben.get("mtime")}
            if frueher["mtime"] is None:
                # Ablage aus einer älteren Fassung: Zustand jetzt nachtragen
                original_stand_merken(self.pfad)
            elif (self.app.einst.get("original_bei_neuausgabe", True)
                    and not stand_gleich(frueher, self.stand)):
                original_setzen(self.pfad, self.zeilen())
                self.original = self.zeilen()
                self.neu_uebernommen = True
        self.diff_aktualisieren(sofort=True)

    def neu_laden(self):
        """Liest die Datei erneut von der Platte und hält die Stelle."""
        if not self.pfad or not os.path.isfile(self.pfad):
            return False
        zeile = int(self.text.index("insert").split(".")[0])
        oben = self.text.index("@0,0")
        self.laden(self.pfad)
        try:
            self.text.mark_set("insert", "%d.0" % min(zeile, self.zeilen_anzahl()))
            self.text.see(oben)
            self.text.see("insert")
        except Exception:
            pass
        self.anzeige_auffrischen(verzoegert=False)
        return True

    def original_neu_setzen(self):
        if not self.pfad:
            return False
        original_setzen(self.pfad, self.zeilen())
        self.original = self.zeilen()
        self.diff_aktualisieren(sofort=True)
        return True

    def original_aus_datei(self, pfad):
        try:
            with open(pfad, "rb") as fh:
                roh = fh.read()
        except OSError:
            return False
        try:
            inhalt = roh.decode("utf-8-sig")
        except UnicodeDecodeError:
            inhalt = roh.decode("cp1252", "replace")
        zeilen = inhalt.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if self.pfad:
            original_setzen(self.pfad, zeilen)
        self.original = zeilen
        self.diff_aktualisieren(sofort=True)
        return True

    def diff_aktualisieren(self, sofort=False):
        if self._diff_auftrag is not None:
            try:
                self.text.after_cancel(self._diff_auftrag)
            except Exception:
                pass
            self._diff_auftrag = None
        if not sofort:
            self._diff_auftrag = self.text.after(600, lambda: self.diff_aktualisieren(True))
            return
        if self.original is None or not self.app.einst.get("hand_erkennen", True):
            self.hand, self.hand_weg = {}, {}
        else:
            self.hand, self.hand_weg = hand_aenderungen(self.original, self.zeilen())
        self.anzeige_auffrischen()
        self.app.status_aktualisieren()

    def hand_anzahl(self):
        return len(self.hand)

    # -- Anzeige ------------------------------------------------------------

    def tags_einrichten(self):
        """Setzt Schriftfarben und -schnitte aller Klassen neu."""
        t = self.text
        einst = self.app.einst
        design = einst.get("design", "hell")
        farben = einst["farben"][design]
        name, groesse = editor_schrift(einst)
        import tkinter.font as tkfont
        try:
            breite = tkfont.Font(font=(name, groesse)).measure("0")
        except Exception:
            breite = 8
        tab = max(8, breite * max(1, int(einst.get("tabbreite", 4) or 4)))
        t.configure(bg=farbe_von(farben, "editor_bg", design),
                    fg=farbe_von(farben, "editor_fg", design),
                    insertbackground=farbe_von(farben, "cursor", design),
                    selectbackground=farbe_von(farben, "editor_sel", design),
                    selectforeground=farbe_von(farben, "editor_fg", design),
                    font=(name, groesse), tabs=(tab,))
        for klasse in SYNTAX_SCHLUESSEL:
            farbe, fett, kursiv = stil_von(farben, klasse, design)
            schnitt = [name, groesse]
            if fett:
                schnitt.append("bold")
            if kursiv:
                schnitt.append("italic")
            t.tag_configure(klasse, foreground=farbe,
                            font=tuple(schnitt) if len(schnitt) > 2 else (name, groesse))
        staerke = einst.get("hand_staerke", "normal")
        hand_bg = farbe_von(farben, "hand_bg", design)
        if staerke == "stark":
            t.tag_configure("hand", background=hand_bg, font=(name, groesse, "bold"))
        else:
            t.tag_configure("hand", background="" if staerke == "dezent" else hand_bg,
                            font="")
        t.tag_configure("aktzeile", background=farbe_von(farben, "zeile_bg", design))
        t.tag_configure("treffer", background=farbe_von(farben, "treffer_bg", design))
        t.tag_configure("treffer_akt", background=farbe_von(farben, "treffer_akt", design))
        # Reihenfolge von unten nach oben: aktive Zeile, Syntaxfarben,
        # Hand-Änderung, Suchtreffer, Auswahl
        for klasse in ("aktzeile",) + SYNTAX_SCHLUESSEL + ("hand", "treffer",
                                                           "treffer_akt"):
            t.tag_raise(klasse)
        t.tag_raise("sel")
        self.nummern.configure(bg=farbe_von(farben, "gutter_bg", design))
        self.anzeige_auffrischen()

    def _sichtbarer_bereich(self):
        t = self.text
        try:
            erste = int(t.index("@0,0").split(".")[0])
            hoehe = max(t.winfo_height(), 1)
            letzte = int(t.index("@0,%d" % hoehe).split(".")[0])
        except Exception:
            return 1, 1
        return erste, letzte

    def anzeige_auffrischen(self, verzoegert=True):
        """Färbt den sichtbaren Bereich ein und zeichnet die Zeilennummern."""
        if self._auftrag is not None:
            try:
                self.text.after_cancel(self._auftrag)
            except Exception:
                pass
            self._auftrag = None
        if verzoegert:
            self._auftrag = self.text.after_idle(self._auffrischen_jetzt)
        else:
            self._auffrischen_jetzt()

    def _auffrischen_jetzt(self):
        self._auftrag = None
        self._einfaerben()
        self._nummern_zeichnen()

    def _einfaerben(self):
        t = self.text
        erste, letzte = self._sichtbarer_bereich()
        von = max(1, erste - 40)
        bis = min(self.zeilen_anzahl(), letzte + 40)
        anfang, ende = "%d.0" % von, "%d.end" % bis
        for klasse in SYNTAX_SCHLUESSEL:
            t.tag_remove(klasse, anfang, ende)
        t.tag_remove("hand", anfang, ende)
        staerke = self.app.einst.get("hand_staerke", "normal")
        for nr in range(von, bis + 1):
            zeile = t.get("%d.0" % nr, "%d.end" % nr)
            if zeile:
                for a, b, klasse in zerlege(zeile, self.dialekt):
                    t.tag_add(klasse, "%d.%d" % (nr, a), "%d.%d" % (nr, b))
            if nr in self.hand and staerke != "dezent":
                t.tag_add("hand", "%d.0" % nr, "%d.0 lineend+1c" % nr)
        self._aktive_zeile()

    def _aktive_zeile(self):
        t = self.text
        t.tag_remove("aktzeile", "1.0", "end")
        if self.app.einst.get("aktive_zeile", True):
            nr = int(t.index("insert").split(".")[0])
            t.tag_add("aktzeile", "%d.0" % nr, "%d.0 lineend+1c" % nr)

    def _nummern_zeichnen(self):
        cv = self.nummern
        cv.delete("all")
        if not self.app.einst.get("zeilennummern", True):
            cv.configure(width=10)
            return
        einst = self.app.einst
        design = einst.get("design", "hell")
        farben = einst["farben"][design]
        name, groesse = editor_schrift(einst)
        stellen = max(3, len(str(max(1, self.zeilen_anzahl()))))
        breite = 16 + stellen * max(7, int(groesse * 0.62))
        if int(cv["width"]) != breite:
            cv.configure(width=breite)
        fg = farbe_von(farben, "gutter_fg", design)
        linie = farbe_von(farben, "gutter_linie", design)
        bal_g = farbe_von(farben, "hand_balken", design)
        bal_n = farbe_von(farben, "hand_neu", design)
        bal_w = farbe_von(farben, "hand_weg", design)
        cv.create_line(breite - 1, 0, breite - 1, cv.winfo_height(), fill=linie)
        stelle = self.text.index("@0,0")
        aktuell = int(self.text.index("insert").split(".")[0])
        while True:
            masse = self.text.dlineinfo(stelle)
            if masse is None:
                break
            y = masse[1]
            nr = int(str(stelle).split(".")[0])
            art = self.hand.get(nr)
            if art:
                cv.create_rectangle(breite - 6, y, breite - 2, y + masse[3],
                                    fill=bal_n if art == "n" else bal_g, outline="")
            if nr in self.hand_weg:
                cv.create_polygon(breite - 9, y, breite - 1, y, breite - 5, y + 5,
                                  fill=bal_w, outline="")
            cv.create_text(breite - 9, y, anchor="ne", text=str(nr),
                           font=(name, groesse, "bold") if nr == aktuell else (name, groesse),
                           fill=farbe_von(farben, "editor_fg", design) if nr == aktuell else fg)
            naechste = self.text.index("%s+1line" % stelle)
            if naechste == stelle:
                break
            stelle = naechste

    # -- Ereignisse ---------------------------------------------------------

    def _scroll_y(self, *args):
        self.text.yview(*args)
        self.anzeige_auffrischen()

    def _y_gesetzt(self, anfang, ende):
        self.vsb.set(anfang, ende)
        self.anzeige_auffrischen()

    def _rad(self, ereignis):
        if ereignis.num == 4:
            self.text.yview_scroll(-3, "units")
        elif ereignis.num == 5:
            self.text.yview_scroll(3, "units")
        else:
            self.text.yview_scroll(int(-1 * (ereignis.delta / 40)), "units")
        self.anzeige_auffrischen()
        return "break"

    def _nummer_geklickt(self, ereignis):
        stelle = self.text.index("@0,%d" % ereignis.y)
        self.text.mark_set("insert", stelle)
        self.text.tag_remove("sel", "1.0", "end")
        self.text.tag_add("sel", "%s linestart" % stelle, "%s lineend+1c" % stelle)
        self.text.focus_set()
        self.anzeige_auffrischen()
        self.app.status_aktualisieren()

    def _inhalt_geaendert(self, _ereignis=None):
        if self.text.edit_modified():
            if self.gespeichert:
                self.gespeichert = False
                self.app.reiter_auffrischen()
            self.text.edit_modified(False)
        self.anzeige_auffrischen()
        self.diff_aktualisieren()

    def auftraege_abraeumen(self):
        """Bricht offene Zeitaufträge dieses Programms ab."""
        for name in ("_auftrag", "_diff_auftrag"):
            kennung = getattr(self, name, None)
            if kennung is not None:
                try:
                    self.text.after_cancel(kennung)
                except Exception:
                    pass
                setattr(self, name, None)

    # -- Springen -----------------------------------------------------------

    def springe(self, zeile, spalte=0, laenge=0):
        stelle = "%d.%d" % (zeile, spalte)
        self.text.mark_set("insert", stelle)
        self.text.see("%d.0" % max(1, zeile - 3))
        self.text.see(stelle)
        if laenge:
            self.text.tag_remove("treffer_akt", "1.0", "end")
            self.text.tag_add("treffer_akt", stelle, "%d.%d" % (zeile, spalte + laenge))
        self.text.focus_set()
        self.anzeige_auffrischen()
        self.app.status_aktualisieren()


# ---------------------------------------------------------------------------
# Teil 7: Reiterleiste für die geöffneten Programme
# ---------------------------------------------------------------------------

def reiter_beschriftung(dok, alle):
    """Reitertext. Heißen mehrere Programme gleich, kommt der Ordner dazu.

    In der Werkstatt heißen die Programme oft nur "1" oder "2" - beschrieben
    ist der Ordner. Ohne Zusatz wären die Reiter nicht auseinanderzuhalten.
    """
    name = dok.name()
    gleiche = [d for d in alle if d.name() == name]
    if len(gleiche) < 2 or not dok.pfad:
        return name

    def ordnerteile(pfad):
        return [t for t in os.path.normpath(os.path.dirname(pfad or "")).split(os.sep) if t]

    eigene = ordnerteile(dok.pfad)
    for tiefe in range(1, min(max(len(eigene), 1), 3) + 1):
        zusatz = os.sep.join(eigene[-tiefe:])
        andere = [os.sep.join(ordnerteile(d.pfad)[-tiefe:])
                  for d in gleiche if d is not dok]
        if zusatz and zusatz not in andere:
            if len(zusatz) > 26:
                zusatz = "..." + zusatz[-23:]
            return "%s \u2013 %s" % (name, zusatz)
    return "%s \u2013 %s" % (name, os.path.dirname(dok.pfad))


class Kurzhinweis(object):
    """Kleines Hinweisfenster, das beim Verweilen auf einem Reiter erscheint."""

    def __init__(self, tk, widget, text, design):
        self.tk = tk
        self.widget = widget
        self.text = text
        self.design = design
        self.fenster = None
        self.auftrag = None
        widget.bind("<Enter>", self._warten, add="+")
        widget.bind("<Leave>", self._weg, add="+")
        widget.bind("<Button-1>", self._weg, add="+")

    def _warten(self, _e=None):
        self._abbrechen()
        self.auftrag = self.widget.after(700, self._zeigen)

    def _abbrechen(self):
        if self.auftrag is not None:
            try:
                self.widget.after_cancel(self.auftrag)
            except Exception:
                pass
            self.auftrag = None

    def _zeigen(self):
        if self.fenster is not None:
            return
        T = THEMEN[self.design]
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
            self.fenster = self.tk.Toplevel(self.widget)
            self.fenster.wm_overrideredirect(True)
            self.fenster.wm_geometry("+%d+%d" % (x, y))
            self.tk.Label(self.fenster, text=self.text, justify="left",
                          bg=T["panel"], fg=T["ink"], relief="solid", borderwidth=1,
                          font=ui_schriften()[0], padx=8, pady=4).pack()
        except Exception:
            self.fenster = None

    def _weg(self, _e=None):
        self._abbrechen()
        if self.fenster is not None:
            try:
                self.fenster.destroy()
            except Exception:
                pass
            self.fenster = None


class Reiterleiste(object):
    """Waagerechte Reiter wie in Notepad++: anklicken, schließen, verschieben."""

    def __init__(self, app, eltern):
        import tkinter as tk

        self.tk = tk
        self.app = app
        self.hoehe = 30
        self.flaeche = tk.Canvas(eltern, height=self.hoehe, highlightthickness=0, bd=0)
        self.innen = tk.Frame(self.flaeche, bd=0)
        self.fenster = self.flaeche.create_window(0, 0, window=self.innen, anchor="nw")
        self.reiter = []
        app.dnd_registrieren(self.flaeche)
        self.innen.bind("<Configure>", self._groesse)
        self.flaeche.bind("<MouseWheel>", self._rad)
        self.flaeche.bind("<Button-4>", self._rad)
        self.flaeche.bind("<Button-5>", self._rad)

    def _groesse(self, _e=None):
        self.flaeche.configure(scrollregion=self.flaeche.bbox("all"))

    def _rad(self, ereignis):
        schritt = -1 if getattr(ereignis, "num", 0) == 4 or getattr(ereignis, "delta", 0) > 0 else 1
        self.flaeche.xview_scroll(schritt * 2, "units")
        return "break"

    def pack(self, **kw):
        self.flaeche.pack(**kw)

    def pack_forget(self):
        self.flaeche.pack_forget()

    def aufbauen(self):
        """Zeichnet die Reiter neu - nach Öffnen, Schließen oder Umbenennen."""
        tk = self.tk
        T = THEMEN[self.app.einst.get("design", "hell")]
        f_text, f_fett, _t, _m = ui_schriften()
        for kind in list(self.innen.winfo_children()):
            kind.destroy()
        self.reiter = []
        self.flaeche.configure(bg=T["bg"])
        self.innen.configure(bg=T["bg"])
        for dok in self.app.dokumente:
            aktiv = dok is self.app.aktiv
            hg = T["reiter_aktiv"] if aktiv else T["reiter"]
            vg = T["ink"] if aktiv else T["muted"]
            rahmen = tk.Frame(self.innen, bg=hg, bd=0, highlightthickness=0)
            rahmen.pack(side="left", padx=(0, 1), pady=(2, 0), fill="y")
            # Kennstreifen oben: blau beim aktiven, orange bei ungespeichertem
            streifen = tk.Frame(rahmen, bg=(T["accent"] if aktiv else hg), height=3)
            streifen.pack(fill="x")
            inhalt = tk.Frame(rahmen, bg=hg)
            inhalt.pack(fill="both", expand=True, padx=(10, 6))
            beschriftung = tk.Label(inhalt,
                                    text=reiter_beschriftung(dok, self.app.dokumente),
                                    bg=hg, fg=vg,
                                    font=f_fett if aktiv else f_text, padx=0)
            beschriftung.pack(side="left", pady=(1, 3))
            punkt = tk.Label(inhalt, text="●" if not dok.gespeichert else "",
                             bg=hg, fg="#E8590C", font=f_text, padx=4)
            punkt.pack(side="left", pady=(1, 3))
            zu = tk.Label(inhalt, text="×", bg=hg, fg=T["muted"],
                          font=(f_text[0], f_text[1] + 2), padx=3, cursor="hand2")
            zu.pack(side="left", pady=(1, 3))

            def waehlen(_e, d=dok):
                self.app.dokument_waehlen(d)
                return "break"

            def schliessen(_e, d=dok):
                self.app.dokument_schliessen(d)
                return "break"

            def hervor(_e, w=zu, t=T):
                w.configure(fg="#C62828")

            def normal(_e, w=zu, t=T):
                w.configure(fg=t["muted"])

            for widget in (rahmen, inhalt, beschriftung, punkt, streifen):
                widget.bind("<Button-1>", waehlen)
                widget.bind("<Button-2>", schliessen)
                widget.bind("<Button-3>", lambda e, d=dok: self.app.reiter_menue(e, d))
            zu.bind("<Button-1>", schliessen)
            zu.bind("<Enter>", hervor)
            zu.bind("<Leave>", normal)
            if dok.pfad:
                hinweis = "%s\n%s" % (dok.name(), dok.pfad)
                for widget in (rahmen, inhalt, beschriftung):
                    Kurzhinweis(tk, widget, hinweis,
                                self.app.einst.get("design", "hell"))
            self.reiter.append((dok, rahmen))
        self.innen.update_idletasks()
        self._groesse()
        self.sichtbar_machen(self.app.aktiv)

    def sichtbar_machen(self, dok):
        """Schiebt den aktiven Reiter in den sichtbaren Bereich."""
        for d, rahmen in self.reiter:
            if d is not dok:
                continue
            self.flaeche.update_idletasks()
            gesamt = max(1, self.innen.winfo_reqwidth())
            sicht = max(1, self.flaeche.winfo_width())
            if gesamt <= sicht:
                self.flaeche.xview_moveto(0)
                return
            links = rahmen.winfo_x()
            rechts = links + rahmen.winfo_width()
            jetzt = self.flaeche.canvasx(0)
            if links < jetzt:
                self.flaeche.xview_moveto(links / float(gesamt))
            elif rechts > jetzt + sicht:
                self.flaeche.xview_moveto(max(0.0, (rechts - sicht) / float(gesamt)))
            return


# ---------------------------------------------------------------------------
# Teil 8: Hauptfenster
# ---------------------------------------------------------------------------

class App(object):
    """Das Programmfenster mit Reitern, Suche, Gliederung und Trefferliste."""

    def __init__(self, dateien=(), instanz=None):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.instanz = instanz
        self.einst = einstellungen_laden()
        self.dokumente = []
        self.aktiv = None
        self.such_auftrag = None
        self._auftraege = []

        # tkinterdnd2 erlaubt das Hineinziehen von Dateien aus dem Explorer.
        # Fehlt es, läuft alles andere unverändert weiter.
        self.dnd_bereit = False
        try:
            from tkinterdnd2 import TkinterDnD

            self.win = TkinterDnD.Tk()
            self.dnd_bereit = True
        except Exception:
            self.win = tk.Tk()
        self.win.title(APP_NAME)
        self.win.geometry(self.einst.get("fenster") or "1180x780")
        self.win.minsize(1000, 540)
        design = self.einst.get("design", "hell")
        thema_anwenden(self.win, ttk, design)

        titelleiste_faerben(self.win, design)
        self.logo = logo_laden(tk, self.win, 44)
        self.symbol = logo_laden(tk, self.win, 32, symbol=True)
        if self.symbol is not None:
            try:
                self.win.iconphoto(True, self.symbol)
            except Exception:
                pass

        self.v_suche = tk.StringVar()
        self.v_ersetzen = tk.StringVar()
        self.v_gross = tk.BooleanVar(value=self.einst.get("suche_grossklein", False))
        self.v_wort = tk.BooleanVar(value=self.einst.get("suche_ganzes_wort", False))
        self.v_regex = tk.BooleanVar(value=self.einst.get("suche_regex", False))
        self.v_treffer = tk.StringVar(value="")
        self.v_dialekt = tk.StringVar(value=dict(DIALEKT_NAMEN)[self.einst.get("dialekt", "auto")])
        self.v_design = tk.StringVar(value="Dunkel" if design == "dunkel" else "Hell")
        self.v_pos = tk.StringVar(value="")
        self.v_satz = tk.StringVar(value="")
        self.v_info = tk.StringVar(value="")
        self.v_hand = tk.StringVar(value="")
        self.v_hinweis = tk.StringVar(value="")

        self._menue_bauen()
        self._suchleiste_bauen()
        self._hinweis_bauen()
        self.reiterleiste = Reiterleiste(self, self.win)
        self._mitte_bauen()
        self._fuss_bauen()
        self._tasten_binden()

        self.win.protocol("WM_DELETE_WINDOW", self.beenden)
        self.win.report_callback_exception = self._fehler_melden
        self.dnd_registrieren(self.win)
        self.ansicht_anwenden()
        geladen = False
        for pfad in dateien:
            if self.datei_oeffnen(pfad):
                geladen = True
        if not geladen:
            self.neues_dokument()
        self._planen(120, self.status_aktualisieren)
        self._planen(300, lambda: titelleiste_faerben(
            self.win, self.einst.get("design", "hell")))
        if self.instanz is not None and self.instanz.fuehrend:
            self._planen(400, self._anfragen_pruefen)

    def _fehler_melden(self, art, wert, spur):
        """Fängt Fehler aus Ereignissen ab.

        Ohne das zeigt Tkinter ein Fenster oder das Programm bricht ab. So
        läuft es weiter, und der Fehler steht in fehler.log im
        Einstellungsordner.
        """
        import traceback

        text = "".join(traceback.format_exception(art, wert, spur))
        ausgeben(text, True)
        fehler_protokollieren(text)

    def _planen(self, ms, fn):
        """Zeitauftrag merken, damit er beim Beenden abgeräumt werden kann."""
        kennung = self.win.after(ms, fn)
        self._auftraege.append(kennung)
        if len(self._auftraege) > 50:
            self._auftraege = self._auftraege[-20:]
        return kennung

    def _auftraege_abraeumen(self):
        """Verhindert, dass Zeitaufträge nach dem Schließen ins Leere laufen."""
        for kennung in self._auftraege + [self.such_auftrag]:
            if kennung is None:
                continue
            try:
                self.win.after_cancel(kennung)
            except Exception:
                pass
        self._auftraege = []
        self.such_auftrag = None
        for dok in self.dokumente:
            dok.auftraege_abraeumen()

    # -- Aufbau -------------------------------------------------------------

    def _menue_knopf(self, beschriftung, taste, menue):
        """Hängt ein Menü als Knopf in die eigene Menüleiste."""
        # width=0: natürliche Textbreite. ttk-Menüknöpfe sind sonst auf elf
        # Zeichen voreingestellt und stehen unnötig weit auseinander.
        knopf = self.ttk.Menubutton(self.menueleiste, text=beschriftung, menu=menue,
                                    style="Menue.TMenubutton", direction="below",
                                    width=0)
        knopf.pack(side="left")
        self.win.bind_all("<Alt-%s>" % taste,
                          lambda e, k=knopf: self._menue_aufklappen(k))
        return knopf

    def _menue_aufklappen(self, knopf):
        """Öffnet ein Menü über die Alt-Taste."""
        try:
            menue = knopf.nametowidget(knopf.cget("menu"))
            menue.tk_popup(knopf.winfo_rootx(),
                           knopf.winfo_rooty() + knopf.winfo_height())
        except Exception:
            pass
        finally:
            try:
                knopf.nametowidget(knopf.cget("menu")).grab_release()
            except Exception:
                pass
        return "break"

    def _menue_bauen(self):
        tk = self.tk
        ttk = self.ttk
        T = THEMEN[self.einst.get("design", "hell")]
        eigen = dict(bg=T["panel"], fg=T["ink"], activebackground=T["accent"],
                     activeforeground="white", borderwidth=1,
                     activeborderwidth=1, disabledforeground=T["muted"])
        # Eigene Menüleiste statt der von Windows: Deren Farben gibt das
        # Betriebssystem vor, im dunklen Design bliebe sie weiß.
        if getattr(self, "menueleiste", None) is not None:
            try:
                self.menueleiste.destroy()
            except Exception:
                pass
        self.menueleiste = ttk.Frame(self.win, style="Menueleiste.TFrame")

        m = tk.Menu(self.win, tearoff=0, **eigen)
        m.add_command(label="Neu", accelerator="Strg+N", command=self.neues_dokument)
        m.add_command(label="Öffnen ...", accelerator="Strg+O", command=self.oeffnen_dialog)
        m.add_separator()
        m.add_command(label="Speichern", accelerator="Strg+S", command=self.speichern)
        m.add_command(label="Speichern unter ...", accelerator="Strg+Umschalt+S",
                      command=self.speichern_unter)
        m.add_command(label="Alle speichern", command=self.alle_speichern)
        m.add_separator()
        m.add_command(label="Neu laden", accelerator="F5", command=self.neu_laden_befehl)
        m.add_separator()
        self.menue_zuletzt = tk.Menu(m, tearoff=0, **eigen)
        m.add_cascade(label="Zuletzt geöffnet", menu=self.menue_zuletzt)
        m.add_separator()
        m.add_command(label="Schließen", accelerator="Strg+W", command=self.dokument_schliessen)
        m.add_command(label="Beenden", command=self.beenden)
        self._menue_knopf("Datei", "d", m)

        m = tk.Menu(self.win, tearoff=0, **eigen)
        m.add_command(label="Rückgängig", accelerator="Strg+Z",
                      command=lambda: self._editor_befehl("<<Undo>>"))
        m.add_command(label="Wiederholen", accelerator="Strg+Y",
                      command=lambda: self._editor_befehl("<<Redo>>"))
        m.add_separator()
        m.add_command(label="Ausschneiden", accelerator="Strg+X",
                      command=lambda: self._editor_befehl("<<Cut>>"))
        m.add_command(label="Kopieren", accelerator="Strg+C",
                      command=lambda: self._editor_befehl("<<Copy>>"))
        m.add_command(label="Einfügen", accelerator="Strg+V",
                      command=lambda: self._editor_befehl("<<Paste>>"))
        m.add_separator()
        m.add_command(label="Alles markieren", accelerator="Strg+A",
                      command=self.alles_markieren)
        self._menue_knopf("Bearbeiten", "b", m)

        m = tk.Menu(self.win, tearoff=0, **eigen)
        m.add_command(label="Suchen", accelerator="Strg+F", command=self.suche_fokus)
        m.add_command(label="Weitersuchen", accelerator="F3",
                      command=lambda: self.treffer_springen(1))
        m.add_command(label="Rückwärts suchen", accelerator="Umschalt+F3",
                      command=lambda: self.treffer_springen(-1))
        m.add_command(label="Ersetzen", accelerator="Strg+H", command=self.ersetzen_zeigen)
        m.add_separator()
        m.add_command(label="Gehe zu Zeile ...", accelerator="Strg+G",
                      command=self.gehe_zu_zeile)
        m.add_command(label="Gehe zu Satznummer ...", accelerator="Strg+Umschalt+G",
                      command=self.gehe_zu_satz)
        m.add_separator()
        # Dieselben Schalter wie in der Suchleiste - dort können sie bei
        # schmalem Fenster abgeschnitten sein.
        m.add_checkbutton(label="Gross- und Kleinschreibung beachten",
                          variable=self.v_gross, command=self.suche_ausfuehren)
        m.add_checkbutton(label="Nur ganzes Wort", variable=self.v_wort,
                          command=self.suche_ausfuehren)
        m.add_checkbutton(label="Regulärer Ausdruck", variable=self.v_regex,
                          command=self.suche_ausfuehren)
        self._menue_knopf("Suchen", "s", m)

        m = tk.Menu(self.win, tearoff=0, **eigen)
        self.v_glied = tk.BooleanVar(value=self.einst.get("gliederung_anzeigen", True))
        self.v_trefferliste = tk.BooleanVar(value=self.einst.get("trefferliste_anzeigen", True))
        self.v_nummern = tk.BooleanVar(value=self.einst.get("zeilennummern", True))
        self.v_aktzeile = tk.BooleanVar(value=self.einst.get("aktive_zeile", True))
        m.add_checkbutton(label="Gliederung", variable=self.v_glied, command=self.ansicht_anwenden)
        m.add_checkbutton(label="Trefferliste", variable=self.v_trefferliste,
                          command=self.ansicht_anwenden)
        m.add_checkbutton(label="Zeilennummern", variable=self.v_nummern,
                          command=self.ansicht_anwenden)
        m.add_checkbutton(label="Aktuelle Zeile hervorheben", variable=self.v_aktzeile,
                          command=self.ansicht_anwenden)
        m.add_separator()
        m.add_command(label="Schrift groesser", accelerator="Strg++",
                      command=lambda: self.schrift_aendern(1))
        m.add_command(label="Schrift kleiner", accelerator="Strg+-",
                      command=lambda: self.schrift_aendern(-1))
        self._menue_knopf("Ansicht", "a", m)

        m = tk.Menu(self.win, tearoff=0, **eigen)
        m.add_command(label="Aktuellen Stand als Original übernehmen",
                      command=self.original_uebernehmen)
        m.add_command(label="Original aus Datei wählen ...", command=self.original_waehlen)
        m.add_command(label="Zur nächsten Hand-Änderung", accelerator="F8",
                      command=lambda: self.hand_springen(1))
        m.add_command(label="Zur vorigen Hand-Änderung", accelerator="Umschalt+F8",
                      command=lambda: self.hand_springen(-1))
        m.add_separator()
        m.add_command(label="Original-Info ...", command=self.original_info_zeigen)
        m.add_separator()
        self.v_neuausgabe = tk.BooleanVar(
            value=self.einst.get("original_bei_neuausgabe", True))
        m.add_checkbutton(
            label="Neu ausgegebene Programme als neues Original übernehmen",
            variable=self.v_neuausgabe, command=self._neuausgabe_setzen)
        m.add_separator()
        m.add_command(label="Originale aufräumen ...", command=self.originale_dialog)
        self._menue_knopf("Original", "o", m)

        m = tk.Menu(self.win, tearoff=0, **eigen)
        m.add_command(label="Farben und Schrift ...", command=self.farbdialog)
        m.add_separator()
        m.add_command(label="Als Standardprogramm für .mpf und .nc anmelden",
                      command=self.windows_anmelden)
        m.add_command(label="Anmeldung entfernen", command=self.windows_abmelden)
        m.add_separator()
        self.v_einzeln = tk.BooleanVar(value=self.einst.get("einzelnes_fenster", True))
        m.add_checkbutton(
            label="Dateien im selben Fenster öffnen (ab dem nächsten Start)",
            variable=self.v_einzeln, command=self._einzelnes_fenster_setzen)
        m.add_separator()
        m.add_command(label="Einstellungsordner öffnen", command=self.ordner_oeffnen)
        self._menue_knopf("Extras", "e", m)

        m = tk.Menu(self.win, tearoff=0, **eigen)
        m.add_command(label="Info", command=self.info_zeigen)
        m.add_command(label="Lizenzen", command=self.lizenzen_zeigen)
        self._menue_knopf("Hilfe", "h", m)
        self.zuletzt_auffrischen()

    def _suchleiste_bauen(self):
        ttk = self.ttk
        self.suchleiste = ttk.Frame(self.win, padding=(10, 6, 10, 4))
        # Rechts steht nur, was die Datei betrifft; davor eine Trennlinie, damit
        # "Ersetzen" nicht als "Datei ersetzen" gelesen wird. Der rechte Knopf
        # wird zuerst gepackt und behält so seinen Platz, auch wenn es links
        # eng wird.
        ttk.Button(self.suchleiste, text="Speichern unter ...",
                   style="Werkzeug.TButton",
                   command=self.speichern_unter).pack(side="right")
        ttk.Separator(self.suchleiste, orient="vertical").pack(
            side="right", fill="y", padx=7, pady=2)
        ttk.Label(self.suchleiste, text="Suchen:", style="Section.TLabel").pack(side="left")
        self.suchfeld = ttk.Entry(self.suchleiste, textvariable=self.v_suche, width=21)
        self.suchfeld.pack(side="left", padx=(6, 4))
        self.suchfeld.bind("<Return>", lambda e: self.treffer_springen(1))
        self.suchfeld.bind("<Shift-Return>", lambda e: self.treffer_springen(-1))
        self.suchfeld.bind("<Escape>", lambda e: self._editor_fokus())
        self.v_suche.trace_add("write", lambda *a: self.suche_geplant())
        ttk.Button(self.suchleiste, text="◀", width=3, style="Werkzeug.TButton",
                   command=lambda: self.treffer_springen(-1)).pack(side="left")
        ttk.Button(self.suchleiste, text="▶", width=3, style="Werkzeug.TButton",
                   command=lambda: self.treffer_springen(1)).pack(side="left", padx=(2, 8))
        ttk.Button(self.suchleiste, text="Ersetzen", style="Werkzeug.TButton",
                   command=self.ersetzen_zeigen).pack(side="left", padx=(0, 10))
        ttk.Label(self.suchleiste, textvariable=self.v_treffer,
                  style="Muted.TLabel", width=13).pack(side="left")
        for text, var in (("Groß/klein", self.v_gross), ("Ganzes Wort", self.v_wort),
                          ("Reg. Ausdruck", self.v_regex)):
            ttk.Checkbutton(self.suchleiste, text=text, variable=var,
                            command=self.suche_ausfuehren).pack(side="left", padx=(0, 5))

        self.ersetzleiste = ttk.Frame(self.win, padding=(10, 0, 10, 6))
        ttk.Label(self.ersetzleiste, text="Ersetzen durch:",
                  style="Section.TLabel").pack(side="left")
        feld = ttk.Entry(self.ersetzleiste, textvariable=self.v_ersetzen, width=30)
        feld.pack(side="left", padx=(6, 8))
        feld.bind("<Return>", lambda e: self.ersetzen_einen())
        ttk.Button(self.ersetzleiste, text="Ersetzen", style="Werkzeug.TButton",
                   command=self.ersetzen_einen).pack(side="left", padx=(0, 4))
        ttk.Button(self.ersetzleiste, text="Alle ersetzen", style="Werkzeug.TButton",
                   command=self.ersetzen_alle).pack(side="left")
        ttk.Button(self.ersetzleiste, text="Schließen", style="Link.TButton",
                   command=self.ersetzen_verbergen).pack(side="left", padx=(10, 0))

    def _hinweis_bauen(self):
        tk = self.tk
        ttk = self.ttk
        self.hinweis = tk.Frame(self.win, bg="#FFF3CD", bd=0)
        self.hinweis_text = tk.Label(self.hinweis, textvariable=self.v_hinweis,
                                     bg="#FFF3CD", fg="#6B4E00", anchor="w",
                                     font=ui_schriften()[0])
        self.hinweis_text.pack(side="left", padx=10, pady=5)
        self.hinweis_knopf = ttk.Button(self.hinweis, text="Jetzt als Original übernehmen",
                                        style="Werkzeug.TButton",
                                        command=self.original_uebernehmen)
        self.hinweis_knopf.pack(side="left", padx=6, pady=4)
        tk.Label(self.hinweis, text="×", bg="#FFF3CD", fg="#6B4E00", cursor="hand2",
                 font=(ui_schriften()[0][0], 12)).pack(side="right", padx=10)
        self.hinweis.winfo_children()[-1].bind("<Button-1>", lambda e: self.hinweis_aus())

    def _mitte_bauen(self):
        tk = self.tk
        ttk = self.ttk
        self.mitte = ttk.PanedWindow(self.win, orient="horizontal")

        self.gliederung_rahmen = ttk.Frame(self.mitte, padding=(0, 0, 0, 0))
        ttk.Label(self.gliederung_rahmen, text="  Gliederung",
                  style="Section.TLabel").pack(fill="x", pady=(4, 2))
        self.gliederung = ttk.Treeview(self.gliederung_rahmen, show="tree", selectmode="browse")
        glied_sb = ttk.Scrollbar(self.gliederung_rahmen, orient="vertical",
                                 command=self.gliederung.yview)
        self.gliederung.configure(yscrollcommand=glied_sb.set)
        glied_sb.pack(side="right", fill="y")
        self.gliederung.pack(fill="both", expand=True)
        self.gliederung.bind("<<TreeviewSelect>>", self.gliederung_gewaehlt)
        self.gliederung_ziele = {}

        self.editorbereich = ttk.Frame(self.mitte)

        self.trefferrahmen = ttk.Frame(self.mitte)
        self.v_trefferkopf = tk.StringVar(value="  Treffer")
        ttk.Label(self.trefferrahmen, textvariable=self.v_trefferkopf,
                  style="Section.TLabel").pack(fill="x", pady=(4, 2))
        self.trefferliste = ttk.Treeview(self.trefferrahmen, columns=("zeile", "text"),
                                         show="headings", selectmode="browse")
        self.trefferliste.heading("zeile", text="Zeile")
        self.trefferliste.heading("text", text="Inhalt")
        self.trefferliste.column("zeile", width=62, anchor="e", stretch=False)
        self.trefferliste.column("text", width=240, anchor="w")
        treffer_sb = ttk.Scrollbar(self.trefferrahmen, orient="vertical",
                                   command=self.trefferliste.yview)
        self.trefferliste.configure(yscrollcommand=treffer_sb.set)
        treffer_sb.pack(side="right", fill="y")
        self.trefferliste.pack(fill="both", expand=True)
        self.trefferliste.bind("<<TreeviewSelect>>", self.treffer_gewaehlt)
        self.trefferliste.bind("<Return>", self.treffer_gewaehlt)

    def _fuss_bauen(self):
        ttk = self.ttk
        self.status = ttk.Frame(self.win, padding=(10, 3))
        design_feld = ttk.Combobox(self.status, textvariable=self.v_design, width=8,
                                   state="readonly", values=("Hell", "Dunkel"))
        design_feld.pack(side="right", padx=(4, 0))
        design_feld.bind("<<ComboboxSelected>>", lambda e: self.design_wechseln())
        ttk.Label(self.status, text="Design:", style="Muted.TLabel").pack(side="right", padx=(12, 4))
        dialekt_feld = ttk.Combobox(self.status, textvariable=self.v_dialekt, width=22,
                                    state="readonly", values=[n for _k, n in DIALEKT_NAMEN])
        dialekt_feld.pack(side="right")
        dialekt_feld.bind("<<ComboboxSelected>>", lambda e: self.dialekt_wechseln())
        ttk.Label(self.status, text="Steuerung:", style="Muted.TLabel").pack(side="right", padx=(0, 4))
        for var in (self.v_pos, self.v_satz, self.v_info):
            ttk.Label(self.status, textvariable=var, style="Muted.TLabel").pack(
                side="left", padx=(0, 14))
        self.hand_marke = ttk.Label(self.status, textvariable=self.v_hand, style="Muted.TLabel")
        self.hand_marke.pack(side="left")

        # Schlanke Fussleiste: Herkunft, Lizenz und Gefahrenhinweis stehen im
        # Info-Fenster, nicht dauerhaft über dem Programm.
        self.fuss = ttk.Frame(self.win, padding=(10, 2, 10, 6))
        ttk.Label(self.fuss, style="Warn.TLabel",
                  text="Verwendung auf eigene Gefahr \u2013 Programme vor dem Einsatz "
                       "im Einzelschritt prüfen"
                  ).pack(side="left")
        ttk.Button(self.fuss, text="Info", style="Link.TButton", takefocus=False,
                   command=self.info_zeigen).pack(side="right")
        ttk.Button(self.fuss, text="Lizenzen", style="Link.TButton", takefocus=False,
                   command=self.lizenzen_zeigen).pack(side="right", padx=(0, 10))
        ttk.Label(self.fuss, text="%s %s" % (APP_NAME, VERSION),
                  style="Foot.TLabel").pack(side="right", padx=10)

    def _tasten_binden(self):
        b = self.win.bind_all
        b("<Control-n>", lambda e: self.neues_dokument())
        b("<Control-o>", lambda e: self.oeffnen_dialog())
        b("<Control-s>", lambda e: self.speichern())
        b("<Control-Shift-S>", lambda e: self.speichern_unter())
        b("<Control-w>", lambda e: self.dokument_schliessen())
        b("<Control-f>", lambda e: self.suche_fokus())
        b("<Control-h>", lambda e: self.ersetzen_zeigen())
        b("<Control-g>", lambda e: self.gehe_zu_zeile())
        b("<Control-Shift-G>", lambda e: self.gehe_zu_satz())
        b("<F3>", lambda e: self.treffer_springen(1))
        b("<Shift-F3>", lambda e: self.treffer_springen(-1))
        b("<F5>", lambda e: self.neu_laden_befehl())
        b("<F8>", lambda e: self.hand_springen(1))
        b("<Shift-F8>", lambda e: self.hand_springen(-1))
        b("<Control-Tab>", lambda e: self.reiter_wechseln(1))
        b("<Control-Shift-Tab>", lambda e: self.reiter_wechseln(-1))
        b("<Control-plus>", lambda e: self.schrift_aendern(1))
        b("<Control-minus>", lambda e: self.schrift_aendern(-1))
        b("<Control-KeyPress-0>", lambda e: self.schrift_aendern(0))

    # -- Ansicht ------------------------------------------------------------

    def ansicht_anwenden(self):
        """Blendet die Bereiche gemäß Einstellungen ein und aus."""
        self.einst["gliederung_anzeigen"] = bool(self.v_glied.get())
        self.einst["trefferliste_anzeigen"] = bool(self.v_trefferliste.get())
        self.einst["zeilennummern"] = bool(self.v_nummern.get())
        self.einst["aktive_zeile"] = bool(self.v_aktzeile.get())

        for teil in (self.menueleiste, self.suchleiste, self.ersetzleiste,
                     self.hinweis, self.mitte, self.status, self.fuss):
            teil.pack_forget()
        self.reiterleiste.pack_forget()
        self.fuss.pack(side="bottom", fill="x")
        self.status.pack(side="bottom", fill="x")
        self.menueleiste.pack(side="top", fill="x")
        self.suchleiste.pack(fill="x")
        if getattr(self, "_ersetzen_offen", False):
            self.ersetzleiste.pack(fill="x")
        if self.v_hinweis.get():
            self.hinweis.pack(fill="x", padx=10, pady=(0, 4))
        self.reiterleiste.pack(fill="x", padx=6)
        self.mitte.pack(fill="both", expand=True, padx=6, pady=(2, 2))

        for teil in (self.gliederung_rahmen, self.editorbereich, self.trefferrahmen):
            try:
                self.mitte.forget(teil)
            except Exception:
                pass
        if self.einst["gliederung_anzeigen"]:
            self.mitte.add(self.gliederung_rahmen, weight=0)
        self.mitte.add(self.editorbereich, weight=1)
        if self.einst["trefferliste_anzeigen"]:
            self.mitte.add(self.trefferrahmen, weight=0)
        self._planen(60, self._sash_setzen)
        self._planen(400, self._sash_setzen)
        if self.aktiv:
            self.aktiv.tags_einrichten()

    def _sash_setzen(self):
        """Breite der Seitenspalten setzen - erst möglich, wenn das Fenster steht."""
        try:
            self.win.update_idletasks()
            breite = self.mitte.winfo_width()
            if breite < 400:
                breite = max(int(self.win.winfo_width()) - 20, 900)
            links = self.einst.get("gliederung_anzeigen")
            rechts = self.einst.get("trefferliste_anzeigen")
            if links:
                self.mitte.sashpos(0, 250)
            if rechts:
                self.mitte.sashpos(1 if links else 0, max(400, breite - 330))
        except Exception:
            pass

    def design_wechseln(self):
        self.einst["design"] = "dunkel" if self.v_design.get() == "Dunkel" else "hell"
        thema_anwenden(self.win, self.ttk, self.einst["design"])
        self._menue_bauen()
        titelleiste_faerben(self.win, self.einst["design"])
        for dok in self.dokumente:
            dok.tags_einrichten()
        self.reiterleiste.aufbauen()
        self.ansicht_anwenden()

    def dialekt_wechseln(self):
        name_zu_schluessel = {n: k for k, n in DIALEKT_NAMEN}
        self.einst["dialekt"] = name_zu_schluessel.get(self.v_dialekt.get(), "auto")
        for dok in self.dokumente:
            dok.dialekt_festlegen()
            dok.anzeige_auffrischen()
        self.gliederung_bauen()
        self.status_aktualisieren()

    def schrift_aendern(self, richtung):
        if richtung == 0:
            self.einst["schriftgroesse"] = 11
        else:
            self.einst["schriftgroesse"] = max(6, min(
                32, int(self.einst.get("schriftgroesse", 11)) + richtung))
        for dok in self.dokumente:
            dok.tags_einrichten()

    # -- Dokumente ----------------------------------------------------------

    def neues_dokument(self):
        dok = Dokument(self, self.editorbereich)
        self.dokumente.append(dok)
        dok.tags_einrichten()
        self.dokument_waehlen(dok)
        return dok

    def _anfragen_pruefen(self):
        """Holt Dateien ab, die ein zweites Programm abgelegt hat."""
        try:
            dateien, gab_anfrage = self.instanz.abholen()
            for pfad in dateien:
                self.datei_oeffnen(pfad)
            if gab_anfrage:
                self.nach_vorn()
        except Exception:
            pass
        self._planen(400, self._anfragen_pruefen)

    def nach_vorn(self):
        """Holt das Fenster in den Vordergrund."""
        try:
            self.win.deiconify()
            self.win.lift()
            self.win.attributes("-topmost", True)
            self.win.after(250, lambda: self.win.attributes("-topmost", False))
            self.win.focus_force()
        except Exception:
            pass

    # -- Dateien hineinziehen ----------------------------------------------

    def dnd_registrieren(self, widget):
        """Macht ein Bedienelement zum Ziel für hineingezogene Dateien."""
        if not self.dnd_bereit:
            return
        try:
            from tkinterdnd2 import DND_FILES

            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._dateien_abgelegt)
        except Exception:
            pass

    def _dateien_abgelegt(self, ereignis):
        """Öffnet die Programme, die ins Fenster gezogen wurden."""
        from tkinter import messagebox

        daten = getattr(ereignis, "data", "") or ""
        try:
            pfade = list(self.win.tk.splitlist(daten))
        except Exception:
            pfade = [t.strip("{}") for t in daten.split() if t.strip()]
        fremde = []
        for pfad in pfade:
            pfad = pfad.strip().strip("{}")
            if not pfad or not os.path.isfile(pfad):
                continue
            if os.path.splitext(pfad)[1].lower() in DATEI_ENDUNGEN + (".txt",):
                self.datei_oeffnen(pfad)
            else:
                fremde.append(pfad)
        for pfad in fremde:
            if messagebox.askyesno(
                    APP_NAME,
                    "%s sieht nicht nach einem NC-Programm aus.\n\nTrotzdem "
                    "öffnen?" % os.path.basename(pfad), parent=self.win):
                self.datei_oeffnen(pfad)
        return getattr(ereignis, "action", None)

    def datei_oeffnen(self, pfad):
        from tkinter import messagebox
        pfad = os.path.abspath(pfad)
        for dok in self.dokumente:
            if dok.pfad and os.path.normcase(dok.pfad) == os.path.normcase(pfad):
                self.dokument_waehlen(dok)
                self.aussen_geaendert_pruefen(dok)
                return True
        if not os.path.isfile(pfad):
            messagebox.showerror(APP_NAME, "Datei nicht gefunden:\n%s" % pfad, parent=self.win)
            return False
        dok = Dokument(self, self.editorbereich)
        try:
            dok.laden(pfad)
        except Exception as fehler:
            dok.rahmen.destroy()
            messagebox.showerror(APP_NAME, "Datei lässt sich nicht lesen:\n%s\n\n%s"
                                 % (pfad, fehler), parent=self.win)
            return False
        # leeres, unberührtes Dokument ersetzen
        if (len(self.dokumente) == 1 and self.dokumente[0].pfad is None
                and self.dokumente[0].gespeichert
                and not self.dokumente[0].inhalt().strip()):
            alt = self.dokumente.pop(0)
            alt.rahmen.destroy()
        self.dokumente.append(dok)
        dok.tags_einrichten()
        self.zuletzt_merken(pfad)
        self.einst["letzter_ordner"] = os.path.dirname(pfad)
        self.dokument_waehlen(dok)
        if dok.neu_uebernommen:
            self.hinweis_zeigen(
                "%s wurde seit dem letzten Mal neu ausgegeben. Dieser Stand gilt "
                "jetzt als Original." % dok.name())
        else:
            self.hinweis_pruefen(dok)
        return True

    def aussen_geaendert_pruefen(self, dok=None):
        """Lädt neu, wenn ein anderes Programm die Datei geschrieben hat.

        Ohne das zeigte der Editor beim erneuten Öffnen aus SolidCAM heraus
        weiter den alten Stand - geprüfte und gefahrene Fassung wären
        auseinandergelaufen.
        """
        from tkinter import messagebox

        dok = dok or self.aktiv
        if dok is None or not dok.pfad or not os.path.isfile(dok.pfad):
            return False
        jetzt = datei_stand(dok.pfad)
        if jetzt is None or dok.stand is None or stand_gleich(jetzt, dok.stand):
            return False
        if not dok.gespeichert and not messagebox.askyesno(
                APP_NAME,
                "%s wurde außerhalb des Editors neu geschrieben.\n\nNeu laden?\n"
                "Ihre noch nicht gespeicherten Änderungen gehen dabei verloren."
                % dok.name(), parent=self.win):
            return False
        dok.neu_laden()
        self.reiter_auffrischen()
        self.gliederung_bauen()
        self.suche_ausfuehren()
        self.status_aktualisieren()
        if dok.neu_uebernommen:
            self.hinweis_zeigen("%s wurde neu ausgegeben und ist jetzt aktuell "
                                "im Editor. Dieser Stand gilt als Original."
                                % dok.name())
        else:
            self.hinweis_zeigen("%s wurde außerhalb geändert und neu geladen."
                                % dok.name())
        return True

    def neu_laden_befehl(self):
        """Datei erneut von der Platte lesen (F5)."""
        from tkinter import messagebox

        dok = self.aktiv
        if dok is None or not dok.pfad:
            return "break"
        if not dok.gespeichert and not messagebox.askyesno(
                APP_NAME, "%s hat noch nicht gespeicherte Änderungen.\n\n"
                          "Trotzdem neu laden?" % dok.name(), parent=self.win):
            return "break"
        if dok.neu_laden():
            self.reiter_auffrischen()
            self.gliederung_bauen()
            self.suche_ausfuehren()
            self.status_aktualisieren()
            self.hinweis_zeigen("%s neu geladen." % dok.name(), 5000)
        return "break"

    def oeffnen_dialog(self):
        from tkinter import filedialog
        auswahl = filedialog.askopenfilenames(
            parent=self.win, title="NC-Programme öffnen",
            initialdir=self.einst.get("letzter_ordner") or None,
            filetypes=[("NC-Programme", "*.mpf *.nc *.spf *.tap *.cnc *.ngc *.iso"),
                       ("SINUMERIK Hauptprogramm", "*.mpf"),
                       ("NC-Datei", "*.nc"), ("Alle Dateien", "*.*")])
        for pfad in auswahl or ():
            self.datei_oeffnen(pfad)

    def dokument_waehlen(self, dok):
        if dok is None or dok not in self.dokumente:
            return
        if self.aktiv is not None and self.aktiv is not dok:
            self.aktiv.rahmen.pack_forget()
        self.aktiv = dok
        dok.rahmen.pack(fill="both", expand=True)
        self.reiterleiste.aufbauen()
        self.titel_setzen()
        dok.anzeige_auffrischen()
        self.gliederung_bauen()
        self.suche_ausfuehren()
        self.status_aktualisieren()
        dok.text.focus_set()

    def dokument_schliessen(self, dok=None):
        from tkinter import messagebox
        dok = dok or self.aktiv
        if dok is None:
            return
        if not dok.gespeichert:
            antwort = messagebox.askyesnocancel(
                APP_NAME, "%s wurde geändert.\n\nÄnderungen speichern?" % dok.name(),
                parent=self.win)
            if antwort is None:
                return
            if antwort and not self.speichern(dok):
                return
        stelle = self.dokumente.index(dok)
        self.dokumente.remove(dok)
        dok.auftraege_abraeumen()
        dok.rahmen.destroy()
        if self.aktiv is dok:
            self.aktiv = None
        if self.dokumente:
            self.dokument_waehlen(self.dokumente[min(stelle, len(self.dokumente) - 1)])
        else:
            self.neues_dokument()

    def reiter_wechseln(self, richtung):
        if len(self.dokumente) < 2:
            return "break"
        i = self.dokumente.index(self.aktiv)
        self.dokument_waehlen(self.dokumente[(i + richtung) % len(self.dokumente)])
        return "break"

    def titel_setzen(self):
        """Voller Pfad im Fenstertitel - bei Programmen, die alle "1" heißen,
        ist der Dateiname allein nichtssagend."""
        dok = self.aktiv
        if dok is None:
            self.win.title(APP_NAME)
            return
        marke = "" if dok.gespeichert else "* "
        self.win.title("%s%s - %s" % (marke, dok.pfad or dok.name(), APP_NAME))

    def reiter_auffrischen(self):
        self.reiterleiste.aufbauen()
        self.titel_setzen()

    def reiter_menue(self, ereignis, dok):
        tk = self.tk
        T = THEMEN[self.einst.get("design", "hell")]
        m = tk.Menu(self.win, tearoff=0, bg=T["panel"], fg=T["ink"],
                    activebackground=T["accent"], activeforeground="white")
        m.add_command(label="Schließen", command=lambda: self.dokument_schliessen(dok))
        m.add_command(label="Andere schließen", command=lambda: self.andere_schliessen(dok))
        m.add_separator()
        m.add_command(label="Pfad kopieren", command=lambda: self.pfad_kopieren(dok))
        m.add_command(label="Ordner öffnen", command=lambda: self.ordner_zeigen(dok))
        try:
            m.tk_popup(ereignis.x_root, ereignis.y_root)
        finally:
            m.grab_release()

    def andere_schliessen(self, dok):
        for anderes in list(self.dokumente):
            if anderes is not dok:
                self.dokument_schliessen(anderes)

    def pfad_kopieren(self, dok):
        if dok.pfad:
            self.win.clipboard_clear()
            self.win.clipboard_append(dok.pfad)

    def ordner_zeigen(self, dok):
        if dok.pfad:
            self._ordner_anzeigen(os.path.dirname(dok.pfad))

    def _ordner_anzeigen(self, ordner):
        import subprocess
        try:
            if sys.platform.startswith("win"):
                os.startfile(ordner)                       # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ordner])
            else:
                subprocess.Popen(["xdg-open", ordner])
        except Exception:
            pass

    # -- Speichern ----------------------------------------------------------

    def speichern(self, dok=None):
        from tkinter import messagebox
        dok = dok or self.aktiv
        if dok is None:
            return False
        if not dok.pfad:
            return self.speichern_unter(dok)
        try:
            dok.speichern()
        except Exception as fehler:
            messagebox.showerror(APP_NAME, "Speichern fehlgeschlagen:\n%s" % fehler,
                                 parent=self.win)
            return False
        self.reiter_auffrischen()
        self.status_aktualisieren()
        return True

    def speichern_unter(self, dok=None):
        from tkinter import filedialog, messagebox
        dok = dok or self.aktiv
        if dok is None:
            return False
        # Dateiart der offenen Datei vorwählen. Bei einem noch nicht
        # gespeicherten Programm entscheidet der erkannte Dialekt.
        endung = os.path.splitext(dok.pfad or dok.name())[1].lower()
        if not endung:
            endung = ".mpf" if dok.dialekt == "sinumerik" else (
                ".h" if dok.dialekt == "heidenhain" else ".nc")
        pfad = filedialog.asksaveasfilename(
            parent=self.win, title="Speichern unter",
            initialdir=(os.path.dirname(dok.pfad) if dok.pfad
                        else self.einst.get("letzter_ordner") or None),
            initialfile=dok.name(), defaultextension=endung,
            filetypes=speicher_dateiarten(endung))
        if not pfad:
            return False
        try:
            dok.speichern(pfad)
        except Exception as fehler:
            messagebox.showerror(APP_NAME, "Speichern fehlgeschlagen:\n%s" % fehler,
                                 parent=self.win)
            return False
        self.zuletzt_merken(pfad)
        self.einst["letzter_ordner"] = os.path.dirname(pfad)
        self.reiter_auffrischen()
        self.status_aktualisieren()
        return True

    def alle_speichern(self):
        for dok in list(self.dokumente):
            if not dok.gespeichert:
                self.speichern(dok)

    # -- Zuletzt geöffnet --------------------------------------------------

    def zuletzt_merken(self, pfad):
        liste = [p for p in self.einst.get("zuletzt", [])
                 if os.path.normcase(p) != os.path.normcase(pfad)]
        liste.insert(0, os.path.abspath(pfad))
        self.einst["zuletzt"] = liste[:12]
        self.zuletzt_auffrischen()

    def zuletzt_auffrischen(self):
        m = self.menue_zuletzt
        m.delete(0, "end")
        liste = [p for p in self.einst.get("zuletzt", []) if os.path.isfile(p)]
        if not liste:
            m.add_command(label="(keine)", state="disabled")
            return
        for pfad in liste:
            m.add_command(label=pfad, command=lambda p=pfad: self.datei_oeffnen(p))
        m.add_separator()
        m.add_command(label="Liste leeren", command=self.zuletzt_leeren)

    def zuletzt_leeren(self):
        self.einst["zuletzt"] = []
        self.zuletzt_auffrischen()

    # -- Suche --------------------------------------------------------------

    def suche_fokus(self):
        self.suchfeld.focus_set()
        self.suchfeld.select_range(0, "end")
        return "break"

    def _editor_fokus(self):
        if self.aktiv:
            self.aktiv.text.focus_set()
        return "break"

    def _muster(self):
        begriff = self.v_suche.get()
        if not begriff:
            return None
        teil = begriff if self.v_regex.get() else re.escape(begriff)
        if self.v_wort.get():
            teil = r"(?<!\w)" + teil + r"(?!\w)"
        marken = 0 if self.v_gross.get() else re.IGNORECASE
        try:
            return re.compile(teil, marken)
        except re.error:
            return None

    def suche_geplant(self):
        """Sucht kurz nach der Eingabe - nicht bei jedem Tastendruck sofort."""
        if self.such_auftrag is not None:
            try:
                self.win.after_cancel(self.such_auftrag)
            except Exception:
                pass
        self.such_auftrag = self.win.after(220, self.suche_ausfuehren)

    def suche_ausfuehren(self):
        self.such_auftrag = None
        self.einst["suche_grossklein"] = bool(self.v_gross.get())
        self.einst["suche_ganzes_wort"] = bool(self.v_wort.get())
        self.einst["suche_regex"] = bool(self.v_regex.get())
        dok = self.aktiv
        if dok is None:
            return
        dok.text.tag_remove("treffer", "1.0", "end")
        dok.text.tag_remove("treffer_akt", "1.0", "end")
        dok.treffer = []
        dok.treffer_nr = -1
        muster = self._muster()
        begriff = self.v_suche.get()
        if muster is None:
            self.v_treffer.set("ungültiger Ausdruck" if begriff else "")
            self.trefferliste_fuellen()
            return
        treffer = []
        for nr, zeile in enumerate(dok.zeilen(), 1):
            for m in muster.finditer(zeile):
                if m.end() == m.start():
                    continue
                treffer.append((nr, m.start(), m.end() - m.start(), zeile))
                if len(treffer) >= 20000:
                    break
            if len(treffer) >= 20000:
                break
        dok.treffer = treffer
        for nr, spalte, laenge, _z in treffer:
            dok.text.tag_add("treffer", "%d.%d" % (nr, spalte),
                             "%d.%d" % (nr, spalte + laenge))
        zeilen_mit = len({t[0] for t in treffer})
        if not begriff:
            self.v_treffer.set("")
        elif treffer:
            self.v_treffer.set("%d in %d Zeilen" % (len(treffer), zeilen_mit))
        else:
            self.v_treffer.set("kein Treffer")
        self.trefferliste_fuellen()

    def trefferliste_fuellen(self):
        """Füllt die Spalte rechts - eine Zeile je Treffer, anklickbar."""
        liste = self.trefferliste
        liste.delete(*liste.get_children())
        dok = self.aktiv
        begriff = self.v_suche.get()
        if dok is None or not begriff:
            self.v_trefferkopf.set("  Treffer")
            return
        self.v_trefferkopf.set("  Treffer für „%s“: %d"
                               % (begriff[:24], len(dok.treffer)))
        design = self.einst.get("design", "hell")
        liste.tag_configure("hand", background=farbe_von(
            self.einst["farben"][design], "hand_bg", design))
        for i, (nr, _spalte, _laenge, zeile) in enumerate(dok.treffer[:4000]):
            marken = ("hand",) if nr in dok.hand else ()
            liste.insert("", "end", iid=str(i), values=(nr, zeile.strip()[:160]), tags=marken)
        if len(dok.treffer) > 4000:
            liste.insert("", "end", iid="mehr",
                         values=("", "... %d weitere Treffer" % (len(dok.treffer) - 4000)))

    def treffer_gewaehlt(self, _ereignis=None):
        auswahl = self.trefferliste.selection()
        if not auswahl or auswahl[0] == "mehr" or self.aktiv is None:
            return
        try:
            i = int(auswahl[0])
        except ValueError:
            return
        if 0 <= i < len(self.aktiv.treffer):
            self.aktiv.treffer_nr = i
            nr, spalte, laenge, _z = self.aktiv.treffer[i]
            self.aktiv.springe(nr, spalte, laenge)

    def treffer_springen(self, richtung):
        dok = self.aktiv
        if dok is None:
            return "break"
        if not dok.treffer:
            self.suche_ausfuehren()
            if not dok.treffer:
                return "break"
            dok.treffer_nr = -1
        if dok.treffer_nr < 0:
            # beim ersten Sprung am Cursor beginnen
            aktuell = int(dok.text.index("insert").split(".")[0])
            spalte = int(dok.text.index("insert").split(".")[1])
            dok.treffer_nr = -1
            for i, (nr, sp, _l, _z) in enumerate(dok.treffer):
                if (nr, sp) >= (aktuell, spalte):
                    dok.treffer_nr = i - 1 if richtung > 0 else i
                    break
        dok.treffer_nr = (dok.treffer_nr + richtung) % len(dok.treffer)
        nr, spalte, laenge, _z = dok.treffer[dok.treffer_nr]
        dok.springe(nr, spalte, laenge)
        kennung = str(dok.treffer_nr)
        if self.trefferliste.exists(kennung):
            self.trefferliste.selection_set(kennung)
            self.trefferliste.see(kennung)
        self.v_treffer.set("%d von %d" % (dok.treffer_nr + 1, len(dok.treffer)))
        return "break"

    # -- Ersetzen -----------------------------------------------------------

    def ersetzen_zeigen(self):
        self._ersetzen_offen = True
        self.ansicht_anwenden()
        return "break"

    def ersetzen_verbergen(self):
        self._ersetzen_offen = False
        self.ansicht_anwenden()

    def ersetzen_einen(self):
        dok = self.aktiv
        if dok is None or not dok.treffer:
            self.treffer_springen(1)
            return
        if dok.treffer_nr < 0:
            self.treffer_springen(1)
            return
        nr, spalte, laenge, _z = dok.treffer[dok.treffer_nr]
        dok.text.delete("%d.%d" % (nr, spalte), "%d.%d" % (nr, spalte + laenge))
        dok.text.insert("%d.%d" % (nr, spalte), self.v_ersetzen.get())
        dok._inhalt_geaendert()
        self.reiter_auffrischen()
        self.suche_ausfuehren()
        self.treffer_springen(1)

    def ersetzen_alle(self):
        from tkinter import messagebox
        dok = self.aktiv
        muster = self._muster()
        if dok is None or muster is None:
            return
        ersatz = self.v_ersetzen.get()
        alt = dok.zeilen()
        anzahl = 0
        neu = []
        for zeile in alt:
            if self.v_regex.get():
                ersetzt, n = muster.subn(ersatz, zeile)
            else:
                ersetzt, n = muster.subn(lambda m: ersatz, zeile)
            anzahl += n
            neu.append(ersetzt)
        if not anzahl:
            messagebox.showinfo(APP_NAME, "Kein Treffer zum Ersetzen.", parent=self.win)
            return
        if not messagebox.askyesno(
                APP_NAME, "%d Treffer in %s ersetzen?" % (anzahl, dok.name()),
                parent=self.win):
            return
        stelle = dok.text.index("insert")
        dok.text.delete("1.0", "end")
        dok.text.insert("1.0", "\n".join(neu))
        try:
            dok.text.mark_set("insert", stelle)
            dok.text.see(stelle)
        except Exception:
            pass
        dok.gespeichert = False
        dok.text.edit_modified(False)
        dok.anzeige_auffrischen()
        dok.diff_aktualisieren(sofort=True)
        self.reiter_auffrischen()
        self.suche_ausfuehren()
        self.gliederung_bauen()
        messagebox.showinfo(APP_NAME, "%d Treffer ersetzt." % anzahl, parent=self.win)

    # -- Springen -----------------------------------------------------------

    def _eingabe(self, titel, frage, vorgabe=""):
        """Kleines Eingabefenster im Design des Programms.

        tkinter.simpledialog zeichnet mit den Systemfarben und bliebe im
        dunklen Design hell.
        """
        tk = self.tk
        ttk = self.ttk
        T = THEMEN[self.einst.get("design", "hell")]
        fenster = tk.Toplevel(self.win)
        fenster.title(titel)
        fenster.configure(bg=T["bg"])
        fenster.resizable(False, False)
        fenster.transient(self.win)
        rahmen = ttk.Frame(fenster, padding=(16, 14))
        rahmen.pack(fill="both", expand=True)
        ttk.Label(rahmen, text=frage).pack(anchor="w")
        wert = tk.StringVar(value=vorgabe)
        feld = ttk.Entry(rahmen, textvariable=wert, width=28)
        feld.pack(fill="x", pady=(6, 12))
        feld.focus_set()
        feld.select_range(0, "end")
        ergebnis = []

        def nehmen(_e=None):
            ergebnis.append(wert.get().strip())
            fenster.destroy()

        knoepfe = ttk.Frame(rahmen)
        knoepfe.pack(fill="x")
        ttk.Button(knoepfe, text="Abbrechen", command=fenster.destroy).pack(side="right")
        ttk.Button(knoepfe, text="Springen", style="Accent.TButton",
                   command=nehmen).pack(side="right", padx=(0, 8))
        feld.bind("<Return>", nehmen)
        fenster.bind("<Escape>", lambda e: fenster.destroy())
        fenster.update_idletasks()
        fenster.geometry("+%d+%d" % (
            self.win.winfo_rootx() + (self.win.winfo_width() - fenster.winfo_width()) // 2,
            self.win.winfo_rooty() + 160))
        fenster.grab_set()
        self.win.wait_window(fenster)
        return ergebnis[0] if ergebnis else None

    def gehe_zu_zeile(self):
        from tkinter import messagebox

        dok = self.aktiv
        if dok is None:
            return "break"
        eingabe = self._eingabe("Gehe zu Zeile",
                                "Zeile (1 bis %d):" % dok.zeilen_anzahl())
        if not eingabe:
            return "break"
        try:
            nr = int(eingabe)
        except ValueError:
            messagebox.showinfo(APP_NAME, "Bitte eine Zeilennummer eingeben.",
                                parent=self.win)
            return "break"
        dok.springe(max(1, min(nr, dok.zeilen_anzahl())))
        return "break"

    def gehe_zu_satz(self):
        from tkinter import messagebox

        dok = self.aktiv
        if dok is None:
            return "break"
        eingabe = self._eingabe("Gehe zu Satznummer",
                                "Satznummer (z. B. 1240 oder N1240):")
        if not eingabe:
            return "break"
        gesucht = eingabe.strip().upper().lstrip("N")
        muster = re.compile(r"^\s*N0*%s\b" % re.escape(gesucht), re.IGNORECASE)
        for nr, zeile in enumerate(dok.zeilen(), 1):
            if muster.match(zeile):
                dok.springe(nr)
                return "break"
        messagebox.showinfo(APP_NAME, "Satznummer %s nicht gefunden." % eingabe,
                            parent=self.win)
        return "break"

    def hand_springen(self, richtung):
        dok = self.aktiv
        if dok is None or not dok.hand:
            return "break"
        aktuell = int(dok.text.index("insert").split(".")[0])
        nummern = sorted(dok.hand)
        ziel = None
        if richtung > 0:
            for nr in nummern:
                if nr > aktuell:
                    ziel = nr
                    break
            ziel = ziel if ziel else nummern[0]
        else:
            for nr in reversed(nummern):
                if nr < aktuell:
                    ziel = nr
                    break
            ziel = ziel if ziel else nummern[-1]
        dok.springe(ziel)
        return "break"

    # -- Gliederung ---------------------------------------------------------

    # Zyklen, die nur die Bearbeitung vorbereiten - nicht als Job auflisten
    _RUEST_ZYKLEN = ("CYCLE800", "CYCLE832", "CYCLE996", "CYCLE998", "CYCLE900")
    # Bearbeitungszyklen: SINUMERIK-Namen, Heidenhain CYCL DEF und die
    # ISO-Bohrzyklen G73...G89 (G80 ist nur das Abwählen und fällt weg).
    _BEARBEITUNG_RE = re.compile(
        r"\b(CYCLE\d+|POCKET\d+|SLOT\d+|HOLES\d+|LONGHOLE|CYCL\s+DEF\s+\d+"
        r"|G7[3469]|G8[1-9])\b", re.I)
    # Werkzeugaufruf: T="NAME" (SINUMERIK) oder T24 an beliebiger Stelle (ISO,
    # dort steht häufig "M06 T24").
    _WERKZEUG_RE = re.compile(r'\bT\s*=\s*"([^"]+)"|\bT\s*(\d+)\b', re.I)
    _WZ_KOMMENTAR_RE = re.compile(r"\(([^)]*)\)|;\s*(.+)$")
    _GRUPPE_RE = re.compile(r'GROUP_BEGIN\s*\(\s*\d*\s*,\s*"([^"]*)"', re.I)
    _MSG_RE = re.compile(r'MSG\s*\(\s*"([^"]*)"', re.I)

    def gliederung_bauen(self):
        """Jobs, Werkzeugwechsel und Hand-Änderungen als anklickbarer Baum."""
        baum = self.gliederung
        baum.delete(*baum.get_children())
        self.gliederung_ziele = {}
        dok = self.aktiv
        if dok is None or not self.einst.get("gliederung_anzeigen", True):
            return
        zeilen = dok.zeilen()
        nutzbar = [("" if z.lstrip().startswith(";") else z) for z in zeilen]

        # Echte Werkzeugwechsel sind T-Aufrufe, denen kurz darauf M6 folgt.
        wechsel = set()
        for i, zeile in enumerate(nutzbar):
            if zeile and self._WERKZEUG_RE.search(zeile):
                for j in range(i, min(i + 4, len(nutzbar))):
                    if re.search(r"\bM0*6\b", nutzbar[j]):
                        wechsel.add(i)
                        break
        hat_gruppen = any("GROUP_BEGIN" in z.upper() for z in nutzbar)

        jobs = baum.insert("", "end", text="Jobs und Zyklen", open=True)
        werkzeuge = baum.insert("", "end", text="Werkzeuge", open=False)
        hand = baum.insert("", "end", text="Hand-Änderungen", open=True)
        aktueller_job = jobs
        anzahl_j = anzahl_w = 0

        for i, zeile in enumerate(nutzbar):
            nr = i + 1
            if not zeile.strip():
                continue
            gross = zeile.upper()
            gruppe = self._GRUPPE_RE.search(zeile)
            if gruppe:
                if anzahl_j < 500:
                    aktueller_job = baum.insert(jobs, "end", open=False,
                                                text="%s  (Zeile %d)"
                                                     % (gruppe.group(1)[:60], nr))
                    self.gliederung_ziele[aktueller_job] = nr
                    anzahl_j += 1
                continue
            if "GROUP_END" in gross:
                aktueller_job = jobs
                continue
            if (i in wechsel or (not wechsel and self._WERKZEUG_RE.search(zeile))) \
                    and anzahl_w < 400:
                treffer = self._WERKZEUG_RE.search(zeile)
                name = treffer.group(1) or ("T" + (treffer.group(2) or ""))
                # Bei ISO steht der Klartext meist als Kommentar daneben
                klartext = self._WZ_KOMMENTAR_RE.search(zeilen[nr - 1])
                if klartext:
                    zusatz = (klartext.group(1) or klartext.group(2) or "").strip()
                    if zusatz and not zusatz.startswith("-"):
                        name = "%s - %s" % (name, zusatz[:40])
                knoten = baum.insert(werkzeuge, "end",
                                     text="%s  (Zeile %d)" % (name, nr))
                self.gliederung_ziele[knoten] = nr
                anzahl_w += 1
                continue
            if not hat_gruppen and "MSG(" in gross and anzahl_j < 500:
                botschaft = self._MSG_RE.search(zeile)
                if botschaft and botschaft.group(1).strip():
                    knoten = baum.insert(jobs, "end",
                                         text="%s  (Zeile %d)"
                                              % (botschaft.group(1)[:60], nr))
                    self.gliederung_ziele[knoten] = nr
                    anzahl_j += 1
                    continue
            bearbeitung = self._BEARBEITUNG_RE.search(zeile)
            if bearbeitung and anzahl_j < 900:
                name = re.sub(r"\s+", " ", bearbeitung.group(1).upper())
                if name.startswith(self._RUEST_ZYKLEN) or name.upper() == "G80":
                    continue
                knoten = baum.insert(aktueller_job, "end",
                                     text="%s  (Zeile %d)" % (name, nr))
                self.gliederung_ziele[knoten] = nr
                anzahl_j += 1

        for nr in sorted(dok.hand)[:300]:
            text = zeilen[nr - 1].strip() if nr - 1 < len(zeilen) else ""
            art = "neu" if dok.hand[nr] == "n" else "geändert"
            knoten = baum.insert(hand, "end",
                                 text="Zeile %d (%s): %s" % (nr, art, text[:50]))
            self.gliederung_ziele[knoten] = nr

        baum.item(jobs, text="Jobs und Zyklen (%d)" % anzahl_j)
        baum.item(werkzeuge, text="Werkzeuge (%d)" % anzahl_w)
        baum.item(hand, text="Hand-Änderungen (%d)" % len(dok.hand))

    def gliederung_gewaehlt(self, _ereignis=None):
        auswahl = self.gliederung.selection()
        if not auswahl or self.aktiv is None:
            return
        nr = self.gliederung_ziele.get(auswahl[0])
        if nr:
            self.aktiv.springe(nr)

    # -- Status -------------------------------------------------------------

    def status_aktualisieren(self):
        dok = self.aktiv
        if dok is None:
            return
        try:
            zeile, spalte = dok.text.index("insert").split(".")
            zeile, spalte = int(zeile), int(spalte)
        except Exception:
            zeile, spalte = 1, 0
        self.v_pos.set("Zeile %d, Spalte %d" % (zeile, spalte + 1))
        text = dok.text.get("%d.0" % zeile, "%d.end" % zeile)
        satz = re.match(r"\s*(N\d+)", text, re.I)
        self.v_satz.set("Satz %s" % satz.group(1).upper() if satz else "")
        kurz = {"sinumerik": "SINUMERIK", "iso": "Fanuc/ISO",
                "heidenhain": "Heidenhain"}.get(dok.dialekt, dok.dialekt)
        ende = {"\r\n": "CRLF", "\n": "LF", "\r": "CR"}.get(dok.zeilenende, "LF")
        self.v_info.set("%d Zeilen | %s | %s | %s"
                        % (dok.zeilen_anzahl(), kurz, dok.codierung.upper(), ende))
        anzahl = dok.hand_anzahl()
        if dok.original is None:
            self.v_hand.set("kein Original")
        elif anzahl:
            self.v_hand.set("%d Zeile%s von Hand"
                            % (anzahl, "" if anzahl == 1 else "n"))
        else:
            self.v_hand.set("wie Original")

    # -- Original -----------------------------------------------------------

    def hinweis_pruefen(self, dok):
        """Weist darauf hin, wenn sehr viel abweicht - meist ein neuer Post-Lauf."""
        if dok.original is None or not dok.hand:
            return
        anteil = len(dok.hand) / float(max(1, dok.zeilen_anzahl()))
        if anteil > 0.35 and len(dok.hand) > 25:
            self.v_hinweis.set(
                "%s weicht in %d Zeilen vom hinterlegten Original ab - wurde das "
                "Programm neu aus SolidCAM ausgegeben?" % (dok.name(), len(dok.hand)))
            self.ansicht_anwenden()

    def hinweis_zeigen(self, text, dauer=10000):
        """Blendet eine Zeile oben ein, die sich von selbst wieder schließt."""
        self.v_hinweis.set(text)
        self.ansicht_anwenden()
        if dauer:
            self._planen(dauer, lambda t=text: self.hinweis_aus(nur_wenn=t))

    def hinweis_aus(self, nur_wenn=None):
        if nur_wenn is not None and self.v_hinweis.get() != nur_wenn:
            return                       # inzwischen steht dort etwas anderes
        self.v_hinweis.set("")
        self.ansicht_anwenden()

    def original_uebernehmen(self):
        from tkinter import messagebox
        dok = self.aktiv
        if dok is None:
            return
        if not dok.pfad:
            messagebox.showinfo(APP_NAME, "Das Programm muss zuerst gespeichert werden.",
                                parent=self.win)
            return
        if dok.hand and not messagebox.askyesno(
                APP_NAME,
                "Der aktuelle Stand wird als Original hinterlegt.\n\n"
                "Die %d bisher hervorgehobenen Hand-Änderungen gelten danach als "
                "Originalzustand und werden nicht mehr markiert.\n\nFortfahren?"
                % len(dok.hand), parent=self.win):
            return
        dok.original_neu_setzen()
        self.hinweis_aus()
        self.gliederung_bauen()
        self.status_aktualisieren()

    def _neuausgabe_setzen(self):
        self.einst["original_bei_neuausgabe"] = bool(self.v_neuausgabe.get())
        einstellungen_speichern(self.einst)

    def original_waehlen(self):
        from tkinter import filedialog, messagebox
        dok = self.aktiv
        if dok is None:
            return
        pfad = filedialog.askopenfilename(
            parent=self.win, title="Originalprogramm wählen (z. B. frisch aus SolidCAM)",
            initialdir=self.einst.get("letzter_ordner") or None,
            filetypes=[("NC-Programme", "*.mpf *.nc *.spf *.tap *.cnc *.ngc"),
                       ("Alle Dateien", "*.*")])
        if not pfad:
            return
        if dok.original_aus_datei(pfad):
            self.gliederung_bauen()
            self.status_aktualisieren()
            messagebox.showinfo(APP_NAME, "Vergleich läuft jetzt gegen:\n%s" % pfad,
                                parent=self.win)

    def original_info_zeigen(self):
        from tkinter import messagebox
        dok = self.aktiv
        if dok is None:
            return
        info = original_info(dok.pfad) if dok.pfad else None
        if not info:
            messagebox.showinfo(APP_NAME, "Für dieses Programm ist kein Original "
                                          "hinterlegt.", parent=self.win)
            return
        messagebox.showinfo(
            APP_NAME,
            "Original hinterlegt am: %s\nZeilen im Original: %s\n"
            "Abweichende Zeilen: %d\n\nAblage:\n%s"
            % (info.get("gesetzt", "?"), info.get("zeilen", "?"),
               dok.hand_anzahl(), _original_ordner()),
            parent=self.win)

    def originale_dialog(self):
        """Zeigt, wie viel Platz die Originale brauchen, und räumt auf."""
        tk = self.tk
        ttk = self.ttk
        from tkinter import messagebox

        T = THEMEN[self.einst.get("design", "hell")]
        fenster = tk.Toplevel(self.win)
        fenster.title("Originale aufräumen")
        fenster.configure(bg=T["bg"])
        fenster.transient(self.win)
        fenster.resizable(False, False)

        rahmen = ttk.Frame(fenster, padding=(14, 12))
        rahmen.pack(fill="both", expand=True)
        ttk.Label(rahmen, text="Abgelegte Originale", style="Section.TLabel").pack(anchor="w")
        ttk.Label(rahmen, text="Zu jedem geöffneten Programm liegt eine Kopie des "
                               "Originalstandes\nin %s.\nDaraus ergibt sich die "
                               "Hervorhebung der Hand-Änderungen." % _original_ordner(),
                  style="Muted.TLabel", justify="left").pack(anchor="w", pady=(2, 10))

        v_stand = tk.StringVar()
        v_weg = tk.StringVar()
        ttk.Label(rahmen, textvariable=v_stand).pack(anchor="w")
        ttk.Label(rahmen, textvariable=v_weg, style="Muted.TLabel").pack(anchor="w", pady=(0, 10))

        offen = [d.pfad for d in self.dokumente if d.pfad]
        v_tage = tk.IntVar(value=int(self.einst.get("aufbewahrung_tage", 90) or 90))
        v_zahl = tk.IntVar(value=int(self.einst.get("originale_hoechstzahl", 400) or 400))
        v_auto = tk.BooleanVar(value=bool(self.einst.get("aufraeumen_beim_beenden", True)))

        def zahlen_lesen():
            try:
                tage = max(1, int(v_tage.get()))
            except Exception:
                tage = 90
            try:
                zahl = max(10, int(v_zahl.get()))
            except Exception:
                zahl = 400
            return tage, zahl

        def auffrischen(*_a):
            tage, zahl = zahlen_lesen()
            anzahl, frei, bleibt, bleibt_bytes = originale_aufraeumen(
                tage, zahl, nur_pruefen=True, schonen=offen)
            v_stand.set("Gespeichert: %d Originale, %s"
                        % (anzahl + bleibt, groesse_lesbar(frei + bleibt_bytes)))
            if anzahl:
                v_weg.set("Nicht mehr gebraucht: %d Stück, %s würden frei"
                          % (anzahl, groesse_lesbar(frei)))
            else:
                v_weg.set("Nichts davon ist entbehrlich.")

        reihe = ttk.Frame(rahmen)
        reihe.pack(fill="x", pady=2)
        ttk.Label(reihe, text="Aufbewahren, solange benutzt in den letzten",
                  width=40).pack(side="left")
        ttk.Spinbox(reihe, from_=1, to=3650, width=6, textvariable=v_tage,
                    command=auffrischen).pack(side="left")
        ttk.Label(reihe, text="Tagen").pack(side="left", padx=(6, 0))
        reihe = ttk.Frame(rahmen)
        reihe.pack(fill="x", pady=2)
        ttk.Label(reihe, text="Höchstens aufbewahren", width=40).pack(side="left")
        ttk.Spinbox(reihe, from_=10, to=10000, width=6, textvariable=v_zahl,
                    command=auffrischen).pack(side="left")
        ttk.Label(reihe, text="Originale").pack(side="left", padx=(6, 0))
        v_tage.trace_add("write", auffrischen)
        v_zahl.trace_add("write", auffrischen)

        ttk.Checkbutton(rahmen, text="Beim Beenden des Programms automatisch aufräumen",
                        variable=v_auto).pack(anchor="w", pady=(10, 0))
        ttk.Label(rahmen, text="Die gerade geöffneten Programme bleiben immer erhalten.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 12))

        def uebernehmen():
            tage, zahl = zahlen_lesen()
            self.einst["aufbewahrung_tage"] = tage
            self.einst["originale_hoechstzahl"] = zahl
            self.einst["aufraeumen_beim_beenden"] = bool(v_auto.get())

        def jetzt():
            uebernehmen()
            tage, zahl = zahlen_lesen()
            anzahl, frei, _b, _bb = originale_aufraeumen(tage, zahl, schonen=offen)
            auffrischen()
            messagebox.showinfo(APP_NAME, "%d Originale entfernt, %s frei."
                                % (anzahl, groesse_lesbar(frei)) if anzahl
                                else "Es war nichts zu entfernen.", parent=fenster)

        def alle():
            if not messagebox.askyesno(
                    APP_NAME,
                    "Alle abgelegten Originale löschen?\n\nDanach gilt bei jedem "
                    "Programm der aktuelle Stand als Original - bisherige "
                    "Hand-Änderungen sind dann nicht mehr hervorgehoben.\n\n"
                    "Die NC-Dateien selbst werden nicht angerührt.",
                    parent=fenster):
                return
            anzahl, frei = originale_alle_loeschen(schonen=offen)
            for dok in self.dokumente:
                dok.original_pruefen()
            auffrischen()
            self.status_aktualisieren()
            messagebox.showinfo(APP_NAME, "%d Originale gelöscht, %s frei."
                                % (anzahl, groesse_lesbar(frei)), parent=fenster)

        def schliessen():
            uebernehmen()
            fenster.destroy()

        knoepfe = ttk.Frame(rahmen)
        knoepfe.pack(fill="x")
        ttk.Button(knoepfe, text="Jetzt aufräumen", style="Accent.TButton",
                   command=jetzt).pack(side="left")
        ttk.Button(knoepfe, text="Alle löschen", command=alle).pack(side="left", padx=6)
        ttk.Button(knoepfe, text="Ordner öffnen",
                   command=lambda: self._ordner_anzeigen(_original_ordner())).pack(side="left")
        ttk.Button(knoepfe, text="Schließen", command=schliessen).pack(side="right")
        fenster.protocol("WM_DELETE_WINDOW", schliessen)
        auffrischen()

    # -- Farbdialog ---------------------------------------------------------

    def farbdialog(self):
        tk = self.tk
        ttk = self.ttk
        from tkinter import colorchooser, filedialog, messagebox

        design = self.einst.get("design", "hell")
        T = THEMEN[design]
        fenster = tk.Toplevel(self.win)
        fenster.title("Farben und Schrift - %s Design"
                      % ("dunkles" if design == "dunkel" else "helles"))
        fenster.configure(bg=T["bg"])
        fenster.geometry("880x700")
        fenster.transient(self.win)

        kopf = ttk.Frame(fenster, padding=(12, 10, 12, 4))
        kopf.pack(fill="x")
        ttk.Label(kopf, text="Diese Farben gelten für das %s Design. Umgeschaltet "
                             "wird unten rechts in der Statusleiste."
                  % ("dunkle" if design == "dunkel" else "helle"),
                  style="Muted.TLabel").pack(anchor="w")

        flaeche = tk.Canvas(fenster, bg=T["bg"], highlightthickness=0)
        leiste = ttk.Scrollbar(fenster, orient="vertical", command=flaeche.yview)
        innen = ttk.Frame(flaeche, padding=(12, 6))
        innen.bind("<Configure>",
                   lambda e: flaeche.configure(scrollregion=flaeche.bbox("all")))
        flaeche.create_window(0, 0, window=innen, anchor="nw")
        flaeche.configure(yscrollcommand=leiste.set)
        fuss = ttk.Frame(fenster, padding=(12, 8))
        fuss.pack(side="bottom", fill="x")
        leiste.pack(side="right", fill="y")
        flaeche.pack(fill="both", expand=True)
        flaeche.bind("<MouseWheel>", lambda e: flaeche.yview_scroll(
            int(-1 * (e.delta / 40)), "units"))
        flaeche.bind("<Button-4>", lambda e: flaeche.yview_scroll(-3, "units"))
        flaeche.bind("<Button-5>", lambda e: flaeche.yview_scroll(3, "units"))

        farben = self.einst["farben"][design]
        knoepfe = {}

        def uebernehmen():
            for dok in self.dokumente:
                dok.tags_einrichten()
            self.trefferliste_fuellen()

        def farbe_waehlen(schluessel, knopf, beispiel=None):
            jetzt = farbe_von(farben, schluessel, design)
            _rgb, neu = colorchooser.askcolor(color=jetzt, parent=fenster,
                                              title="Farbe wählen")
            if not neu:
                return
            wert = farben.get(schluessel)
            if isinstance(wert, (list, tuple)):
                farben[schluessel] = [neu, int(wert[1]), int(wert[2])]
            else:
                farben[schluessel] = neu
            knopf.configure(bg=neu, activebackground=neu)
            if beispiel is not None:
                beispiel.configure(fg=neu)
            uebernehmen()

        def schnitt_umschalten(schluessel, stelle, var, beispiel):
            wert = farben.get(schluessel)
            if not isinstance(wert, (list, tuple)):
                return
            neu = [wert[0], int(wert[1]), int(wert[2])]
            neu[stelle] = 1 if var.get() else 0
            farben[schluessel] = neu
            name, groesse = editor_schrift(self.einst)
            schnitt = [name, groesse]
            if neu[1]:
                schnitt.append("bold")
            if neu[2]:
                schnitt.append("italic")
            beispiel.configure(font=tuple(schnitt))
            uebernehmen()

        def zeile_bauen(eltern, schluessel, beschriftung, beispieltext, mit_schnitt):
            reihe = ttk.Frame(eltern)
            reihe.pack(fill="x", pady=1)
            ttk.Label(reihe, text=beschriftung, width=34).pack(side="left")
            jetzt = farbe_von(farben, schluessel, design)
            knopf = tk.Button(reihe, bg=jetzt, activebackground=jetzt, width=4,
                              relief="solid", bd=1, highlightthickness=0, text=" ",
                              cursor="hand2")
            knopf.pack(side="left", padx=(0, 8))
            name, groesse = editor_schrift(self.einst)
            _f, fett, kursiv = stil_von(farben, schluessel, design)
            schnitt = [name, groesse]
            if fett:
                schnitt.append("bold")
            if kursiv:
                schnitt.append("italic")
            beispiel = tk.Label(reihe, text=beispieltext, fg=jetzt, font=tuple(schnitt),
                                bg=farbe_von(farben, "editor_bg", design),
                                anchor="w", padx=6, width=22)
            if mit_schnitt:
                beispiel.pack(side="left", padx=(0, 10))
            knopf.configure(command=lambda s=schluessel, k=knopf, b=beispiel:
                            farbe_waehlen(s, k, b if mit_schnitt else None))
            knoepfe[schluessel] = (knopf, beispiel if mit_schnitt else None)
            if mit_schnitt:
                v_fett = tk.BooleanVar(value=fett)
                v_kursiv = tk.BooleanVar(value=kursiv)
                ttk.Checkbutton(reihe, text="fett", variable=v_fett,
                                command=lambda s=schluessel, v=v_fett, b=beispiel:
                                schnitt_umschalten(s, 1, v, b)).pack(side="left")
                ttk.Checkbutton(reihe, text="kursiv", variable=v_kursiv,
                                command=lambda s=schluessel, v=v_kursiv, b=beispiel:
                                schnitt_umschalten(s, 2, v, b)).pack(side="left", padx=(6, 0))
                knoepfe[schluessel] = (knopf, beispiel, v_fett, v_kursiv)

        letzte_gruppe = None
        for schluessel, beschriftung, gruppe, beispiel in SYNTAX_KLASSEN:
            if gruppe != letzte_gruppe:
                ttk.Label(innen, text=gruppe, style="Section.TLabel").pack(
                    anchor="w", pady=(10, 2))
                letzte_gruppe = gruppe
            zeile_bauen(innen, schluessel, beschriftung, beispiel, True)

        ttk.Label(innen, text="Editorfarben", style="Section.TLabel").pack(
            anchor="w", pady=(14, 2))
        for schluessel, beschriftung in EDITOR_FARBEN:
            zeile_bauen(innen, schluessel, beschriftung, "", False)

        ttk.Label(innen, text="Schrift und Hervorhebung", style="Section.TLabel").pack(
            anchor="w", pady=(14, 2))
        reihe = ttk.Frame(innen)
        reihe.pack(fill="x", pady=2)
        ttk.Label(reihe, text="Schriftart", width=34).pack(side="left")
        import tkinter.font as tkfont
        familien = sorted({f for f in tkfont.families(self.win) if not f.startswith("@")},
                          key=str.lower)
        v_schrift = tk.StringVar(value=editor_schrift(self.einst)[0])
        feld = ttk.Combobox(reihe, textvariable=v_schrift, values=familien, width=28)
        feld.pack(side="left")
        v_groesse = tk.IntVar(value=editor_schrift(self.einst)[1])
        ttk.Label(reihe, text="Größe", width=9, anchor="e").pack(side="left", padx=(10, 4))
        ttk.Spinbox(reihe, from_=6, to=32, width=5, textvariable=v_groesse).pack(side="left")

        def schrift_setzen(*_a):
            self.einst["schrift"] = v_schrift.get()
            try:
                self.einst["schriftgroesse"] = int(v_groesse.get())
            except Exception:
                pass
            uebernehmen()

        feld.bind("<<ComboboxSelected>>", schrift_setzen)
        feld.bind("<Return>", schrift_setzen)
        v_groesse.trace_add("write", schrift_setzen)

        reihe = ttk.Frame(innen)
        reihe.pack(fill="x", pady=(8, 2))
        ttk.Label(reihe, text="Hervorhebung von Hand-Änderungen",
                  width=34).pack(side="left")
        v_staerke = tk.StringVar(value=self.einst.get("hand_staerke", "normal"))

        def staerke_setzen():
            self.einst["hand_staerke"] = v_staerke.get()
            uebernehmen()

        for wert, text in (("dezent", "nur Randmarke"), ("normal", "Randmarke und Farbe"),
                           ("stark", "Randmarke, Farbe und fett")):
            ttk.Radiobutton(reihe, text=text, value=wert, variable=v_staerke,
                            command=staerke_setzen).pack(side="left", padx=(0, 10))

        reihe = ttk.Frame(innen)
        reihe.pack(fill="x", pady=2)
        v_erk = tk.BooleanVar(value=self.einst.get("hand_erkennen", True))

        def erkennen_setzen():
            self.einst["hand_erkennen"] = bool(v_erk.get())
            for dok in self.dokumente:
                dok.original_pruefen()
            self.status_aktualisieren()

        ttk.Checkbutton(reihe, text="Hand-Änderungen gegenüber dem Original erkennen",
                        variable=v_erk, command=erkennen_setzen).pack(side="left")
        reihe = ttk.Frame(innen)
        reihe.pack(fill="x", pady=2)
        v_bak = tk.BooleanVar(value=self.einst.get("sicherungskopie", True))

        def bak_setzen():
            self.einst["sicherungskopie"] = bool(v_bak.get())

        ttk.Checkbutton(reihe, text="Beim Speichern eine Sicherungskopie (.bak) anlegen",
                        variable=v_bak, command=bak_setzen).pack(side="left")

        def zuruecksetzen():
            if not messagebox.askyesno(APP_NAME, "Alle Farben dieses Designs auf die "
                                                 "Voreinstellung zurücksetzen?",
                                       parent=fenster):
                return
            self.einst["farben"][design] = farben_standard(design)
            uebernehmen()
            fenster.destroy()
            self.farbdialog()

        def farben_speichern():
            import json
            pfad = filedialog.asksaveasfilename(
                parent=fenster, title="Farben speichern", defaultextension=".json",
                initialfile="nc-editor-farben-%s.json" % design,
                filetypes=[("Farbdatei", "*.json")])
            if not pfad:
                return
            try:
                with open(pfad, "w", encoding="utf-8") as fh:
                    json.dump({"design": design, "farben": farben}, fh,
                              indent=2, ensure_ascii=False)
            except Exception as fehler:
                messagebox.showerror(APP_NAME, str(fehler), parent=fenster)

        def einlesen():
            import json
            pfad = filedialog.askopenfilename(parent=fenster, title="Farben laden",
                                              filetypes=[("Farbdatei", "*.json"),
                                                         ("Alle Dateien", "*.*")])
            if not pfad:
                return
            try:
                with open(pfad, "r", encoding="utf-8") as fh:
                    gelesen = json.load(fh)
                neu = gelesen.get("farben", gelesen)
                if not isinstance(neu, dict):
                    raise ValueError("Unerwarteter Inhalt")
            except Exception as fehler:
                messagebox.showerror(APP_NAME, "Datei nicht lesbar:\n%s" % fehler,
                                     parent=fenster)
                return
            voll = farben_standard(design)
            voll.update(neu)
            self.einst["farben"][design] = voll
            uebernehmen()
            fenster.destroy()
            self.farbdialog()

        ttk.Button(fuss, text="Zurücksetzen", command=zuruecksetzen).pack(side="left")
        ttk.Button(fuss, text="Exportieren ...", command=farben_speichern).pack(side="left", padx=6)
        ttk.Button(fuss, text="Importieren ...", command=einlesen).pack(side="left")
        ttk.Button(fuss, text="Schließen", style="Accent.TButton",
                   command=fenster.destroy).pack(side="right")
        ttk.Label(fuss, text="Änderungen wirken sofort.",
                  style="Muted.TLabel").pack(side="right", padx=10)

    # -- Sonstiges ----------------------------------------------------------

    def _editor_befehl(self, ereignis):
        if self.aktiv:
            try:
                self.aktiv.text.event_generate(ereignis)
            except Exception:
                pass

    def alles_markieren(self):
        if self.aktiv:
            self.aktiv.text.tag_add("sel", "1.0", "end-1c")
        return "break"

    def _einzelnes_fenster_setzen(self):
        self.einst["einzelnes_fenster"] = bool(self.v_einzeln.get())
        einstellungen_speichern(self.einst)

    def ordner_oeffnen(self):
        self._ordner_anzeigen(daten_verzeichnis())

    def windows_anmelden(self):
        from tkinter import messagebox
        if not sys.platform.startswith("win"):
            messagebox.showinfo(APP_NAME, "Diese Funktion gibt es nur unter Windows.",
                                parent=self.win)
            return
        ok, meldung = windows_registrieren(False)
        if ok:
            if messagebox.askyesno(
                    APP_NAME, meldung + "\n\nJetzt die Windows-Einstellungen für "
                                        "Standard-Apps öffnen?", parent=self.win):
                standard_apps_oeffnen()
        else:
            messagebox.showerror(APP_NAME, meldung, parent=self.win)

    def windows_abmelden(self):
        from tkinter import messagebox
        if not sys.platform.startswith("win"):
            return
        ok, meldung = windows_registrieren(True)
        (messagebox.showinfo if ok else messagebox.showerror)(
            APP_NAME, meldung, parent=self.win)

    def info_zeigen(self):
        """Info-Fenster: Herkunft, Lizenz, Gefahrenhinweis und Ablageorte."""
        tk = self.tk
        ttk = self.ttk

        design = self.einst.get("design", "hell")
        T = THEMEN[design]
        fenster = tk.Toplevel(self.win)
        fenster.title("Info")
        fenster.configure(bg=T["bg"])
        fenster.resizable(False, False)
        fenster.transient(self.win)

        # Das Typenschild steht jetzt hier statt dauerhaft über dem Programm
        kopf = tk.Canvas(fenster, height=84, width=600, bg=T["bg"],
                         highlightthickness=0)
        kopf.pack(fill="x", padx=10, pady=(10, 6))
        kopf.bind("<Configure>", lambda e: typenschild(
            kopf, self.logo, APP_NAME,
            "NC-Programme lesen, suchen und ändern", design))

        rahmen = ttk.Frame(fenster, padding=(16, 2, 16, 12))
        rahmen.pack(fill="both", expand=True)

        ttk.Label(rahmen, text="Fassung %s" % VERSION,
                  style="Section.TLabel").pack(anchor="w")
        ttk.Label(rahmen, text="Editor für NC-Programme (.mpf, .nc). Läuft "
                               "offline, es werden keine Daten übertragen.",
                  style="Muted.TLabel", justify="left").pack(anchor="w", pady=(2, 10))

        # ---- Gefahrenhinweis, deutlich abgesetzt ----
        warn_bg = "#FFF3CD" if design == "hell" else "#3B2F12"
        warn_fg = "#6B4E00" if design == "hell" else "#F0D79A"
        kasten = tk.Frame(fenster, bg="#E8A33D")
        kasten.pack(fill="x", padx=16, pady=(0, 12))
        innen = tk.Frame(kasten, bg=warn_bg)
        innen.pack(fill="both", expand=True, padx=1, pady=1)
        tk.Label(innen, text="Verwendung auf eigene Gefahr",
                 bg=warn_bg, fg=warn_fg, font=ui_schriften()[1],
                 anchor="w").pack(fill="x", padx=10, pady=(7, 0))
        tk.Label(innen, justify="left", anchor="w", bg=warn_bg, fg=warn_fg,
                 font=ui_schriften()[0],
                 text="Das Programm wird ohne jede Gewährleistung bereitgestellt.\n"
                      "Prüfen Sie geänderte NC-Programme vor dem Einsatz an der\n"
                      "Maschine im Einzelschritt, mit Probelauf und bei reduziertem\n"
                      "Vorschub. Für Schäden an Werkstück, Werkzeug, Maschine oder\n"
                      "Personen wird keine Haftung übernommen."
                 ).pack(fill="x", padx=10, pady=(2, 8))

        unten = ttk.Frame(fenster, padding=(16, 0, 16, 12))
        unten.pack(fill="both", expand=True)

        zeile = ttk.Frame(unten)
        zeile.pack(anchor="w")
        ttk.Label(zeile, text="\u00a9 %s %s \u2013 Open Source unter der MIT-Lizenz, "
                              "frei nutzbar und weitergebbar."
                  % (APP_YEAR, APP_AUTHOR), style="Muted.TLabel").pack(side="left")
        zeile = ttk.Frame(unten)
        zeile.pack(anchor="w", pady=(2, 10))
        ttk.Button(zeile, text=APP_URL.split("//")[-1], style="Link.TButton",
                   takefocus=False, cursor="hand2",
                   command=lambda: link_oeffnen(APP_URL)).pack(side="left")

        ttk.Label(unten, justify="left", style="Muted.TLabel",
                  text="SINUMERIK, FANUC, Haas, HEIDENHAIN, SolidCAM, SOLIDWORKS und\n"
                       "Windows sind Marken ihrer jeweiligen Inhaber. Es besteht keine\n"
                       "Verbindung zu diesen Herstellern. Alle Lizenz- und\n"
                       "Markenhinweise stehen unter \u201eLizenzen\u201c."
                  ).pack(anchor="w", pady=(0, 10))

        ttk.Separator(unten, orient="horizontal").pack(fill="x", pady=(0, 8))
        ttk.Label(unten, justify="left", style="Muted.TLabel",
                  text="Einstellungen:  %s\nOriginale:  %s\nDateien hineinziehen:  %s"
                       % (einstellungen_pfad(), _original_ordner(),
                          "möglich" if self.dnd_bereit
                          else "nicht möglich (tkinterdnd2 fehlt)")
                  ).pack(anchor="w")

        knoepfe = ttk.Frame(unten)
        knoepfe.pack(fill="x", pady=(14, 0))
        ttk.Button(knoepfe, text="Schließen", style="Accent.TButton",
                   command=fenster.destroy).pack(side="right")
        ttk.Button(knoepfe, text="Lizenzen",
                   command=self.lizenzen_zeigen).pack(side="right", padx=8)
        ttk.Button(knoepfe, text="Einstellungsordner öffnen",
                   command=self.ordner_oeffnen).pack(side="left")
        fenster.bind("<Escape>", lambda e: fenster.destroy())
        fenster.update_idletasks()
        fenster.geometry("+%d+%d" % (
            self.win.winfo_rootx() + max(0, (self.win.winfo_width()
                                             - fenster.winfo_width()) // 2),
            self.win.winfo_rooty() + 80))

    def lizenzen_zeigen(self):
        """Fenster mit allen Lizenz- und Markenhinweisen (im Programm eingebaut)."""
        tk = self.tk
        ttk = self.ttk
        from tkinter import filedialog, messagebox, scrolledtext

        T = THEMEN[self.einst.get("design", "hell")]
        text = lizenztexte()
        fenster = tk.Toplevel(self.win)
        fenster.title("Lizenzen")
        fenster.configure(bg=T["bg"])
        fenster.geometry("920x720")
        fenster.transient(self.win)

        kopf = ttk.Frame(fenster, padding=(12, 10, 12, 4))
        kopf.pack(fill="x")
        ttk.Label(kopf, text="Lizenz des %s und der verwendeten Drittkomponenten"
                  % APP_NAME, style="Section.TLabel").pack(anchor="w")
        ttk.Label(kopf, text="Enthält auch die Markenhinweise. Dieselben Texte "
                             "liefert  ncedit.py --lizenzen",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 0))

        # Sprungmarken zu den Abschnitten - der Text ist über 2000 Zeilen lang.
        # Überschriften stehen entweder hinter einer Linie aus 70 "=" oder
        # über einer kurzen "="-Linie.
        zeilen = text.split("\n")
        linie = "=" * 70
        # Die eingebetteten Fremdlizenzen haben eigene Unterüberschriften, die
        # hier nichts zu suchen haben. Deshalb gelten unterstrichene
        # Überschriften nur bis zur ersten nummerierten Komponente.
        erste_komponente = len(zeilen)
        for nr in range(2, len(zeilen)):
            if zeilen[nr - 2].strip() == linie and re.match(r"^\d+\) ", zeilen[nr - 1]):
                erste_komponente = nr
                break
        marken = []
        for nr in range(2, len(zeilen) + 1):
            zeile = zeilen[nr - 1].strip()
            if not zeile or zeile == linie or zeilen[nr - 1].startswith(" "):
                continue
            vorher = zeilen[nr - 2].strip()
            nachher = zeilen[nr].strip() if nr < len(zeilen) else ""
            if vorher == linie:
                marken.append((zeile[:60], nr))
            elif (nr < erste_komponente and nachher
                  and set(nachher) == {"="} and nachher != linie):
                marken.append((zeile[:60], nr))

        fuss = ttk.Frame(fenster, padding=(12, 8))
        fuss.pack(side="bottom", fill="x")
        rahmen = tk.Frame(fenster, bg=T["line"])
        rahmen.pack(fill="both", expand=True, padx=12)
        feld = scrolledtext.ScrolledText(rahmen, font=ui_schriften()[3], wrap="word",
                                         bd=0, relief="flat", highlightthickness=0,
                                         bg=T["feld"], fg=T["ink"], padx=10, pady=8)
        feld.pack(fill="both", expand=True, padx=1, pady=1)
        feld.insert("1.0", text)
        feld.configure(state="disabled")

        if marken:
            ttk.Label(fuss, text="Abschnitt:", style="Muted.TLabel").pack(side="left")
            v_marke = tk.StringVar(value=marken[0][0])
            auswahl = ttk.Combobox(fuss, textvariable=v_marke, state="readonly",
                                   width=42, values=[m[0] for m in marken])
            auswahl.pack(side="left", padx=(6, 12))

            def springen(_e=None):
                for name, zeile in marken:
                    if name == v_marke.get():
                        feld.see("%d.0" % max(1, zeile - 2))
                        return

            auswahl.bind("<<ComboboxSelected>>", springen)

        def speichern():
            pfad = filedialog.asksaveasfilename(
                parent=fenster, title="Lizenztexte speichern",
                initialfile="NC-Editor-%s-Lizenzen.txt" % VERSION,
                defaultextension=".txt", filetypes=[("Textdatei", "*.txt")])
            if not pfad:
                return
            try:
                with open(pfad, "w", encoding="utf-8") as fh:
                    fh.write(text)
            except Exception as fehler:
                messagebox.showerror(APP_NAME, str(fehler), parent=fenster)

        ttk.Button(fuss, text="Schließen", style="Accent.TButton",
                   command=fenster.destroy).pack(side="right")
        ttk.Button(fuss, text="Als Datei speichern ...",
                   command=speichern).pack(side="right", padx=8)

    def beenden(self):
        from tkinter import messagebox
        for dok in list(self.dokumente):
            if not dok.gespeichert:
                antwort = messagebox.askyesnocancel(
                    APP_NAME, "%s wurde geändert.\n\nÄnderungen speichern?" % dok.name(),
                    parent=self.win)
                if antwort is None:
                    return
                if antwort and not self.speichern(dok):
                    return
        try:
            self.einst["fenster"] = self.win.geometry()
        except Exception:
            pass
        if self.einst.get("aufraeumen_beim_beenden", True):
            # Hält den Ablageordner klein: weg kommt, was nicht mehr
            # gebraucht wird. Die gerade geöffneten Programme bleiben.
            try:
                originale_aufraeumen(
                    self.einst.get("aufbewahrung_tage", 90),
                    self.einst.get("originale_hoechstzahl", 400),
                    schonen=[d.pfad for d in self.dokumente if d.pfad])
            except Exception:
                pass
        einstellungen_speichern(self.einst)
        self._auftraege_abraeumen()
        if self.instanz is not None:
            self.instanz.freigeben()
        self.win.destroy()

    def starten(self):
        self.win.mainloop()


# ---------------------------------------------------------------------------
# Teil 12: Windows - Anmeldung als Programm für .mpf und .nc
# ---------------------------------------------------------------------------
#
# Angemeldet wird nur im Benutzerzweig (HKEY_CURRENT_USER), deshalb sind keine
# Administratorrechte nötig. Windows 10 und 11 lassen das Standardprogramm
# aus Sicherheitsgründen nicht mehr durch ein Programm selbst setzen - die
# letzte Bestätigung macht der Benutzer in den Windows-Einstellungen. Diese
# Anmeldung sorgt dafür, dass der Editor dort und unter "Öffnen mit"
# überhaupt zur Auswahl steht.

PROGID_VORSATZ = "NCEditor"
ENDUNG_NAMEN = {
    ".mpf": "NC-Programm (SINUMERIK Hauptprogramm)",
    ".nc": "NC-Programm",
    ".spf": "NC-Unterprogramm (SINUMERIK)",
    ".tap": "NC-Programm",
    ".cnc": "NC-Programm",
    ".ngc": "NC-Programm",
}
REG_ENDUNGEN = (".mpf", ".nc", ".spf")


def _start_befehl():
    """Befehlszeile, mit der Windows eine Datei an dieses Programm übergibt."""
    if getattr(sys, "frozen", False):
        return '"%s" "%%1"' % sys.executable, sys.executable
    skript = os.path.abspath(__file__)
    ordner = os.path.dirname(sys.executable)
    pythonw = os.path.join(ordner, "pythonw.exe")
    starter = pythonw if os.path.isfile(pythonw) else sys.executable
    return '"%s" "%s" "%%1"' % (starter, skript), starter


def _symbol_pfad():
    """Liefert "Datei,Index" für das Programmsymbol oder None."""
    if getattr(sys, "frozen", False):
        return "%s,0" % sys.executable
    ziel = os.path.join(daten_verzeichnis(), "ncedit.ico")
    if os.path.isfile(ziel):
        return "%s,0" % ziel
    try:
        import base64
        from io import BytesIO
        from PIL import Image

        roh = base64.b64decode("".join(ICON_PNG_B64))
        bild = Image.open(BytesIO(roh)).convert("RGBA")
        bild.save(ziel, format="ICO",
                  sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (256, 256)])
        return "%s,0" % ziel
    except Exception:
        return None


def windows_registrieren(entfernen=False):
    """Meldet das Programm für .mpf/.nc an oder entfernt die Anmeldung."""
    if not sys.platform.startswith("win"):
        return False, "Nur unter Windows möglich."
    try:
        import winreg
    except ImportError:
        return False, "Registrierungszugriff nicht verfügbar."

    befehl, programm = _start_befehl()
    anwendung = os.path.basename(programm)
    klassen = r"Software\Classes"

    def loeschen(wurzel, pfad, tiefe=0):
        if tiefe > 8:
            return
        try:
            with winreg.OpenKey(wurzel, pfad, 0, winreg.KEY_READ) as schluessel:
                versuche = 0
                while versuche < 200:
                    try:
                        unter = winreg.EnumKey(schluessel, 0)
                    except OSError:
                        break
                    loeschen(wurzel, pfad + "\\" + unter, tiefe + 1)
                    versuche += 1
            winreg.DeleteKey(wurzel, pfad)
        except OSError:
            pass

    try:
        if entfernen:
            for endung in REG_ENDUNGEN:
                progid = PROGID_VORSATZ + endung
                loeschen(winreg.HKEY_CURRENT_USER, klassen + "\\" + progid)
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        klassen + "\\" + endung + r"\OpenWithProgids",
                                        0, winreg.KEY_SET_VALUE) as schluessel:
                        winreg.DeleteValue(schluessel, progid)
                except OSError:
                    pass
            loeschen(winreg.HKEY_CURRENT_USER,
                     klassen + "\\Applications\\" + anwendung)
            loeschen(winreg.HKEY_CURRENT_USER, r"Software\%s" % APP_NAME)
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\RegisteredApplications", 0,
                                    winreg.KEY_SET_VALUE) as schluessel:
                    winreg.DeleteValue(schluessel, APP_NAME)
            except OSError:
                pass
            _explorer_benachrichtigen()
            return True, "Die Anmeldung wurde entfernt."

        symbol = _symbol_pfad()
        for endung in REG_ENDUNGEN:
            progid = PROGID_VORSATZ + endung
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  klassen + "\\" + progid) as schluessel:
                winreg.SetValueEx(schluessel, "", 0, winreg.REG_SZ,
                                  ENDUNG_NAMEN.get(endung, "NC-Programm"))
                winreg.SetValueEx(schluessel, "FriendlyTypeName", 0, winreg.REG_SZ,
                                  ENDUNG_NAMEN.get(endung, "NC-Programm"))
            if symbol:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                      klassen + "\\" + progid + r"\DefaultIcon") as s:
                    winreg.SetValueEx(s, "", 0, winreg.REG_SZ, symbol)
            for verb in ("open", "edit"):
                with winreg.CreateKey(
                        winreg.HKEY_CURRENT_USER,
                        klassen + "\\" + progid + r"\shell\%s\command" % verb) as s:
                    winreg.SetValueEx(s, "", 0, winreg.REG_SZ, befehl)
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                  klassen + "\\" + endung) as s:
                pass
            with winreg.CreateKey(
                    winreg.HKEY_CURRENT_USER,
                    klassen + "\\" + endung + r"\OpenWithProgids") as s:
                winreg.SetValueEx(s, progid, 0, winreg.REG_NONE, b"")

        # Eintrag unter "Öffnen mit" und in der Liste der Standard-Apps
        grund = klassen + "\\Applications\\" + anwendung
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, grund) as s:
            winreg.SetValueEx(s, "FriendlyAppName", 0, winreg.REG_SZ, APP_NAME)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              grund + r"\shell\open\command") as s:
            winreg.SetValueEx(s, "", 0, winreg.REG_SZ, befehl)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              grund + r"\SupportedTypes") as s:
            for endung in REG_ENDUNGEN:
                winreg.SetValueEx(s, endung, 0, winreg.REG_SZ, "")

        faehig = r"Software\%s\Capabilities" % APP_NAME
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, faehig) as s:
            winreg.SetValueEx(s, "ApplicationName", 0, winreg.REG_SZ, APP_NAME)
            winreg.SetValueEx(s, "ApplicationDescription", 0, winreg.REG_SZ,
                              "Editor für NC-Programme mit Farbhervorhebung")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              faehig + r"\FileAssociations") as s:
            for endung in REG_ENDUNGEN:
                winreg.SetValueEx(s, endung, 0, winreg.REG_SZ,
                                  PROGID_VORSATZ + endung)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                              r"Software\RegisteredApplications") as s:
            winreg.SetValueEx(s, APP_NAME, 0, winreg.REG_SZ, faehig)

        _explorer_benachrichtigen()
        return True, (
            "%s ist jetzt für %s angemeldet.\n\n"
            "Windows 10 und 11 lassen das Standardprogramm nicht durch ein Programm "
            "selbst setzen. Die letzte Bestätigung machen Sie einmalig in Windows:\n"
            "Rechtsklick auf eine .mpf-Datei, „Öffnen mit“, „Andere App "
            "auswählen“, %s wählen und „Immer“ anhaken -\n"
            "oder in Einstellungen, Apps, Standard-Apps."
            % (APP_NAME, ", ".join(REG_ENDUNGEN), APP_NAME))
    except OSError as fehler:
        return False, "Anmeldung fehlgeschlagen:\n%s" % fehler


def _explorer_benachrichtigen():
    """Sagt dem Explorer, dass sich Dateizuordnungen geändert haben."""
    try:
        import ctypes

        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception:
        pass


def standard_apps_oeffnen():
    try:
        os.startfile("ms-settings:defaultapps")      # noqa: S606
    except Exception:
        try:
            import subprocess
            subprocess.Popen(["control", "/name", "Microsoft.DefaultPrograms"])
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Teil 13: Start
# ---------------------------------------------------------------------------

# Vollständige Lizenztexte, komprimiert eingebettet: eigene MIT-Lizenz,
# Markenhinweise und die Lizenzen aller mitgelieferten Fremdkomponenten.
# Anzeigen mit der Schaltfläche "Lizenzen" oder mit  ncedit.py --lizenzen
LIZENZEN_Z_B64 = (
    "eNrtfdt2G0d67n09RYVrZYnUNCGSsmxLTrIHJEEKNk8BQMlydlbUAApAm41uTB9IQdf7PXIzN3mBXM1V/GL7P1RVVx9AghRt"
    "z2TINSOTQHed6z//33/S/alzBv8T/6x/hP3ty37E2cF2ZxxkcSK35flCRbIf58lIyTzKVCLH8P/T7mD7JPisos9ilmWL9M2L"
    "F0GcbafBfBEuW6N4/lhDEdCTPAlGKkqVEAfxYpkE01kmN0dbcm9n72t5MEuCNIsXMxhVfzSbB6MrT1bGIi5UMg/SNIgjGaQS"
    "HlXDpZwmPsxn7MlJopSMJ3I085Op8mQWSz9ayoVKUnghHmZ+EAXRVPpyBP0LeDKbQTNpPMlu/ETBw2Ppp2k8CnxoT47jUT5X"
    "UeZn2N8kCFUqN7OZkht9/cbGFnUyVn4ogkjid+YreRNkszjPZKLSLAlG2AbMJxqF+RjHYL4Og3mge8DXaVFSAY3mKcwAx+nJ"
    "eTwOJvhfRdNa5MMwSGeeHAfY9DDP4MMUP6TV9XAeL2DPUxWGAloIYNw012J09AwOfYELmuklSvGTm1k8L88kSMUkTyLoUtE7"
    "4xiWjHr8WY0y/AQfn8RhGN/g1EZxBIcOZpS+EWIAX/nD+FrRXHjPoziDofIQcAMWxa7qr9KZH4ZyqPSCQb+wvL4znQS7TzPY"
    "+MAP5SJOqL/qNFvQ/9uO7J8fDd63ex3Z7cuL3vm77mHnUG60+/D3hiffdwdvzy8HEp7otc8GH+T5kWyffZA/dM8OPdn58aLX"
    "6ffleU90Ty9Ouh34rHt2cHJ52D07lvvw3tk5HOwuHG9odHAusUPdVLfTx8ZOO72Dt/Bne7970h188MRRd3CGbR6d92RbXrR7"
    "g+7B5Um7Jy8uexfn/Q50fwjNnnXPjnrQS+e0czZoQa/wmey8gz9k/2375AS7Eu1LGH0PxycPzi8+9LrHbwfy7fnJYQc+3O/A"
    "yNr7Jx3uCiZ1cNLunnrysH3aPu7QW+fQSk/gYzw6+f5tBz/C/trwv4NB9/wMp3FwfjbowZ8ezLI3sK++7/Y7nmz3un1ckKPe"
    "+akncDnhjXNqBN4763AruNSytCPwCP592e/YBuVhp30CbfXxZZyieRh284c8+Sz9fCIPVZ6lo9kb+b1CMjb2kwlcw0gWFO8q"
    "TjMVhXEqozwDAufJa5X88ucIHo+AAI7FjQoyvFBD/M7PRzM8YyqYqgjauUjin9UVNNCS+wovbB5N30CvCZAReERaArZNbTEJ"
    "nQURNJrKYaiCYSZVAqeYmuikcoqfXKkgUvJY3fzy51kCD6UZNAu0eap4YJlCkg19A0mbz5W8jpFKz2UniFI/g5lHTLR9mDq2"
    "FNBXn1UIfydBluFYJNxnAU0MVYgLtUh++csExiBO/V/+EyYLRAImmmbUkIqmQElGcGN4Apn6lMEqi9N27wfLj4TAaRcLiy8r"
    "s1RphiOH31Jphk3THQLVUzMz43cqGQbRGCf7ORe4T2+B4GRAn3AzcCTIkSJYh8iP6Ld+pnKVwAuKNss2rlq0CXooN0EyFtfI"
    "DGa4aTd0FoAr+Hk6VbSzQFBgvsTvYKh/yT5nHvRCi5LJGB8HphHoh2Hqh4GSZ/6cGktwoNAULFAYqF/+k5ZOD9GT+RzmgvOE"
    "pYftxkOElPRGhbCekTgEFhLowdvJpGOgVnSsaNJ6Fvl8quAVeQUNt2QfRpDCYsEuJ1fwKQ5SwCpOVZb4eDjNFwH0m8ifFRy5"
    "ELdCdqOZP1QJEF0p4TJeAt3p/uDBr6dtIDAetgwTSyX9mD/ax/D0Ufvs8kDe8sMPHMQJUFpiVvDSW99Pb3uHH2jnWTz3mft1"
    "o1ELX+wAAT572+6eASk5g4H9EPoJHj3z4mGvJb8/B5IJVNJ5Wh7Ph29xbnEYjA/apys7tg+cZGPssH9+0j18f977ob/ihUPg"
    "+n4eZrK/hFM5h8NMTbyPk6u0Muv3sDXxTerJ02CUxCg6wMKqaazkZZfasp9XXrxYAsOPblku/YBlu0cxnB3z9lmcqYU//sMf"
    "Vr19CK++jYV4T1RN2aukT/PVL/8d4RW54+yAzBAYanijokikcBpnAXwRweHP9J1HCjxVk1/+MksyOqst2OaUKNWRmoUKaUME"
    "i/iW6SH8Fv7y5zTNoDVol1sylwrvzRiWn0gKjpUuJNJq6H889OGS//Jn4uRAVfSdZKJiSALcsxAEmv0AaFsM3N9cGmmu4Bgk"
    "BvizIDkCLupUQfcTILklggKfpUxF9bXOZIkg+2EKAl2AKznQtLL7FtgYPtQ7P+61T087okH4bUfEnWxDOGlYWbzrSDSIxvMI"
    "fvnvySTC7x1WJdOFgkWDvzwB6xIkMKwI7i8KUD0Fq6mAh+BOEeOBfq5BFjOUWXZnMD3ctyyft5iY6778ZIinJasROWQc8BqM"
    "CpuPiD6P5S9/gROSAQ+dZryJKQi9KRwdOHCRwoWEIfyAAhqTt3NgkEHk65GgzEmHBBePDgKuAGwKMLmZGgJ1FPjSW5jU9i//"
    "D+fO1B9YNGyDh1vDzMCy8QwYtvjH9sXFYXvQ/sf/aznU/411x4qGHcLpsl2CoAjHHl7+DDOHY/nfKVHrTeCkZnPe2IGj1mSb"
    "gjWBflEh2MJtP9FKm3wHcs1hrzsY/HB+enF+BtKZo8mt0IVwoUBehvngqWDeS+wPxQUJFyuB40WnGtdoXGK/+mbArg0/37QE"
    "PhDwerfUJwUsPWOpQ19MPGIqAVFgyDcBeTG+j7zYyjuJKBSDNA59WHi+NfYKS7oyzFL1LdzGewtjRlkEWT2RiWAurBwgHk2P"
    "3d2S2VWA52wcjfegZ3O1+fKgRARHC0UikIYCZKZAMqVRaKegauVDVCBfdMLAv9574TT2G+m3O/JiBqR2sQDxz59Gv/zXky77"
    "pMs+6bJ/z7osCJ3ywr9CQv7LX4Cgg/iJ9Hlwtd1JWDdFGp1dHUaHEnWcYxXDlZEXKvPTIP0O6Z5lHoK1LeBi0S9/Hs1Q85Xt"
    "IVDmCLTC1qPR4b0tPZ7tyjA9EhmQErt0Gj5LFahcK4jxgmcC1BiefjQ6fEh8y7nwIM+hgKGSBEUlrcTB0pA2KMd5Mpq9EeXF"
    "9UASxUsI1/EAiGaCFAGtksBysmASjEAsSpUPL8qNQzWPr0D3jtMNT7Sns8CHTU389EpdB3CU4AYDqTxOAoVyBnBWYMmd7VM/"
    "CN9IPf8/BkHWGttmWtNECCN2kFaEy8rbTDTIpfLwuyVFQFiGy193JilORakRECO1Pb9rEoMSJYVDMQfNYbEIl8TMgCYyGyq4"
    "lEBGQkTPTjCP4BFQDj4tYOOCDN4FRjEK/WDOdBRknOA6GOe+bq2lqXQOHCkpc1WXNDfzJIcHCSTomgk1cNYgS6ssFeVpZNA5"
    "KH3Y9CKJYWAwKZDHQHH6BG0zQylzDpg/tJko5OeWNUjNGpirwOs4AqH5CYzFchIQBofQ/5zei5bFDJCDtEBrlDdoF0I7xhQ2"
    "DofrCctbYchJvIRTtpQTRQ0n6k95kEDDZjqaCfF6whkc47rBKp/ikgUjn1kVsU13jeb+Ejle+WxiS0Fi9oZWOFLwDcxLnxPq"
    "i4dXHJkxXFaYEzyIu1ksLK2MwDcidWOOF/Q9CuFAw0HBozEi4UfLI5MAFEC58KckWCkfDj2eGZASoF1saMnHE85QI3+SDn86"
    "7PYHvS6wzPMSawKeiZwJ2eAHcUTP9TrIZoD/6t/6F52DbvuEOC9aNgb4O3G8s37nXy/hA/jWMDVheJHmQpa/4K8gARh2Aq0N"
    "+vLw/OAS+WsbGRQ1CoMRwD277+Cjd8AjkSd1zo88mprsHpWm9bb9rgNzgS/ah++AEx7qHgXw8X6XWSp+1L88eKsHqIUS0wLy"
    "+tLK0GSPugewgh/wG2LZtESFWOEJK4N4DUKIR2PU8sqXSiOeEUe2y/JIeTWFK1udk+igJSy53+53+9zKrRPHtRRwhM73T7rH"
    "tB94NnSj8rTdRTWxfXYAI+pfXlyAEOLJS1RkYT0kmrvgKxxaH7dRnJ4f0ipiO/3HY+cvt+RFQPduW57E09gHLRSN267BNV3O"
    "h3EoN4PoKmyVjCxbLltfkPFqe0HNtTSTD+JH4+pI1LWBrDv3p0gdToJh4idLuXnRPdlCwR7HUxjm5f/8l9x9/fqb7b2d3V2k"
    "Pn01AjIrT/xhKtv7jQ+/sg8fARFMgit5AmsxIzoMmgCTVqRdQq8b0DyiLMDfozHQHBgKks4rkHCz5iFBBzvYwfdqAireUj5r"
    "h+rTM3kQ+slVQz8nwZXCVj1Z9Kjp9xj3CSUuGECMzt2Unbvo0j04vTTKKMgM+8tCYfSAgNN/tGKFJJpobZXH4ZfI5hz2XOJ4"
    "nlzGObMV5lH458y/RmbmgwJLg0uzOB6zgnYTEF9DX27B52viAS9AoXJd3M6z6YWCbTdzanErp9aDYw1Ws8GKMi5KLIcZ4go1"
    "EBR8P0nLbNyzfFwMY5o4NHIfDZJbxUbTfEH6IRrLypvhiArAENGOCjyufOSR3xfMnNjuUIk81WLHGISJLCDGC9+SYg4SF5kc"
    "jLEBFWZHwjDSgVlwYZYxXagRigeeFT8WSYCN2qkBEet3DnodoPTt/T4OrkxSLbOA74D7OmSf9K5e57jd0ypqty8cNmjVWXxt"
    "La5BPWvG0Wrg/JVxai1PD7OulRr+LgzLX8ncNYO2f75/2x70z6HrHsyvf3kyMEqoODnv08gvkYOhtRNfBWYCo+6vo+SedY6B"
    "DXWApwirmaLi2z2/7OsXCrX3ToWXFVxx0enBnE+RU9XkEbT9bcOPEG0Yfs0ctvs1dBeGgR+NWCGh4JRTNQ78Fn6hTUdob1LJ"
    "tRpDcz1VOnl43OHk0p1gsoefDEFnAo4ALc7h1hGVIS8hnUoxd2RWj0RFthihiFi/4U02IEGyrcqAMO22ZHlIZLDRYxnFY3gu"
    "TzMt2DeRDGQNfL89vvchqqpo8bPd6UvtjsVqPwmsyV59DNCXswhmDDC7cT5Sv8Yw0AYPTeDXZTKrWQgKCwnoA0DfA/Se2IU2"
    "PADfdudAIqVzlEqGrv0PdALr1iG8w3TetQAmjMCGX+AlK2xfDVTBoRtWBBUPEkFdYiJW28RgWobAdQ5XmcOqs9SEpEnvMMSn"
    "pm4IV8uwqkfnxw5Mpt37sFrzkJvFkogmqRz25OCyR0IqKwX7/UF3cDnoyOPz80Na6H6n96570Ol/VydgnkPBvsPf9y+B+OAG"
    "oWTc611eIM3Zgpm/R4IoDtqXqJDg6pJATufgvEf6SLO9r6B+KJYfDFyz4DmTP2eODoksWQO3LFnsngnWWz7crYwZ7eo+epSm"
    "l/u988FJt04yd157JDvSvy9RTv1aq9RyP4mzMEBPO+rVrSfPwt+zZ0E45qO/R8/C36VrobR/Di35qXuxp/96nB9tf16wccCT"
    "G8PPwWJvw2PJoiAKodbNN+AX8wjRDbhrVcUlcQ/95sEWKuJfI4F7Lb/PUUaUwEkUHNQx7C4Ih+JJOFxTOESqwrEQskbFaQCs"
    "AkogKygjwnoih/iONHn8Xo9CUqOFkn8D/IZlSRNoYZvF+zehh3JtN8c2CncF7I1kYTTDAyH90VUU34RqPMUTIfVi6CdIMixx"
    "l5s4D8c4YtCIE6XPGqwwsjkcqDFfw/RfoiKBkVBjs+6g3qa0cDR1aGQB04rCJQinyZVCngbUcjTjg+pOv7ZC+OhQsdWkaRGE"
    "+IoX3+jhjtaNlnHdKGnewBdUNAa+rUjrTuI5LC72rBcB7d9JcI0m+YRYjruJVX1bq9la6aZWXI37TrlaK7UfPxLVf/asKj2L"
    "taXnVQZcsbb0vJLui6r0LG+z1teJu6jb5O8rJIsGIVneS0gWdSFZri8ki0YhWa4nJItbhGR5q5As1hCS5e1CsrhLSJa3Csma"
    "ITA78OTPKf3yR380b8XJVBCreWF4jrnxcre10/oW7+HuS2QpSxShXz8uW9Qc97D9bvfQFd7Z4vstsTNPvgMuEp+AuEBmS/96"
    "d2y9YX/FVg/5iIytxNWQQP0+Vg8zDDZdPMjqUTd5YGPrWj1+BZOHdEwe4kEmj1+RaKPJQ9xp8nBmef7+7C6Lh2i0eMiHWjzE"
    "g4n5r2HxcIi5eKDFo4GYi/tZPH5dYq5p5lGv0xl8uOjssRp8lCg1WC6UlHtw9UAoxCwVSnZJZSmg4CZOriR7jPwIRSojU4lQ"
    "TUHRWFrxCIROKzIZ7xmKDSAWJ+hBQyFs7l8pTQsWmPsD4mee+sNQ4ZfQwLUPBGLu/wzSXkZhESCXXaswRpsAEF3leqEC6FL7"
    "5m5iMc+znIajPoGWnoIsR+66bU019Xg4cgV6nysfTQxIkJ+DIP2cqdloFqOvSj6PI/XciJTQun29CJMQQxjWDalkaM7BqAbg"
    "LejKa/KxYfRDxD7BYun3yJDA4R8whsQsSaplVBJMW+jd3JalPTsxxhXYOvQiBybyAtZRfgRqmb44Gpy0Bj8OPsKizTgXiZyk"
    "aTAPQj8xdpJCqt7vH9pAnOe4o88laQ6OuwqIMuw7NUPrBkwAA2tID0H5uggekvAfZgh2yHpqEseKc6Vm9ByfpRUNhDVQ3Htg"
    "cCFzRjNJO0qcbYuaGcwKdy2e3zQPMpb5rXTPizCOo2eZ1pmUPD67lMcYlu2H1MwFWa3M4rbYq3zGShhM13Aw7oZjwuYLGK85"
    "vaZN06hukJrRjVpZ6aVHChXeJ/PRnrPTkhuyLdnBFS1J+yJcYTgJ+ihI7SnQx+D44uR6jw6ClJt41GSI3NJ5GW41XWnWkzD1"
    "It6ig2W3CG0QsEO8hPAAOp6X9DzPWUInLb1SdqngVziC0py7IHIWi7gzjUyOc1o78oDro0bhU/qw6Tgz66zHEe4fHtHlujg4"
    "ghOCSltCWwE9UsN+sUfFaefwMHOj5Y86wUjqVCQYPocSyKZNZamGqIylA5upUtoM+zFNRi+G48mLXqd9eNr5yNSSPl2M7Kdb"
    "GP6CXlxQVsUsDscp7VmivTrSiHdSsoQndetSt++n6sUEZpHOWqOPLAKJj9oi+QKNzRlcsxcUFQr32Tw6+/idpJCrG8xWWvhJ"
    "ZtYAl5FXD63FGMuFiQX2vho1Xu/AFCR9ibbfPCTqzwEZ8jMoAXa5aUl4tPj4C/wSBrDFJ0dkcVy/NMXyulRWd+osL8jv8STI"
    "YFrbsyEugF3i8jezj3RYUCzGVRSZj3lKfjiPgboXcXxayVeYPZdM9vPPn5l4fpwNtydZazQCuqkPPE6Wwt+enYdjjPp4Jq1t"
    "+x5zkaeHr4C9qNFVms+liTCASxmjbYTvHp2GsRrmU4q8gTkY7odXQgzzAE7NFkcmsgWHicI4nsOEW4+rajVlv5WY0IWm6Ccg"
    "iYGc1/jC/bswP3s7O19vf+9H23vfND9YKH/akLmz59FbcrgUbs4haARykCdASD3ZizG3Ci5/OFPhnG1Q7zGtKpEnag7fTQXm"
    "mgG1Ib6B2kY5QKqyBnYRYE8KyYQYskxh65B2Y9gvSiMLf3TlT1X6ncC7bi1Wc7JV6UPrcYgICw3mTNneSE5jMQ1Vqms/CeIc"
    "/SRxyPJGQSi1zIEHOFFwwFApxdMFf/jI0GJPO4Wr29niOSIlNPcaozXRz2HiifW91PyGwmWQMZj50aoKaVkuMTk5wTdtJFUA"
    "uttNZEUGV1wc2NhUHJ4/mZBABC/lqeErdvVLkqunv84wt9DyLVyomsecxFCaBQyWNXLYq6UMFYifDSsAk8Ek3CBKFxS2iy5B"
    "7gzEJuS9bWRcGUbi8D50v8d8380uzHdB2WeZ/P6icwysMonzxZYlDl7BVUOYxghYAMbNEllPWdel9pDXojBMTsWSoRdpEGjK"
    "I/Q80bP4CIvgRvjBRsLgChe3nZK/Ebr+Uw7dwZoh50XqIRcx8A4WtZBXvuFbF8P10GITGk2DVBWR0o6BFDN4W/JtfINnnuR0"
    "ikMbKn0TiS1hrvrYhFBfYe41TAmIHdoQgBZCA5sfYZmD9FlJbd8yI/kAciZJK3ktWBwp5w2MC7sneRQ2DLPHcV7A81Cg1iOZ"
    "5BgRHydzz+otMyARHHW18JEU4zh0wPY2ruYz+Ax2pTQOY19eJCpTJiasZLZ3hlcy15sVyfhCEvnXY5zQp9Z8z74f6yZwrPim"
    "ESQjFFZNL7EOUTntzsg4bFDzGh0SIp3rhAwT5z6CIw7H4hlN+D2eN233JvXKeGn5YBZnlu+DPbkkaxnzU2o9vSShOXYz6drN"
    "Up68c6ILJYhHYkxDfGGgSfS2E20aAd9NcBtZfq5xKU2U/BTYr4KtgyvoD4MQtUymiaQvNDE4VKGhQdSSwiWMcE5i9ELFC9S2"
    "MHGDLqhm3z7eO8x4TjRHn5svoBFe2ReOgYt963rWCx2qpa1XhbbRotkjCRTukmvFy+gzbpTnJ32BNzY2WLcpOaVLcQYlx+D/"
    "/Jf8pyUIg/9SWgpuQq/k5s3NTcsInGgP3tLqWs2uqvvHrHykrBiyugh9mKDuwlrprv0wV4VQVhVCcaK4dyOt4bNiIE7Q/iAH"
    "qG2LEpPewWTzSRBph2Fd7BjMgAxP6fy5y6w5COvvHzU/e+bJj9Uj8cwzhLn4yvD5Z5K2X1rtAQQB1jy0PG9U7hDFFFdoMIEm"
    "Nq1Gbpall5r4og91WYLZQr8ZttMwbFT0SB1Alxk52PxwMfNxOkPQtfFiTsgcAHcCd4x44UcgeHpWqZ2VXjJOb9FBLWzeML5F"
    "7NHTWR/QCH35DAUlX1IyNAiuuNJOGApeAbiS2uGnm3iWas1IaMUIOfGNgvPm48ZFVyQqZ7TedN3gBn7U1PMZDu6j+qRGeYZG"
    "pmcty9r1E6Ty2ftKNij44KOlv1JPqiR4CCNyPFtfWiptdBDJkk/TlcPMZnlSOkvDTVkVERcCHiBrPHXGB6Hi8zdpXWwnvwlI"
    "Jc6I1hVj0FYj/DMgWcEMCmPLmTpzotKclqYi5ZY8s/oG4CJrfkdySB6leUL5P2Su1zHRPnG9YJSjgs6DIO3wmpzJJMOX76bl"
    "gyQrj9COg2uMZH+ypGdbt8rnjdEPOzt07Ur3TMg19IRmmofGR7WAyRHXY7aJs0FTYYv8OmcgUTHbWjYRprcdaQy1aMX+HgOb"
    "S34K7TO2gULVSCFoRMcKdclg3eCe8GSTU8K1wQvpRg1hyzVvhCR/hHVIkEdCtqXjk0Cyz16Jiu/4fffkhEze50fVfK+a+wUa"
    "KZwRRfyl9gtr471x3ui4HfapnJmRDs6hEfIP6P6qC9zk7BKN6mpFK6BYv5R4PkjA4fgmwFvpio4eiUsLhYzLXNIASM11PCKj"
    "N59HWcqC1NF2kskWhtiphAVWpo+k+8FYgZWiOMJReSRboGbHcQxAAFDUI7kcZdaJ595cM5IiTK+iWFlWj1SBkikcP6iMOdSO"
    "7Css4qRbmh06neu+8corUl1ICCLRiTNCvuNXsljIIvGRSRVTT1gAkAKJaJG6nDARNDY8ffV0wCU0gj2hCr1eLCDL8hXPLw7U"
    "dbNW/Kzu7iPF0hL05kdtbX+2BcTO53iY73iyRpkH2XYMPFULYQmGhUYI50XTl7LMDwzTMCE0JtfSSbZEJWFE9qcIE4t0I1Ur"
    "OgvDBeWTNh1Wi+dEnvWIPd1I4yjIRLywdA4PBu1GEdJZsGlpjJetFcvc5EjWvlu8TI58zPk8WttB1pW6JmY3QRsNpGOj8JlD"
    "Qs4r/r2q7QwUaVeWDZYGWFvI9wRKZPaqJoIvQJIEzfSyd1Iz2tyoISfDWhWtaa/QHIMiKR+yIEWFG4GH/CxOloavpcr1KDlJ"
    "3njQ7FqUApnw0vHKkDEha9BvPA6/+hk3Ab93uT5toqyor6hl4sIyS67ppqRBF7YAULUo34tykDEczA/wshKZ0wFkhY+pgSWe"
    "qYDEhjKFMiJy2eqFn0SxtgBw2C4POatEienIgQll5hlt03O9XV4RJ0Z5/cLSrfSOeLByMBgdnTSfwl3HlUanjzaJ6Sg6z9HQ"
    "ycwTEakDxThRxdEtiNhilvhkf48dRaOs0mkXWy1sAimo488rAifeNOoKzocdFneRQhQf6ujTZ7RUxceHzkViAbmtnYRsf8C5"
    "p8E0YitESfuyIiOZDG2WPLOIEUlWIKTigbTHi4TSrFHmq7qyRTFjj+0ulf6ZQ/HRwG2gcwWSJo7UyaPRZ88z/J9Om42Xtwzc"
    "DYhnoyPnUsIE+DrD9sUJifFLadJFHTJEf2IoI71mNStXC7E3GIdgeEMRQapzQykiGP/PK4i3wqq5QlqLQGj9nl+15AHL2CXl"
    "WZhhs5HwBr35rK5hWE/q2lHMGC2fNfaCP0ZxNI1yCiPTdBDOyyhP8UhPtbcz1+mipEoZ8AMYpmnVw03XKqA162W5Tpog0x8q"
    "t4bzWme3CZcuZbPSNeVGgMrZIxjGMWmWRCO0t8YjHkSAaG48kwwm2kKBP3jIkXqzeRxIMzzI1kVQJRZ6p+pRTa3qSm2T6+fW"
    "9Rrm05RvAC0G/mKCOLQbEL8eK7xtcBnSXKWGx1vSVViidcarJ1U2otGcAwmZoeRF7Astr0NlppXxaExeetUkxFEnGHJL+8bS"
    "kdSR7a5IZqQp19NvGHjVrwqH6ePHj8Kgfz3nn1IOzwHl8OySN4jzy9Gglo5i+RMcJl+e+QlIYWHwSMk7gpN35EOTd0RT8o68"
    "X/KOuDV5R66VvCPWSN6RtyfviPWSd+TtyTviV0veERVYsN88eUc0KeL3S94R1eQd+aDknbthV9bI3RErcnfkfXJ3xF25O3dm"
    "SYv7wIK5uTtAOSpGcaXDIfBm+mgx8iQQH4xhGHH873jSmm29cekN2Y8OQAkjdl2APCESgAeS6408VZ8CoD59VF3kZUTBKkG2"
    "LLexa73Xu7u/NsmSvvgiklXKNxQPI1kN+YbiviRrVb6hWJ9k3ZJvKNYnWU/5hr9PvqHgQObTi0sCcIBxdtrQFQJIIAE467yH"
    "vn/sHpzL/qA9AMJw1n0HlAwtgr8OMePI3y8hZm4iorgPMRMH7LItZCKyVGp6Zo0jcUT26TDEeASEqJYnCg928ixF6mbkY+uu"
    "FhN00qPxjWXYaRxro3/ROMqz6YwSxkBbHvpDNEnM/OhKzoI5av+ZmMNRRMHtvqKfEzy3tui38yT1PUl9T1Lfk9S3LqH8Ac2L"
    "8gJ9/cnYybkF4mNInI2x/xENEN9+jdZNOHVkW0Z3NqMjYlyvzII5v25DZmzImX4Gg0aw0pIqKIM28mE8M5rDfTRwXUbjOB8C"
    "FcGQk6xMzG0YGll4Z3oomsbqbI+37d7R/uVPP8FvJsC1GdIsjbcxrgc+29DxrRtO1Mmhps18OVviCI2iJljJtkzyMhlNyu0D"
    "1Zkgem5WpE9giHABJiqYKKJlNqXjh0eAAgqHY5jhKIvJu80hTtoaNMSo/1rq3w6I0Ht7Uh7H8RQB3akGRvUhxJ3b25GyA2wO"
    "uJPcX/pTIDm15157/NyRP1LDOL5a0dyeh21KeRp/DsLQdytJVB/dxXjVMbFRYLpIstW4+tDOtx6h1smz+Crw3bIWLk4ckq1g"
    "HACb3tyGtdmqtfJaSj7TfaTtoVo2DeYUXe9YySKl8GgsntI90SUGNJBtreFvJBcPQ694Wp/jzisPo29p6fCfXfwHl2jvpZT7"
    "ajb2x7KTTvzZMK5P/St89xtPL8LOa1oJ/OdlrakeHK+3fta0J7uvX2MK6M6rcthvU5RvdU2+Bpln6oew7v3WSW2r8WSd+hls"
    "n58ihmCq6lv8LY0UFh9YDw4xTqNl40P2eLXH8ZCPau05Qp55hSEG6pMKQFEdZypUn2dRcBVfC7qGFMhYh7nF4E4ssYJ3u4ra"
    "a8PGObIJ6eHtApERMmroti6an8mJqODcpt4KKaQBS1A8FPXXZtSKW2WEUmzcDcZ5JjAVfzFLC9C/koZVkexWQtXWsKOaMWop"
    "jfI3wqgl5t8AU4tDFxqKtjbst+1+EyRtU2KhKEHS1lpqhKLtV7Fo5R2oV/cCArtTpWzJsnZlZTiE6b08w2F3++JWBNrGFasC"
    "z4oHAs/KKvCsZuInB6f9PQQnzTKQGuCPClyVpndAS4ie479IwPxprpLHhaeSjwpPJR8Tnko+GjyVfBR4KvnXUvji9zQXyccy"
    "F8lHLHwhHwedSj4qOpV81MIXDehUJ9399rvuUdlsjaBPsZKHwAbjv2oo0F8PFON3RsR4PDiMvwIsDPFg+M8q1xf3hv98PCyM"
    "u+A/xUr4z98B2ciCYYiHIBv9avCfLgDSw+A/V4BhiHXhP28Hw9h+1B/QxFDSeSPRXB0P89boCZToCZToCZToCZToCZTod6HD"
    "cJ+T8X+ghXr5IhiNfl6o6YvnmNDPKJQYx4rqIFOze2Q2y819hL/kKGjyiqKyTPF3BP/I6Y2hoqQkjIT+hy2kVSZjeY2EZQxa"
    "hH7wDR4UBcsWOckYKL0y8XidvGPMkUPFUBSgLl5jbrGTVdwYSGxD8uGrZ9cGXxPIWvf7Y84hpgUndChFhVHcUmEEAAW332qQ"
    "aDU0mJ+aUemIb/UJPyYFFj0mAWYoEA2FTxdWm3bmy9nsf8p9TOv1MN41T/wRGwMw3yLTGb8Y6SsmQRZh62RbdHPRtJGxpdN9"
    "3BwDS8qtQoyMAtbBE9gzrETimRRjXBGs/oZlx4L0ipIyY3eAJiaXxti6reScSVjDOKHdl0CeZ/EcmjtuyRMfcQ+O82Acy3fA"
    "q4YKDSYtkih6LFH0aqlpDYlpt9mKHmLG3UQ/kTE06BSgrboZ16kHU7WRpEq4tpHN3S08y/S2k9/hSh8TqrtSWUMnXVFDddFA"
    "OayAsw5Nko0xn3hO/nWxBVRGLd7WKedLLUSIUroPU4WmjB+vnPJTTvYha5mo5vqsTPWpxg1v7tHSUEB7kerKa7JiBVQ5d6h8"
    "vWkglGvDxGWjtqiVVJvITbUhX2gN94JgLzZgrFgLqzhruGUa2qLWiTl9NK+AtxsvmA5jRxh4FJuBFMD6BjqV35ww9D+mQaIX"
    "wsJdpN85GMGpbgnrh1luSS2M/TkCmeCwDFQFo/iUE3BK+Tcr029s6I1LIj1RpNzE1aybahgOL1Ep6QZThShyopJ3U73JKMaY"
    "hZzoukR6wXHQOBxejGepzo9JpD4Y9Le4rWIRxfvr2Pby9jnwdaX1EJS8MWiqYejmYNOWA53aWH2WnhXEBo6VeK/KIBXaVItX"
    "ssjVciZfsWVzvvwQK2ziEW4AoKi6nBz4iaWkivYGTYK0BNKbBHMCU5PRtCWvCYkaLXTIGC+j4BOeqkkwzbW7FxEGgVJvmE/V"
    "BuHPaJ1GKxIIENfOsxgfaoluJcVZd4kBC4VxunBQGzRv9AKETj1L9q4bmDLJMGUT63o2VbH0CFO5yUNsTXNgpZ6eRgsouSfC"
    "jECp0hnBQ+isGgN7xe+jjR8ITRhuo4W+Ov4fMQklxQ7zudDjxRy8FYOmUeOBLmnNqBMqJqfaOE50kZKnfE6LQeemkscgwOqc"
    "xQHc6Os4wKOTAcXmUI1Ce4MNS5epPPnpPdC/DEt90svYHi2NnuLMT8VQAblN1DzGCwCMIp5SCrxn9Ut8kfpP8HlJz6ck7BAl"
    "sAiGSmzkhKCHAhF8Ae+lG+YqZQoLEAOFA86gGKHdQILgIP1wimiaszkRPwEt5CFtop0yx26gHyih2D14PcccKVx0Lpvqj4mU"
    "DhnkklKK/GQssIWxwhWlgijvlX7c5m05fITyRTZwk47R8xqMUo43YK4IZxMjX9CrpYv9FXYUWAIsjoZOKF3ob77I+yjUoO9c"
    "h0koLFsA49lM51sMMoFPoH+EAh3XbWPjV1NNdJLii+n4ansRfBrmkxfPy0b5vR3Zmc/9KFehPA5CYJRLkOmfzPNP5vkn8/yT"
    "ef7JPP9w2gt3MAGG/h8/R8ELEIfHobp5Lm7Hn6Sf9sIfzSzc8m3Pv7Mgvjue/B5oOBIdDGxb+RKmTurMSZ+6wbzJFyZQ8gWN"
    "Dg7Bqb3Wh10KD6ELRUeo14Gzc3hp6kq6tZHhE2pgt4SE1TJT3tAz2tDBAwiG7UBfVaCrtZbmWdJJ/EI3Vc2lRWF6jF2y3NtX"
    "I25kF9on0C352grghlBWxxUntYEVFDq+iRhECI0raEUpaqZb4M+mN3RSF6tDBtKpjPWMAyBMsQ41XRtEHjnVWP0RtWJGoasu"
    "aQQNtl/hV4FKTSVaRBUNTSUm+iOkQZNxAD/lqFnUPtihIKV50HAJLHFPHbZQYNIYsBqVwK6q3XCzRxu6lQ2Ner4ZbPGr8Q0K"
    "oxxqS2a2iH+nSJ2Rr6VIg1dBX9EKICOLQKUiwRi5PAKA8sA8i/M0XNoE+gJ+0SJR0aQ3AxgJbU86CxaMkTbhWrgjbHrz1c4/"
    "bnEOvAuGQA3lGYmhJHLPYPVS0yI0OVQRLAIpcKXWnXEWW/4hzjfIYIW/JRtb7q77kRtEGWP8aHE+DBgIw9QQNoNVvgv7xZCx"
    "qepHrU+i0QaLJpWTVkAI0rcTWnHKRy/jJVp4TRMqZUDFQ44xJhHcqH+OLObVvVcWgdoz99/RSF00Fxj6OVnq6kNHswF9VigZ"
    "ZAaZK5TyUTc3FxQWJ+Vgd32g6JPQBsSD+M6jZeSj0gR1G5VpanCksQtP5GlIgVqEmku9YKa2ZhUaH1hQwyK5EtPZnWm/j5Or"
    "GlEwEDPaqAQnrbgCIBDqadgLwEunpzX3EfDm2g9CUq+KqHwL8I94qNYQiOqXpQuVADFD3twgMCQrWYa8ZWzMTDhag1rkYzqY"
    "zkhwBFItxbYXaHUJPrGNeKtYhcMC4wkXJN2ongA2UzWtgZ69wWygNTADt3YyvIqu0YhpFXbF+LbkOUHQ3IIYYE5HjHI1HLzr"
    "IGWLK1WrMLiiClZYR9MzodDb7N4m3Zj1RtDq+xjkF9KlKCy29T2v02NDpyal6w+CX2X59OrhadZ7p6GzaGEShVYUcz8VBi7j"
    "ScF1oWmA2oG2EMRBpIUbom9qyMa7LbPphAYx8UfEJDyHR9pFrQ1K2+yLXT9wkKUbd7x6B4pUtQZ8KwPsqXmpHQc2VtoTxqwx"
    "pf90SzGvDb0F368avOdcCrTTUFpDaMh2mg+1qgvtGbmDbV0Ww1ZfBepIW9QqYoWFzKLLeRu3cAUVpMrUPZ73oYLFnBjDRKPw"
    "sh63lxt2Thu6Leb3lizDSyqEC5jEEWJVExx+SOfIRPij8JFHJm8Jb4G76KpYKG0TdF1318iDb2NFlna5fWBSqh1TGVHGK5kP"
    "jCiUUsWG1CXhhG2CLGREPFI/UeQlsbRiZS130T2HjJROgbPauG5jRl2hkGjscU70UouR74niFayJStAYSFNnruY8oktiEYzy"
    "OE+LwoiGKKF0ZEQugm4xTiDcI1rYxpNIBvMzAtZ072pro36FK/K1nba5gXeKPO4CchB0udPCmAkioyJKDoN2+ykuIftmMjbR"
    "WkMcCbzO9WNCtNdC4yHLnIXlzEhWsl+Osm5UZpxr5lJlBVxSOgtU8oGSXIDOd79AczTHzwF+jOJo2xYfwj+3TXB9GRLSAYCs"
    "cXMHBdIaqtD3gJRf1SldQc7ZLcNmcUaGtJ9Y/MhK3HvZfWvGYmkxCcu1HhvYOdEW3qCXzgZdkHH8f8HubDqe88y3wLfoQWKF"
    "aEs7AtzdwzgHj4M4UMozAyI9Osa0SGICKgTyy/8CRSGIKVyRAq+XBWUtFRKZMTOjAA3aoyryMLnPaJWRdumhabcUP+tMDlaR"
    "GnFX19LNCG5vmvpJQLdzgvjq1p0VGN7nXvzNdAvUYA1hRwrgHA2wTpprkFRfMBMydlA6gJRcgUJeeXC6ixsqIqt5XQvdpB8s"
    "/ha6lIIMz7TdlCyY6jzKqY9fE5HTivtmwbCsbJ3EabrNOPPkD83JT0F/EzZ/6N9giSmcaqimzAS0kfx9IV9TXEmJKt5G4Ign"
    "8MBTrWoX7TgAh0szLbMfc5JUybHP0RHuSTQikxPK8cEAw5XumGZ5Rqpi7oBXFHfPnBW/QMpBr44+fHZ10Z+IGhiTgq+q5vgi"
    "fqkwwVeoUCkBx6VHt0h5pqAEamz5vO7k0IJQucyAzwndjZSs6uotjtZcqewuSFnUq7Z4puhtmOJ4qcQb6RtYTRmmGGVpSfS1"
    "2iHhu1UnWknB0jtGASe2z6HTJxtuClHaAHmyUSfBI4QBbxGeE5026nSPJM4eaQpgIwfd2FaYS8s9j5ye2bnjFfldVoU3EQfV"
    "yTkd2w7dVC3fTXL1rMMVyOJYodzkOcIEHdGsuG4mJdbWFaiMp0pSy5IbU0/TBg1OA3eiI5F8WLEbj1SaSZ1VlxdtTCE7dv+1"
    "4odbvXF2PugedDaohgMHKKHrX8c8MUK7+XFvl0MCGm5KbWVt5W3pWpAQfdc6e4tDpxqXVZcsUu7ya6JGlIEnQlPw1llXp5nm"
    "FW5cV66YlHHpHkTtdJrRrzjYqVh9In1jhumbMRZr7URLuacqvXUM37nEvHTI3HtdwfsNJgWdQZY5LThgvf048eqr7BtZz7Fy"
    "ad2gYZUmlZtCAsQ1xWSQLSVIxtsUOGv3JkL7HEbTcI4011rHXUf6VV9mZ7+lCXEFJmWMfBhMY5VXCvApDUffLY2R6trmLdvw"
    "x2P8nUtHOSfSacUMXa/QOjfB49VPg3Hp6JA+RQUwxyoa53MjtpZOjCEsrP+Z7azSNFpgY8TAMglNl4lrqw45XC1L8ur5K1Bg"
    "m/wWjUtUaBUktpKxngWAiuHL2QpsxCJxF0OOG8A8GiX4wrTX4DLiZspw6/XReE6xJh3O16yKuNY5e5WoPezaseYVA6h5q0pc"
    "2ErdXItHn6OSWcZqKhVNoLQhr0jZMWF4pKs6Zdla8pLLcuCmOUVTOVSmcJBY+8ayKkU6xizHjLXSdFVI+h8YrbxkyLHpw4X1"
    "+T6qmQnhdSNf/VA3waLr2Hgf+f2zOMOXrPfGhmEQWhgBjTGSvx5ammPGtRqrAgzZ2RLdEUsXbCDNVKESWcCKpb4hpJHp0gpj"
    "V/WwC5KoqZ/oUK6K7qF9AV8DKTQCSNriICwjR9sQLBK53XRtp1ITiS/GjYHgN45Eg1YvHbmk/yyiKTVSjj60ZsReYXXSaqqN"
    "wJrQfPwU9gRZOm0pMP54ju5pHS6kKxrrrSjVAKjZZ81tMvumuUEDC+CV+qZFcMU6PgaeMrVP7CWwQx0uHYQfVLEKMkC7SMpL"
    "YQXzig3Tdz8thrpJgZ/+aFZVUd2n0XxZ2twtSXFUFQgIo4aUM9+7HZ1Gbt3ypUz4WgaDUU51HkNhJvUa0A08NqoX1c1K96hw"
    "LAy6g5OOh9nv2276u1fPoocGSvE4uo0mqIwPGgA7BboaLosA65A5+lixVlg+LrBzSbxIEAuCkipgcLkJGE6Ui2lesfdzrgRM"
    "15DrICXKboEl6G4SUbflQKBx19FaV2b57H3bYqQla304MTG6LaxJHsUSxB8NZcNtYFU4MnbCGEHTdkwtxpOVYWSnYzKI1DQM"
    "phhavuVZb7dXMuVay8+d532TBQW06YfBkAQ6GtwU7RHWb2G6xJydLCXvePP9YOpZYh9olDFbhhHLXLcWd9wJe3dt+Pi2CQko"
    "ggMo1LowssHjAYZna1eCjbcnuIlKLD3a3BBRHwMe2GeOXNzyaoIuqii6tJq5pTE5fxJEJuC6oKuuxWDzVp+4GRVOO4z5wCK6"
    "JVatdGyHV8CU4wXCn3PxnRwHPvGDMOcgdxCPJ3lUCDfEBBsiQZyAcrse3LFK4eDgOUQBvWqIs4jy2pjuj68DcpJOdPhGahMf"
    "THCDbp5vwOuWbFOKA67CeydavV0waudSvJ+h6F6+rlVn4a3uNiOFjmZxzFZQsnSWnO1kcwW5DUuCwOp7OgmD6h7SJDTSvgmu"
    "p3On5hGGlhQGMV7WIug+HobaCpWaNFwdMYunEebjRHAHacndo5y6pZxpoxeM1tNpuJgfRbREoeMNsTK3douQEVd/jIS0kqdC"
    "kk7hRSkoemEpco6BtgnrPBiiz3jh+b7T2kzs2ozVBNQVfgOj9xtM534yD23iW7QsVrG4znmSFN4yk9AAhzWhugpsRPXqduPh"
    "UgsbxYQofbBYUyvMu7kTjthox8IHuHPGYYMNYXD0ffviAh7p/vgGt5CsBZySQ+ELbugefrc0KTRWaxqs+YKnwyjK1gQjVsdw"
    "a5IFlVU2EcxWk58ECjMogEHAZWeiP0QvpYKTufFv/75RKClomdDcbmkOE1FVrfU5mnRLbh5Siqg22jh31DT+D1tc+onUVA3P"
    "O1TFOEwEdsG2Hd8s3pV0CfT8k3WEklJvwCl1LSQ0ZtLTJiXGqfykz02qs4pI7VKc9KGZsXGturhFnCRlXIP44gYMjgzXSIM3"
    "TKJOLfgFhwkHL7D+eL1yxu9qzTOFkUPXKtSUsnAm/tsSfv5d/pupFlTxsv47PX5Sx9EsHx/PDQjVQFgm5nLrO508a3N5bXow"
    "LZ0W4xtLwjqav6P1M1pXyU5cHGRTquPukFNdyH0bhkyvrCOhr5I9dMyZkOWKkbUIp2rh9FUS+BeK30bwpmXrK1UagjnkRU0U"
    "P5rmmDE2xWqUUTWyT1tLCnk9rc/rt0lxBzFxmV9X80h2d+nunwTDD/m1rYbU5ticv/p0EsHpJFI+/8J8ElEYBL0HAX20mkdx"
    "76SSLx6I1BFgteSStSFHRNVdoOfmFlczFI8hdKmOmvlY1yZPy5XWgPRQu0ODARBLymxMVVE7TTUngpYTMIUxwqxbVO0RcmOE"
    "g5jysNwY8WDASlcXF6tyY+Q9cmPEXbkxcq3cGHEfyJSm3BjxUMiUUm6M+DLIFJ0bI/5qIFMeKTemwPPDNOgnBJMnBJO/TQST"
    "vZ0nBJMnBJMnBJMnBJMnBJO/eQQTK5Oc/HTaFuLHn+RlhgVDWA3Gq/nPtR+2RxzWi4PY41jEGjh1C5B76cIF8q3SWgMhPXBe"
    "KYyU3JoUkh4UcbFOu/y5LWBibcG6XbmJroLRTI2umusnQBNDjHtM1D9s2Xi/bTzu4ee5z5kmOnEAjxjQOcJAKZ789NmD/4/V"
    "iLkPvgV/kNWN/sbarVkc62pYpcZEESmDjRp/EsLATFUWL7L/oCCimT/Ww7QJcbrlKyekBN63wSswemmqrSw5yMdt0FBhMnHY"
    "BrDbk+OLk+u91u4fnAkSdIwGh4FhTEEw8mg7ecLXgbqRDo4JLysJiujhsM37Y3+RGRI0/Yz5VUy8TNtaXQ6qkp3RJtnjhkYZ"
    "HCkN1B1mW9dALr9c4DcUC6IrN6dZOSpVSnvUrcLahIGPPnQSBZ16NsUsq3tcPzADnRYJazHHUOypStd6DYlBHoRjnQtjgvXS"
    "8hs8SN4afcINUosZX3URkVSYv17+oSXPKNh7wgKPbgSl+nzhHjYiTmg0QW/2ULFXLggzd8gqNdedNhf/5LNnUtOxxrTdFy2+"
    "KdBgpoUxHjY9QyIWFMVO6BF3P9dbPfUpS3znNfJr8SLesYaiFPxVrOE1zD7OGXOpoNyGSOnujb41juvKletWMHtV3B0YFapH"
    "OsuqPj3Dikn3K8+AFJ2QAr9A3EAnw4j9SRmqOjof+ZoGjzoOyiEcfGXCbIhB2x5S2IKQ+rFDCYHAlq3pTX0WReKBBmLSFtuX"
    "Qv9myQBDhMmQGniibLVyg2mz6UY5OskwO92OHiyZzDHLijgvetXnGO+fso/CXSUW0ZEgmavPHCgyrqKFqcZeiDQc8EDDrGqk"
    "zsCZB8Uh4lBtKu1dZ5kxyPTEFnB1Mj9ZciJL6QxtFalnkZ+BpEDv0ovk9tYrbez4zD2JcxYJwJRyjR5wx1hJurs+VLCkQ1zI"
    "Yfxpg93vVNzCIXhvCjyNih5ogpvrCyj/SbsksvzK96OA/BGfPr/4F71HzQUj0allqGCR7Fw2ntINeWNvtK4t1jIs6w0zMGRC"
    "QM502fkL3m7jFri2HpzdWjvUDDdy19uN775c692XvApncaYKuzmKB6CHwYw3NYcHjZ3Ye0KV27dsICieOVp0Pl+BsgHXDEGh"
    "ryKeiMEsx7gPPmwUVhDqLlVr2jICDlt72fZ9gz5FtPL4I0y4CpesgNYJD36INgO2JGgvM0U84NUEuS3ICu4Uxe64nBODzRYc"
    "l3RmV3Ir32kiIaAvpUaJZXMU6FOsE4K+k145ehSmFE00yoS+04Wz1RVyL86OhShsyxzu5hWW2h6zAe1IaxB9V/yA0oMlbBUJ"
    "vSNy3aD+1HCY1vYWyeeyVizoFRfJw1vV3J/xEdXf1kD28PZBnM5hSwcJaOmND+7s2HLWO1/Rv18jbu238jhUUSR7PnLDdPtC"
    "zbCOTqtxpF9vwz/fyHY0xoAC0BXCKfpjmieFz8vjfCk7CZy6PlyOMMICcaRmya/2dKk4hjV02AXGmqBNrs4uCr2o0J890WDN"
    "uyuOj8wKNo5PQHM1Q95dVjxoJMgYgGAskPa7iV+oYTuhbDptq4SexwAoZDCEqaC0VgvHK6yPQ2XiwowdoohXEpWgmxLEQxH7"
    "RiFypQA4E+olNGoBxXJ5zEXwxUjDyljxphiPq/CbAWAFKWjNCnjF0yaOanWclCjHST2G3VBUDLiu3dAERt1qNhQri0M55bAo"
    "vWyXtTM3Nrdkh0BjjM4igDlZmzSa9pY6ic0+w+mMNdu7Y9Sr2eCFTmCtCl4YeaAtAwSTUYg/c05UdG0HopYKw6wEB43hKIrj"
    "Pj2DUIpjtZILrMEeOrDJXmlMpxa8xdgfCeq9yKunXNHRjPfNpj01rpP0jXbSvBLQ/0sd731QjUExbg2yBDHiJ+66HisxMSPQ"
    "pjbt0C9PpeKhXZMr7MpNimMMhgsY+U7rlYXa2m193Xr5aks8WgyC7sMu+W5rp/WNJ7/PYbl3idbveJXezbevPGIipKF/Gcug"
    "2AJRslLyuLZxOF/zRpMh0wksQXMxR/Xra4bxRcLxsbOVRMfMpKUWHcXL3s3CNpQKzBGyCDvGt1+ElsPTmrFqGbkfzIGOXwRo"
    "LpQH/jhQ+Sf6ghlYCya8hCdYFj9FBI9eHoaYlaCxSwsOTB8cg74FJBrdJ74G7PievPYfctPEGBhK35/5sCD+MB+PtSFD+/qJ"
    "PxKMHQxmLvfh4mCZUVPkszJ16x4wUy5W8Y2V25nFAmeyvNQkXzMajT7TRcCbin6OlxpQrNAb9ZGnQCPzeon9NXZFZA0aZVlz"
    "ArcjSw0vMU3ekJKah5NAR0mbaMU6C2YFDd6PlBqnxv5rGgqq8RbIgyd+HmZpAfTL0q8wIe4UygLUL534bF6wLj8N1oBBX67/"
    "j+zANBGjL9qNQZcCEIs+SvulMq8bOlpjo2LN0nqBxpbetsmDwjErVK8P9aZvP4nXJrC5KmaglMIgwORRNiFf/Hi8UDaeyDF8"
    "VKnKTuv1NwWKIla5dIkKXfFTjN+T6EpkmlOnKqYY8M4tRKRs2tdXHnq/Dw2RZRoi6jSEG7ydhkiXhog1aMgAqB76TvkaN82Q"
    "vnmPpGEur4Eto2AcXDWt9revkUiDZIiSdLHUPO5Tn7bgmxVr3Cip1xe3WItvv/XEQxfXIdDCbfA+i2sItLhlcb+PZ5HcRxmG"
    "ScgP6hru1D5cRcUcvO8DlczTmdKB/qf+NMpT+TYO59NE27GPEzWVvViF8SS1WzbwI0SNarqt2rTt3tbbbpoo0LlLN00HmJko"
    "xPpuv7J7+srda1xG58p9vWK/11e3VkJWlV3SFpFmo2lDNkRQ4IlqL1exx6nirPhiq/UGlo8j+5twLbnu+djX8Ce1WdCnF0C7"
    "8ZN5MOYPBsAT36spbdxq5bmkUXJ0BfOn0jUWbeO6hbmXl8wedtc3F6BtWWueJFKKh+meeOIruienFUzKGmihpdxz8DpoBHOo"
    "rCeRXNHV9CHh5guZVCL0+8O8yMC5KofI0/47jDvUqULWNmS9oit2p0k5FLcn0TxmUIkDvHlv/dCElYgH64eVkNlG1aeiW62p"
    "VFmdygI4rK9T4ah+a42qeqDlLQe6wR3P0Vt2Y+5yzhfr7jOKy3wRI+qKIPw/W0zDHFonyUJH/1d9+KWAClHrpaKJV9Twsi5N"
    "+jVp3qKseZcMnoPuUalyMDOBb79lpo9c8ASkUmSTNUaxq5+BqwW32RZ9MNzhopoYXb1IJYQGlFoVmbYqNcgpaq3ieC1fpoab"
    "W9pEi9pAcq+BRm6uC5DeVoebUTIwVtuv1RIvlU2nqJMaIi19RYDIbtS1cNaYnqiup3tLch3UxDFcbsyLWBXz4gzNrIqbCuGV"
    "o7CFM2uY2V1ju6Ok+LYJv761qrjQgdmeja8uV9MuInRNMxSE3Dao6B+E22w1GhvauqtQAQaD1sKv++1TedI5OjrhqOs+tHZw"
    "fiaPe+2Lt92DpmKVNrbaLUZgwrBXR1mXlsIEcevv3r9tD/rnFP4MK3R5MjBVxeulBpxoak+YIGj4DMOrbg9C5s68xqoDwgmZ"
    "NmHQd9Yz1/XLLzo9WJrT9tlBPUC6RIPed/YvRM1ktAtKn2O9eMpqecpqecpqecpqecpq+ZvNavlw+e4pj/GJ4j9R/CeK/0Tx"
    "//dT/POLzhknMj7HuJ5BCdfBAmy7OTtkRFpZMmUPEZtzctY9l/v9wwKKwUYJcq5Yc/aGE4QRa1ISoL/1udR4EYyGZ7FOmPO4"
    "WEkaedl8welWbCXjz7Ax7NGYIZrs9fJ5Y0jVHrrDv/Kw9ihZ5hAr2Qc6E3LZT2CScX5NMYGXBydbcI5VOMWyqbe1BQx1olIE"
    "UNtXURxk8tQf/anxjZf6jXaUxRHBaqYjf75QKx/eee3JI5jlKA7S7fMwuA4U4gZd++jnbnjnlYcxqcBrDpM4RKaLdWu7aISV"
    "A+WvnsbOS09+8KMoGF0R4MZolityvzQ8v6ufP/SBpaCnI01VlDZGulGd9T1PHsB+wn6dGfzS8bNORpGsfdjrAHND5eYB3OUt"
    "PdvGBaGG4M5QHD5iez/rFtGFzov4bqNIw189glwDrXy5aGMOMUk38PsXl/3ERr5YwIE2HqP85yOMRbvzdEsPk3IqEg4fgMeo"
    "B/qRZIVndNQerSQoNPZ4VUFpaBWh4c7KoOfvzxqFBmzsPnLDitqgdKvXFR1uKQ+K7awvPdxeIZRWfT0B4q4ioXp6d8kQ69QJ"
    "5d27Q4yQ64oR2NptkoR8/sJKE732v56yewdW30bIbcIfW65S+T//hRT5lXRIMHCY0SwCtjM18c9UFqI7aG/Jf5rEafrHIPNb"
    "0/i6Fc//pdbU1/KHmY9Jdm/jNFrKf7qiv2b4xx/VNMynmNLwL7d7Ej1OCUIaoyuSGNxzhXEcGt6JIq+IVIl6+idDaRrMzKZE"
    "NMagMqXgN7aoEwylFRa3vOIHcLyLrphTdzXT61rEafblAF3EaZETAku9u76dSlEaJJDo6hFlB0rfxtcS8Y1NfiwvUcrJnRbm"
    "v8ismeRJBF1q1EcshlhN019VzGGw0gt0mxPIoim7qSm+M52Eah5lPnu2rSe4Ms07PCeM3HCr28Qh7KZos+srqVMrup63EnBP"
    "3F3TGajO2fmZi0a7QukT7UsYfU/DeFU5V13hI27gFW4RTXZEs07Uhv+x2wGmURA3omNl95EhV+g28cSdzgu7I0gVC2cGNSgP"
    "O+0TaAtVO5pi3Z0xODj5j8EPtyFlFMnWPTV1C4VY0Z/u/4EfBkDCosAHkp1H8jTAqjW6Mhp5ROBzxtsboWudy85Q5UtbYIgj"
    "HVXaquRZafhviw0QGoCHKixvyX2o85EdQHMrFOElENVk6lYZVcUliXXU7ApBEVXnsE0Nq5HFmn9Y1IItyoKv+gRtMzWoOX8T"
    "JViQtffa+Hn9aOyA72hi4JTjFFRrL9MVhAhVN3Uh4c9iayGymOWejY0SqHBylSoCTg0qEN86fLXIaKIqgzlFV56WkP5rQAda"
    "/a2fvyARvhMcgaGv5Gfmc6Ij6XSSvz4yGkkcZou76TVoFJG6MccraQIKge3h/NYEhG7EfKSShQi9ScERnEEJTzAS4bLRNYvX"
    "0iEutiZ22ZA0OCevLNKwD0Rk6pJho8cWyGmzLFjxf1aEHVEIOyDKyUOQC5E4ai+1EU47ve47+OgdNIcEpXN+xLKR6B6VpvW2"
    "/a4DcwGh6W7Di7CGF7eFUrVw/IAme9Q9gBX8YKVv132+pjpgdAFxOytZqQgIzUo8w0u2y8xktRp0fgY7WoGOpEZunTct5dm5"
    "ON8HiZa2A3mhblSetlHIPkMnNZyHy4sLYCCevLwA2RyWQ3TO3uJXOLI+7eLp+SEtImFSwpIfn4NIfkbyPxyGNyZ6h4jTCC+w"
    "kyBskEcsKrAh/K1+SyNR2lpf8tj+rUUODhVFUOKNnhbc4D4xgtJGNVVqdRiKcMq365eO1JiSVNs44JTkI+RNeahJyuZRu5du"
    "IYk/IAOcfLXX2tv7prX7miwgm3tbrVXzLkYkSiUluYQNsidTYfwQcY0pGc6dhpG2BGHNMvYMoq4cFKFTBwa224q+Rn0Xq9dQ"
    "Nq1haWXMXPd4stvf7Oy+5OnubtF4cVFaTbUukP+oaUxhmy6UD3M+u+HO4CzDBg7MRed1Sq1esHqNiYbijqV0LQq1LuPKMlUu"
    "cLW0BdaEs1sJ5sf2patQYTCYh+FeL+nfr+jfbzly9Byj/Smo7tHCvagA1qOEezHSRXaLkG/CuRrZ/DCmdYMm7qMdFG0W4X+i"
    "Aob1iIpHKRDt71DxWKF5oOdBHvfOLy/W1zNWmE4eqGeUgqTEl+oZbthUx0Lk2fJs1plSmDULJ2n5njq1yIGo2nDCMnyWU5w0"
    "tt5RTtjANGVdn6GcqyvMGGpWhrJ31Eiv+mqjh7U8wkKV+vFgvxQVdlBY+b/GDDb0Z6SpWnqUC7eU/ZmfLJi2fB+nMzkA5ShU"
    "WdYINdj6IouNqFps5B0WG3Evi40xMT/cYiMKi428t8VGrLDYyNstNmI9i41ssNiIX91iI+oWm/UIp3gMwimqhFOuTTi/VMy+"
    "h8XGyNDiS4im+O2NM+JRiWZaVrRTweElQWILD3N5OIeQymZCKh5CSK1cdn9CiqfVNwAflooenh5cVAS6109C3JMQ9yTEPQlx"
    "v6IQx562N5haixroBcI4JSBXoffuR0zRSvFs53NLqH466YK8Z3CkEclo9xv5vfKj7RDnfOwHIdeUxRzPK9keY1KSuA0B+5mf"
    "bgfpszJIXB3jB9qwyHFltB1CEHBVeLi4MxWOV0DoCGlrntXTFl3Mcxx2Wfp0Ug41ho8telaFZHct20I6UqCTTqaruDi10MnM"
    "j1YSDTnrFAFD2HVoCAXecHmL86yajPiFaDXlrMJ7wdU4mMP18Mx7wtWsgKoRtuqhzpprhquRjwFXY24y1+e9H16NtNmV98qp"
    "XJE9KesXTv84d07Kn/GBPxJqa5xMiyrGcx8f+KMf5vMoaI2w09Gspca5EKUtU/IzYtJafI3Sht0ovQnF4svnMKPnWI5KBdfI"
    "jEMVTbPZUhdzNDtIKgciPerEZp4jeyIsUcArRLodpUfqwKkmODDdiBmkrdHHQB+wMoYaggxjV000kqnv8NbZurGmErtbrMrU"
    "JOBVKl1Oi7mtp9O8QvbimNYD42gBOnVAqO4n8VTCQSHcAQf/zi4fnjLCR9Eg8LAAF1w0AivGU2tH7X+1OHqlNnSMQLXycmXs"
    "9moU4ulP/cGhEE40J8MK/EQGVWAYxd2uJIidqsyH8fmZjoXjFHVUuicwZ1yTXzGDoBxmJx6aQSB1BsGXJhCU4tm4ctW98wce"
    "IX3ADEOYGtIPi6yr+Cu4ruRDwupEU97AkT9Swzi+8ihvAE+Rt34GwRcnEBShmvK3yh+QTv6AeJSAwPU8gGtFA2IooLhH/oBc"
    "J39APDQOsDkIUNwvCPD2CECxfgTgOuF/Yo3wv98uf6DBF/6Q/IF/fpQf8dWWvFjCbYvkZpQnXAg9kS31icC6ZiidRFtCV01M"
    "ddnEBb2BYs1jDUO0WxLWZKC3yNUExa2AsTz2G1QSgQFnhb+WYypASdpJUfjg0joIANWLEaJFAtfpAyGekd3i1IdXkEunWMsV"
    "493hic2D912sQq9Kcx/dBK0o3DLdnBH2ZwjEFwODQEQDqXXE+QQEJm2LKCKABoyuvX/Qkno0IHoS3C9P4lkqsMznKFigbkK6"
    "lIciqYUHtgjScyoh7dZs10VKyDvKVZsY14j7wUeDKIfekcpyfZfIbLvmvk5sFHIyYaP90RdAKGPdCLgTFTymeP9e09pESdBC"
    "DQgOx7XfytMtVJZ79IEn3wUJCOaBr+NXZg5mU4oI79CZ1Qq0WdlRBmFOiNfEOGc8L8Mm9UxGMaFtXaswXpAOkykfODJJ91ks"
    "9hWq3q0RcpuYuTW+zB/rNk78YUqvsY57PsrioUosfAViJS5hNTynW/uK7UkeggKSodMdTyRrlwzZM1QjbOKneFFacO4M3TZu"
    "w4V94SjOQcyjrdm86B/Ruovm+/hikU5ebNF9wBmij8YnqHRgu5MAEWmnfqRtEsLcmBLEC2b+3Jj12DbREV3Qs+D8Esg1pswA"
    "/0UI+epMqGO4AwuyXFCikpo7KwijR6sHCJx6jvoEsKBHG9FniW7TPVsImKeRclCVwvOZzcrPH2JMAolPW7Ccb0mC5xl5VLfC"
    "s/XP4TNPdy9s9xTzQOV8SX05vjjZpvI5GUKAc7EhrsZEyVO6yErwWaU0EFPTwDSncbh7/KfV/A61xEMVDtB4qn/OEcrMVBSB"
    "noVs+KEbfsdPMeT/gxEYPIqd1uvWDiKc5XK3tVd+wQDUvEI8zfdd+/lSgz3utl6aN1/hu24DBgXtNb4L5KD+7tflvrgJ+iFA"
    "Qv3jvhtx2QasFlx+tWjKfdW50uZVRFvdXf3qblOvS6Roe1u6691S1zCUP5g23ffhJMv6qEsvr/OqWSzotvLu7h9Me+u8u1d+"
    "17aFGWJ3vfuy8u7e2u/usS5JCk6t393tCG5Kw7ugu8YZ3ESsTED14Mq3jWwAiFQ/Vz7XKARd/llSAezW9KMox0PhYBcncPkd"
    "8mLQNT2Myw10FQ94yqMSj2gJcBCsyZZVaOMGV9hqs/5VVfl3kTzZEiLMHXbmYwswUclE9P3a0gLIm+dDLHdkBBnojGFWSSGz"
    "GhEtQ5DWUQ5pOkygmP0zzD9QICwn13bRJHsBuunHIPYACQQZwtOXRdvryqP2dC74yOeSkzY5k2w8PqxAjIY0oOtYAZtzTnHt"
    "nQ6FuWeenMU3yOE92/ezVNczoeayOBzTk8XHNGEanylwtaHNQnaIG4VKixuP3iY/urJwvCQlwcaloP3K6zjMgYXh+tzMYib3"
    "KAjZlSSJAkQwRufTvr25LvySqoJRmc1D68x+S4LycWrVSVOFmxS5A9BkOBTW0Q/kJX108WHwFvSSL5aa9akpuRVrlaDMzjmH"
    "RtwiYpisoaJ0uxCwbQzSRiuuX37Z+hYxaHXtFLhjaGZbmCJABq+zsLLVB0Zh8PXREcWoDUMYce8nlcTbOvAQbWIFyifBiboV"
    "V7RkQloB7KceuCnj5RRYK2B4BzPnxvLqpTbUnytxwBHGtTDj9TNnCIK3tjBHHJ1fnh1yRK0uiCFBQe3j33vifrDju9qIbdpp"
    "H/c6rFBTXnh2o3RRyNW7KzY3YHExisasZrdISACd5dyRD+Xmht4EtbFFNRZTctsg3lzhOMvTevAudEIj2Nhy7IVYQtGxlBnU"
    "ulUJW7CWey3ZL/tZdNA8J6Eba5nxqZgT0y4yB/AgsQddkPPIPqRYLFafQKVKQSjzTGIB1RTykDaE4+0bJB02qSIuDHuYPuKH"
    "y89oTVQoXGq8amOEA66yCP2lLgGDMugiwUBejQZMWhSXJK4ncbhLa7fSD6nAWGLzJopmNJ/yhLH0OeSWDicswrOG1aHO+Dvt"
    "FXErU3kiaKkWwdFWM8gJbJpR6l86WPWvGLGe/v2G/v2W/n3tMU6ZwJRyT6eCw7/07i69q1Hx6d3dbxghn/6ldxneeo/e3aN3"
    "917ecsS/a4pk29AYwYUbee2FFXrrKCPEHB84nS9bqLWRqYH8oPZk6eeRS1Z227JxU0tUUMeWTBlTgDQeTIzfyww8KuHQ+9qD"
    "g6yJqWqliwIUwmA44B0rzMDYWsC4uJGwY9ZhJpR0w/WNrYeEPWGI38Dty2ESqIlTZ5KGYSQiAqawpBaW6asW3cIgNQKUWXh3"
    "nHYc5GkwxlhBhTxbLEGetn/o9NHs2eugZdZkjZDh0LXM1kM2oIF9bYg7gq/b8GmnYqPUCSilftASbIyufbLllXt2Or4DU1GY"
    "gIwG0y7FRLQHrnFQc5D33ZMTQmExgSA6i7nbO9T5OmTsxfyKV7zGbArGSbkJPoZddEx+DQdeQGe9ftGdHWOjAXg1LmOPs7Xb"
    "fdHW6Iu0FpgA8oFswTbNhP5aKQsVqI42+6ec/HOHfVQ/C4vxteGSNYJHkQp+nsVUZ4+tHehHiNA3mC/w7FnHiRgmlHCl/RxN"
    "jAf6+oZyG2Y6GaGZCxXhTGP8gCxEbHkh3F4GIoXmZsGCTIZTFWGpA7z7iHAOHxNa8s8xiDBYcjbLE2W5PW47clJLl+SqyVvP"
    "6orcQmxKZAlcX/TAc50I/IsdQuR9tt9i/UPmiHUHj7AOHgqITa4pZxAmZoboGepGrl3GlYGl/LYl95fEfygnBMMItZxVitNh"
    "cYNpiGfbFAXhgnUeIi8w+aPriAzCLhNJ9R2MqmodIIBoTdLCa6IvKOjn4l7yGzdsXqff++eXvYNOQz9GRtxdU+xzTCGbG/wH"
    "Snmg6LDIJuLJhMLuQKv6ekf2feA38dSXbThROexJHwHRJUjVie/Jg7Z8/Wrn1a6VEsWDpMTqtolaxaSVoqEsi4aVOMnNDTfO"
    "b2Pr/rJiyepbPwaeecANv6wKj9uF9CjuJz3KZulR3F96rMaairL0WIoq/xIZsmYptxSGjBJudF4RDO6t0aVcLV3p/grJoTyb"
    "e8gP+uL9FiJEtavfTYooRV7eQ5YAeU3P4WHihJvxL79IqBCwi65QQeKCV8gWpbRm/NudsskmFl8sT7z6DeWJ1bKLFSI4BZbv"
    "CxFKrCMFlygrQDYSKp6bpYYFooXOxEZT6c8KcgLRMR0dGU2A5FBhGHyLyAEHI8kHSTqikHTkgyQdUWZwXFj0nsKOqAs7urVV"
    "8k5aEXjELQKPXFfgEa7AQxWcqfIwBjnbSiUbJSK7IcN4GqcOrfMzoWsFF34/+CZFxv+CHm7Nsnlo8AwoDqdaUshZjiKmNram"
    "9iEhDrBwu75EVi5B+avIZeSyuVUiY3vx49vTKs5xC4UnmpzjjtAlHaHr29ev5AX7xuX7GUIXHiYkOlj3eJssHrsg3eBM17PR"
    "ifWlL8O42ejvSGFiXSnsVzDQ4UzFbULWGhY6cR8Za6WFTqwtYzVb6PjsrSFjyVUyFjtARLOhTntHmix1sslSJ3R6wM7uytPb"
    "GNrxnSysZ+JO6xmfpdWTFrdKeZKDwpFdopAboL9O5cSdeLYNcrk9HUjhKAsIk81UJVwSa6PLzRhjTQ3ewJ9y9DhuvZEbpbEH"
    "aRVLNV1xooVzomGo5SEWu2WYUrF9oGdxgWBy7pV612Q6jA3uC3VJLD1SmUNa7dREHiHYKZ3nFD0TGKuPZaTQaZnITQzij7jQ"
    "zgwGHSqYMdKe1t7ei92d3Zd6eMWScp10jnzQGGs2BB6P6qclMTWM4SiPTjSMTl72Tt5IzaFm47DFY2jB4y/cUWz8yvZTXt3/"
    "LVZUng7L5sQEa8ZUfQ/voRJRO7+FQlTu6Pc2qvJC3c+0SjP4Itsq9/o7W1h57n+zdtb76EVEkxivRwRu5NpCR665KtElMD81"
    "Zs0obQAMEBWIR92wE9EPjRFd8QzPAO5DY4PrLgjGxryD3VrdhLC7vAYlDXF74uhGYfAnUgYTOOlqauazZ6mrtMmK0iYakHek"
    "g7xDTm34C8NCCFahLPownRVxhd8zFS7ILhnDUiTaRHzM1mqFwse4VnWNAXLhslTr1IlhObuUx1SAN5QXJJEV4KXHFwjlTfVg"
    "Vy5REVvK54EPwwpdgrGNfCbQaZqTn58zEnWV3sQsDOnRqMZewNymWM8rlV958hWzkW9WS7Z1dVnc0zFQVZfF/RwDRLQalGXx"
    "AM8AtVVSlcWDXAOupizu7xqAU0E8T9/DDYywuRhsYGAnKlUcVWxB9KitYaG/inU8CppGOjqIo7+Ke+uv0tVfTQgcDxv12fd3"
    "qLMcuTl42zu/PH6LsZfiIcXq6yUJ5bYOD7cB8LIxAL49B/kyGftzj6JinFB3HWVXzxq7ExuhoTDofVERTD12jYPQgEsj6tll"
    "D0FGEBYZQT4IGUE41S0bqhwWcJA6gb15O4TZDlgGPDK3omnIosIhMjoNvwMErJp02FjzsKh3aPOsMOtKlLKt+iBtvSV762kb"
    "pAH4B+S5txLO8aB3eSod6Q4EJif5ifAAep3jdg8TgkQF+7rIrMHX1kZSN2gKXkNO1B0DtXKclSQdpMs76xGWShCKB5YgLGP1"
    "iib4hYY8I8pF6p5f9jVeQ6nooLhn0UHZUHTwp07vfBs2EZ+mpFNNpI5oOQ47BqtBk6kSiucDSFQz2VqHkmhDTjMx0WRDGLJR"
    "zU5tJB1rYIZUwDRvP/DCHvgqZOf9z7twcgVvBydqwAKxZ1sn+oki5W/NQ766zqa4xyGXdx5ycfchX6eyprjjkD9S4tqrLTkY"
    "hbckz2FFeBAbQswBw2/PhyqZhL/8eTRTtby6bBRuY8LYo2bWfRHINgqeDwfZlu0RKhOkWgnXDNkAvv03h75dAoO7J/q2XIm+"
    "LdZA35broG+LOvq2fAj6trAgd78L+rYFGLs3+rZsQN8W66FvyzvRt8UjoW9bC9YHcS/07RVJ2Lejb8s10LfFSvRtuSb6trg1"
    "bflh6NuuNVKsn3v/pVBcq9C3y6spyvDb8oHw2wKO0EPgt2UVfls8Jvy2ycS9J/x2E3S0WBt+W66E3xZ3wm/L1fDbeuJiNf62"
    "vAf+tqjhb8vfHH9bT1Y4+Ntfyc0hzPeli78t7zADOpiIawFwyyYAbrEOALe8A4BbrADgdjJsHkku+hoEt6snue1echt8ARxP"
    "FTBC95HhhJXh5JMM9yTDPclwTzLckwz3JMM9yXB1Ge7lkwy3loz0DYJXddmvh8FPKMxNfvlLIsewwh0g/ej5L4S7ktyGXkH9"
    "4qOKbYdqhUCp3LFu78dxFsY+PgbDBNkA4QkSeu344kRiiQAFByQR7TyN/NlcXdEpCVFkQeacjpNcja5ChBVCp1w+hPs89uk9"
    "njhs1kUSw1GAA8yti6EKAzUMphROjYcoj/D3TR/jkiJ0Pm3HE7gdW/JGBfDC53yqhipqyX6gZgXkUGXpXqjoRUroOC/MDmMM"
    "svj/tnzvrA=="
)


def lizenztexte():
    """Die eingebetteten Lizenztexte im Klartext."""
    import base64
    import zlib

    try:
        roh = zlib.decompress(base64.b64decode("".join(LIZENZEN_Z_B64)))
        return roh.decode("utf-8", "replace")
    except Exception:
        return ("%s %s - MIT-Lizenz, (c) %s %s, %s\n\n"
                "Die eingebetteten Lizenztexte ließen sich nicht lesen.\n"
                % (APP_NAME, VERSION, APP_YEAR, APP_AUTHOR, APP_URL))


def selbsttest():
    """Prüft, ob das Programm wirklich startet.

    Wird beim Bau der exe aufgerufen. Der frühere Kurztest rief nur
    --icon-export auf und endete, bevor überhaupt ein Fenster entstand -
    ein kaputtes Fenster-Gespann wäre damit nicht aufgefallen.
    Ohne Konsole zählt der Rückgabewert, nicht die Ausgabe.
    """
    try:
        import tkinter  # noqa: F401
    except ImportError:
        ausgeben("FEHLER: Tkinter fehlt\n", True)
        return 2
    try:
        app = App([])
        app.win.update()
        dok = app.aktiv
        probe = ['N10 G54 G17 G90', 'N20 T="FRAESER8" M6', 'N30 G1 Z-5 F120',
                 'N40 G0 X10 Y20', 'N50 M30']
        dok.text.insert("1.0", "\n".join(probe))
        dok.dialekt_festlegen()
        dok.anzeige_auffrischen(verzoegert=False)
        app.v_suche.set("F120")      # kommt genau einmal vor
        app.suche_ausfuehren()
        app.win.update()
        teile = zerlege(probe[2], "sinumerik")
        klassen = {k for _a, _b, k in teile}
        app.win.destroy()
    except Exception as fehler:
        ausgeben("FEHLER im Selbsttest: %s\n" % fehler, True)
        return 1
    if not klassen >= {"satznummer", "g_bahn", "koordinate", "vorschub"}:
        ausgeben("FEHLER: Einfärbung unvollständig: %s\n" % sorted(klassen), True)
        return 1
    if len(dok.treffer) != 1:
        ausgeben("FEHLER: Suche fand %d statt 1 Treffer\n" % len(dok.treffer), True)
        return 1
    ausgeben("Selbsttest bestanden: Fenster, Einfärbung und Suche laufen.\n")
    return 0


def main(argv):
    argumente = list(argv[1:])
    if argumente and argumente[0] in ("--version", "-V"):
        ausgeben("%s %s\n" % (APP_NAME, VERSION))
        return 0
    if argumente and argumente[0] in ("--lizenzen", "--licenses"):
        ausgeben(lizenztexte())
        return 0
    if argumente and argumente[0] in ("--hilfe", "--help", "-h", "/?"):
        ausgeben(__doc__ or "")
        return 0
    if argumente and argumente[0] in ("--registrieren", "--register"):
        ok, meldung = windows_registrieren(False)
        ausgeben(meldung + "\n")
        return 0 if ok else 1
    if argumente and argumente[0] in ("--abmelden", "--unregister"):
        ok, meldung = windows_registrieren(True)
        ausgeben(meldung + "\n")
        return 0 if ok else 1
    if argumente and argumente[0] in ("--selbsttest", "--selftest"):
        return selbsttest()
    if len(argumente) == 2 and argumente[0] == "--icon-export":
        import base64
        with open(argumente[1], "wb") as fh:
            fh.write(base64.b64decode("".join(ICON_PNG_B64)))
        return 0

    dateien = [a for a in argumente if not a.startswith("-")]
    try:
        import tkinter  # noqa: F401
    except ImportError:
        ausgeben("Tkinter fehlt. Bitte Python von python.org installieren.\n", True)
        return 2

    # Läuft schon ein Fenster, bekommt es die Datei als neuen Reiter.
    instanz = Einzelinstanz()
    if einstellungen_laden().get("einzelnes_fenster", True):
        if not instanz.uebernehmen():
            if instanz.anfrage_stellen(dateien):
                return 0
            # Das laufende Fenster meldet sich nicht - lieber ein eigenes
            # öffnen, als den Doppelklick ins Leere laufen zu lassen.
    else:
        instanz.fuehrend = False
    App(dateien, instanz).starten()
    return 0


if __name__ == "__main__":        # (c) Christopher Schmick, iot-simply.com
    try:
        sys.exit(main(sys.argv))
    except SystemExit:
        raise
    except Exception:                 # lieber ein Rückgabewert als ein Fehlerfenster
        import traceback

        _text = traceback.format_exc()
        ausgeben(_text, True)
        fehler_protokollieren(_text)
        sys.exit(1)
