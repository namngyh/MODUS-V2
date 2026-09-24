# 001 — Gộp bar 1 phút về bar 5 phút

- **Trạng thái**: xong
- **Ngày**: 2026-09-05
- **Ảnh hưởng tới**: `laplace/loader.py`, `laplace/config.py`, toàn bộ nhóm `flow`,
  bất biến mới #11, #12 và #13

## 1. Câu hỏi

`ohlc_export.csv` đã đổi từ bar 5 phút sang bar 1 phút (533.344 dòng, tới 2026-09-04).
Người dùng giao dịch chủ yếu trên nến 5 phút, nên cadence quyết định của mô hình phải
khớp cadence giao dịch. Gộp về 5 phút ngay tại tầng loader, giữ nguyên toàn bộ bộ chu kỳ
`(6, 12, 24, 51, 102, 255)` và ý nghĩa 30 phút / 1 giờ / 2 giờ / 1 phiên / 2 phiên /
1 tuần của chúng.

Không chọn phương án giữ bar 1 phút vì như thế mọi hằng số thời gian sẽ sai 5 lần mà
không test nào đỏ — chúng vẫn là chu kỳ hợp lệ, chỉ không còn là chu kỳ mình định.

## 2. Đầu vào → đầu ra

| | Thứ gì | Đơn vị |
|---|---|---|
| Vào | `ohlc_export.csv`, bar 1 phút, 533.344 dòng, 2017-11-06 → 2026-09-04 | điểm chỉ số, hợp đồng |
| Ra | DataFrame bar 5 phút, ~111.600 dòng, index `DatetimeIndex` | như trên, không đổi đơn vị |

Quy tắc gộp trong mỗi bucket 5 phút:

| Cột | Phép gộp |
|---|---|
| `open` | first |
| `high` | max |
| `low` | min |
| `close` | last |
| `volume`, `buy_vol`, `buy_val`, `sell_vol`, `sell_val` | sum |

**Quy ước nhãn bucket: `label="left", closed="left"`** — bucket `[t, t+5)` mang nhãn `t`.
Đây không phải lựa chọn, mà là kết quả đo: đối chiếu với 109.359 bar 5 phút của chính
nhà cung cấp (bản lưu trong `data/features/ohlcv.parquet` của lần build trước) cho kết
quả **khớp 100,00% trên cả `open`, `high`, `low`, `close`, `volume`**. Quy ước
`label="right"` chỉ khớp 10–18%.

Bucket rỗng bị loại, nên nghỉ trưa (11:30–13:00) và qua đêm không sinh bar giả. Vì các
mốc 11:30 / 13:00 / 14:45 đều chia hết cho 5 phút, không bucket nào bắc qua ranh giới
phiên.

### Cột order flow đổi ngữ nghĩa

Đây là thay đổi thực chất, không phải hệ quả của việc gộp bar:

| | File 5 phút cũ | File 1 phút mới |
|---|---:|---:|
| `(buy_vol + sell_vol) / volume`, trung vị | 0,183 | **1,000** |
| Số bar có `buy + sell == volume` | 3,8% | **99,4%** |

File cũ chỉ phân loại ~18% khối lượng (nhiều khả năng là một tập con loại lệnh); file mới
phân loại **toàn bộ** khối lượng thành chủ động mua hoặc chủ động bán. Đây là dữ liệu tốt
hơn hẳn: `flow__ofi` nay là mất cân bằng dòng lệnh thật trên toàn bộ khối lượng, không
phải trên một lát 18%.

Hệ quả trực tiếp: `flow__participation` = `(buy+sell)/volume` nay gần như hằng số 1,0 và
sẽ bị `prune_columns()` loại tự động. Đó là hành vi đúng, không cần sửa tay. 0,6% số bar
lệch là các phiên ATC, nơi khớp lệnh định kỳ không có bên chủ động.

> **Dự đoán này sai** — xem mục Kết quả. Giữ nguyên câu trên thay vì sửa lại cho khớp
> thực tế, vì giá trị của spec nằm ở chỗ so được cái đã nghĩ với cái đã xảy ra.

## 3. Lập luận nhân quả

Phép gộp chỉ dùng các bar 1 phút **nằm trong chính bucket đó**; không có cửa sổ trượt,
không có tham số ước lượng, không đọc sang bucket kế tiếp.

Điểm cần nói rõ: bar mang nhãn `09:00` gộp khoảng `[09:00, 09:05)` nên chỉ *hoàn tất* lúc
09:05. Đây đúng bằng quy ước mà nhà cung cấp đã dùng cho file 5 phút cũ (đã đo ở mục 2),
và cũng đúng bằng quy ước toàn pipeline vẫn giả định: **thông tin của bar `t` là thông
tin có được tại thời điểm đóng bar `t`**, quyết định tại bar `t` được thực hiện ở giá
đóng cửa bar `t` hoặc mở cửa bar `t+1`. Bots đã theo đúng quy ước này ("vị thế tại bar
`i` có hiệu lực từ cuối bar `i`"). Không có gì thay đổi, nên bất biến #2 vẫn giữ nguyên
và `test_features_identical_when_future_removed` vẫn là bài kiểm tra hợp lệ.

## 4. Bất biến

Hai bất biến mới, thêm vào bảng trong CLAUDE.md:

- **#11** — Bar sau khi nạp phải đúng kích thước khai báo trong `FeatureConfig.bar_minutes`.
- **#12** — Chu kỳ trong `all_periods` phải tương ứng đúng các tầm nhìn đã định
  (30 phút, 1 giờ, 2 giờ, 1 phiên, 2 phiên, 1 tuần) theo kích thước bar đã khai báo.

Bất biến #12 chính là thứ đáng lẽ đã bắt được vụ đổi dữ liệu này ngay lập tức.

## 5. Bài test làm spec này thất bại

```
tests/test_resample.py::test_resample_reproduces_vendor_five_minute_bars
tests/test_resample.py::test_loaded_bars_have_the_configured_size
tests/test_resample.py::test_periods_match_their_intended_horizons
tests/test_resample.py::test_no_bucket_spans_a_session_boundary
```

- Bài thứ nhất đối chiếu với 6.000 bar thật của nhà cung cấp lưu ở
  `tests/fixtures/vendor_5min_ohlcv.parquet` (ba đoạn rời nhau, 2018 / 2021 / 2026). Đảo
  `label` sang `"right"`, hoặc đổi `first`/`last` thành `last`/`first`, là test đỏ ngay.
- Bài thứ hai đỏ nếu ai đó thay file dữ liệu bằng độ phân giải khác mà không khai lại.
- Bài thứ ba đỏ nếu đổi `bar_minutes` mà quên chỉnh `all_periods` — đúng cái bẫy đã gặp.
- Bài thứ tư đỏ nếu một bucket gộp lẫn bar trước và sau nghỉ trưa, hoặc bắc qua hai ngày.

## 6. Tiêu chí chấp nhận

Đây là thay đổi kỹ thuật, không phải giả thuyết thị trường, nên tiêu chí là kỹ thuật.
Chưa nhìn vào tập test lần nào cho mục đích đánh giá mô hình.

- Gộp lại đúng **100%** bar 5 phút của nhà cung cấp trên 6.000 bar đối chiếu
- Số bar sau gộp: 111.000–112.000; trung vị bar/phiên = 51
- Toàn bộ 31 test hiện có vẫn xanh
- `build_features.py` chạy dưới 60 giây
- `flow__participation` bị loại tự động, không phải xoá tay

---

## Kết quả

**Chấp nhận.** Đã làm:

- `FeatureConfig.bar_minutes = 5`; loader gọi `resample_bars()` khi phát hiện nguồn mịn hơn
- Chu kỳ nay **suy ra từ tầm nhìn tính bằng phút** thay vì khai thẳng bằng số bar — đây là
  phần sửa tận gốc, không nằm trong spec ban đầu nhưng là cách duy nhất làm bất biến #12
  thành cấu trúc chứ không phải lời nhắc
- Thêm `--bar-minutes` cho CLI, `describe_periods()` in ra ngay đầu mỗi lần build
- `meta.json` ghi thêm khối `derived` để bản lưu trên đĩa tự mô tả được chính nó

Đối chiếu với tiêu chí ở mục 6:

| Tiêu chí | Kết quả |
|---|---|
| Gộp lại đúng 100% bar nhà cung cấp | **đạt** — 6.000/6.000 bar, cả 5 cột |
| 111.000–112.000 bar, trung vị 51 bar/phiên | **đạt** — 111.624 bar thô, trung vị 51 |
| 31 test cũ vẫn xanh | **đạt** — 36/36 (thêm 5 test của spec này) |
| Build dưới 60 giây | **đạt** — 8,9 giây |
| `flow__participation` bị loại tự động | **không đạt — tiêu chí sai, không phải code sai** |

### Hai điều học được

**1. Tiêu chí cuối cùng của tôi đặt sai.** Tôi dự đoán `participation = (buy+sell)/volume`
sẽ thành hằng số 1,0 và bị tỉa. Thực tế nó bằng 1,0 ở 97,58% số bar, còn 2,42% có khối
lượng không phân loại được — và **1.558 bar trong số đó không phải bar ATC** (tương quan
với `session__is_last_bar` chỉ 0,379). Vậy cột này vẫn mang thông tin thật và giữ lại là
đúng. Đây là lý do mục 6 phải viết trước: nếu viết sau khi chạy, tôi đã hợp lý hoá kết
quả thay vì phát hiện mình đoán sai.

**2. Bar cuối của ban đối chiếu là bar dở.** Lần chạy đầu khớp 5.999/6.000; bar lệch là
bar cuối cùng của file 5 phút cũ (`2026-08-11 14:10`), nhà cung cấp export giữa chừng nên
nó chỉ có 2.886 hợp đồng thay vì 5.609. Bản gộp của ta đúng hơn bản đối chiếu. Đã loại
bar đó khỏi fixture kèm ghi chú lý do — không hạ ngưỡng test xuống 99,9%, vì như thế sẽ
che mất một sai lệch thật trong tương lai.

### Ảnh hưởng ngoài dự kiến (tốt)

Cột order flow của nguồn 1 phút phân loại toàn bộ khối lượng, nên `flow__ofi` nay sạch
hơn hẳn: độ lệch chuẩn giảm từ ~0,497 xuống 0,317 vì nó là mất cân bằng thật trên toàn bộ
khối lượng chứ không phải nhiễu lấy mẫu trên một lát 18%. Nhóm `flow` đáng được đánh giá
lại về mức đóng góp khi có nhãn.

### Còn nợ

Tập test nay dài thêm tới 2026-09-04 (14.304 bar thay vì 13.565). Chưa nhìn vào nó lần
nào cho mục đích đánh giá mô hình.
