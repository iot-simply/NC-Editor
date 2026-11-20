#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft byteweise, dass der Editor NC-Dateien unveraendert zurueckschreibt.

Das ist der wichtigste Test des Programms: Was gespeichert wird, muss exakt
dem Original entsprechen - bis auf die Zeilen, die tatsaechlich geaendert
wurden. Geprueft werden Zeilenenden (LF und CRLF), Zeichensatz (UTF-8 und
ANSI), Tabulatoren, Leerzeichen am Zeilenende, Leerzeilen sowie Dateien mit
und ohne abschliessenden Zeilenumbruch.

Aufruf:   python tests/speichern_test.py
Ergebnis: Rueckgabewert 0, wenn alles stimmt.
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter.messagebox as mb                                    # noqa: E402

mb.showerror = mb.showinfo = lambda *a, **k: None
mb.askyesno = lambda *a, **k: True
mb.askyesnocancel = lambda *a, **k: False

import ncedit                                                      # noqa: E402

# Typische Faelle aus der Werkstatt. Die Programme sind kurz gehalten, decken
# aber alle Eigenheiten ab, die beim Schreiben schiefgehen koennen.
FAELLE = {
    # SINUMERIK aus SolidCAM: LF, Tabulator vor dem Kommentar, Schluss-Umbruch
    "sinumerik.mpf": (
        b"; TEIL-NAME    : MUSTER-1\n"
        b"N10 TRANS\n"
        b'N20 T="BOHRER10"\n'
        b"N30 M6\n"
        b"N40 S3900 M3 D1\t; DREHZAHL\n"
        b"\n"
        b"N50 G0 X2 Y2.5 \n"
        b"N60 G1 Z-11.92 F42000 \n"
        b"N70 M30\n"
    ),
    # Fanuc von der Maschine: endet mit % OHNE Zeilenumbruch
    "fanuc.nc": (
        b"%\n"
        b"O1\n"
        b"(MUSTER-2)\n"
        b"G40 G90 G17 G80 G49\n"
        b"\n"
        b"M06 T24 ( MESSERKOPF D=63.0)\n"
        b"S4000 M3\n"
        b"G43 H24 Z25.\n"
        b"G1 Z0. F1200.\n"
        b"   X97.901\n"
        b"M30\n"
        b"%"
    ),
    # Dieselbe Datei mit Windows-Zeilenenden
    "fanuc_crlf.nc": None,          # wird unten aus fanuc.nc erzeugt
    # ANSI mit Umlauten, CRLF, ohne Schluss-Umbruch
    "ansi.mpf": (
        b"N10 G54\r\n"
        b'N20 T="FR\xc4SER8" M6 ; GRO\xdfER FR\xc4SER\r\n'
        b"N30\tG1 Z-5 F120   \r\n"
        b"N40 M30"
    ),
    # Leerzeilen, Tabulatoren, Leerzeichen am Zeilenende
    "sonderfall.nc": b"%\nO1\n\n\tG0 X1   \n   \nN10 M30\n%",
    # Datei mit zwei Zeilenumbruechen am Schluss
    "zwei_umbrueche.nc": b"N10 G54\nN20 M30\n\n",
}
FAELLE["fanuc_crlf.nc"] = FAELLE["fanuc.nc"].replace(b"\n", b"\r\n")

# (Datei, Zeilennummer, neuer Zeileninhalt)
AENDERUNGEN = (
    ("sinumerik.mpf", 5, "N40 S3200 M3 D1\t; DREHZAHL VON HAND REDUZIERT"),
    ("fanuc.nc", 7, "S3200 M3"),
    ("fanuc_crlf.nc", 7, "S3200 M3"),
    ("ansi.mpf", 3, "N30\tG1 Z-6 F100"),
    ("sonderfall.nc", 4, "\tG0 X2   "),
    ("zwei_umbrueche.nc", 2, "N20 M30 ; HAND"),
)

fehler = []


def pruefe(name, ist, soll):
    if ist == soll:
        print("  OK     %-52s %6d Bytes" % (name, len(ist)))
        return True
    fehler.append(name)
    stelle = next((i for i in range(min(len(ist), len(soll))) if ist[i] != soll[i]),
                  min(len(ist), len(soll)))
    print("  FEHLER %-52s %d statt %d Bytes" % (name, len(ist), len(soll)))
    print("         erste Abweichung bei Byte %d: %r != %r"
          % (stelle, ist[max(0, stelle - 20):stelle + 20],
             soll[max(0, stelle - 20):stelle + 20]))
    return False


def erwartet(roh, nummer, neu):
    """Baut unabhaengig vom Programm nach, wie die Datei aussehen muss."""
    kodierung = "utf-8"
    try:
        roh.decode("utf-8")
    except UnicodeDecodeError:
        kodierung = "cp1252"
    ende = b"\r\n" if b"\r\n" in roh else b"\n"
    zeilen = roh.decode(kodierung).replace("\r\n", "\n").split("\n")
    zeilen[nummer - 1] = neu
    return ende.join(z.encode(kodierung) for z in zeilen)


def main():
    ordner = tempfile.mkdtemp(prefix="ncedit-test-")
    # Eigener Einstellungsordner, damit der Test nichts am Rechner veraendert
    os.environ["APPDATA"] = os.path.join(ordner, "appdata")
    os.environ["HOME"] = ordner
    for name, roh in FAELLE.items():
        with open(os.path.join(ordner, name), "wb") as fh:
            fh.write(roh)

    app = ncedit.App([])
    app.win.update()

    print("\n1) Unveraendert speichern (gleiche Datei)")
    for name, roh in FAELLE.items():
        pfad = os.path.join(ordner, name)
        app.datei_oeffnen(pfad)
        app.win.update()
        app.aktiv.speichern()
        app.win.update()
        with open(pfad, "rb") as fh:
            pruefe(name, fh.read(), roh)
        app.dokument_schliessen(app.aktiv)
        app.win.update()

    print("\n2) Unveraendert speichern unter neuem Namen")
    for name, roh in FAELLE.items():
        app.datei_oeffnen(os.path.join(ordner, name))
        app.win.update()
        ziel = os.path.join(ordner, "kopie_" + name)
        app.aktiv.speichern(ziel)
        app.win.update()
        with open(ziel, "rb") as fh:
            pruefe("kopie_" + name, fh.read(), roh)
        app.dokument_schliessen(app.aktiv)
        app.win.update()

    print("\n3) Mit genau einer geaenderten Zeile speichern unter")
    for name, nummer, neu in AENDERUNGEN:
        roh = FAELLE[name]
        app.datei_oeffnen(os.path.join(ordner, name))
        app.win.update()
        dok = app.aktiv
        dok.text.delete("%d.0" % nummer, "%d.end" % nummer)
        dok.text.insert("%d.0" % nummer, neu)
        dok._inhalt_geaendert()
        app.win.update()
        ziel = os.path.join(ordner, "neu_" + name)
        dok.speichern(ziel)
        app.win.update()
        with open(ziel, "rb") as fh:
            pruefe("%s, Zeile %d geaendert" % (name, nummer), fh.read(),
                   erwartet(roh, nummer, neu))
        app.dokument_schliessen(dok)
        app.win.update()

    print("\n4) Quelldatei bleibt beim Speichern unter unberuehrt")
    for name, nummer, _neu in AENDERUNGEN:
        with open(os.path.join(ordner, name), "rb") as fh:
            pruefe("Quelle " + name, fh.read(), FAELLE[name])

    print("\n5) Hand-Aenderungen stehen nur im Editor, nie in der Datei")
    pfad = os.path.join(ordner, "fanuc.nc")
    app.datei_oeffnen(pfad)
    app.win.update()
    dok = app.aktiv
    dok.text.delete("7.0", "7.end")
    dok.text.insert("7.0", "S3200 M3")
    dok._inhalt_geaendert()
    dok.diff_aktualisieren(sofort=True)
    stand = [("im Editor markiert", dict(dok.hand), {7: "g"})]

    # Speichern unter demselben Namen: Markierung muss bleiben
    dok.speichern()
    app.win.update()
    stand.append(("nach Speichern, gleiche Datei", dict(dok.hand), {7: "g"}))
    with open(pfad, "rb") as fh:
        geschrieben = fh.read()
    pruefe("Datei = Original + genau diese Aenderung", geschrieben,
           FAELLE["fanuc.nc"].replace(b"S4000 M3", b"S3200 M3", 1))
    marker = [m for m in (b"HAND", b"*HAND*", b";NCE", b"<<<", b">>>", b"@@")
              if m in geschrieben]
    if marker:
        fehler.append("Markierung in der Datei gelandet")
        print("  FEHLER in der Datei steht eine Markierung: %r" % marker)
    else:
        print("  OK     in der Datei steht keinerlei Markierung")

    # Speichern unter neuem Namen: der geschriebene Stand ist das neue Original
    ziel = os.path.join(ordner, "unter_neuem_namen.nc")
    dok.speichern(ziel)
    app.win.update()
    stand.append(("nach Speichern unter neuem Namen", dict(dok.hand), {}))
    app.dokument_schliessen(dok)
    app.win.update()
    app.datei_oeffnen(ziel)
    app.win.update()
    stand.append(("neue Datei erneut geoeffnet", dict(app.aktiv.hand), {}))
    for beschreibung, ist, soll in stand:
        if ist == soll:
            print("  OK     %-52s %s" % (beschreibung, ist or "keine Markierung"))
        else:
            fehler.append(beschreibung)
            print("  FEHLER %-52s %s statt %s" % (beschreibung, ist, soll))
    with open(ziel, "rb") as fh:
        pruefe("neue Datei inhaltlich gleich der gespeicherten", fh.read(),
               geschrieben)

    # Beim Speichern unter neuem Namen gibt es nichts zu sichern - eine
    # Sicherungskopie entsteht nur, wenn eine vorhandene Datei ueberschrieben
    # wird. Das war oben beim Speichern von fanuc.nc der Fall.
    print("\n6) Sicherungskopie .bak ist der Stand vor dem Speichern")
    if os.path.isfile(ziel + ".bak"):
        fehler.append("Speichern unter neuem Namen legt unnoetig eine .bak an")
        print("  FEHLER fuer die neue Datei wurde eine .bak angelegt")
    else:
        print("  OK     fuer eine neue Datei entsteht keine .bak")
    with open(pfad + ".bak", "rb") as fh:
        pruefe("fanuc.nc.bak = Stand vor dem Speichern", fh.read(),
               FAELLE["fanuc.nc"])

    print("\n7) Aufraeumen der Originale")
    import time as _time

    # Ein Original, dessen NC-Datei es nicht mehr gibt
    verwaist = os.path.join(ordner, "verschwunden.mpf")
    with open(verwaist, "wb") as fh:
        fh.write(b"N10 M30\n")
    app.datei_oeffnen(verwaist)
    app.win.update()
    app.dokument_schliessen(app.aktiv)
    app.win.update()
    os.remove(verwaist)

    # Ein Original, das lange nicht gebraucht wurde
    altes = os.path.join(ordner, "altes.mpf")
    with open(altes, "wb") as fh:
        fh.write(b"N10 G54\nN20 M30\n")
    app.datei_oeffnen(altes)
    app.win.update()
    app.dokument_schliessen(app.aktiv)
    app.win.update()
    kopie = os.path.join(ncedit._original_ordner(),
                         ncedit._schluessel(altes) + ".txt")
    lange_her = _time.time() - 400 * 86400
    os.utime(kopie, (lange_her, lange_her))

    # Ein gerade geoeffnetes Programm muss auf jeden Fall bleiben
    app.datei_oeffnen(ziel)
    app.win.update()
    offen = [d.pfad for d in app.dokumente if d.pfad]
    entfernt, _frei, bleibt, _bb = ncedit.originale_aufraeumen(
        90, 400, schonen=offen)
    behalten = os.path.isfile(os.path.join(
        ncedit._original_ordner(), ncedit._schluessel(ziel) + ".txt"))
    pruefungen = (
        ("verwaistes Original entfernt",
         not os.path.isfile(os.path.join(ncedit._original_ordner(),
                                         ncedit._schluessel(verwaist) + ".txt"))),
        ("lange unbenutztes Original entfernt", not os.path.isfile(kopie)),
        ("mindestens zwei entfernt", entfernt >= 2),
        ("geoeffnetes Programm behalten", behalten),
    )
    for beschreibung, ok in pruefungen:
        if ok:
            print("  OK     %s" % beschreibung)
        else:
            fehler.append(beschreibung)
            print("  FEHLER %s" % beschreibung)

    # Auch beim Loeschen aller Originale bleibt das offene Programm verschont
    ncedit.originale_alle_loeschen(schonen=offen)
    if os.path.isfile(os.path.join(ncedit._original_ordner(),
                                   ncedit._schluessel(ziel) + ".txt")):
        print("  OK     'alle loeschen' verschont das geoeffnete Programm")
    else:
        fehler.append("'alle loeschen' hat das offene Programm erwischt")
        print("  FEHLER 'alle loeschen' hat das offene Programm erwischt")

    print("\n8) Neuer Lauf des Postprozessors gilt nicht als Hand-Aenderung")
    import time as _zeit

    post = os.path.join(ordner, "aus_cam.mpf")
    erster = (b"; DATUM - ZEIT : 17-NOV-2026 - 06:00:00\n"
              b"N10 G54\nN20 S3900 M3\nN30 G1 Z-5 F120\nN40 M30\n")
    zweiter = (b"; DATUM - ZEIT : 17-NOV-2026 - 08:15:00\n"
               b"N10 G54\nN20 S4100 M3\nN30 G1 Z-5 F140\nN40 M30\n")
    with open(post, "wb") as fh:
        fh.write(erster)
    app.datei_oeffnen(post)
    app.win.update()
    app.dokument_schliessen(app.aktiv)
    app.win.update()

    _zeit.sleep(0.02)                      # neue Zeitmarke erzwingen
    with open(post, "wb") as fh:
        fh.write(zweiter)
    app.datei_oeffnen(post)
    app.win.update()
    nach_lauf = app.aktiv.hand_anzahl()

    # Eigene Aenderung muss weiterhin erkannt werden
    dok = app.aktiv
    dok.text.delete("3.0", "3.end")
    dok.text.insert("3.0", "N20 S3000 M3 ; HAND")
    dok._inhalt_geaendert()
    dok.diff_aktualisieren(sofort=True)
    nach_hand = dok.hand_anzahl()
    app.speichern(dok)
    app.win.update()
    nach_speichern = dok.hand_anzahl()
    app.dokument_schliessen(dok)
    app.win.update()
    app.datei_oeffnen(post)
    app.win.update()
    nach_oeffnen = app.aktiv.hand_anzahl()

    # Datei bleibt offen und wird von aussen neu geschrieben
    _zeit.sleep(0.02)
    with open(post, "wb") as fh:
        fh.write(zweiter)
    app.datei_oeffnen(post)                # so ruft SolidCAM den Editor erneut
    app.win.update()
    aktuell = app.aktiv.text.get("3.0", "3.end").strip() == "N20 S4100 M3"

    for beschreibung, ist, soll in (
            ("neuer Lauf gilt als neues Original", nach_lauf, 0),
            ("eigene Aenderung wird erkannt", nach_hand, 1),
            ("bleibt nach dem Speichern erkannt", nach_speichern, 1),
            ("bleibt nach erneutem Oeffnen erkannt", nach_oeffnen, 1)):
        if ist == soll:
            print("  OK     %-46s %d" % (beschreibung, ist))
        else:
            fehler.append(beschreibung)
            print("  FEHLER %-46s %d statt %d" % (beschreibung, ist, soll))
    if aktuell:
        print("  OK     Inhalt nach neuem Lauf ist aktuell")
    else:
        fehler.append("Inhalt nach neuem Lauf veraltet")
        print("  FEHLER Inhalt nach neuem Lauf ist veraltet")

    print("\n9) Gleichnamige Programme in verschiedenen Ordnern")
    # In der Werkstatt heissen die Programme oft nur "1" - beschrieben ist der
    # Ordner. Originale und Hand-Aenderungen duerfen sich nicht vermischen.
    auftraege = []
    for auftrag, inhalt in (("Deckel 1001", b"N10 G54\nN20 S3900 M3\nN30 M30\n"),
                            ("Flansch 1002", b"N10 G55\nN20 S2500 M3\nN30 M30\n"),
                            ("Halter 1003", b"N10 G56\nN20 S1800 M3\nN30 M30\n")):
        unterordner = os.path.join(ordner, auftrag)
        os.makedirs(unterordner, exist_ok=True)
        pfad = os.path.join(unterordner, "1.MPF")
        with open(pfad, "wb") as fh:
            fh.write(inhalt)
        auftraege.append(pfad)

    for pfad in auftraege:
        app.datei_oeffnen(pfad)
        app.win.update()
    offen = [d for d in app.dokumente if d.pfad in auftraege]
    beschriftungen = {ncedit.reiter_beschriftung(d, app.dokumente) for d in offen}

    # Nur im ersten Auftrag etwas von Hand aendern
    erstes = [d for d in app.dokumente if d.pfad == auftraege[0]][0]
    app.dokument_waehlen(erstes)
    app.win.update()
    erstes.text.delete("2.0", "2.end")
    erstes.text.insert("2.0", "N20 S3000 M3 ; HAND")
    erstes._inhalt_geaendert()
    app.speichern(erstes)
    app.win.update()
    for dok in offen:
        dok.original_pruefen()
    markierungen = [d.hand_anzahl() for d in offen]
    inhalte = [d.text.get("1.0", "1.end") for d in offen]

    for beschreibung, ok in (
            ("drei Programme geoeffnet", len(offen) == 3),
            ("Reiter sind unterscheidbar", len(beschriftungen) == 3),
            ("Hand-Aenderung bleibt beim eigenen Auftrag",
             markierungen == [1, 0, 0]),
            ("Inhalte nicht vermischt",
             inhalte == ["N10 G54", "N10 G55", "N10 G56"])):
        if ok:
            print("  OK     %s" % beschreibung)
        else:
            fehler.append(beschreibung)
            print("  FEHLER %s" % beschreibung)
    if not all(ok for _b, ok in (("", len(beschriftungen) == 3),)):
        print("         Beschriftungen: %s" % sorted(beschriftungen))

    app.beenden()
    shutil.rmtree(ordner, ignore_errors=True)

    if fehler:
        print("\nFEHLGESCHLAGEN (%d): %s" % (len(fehler), " | ".join(fehler)))
        return 1
    print("\nAlle Pruefungen bestanden.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
