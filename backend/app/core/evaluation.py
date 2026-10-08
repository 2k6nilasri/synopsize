import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, TypeVar

T = TypeVar("T")


def _edit_distance(reference: Sequence[T], prediction: Sequence[T]) -> int:
    previous = list(range(len(prediction) + 1))
    for row, reference_char in enumerate(reference, start=1):
        current = [row]
        for column, prediction_char in enumerate(prediction, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (reference_char != prediction_char),
                )
            )
        previous = current
    return previous[-1]


def _metrics(records: List[Dict[str, Any]], bins: int) -> Dict[str, Any]:
    count = len(records)
    exact_matches = 0
    word_errors = 0
    reference_words = 0
    character_errors = 0
    reference_characters = 0
    brier_total = 0.0
    calibration_bins = [
        {"count": 0, "confidence_total": 0.0, "correct_total": 0}
        for _ in range(bins)
    ]

    for record in records:
        reference = " ".join(record["reference"].split())
        prediction = " ".join(record["prediction"].split())
        confidence = record["confidence"]
        correct = reference == prediction
        exact_matches += int(correct)
        confidence_outcome = 1.0 if correct else 0.0
        brier_total += (confidence - confidence_outcome) ** 2

        words_reference = reference.split()
        words_prediction = prediction.split()
        word_errors += _edit_distance(words_reference, words_prediction)
        reference_words += max(1, len(words_reference))
        character_errors += _edit_distance(reference, prediction)
        reference_characters += max(1, len(reference))

        bin_index = min(int(confidence * bins), bins - 1)
        calibration_bins[bin_index]["count"] += 1
        calibration_bins[bin_index]["confidence_total"] += confidence
        calibration_bins[bin_index]["correct_total"] += int(correct)

    ece = 0.0
    summarized_bins = []
    for index, calibration_bin in enumerate(calibration_bins):
        bin_count = calibration_bin["count"]
        if not bin_count:
            continue
        mean_confidence = calibration_bin["confidence_total"] / bin_count
        accuracy = calibration_bin["correct_total"] / bin_count
        ece += (bin_count / count) * abs(mean_confidence - accuracy)
        summarized_bins.append(
            {
                "range": [index / bins, (index + 1) / bins],
                "count": bin_count,
                "mean_confidence": round(mean_confidence, 6),
                "exact_match_rate": round(accuracy, 6),
            }
        )

    return {
        "sample_count": count,
        "exact_match_rate": round(exact_matches / count, 6),
        "word_error_rate": round(word_errors / reference_words, 6),
        "character_error_rate": round(character_errors / reference_characters, 6),
        "brier_score": round(brier_total / count, 6),
        "expected_calibration_error": round(ece, 6),
        "calibration_bins": summarized_bins,
    }


def evaluate_records(
    records: List[Dict[str, Any]], bins: int = 10
) -> Dict[str, Any]:
    if bins < 1:
        raise ValueError("Number of calibration bins must be positive.")
    if not records:
        raise ValueError("Evaluation dataset must contain at least one record.")

    validated: List[Dict[str, Any]] = []
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for line_number, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {line_number} must be a JSON object.")
        reference = record.get("reference")
        prediction = record.get("prediction")
        extractor = record.get("extractor", "unspecified")
        confidence = record.get("confidence")
        if not isinstance(reference, str) or not isinstance(prediction, str):
            raise ValueError(
                f"Record {line_number} needs string reference and prediction fields."
            )
        if not isinstance(extractor, str) or not extractor.strip():
            raise ValueError(f"Record {line_number} has an invalid extractor.")
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
            or not 0 <= confidence <= 1
        ):
            raise ValueError(
                f"Record {line_number} confidence must be a finite number from 0 to 1."
            )
        clean_record = {
            "reference": reference,
            "prediction": prediction,
            "extractor": extractor,
            "confidence": float(confidence),
        }
        validated.append(clean_record)
        grouped[extractor].append(clean_record)

    return {
        "metric_note": (
            "Confidence calibration compares supplied scores with exact block "
            "matches on this labeled dataset; it does not establish correctness "
            "for documents outside this dataset."
        ),
        "overall": _metrics(validated, bins),
        "by_extractor": {
            extractor: _metrics(group, bins)
            for extractor, group in sorted(grouped.items())
        },
    }


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {error.msg}"
                ) from error
    return records


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate extractor outputs against labeled ground truth."
    )
    parser.add_argument("dataset", type=Path, help="Labeled JSONL evaluation set")
    parser.add_argument("--bins", type=int, default=10)
    args = parser.parse_args()
    try:
        report = evaluate_records(_load_jsonl(args.dataset), bins=args.bins)
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
