"""Doc va lam sach du lieu OHLCV tho."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FeatureConfig

# CHU Y: file CSV gan NHAM nhan BUY va SELL - anh xa duoi day doi lai cho dung.
#
# Bang chung (spec 003, doi chieu voi PostgreSQL nguon):
#   db.buy_vol  == csv.SELL_VOL  o 99,996% so dong
#   db.sell_vol == csv.BUY_VOL   o 99,997% so dong
#
# Hai kiem chung kinh te doc lap deu cho thay DB dung va CSV sai:
#   1. Gia TB ben mua tru ben ban phai DUONG (nguoi mua chu dong tra gia chao ban).
#      Nhan DB: +0,586 diem, duong o 94,7% so bar. Nhan CSV: -0,0002, duong o 39,1%.
#   2. corr(mat can bang mua-ban, return trong bar) phai DUONG.
#      Nhan DB: +0,34. Nhan CSV: -0,34.
#
# Bat bien #16 canh dieu nay khong tai dien.
RAW_COLUMNS = {
    "OPEN_PX": "open",
    "HIGH_PX": "high",
    "LOW_PX": "low",
    "CLOSE_PX": "close",
    "VOL": "volume",
    "SELL_VOL": "buy_vol",
    "SELL_VAL": "buy_val",
    "BUY_VOL": "sell_vol",
    "BUY_VAL": "sell_val",
}


def load_ohlcv(cfg: FeatureConfig) -> pd.DataFrame:
    """Tra ve DataFrame index datetime, cot chuan hoa chu thuong, da sap xep.

    Cot `date` giu lai ranh gioi phien - gan nhu moi buoc sau deu can groupby theo no
    de tranh tinh dac trung bac qua dem.
    """
    raw = pd.read_csv(cfg.csv_path)
    if cfg.symbol is not None:
        raw = raw[raw["SYMBOL"] == cfg.symbol]

    ts = pd.to_datetime(
        raw["TRADING_DATE"].astype(str) + " " + raw["TRADING_TIME"].astype(str),
        format="%Y%m%d %H:%M:%S",
    )
    df = raw.rename(columns=RAW_COLUMNS)[list(RAW_COLUMNS.values())].astype("float64")
    df.index = pd.DatetimeIndex(ts, name="ts")
    df["symbol"] = raw["SYMBOL"].to_numpy()

    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = resample_bars(df, cfg.bar_minutes)
    df = _sanitise(df)

    df["date"] = df.index.normalize()
    df["bar_of_day"] = df.groupby("date").cumcount()
    # Do dai phien *du kien*, lay tu phien lien truoc. Dem so bar cua chinh phien
    # dang chay la nhin trom tuong lai: o bar 09:30 chua the biet hom nay se co 51
    # hay 42 bar. So bar phien truoc thi da biet chac.
    per_day = df.groupby("date")["close"].size()
    df["bars_prev_day"] = df["date"].map(per_day.shift(1)).fillna(per_day.median())
    return df


AGGREGATION = {
    "open": "first", "high": "max", "low": "min", "close": "last",
    "volume": "sum", "buy_vol": "sum", "buy_val": "sum",
    "sell_vol": "sum", "sell_val": "sum", "symbol": "first",
}


def detect_bar_minutes(index: pd.DatetimeIndex) -> float:
    """Kich thuoc bar cua chuoi, do bang khoang cach hay gap nhat.

    Dung mode chu khong phai trung binh hay min: chuoi co nghi trua (90 phut) va qua
    dem (~18 gio) nen ca hai thong ke kia deu vo nghia.
    """
    gaps = pd.Series(index).diff().dt.total_seconds().div(60).dropna()
    return float(gaps.mode().iloc[0]) if len(gaps) else float("nan")


def resample_bars(df: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """Gop bar nguon ve kich thuoc `minutes`. Khong lam gi neu da dung kich thuoc.

    Quy uoc nhan `label="left", closed="left"` - bucket [t, t+minutes) mang nhan t -
    khong phai lua chon tuy y ma la ket qua doi chieu voi chinh bar 5 phut cua nha
    cung cap: khop 100% tren OHLCV, trong khi "right" chi khop 10-18% (spec 001).

    Bucket rong bi loai, nen nghi trua va qua dem khong sinh bar gia. Vi cac moc
    11:30 / 13:00 / 14:45 deu chia het cho 5 phut, khong bucket nao bac qua ranh
    gioi phien.
    """
    source = detect_bar_minutes(df.index)
    if not (source < minutes):
        return df
    agg = {k: v for k, v in AGGREGATION.items() if k in df.columns}
    out = df.resample(f"{minutes}min", label="left", closed="left").agg(agg)
    return out.dropna(subset=["open"])


def _sanitise(df: pd.DataFrame) -> pd.DataFrame:
    """Sua cac bar khong nhat quan thay vi vut bo - vut bo se tao lo hong thoi gian."""
    body_hi = df[["open", "close"]].max(axis=1)
    body_lo = df[["open", "close"]].min(axis=1)
    df["high"] = np.maximum(df["high"].to_numpy(), body_hi.to_numpy())
    df["low"] = np.minimum(df["low"].to_numpy(), body_lo.to_numpy())

    for col in ("open", "high", "low", "close"):
        df.loc[df[col] <= 0, col] = np.nan
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].ffill()

    for col in ("volume", "buy_vol", "buy_val", "sell_vol", "sell_val"):
        df[col] = df[col].clip(lower=0.0)
    return df


def third_thursday(year: int, month: int) -> pd.Timestamp:
    """Ngay dao han phai sinh chi so VN30 (thu Nam thu ba cua thang)."""
    first = pd.Timestamp(year=year, month=month, day=1)
    offset = (3 - first.dayofweek) % 7          # 3 = Thursday
    return first + pd.Timedelta(days=offset + 14)


def days_to_expiry(index: pd.DatetimeIndex) -> pd.Series:
    """So ngay lich con lai den dao han hop dong thang hien hanh.

    VN30F1M la hop dong xoay vong: gan ngay dao han, thanh khoan va basis hanh xu
    khac han - mo hinh can biet vi tri trong chu ky nay.
    """
    days = index.normalize()
    exp = pd.Series(
        [third_thursday(t.year, t.month) for t in days], index=index, dtype="datetime64[ns]"
    )
    rolled = exp < days                          # da qua dao han -> nhin sang thang sau
    if rolled.any():
        nxt = (days[rolled] + pd.offsets.MonthBegin(1)).normalize()
        exp.loc[rolled] = [third_thursday(t.year, t.month) for t in nxt]
    return (exp - pd.Series(days, index=index)).dt.days.astype("float64")
