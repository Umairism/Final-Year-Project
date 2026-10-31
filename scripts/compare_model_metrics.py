#!/usr/bin/env python3
"""
scripts/compare_model_metrics.py

Compares two model evaluation metric JSON files side-by-side and displays
key classification metrics, per-class precision/recall/F1/support, AUROC/AUPRC,
confusion matrices, and deltas.

Does NOT declare an automated clinical winner. Any decision must be made
via clinical and protocol review.

Usage:
    python scripts/compare_model_metrics.py --base path/to/base.json --candidate path/to/cand.json [--base-label "Run 1"] [--candidate-label "Run 3"]
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


def _safe_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _format_val(val: Optional[float], precision: int = 4) -> str:
    if val is None:
        return "N/A"
    return f"{val:.{precision}f}"


def _format_delta(cand: Optional[float], base: Optional[float], precision: int = 4) -> str:
    if cand is None or base is None:
        return "—"
    delta = cand - base
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.{precision}f}"


def load_metrics_json(path: str) -> Dict[str, Any]:
    """Load and validate a metrics JSON file."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Metrics file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Malformed JSON in {path}: {e}")

    if not isinstance(data, dict):
        raise ValueError(f"Root JSON entity in {path} must be an object/dict.")
    return data


def extract_split_metrics(data: Dict[str, Any], split: str) -> Dict[str, Any]:
    """
    Extract accuracy, balanced_accuracy, macro_f1, weighted_f1 for a given split
    (e.g., 'val', 'validation', 'test'). Supports nested dicts or prefixed flat keys.
    """
    split_aliases = [split]
    if split in ("val", "validation"):
        split_aliases = ["validation", "val"]

    candidates = {}
    for s in split_aliases:
        if s in data and isinstance(data[s], dict):
            candidates = data[s]
            break
        elif f"{s}_metrics" in data and isinstance(data[f"{s}_metrics"], dict):
            candidates = data[f"{s}_metrics"]
            break
        elif "metrics" in data and isinstance(data["metrics"], dict) and s in data["metrics"]:
            candidates = data["metrics"][s]
            break

    def _get_key(canonical_name: str, aliases: List[str]) -> Optional[float]:
        # Check in nested candidate dict
        for k in [canonical_name] + aliases:
            if k in candidates:
                return _safe_float(candidates[k])
        # Check flat in root data
        for s in split_aliases:
            for p in ["", f"{s}_", f"{s}."]:
                for k in [canonical_name] + aliases:
                    full = f"{p}{k}"
                    if full in data:
                        return _safe_float(data[full])
                    if "metrics" in data and isinstance(data["metrics"], dict) and full in data["metrics"]:
                        return _safe_float(data["metrics"][full])
        return None

    return {
        "accuracy": _get_key("accuracy", ["acc"]),
        "balanced_accuracy": _get_key("balanced_accuracy", ["balanced_acc", "bacc"]),
        "macro_f1": _get_key("macro_f1", ["macro-F1", "macro_f1_score", "f1_macro"]),
        "weighted_f1": _get_key("weighted_f1", ["weighted-F1", "weighted_f1_score", "f1_weighted"]),
        "auroc": _get_key("auroc", ["roc_auc", "auc", "auroc_macro_ovr"]),
        "auprc": _get_key("auprc", ["pr_auc", "average_precision"]),
    }


def extract_per_class(data: Dict[str, Any], split: str = "test") -> Dict[str, Dict[str, Optional[float]]]:
    """
    Extract per-class metrics: precision, recall, f1-score, support.
    """
    split_aliases = [split]
    if split in ("val", "validation"):
        split_aliases = ["validation", "val"]

    target = None
    for s in split_aliases:
        if s in data and isinstance(data[s], dict) and "per_class" in data[s]:
            target = data[s]["per_class"]
            break
        for key in [f"{s}_per_class", "per_class", f"{s}_classification_report", "classification_report"]:
            if key in data and isinstance(data[key], dict):
                target = data[key]
                break
            if "metrics" in data and isinstance(data["metrics"], dict) and key in data["metrics"]:
                target = data["metrics"][key]
                break
        if target:
            break

    result: Dict[str, Dict[str, Optional[float]]] = {}
    if target:
        for cls_name, vals in target.items():
            if not isinstance(vals, dict):
                continue
            if cls_name.lower() in ["accuracy", "macro avg", "weighted avg", "samples avg"]:
                continue
            result[cls_name] = {
                "precision": _safe_float(vals.get("precision")),
                "recall": _safe_float(vals.get("recall")),
                "f1": _safe_float(vals.get("f1-score") or vals.get("f1") or vals.get("f1_score")),
                "support": _safe_float(vals.get("support")),
            }
    return result


def extract_confusion_matrix(data: Dict[str, Any], split: str = "test") -> Optional[List[List[Any]]]:
    split_aliases = [split]
    if split in ("val", "validation"):
        split_aliases = ["validation", "val"]

    for s in split_aliases:
        if s in data and isinstance(data[s], dict) and "confusion_matrix" in data[s]:
            return data[s]["confusion_matrix"]
        for key in [f"{s}_confusion_matrix", "confusion_matrix", f"{s}_cm", "cm"]:
            if key in data and isinstance(data[key], list):
                return data[key]
            if "metrics" in data and isinstance(data["metrics"], dict) and key in data["metrics"]:
                val = data["metrics"][key]
                if isinstance(val, list):
                    return val
    return None


def print_comparison_table(
    title: str,
    base_label: str,
    cand_label: str,
    metrics: List[Tuple[str, Optional[float], Optional[float]]],
):
    print(f"\n--- {title} ---")
    header = f"{'Metric':<25} | {base_label:<14} | {cand_label:<14} | {'Delta':<12}"
    print(header)
    print("-" * len(header))
    for name, base_v, cand_v in metrics:
        b_str = _format_val(base_v)
        c_str = _format_val(cand_v)
        d_str = _format_delta(cand_v, base_v)
        print(f"{name:<25} | {b_str:<14} | {c_str:<14} | {d_str:<12}")


def print_per_class_table(
    base_label: str,
    cand_label: str,
    base_classes: Dict[str, Dict[str, Optional[float]]],
    cand_classes: Dict[str, Dict[str, Optional[float]]],
):
    all_classes = sorted(list(set(base_classes.keys()) | set(cand_classes.keys())))
    if not all_classes:
        return

    print("\n--- Per-Class Test Metrics ---")
    header = f"{'Class':<12} | {'Metric':<10} | {base_label:<12} | {cand_label:<12} | {'Delta':<10}"
    print(header)
    print("-" * len(header))
    for c in all_classes:
        b_metrics = base_classes.get(c, {})
        c_metrics = cand_classes.get(c, {})
        for m in ["precision", "recall", "f1", "support"]:
            b_val = b_metrics.get(m)
            c_val = c_metrics.get(m)
            d_str = _format_delta(c_val, b_val, precision=2 if m == "support" else 4)
            b_str = _format_val(b_val, precision=0 if m == "support" else 4)
            c_str = _format_val(c_val, precision=0 if m == "support" else 4)
            print(f"{c:<12} | {m:<10} | {b_str:<12} | {c_str:<12} | {d_str:<10}")


def check_split_alignment(
    base_data: Dict[str, Any],
    cand_data: Dict[str, Any],
    base_label: str,
    cand_label: str,
) -> Tuple[bool, List[str]]:
    """
    Verify whether base and candidate share identical validation and test supports.
    Returns (is_aligned, list_of_mismatch_descriptions).
    """
    mismatches = []
    
    for split in ["validation", "test"]:
        base_pc = extract_per_class(base_data, split)
        cand_pc = extract_per_class(cand_data, split)
        
        base_tot = sum(v.get("support", 0.0) or 0.0 for v in base_pc.values()) if base_pc else 0.0
        cand_tot = sum(v.get("support", 0.0) or 0.0 for v in cand_pc.values()) if cand_pc else 0.0
        
        if base_tot > 0 and cand_tot > 0 and abs(base_tot - cand_tot) > 1e-5:
            mismatches.append(
                f"{split.capitalize()} total support mismatch: [{base_label}: {int(base_tot)}] vs [{cand_label}: {int(cand_tot)}]"
            )
        
        # Check per-class support
        all_classes = set(base_pc.keys()) | set(cand_pc.keys())
        for cls in all_classes:
            b_sup = base_pc.get(cls, {}).get("support")
            c_sup = cand_pc.get(cls, {}).get("support")
            if b_sup is not None and c_sup is not None and abs(b_sup - c_sup) > 1e-5:
                mismatches.append(
                    f"{split.capitalize()} '{cls}' support mismatch: [{base_label}: {int(b_sup)}] vs [{cand_label}: {int(c_sup)}]"
                )

    return len(mismatches) == 0, mismatches


def main():
    parser = argparse.ArgumentParser(description="Side-by-side model metrics comparison.")
    parser.add_argument("--base", required=True, help="Path to base evaluation_metrics.json")
    parser.add_argument("--candidate", required=True, help="Path to candidate evaluation_metrics.json")
    parser.add_argument("--base-label", default="Base", help="Display label for base run")
    parser.add_argument("--candidate-label", default="Candidate", help="Display label for candidate run")
    parser.add_argument("--strict", action="store_true", help="Fail if dataset splits or supports differ")

    args = parser.parse_args()

    try:
        base_data = load_metrics_json(args.base)
    except Exception as e:
        sys.stderr.write(f"ERROR loading base metrics: {e}\n")
        sys.exit(1)

    try:
        cand_data = load_metrics_json(args.candidate)
    except Exception as e:
        sys.stderr.write(f"ERROR loading candidate metrics: {e}\n")
        sys.exit(1)

    base_label = args.base_label
    cand_label = args.candidate_label

    is_aligned, mismatches = check_split_alignment(base_data, cand_data, base_label, cand_label)

    print("=" * 70)
    print(f"HealSense Model Metrics Comparison: [{base_label}] vs [{cand_label}]")
    print("=" * 70)

    if not is_aligned:
        print("\n" + "!" * 70)
        print(" WARNING: DATASET SPLIT / COHORT MISMATCH DETECTED")
        print(" The compared runs were evaluated on DIFFERENT dataset cohorts or splits:")
        for m in mismatches[:6]:
            print(f"   • {m}")
        if len(mismatches) > 6:
            print(f"   • ... and {len(mismatches) - 6} more mismatch(es)")
        print(" DELTAS DO NOT REFLECT A STRICT CONTROLLED SAME-SPLIT A/B TEST.")
        print(" Deltas compound model architecture shifts with patient cohort variance.")
        print("!" * 70)
        if args.strict:
            sys.stderr.write("\nERROR: Aborting comparison because --strict was specified and splits differ.\n")
            sys.exit(2)

    # Validation
    base_val = extract_split_metrics(base_data, "val")
    cand_val = extract_split_metrics(cand_data, "val")
    val_rows = [
        ("Accuracy", base_val["accuracy"], cand_val["accuracy"]),
        ("Balanced Accuracy", base_val["balanced_accuracy"], cand_val["balanced_accuracy"]),
        ("Macro-F1", base_val["macro_f1"], cand_val["macro_f1"]),
        ("Weighted-F1", base_val["weighted_f1"], cand_val["weighted_f1"]),
    ]
    if base_val["auroc"] is not None or cand_val["auroc"] is not None:
        val_rows.append(("AUROC", base_val["auroc"], cand_val["auroc"]))
    if base_val["auprc"] is not None or cand_val["auprc"] is not None:
        val_rows.append(("AUPRC", base_val["auprc"], cand_val["auprc"]))
    print_comparison_table("Validation Set Metrics", base_label, cand_label, val_rows)

    # Test
    base_test = extract_split_metrics(base_data, "test")
    cand_test = extract_split_metrics(cand_data, "test")
    test_rows = [
        ("Accuracy", base_test["accuracy"], cand_test["accuracy"]),
        ("Balanced Accuracy", base_test["balanced_accuracy"], cand_test["balanced_accuracy"]),
        ("Macro-F1", base_test["macro_f1"], cand_test["macro_f1"]),
        ("Weighted-F1", base_test["weighted_f1"], cand_test["weighted_f1"]),
    ]
    if base_test["auroc"] is not None or cand_test["auroc"] is not None:
        test_rows.append(("AUROC", base_test["auroc"], cand_test["auroc"]))
    if base_test["auprc"] is not None or cand_test["auprc"] is not None:
        test_rows.append(("AUPRC", base_test["auprc"], cand_test["auprc"]))
    print_comparison_table("Test Set Metrics", base_label, cand_label, test_rows)

    # Per-Class Test Metrics
    base_cls = extract_per_class(base_data, "test")
    cand_cls = extract_per_class(cand_data, "test")
    print_per_class_table(base_label, cand_label, base_cls, cand_cls)

    # Confusion Matrices
    base_cm = extract_confusion_matrix(base_data, "test")
    cand_cm = extract_confusion_matrix(cand_data, "test")
    if base_cm or cand_cm:
        print("\n--- Confusion Matrices (Test) ---")
        if base_cm:
            print(f"[{base_label}]:")
            for row in base_cm:
                print("  ", row)
        if cand_cm:
            print(f"[{cand_label}]:")
            for row in cand_cm:
                print("  ", row)

    print("\n" + "=" * 70)
    print("NOTE: Metric deltas are informational. No automated clinical winner is declared.")
    print("Review validation macro-F1, balanced accuracy, warning/critical F1, and critical recall.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()

