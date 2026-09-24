# laplace — đầu vào cho mô hình deep learning auto-trading

Sinh ma trận đặc trưng từ dữ liệu OHLCV của VN30F1M — nguồn là bar 1 phút, gộp về
**bar 5 phút** ngay tại loader để khớp cadence giao dịch thực tế ([spec 001](specs/001-gop-bar-1-phut-ve-5-phut.md)), gồm các biến đổi cơ
bản từ OHLC cộng với các nhóm indicator TA-Lib: **cycles, momentum, overlap,
statistic, volatility, volume** — thêm ba nhóm ngoài TA-Lib: **order flow**
(từ `BUY_VOL`/`SELL_VOL`), **session** (vị trí trong phiên, ngày đến đáo hạn), và
**bot** (toàn bộ đầu vào của hai bot AFL trong [bot/](bot/)).

Kết quả: **454 đặc trưng × 110.098 bar**, đã chuẩn hoá, chia tập theo thời gian, sẵn
sàng đưa vào LSTM encoder + PPO. Kèm theo — lưu tách riêng, **không** phải đặc trưng —
là lịch sử quyết định `{-1, 0, 1}` của hai bot để agent đối chiếu.

## Cài đặt

```bash
pip install -r requirements.txt
```

## Chạy

```bash
python build_features.py --out data/features            # dựng và ghi ra đĩa
python build_features.py --dry-run --horizon 12         # chỉ xem báo cáo
python build_features.py --candles --window 32           # bật lại nhóm, đổi cửa sổ
python -m pytest tests/ -q                              # 27 passed
```

Dùng trong Python:

```python
import torch
from laplace import FeatureConfig, build_feature_frame
from laplace.dataset import make_datasets, signals_at_ends, torch_dataset

cfg = FeatureConfig(window=64)
fs = build_feature_frame(cfg)          # ~7 giây cho 110k bar
print(fs.report())

ds = make_datasets(fs, cfg, horizon=12)["train"]
loader = torch.utils.data.DataLoader(torch_dataset(ds), batch_size=128, shuffle=True)
next(iter(loader)).shape               # torch.Size([128, 64, 454])

ref = signals_at_ends(fs, ds.ends)     # ý kiến của hai bot tại bar cuối mỗi cửa sổ
```

## Các nhóm đặc trưng

| Nhóm | Cột | Nội dung |
|---|---:|---|
| `base` | 71 | log-return đa tầm nhìn, hình học nến (thân/bóng/CLV), 4 ước lượng biến động (realized, Parkinson, Garman-Klass, Rogers-Satchell), vị trí trong biên độ, hệ số hiệu quả Kaufman, khối lượng đã khử mùa vụ trong phiên |
| `cycles` | 7 | Hilbert transform: chu kỳ trội, pha, phasor, sine, trend mode |
| `momentum` | 131 | RSI, CCI, MFI, ADX/DI, AROON, STOCH, MACD, PPO, ULTOSC, WILLR… quét qua 6 chu kỳ |
| `overlap` | 113 | 9 họ trung bình động × 6 chu kỳ (kèm độ dốc), Bollinger, ACCBANDS, SAR, MAMA, HT_TRENDLINE |
| `statistic` | 52 | hồi quy tuyến tính (giá trị, góc, độ dốc), STDDEV, VAR, AVGDEV, BETA/CORREL |
| `volatility` | 7 | ATR, NATR, TRANGE |
| `volume` | 5 | AD, OBV, ADOSC ở ba cặp chu kỳ |
| `flow` | 22 | mất cân bằng lệnh mua/bán, delta luỹ kế trong phiên, chênh lệch giá mua/bán, phân kỳ dòng tiền–giá — nguồn 1 phút phân loại **toàn bộ** khối lượng thành chủ động mua/bán (file 5 phút cũ chỉ phân loại ~18%) |
| `session` | 19 | tiến độ phiên, sin/cos giờ, khoảng cách bar (bắt nghỉ trưa 90 phút), thứ/tháng, ngày đến đáo hạn |
| `bot` | 25 | đầu vào của hai bot AFL — [xem mục riêng](#hai-bot-afl) |

Chu kỳ được **khai bằng phút rồi suy ra số bar**, không khai thẳng bằng số bar: 30 phút,
1 giờ, 2 giờ, 1 phiên (255 phút), 2 phiên, 1 tuần → `(6, 12, 24, 51, 102, 255)` với bar 5
phút. Nhờ vậy đổi độ phân giải dữ liệu không làm lệch ý nghĩa của chúng — một cái bẫy đã
thực sự sập một lần, xem [CLAUDE.md](CLAUDE.md).

Nhóm **`candles`** (61 mẫu nến TA-Lib) đã tắt mặc định. Code vẫn còn nguyên trong
`indicators.py`, bật lại bằng `--candles` hoặc `FeatureConfig(use_candles=True)` nếu muốn
đo đóng góp của nhóm này. Bật lên thì ma trận thành 506 cột — 52 mẫu sống sót, 9 mẫu bị
loại vì gần như không xuất hiện lần nào trong 9 năm dữ liệu 5 phút.

**Danh sách đầy đủ từng cột** — kèm công thức và quy tắc chuẩn hoá — nằm ở
[FEATURES.md](FEATURES.md), sinh tự động từ [`laplace/catalog.py`](laplace/catalog.py)
mỗi lần chạy `build_features.py`, nên không bao giờ lệch khỏi thứ pipeline thực sự tạo
ra. Bản máy đọc được: `data/features/catalog.json`.

## Hai bot AFL

[`laplace/bots.py`](laplace/bots.py) dịch nguyên hai file trong [bot/](bot/) sang Python,
dùng lớp primitive AmiBroker ở [`laplace/afl.py`](laplace/afl.py) (`Cross`, `Flip`,
`ExRem`, `StochK`, `Ref`). Tham số lấy đúng giá trị mặc định của `Optimize()` — AmiBroker
trả về đối số thứ hai khi không chạy optimization; `roofing2.afl` ở `STAGE = 0` nên bốn
nút lõi bị khoá ở `LengthFix/HPfix/SSfix/SigFix`.

**KESPT** = SuperTrend(3, ATR 28) × KF/STORSI × lọc EMA300. Đóng góp vào đặc trưng:
hai băng SuperTrend, đường ST đang hoạt động, trạng thái trend, **khoảng cách tới đường
ST tính bằng ATR** (đại lượng bot thực sự dựa vào), RSI(22), StochK(22,43), LinearReg của
cả hai, STORSI, STORSIma, histogram, EMA300 và độ dốc.

**Roofing** = Ehlers Roofing Filter (high-pass 2 cực + Super Smoother) × momentum thrust
z-score × lọc EMA240. Đóng góp: HP, Filt, đường tín hiệu WMA(10), histogram, Mom, MomZ,
EMA240, `emafilter = Ref(EMA, −1)`, và hai cổng trạng thái.

Cả hai vòng lặp đều đệ quy — SuperTrend sửa băng tại chỗ rồi bar sau đọc lại giá trị đã
sửa, Roofing là bộ lọc IIR 2 cực — nên không vector hoá được và phải giữ đúng thứ tự cập
nhật của bản gốc. `tests/test_bots.py` kiểm chứng bằng bất biến hình học (đường ST luôn
nằm đúng phía của giá) và bằng bài kiểm tra nhân quả.

Cột nào trùng lặp với đặc trưng đã có sẽ **tự động bị loại** theo tương quan trên tập
train, nên không cần lọc tay:

```
bot__kespt_atr28        → trùng lặp với volatility__ATR24
bot__kespt_rsi22        → trùng lặp với momentum__RSI24
bot__roof_ema240        → trùng lặp với overlap__EMA255
bot__roof_emafilter     → trùng lặp với overlap__EMA255
bot__kespt_ema300_slope → trùng lặp với bot__kespt_ema300
```

### Tín hiệu — không phải đặc trưng

`build_bot_signals()` mô phỏng máy trạng thái vị thế của backtester AmiBroker (đóng lệnh
trước, mở lệnh sau, nên tín hiệu đảo chiều xử lý gọn trong một bar) và cho ra
`signals.parquet`:

| Cột | Ý nghĩa |
|---|---|
| `kespt_pos`, `roofing_pos` | **0 = đứng ngoài, 1 = long, −1 = short** |
| `both_pos` | vị thế khi hai bot đồng thuận, ngược lại 0 |
| `*_buy`, `*_sell`, `*_short`, `*_cover` | bar xảy ra sự kiện vào/ra lệnh |

Chúng nằm ngoài `features.npy` và không đi qua scaler — có một test riêng
(`test_signals_stay_out_of_the_feature_matrix`) canh việc này, vì nếu để lọt vào X thì mô
hình chỉ học cách sao chép bot thay vì học thị trường.

Phân bố sau burn-in:

```
kespt    long  41.328   short  29.759   flat  38.272    (65,0% thời gian có vị thế)
roofing  long   9.739   short   7.944   flat  91.676    (16,2% thời gian có vị thế)
both     long   9.135   short   7.203   flat  93.021    (14,9% thời gian có vị thế)
```

Hai bot chỉ đồng thuận **49,6%** số bar — đủ khác nhau để làm hai ý kiến độc lập, không
phải một tín hiệu nhân đôi.

Backtest thô để kiểm chứng bản dịch (1 hợp đồng, phí 0,4 điểm/lượt, toàn bộ 2017–2026):

| Bot | Lãi ròng | /năm | MDD | Số lượt | CAR/MDD |
|---|---:|---:|---:|---:|---:|
| KESPT | 4.454 đ | 508 đ | −301 đ | 3.090 | 1,69 |
| Roofing | 1.444 đ | 165 đ | −161 đ | 3.556 | 1,02 |

Cả hai có lãi ở **mọi năm** (trừ Roofing hoà vốn ở phần 2026 chưa trọn năm) — bằng chứng
tốt rằng chuỗi tín hiệu được dịch đúng, vì một lỗi lệch chỉ số trong vòng lặp gần như
chắc chắn sẽ biến kết quả thành nhiễu. Lưu ý đây là **in-sample**: cả hai bot đã được tối
ưu trên chính dữ liệu này, nên con số trên đo độ trung thực của bản dịch chứ không phải
kỳ vọng lợi nhuận tương lai.

## Nguyên tắc thiết kế

### 1. Không đưa mức giá thô vào mô hình

VN30F1M đi từ ~600 (2017) lên ~1900 (2026). Mạng học trên mức giá sẽ không tổng quát hoá
sang vùng giá chưa từng thấy. Mỗi output của TA-Lib được gán một *kiểu đơn vị*, và
[`laplace/norms.py`](laplace/norms.py) quy đổi nó về đại lượng không thứ nguyên:

| Kiểu | Ví dụ | Phép biến đổi |
|---|---|---|
| `price` | SMA, BBANDS, SAR, TSF | `log(x / close)` |
| `pdiff` | MACD, ATR, STDDEV, MOM | `x / close` |
| `pct100` | RSI, ADX, MFI, STOCH | `x / 50 − 1` |
| `pct100n` | WILLR | `x / 50 + 1` |
| `signed100` | CMO, AROONOSC, mẫu nến | `x / 100` |
| `flow_diff` | AD, OBV | `diff(x) / khối lượng trung bình` |
| `absprice` + `sign` | SAREXT | tách mức và chiều |

Hai trường hợp dễ hỏng nhất nếu bỏ qua bước này: **OBV/AD** là tổng luỹ kế từ 2017, mức
của chúng chỉ phản ánh điểm bắt đầu tính chứ không mang thông tin — chỉ biến thiên mới có
nghĩa. **SAREXT** trả về giá trị âm khi ở chiều bán; `log` thẳng sẽ biến 48% số bar thành
NaN.

Đặc trưng bot theo đúng quy tắc đó: `STORSI = 3,7·LRSI + LSTO` được chia cho `n1 + 1` để
về lại thang 0–100 trước khi đổi sang −1…1; `Filt` của Roofing là giá đã lọc thông cao nên
chia cho `close`.

### 2. Ranh giới rò rỉ dữ liệu nằm ở đúng một chỗ

`base.py` / `indicators.py` / `orderflow.py` / `session.py` / `bots.py` chỉ chứa phép biến
đổi nhân quả **không tham số**. Mọi thứ *ước lượng* từ dữ liệu — trung vị, IQR, danh sách
cột bị loại — nằm trong `scaling.py` và **chỉ khớp trên tập train**.

Ba bẫy đã xử lý:

- **Độ dài phiên**: ở bar 09:30 chưa thể biết hôm nay sẽ có 51 hay 42 bar. `day_progress`
  dùng số bar của phiên *liền trước*; `is_last_bar` lấy từ lịch giao dịch (14:45) chứ
  không phải từ việc đếm bar đã xảy ra.
- **Mùa vụ khối lượng**: bar 09:00 luôn lớn hơn bar 11:20, nên so sánh trực tiếp là vô
  nghĩa. Dùng trung bình trượt 60 phiên của *chính bar đó*, đã shift 1.
- **Embargo**: bỏ 102 bar sau mỗi mốc chia tập, nếu không điểm valid đầu tiên vẫn "biết"
  về các bar train cuối cùng qua cửa sổ 64 bar và các indicator chu kỳ dài.

`tests/test_no_lookahead.py` kiểm chứng bằng cách cắt dữ liệu tại bar *t*, tính lại toàn
bộ, và đòi hỏi giá trị tại *t* trùng khớp với khi tính trên toàn chuỗi — tại 3 điểm cắt
cho đặc trưng, 2 điểm cắt cho tín hiệu bot.

### 3. Không vật chất hoá tensor 3 chiều

Với 83k cửa sổ × 64 bar × 454 đặc trưng, mảng `(N, L, F)` chiếm **9,6 GB** — trong khi ma
trận 2 chiều gốc chỉ 199 MB. Các cửa sổ chồng lấn nhau 63/64, lưu tách ra là nhân bản dữ
liệu 64 lần một cách vô ích. `SequenceDataset` cắt lát lười ngay trong `__getitem__`;
`features.npy` đọc được bằng `np.load(mmap_mode="r")`.

### 4. Tự động tỉa cột

Trên tập train, loại bỏ cột hằng số, cột gần như luôn bằng 0, và cột trùng lặp
`|corr| ≥ 0,999`. Với cấu hình hiện tại cả 85 cột bị loại đều thuộc loại trùng lặp, và
phần lớn là những trùng lặp mà lọc tay sẽ bỏ sót:

```
momentum__CMO6       → trùng RSI6         (CMO chỉ là RSI đổi thang)
momentum__MOM6       → trùng base__ret6
momentum__WILLR6     → trùng base__pos6
overlap__EMA255_slope → trùng EMA255      (log(EMA_t/EMA_t−1) ≈ −α·log(EMA/C), corr −0,9998)
overlap__SMA6_slope   → trùng base__ret6
```

Lý do từng cột nằm trong `meta.json` và `catalog.json`.

## Kết quả ghi ra đĩa

```
data/features/
  features.npy      200 MB   (110098, 454) float32, mmap được
  catalog.json               danh mục 539 cột (454 dùng + 85 đã loại) kèm mô tả
  index.parquet              timestamp của từng hàng
  ohlcv.parquet              bar gốc, dùng cho backtest và sinh nhãn
  signals.parquet            vị thế {-1,0,1} và sự kiện vào/ra của hai bot
  splits.npz                 chỉ số train / valid / test
  scaler.npz + .json         center, scale, danh sách cột — dùng lại khi suy luận
  meta.json                  cột, nhóm, lý do loại cột, config đầy đủ
```

Chia tập mặc định:

```
train    83.088 bar   2017-12-18 → 2024-06-28
valid    12.502 bar   2024-07-03 → 2025-06-30
test     14.304 bar   2025-07-03 → 2026-09-04
```

## Cấu trúc

```
build_features.py      CLI
bot/                   hai file AFL gốc
laplace/
  config.py            FeatureConfig — bật/tắt từng nhóm, chu kỳ, mốc chia tập
  loader.py            đọc CSV, làm sạch, ngày đáo hạn (thứ Năm thứ ba)
  utils.py             chia/log an toàn, trung bình mùa vụ nhân quả
  norms.py             quy đổi đơn vị cho từng kiểu output
  base.py              biến đổi cơ bản từ OHLC
  indicators.py        registry TA-Lib (Spec) cho 7 nhóm
  orderflow.py         đặc trưng dòng lệnh
  session.py           đặc trưng lịch và vị trí trong phiên
  afl.py               primitive AmiBroker: Cross, Flip, ExRem, StochK, Ref
  bots.py              bản dịch hai bot → đặc trưng + tín hiệu
  scaling.py           chia tập, tỉa cột, RobustScaler
  pipeline.py          ghép tất cả
  dataset.py           cửa sổ trượt, torch Dataset, lưu/đọc
  catalog.py           sinh danh mục đặc trưng từ chính các Spec
tests/
  test_no_lookahead.py
  test_bots.py
```

Thêm một indicator mới chỉ là thêm một dòng `Spec` vào `indicators.py` — cùng với kiểu
chuẩn hoá của nó, nên không thể quên bước đổi đơn vị.

## Bước tiếp theo

Với khung LSTM encoder + PPO hai head (entry / exit), phần còn thiếu là **môi trường**,
chứ không hẳn là nhãn:

- **Reward**: P&L theo điểm trừ chi phí, tính từ `ohlcv.parquet`. Chi phí giao dịch VN30F
  (phí + trượt giá) vào khoảng 0,3–0,5 điểm mỗi lượt — phải nằm trong reward ngay từ đầu,
  nếu không PPO sẽ hội tụ về một policy đảo vị thế liên tục.
- **State**: output của encoder ghép thêm vị thế hiện tại và số bar đã nắm giữ. Head exit
  chỉ có ý nghĩa khi state biết đang có lệnh, nên hai thứ này không thể nằm trong
  `features.npy` (chúng phụ thuộc hành động của agent, không phải thị trường).
- **Warm-start**: `signals_at_ends()` cho ra hành động của hai bot tại đúng bar mà policy
  ra quyết định. Pretrain head entry bằng cross-entropy trên `both_pos` là cách rẻ để
  tránh giai đoạn đầu PPO đi lang thang — sau đó thả cho RL tự tối ưu.

Về các component bổ sung bạn nhắc tới: **GARCH** cho ra dự báo σ *một bước tới* — thứ mà
`base__rv*` (biến động đã thực hiện, nhìn về quá khứ) không có; nó hợp làm bộ chuẩn hoá
reward và làm đầu vào sizing hơn là thêm một cột X. **Bayesian inference** hữu ích nhất ở
chỗ ước lượng độ bất định của policy để quyết định *không* vào lệnh khi posterior còn
rộng. Cả hai đều gắn vào state/reward chứ không thuộc pipeline đặc trưng này, nên tôi để
ngoài phạm vi hiện tại.

Lưu ý khi huấn luyện: các cửa sổ liền kề chồng lấn 63/64, nên `shuffle=True` **không** làm
chúng độc lập.
