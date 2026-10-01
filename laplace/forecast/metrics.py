"""Thuoc do cho LSTM du bao (spec 008 muc 6).

Khong cham bang ty le doan dung: no thuong cho viec chon cau hoi de, va bo qua do tu tin.
Thuoc do chinh la entropy cheo (nats, nho hon la tot hon), so voi moc "doan theo ty le
nhom" cua phan hoc.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .labels import UP

EPS = 1e-12


def baseline_probs(labels: np.ndarray, n_classes: int = 3) -> np.ndarray:
    """Moc so sanh: luon noi ty le nhom cua phan hoc."""
    counts = np.bincount(np.asarray(labels, dtype=np.int64), minlength=n_classes)
    return counts / counts.sum()


def log_loss(prob: np.ndarray, labels: np.ndarray) -> float:
    p = np.clip(prob[np.arange(len(labels)), labels], EPS, 1.0)
    return float(-np.log(p).mean())


def calibration_up(prob: np.ndarray, labels: np.ndarray, bins: int = 10) -> pd.DataFrame:
    """'Noi X % len truoc thi thuc te len truoc bao nhieu %' theo 10 khoang."""
    p = prob[:, UP]
    hit = (labels == UP).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    which = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    rows = []
    for b in range(bins):
        m = which == b
        if m.any():
            rows.append({"khoang": f"{edges[b]:.1f}-{edges[b + 1]:.1f}", "so_nen": int(m.sum()),
                         "du_bao_tb": float(p[m].mean()), "thuc_te": float(hit[m].mean())})
    return pd.DataFrame(rows)


def evaluate(prob: np.ndarray, labels: np.ndarray, base: np.ndarray) -> dict:
    model_ll = log_loss(prob, labels)
    base_ll = log_loss(np.tile(base, (len(labels), 1)), labels)
    cal = calibration_up(prob, labels)
    gap = (cal["du_bao_tb"] - cal["thuc_te"]).abs()
    return {
        "n": int(len(labels)),
        "log_loss": model_ll,
        "log_loss_baseline": base_ll,
        "improvement": base_ll - model_ll,          # > 0 nghia la hon moc
        "ece_up": float((gap * cal["so_nen"]).sum() / cal["so_nen"].sum()),
        "class_freq": baseline_probs(labels).tolist(),
        "calibration_up": cal.to_dict(orient="records"),
    }
