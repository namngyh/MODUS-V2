"""Dac trung dong lenh tu BUY_VOL/SELL_VOL/BUY_VAL/SELL_VAL.

Khong thuoc bo TA-Lib nhung day la thong tin ma OHLC don thuan khong the tai tao:
hai cay nen giong het nhau co the duoc tao ra boi ap luc mua rong hoac ban rong.
Voi mo hinh intraday, mat can bang dong lenh thuong la nhom co suc du bao cao nhat.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FeatureConfig
from .utils import log_ratio, prefix, safe_div


def build_orderflow(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    bv, sv = df["buy_vol"].to_numpy(), df["sell_vol"].to_numpy()
    bval, sval = df["buy_val"].to_numpy(), df["sell_val"].to_numpy()
    close = df["close"]
    out = pd.DataFrame(index=df.index)

    active = bv + sv
    out["ofi"] = safe_div(bv - sv, active)                      # -1..1
    out["ofi_val"] = safe_div(bval - sval, bval + sval)
    # Da bo (spec 006) - ca bon la san pham phu cua nha cung cap, khong phai thi truong:
    #   participation = (mua + ban) / tong: bang 1 suot 2017-2022, tu 2023 chi phan anh
    #     viec 3,5 % khoi luong khong con duoc phan loai.
    #   buy_px_edge, sell_px_edge, px_spread: CSV dung MOT gia chung cho hai ben nen
    #     gan nhu bang 0; tren DB thi co that - mo hinh se gap luc live mot phan phoi
    #     chua tung thay luc train.

    # Delta luy ke trong phien, chuan hoa theo khoi luong da khop trong phien.
    # Reset moi ngay: delta tich luy tu phien truoc khong con y nghia sau qua dem.
    delta = pd.Series(bv - sv, index=df.index)
    grp = delta.groupby(df["date"], sort=False)
    cum_delta = grp.cumsum()
    cum_active = pd.Series(active, index=df.index).groupby(df["date"], sort=False).cumsum()
    out["cum_delta_day"] = safe_div(cum_delta.to_numpy(), cum_active.to_numpy())

    ofi = out["ofi"]
    for w in cfg.all_periods:
        # Mat can bang trung binh truot: mot bar don le rat nhieu, phai lam muot.
        out[f"ofi_ma{w}"] = ofi.rolling(w, min_periods=max(2, w // 4)).mean()
        # Delta rong chuan hoa theo tong hoat dong trong cung cua so.
        num = pd.Series(bv - sv, index=df.index).rolling(w, min_periods=max(2, w // 4)).sum()
        den = pd.Series(active, index=df.index).rolling(w, min_periods=max(2, w // 4)).sum()
        out[f"ofi_net{w}"] = safe_div(num.to_numpy(), den.to_numpy())

    log_active = np.log1p(active)
    for w in cfg.vol_windows:
        ma = pd.Series(log_active, index=df.index).rolling(w, min_periods=max(3, w // 4)).mean()
        out[f"active_rel{w}"] = log_active - ma.to_numpy()

    # Phan ky: gia tang nhung dong tien ban rong (hoac nguoc lai) - tin hieu dao chieu.
    ret = log_ratio(close, close.shift(1))
    out["flow_price_div"] = np.sign(ret) * (-out["ofi_ma12"].to_numpy())
    return prefix(out, "flow")
