"""Canh cac bat bien duoc ghi trong CLAUDE.md.

Moi quy tac trong muc "Bat bien" cua CLAUDE.md phai co mot bai test o day hoac o
test_no_lookahead.py / test_bots.py. Mot bat bien khong co bai test lam no that bai
thi chi la mot loi chuc: khong ai phat hien duoc khi no bi pha.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from laplace.catalog import build_catalog
from laplace.config import FeatureConfig
from laplace.dataset import make_datasets
from laplace.loader import load_ohlcv
from laplace.pipeline import build_feature_frame


@pytest.fixture(scope="module")
def cfg() -> FeatureConfig:
    return FeatureConfig()


@pytest.fixture(scope="module")
def raw(cfg) -> pd.DataFrame:
    return load_ohlcv(cfg)


@pytest.fixture(scope="module")
def fs(cfg, raw):
    return build_feature_frame(cfg, raw)


def test_no_feature_tracks_the_raw_price_level(fs):
    """Bat bien 1: khong dac trung nao duoc mang muc gia.

    VN30F1M di tu ~600 len ~1900 diem trong 9 nam. Mot cot con mang muc gia se
    tuong quan gan 1.0 voi close va mo hinh se hoc mot the gioi khong lap lai.
    Nguong 0.5 rong rai: cot cao nhat hien tai la 0.26.
    """
    X = fs.features.to_numpy(dtype="float64")
    close = fs.ohlcv["close"].to_numpy(dtype="float64")
    train = fs.split.train

    offenders = []
    for j, name in enumerate(fs.columns):
        x, y = X[train, j], close[train]
        ok = np.isfinite(x)
        if ok.sum() < 1000:
            continue
        r = np.corrcoef(x[ok], y[ok])[0, 1]
        if np.isfinite(r) and abs(r) > 0.5:
            offenders.append((name, round(float(r), 3)))

    assert not offenders, f"dac trung bam theo muc gia: {offenders}"


def test_non_regime_features_do_not_drift_across_years(fs, cfg):
    """Bat bien 19: che do thi truong chi duoc vao X qua cot da khai `regime`.

    Moi do troi khac la loi do cho toi khi chung minh nguoc lai. Vi du that: muc mat
    can bang mua-ban tho nhay tu -0,13 len +0,05 nam 2023 - voi scaler tinh, ca tap
    valid va test se nam o +3 sigma, va mo hinh thay "luc mua manh" o moi bar.
    """
    from laplace.stationarity import is_regime, yearly_drift

    drift = yearly_drift(fs.features, fs.split.train)
    limit = 1.0
    offenders = {c: round(float(d), 2) for c, d in drift.items()
                 if not is_regime(c, cfg) and d >= limit}
    assert not offenders, f"cot khong khai regime nhung troi >= {limit} sigma: {offenders}"


def test_vendor_artefact_columns_are_gone(fs):
    """Bon cot do cach ghi so lieu cua nha cung cap sinh ra, khong phai thi truong (spec 006)."""
    gone = {"flow__participation", "flow__buy_px_edge", "flow__sell_px_edge", "flow__px_spread"}
    assert not gone & set(fs.columns) and not gone & set(fs.dropped)


def test_stationarize_does_not_extend_burn_in(fs, raw):
    """Lop tinh dung khong duoc cat them bar dau chuoi.

    Da xay ra that: z-score cua mot cot hang so thanh NaN, burn-in dai them 7.843 bar
    (8 thang train) ma moi bai khac van xanh.
    """
    before = build_feature_frame(FeatureConfig(stationarize=False), raw)
    assert fs.burn_in == before.burn_in, \
        f"burn-in {before.burn_in} -> {fs.burn_in} bar sau khi bat lop tinh dung"


def test_every_column_is_documented(fs, cfg):
    """Bat bien 2: danh muc sinh tu code va phu het moi cot.

    Neu them mot indicator ma quen mo ta, FEATURES.md se co o trong - tai lieu sai
    con te hon khong co tai lieu.
    """
    catalog = build_catalog(fs.columns, cfg, fs.dropped)
    kept = catalog[catalog["status"] == "kept"]

    assert list(kept["column"]) == fs.columns
    blank = kept[(kept["description"] == "") | (kept["formula"] == "")]
    assert blank.empty, f"cot thieu mo ta: {list(blank['column'])}"


def test_datasets_share_one_two_dimensional_matrix(fs, cfg):
    """Bat bien 3: khong vat chat hoa tensor 3 chieu.

    Ba tap phai tro toi cung mot ma tran (T, F); moi cua so la mot lat cat luoi.
    Neu ai do doi sang precompute (N, L, F) thi bo nho nhay tu ~200 MB len ~13 GB.
    """
    datasets = make_datasets(fs, cfg)
    matrices = [d.matrix for d in datasets.values()]

    assert all(m.ndim == 2 for m in matrices)
    assert all(m is matrices[0] for m in matrices)
    # Nguong theo ty le chu khong theo so MB tuyet doi: bar 1 phut hay 5 phut thi
    # bat bien van la "khong nhan ban du lieu theo cua so".
    materialised = sum(d.nbytes_if_materialised for d in datasets.values())
    assert matrices[0].nbytes < materialised / 10

    # Lat cat phai dung noi dung: mau cuoi cung cua tap test la `window` bar cuoi.
    ds = datasets["test"]
    end = int(ds.ends[-1])
    np.testing.assert_array_equal(
        ds[len(ds) - 1], matrices[0][end - cfg.window + 1: end + 1]
    )


def test_disabled_group_leaves_no_columns(raw):
    """Bat bien 4: tat mot nhom trong config thi khong con cot nao cua nhom do.

    Cac co bat/tat la co che chay ablation; neu chung khong that su go het cot thi
    ket qua ablation vo nghia.
    """
    for flag, prefix in (("use_candles", "candles__"), ("use_orderflow", "flow__"),
                         ("use_bots", "bot__")):
        cfg = FeatureConfig(**{flag: False})
        fs = build_feature_frame(cfg, raw)
        assert not [c for c in fs.columns if c.startswith(prefix)], flag


def test_position_state_not_in_feature_matrix(fs):
    """Bat bien 14: trang thai vi the khong bao gio nam trong ma tran dac trung.

    Sau bien vi the va bon so hang tuong tac deu phu thuoc hanh dong cua agent, khong
    phai thi truong. Cho chung vao X thi hai chuyen xay ra: cac cot do vo nghia khi
    chua co agent, va bat bien #2 (nhan qua) khong con kiem tra duoc vi gia tri cua
    chung phu thuoc mot policy chu khong phai mot ham cua du lieu.
    """
    from laplace.rl.state import STATE_NAMES

    assert not set(STATE_NAMES) & set(fs.columns)
    # Khong cot nao duoc mang tien to danh rieng cho trang thai vi the.
    assert not [c for c in fs.columns if c.split("__")[-1].startswith("pos_")]


def test_loader_never_opens_a_network_connection(cfg):
    """Bat bien 15: duong huan luyen khong bao gio cham mang.

    Day la thu giu cho pipeline tai lap duoc va chay duoc khi mat mang. Neu ai do tien
    tay cho `loader.py` doc thang tu PostgreSQL, hai lan build cach nhau mot ngay se cho
    hai bo dac trung khac nhau ma khong co gi bao.
    """
    import socket

    from laplace.loader import load_ohlcv

    real = socket.socket

    def forbidden(*a, **k):
        raise AssertionError("loader.py vua mo mot socket - xem bat bien #15")

    socket.socket = forbidden
    try:
        df = load_ohlcv(cfg)
    finally:
        socket.socket = real
    assert len(df) > 0


def test_order_flow_imbalance_moves_with_price(raw):
    """Bat bien 16: ap luc mua phai day gia LEN trong chinh bar do.

    Day la bai bat duoc viec doi nhan BUY/SELL (spec 003). Voi nhan sai, tuong quan la
    -0,30 thay vi +0,30 - doi dau chu khong phai bang 0, nen rat de thay.

    Bai anh em cua no (gia TB ben mua > ben ban) nam o tests/test_fetch.py chu khong o
    day: file CSV dung MOT gia chung cho ca hai ben (52,6% so bar co gia hai ben bang
    het nhau, trong khi DB chi 0,6%), nen thong tin do khong ton tai tren duong CSV.
    """
    flow = (raw["buy_vol"] - raw["sell_vol"]) / (raw["buy_vol"] + raw["sell_vol"]).replace(0, np.nan)
    ret = np.log(raw["close"] / raw["open"])
    m = flow.notna() & np.isfinite(ret)
    corr = np.corrcoef(flow[m], ret[m])[0, 1]
    assert corr > 0.1, f"corr(mat can bang, return trong bar) = {corr:+.4f}, phai duong"
