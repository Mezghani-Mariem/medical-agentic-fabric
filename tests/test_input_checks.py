from pathlib import Path

import pytest

from app.input_checks import MAX_ECG_BYTES, MAX_REPORT_BYTES, check_inputs

ECG = b"time,signal\r\n0,0.1\r\n1,-2.4e-2\r\n2,.25\r\n"
REPORT = "Nom: Exemple\nPrénom: Fictive\nPatient ID: DEMO-001\nObservation: rapport synthétique.\n".encode()
ROOT = Path(__file__).resolve().parents[1]


def test_valid_input_and_exact_contract():
    result = check_inputs(ECG, REPORT)
    assert set(result) == {"valid", "reasons", "report_clean"}
    assert result["valid"] is True
    assert result["reasons"] == []
    assert "Observation: rapport synthétique." in result["report_clean"]
    assert all(value not in result["report_clean"] for value in ("Exemple", "Fictive", "DEMO-001"))
    assert result["report_clean"].count("[MASQUÉ]") == 3


@pytest.mark.parametrize("ecg,report", [(b"", REPORT), (ECG, b""), (b" \r\n", REPORT), (ECG, b"\t\n")])
def test_empty_uploads(ecg, report):
    result = check_inputs(ecg, report)
    assert not result["valid"] and result["reasons"]
    assert result["report_clean"] == ""


@pytest.mark.parametrize("ecg", [
    b"value\n1\n", b"signal\n", b"signal\nabc\n", b"signal\nNaN\n", b"signal\ninf\n",
    b"signal\n-Infinity\n", b"signal\n1e999\n", b"signal\n1_000\n", b"signal\n\"1\n",
    b"signal,x\n1\n", b"signal\n1,2\n", b"signal,signal\n1,2\n", b"signal,\n1,2\n",
    b"time;signal\n0;1\n", b"signal,x\n,ok\n", b" Signal\n1\n", b"signal\n\x00\n",
    b"signal\n\xff\n", pytest.param(b"signal\n\"" + b"1" * 140000 + b"\"\n", id="field-too-long"),
])
def test_invalid_csv_returns_safe_errors(ecg):
    result = check_inputs(ecg, REPORT)
    assert result["valid"] is False
    assert result["reasons"] and result["report_clean"] == ""
    assert "DEMO-001" not in str(result["reasons"])


@pytest.mark.parametrize("report", [b"\xff", b"abc\x00def", b"a\x1bb", b"\xef\xbb\xbf"])
def test_invalid_text_or_binary(report):
    assert not check_inputs(ECG, report)["valid"]


def test_size_limits_are_inclusive_and_measured_in_bytes():
    exact_ecg = b"signal\n" + b"0\n" * ((MAX_ECG_BYTES - 7) // 2) + b"\n"
    assert len(exact_ecg) == MAX_ECG_BYTES
    assert check_inputs(exact_ecg, b"x" * MAX_REPORT_BYTES)["valid"]
    assert not check_inputs(exact_ecg + b"\n", REPORT)["valid"]
    assert not check_inputs(ECG, b"x" * (MAX_REPORT_BYTES + 1))["valid"]
    assert not check_inputs(ECG, ("é" * MAX_REPORT_BYTES).encode())["valid"]


def test_bom_crlf_and_extra_columns():
    result = check_inputs(b"\xef\xbb\xbf" + ECG, b"\xef\xbb\xbf" + REPORT)
    assert result["valid"]
    assert not result["report_clean"].startswith("\ufeff")


@pytest.mark.parametrize("label", ["Nom", "NOM", "prénom", "Prenom", "Patient ID", "patient_id", "Patient-ID"])
def test_structured_fields_masked_with_spacing_and_equals(label):
    result = check_inputs(ECG, f"  {label} = VALEUR_FICTIVE\r\nContexte: synthétique".encode())
    assert result["valid"]
    assert "VALEUR_FICTIVE" not in result["report_clean"]
    assert "Contexte: synthétique" in result["report_clean"]


def test_no_claim_of_free_text_anonymization_and_no_mutation():
    report = b"Observation: Nom Exemple dans une phrase.\nNom: Exemple\nNom: Autre\n"
    before = bytes(report)
    result = check_inputs(ECG, report)
    assert "Nom Exemple dans une phrase" in result["report_clean"]
    assert result["report_clean"].count("[MASQUÉ]") == 2
    assert report == before
    assert check_inputs(ECG, result["report_clean"].encode()) == result


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_masking_handles_every_common_line_ending(newline):
    report = newline.join(["Nom: EXEMPLE", "Prénom: FICTIF", "Patient ID: DEMO", "Contexte: synthétique"])
    result = check_inputs(ECG, report.encode())
    assert result["valid"]
    assert result["report_clean"].count("[MASQUÉ]") == 3
    assert result["report_clean"].count(newline) == 3


@pytest.mark.parametrize("ecg,report", [(None, REPORT), (ECG, None), ("signal\n1", REPORT), (ECG, 42)])
def test_wrong_types_do_not_crash(ecg, report):
    assert not check_inputs(ecg, report)["valid"]


def test_preprocessing_minimum_length_is_not_enforced_here():
    assert check_inputs(b"signal\n1\n", b"Synthese fictive")["valid"]


def test_sample_files():
    valid = (ROOT / "samples/ecg_valid.csv").read_bytes()
    report = (ROOT / "samples/report_valid.txt").read_bytes()
    assert check_inputs(valid, report)["valid"]
    assert not check_inputs((ROOT / "samples/ecg_invalid.csv").read_bytes(), report)["valid"]
    assert not check_inputs(valid, (ROOT / "samples/report_invalid.txt").read_bytes())["valid"]
