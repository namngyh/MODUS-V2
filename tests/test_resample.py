"""Canh spec 001 - gop bar 1 phut ve bar 5 phut.

Bai test dau tien la bai quan trong nhat: doi chieu ket qua gop voi 6.000 bar 5 phut
that cua nha cung cap, luu lai truoc khi file nguon bi thay. Nho no ma quy uoc nhan
bucket (label="left") la mot su that do duoc, khong phai mot lua chon co the troi di.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from laplace.config import SESSION_MINUTES, FeatureConfig
from laplace.loader import load_ohlcv

FIXTURE = Path(__file__).parent / "fixtures" / "vendor_5min_ohlcv.parquet"


@pytest.fixture(scope="module")
def cfg() -> FeatureConfig:
    return FeatureConfig()


@pytest.fixture(scope="module")
def bars(cfg) -> pd.DataFrame:
    return load_ohlcv(cfg)


def test_resample_reproduces_vendor_five_minute_bars(bars):
    """Gop lai phai ra dung bar 5 phut ma nha cung cap tung phat.

    Doi label sang "right", hoac doi first/last cua open/close, la test do ngay.
    """
    vendor = pd.read_parquet(FIXTURE)
    ours = bars.loc[bars.index.isin(vendor.index), list(vendor.columns)]

    assert len(ours) == len(vendor), "thieu bar so voi ban doi chieu"
    for col in vendor.columns:
        matched = np.isclose(ours[col].to_numpy(), vendor[col].to_numpy()).mean()
        assert matched == 1.0, f"{col} chi khop {matched:.4f}"


def test_loaded_bars_have_the_configured_size(bars, cfg):
    """Bat bien 11: kich thuoc bar sau khi nap dung bang cai da khai bao.

    Do se do neu ai do thay file du lieu bang do phan giai khac ma khong khai lai -
    dung tinh huong da xay ra voi file 1 phut.
    """
    gaps = pd.Series(bars.index).diff().dt.total_seconds().div(60).dropna()
    assert gaps.mode().iloc[0] == cfg.bar_minutes

    # Moi khoang cach deu phai la boi cua kich thuoc bar: khoang lon hon chi xuat
    # hien o nghi trua va qua dem, khong bao gio la mot bar le do.
    assert (gaps % cfg.bar_minutes == 0).all()


def test_periods_match_their_intended_horizons(cfg):
    """Bat bien 12: chu ky (so bar) van dung tam nhin (phut) da dinh."""
    expected = {
        30: "30 phut", 60: "1 gio", 120: "2 gio",
        SESSION_MINUTES: "1 phien",
        2 * SESSION_MINUTES: "2 phien",
        5 * SESSION_MINUTES: "1 tuan",
    }
    minutes = [p * cfg.bar_minutes for p in cfg.all_periods]
    assert minutes == sorted(expected), f"chu ky ra {minutes} phut, khong dung y dinh"

    assert cfg.session_bars == SESSION_MINUTES // cfg.bar_minutes
    assert cfg.embargo_bars == 2 * cfg.session_bars


def test_no_bucket_spans_a_session_boundary(cfg):
    """Mot bar 5 phut khong duoc gop lan bar truoc va sau nghi trua, hay hai ngay."""
    raw = pd.read_csv(cfg.csv_path)
    ts = pd.to_datetime(raw["TRADING_DATE"].astype(str) + " " + raw["TRADING_TIME"],
                        format="%Y%m%d %H:%M:%S")
    src = pd.Series(ts.to_numpy(), index=ts).sort_index()

    bucket = src.index.floor(f"{cfg.bar_minutes}min")
    span = src.groupby(bucket).agg(["min", "max"])
    width = (span["max"] - span["min"]).dt.total_seconds().div(60)

    assert (width < cfg.bar_minutes).all(), "co bucket rong hon mot bar"
    assert (span["min"].dt.normalize() == span["max"].dt.normalize()).all(), \
        "co bucket bac qua hai ngay"


def test_order_flow_now_classifies_all_volume(bars):
    """File moi phan loai toan bo khoi luong, khac han file cu (~18%).

    Ghi lai thanh test de neu nha cung cap doi nguoc lai thi biet ngay, vi y nghia
    cua ca nhom `flow` phu thuoc vao dieu nay.
    """
    classified = bars["buy_vol"] + bars["sell_vol"]
    ratio = (classified / bars["volume"].replace(0, np.nan)).dropna()
    assert ratio.median() == pytest.approx(1.0, abs=0.01)
