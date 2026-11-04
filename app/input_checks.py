"""Validate synthetic uploads and mask structured identifiers, without I/O.

The backend must use ``report_clean`` downstream. This is basic field masking,
not free-text anonymization. Original bytes are never changed in place.
"""

import csv
import io
import math
import re

MAX_ECG_BYTES = 2 * 1024 * 1024
MAX_REPORT_BYTES = 64 * 1024
MAX_CSV_FIELD_CHARS = 131_072
MASK = "[MASQUÉ]"
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_IDENTITY = re.compile(
    r"(?<![^\r\n])([ \t]*(?:nom|pr[ée]nom|patient[ _-]*id)[ \t]*[:=][ \t]*)[^\r\n]*",
    re.IGNORECASE | re.MULTILINE,
)


def _decode(data: bytes, name: str, limit: int, reasons: list[str]) -> str | None:
    if not isinstance(data, bytes):
        reasons.append(f"{name} : des octets sont attendus.")
        return None
    if not data:
        reasons.append(f"{name} : fichier vide.")
        return None
    if len(data) > limit:
        reasons.append(f"{name} : taille maximale dépassée ({limit} octets).")
        return None
    try:
        text = data.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        reasons.append(f"{name} : encodage UTF-8 requis.")
        return None
    if not text.strip():
        reasons.append(f"{name} : contenu vide.")
        return None
    if _CONTROL.search(text):
        reasons.append(f"{name} : caractères binaires ou de contrôle interdits.")
        return None
    return text


def _check_csv(text: str, reasons: list[str]) -> None:
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        header = next(reader, [])
        if any(len(value) > MAX_CSV_FIELD_CHARS for value in header):
            raise csv.Error("field too long")
        if not header or "signal" not in header:
            reasons.append("ECG : le CSV doit contenir une colonne exacte 'signal' (séparateur virgule).")
            return
        if len(set(header)) != len(header) or any(not value.strip() for value in header):
            reasons.append("ECG : noms de colonnes vides ou dupliqués.")
            return
        signal_index = header.index("signal")
        count = 0
        for row in reader:
            if not row:  # harmless empty lines, including the final newline
                continue
            if any(len(value) > MAX_CSV_FIELD_CHARS for value in row):
                raise csv.Error("field too long")
            if len(row) != len(header):
                reasons.append(f"ECG : nombre de colonnes incorrect à la ligne {reader.line_num}.")
                return
            value = row[signal_index].strip()
            if not _NUMBER.fullmatch(value) or not math.isfinite(float(value)):
                reasons.append(f"ECG : 'signal' doit être numérique et fini à la ligne {reader.line_num}.")
                return
            count += 1
        if count == 0:
            reasons.append("ECG : aucune valeur de signal.")
    except (csv.Error, ValueError, OverflowError):
        reasons.append("ECG : CSV mal formé ou champ trop long.")


def check_inputs(ecg_bytes: bytes, report_bytes: bytes) -> dict:
    """Return exactly {valid, reasons, report_clean}; never store or log uploads.

    UTF-8 (optional BOM), comma-separated CSV, finite numeric ``signal`` and a
    nonempty text report are required. Limits are inclusive, measured in bytes.
    Minimum signal length/quality belong to the preprocessing module.
    """
    reasons: list[str] = []
    ecg = _decode(ecg_bytes, "ECG", MAX_ECG_BYTES, reasons)
    report = _decode(report_bytes, "Rapport", MAX_REPORT_BYTES, reasons)
    if ecg is not None:
        _check_csv(ecg, reasons)
    return {
        "valid": not reasons,
        "reasons": reasons,
        "report_clean": _IDENTITY.sub(lambda match: match[1] + MASK, report)
        if not reasons and report is not None else "",
    }


if __name__ == "__main__":
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Contrôle de fichiers synthétiques uniquement")
    parser.add_argument("ecg", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        result = check_inputs(args.ecg.read_bytes(), args.report.read_bytes())
    except OSError:
        result = {"valid": False, "reasons": ["Impossible de lire les fichiers."], "report_clean": ""}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["valid"] else 1)
