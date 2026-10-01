"""Tien xu ly rieng cho TUNG lan hoc (spec 008, bat bien #20).

Bo cot trung lap va scaler la tham so uoc luong tu du lieu. Khop chung tren ca 2018-2021
thi lan "hoc 2018 -> du bao 2019" da ngam thay so lieu 2019-2021 - trai nguyen tac ngoai
mau. Nen moi lan hoc khop lai chi tren phan hoc cua chinh no.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..scaling import FeatureScaler, prune_columns


def prepare_fold_matrix(features: pd.DataFrame, train_mask: np.ndarray,
                        clip: float = 8.0, mode: str = "robust") -> tuple[np.ndarray, list[str]]:
    """Tra ve (ma tran (T, F) float32 da scale cho MOI nen, danh sach cot giu lai)."""
    keep, _ = prune_columns(features, train_mask)
    scaler = FeatureScaler(clip=clip, mode=mode).fit(features[keep], train_mask)
    return scaler.transform(features[keep]), keep
