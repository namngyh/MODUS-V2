# 006 — Lớp tính dừng: sửa dòng lệnh và biến động, giữ thông tin chế độ

- **Trạng thái**: xong
- **Ngày**: 2026-09-24
- **Ảnh hưởng tới**: `laplace/stationarity.py` (mới), `pipeline.py`, `config.py`,
  `catalog.py`; nhóm `flow`, `volatility`, cột biến động trong `base`, `statistic`,
  `momentum`, `bot`; bất biến mới #19
- **Đánh số lại**: behavior cloning (trước ghi là "spec 006") chuyển sang **spec 007**

## 1. Câu hỏi

Người dùng yêu cầu: *dừng hoá trước, chuẩn hoá sau*, và xử lý theo bản chất từng loại
chỉ báo. Đo trên train cho thấy pipeline đã làm đúng điều đó với phần lớn cột, nhưng hai
nhóm thì không. Spec này sửa đúng hai nhóm đó (phương án A), và biến nguyên tắc thành
một bất biến có test canh.

## Ký hiệu

| Ký hiệu | Nghĩa | Hình dạng / đơn vị |
|---|---|---|
| `x_t` | Giá trị một cột đặc trưng tại bar *t*, sau bước đổi đơn vị của `norms.py` | số thực, không đơn vị |
| `W` | Cửa sổ cuộn | **255 bar = 1 tuần** (khai bằng phút: `5 × 255`) |
| `μ_t`, `s_t` | Trung bình và độ lệch chuẩn của `x` trên W bar **trước** *t* (`t−W … t−1`) | cùng đơn vị với `x` |
| `z_t` | **Rolling z-score** `(x_t − μ_t) / s_t`: "hôm nay lệch bao nhiêu so với tuần trước" | số độ lệch chuẩn |
| `F_ν` | Hàm phân phối tích luỹ của Student-t với ν bậc tự do. ν nhỏ thì đuôi dày | ν = 5 |
| **PIT** | *Probability integral transform*: `u = 2·F_ν(z) − 1`. Đổi z thành xác suất, ép đuôi lại | khoảng (−1, 1) |
| `σ_train` | Độ lệch chuẩn của cột trên tập train | cùng đơn vị với `x` |
| **Độ trôi** | (trung bình năm cao nhất − thấp nhất) / `σ_train`. Tính trên train, sau khi cắt đuôi ở phân vị 1 %/99 %, chỉ lấy năm có ≥ 3.000 bar | bội số `σ_train` |

## 2. Đo trước khi làm (chỉ tập train, 454 cột)

| Nguyên nhân trôi | Cột | Số liệu | Xử lý |
|---|---|---|---|
| Gãy cấu trúc | `flow__*` (trừ `active_rel*`) | Mất cân bằng thô: **−0,13** (2017–22) → **+0,05** (2023–24). Độ trôi trung vị **1,50σ** | Xoá bằng rolling z |
| Chế độ biến động — thật | Mức biến động | Độ phân tán năm 2022 gấp 7 lần năm 2024. Độ trôi trung vị 1,04σ | Giữ mức (log), **thêm** cột rolling z |
| Xu hướng dài — thật | Chu kỳ ≥ 102 bar (2 phiên) | Độ trôi trung vị 0,34σ | Giữ nguyên, khai là `regime` |
| — | 293 cột còn lại | Độ trôi trung vị **0,17σ**; chỉ 2 cột > 1σ (`kespt_st_up/dn` 1,10) | Giữ nguyên |

`kespt_st_up/dn` = `log((hl2 ± 3·ATR) / C)` — khoảng cách tới một dải rộng 3·ATR, tức là
**thước đo biến động đội lốt**. Chúng thuộc lớp biến động theo quy tắc, không phải ngoại lệ.

ADF bác bỏ nghiệm đơn vị ở 99,3 % số cột: **không cột nào là bước ngẫu nhiên**, nên sai
phân không phải công cụ đang thiếu.

## 3. Đầu vào → đầu ra

Mỗi cột được gán **đúng một lớp** bằng quy tắc theo tên (thứ tự ưu tiên từ trên xuống),
không bằng danh sách tay:

| Lớp | Quy tắc | Phép biến đổi | Đầu ra |
|---|---|---|---|
| `adaptive` | `flow__*` trừ `flow__active_rel*` | `PIT(z(x))` thay tại chỗ | (−1, 1) |
| `variance` | `volatility__*`; `base__{rv,park,gk,rs}N`; `statistic__{STDDEV,VAR,AVGDEV}N`; `momentum__{PLUS,MINUS}_DMN`; `bot__kespt_st_{up,dn}` | `log(max(\|x\|, 1e−5))` thay tại chỗ (**mức**, coi là `regime`) **và** thêm cột `<tên>_z = PIT(z(log …))` | log tỷ lệ; (−1, 1) |
| `regime` | Tên chứa một số ≥ `2 × session_bars` (102) | giữ nguyên | như cũ |
| `stationary` | còn lại, kể cả mọi cột `_z` sinh ra ở trên | giữ nguyên | như cũ |

Nhóm 1 của người dùng (chỉ báo có giới hạn: RSI, Stoch, %R) nằm trong `stationary` và
**không bị động tới**: chúng đã được ánh xạ cố định về [−1, 1] ở `norms.py`.

Sau bước này, scaler robust khớp trên train vẫn chạy như cũ.

**Tham số mới** (đặt trước, không tinh chỉnh): `W = 255 bar`, `ν = 5`, sàn log `1e−5`,
`min_periods = W / 4`. Không tham số nào ước lượng từ dữ liệu.

## 4. Lập luận nhân quả

`μ_t` và `s_t` lấy từ `x.shift(1).rolling(W)` — chỉ các bar **trước** *t*. `log` và
`PIT` là hàm từng điểm. Không có tham số nào khớp trên tập nào cả. Bất biến #2
(`test_features_identical_when_future_removed`) phủ luôn bước này vì nó được gọi bên
trong `build_raw_features`.

Burn-in: cột chậm nhất vẫn là T3(255) (~1.524 bar); rolling z của `ATR255` cần 255 + 64
bar, nên burn-in không đổi.

## 5. Bất biến

**Mới #19** — Cột không thuộc lớp `regime` (và không phải mức của lớp `variance`) có độ
trôi theo năm trên train **< 1,0σ**. Chế độ thị trường chỉ được vào X qua cột đã khai
`regime`; mọi độ trôi khác là lỗi đo cho tới khi chứng minh ngược lại.

Ảnh hưởng: #1 (không mang mức giá), #8 (catalog phủ mọi cột), #9 (tắt nhóm là hết cột)
— phải vẫn xanh.

## 6. Bài test làm spec này thất bại

```
tests/test_stationarity.py::test_adaptive_column_forgets_a_level_shift
tests/test_stationarity.py::test_variance_level_keeps_the_regime_and_z_forgets_it
tests/test_stationarity.py::test_rolling_zscore_uses_only_the_past
tests/test_stationarity.py::test_pit_is_bounded_and_monotone
tests/test_stationarity.py::test_classes_follow_the_rules
tests/test_invariants.py::test_non_regime_features_do_not_drift_across_years
```

- **forgets a level shift** — chuỗi tổng hợp nhảy +0,2 ở giữa (mô phỏng OFI 2023). Ngay
  sau cú nhảy `|u|` lớn; sau W bar trung vị `|u|` về gần 0
- **keeps the regime** — biến động nhân đôi: cột mức lệch đúng `log 2` và **giữ** lệch;
  cột `_z` về gần 0. Đây là bài canh phần "không xoá thông tin chế độ"
- **only the past** — sửa `x` tại *t* và sau đó, `z` trước *t* không đổi; sửa `x_t` không
  làm đổi `μ_t`
- **bounded and monotone** — `u ∈ (−1, 1)`, đơn điệu, `u(0) = 0`
- **follow the rules** — mỗi quy tắc ở mục 3 cho đúng lớp trên vài tên mẫu, kể cả
  `base__rv255_z` là `stationary` chứ không phải `regime`
- **do not drift** — bất biến #19 trên dữ liệu thật

## 7. Tiêu chí chấp nhận

Tập test: **không nhìn** (vẫn 1 lần). Đặt trước khi chạy:

| Tiêu chí | Ngưỡng |
|---|---|
| Bất biến #19 | Mọi cột không-regime < 1,0σ |
| Dòng lệnh sau biến đổi | Độ trôi trung vị nhóm `flow` từ 1,50σ xuống **< 0,5σ** |
| Toàn bộ suite | 83 test cũ + test mới đều xanh |
| Bất biến #1 | vẫn < 0,5 |
| **Kiểm tra đổi ý (A → B)** | Trên **valid** so với train: nếu > 30 % số cột không-flow, không-regime lệch trung bình > 1σ thì gãy cấu trúc là phổ biến → quay lại bàn phương án B |

Hệ quả phải ghi: X đổi nghĩa nên **ngưỡng nhiễu 164 điểm của spec 005 hết hiệu lực** và
phải đo lại trước khi so sánh bất cứ gì ở spec 007.

**Không** đặt tiêu chí về lợi nhuận — spec này sửa đầu vào, không hỏi mô hình kiếm được
bao nhiêu.

---

## Kết quả (2026-09-24)

**Trạng thái: chấp nhận** sau khi xoá bốn cột (mục cuối). Trước đó bất biến #19 vướng đúng một
cột (`flow__participation`, 1,01σ). Không nới ngưỡng.

| Tiêu chí | Kết quả |
|---|---|
| Độ trôi trung vị nhóm `flow` < 0,5σ | **đạt** — 1,25σ → **0,04σ** |
| Bất biến #19 | **đạt** sau khi xoá bốn cột (trước đó vướng `flow__participation` 1,01σ) |
| Suite | **110/110** (83 cũ + 27 mới) |
| Bất biến #1 (mức giá) | đạt |
| Kiểm tra đổi ý A → B trên valid | **0,0 %** cột lệch > 1σ (ngưỡng 30 %). Lệch lớn nhất 0,34σ (`BETA51`). Gãy cấu trúc **không** phổ biến → giữ A |
| Build | 8 s → 14 s; 454 → **496 cột** (+42 cột `_z`, −4 cột sản phẩm phụ của nhà cung cấp, xem dưới); 97 cột loại vì trùng lặp |

Độ trôi trung vị theo lớp sau khi làm: `adaptive` 0,04 · `stationary` 0,13 · `regime`
0,34 · `variance` (mức, được phép) 1,20.

### Gãy cấu trúc 2023 là do nhà cung cấp — đã có bằng chứng

Rủi ro "không lượng hoá được" ở phần thảo luận (gãy OFI là lỗi đo hay thị trường thật?)
nay có câu trả lời. Tỷ lệ `(mua + bán) / tổng khối lượng`:

| | 2017–2022 | 2023–2024 |
|---|---|---|
| Trung bình | 0,996 – 1,000 | **0,965** |

Trước 2023 mọi hợp đồng khớp đều được gán mua hoặc bán; từ 2023, 3,5 % không được gán.
Cùng năm mức mất cân bằng nhảy −0,13 → +0,05. Thay đổi ở **cách phân loại**, không phải
ở thị trường — đúng loại dịch chuyển mà rolling z-score được dùng để xoá.

### Ba lỗi trong lúc làm, không lỗi nào làm chương trình dừng

1. **Burn-in dài thêm 7.843 bar (8 tháng train).** `participation` hằng số tới 08/2018
   → độ lệch chuẩn cuộn = 0 → z = NaN → cột "chưa hợp lệ" → cắt đầu chuỗi. Mọi test
   khác vẫn xanh. Sửa: quá khứ hằng số cho z = 0 (bằng nó) hoặc ±∞ (khác nó). Thêm
   `test_constant_past_gives_a_defined_zscore_not_nan` và
   `test_stationarize_does_not_extend_burn_in`.
2. **Catalog sửa đè đối tượng dùng chung** — tạo mô tả cột `_z` làm đổi tên luôn cột gốc.
   Bài #8 bắt được.
3. **Định nghĩa độ trôi ghi trong spec (năm ≥ 3.000 bar) sai với cột theo mùa**:
   2024 chỉ có tháng 1–6 nên `month_sin` "trôi" 1,92σ. Đổi thành **chỉ so năm đủ**
   (≥ 90 % số bar của năm dày nhất). Đây là đổi phương pháp đo sau khi thấy kết quả —
   ghi lại để biết. Nó không làm cột nào khác đổi từ đỏ sang xanh.

**Hệ quả:** X đổi nghĩa ⇒ ngưỡng nhiễu 164 điểm của spec 005 hết hiệu lực, phải đo lại
trước spec 007.

### Quyết định: xoá bốn cột sản phẩm phụ của nhà cung cấp (người dùng duyệt 2026-09-24)

| Cột | Vì sao không phải thông tin thị trường |
|---|---|
| `flow__participation` | Bằng 1 suốt 2017–2022; từ 2023 chỉ đo phần khối lượng nhà cung cấp thôi phân loại. Là cột duy nhất vướng bất biến #19 (1,01σ) |
| `flow__buy_px_edge`, `sell_px_edge`, `px_spread` | CSV dùng một giá chung cho hai bên nên gần như bằng 0 (spec 003). Trên DB thì có thật → lúc live mô hình gặp một phân phối chưa từng thấy lúc train |

Đã cân nhắc và bác: khai `participation` là `regime` — test xanh nhưng là che lỗi, vì lớp
`regime` dành cho thông tin thị trường thật. Canh bằng
`test_vendor_artefact_columns_are_gone`.
