"""
Unit tests for scripts/compare_model_metrics.py
Uses isolated temporary JSON fixtures to test metrics comparison logic
without inventing real project evaluation metrics.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def test_compare_model_metrics_smoke():
    repo_root = Path(__file__).resolve().parent.parent.parent
    script_path = repo_root / "scripts" / "compare_model_metrics.py"

    dummy_base = {
        "val": {"accuracy": 0.60, "balanced_accuracy": 0.55, "macro_f1": 0.52},
        "test": {"accuracy": 0.59, "balanced_accuracy": 0.54, "macro_f1": 0.51, "weighted_f1": 0.58},
        "test_per_class": {
            "normal": {"precision": 0.70, "recall": 0.80, "f1": 0.75, "support": 100},
            "warning": {"precision": 0.50, "recall": 0.40, "f1": 0.45, "support": 50},
            "critical": {"precision": 0.40, "recall": 0.30, "f1": 0.35, "support": 30},
        },
        "test_confusion_matrix": [[80, 15, 5], [20, 20, 10], [10, 11, 9]],
    }

    dummy_cand = {
        "val": {"accuracy": 0.61, "balanced_accuracy": 0.57, "macro_f1": 0.56},
        "test": {"accuracy": 0.60, "balanced_accuracy": 0.58, "macro_f1": 0.57, "weighted_f1": 0.61},
        "test_per_class": {
            "normal": {"precision": 0.71, "recall": 0.75, "f1": 0.73, "support": 100},
            "warning": {"precision": 0.52, "recall": 0.45, "f1": 0.48, "support": 50},
            "critical": {"precision": 0.42, "recall": 0.50, "f1": 0.46, "support": 30},
        },
        "test_confusion_matrix": [[75, 18, 7], [18, 22, 10], [8, 7, 15]],
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        base_path = Path(tmpdir) / "base_eval.json"
        cand_path = Path(tmpdir) / "cand_eval.json"

        with open(base_path, "w", encoding="utf-8") as f:
            json.dump(dummy_base, f)
        with open(cand_path, "w", encoding="utf-8") as f:
            json.dump(dummy_cand, f)

        res = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--base",
                str(base_path),
                "--candidate",
                str(cand_path),
                "--base-label",
                "Dummy Base",
                "--candidate-label",
                "Dummy Cand",
            ],
            capture_output=True,
            text=True,
        )

        assert res.returncode == 0, f"Script failed with stderr:\n{res.stderr}"
        assert "HealSense Model Metrics Comparison" in res.stdout
        assert "Validation Set Metrics" in res.stdout
        assert "Test Set Metrics" in res.stdout
        assert "Per-Class Test Metrics" in res.stdout
        assert "NOTE: Metric deltas are informational." in res.stdout

