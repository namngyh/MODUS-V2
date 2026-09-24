"""Dac trung lich va vi tri trong phien giao dich.

Bar 5 phut khong dong nhat: bar mo cua, bar quanh nghi trua va bar ATC co dac tinh
bien dong/thanh khoan rat khac nhau. Mo hinh chuoi khong tu suy ra duoc dieu do neu
khong duoc noi dang o dau trong phien.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FeatureConfig
from .loader import days_to_expiry
from .utils import prefix, safe_div


def _cyc(values, period):
    ang = 2 * np.pi * np.asarray(values, dtype="float64") / period
    return np.sin(ang), np.cos(ang)


def build_session(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    idx = df.index
    out = pd.DataFrame(index=idx)

    minute = idx.hour * 60 + idx.minute
    end_h, end_m, _ = (int(v) for v in cfg.session_end.split(":"))
    end_minute = end_h * 60 + end_m

    progress = safe_div(df["bar_of_day"].to_numpy(), (df["bars_prev_day"] - 1).to_numpy(), 0.0)
    out["day_progress"] = np.clip(progress, 0.0, 1.0) * 2 - 1
    out["is_first_bar"] = (df["bar_of_day"] == 0).astype("float64")
    # Moc dong phien lay tu lich giao dich, khong phai tu viec dem bar da xay ra:
    # "day la bar cuoi cua phien" chi biet duoc sau khi phien ket thuc.
    out["is_last_bar"] = (minute >= end_minute).astype("float64")
    out["bars_to_close"] = np.log1p(np.clip((end_minute - minute) / 5.0, 0, None))

    # Chu ky trong ngay ma hoa bang sin/cos: 09:00 va 14:45 khong duoc phep o hai dau
    # mot thang do tuyen tinh khi mang coi chung la mot dai luong lien tuc.
    s, c = _cyc(minute, 24 * 60)
    out["tod_sin"], out["tod_cos"] = s, c
    out["minute_norm"] = (minute - 9 * 60) / (5.75 * 60)

    # Khoang cach thuc te toi bar truoc: bat duoc nghi trua (90 phut) va qua dem.
    gap_min = pd.Series(idx, index=idx).diff().dt.total_seconds().to_numpy() / 60.0
    out["bar_gap"] = np.log1p(np.nan_to_num(gap_min, nan=5.0).clip(0, 60 * 24))
    out["after_lunch"] = (np.nan_to_num(gap_min, nan=5.0) > 30).astype("float64") * (
        out["is_first_bar"].to_numpy() == 0
    )

    dow = idx.dayofweek.to_numpy()
    s, c = _cyc(dow, 7)
    out["dow_sin"], out["dow_cos"] = s, c
    out["is_monday"] = (dow == 0).astype("float64")
    out["is_friday"] = (dow == 4).astype("float64")

    s, c = _cyc(idx.month.to_numpy() - 1, 12)
    out["month_sin"], out["month_cos"] = s, c
    out["dom_norm"] = (idx.day.to_numpy() - 15.5) / 15.5

    # VN30F1M la hop dong xoay vong theo thang: gan dao han, basis va thanh khoan
    # doi hanh vi ro ret, va co hieu ung dao hop dong.
    dte = days_to_expiry(idx)
    out["dte"] = dte.to_numpy() / 30.0
    out["dte_inv"] = 1.0 / (1.0 + dte.to_numpy())
    out["is_expiry_week"] = (dte.to_numpy() <= 5).astype("float64")
    out["is_expiry_day"] = (dte.to_numpy() == 0).astype("float64")
    return prefix(out, "session")
