"""Canh spec 003 - tang snapshot du lieu tu PostgreSQL.

Bai quan trong nhat la `test_snapshot_reproduces_the_csv_exactly`: no chung minh duong
DB va duong CSV cho ra cung mot thu. Neu khong co no thi khi chuyen sang DB, moi sai
lech (mui gio, kieu numeric, quen loc is_final) se lang le doi ca bo dac trung.

Cac bai can DB duoc danh dau `db` va tu bo qua khi khong noi duoc - suite phai chay
duoc ca khi ngoai tuyen.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import pytest

from laplace.fetch import (
    SnapshotSpec,
    fetch_snapshot,
    load_snapshot,
    snapshot_paths,
)

pytestmark = pytest.mark.db


def _dsn_or_skip() -> str:
    dsn = os.environ.get("PG_DSN")
    if not dsn:
        pytest.skip("khong co PG_DSN")
    try:
        import psycopg

        with psycopg.connect(dsn, connect_timeout=5):
            pass
    except Exception as exc:  # noqa: BLE001 - moi loi ket noi deu la ly do bo qua
        pytest.skip(f"khong noi duoc DB: {str(exc).splitlines()[0][:60]}")
    return dsn


@pytest.fixture(scope="module")
def dsn() -> str:
    return _dsn_or_skip()


@pytest.fixture(scope="module")
def spec() -> SnapshotSpec:
    return SnapshotSpec(symbol="VN30F1M", start="2017-11-06", end="2026-09-05")


@pytest.fixture(scope="module")
def snapshot(dsn, spec, tmp_path_factory):
    out = tmp_path_factory.mktemp("snapshots")
    return fetch_snapshot(spec, dsn=dsn, outdir=out)


def test_snapshot_reproduces_the_csv_exactly(snapshot):
    """Snapshot tu DB phai khop tung dong voi ohlc_export.csv.

    Day la cach duy nhat chung minh hai duong du lieu cho ra cung mot thu. Sai mui gio,
    sai kieu `numeric`, hay quen loc `is_final` deu lam bai nay do.
    """
    got = load_snapshot(snapshot.parquet).set_index("ts").sort_index()

    raw = pd.read_csv("ohlc_export.csv")
    ts = pd.to_datetime(raw["TRADING_DATE"].astype(str) + " " + raw["TRADING_TIME"],
                        format="%Y%m%d %H:%M:%S")
    csv = raw.set_index(ts).sort_index()
    csv = csv[~csv.index.duplicated(keep="last")]

    assert len(got) == len(csv), f"DB {len(got):,} dong, CSV {len(csv):,} dong"
    pd.testing.assert_index_equal(got.index, csv.index, check_names=False)

    # OHLCV: cho phep vai bar lech vi DB co the da dinh chinh sau khi CSV duoc xuat.
    # Do duoc: open 0, high 1, low 0, close 2, volume 20 dong tren 533.344.
    pairs = [("open", "OPEN_PX"), ("high", "HIGH_PX"), ("low", "LOW_PX"),
             ("close", "CLOSE_PX"), ("volume", "VOL")]
    for ours, theirs in pairs:
        differs = ~np.isclose(got[ours].to_numpy("float64"), csv[theirs].to_numpy("float64"))
        assert differs.sum() <= 50, f"cot {ours} lech {differs.sum()} dong - qua nhieu de la dinh chinh"

    # Cac cot order flow KHONG khop, va ly do da duoc xac dinh - xem bai duoi.


def test_csv_has_buy_and_sell_swapped_relative_to_db(snapshot):
    """File CSV gan nham nhan BUY/SELL. DB moi la ban dung.

    Hai kiem chung doc lap, deu chi cung mot huong:

    1. Gia trung binh ben mua phai CAO hon ben ban (nguoi mua chu dong tra gia chao
       ban). Voi nhan cua DB: +0,586 diem, duong o 94,7% so bar. Voi nhan cua CSV:
       -0,0002 diem, duong o 39,1% - vo ly ve mat kinh te.
    2. Mat can bang mua-ban phai cung dau voi bien dong gia trong bar. Voi nhan cua DB:
       corr = +0,34. Voi nhan cua CSV: -0,34.

    Bai test nay khoa lai phat hien do. Khi `loader.py` duoc sua de doi hai cot, bai
    nay phai duoc cap nhat cung luc - chinh la de khong ai quen.
    """
    got = load_snapshot(snapshot.parquet).set_index("ts").sort_index()
    raw = pd.read_csv("ohlc_export.csv")
    ts = pd.to_datetime(raw["TRADING_DATE"].astype(str) + " " + raw["TRADING_TIME"],
                        format="%Y%m%d %H:%M:%S")
    csv = raw.set_index(ts).sort_index()
    csv = csv[~csv.index.duplicated(keep="last")]

    # Cot KHOI LUONG hoan doi sach: chi lech dung may bar da duoc dinh chinh.
    for db_col, csv_col in (("buy_vol", "SELL_VOL"), ("sell_vol", "BUY_VOL")):
        same = np.isclose(got[db_col].to_numpy("float64"), csv[csv_col].to_numpy("float64"))
        assert same.mean() > 0.999, f"{db_col} khong con khop voi {csv_col}: {same.mean():.5f}"

    # Cot GIA TRI cung hoan doi nhung kem mot sai lech nho ~0,02% ma toi CHUA giai
    # thich duoc (lam tron o nguon? tinh lai bang gia khac?). Chot nguong o 0,1% de
    # neu sai lech nay lon len thi co bao.
    for db_col, csv_col in (("buy_val", "SELL_VAL"), ("sell_val", "BUY_VAL")):
        a = got[db_col].to_numpy("float64")
        c = csv[csv_col].to_numpy("float64")
        m = c > 0
        rel = np.abs(a[m] - c[m]) / c[m]
        assert np.median(rel) < 1e-3, f"{db_col} lech qua xa {csv_col}: {np.median(rel):.5f}"


def test_snapshot_name_is_content_addressed(dsn, tmp_path):
    """Fetch hai lan cung mot khoang phai ra cung mot ten file."""
    spec = SnapshotSpec(symbol="VN30F1M", start="2024-01-02", end="2024-01-31")
    a = fetch_snapshot(spec, dsn=dsn, outdir=tmp_path)
    b = fetch_snapshot(spec, dsn=dsn, outdir=tmp_path)
    assert a.parquet.name == b.parquet.name
    assert a.meta["content_hash"] == b.meta["content_hash"]
    assert a.meta["n_rows"] > 0


def test_snapshot_metadata_records_provenance(snapshot):
    """Thieu bat ky truong nao thi ban chup khong tu mo ta duoc chinh no."""
    meta = json.loads(snapshot.json.read_text(encoding="utf-8"))
    for field in ("query", "n_rows", "ts_first", "ts_last", "content_hash",
                  "fetched_at", "server_version", "symbol", "max_updated_at"):
        assert field in meta and meta[field] is not None, f"thieu truong {field}"
    assert meta["n_rows"] == 533_344


def test_fetch_refuses_to_run_without_credentials(spec, tmp_path, monkeypatch):
    """Khong duoc co DSN mac dinh nao trong code."""
    monkeypatch.delenv("PG_DSN", raising=False)
    with pytest.raises(RuntimeError, match="PG_DSN"):
        fetch_snapshot(spec, dsn=None, outdir=tmp_path)


def test_snapshot_paths_are_deterministic(tmp_path):
    """Ten file suy ra tu spec + hash, khong phu thuoc thoi diem chay."""
    spec = SnapshotSpec(symbol="VN30F1M", start="2024-01-02", end="2024-01-31")
    p1 = snapshot_paths(spec, "abc12345", tmp_path)
    p2 = snapshot_paths(spec, "abc12345", tmp_path)
    assert p1 == p2
    assert "VN30F1M" in p1.parquet.name and "abc12345" in p1.parquet.name


def test_db_buy_side_pays_more_than_sell_side(snapshot):
    """Bat bien 16, ve chi kiem duoc tren du lieu DB.

    Nguoi mua chu dong tra gia chao ban nen gia trung binh cua ho phai cao hon - hieu
    hai gia chinh la chenh lech mua-ban. Do duoc tren DB: +0,586 diem, duong o 94,7%
    so bar.

    Khong dua bai nay vao test_invariants.py vi file CSV dung mot gia chung cho ca hai
    ben (gia hai ben bang nhau o 52,6% so bar, DB chi 0,6%), nen tren duong CSV cac cot
    `buy_px_edge` / `sell_px_edge` / `px_spread` khong mang thong tin gi.
    """
    df = load_snapshot(snapshot.parquet)
    px_buy = df["buy_val"] / df["buy_vol"].replace(0, np.nan)
    px_sell = df["sell_val"] / df["sell_vol"].replace(0, np.nan)
    diff = (px_buy - px_sell).dropna()

    assert diff.mean() > 0.3, f"chenh lech mua-ban chi {diff.mean():+.4f} diem"
    assert (diff > 0).mean() > 0.9, f"chi {100 * (diff > 0).mean():.1f}% so bar duong"
