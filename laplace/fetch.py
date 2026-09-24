"""Lay du lieu tu PostgreSQL ra file snapshot (spec 003).

Module nay la duong DUY NHAT trong repo duoc mo ket noi mang. `loader.py` chi doc file,
va bat bien #15 canh dieu do.

Ly do tach ra: neu pipeline doc thang tu DB thi hai lan build cach nhau mot ngay se cho
hai bo dac trung khac nhau - DB co them bar moi, hoac nha cung cap dinh chinh bar cu -
va cau "mo hinh nay huan luyen tren dung du lieu nao" khong con tra loi duoc.

Cach dung:

    python -m laplace.fetch --symbol VN30F1M --start 2017-11-06 --end 2026-09-05

Thong tin dang nhap doc tu bien moi truong PG_DSN, khong co mac dinh trong code.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Cot lay tu bars_1m. Giu dung ten cua DB o day; doi ten sang quy uoc cua pipeline la
# viec cua loader, khong phai cua tang nay.
COLUMNS = (
    "symbol", "ts", "open", "high", "low", "close", "ref_px", "volume", "value",
    "buy_vol", "buy_val", "sell_vol", "sell_val",
    "frn_buy_vol", "frn_buy_val", "frn_sell_vol", "frn_sell_val", "adj_rate",
)
NUMERIC = tuple(c for c in COLUMNS if c not in ("symbol", "ts"))

# Gio san giao dich. DB luu timestamptz theo UTC; phien VN30F chay 09:00-14:45 gio
# dia phuong, nen phai doi ve day truoc khi bo mui gio.
MARKET_TZ = "Asia/Ho_Chi_Minh"


@dataclass(frozen=True)
class SnapshotSpec:
    """Mot lat cat can lay. Bat bien theo thoi gian: cung spec -> cung du lieu."""

    symbol: str
    start: str                 # ngay dau, bao gom (YYYY-MM-DD)
    end: str                   # ngay cuoi, KHONG bao gom
    table: str = "bars_1m"

    def slug(self) -> str:
        return f"{self.symbol}_{self.start}_{self.end}"


@dataclass(frozen=True)
class SnapshotPaths:
    parquet: Path
    json: Path


@dataclass
class Snapshot:
    parquet: Path
    json: Path
    meta: dict
    frame: pd.DataFrame


def snapshot_paths(spec: SnapshotSpec, content_hash: str, outdir: Path) -> SnapshotPaths:
    """Ten file suy ra tu spec va hash noi dung, khong phu thuoc thoi diem chay."""
    stem = f"{spec.slug()}_{content_hash}"
    outdir = Path(outdir)
    return SnapshotPaths(outdir / f"{stem}.parquet", outdir / f"{stem}.json")


def _build_query(spec: SnapshotSpec) -> str:
    """Chi lay bar da chot (`is_final`).

    `bars_1m` co `updated_at` va co `is_final`, nghia la mot bar co the duoc sua lai sau
    khi phat. Lay ca bar chua chot se dua vao snapshot nhung gia tri con doi duoc.
    """
    cols = ", ".join(COLUMNS)
    return (
        f"select {cols}, updated_at from {spec.table} "
        f"where symbol = %(symbol)s and ts >= %(start)s and ts < %(end)s "
        f"and is_final order by ts"
    )


def _content_hash(df: pd.DataFrame) -> str:
    """Hash cua chinh noi dung, de hai lan fetch giong nhau cho cung mot ten file."""
    h = hashlib.sha256()
    h.update(",".join(df.columns).encode())
    h.update(pd.util.hash_pandas_object(df, index=False).values.tobytes())
    return h.hexdigest()[:8]


def fetch_snapshot(spec: SnapshotSpec, dsn: str | None = None,
                   outdir: str | Path = "data/snapshots") -> Snapshot:
    """Lay mot lat cat tu DB, ghi ra parquet kem file mo ta nguon goc."""
    dsn = dsn or os.environ.get("PG_DSN")
    if not dsn:
        raise RuntimeError(
            "Khong co thong tin ket noi. Dat bien moi truong PG_DSN; khong co DSN mac "
            "dinh trong code va khong commit mat khau vao repo."
        )

    import psycopg  # nhap tai cho: phan con lai cua package khong duoc phu thuoc psycopg

    query = _build_query(spec)
    params = {"symbol": spec.symbol, "start": spec.start, "end": spec.end}
    with psycopg.connect(dsn, connect_timeout=15) as conn:
        server = conn.execute("select version()").fetchone()[0].split(",")[0]
        rows = conn.execute(query, params).fetchall()

    df = pd.DataFrame(rows, columns=[*COLUMNS, "updated_at"])
    max_updated = df["updated_at"].max() if len(df) else None
    df = df.drop(columns=["updated_at"])

    # Postgres tra `numeric` ve Decimal; ep sang float64 de parquet va pipeline dung
    # cung mot kieu voi duong CSV.
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    # `ts` la timestamptz luu theo UTC. Doi sang gio Viet Nam TRUOC khi bo mui gio,
    # neu khong bar 14:27 se thanh 07:27 va lech ca phien giao dich 7 tieng. Toan bo
    # pipeline (va file CSV) lam viec voi gio dia phuong khong mang mui gio.
    df["ts"] = (pd.to_datetime(df["ts"], utc=True)
                .dt.tz_convert(MARKET_TZ).dt.tz_localize(None))

    content = _content_hash(df)
    paths = snapshot_paths(spec, content, Path(outdir))
    paths.parquet.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(paths.parquet, index=False)

    meta = {
        "symbol": spec.symbol,
        "table": spec.table,
        "start": spec.start,
        "end": spec.end,
        "query": query,
        "n_rows": len(df),
        "ts_first": str(df["ts"].iloc[0]) if len(df) else None,
        "ts_last": str(df["ts"].iloc[-1]) if len(df) else None,
        "content_hash": content,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "server_version": server,
        # Bar co the duoc sua lai sau khi phat; ghi lai de biet ban chup phan anh
        # trang thai nao cua DB.
        "max_updated_at": str(max_updated) if max_updated is not None else None,
        "timezone": MARKET_TZ,
    }
    paths.json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return Snapshot(paths.parquet, paths.json, meta, df)


def load_snapshot(path: str | Path) -> pd.DataFrame:
    """Doc lai mot snapshot. Khong cham mang."""
    return pd.read_parquet(path)


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--symbol", default="VN30F1M")
    p.add_argument("--start", default="2017-11-06", help="ngay dau, bao gom")
    p.add_argument("--end", default="2026-09-05", help="ngay cuoi, KHONG bao gom")
    p.add_argument("--table", default="bars_1m")
    p.add_argument("--out", default="data/snapshots")
    a = p.parse_args(argv)

    spec = SnapshotSpec(a.symbol, a.start, a.end, a.table)
    snap = fetch_snapshot(spec, outdir=a.out)
    print(f"{snap.meta['n_rows']:,} dong  {snap.meta['ts_first']} -> {snap.meta['ts_last']}")
    print(f"hash {snap.meta['content_hash']} | {snap.meta['server_version']}")
    print(f"ghi vao {snap.parquet}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
