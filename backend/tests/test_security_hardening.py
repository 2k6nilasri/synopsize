import socket
from unittest.mock import patch

import pytest

import app.core.security as security
from app.core.antivirus import (
    AntivirusUnavailableError,
    MalwareDetectedError,
    scan_with_clamd,
)
from app.core.evaluation import evaluate_records


class FakeClamdSocket:
    def __init__(self, response: bytes):
        self.response = response
        self.sent = bytearray()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def settimeout(self, _timeout):
        pass

    def sendall(self, data):
        self.sent.extend(data)

    def recv(self, _size):
        response, self.response = self.response, b""
        return response


def test_clamd_streams_content_and_returns_clean_result():
    scanner = FakeClamdSocket(b"stream: OK\0")
    with patch("app.core.antivirus.socket.create_connection", return_value=scanner):
        result = scan_with_clamd(b"document bytes", "clamav", 3310, 2)

    assert result == "stream: OK"
    assert b"document bytes" in scanner.sent
    assert scanner.sent.endswith(b"\0\0\0\0")


def test_clamd_rejects_detected_malware():
    scanner = FakeClamdSocket(b"stream: Eicar-Test-Signature FOUND\0")
    with patch("app.core.antivirus.socket.create_connection", return_value=scanner):
        with pytest.raises(MalwareDetectedError, match="FOUND"):
            scan_with_clamd(b"malware", "clamav", 3310, 2)


def test_clamd_connection_errors_are_explicit():
    with patch(
        "app.core.antivirus.socket.create_connection",
        side_effect=socket.timeout("timed out"),
    ):
        with pytest.raises(AntivirusUnavailableError, match="Could not complete"):
            scan_with_clamd(b"content", "clamav", 3310, 0.1)


def test_required_antivirus_mode_fails_closed_when_scanner_unavailable(monkeypatch):
    monkeypatch.setattr(security, "ANTIVIRUS_MODE", "required")

    def scanner_unavailable(*_args):
        raise AntivirusUnavailableError("scanner offline")

    monkeypatch.setattr(security, "scan_with_clamd", scanner_unavailable)
    report = security.validate_uploaded_file(b"plain text", "note.txt", store=False)

    antivirus = next(check for check in report["checks"] if check["name"] == "Antivirus Scan")
    assert report["is_valid"] is False
    assert antivirus["passed"] is False
    assert antivirus["status"] == "unavailable"


def test_disabled_antivirus_is_reported_as_not_run(monkeypatch):
    monkeypatch.setattr(security, "ANTIVIRUS_MODE", "disabled")
    report = security.validate_uploaded_file(b"plain text", "note.txt", store=False)

    antivirus = next(check for check in report["checks"] if check["name"] == "Antivirus Scan")
    assert report["is_valid"] is True
    assert antivirus["passed"] is None
    assert antivirus["status"] == "disabled"


def test_detected_malware_is_blocked(monkeypatch):
    monkeypatch.setattr(security, "ANTIVIRUS_MODE", "required")
    monkeypatch.setattr(
        security,
        "scan_with_clamd",
        lambda *_args: (_ for _ in ()).throw(MalwareDetectedError("test malware")),
    )
    report = security.validate_uploaded_file(b"infected", "note.txt", store=False)

    antivirus = next(check for check in report["checks"] if check["name"] == "Antivirus Scan")
    assert report["is_valid"] is False
    assert antivirus["status"] == "infected"
    assert "test malware" in antivirus["message"]


def test_evaluation_reports_accuracy_and_calibration_by_extractor():
    report = evaluate_records(
        [
            {
                "extractor": "tesseract",
                "confidence": 0.9,
                "reference": "recognized text",
                "prediction": "recognized text",
            },
            {
                "extractor": "tesseract",
                "confidence": 0.8,
                "reference": "correct text",
                "prediction": "wrong text",
            },
        ],
        bins=5,
    )

    assert report["overall"]["sample_count"] == 2
    assert report["overall"]["exact_match_rate"] == 0.5
    assert report["overall"]["expected_calibration_error"] == 0.35
    assert report["by_extractor"]["tesseract"]["word_error_rate"] > 0


def test_evaluation_rejects_invalid_confidence():
    with pytest.raises(ValueError, match="finite number from 0 to 1"):
        evaluate_records(
            [{"reference": "a", "prediction": "a", "confidence": 1.1}]
        )
