"""Tai lap hai bot AFL trong bot/ bang Python.

Sinh ra hai thu tach biet nhau:

  1. `build_bot_features()` - cac dai luong lien tuc va trang thai trung gian ma
     hai bot dung lam dau vao (SuperTrend, STORSI, Roofing Filter, MomZ...). Day la
     *dac trung*, di vao ma tran X cua mo hinh.

  2. `build_bot_signals()`  - quyet dinh cuoi cung cua moi bot duoi dang chuoi vi
     the {-1, 0, 1}. Day *khong* phai dac trung: no la y kien cua mot chuyen gia
     ben ngoai de agent doi chieu voi quyet dinh cua chinh no (imitation warm-start,
     reward shaping, hoac chi de do luong do lech).

Tham so lay dung gia tri mac dinh cua Optimize() trong file AFL - AmiBroker tra ve
doi so thu hai khi khong chay optimization. Roofing chay o STAGE = 0 nen bon nut loi
bi khoa o LengthFix/HPfix/SSfix/SigFix.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import talib

from .afl import cross, exrem, flip, position_from_signals, ref, stoch_k
from .config import FeatureConfig
from .utils import log_ratio, prefix, safe_div, safe_log


@dataclass(frozen=True)
class KesptParams:
    """Mac dinh cua Optimize() trong 'KESPT 01-21 (Netprofit).afl'."""

    factor: float = 3.0          # ST Factor
    atr_period: int = 28         # ST ATR
    rsi_period: int = 22         # KF Periods
    ksmooth: int = 43            # KF %K avg
    reg_period: int = 54         # KF LinRegPeriods
    ma_period: int = 34          # KF MAPeriods
    n1: float = 3.7              # KF N1
    ema_period: int = 300        # EMA Periods


@dataclass(frozen=True)
class RoofingParams:
    """Gia tri chot o STAGE = 0 trong 'roofing2.afl'."""

    length: int = 240            # LengthFix - EMA loc xu the
    hp_period: int = 120         # HPfix     - cutoff high-pass
    ss_period: int = 22          # SSfix     - super smoother
    sig_len: int = 10            # SigFix    - WMA duong tin hieu
    mom_len: int = 45            # Mom_Len
    mom_norm: int = 160          # Mom_Norm
    mom_thr: float = 0.72        # Mom_Thr


@dataclass
class BotRun:
    """Ket qua chay mot bot: dai luong trung gian + bon tin hieu + chuoi vi the."""

    values: dict[str, np.ndarray]
    buy: np.ndarray
    sell: np.ndarray
    short: np.ndarray
    cover: np.ndarray
    position: np.ndarray


# --------------------------------------------------------------------------- #
# SuperTrend - vong lap de quy, phai giu nguyen thu tu cap nhat cua ban AFL
# --------------------------------------------------------------------------- #
def supertrend(high, low, close, factor: float, period: int):
    """Ban dich sat vong for trong KESPT.

    Up/Dn duoc sua tai cho trong vong lap va bar sau doc lai gia tri da sua cua bar
    truoc, nen khong the vector hoa. Thu tu bon buoc - cap nhat trend, tinh flag,
    keo bang theo huong co loi, reset bang khi dao chieu - phai giu dung nguyen ban.
    """
    high = np.asarray(high, dtype="float64")
    low = np.asarray(low, dtype="float64")
    close = np.asarray(close, dtype="float64")
    n = len(close)

    iatr = talib.ATR(high, low, close, timeperiod=period)
    hlc3 = (high + low + close) / 3.0
    up = hlc3 + factor * iatr
    dn = hlc3 - factor * iatr

    trend = np.ones(n, dtype="int8")
    line = np.full(n, np.nan)
    change_of_trend = 0

    for i in range(1, n):
        trend[i] = trend[i - 1]
        if close[i] > up[i - 1]:
            trend[i] = 1
            if trend[i - 1] == -1:
                change_of_trend = 1
        elif close[i] < dn[i - 1]:
            trend[i] = -1
            if trend[i - 1] == 1:
                change_of_trend = 1
        else:
            change_of_trend = 0

        flag = trend[i] < 0 and trend[i - 1] > 0
        flagh = trend[i] > 0 and trend[i - 1] < 0

        if trend[i] > 0 and dn[i] < dn[i - 1]:
            dn[i] = dn[i - 1]
        if trend[i] < 0 and up[i] > up[i - 1]:
            up[i] = up[i - 1]

        if flag:
            up[i] = (high[i] + low[i]) / 2 + factor * iatr[i]
        if flagh:
            dn[i] = (high[i] + low[i]) / 2 - factor * iatr[i]

        line[i] = dn[i] if trend[i] == 1 else up[i]
        if change_of_trend:
            change_of_trend = 0

    return up, dn, trend, line, iatr


# --------------------------------------------------------------------------- #
# Ehlers Roofing Filter
# --------------------------------------------------------------------------- #
def roofing_filter(close, hp_period: int, ss_period: int):
    """High-pass 2 cuc + Super Smoother (Butterworth 2 cuc) cua John Ehlers.

    AFL khoi tao `HP = 0` va `Filt = 0` cho toan mang roi chay vong tu i = 2, nen
    hai phan tu dau la 0 chu khong phai NaN - giu dung vay de so khop tin hieu.
    """
    close = np.asarray(close, dtype="float64")
    n = len(close)

    w = 0.707 * 2 * np.pi / hp_period
    alpha1 = (np.cos(w) + np.sin(w) - 1) / np.cos(w)
    k1 = (1 - alpha1 / 2) ** 2
    k2 = 2 * (1 - alpha1)
    k3 = (1 - alpha1) ** 2

    hp = np.zeros(n)
    for i in range(2, n):
        hp[i] = (k1 * (close[i] - 2 * close[i - 1] + close[i - 2])
                 + k2 * hp[i - 1] - k3 * hp[i - 2])

    a1 = np.exp(-1.414 * np.pi / ss_period)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / ss_period)
    c2, c3 = b1, -a1 * a1
    c1 = 1 - c2 - c3

    filt = np.zeros(n)
    for i in range(2, n):
        filt[i] = c1 * (hp[i] + hp[i - 1]) / 2 + c2 * filt[i - 1] + c3 * filt[i - 2]

    return hp, filt


# --------------------------------------------------------------------------- #
# Chay tung bot
# --------------------------------------------------------------------------- #
def run_kespt(df: pd.DataFrame, p: KesptParams = KesptParams()) -> BotRun:
    o, h, l, c = (df[k].to_numpy(dtype="float64") for k in ("open", "high", "low", "close"))

    up, dn, trend, line, iatr = supertrend(h, l, c, p.factor, p.atr_period)
    buy2 = flip(trend == 1, trend == -1)
    short2 = flip(trend == -1, trend == 1)

    rsi = talib.RSI(c, timeperiod=p.rsi_period)
    stok = stoch_k(h, l, c, p.rsi_period, p.ksmooth)
    lrsi = talib.LINEARREG(rsi, timeperiod=p.reg_period)
    lsto = talib.LINEARREG(stok, timeperiod=p.reg_period)
    storsi = p.n1 * lrsi + lsto
    storsi_ma = talib.WMA(storsi, timeperiod=p.ma_period)
    hiskf = storsi - storsi_ma

    buy1 = flip(cross(storsi, storsi_ma), cross(storsi_ma, storsi))
    short1 = flip(cross(storsi_ma, storsi), cross(storsi, storsi_ma))

    ema = talib.EMA(c, timeperiod=p.ema_period)

    buy_sig = buy1 & buy2
    short_sig = short1 & short2
    buy = buy_sig & (c > ema)
    short = short_sig & (c < ema)
    sell = short_sig.copy()          # dao chieu: tin hieu short dong lenh long
    cover = buy_sig.copy()

    buy = exrem(buy, sell)
    sell = exrem(sell, buy)
    short = exrem(short, cover)
    cover = exrem(cover, short)

    values = {
        "st_up": up, "st_dn": dn, "st_line": line, "st_trend": trend.astype("float64"),
        "atr": iatr, "rsi": rsi, "stochk": stok, "lrsi": lrsi, "lsto": lsto,
        "storsi": storsi, "storsi_ma": storsi_ma, "hiskf": hiskf, "ema": ema,
        "kf_state": np.where(buy1, 1.0, np.where(short1, -1.0, 0.0)),
        "sig_state": buy_sig.astype("float64") - short_sig.astype("float64"),
        "n1": np.full(len(c), p.n1),
    }
    return BotRun(values, buy, sell, short, cover,
                  position_from_signals(buy, sell, short, cover))


def run_roofing(df: pd.DataFrame, p: RoofingParams = RoofingParams()) -> BotRun:
    c = df["close"].to_numpy(dtype="float64")

    hp, filt = roofing_filter(c, p.hp_period, p.ss_period)
    f0 = filt
    s0 = talib.WMA(filt, timeperiod=p.sig_len)

    mom = filt - ref(filt, -p.mom_len)
    momz = mom / (talib.STDDEV(mom, timeperiod=p.mom_norm, nbdev=1.0) + 1e-6)

    buy0 = cross(f0, s0)
    short0 = cross(s0, f0)
    open_buy = flip(buy0, short0)
    open_short = flip(short0, buy0)

    ema = talib.EMA(c, timeperiod=p.length)
    emafilter = ref(ema, -1)                    # AFL: Ref(EMA(C, length), -1)

    buy = open_buy & (c > emafilter) & (momz > p.mom_thr)
    sell = short0.copy()
    short = open_short & (c < emafilter) & (momz < -p.mom_thr)
    cover = buy0.copy()

    buy = exrem(buy, sell)
    sell = exrem(sell, buy)
    short = exrem(short, cover)
    cover = exrem(cover, short)

    values = {
        "hp": hp, "filt": f0, "signal": s0, "hist": f0 - s0,
        "mom": mom, "momz": momz, "ema": ema, "emafilter": emafilter,
        "open_state": open_buy.astype("float64") - open_short.astype("float64"),
        "mom_gate": (momz > p.mom_thr).astype("float64")
                    - (momz < -p.mom_thr).astype("float64"),
    }
    return BotRun(values, buy, sell, short, cover,
                  position_from_signals(buy, sell, short, cover))


# --------------------------------------------------------------------------- #
# Dac trung
# --------------------------------------------------------------------------- #
def build_bot_features(df: pd.DataFrame, cfg: FeatureConfig,
                       runs: dict[str, BotRun] | None = None) -> pd.DataFrame:
    """Dau vao cua hai bot, da quy doi ve dai luong khong thu nguyen.

    Cung quy tac don vi nhu phan con lai cua pipeline: muc gia -> log(x/close),
    chenh lech gia -> x/close, dao dong 0..100 -> x/50 - 1. Cot nao trung lap voi
    dac trung da co (vi du EMA240 gan nhu trung EMA255) se bi prune_columns() loai
    tu dong theo tuong quan tren tap train.
    """
    runs = runs or {"kespt": run_kespt(df), "roofing": run_roofing(df)}
    c = df["close"]
    close = c.to_numpy(dtype="float64")
    out = pd.DataFrame(index=df.index)

    k = runs["kespt"].values
    # --- SuperTrend ---
    out["kespt_st_up"] = log_ratio(k["st_up"], close)
    out["kespt_st_dn"] = log_ratio(k["st_dn"], close)
    out["kespt_st_line"] = log_ratio(k["st_line"], close)
    out["kespt_st_trend"] = k["st_trend"]
    # Khoang cach toi duong SuperTrend tinh bang ATR: "con bao nhieu truoc khi dao
    # chieu" - dai luong ma bot thuc su dua vao, khong phu thuoc muc gia hay che do
    # bien dong.
    out["kespt_st_dist_atr"] = safe_div(close - k["st_line"], k["atr"])
    out["kespt_atr28"] = safe_div(k["atr"], close)

    # --- KF / STORSI ---
    # LRSI va LSTO deu la 0..100; STORSI = n1*LRSI + LSTO nen chia cho (n1+1) de dua
    # ve dung thang do 0..100 truoc khi doi sang -1..1.
    span = k["n1"][0] + 1.0
    out["kespt_rsi22"] = k["rsi"] / 50.0 - 1.0
    out["kespt_stochk"] = k["stochk"] / 50.0 - 1.0
    out["kespt_lrsi"] = k["lrsi"] / 50.0 - 1.0
    out["kespt_lsto"] = k["lsto"] / 50.0 - 1.0
    out["kespt_storsi"] = (k["storsi"] / span) / 50.0 - 1.0
    out["kespt_storsi_ma"] = (k["storsi_ma"] / span) / 50.0 - 1.0
    out["kespt_hiskf"] = (k["hiskf"] / span) / 50.0

    # --- EMA300 ---
    out["kespt_ema300"] = log_ratio(k["ema"], close)
    out["kespt_ema300_slope"] = np.append(np.nan, np.diff(safe_log(k["ema"])))
    out["kespt_above_ema"] = np.sign(close - k["ema"])

    out["kespt_kf_state"] = k["kf_state"]
    out["kespt_sig_state"] = k["sig_state"]

    r = runs["roofing"].values
    # --- Roofing filter ---
    # HP va Filt la gia da loc thong cao: don vi diem gia, nen chia cho close.
    out["roof_hp"] = safe_div(r["hp"], close)
    out["roof_filt"] = safe_div(r["filt"], close)
    out["roof_signal"] = safe_div(r["signal"], close)
    out["roof_hist"] = safe_div(r["hist"], close)
    out["roof_mom"] = safe_div(r["mom"], close)
    out["roof_momz"] = r["momz"]                      # da la z-score, giu nguyen
    out["roof_ema240"] = log_ratio(r["ema"], close)
    out["roof_emafilter"] = log_ratio(r["emafilter"], close)
    out["roof_ema240_slope"] = np.append(np.nan, np.diff(safe_log(r["ema"])))
    out["roof_above_ema"] = np.sign(close - r["emafilter"])
    out["roof_open_state"] = r["open_state"]
    out["roof_mom_gate"] = r["mom_gate"]

    # --- Hai bot dong thuan hay mau thuan ---
    out["agree_trend"] = out["kespt_st_trend"] * out["roof_open_state"]
    return prefix(out, "bot")


# --------------------------------------------------------------------------- #
# Tin hieu (KHONG phai dac trung)
# --------------------------------------------------------------------------- #
def build_bot_signals(df: pd.DataFrame,
                      runs: dict[str, BotRun] | None = None) -> pd.DataFrame:
    """Lich su quyet dinh cua hai bot.

    Cot `<bot>_pos` la thu ma cau hoi nham toi: 0 = dung ngoai, 1 = long, -1 = short.
    Bon cot su kien di kem cho biet *bar nao* vi the doi - huu ich khi shaping reward
    quanh thoi diem vao/ra lenh thay vi tren toan bo doan nam giu.
    """
    runs = runs or {"kespt": run_kespt(df), "roofing": run_roofing(df)}
    out = pd.DataFrame(index=df.index)
    for name, run in runs.items():
        out[f"{name}_pos"] = run.position
        out[f"{name}_buy"] = run.buy.astype("int8")
        out[f"{name}_sell"] = run.sell.astype("int8")
        out[f"{name}_short"] = run.short.astype("int8")
        out[f"{name}_cover"] = run.cover.astype("int8")
    out["both_pos"] = np.where(
        out["kespt_pos"] == out["roofing_pos"], out["kespt_pos"], 0
    ).astype("int8")
    return out.astype("int8")
