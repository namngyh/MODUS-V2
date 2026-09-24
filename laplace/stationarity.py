"""Lop tinh dung cua tung cot (spec 006): dung hoa truoc, chuan hoa sau.

Moi cot duoc gan DUNG MOT lop bang quy tac theo ten - khong bang danh sach tay, de
khong the "xep" mot cot vao lop mien tru chi vi no lam test do.

    adaptive   : dong lenh mua/ban. Muc cua no gay cau truc nam 2023 (-0,13 -> +0,05),
                 nhieu kha nang do cach phan loai lenh doi. Thay bang PIT(z(x)).
    variance   : muc bien dong. Log de nen phuong sai; GIU muc (thong tin che do that)
                 va THEM cot `_z` = PIT(z(log x)) cho cau hoi "hom nay so voi tuan truoc".
    regime     : chu ky >= 2 phien. Troi theo nam vi thi truong troi theo nam - do chinh
                 la tin hieu. Giu nguyen.
    stationary : con lai. Giu nguyen.

Nguyen tac: z-score cuon xoa MOI dich chuyen keo dai hon W bar, ca loi do lan thong
tin that. Nen chi dung no o noi dich chuyen la loi do.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

from .config import FeatureConfig

CLASSES = ("adaptive", "variance", "regime", "stationary")

_VARIANCE = re.compile(
    r"^(volatility__.+"
    r"|base__(rv|park|gk|rs)\d+"
    r"|statistic__(STDDEV|VAR|AVGDEV)\d+"
    r"|momentum__(PLUS|MINUS)_DM\d+"
    r"|bot__kespt_atr\d+"                # ATR cua SuperTrend, chia cho gia
    r"|bot__kespt_st_(up|dn))$"          # log((hl2 +- 3 ATR) / C): bien dong doi lot
)
_ADAPTIVE = re.compile(r"^flow__(?!active_rel)")
_Z_SUFFIX = "_z"


def _is_variance(col: str) -> bool:
    return bool(_VARIANCE.match(col))


def classify(col: str, cfg: FeatureConfig) -> str:
    """Lop cua mot cot, theo thu tu uu tien o docstring cua module."""
    if col.endswith(_Z_SUFFIX) and _is_variance(col[: -len(_Z_SUFFIX)]):
        # Phai dung TRUOC quy tac regime: `base__rv255_z` chua so 255 nhung da bi
        # z-score cuon, nen phai chiu bat bien do troi nhu moi cot thuong.
        return "stationary"
    if _ADAPTIVE.match(col):
        return "adaptive"
    if _is_variance(col):
        return "variance"
    horizon = 2 * cfg.session_bars
    if any(int(n) >= horizon for n in re.findall(r"\d+", col.split("__", 1)[-1])):
        return "regime"
    return "stationary"


def is_regime(col: str, cfg: FeatureConfig) -> bool:
    """Cot duoc phep mang thong tin che do: lop regime va cot muc cua lop variance."""
    return classify(col, cfg) in ("regime", "variance")


def rolling_zscore(df: pd.DataFrame, window: int) -> pd.DataFrame:
    """z_t = (x_t - mu_t) / s_t, voi mu_t va s_t lay tren W bar TRUOC t.

    Loai bar hien tai khoi thong ke: neu gom ca x_t thi mot cu giat lon tu keo mu_t va
    s_t theo, va z_t bi nen lai dung o bar ma no can noi to nhat.
    """
    past = df.shift(1).rolling(window, min_periods=max(2, window // 4))
    mu, sd = past.mean(), past.std()
    dev = df - mu
    z = dev / sd.where(sd > 1e-12)
    # Qua khu la hang so (sd = 0, vi du `participation` truoc 08/2018 luon bang 1):
    # z khong xac dinh theo cong thuc nhung co nghia ro rang - bang hang so do thi
    # "khong lech" (0), khac thi lech vo cung (+-inf, qua PIT thanh +-1). De NaN o day
    # se keo burn-in them 8 thang. NaN chi con lai o doan khoi dong (mu chua co).
    flat = (sd <= 1e-12) & mu.notna() & df.notna()
    # Khong viet sign(dev) * inf: sign(0) * inf = NaN, dung truong hop can bang 0.
    d = dev.to_numpy()
    fill = np.where(d > 1e-12, np.inf, np.where(d < -1e-12, -np.inf, 0.0))
    return z.mask(flat, pd.DataFrame(fill, index=z.index, columns=z.columns))


def pit(z: np.ndarray, dof: float) -> np.ndarray:
    """u = 2 F_nu(z) - 1 trong (-1, 1). Ep duoi: cu giat 6 sigma khong chiem tron thang."""
    z = np.asarray(z, dtype="float64")
    return 2.0 * student_t.cdf(z, dof) - 1.0


def stationarize(block: pd.DataFrame, cfg: FeatureConfig) -> pd.DataFrame:
    """Ap phep bien doi theo lop cho mot khoi cot. Nhan qua, khong tham so uoc luong."""
    classes = {c: classify(c, cfg) for c in block.columns}
    adaptive = [c for c, k in classes.items() if k == "adaptive"]
    variance = [c for c, k in classes.items() if k == "variance"]
    if not adaptive and not variance:
        return block

    out = block.copy()
    w, dof = cfg.rolling_window, cfg.pit_dof

    if adaptive:
        z = rolling_zscore(block[adaptive], w)
        out[adaptive] = pit(z.to_numpy(), dof)

    if variance:
        # |x|: bang duoi SuperTrend mang dau am. San chan log(0) o bar khong bien dong.
        level = np.log(block[variance].abs().clip(lower=cfg.log_floor))
        out[variance] = level
        z = rolling_zscore(level, w)
        extra = pd.DataFrame(pit(z.to_numpy(), dof), index=block.index,
                             columns=[f"{c}{_Z_SUFFIX}" for c in variance])
        # Dat cot _z ngay sau cot muc cua no de danh muc de doc.
        out = pd.concat([out, extra], axis=1)
        order = []
        for c in block.columns:
            order.append(c)
            if c in extra.columns.str[: -len(_Z_SUFFIX)]:
                order.append(f"{c}{_Z_SUFFIX}")
        out = out[order]
    return out


def yearly_drift(features: pd.DataFrame, mask: np.ndarray,
                 min_coverage: float = 0.9) -> pd.Series:
    """Do troi theo nam tren tap `mask`, tinh bang boi so do lech chuan cua tap do.

    (TB nam cao nhat - TB nam thap nhat) / std, sau khi cat duoi o phan vi 1 %/99 %.
    Chi so NAM DU (>= min_coverage so bar cua nam day nhat): nam thieu vai thang lam
    cot theo mua (month_sin) "troi" chi vi thieu mua, khong phai vi du lieu doi.
    Dung trung binh chu khong dung trung vi: voi cot nhi phan, trung vi nhay thang tu
    0 len 1 va phong dai do troi.
    """
    sub = features.iloc[np.flatnonzero(mask)]
    lo, hi = sub.quantile(0.01), sub.quantile(0.99)
    sub = sub.clip(lo, hi, axis=1)
    years = sub.index.year
    counts = pd.Series(years).value_counts()
    keep = np.isin(years, counts[counts >= min_coverage * counts.max()].index)
    means = sub[keep].groupby(years[keep]).mean()
    sd = sub.std().where(lambda s: s > 1e-12)
    return ((means.max() - means.min()) / sd).fillna(0.0)
