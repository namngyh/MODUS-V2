"""Dong goi ma tran dac trung thanh chuoi cua so truot cho mo hinh chuoi.

Diem quan trong: *khong* vat chat hoa tensor 3 chieu. Voi 109k bar, cua so 64 va
481 dac trung, mang (N, L, F) float32 chiem khoang 13 GB - trong khi ma tran 2
chieu goc chi 210 MB. Cac cua so chong lan nhau toi 63/64, nen luu tach ra la nhan
ban du lieu gap 64 lan mot cach vo ich. Dataset o day cat lat luoi tu ma tran 2
chieu ngay trong __getitem__.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .catalog import build_catalog, to_markdown
from .config import FeatureConfig
from .pipeline import FeatureSet


def window_ends(
    fs: FeatureSet, cfg: FeatureConfig, mask: np.ndarray, horizon: int = 0
) -> np.ndarray:
    """Chi so cac bar co the lam *bar cuoi* cua mot cua so hop le.

    `horizon` la so bar ma nhan se nhin toi tuong lai; cac bar cuoi chuoi khong du
    tuong lai de gan nhan se bi loai o day chu khong phai o buoc sinh nhan.
    """
    n = len(fs.features)
    idx = np.arange(n)
    ok = mask.copy()
    ok[: cfg.window - 1] = False                      # khong du lich su
    if horizon > 0:
        ok[n - horizon:] = False                      # khong du tuong lai de gan nhan

    if not cfg.cross_day:
        # Bat buoc ca cua so nam gon trong mot phien.
        day = fs.ohlcv["date"].to_numpy()
        start_day = np.roll(day, cfg.window - 1)
        ok &= (start_day == day)
        ok[: cfg.window - 1] = False

    ends = idx[ok]
    return ends[:: cfg.stride]


@dataclass
class SequenceDataset:
    """Dataset cat lat luoi. Tuong thich torch.utils.data.Dataset.

    `matrix` la mang (T, F) da scale; `ends` la cac bar cuoi cua so. Mau thu i la
    matrix[end - L + 1 : end + 1].
    """

    matrix: np.ndarray
    ends: np.ndarray
    window: int
    targets: np.ndarray | None = None

    def __len__(self) -> int:
        return len(self.ends)

    def __getitem__(self, i: int):
        end = int(self.ends[i])
        x = self.matrix[end - self.window + 1: end + 1]
        if self.targets is None:
            return x
        return x, self.targets[i]

    def to_array(self) -> np.ndarray:
        """Vat chat hoa thanh (N, L, F). Chi dung cho tap nho - kiem tra bang tay,
        ve bieu do. Voi tap train day du se het bo nho."""
        offsets = np.arange(-self.window + 1, 1)
        return self.matrix[self.ends[:, None] + offsets[None, :]]

    @property
    def nbytes_if_materialised(self) -> int:
        return len(self.ends) * self.window * self.matrix.shape[1] * 4


def make_datasets(
    fs: FeatureSet, cfg: FeatureConfig, horizon: int = 0
) -> dict[str, SequenceDataset]:
    matrix = fs.matrix()
    out = {}
    for name in ("train", "valid", "test"):
        ends = window_ends(fs, cfg, getattr(fs.split, name), horizon)
        out[name] = SequenceDataset(matrix, ends, cfg.window)
    return out


def torch_dataset(ds: SequenceDataset):
    """Boc thanh torch Dataset. Import torch o trong ham de phan con lai cua
    package van dung duoc khi khong cai torch."""
    import torch
    from torch.utils.data import Dataset

    class _TorchSeq(Dataset):
        def __len__(self):
            return len(ds)

        def __getitem__(self, i):
            item = ds[i]
            if ds.targets is None:
                return torch.from_numpy(np.ascontiguousarray(item))
            x, y = item
            return torch.from_numpy(np.ascontiguousarray(x)), torch.as_tensor(y)

    return _TorchSeq()


def save_dataset(fs: FeatureSet, cfg: FeatureConfig, outdir: str | Path) -> Path:
    """Ghi ra dia: ma tran 2 chieu + sieu du lieu du de tai lap va suy luan.

    Ma tran luu dang .npy de np.load(mmap_mode="r") doc duoc ma khong nap het vao RAM.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    np.save(outdir / "features.npy", fs.matrix())
    fs.scaler.save(outdir / "scaler")
    if fs.signals is not None:
        # Luu tach khoi features.npy: day la tin hieu tham chieu, khong phai dau vao.
        fs.signals.reset_index().to_parquet(outdir / "signals.parquet")
    fs.features.index.to_frame(index=False).to_parquet(outdir / "index.parquet")
    fs.ohlcv.reset_index().to_parquet(outdir / "ohlcv.parquet")

    splits = {n: np.flatnonzero(getattr(fs.split, n)) for n in ("train", "valid", "test")}
    np.savez_compressed(outdir / "splits.npz", **splits)

    # Danh muc sinh cung luc voi du lieu, khong phai buoc rieng - de khong bao gio
    # co chuyen ma tran co 506 cot con tai lieu ta 481.
    catalog = build_catalog(fs.columns, cfg, fs.dropped)
    catalog.to_json(outdir / "catalog.json", orient="records",
                    force_ascii=False, indent=0)
    Path("FEATURES.md").write_text(to_markdown(catalog), encoding="utf-8")

    (outdir / "meta.json").write_text(
        json.dumps(
            {
                "columns": fs.columns,
                "groups": {g: len(c) for g, c in fs.groups.items()},
                "dropped": fs.dropped,
                "burn_in": fs.burn_in,
                "n_bars": len(fs.features),
                "window": cfg.window,
                "cross_day": cfg.cross_day,
                "config": {k: list(v) if isinstance(v, tuple) else v
                           for k, v in vars(cfg).items()},
                # Chu ky la property suy ra tu tam nhin nen khong nam trong vars();
                # ghi ra day de ban luu tren dia tu mo ta duoc chinh no.
                "derived": {
                    "bar_minutes": cfg.bar_minutes,
                    "all_periods": list(cfg.all_periods),
                    "session_bars": cfg.session_bars,
                    "embargo_bars": cfg.embargo_bars,
                    "return_horizons": list(cfg.return_horizons),
                    "vol_windows": list(cfg.vol_windows),
                    "periods_meaning": cfg.describe_periods(),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return outdir


def load_dataset(outdir: str | Path, mmap: bool = True):
    """Doc lai thu da luu: (matrix, index, splits, meta)."""
    outdir = Path(outdir)
    matrix = np.load(outdir / "features.npy", mmap_mode="r" if mmap else None)
    index = pd.DatetimeIndex(pd.read_parquet(outdir / "index.parquet").iloc[:, 0])
    splits = dict(np.load(outdir / "splits.npz"))
    meta = json.loads((outdir / "meta.json").read_text(encoding="utf-8"))

    sig_path = outdir / "signals.parquet"
    signals = None
    if sig_path.exists():
        signals = pd.read_parquet(sig_path).set_index("ts")
    return matrix, index, splits, meta, signals


def signals_at_ends(fs: FeatureSet, ends: np.ndarray) -> np.ndarray:
    """Tin hieu cua hai bot tai *bar cuoi* cua tung cua so.

    Dung de doi chieu voi hanh dong ma policy chon tai cung buoc do: warm-start bang
    imitation, cong them mot so hang thuong/phat vao reward, hoac chi de theo doi ty
    le agent lech khoi bot. Tin hieu tai bar t da co hieu luc tu cuoi bar t nen
    khong ro ri thong tin tuong lai.
    """
    if fs.signals is None:
        raise ValueError("FeatureSet khong co tin hieu bot (emit_bot_signals=False)")
    return fs.signals.to_numpy()[ends]
