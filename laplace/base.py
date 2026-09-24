"""Bien doi co ban tu OHLC - tang nen tang duoi moi indicator.

Nguyen tac xuyen suot: khong bao gio dua muc gia tho vao mo hinh. Gia VN30F di tu
~600 (2017) len ~1900 (2026); mang hoc tren muc gia se khong tong quat hoa sang
vung gia chua tung thay. Moi dac trung o day deu la ty le hoac log-ty-le nen
phan phoi on dinh theo thoi gian.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FeatureConfig
from .utils import causal_seasonal_mean, log_ratio, prefix, safe_div

LOG2 = np.log(2.0)


def build_base(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    prev_c = c.shift(1)
    out = pd.DataFrame(index=df.index)

    # --- hinh hoc trong mot cay nen (khong dung cua so) ---
    out["ret1"] = log_ratio(c, prev_c)
    out["gap"] = log_ratio(o, prev_c)                    # nhay gia dau bar / qua dem
    out["oc"] = log_ratio(c, o)                          # than nen co dau
    out["hl"] = log_ratio(h, l)                          # bien do (uoc luong Parkinson)
    out["ho"] = log_ratio(h, o)
    out["lo"] = log_ratio(l, o)
    out["hc"] = log_ratio(h, c)
    out["lc"] = log_ratio(l, c)

    rng = (h - l).to_numpy()
    body_hi = np.maximum(o.to_numpy(), c.to_numpy())
    body_lo = np.minimum(o.to_numpy(), c.to_numpy())
    # Bar phang (H==L, hay gap o bar ATC) -> quy uoc 0 thay vi inf.
    out["clv"] = safe_div((c - l).to_numpy() - (h - c).to_numpy(), rng)   # -1..1
    out["body_frac"] = safe_div(np.abs(c - o).to_numpy(), rng)           # 0..1
    out["upper_wick"] = safe_div(h.to_numpy() - body_hi, rng)
    out["lower_wick"] = safe_div(body_lo - l.to_numpy(), rng)
    out["direction"] = np.sign((c - o).to_numpy())
    out["is_flat"] = (rng <= 0).astype("float64")

    # --- loi nhuan da tam nhin ---
    # Chia cho sqrt(k) de moi tam nhin co cung do lon: duoi buoc ngau nhien,
    # phuong sai cua loi nhuan k-buoc ty le voi k.
    for k in cfg.return_horizons:
        out[f"ret{k}"] = log_ratio(c, c.shift(k)) / np.sqrt(k)

    # --- do bien dong ---
    r1 = out["ret1"]
    for w in cfg.vol_windows:
        rv = r1.rolling(w, min_periods=max(3, w // 4)).std()
        out[f"rv{w}"] = rv
        out[f"park{w}"] = np.sqrt(
            (out["hl"] ** 2).rolling(w, min_periods=max(3, w // 4)).mean() / (4 * LOG2)
        )
        gk = 0.5 * out["hl"] ** 2 - (2 * LOG2 - 1) * out["oc"] ** 2
        out[f"gk{w}"] = np.sqrt(gk.rolling(w, min_periods=max(3, w // 4)).mean().clip(lower=0))
        rs = out["ho"] * out["hc"] + out["lo"] * out["lc"]
        out[f"rs{w}"] = np.sqrt(rs.rolling(w, min_periods=max(3, w // 4)).mean().clip(lower=0))

    # Chuan hoa loi nhuan theo bien dong: don vi "bao nhieu sigma", giup mo hinh
    # so sanh duoc mot cu 5 diem nam 2018 voi cung 5 diem nam 2026.
    base_vol = r1.rolling(cfg.vol_windows[-1], min_periods=50).std()
    for k in cfg.return_horizons:
        out[f"ret{k}_z"] = safe_div(out[f"ret{k}"].to_numpy(), base_vol.to_numpy())

    # Ty le bien dong ngan/dai: >1 = che do vua bung bien dong.
    fast, slow = cfg.vol_windows[0], cfg.vol_windows[-1]
    out["vol_ratio"] = np.log(safe_div(out[f"rv{fast}"].to_numpy(), out[f"rv{slow}"].to_numpy(), 1.0).clip(1e-6))

    # --- vi tri trong bien do va chat luong xu the ---
    for w in cfg.all_periods:
        hh = h.rolling(w, min_periods=max(2, w // 4)).max()
        ll = l.rolling(w, min_periods=max(2, w // 4)).min()
        out[f"pos{w}"] = safe_div((c - ll).to_numpy(), (hh - ll).to_numpy(), 0.5) * 2 - 1
        out[f"dhh{w}"] = log_ratio(c, hh)                 # <=0, khoang cach toi dinh
        out[f"dll{w}"] = log_ratio(c, ll)                 # >=0, khoang cach toi day
        # He so hieu qua Kaufman: |dich chuyen rong| / |tong duong di|.
        # ~1 = xu the sach, ~0 = di ngang nhieu.
        net = (c - c.shift(w)).abs()
        path = c.diff().abs().rolling(w, min_periods=max(2, w // 4)).sum()
        out[f"er{w}"] = safe_div(net.to_numpy(), path.to_numpy())

    out = pd.concat([out, _volume_block(df, cfg)], axis=1)
    return prefix(out, "base")


def _volume_block(df: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    """Khoi khoi luong o dang khong thu nguyen.

    Khoi luong tho tang truong nhieu lan qua 9 nam, khong the dua thang vao mang.
    Tat ca deu la ty le so voi mot chuan lich su.
    """
    v = df["volume"]
    log_v = np.log1p(v)
    out = pd.DataFrame(index=df.index)

    for w in cfg.vol_windows:
        ma = log_v.rolling(w, min_periods=max(3, w // 4)).mean()
        sd = log_v.rolling(w, min_periods=max(3, w // 4)).std()
        out[f"vol_rel{w}"] = log_v - ma
        out[f"vol_z{w}"] = safe_div((log_v - ma).to_numpy(), sd.to_numpy())

    # Khu mua vu trong phien: khoi luong bar 09:00 va bar 11:20 khac han nhau ve
    # ban chat, so sanh truc tiep la vo nghia.
    seasonal = causal_seasonal_mean(log_v, df["bar_of_day"], lookback=60)
    out["vol_seasonal_adj"] = log_v - seasonal

    out["dollar_vol"] = np.log1p(v * df["close"]) - np.log1p(v * df["close"]).rolling(
        cfg.vol_windows[-1], min_periods=50
    ).mean()
    out["vol_ret_corr"] = (
        np.sign(df["close"].diff().to_numpy()) * out["vol_z" + str(cfg.vol_windows[0])]
    )
    return out
