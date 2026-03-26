#!/usr/bin/env python3
"""
assemble.py — Patagonia Webseite Build-Script
============================================
Liest alle Fragment-HTML-Dateien aus dem /build Ordner,
extrahiert <style>-Blöcke, kombiniert alles zu einer
sauberen index.html Datei.

Verwendung:
    python assemble.py
    python assemble.py --output index.html
    python assemble.py --check-images
"""

import os
import re
import sys
import argparse
from pathlib import Path

# -------------------------------------------------------
# Konfiguration
# -------------------------------------------------------
BUILD_DIR   = Path(__file__).parent / "build"
OUTPUT_FILE = Path(__file__).parent / "index.html"
IMG_DIR     = Path(__file__).parent / "img"

# Reihenfolge der Fragmente (Dateiname → Beschreibung)
FRAGMENTS = [
    ("01_hero.html",              "Hero Section"),
    ("04_timeline.html",          "Reiseplan Timeline"),
    ("06_keyfacts_mendoza.html",  "Key Facts & Mendoza"),
    ("08_anmeldung.html",         "Anmeldung & Footer"),
]

# Bilder die vorhanden sein müssen
REQUIRED_IMAGES = [
    "logo.png",
    "buenosaires.jpg",
    "gletscher.jpg",
    "fitzroy.jpg",
    "patagonia.jpg",
    "mendoza.jpg",
    "swiss.jpg",
]


# -------------------------------------------------------
# Hilfsfunktionen
# -------------------------------------------------------

def read_file(path: Path) -> str:
    """Liest eine Datei und gibt den Inhalt zurück."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def extract_styles(html: str) -> tuple[str, str]:
    """
    Trennt <style>...</style> Blöcke vom restlichen HTML.
    Gibt (styles_combined, html_without_styles) zurück.
    """
    style_blocks = []
    def collect_style(m):
        style_blocks.append(m.group(1).strip())
        return ""  # Entferne den <style>-Block aus dem HTML

    html_clean = re.sub(
        r'<style[^>]*>(.*?)</style>',
        collect_style,
        html,
        flags=re.DOTALL | re.IGNORECASE
    )
    return "\n\n".join(style_blocks), html_clean


def extract_scripts(html: str) -> tuple[str, str]:
    """
    Trennt <script>...</script> Blöcke vom restlichen HTML.
    Gibt (scripts_combined, html_without_scripts) zurück.
    """
    script_blocks = []
    def collect_script(m):
        script_blocks.append(m.group(0).strip())
        return ""

    html_clean = re.sub(
        r'<script[^>]*>.*?</script>',
        collect_script,
        html,
        flags=re.DOTALL | re.IGNORECASE
    )
    return "\n\n".join(script_blocks), html_clean


def strip_html_boilerplate(html: str) -> str:
    """
    Entfernt <!DOCTYPE>, <html>, <head>, <body>, </body>, </html>
    aus Fragment-Dateien. Behält Inhalts-HTML.
    """
    # Entferne alles von <!DOCTYPE bis Ende von <body ...>
    html = re.sub(r'<!DOCTYPE[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<html[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'<head[^>]*>.*?</head>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<body[^>]*>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</body>', '', html, flags=re.IGNORECASE)
    html = re.sub(r'</html>', '', html, flags=re.IGNORECASE)
    return html.strip()


def check_images() -> list[str]:
    """Prüft ob alle benötigten Bilder vorhanden sind."""
    missing = []
    for img in REQUIRED_IMAGES:
        if not (IMG_DIR / img).exists():
            missing.append(str(IMG_DIR / img))
    return missing


def section_divider(name: str) -> str:
    """Erstellt einen HTML-Kommentar als Trennzeichen."""
    bar = "=" * 60
    return f"\n\n<!-- {bar}\n     {name}\n     {bar} -->\n"


# -------------------------------------------------------
# Haupt-Build-Funktion
# -------------------------------------------------------

def assemble(output_path: Path, verbose: bool = True) -> None:
    all_styles  = []
    all_body    = []
    all_scripts = []

    # --- 1. Basis-Datei (Head) lesen ---
    base_path = BUILD_DIR / "00_base.html"
    if not base_path.exists():
        print(f"FEHLER: Basis-Datei nicht gefunden: {base_path}")
        sys.exit(1)

    base_html = read_file(base_path)

    # Extrahiere <style> aus Base (in <head>)
    head_style_match = re.search(
        r'<style[^>]*>(.*?)</style>',
        base_html,
        flags=re.DOTALL | re.IGNORECASE
    )
    base_styles = head_style_match.group(1).strip() if head_style_match else ""

    # Extrahiere <head> Inhalt (alles zwischen <head> und </head>)
    head_match = re.search(
        r'<head[^>]*>(.*?)</head>',
        base_html,
        flags=re.DOTALL | re.IGNORECASE
    )
    head_content_raw = head_match.group(1) if head_match else ""
    # Entferne den <style>-Block — kommt separat unten
    head_content = re.sub(
        r'<style[^>]*>.*?</style>', '',
        head_content_raw,
        flags=re.DOTALL | re.IGNORECASE
    ).strip()

    if verbose:
        print(f"  Base:    00_base.html — Head geladen")

    all_styles.append(f"/* === BASE STYLES === */\n{base_styles}")

    # --- 2. Fragmente verarbeiten ---
    for filename, description in FRAGMENTS:
        fpath = BUILD_DIR / filename
        if not fpath.exists():
            print(f"  WARNUNG: Fragment nicht gefunden: {fpath} — übersprungen")
            continue

        raw = read_file(fpath)

        # Boilerplate entfernen (DOCTYPE, html, head, body)
        raw = strip_html_boilerplate(raw)

        # Style-Blöcke herausziehen
        styles, raw = extract_styles(raw)

        # Script-Blöcke herausziehen
        scripts, raw = extract_scripts(raw)

        # Kommentare aus dem rohen HTML übernehmen (section divider)
        section_comment = re.search(r'<!--[^\[].+?-->', raw, re.DOTALL)

        if styles:
            label = f"/* === {description.upper()} === */"
            all_styles.append(f"{label}\n{styles}")

        if scripts:
            all_scripts.append(scripts)

        all_body.append(section_divider(description))
        all_body.append(raw.strip())

        if verbose:
            print(f"  Fragment: {filename} ({description})")

    # --- 3. Scripts-Datei (99) verarbeiten ---
    scripts_path = BUILD_DIR / "99_scripts.html"
    if scripts_path.exists():
        raw_scripts = read_file(scripts_path)
        raw_scripts = strip_html_boilerplate(raw_scripts)
        _, remaining = extract_styles(raw_scripts)  # keine styles erwartet
        scripts_extracted, _ = extract_scripts(remaining)
        if scripts_extracted:
            all_scripts.append(scripts_extracted)
        if verbose:
            print(f"  Scripts: 99_scripts.html")

    # --- 4. Zusammenbauen ---
    combined_styles  = "\n\n".join(filter(None, all_styles))
    combined_body    = "\n".join(all_body)
    combined_scripts = "\n\n".join(filter(None, all_scripts))

    output = f"""<!DOCTYPE html>
<html lang="de">
<head>
{head_content}

  <style>
{combined_styles}
  </style>
</head>
<body>

{combined_body}

{combined_scripts}

</body>
</html>
"""

    # --- 5. Schreiben ---
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    size_kb = output_path.stat().st_size / 1024
    if verbose:
        print(f"\n  Output:  {output_path}")
        print(f"  Groesse: {size_kb:.1f} KB")
        print(f"  Zeilen:  {output.count(chr(10))}")


# -------------------------------------------------------
# CLI
# -------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Patagonia Webseite — HTML Assembler"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(OUTPUT_FILE),
        help=f"Output-Datei (Standard: {OUTPUT_FILE})"
    )
    parser.add_argument(
        "--check-images",
        action="store_true",
        help="Nur Bilder prüfen, nichts zusammenbauen"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimale Ausgabe"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  Patagonia 2027 — Build")
    print("=" * 50)

    # Bilder prüfen
    missing = check_images()
    if missing:
        print("\n  WARNUNG — Fehlende Bilder:")
        for m in missing:
            print(f"    - {m}")
        if args.check_images:
            sys.exit(1)
    else:
        if not args.quiet:
            print(f"\n  Bilder: alle {len(REQUIRED_IMAGES)} vorhanden")

    if args.check_images:
        print("  Bilder-Check abgeschlossen.")
        return

    print()
    assemble(Path(args.output), verbose=not args.quiet)
    print("\n  Build erfolgreich abgeschlossen.")
    print("=" * 50)


if __name__ == "__main__":
    main()
