#!/usr/bin/env python3
"""Datenschutz-Check: verhindert, dass persönliche Daten oder Schlüssel ins Repo kommen.

Aufruf:
  privacy_check.py            prüft die für den Commit vorgemerkten Dateien (pre-commit)
  privacy_check.py --all      prüft alle Dateien im Repo (z. B. für GitHub Actions)

Freigeben:
  - Zeile enthält den Kommentar  privacy-ok
  - Begriff steht in .privacy-allowlist.txt (wird mit hochgeladen)
Sperrliste:
  - .privacy-blocklist.txt (bleibt lokal, steht in .gitignore), ein Wort pro Zeile
"""
import re, subprocess, sys
from pathlib import Path

ROOT = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip() or ".")

PATTERNS = [
    ("E-Mail-Adresse", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")),
    ("Telefonnummer", re.compile(r"(?<![\w.,])(?:(?:\+|00)\d{2}[\s/-]?\d{2,5}[\s/-]?\d{3,}|0\d{2,5}[\s/-]\d{3,}(?:[\s-]?\d+)*)")),
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b")),
    ("Datum mit Jahr (Geburtsdatum?)", re.compile(r"\b\d{1,2}\.\s?\d{1,2}\.\s?(?:19|20)\d{2}\b")),
    ("Straße + Hausnummer", re.compile(r"\b[A-ZÄÖÜ][a-zäöüß-]*(?:straße|strasse|str\.|weg|allee|platz|damm|ring|gasse|chaussee)\s+\d+\s?[a-z]?\b")),
    ("PLZ + Ort", re.compile(r"(?<![\d.,])\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]{2,}")),
    ("Token (JWT, z. B. Graph-Token)", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("GitHub-Token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("API-Schlüssel", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}|\bAKIA[0-9A-Z]{16}\b|\bAIza[0-9A-Za-z_-]{30,}")),
    ("Privater Schlüssel", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
BAD_NAMES = re.compile(r"(^|/)(\.graph_token|\.env(\..*)?|.*\.pem|.*\.key|id_rsa.*|.*token.*\.txt)$", re.I)
SKIP_NAMES = {".privacy-allowlist.txt", ".githooks/privacy_check.py"}

def read_list(name):
    p = ROOT / name
    if not p.exists():
        return []
    return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]

def files(all_files):
    if all_files:
        cmd = ["git", "ls-files"]
    else:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    return [f for f in subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT).stdout.splitlines() if f]

def content(path, all_files):
    if all_files:
        data = (ROOT / path).read_bytes()
    else:
        data = subprocess.run(["git", "show", ":" + path], capture_output=True, cwd=ROOT).stdout
    if b"\0" in data[:8000]:
        return None  # Binärdatei (Bilder)
    return data.decode("utf-8", errors="replace")

def main():
    all_files = "--all" in sys.argv
    allow = [a.lower() for a in read_list(".privacy-allowlist.txt")]
    block = read_list(".privacy-blocklist.txt")
    block_re = [(w, re.compile(re.escape(w), re.I)) for w in block]
    hits = []
    for f in files(all_files):
        if BAD_NAMES.search(f):
            hits.append((f, 0, "Verbotener Dateiname", f))
            continue
        if f in SKIP_NAMES:
            continue
        text = content(f, all_files)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if "privacy-ok" in line:
                continue
            for label, rx in PATTERNS:
                for m in rx.finditer(line):
                    if m.group(0).lower() not in allow:
                        hits.append((f, n, label, m.group(0)))
            for w, rx in block_re:
                if rx.search(line):
                    hits.append((f, n, "Sperrliste", w))
    if not hits:
        print("Datenschutz-Check: alles sauber.")
        return 0
    print("\n⛔  Datenschutz-Check hat etwas gefunden:\n")
    for f, n, label, val in hits:
        shown = val if len(val) <= 40 else val[:12] + "…" + val[-6:]
        if label.startswith(("Token", "GitHub", "API", "Privat")):
            shown = val[:6] + "…(versteckt)"
        print(f"  {f}:{n}  {label}: {shown}")
    print("\nCommit abgebrochen. Entferne die Daten oder gib die Zeile mit dem Kommentar 'privacy-ok' frei")
    print("bzw. trag den Begriff in .privacy-allowlist.txt ein.\n")
    return 1

if __name__ == "__main__":
    sys.exit(main())
