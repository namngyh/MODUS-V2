"""Lich hoc ngoai mau theo nam (KIENTRUC muc 3, spec 008).

    oof_2019 : hoc 2018            -> du bao 2019   (du lieu cho Meta)
    oof_2020 : hoc 2018-2019       -> du bao 2020
    oof_2021 : hoc 2018-2020       -> du bao 2021
    final    : hoc 2018-2021 (train) -> du bao valid 2022 (cham diem)

Bat bien #20: khong nen hoc nao co dap an cham giai doan du bao. Nhan nhin truoc toi nen
`end[t]`, nen nen t chi duoc hoc khi end[t] < nen dau tien cua giai doan du bao.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..scaling import TimeSplit


@dataclass
class Fold:
    name: str
    train_ends: np.ndarray       # chi so nen cuoi cua so dung de hoc (da purge)
    predict_ends: np.ndarray     # chi so nen cuoi cua so can du bao
    train_mask: np.ndarray       # (T,) bool: phan hoc - noi DUY NHAT duoc khop tien xu ly


def make_schedule(index: pd.DatetimeIndex, split: TimeSplit, end: np.ndarray,
                  session: np.ndarray | None = None, window: int = 64) -> list[Fold]:
    """Cac lan hoc theo thu tu. `end` la nen cuoi ma nhan cua moi nen nhin toi."""
    n = len(index)
    years = np.asarray(index.year)
    train = np.asarray(split.train)
    has_history = np.arange(n) >= window - 1
    train_years = sorted(set(years[train].tolist()))

    def fold(name: str, fit_years: list[int], predict_mask: np.ndarray) -> Fold:
        mask = train & np.isin(years, fit_years)
        pred = np.flatnonzero(predict_mask & has_history)
        cand = np.flatnonzero(mask & has_history)
        ends = cand[end[cand] < pred.min()]          # purge: dap an khong cham du bao
        return Fold(name, ends, pred, mask)

    folds = [fold(f"oof_{y}", train_years[:i], train & (years == y))
             for i, y in enumerate(train_years) if i > 0]
    folds.append(fold("final", train_years, np.asarray(split.valid)))
    return folds


def split_train_holdout(train_ends: np.ndarray, end: np.ndarray,
                        holdout_frac: float = 0.1) -> tuple[np.ndarray, np.ndarray]:
    """10 % cuoi theo thoi gian de canh dung; purge giua hai phan nhu giua hoc va du bao."""
    ends = np.sort(train_ends)
    cut = int(round(len(ends) * (1 - holdout_frac)))
    hold = ends[cut:]
    fit = ends[:cut]
    fit = fit[end[fit] < hold.min()]
    return fit, hold
