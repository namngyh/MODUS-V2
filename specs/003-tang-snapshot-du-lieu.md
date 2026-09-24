# 003 — Tầng snapshot: lấy dữ liệu từ PostgreSQL ra file

- **Trạng thái**: xong
- **Ngày**: 2026-09-06
- **Ảnh hưởng tới**: `laplace/fetch.py` (mới), bất biến #15. **Không** đụng `loader.py`

## 1. Câu hỏi

Có một PostgreSQL 16 + TimescaleDB trên VPS `qp-vps`, nối qua Tailscale, chứa `bars_1m`
(911 MB), `bars_1d` (26 năm, 389 mã) và `ticks` (bid/ask, 6 tuần). Cần một đường lấy dữ
liệu từ đó ra file.

Quyết định phạm vi đã chốt: **DB chỉ dùng khi vận hành thử / paper trading.** Giai đoạn
xây mô hình vẫn dùng `ohlc_export.csv`. Nên tầng này xây trước để sẵn sàng, chứ chưa nối
vào đường huấn luyện.

## 2. Đã chốt

### 2.1 Không bao giờ đọc thẳng từ DB trong pipeline huấn luyện

```
PostgreSQL ──► fetch.py ──► data/snapshots/<file>.parquet ──► loader.py
               (chạy tay)    + <file>.json mô tả nguồn gốc     (không đổi một dòng)
```

Lý do là tính tái lập. Nếu `loader.py` mở kết nối, hai lần build cách nhau một ngày cho
hai bộ đặc trưng khác nhau — DB có thêm bar mới, hoặc nhà cung cấp đính chính bar cũ — và
câu *"mô hình này huấn luyện trên đúng dữ liệu nào"* không còn trả lời được. Fixture đối
chiếu 6.000 bar ở spec 001 cũng mất chỗ đứng.

### 2.2 Snapshot định danh bằng nội dung

Tên file mang hash của chính nội dung, nên hai lần fetch cùng một khoảng cho ra cùng một
tên. Kèm file `.json` ghi: câu truy vấn, số dòng, bar đầu/cuối, hash, thời điểm lấy,
phiên bản server.

Một lần huấn luyện gắn với đúng một hash. Muốn cập nhật dữ liệu thì chạy `fetch` tạo
snapshot mới, không sửa code.

### 2.3 Thông tin đăng nhập không nằm trong repo

Đọc từ biến môi trường `PG_DSN` (máy này đã có sẵn). Không có DSN mặc định trong code,
không commit `.env`.

## 3. Cái gì trong DB dùng được, cái gì không

Đã đo độ phủ thật, không tin vào tên cột:

| Cột / bảng | Phủ | Dùng để huấn luyện được? |
|---|---|---|
| `bars_1m` cho VN30F1M | 533.344 dòng, 2017-11 → 2026-09 | ✅ **khớp chính xác file CSV** |
| `ref_px`, `value`, `adj_rate`, `is_final` | 100% toàn lịch sử | ✅ |
| `bars_1d.oi` (open interest) | 2.259 phiên, từ 2017-08 | ⚠️ xem mục 3.1 |
| `frn_*` (dòng tiền ngoại) trong `bars_1m` | chỉ từ **2025-10-31** (7,6%) | ❌ tập train kết thúc 2024-06, phủ bằng 0 |
| VN30INDEX 1 phút (để tính basis) | chỉ từ **2025-07-24** | ❌ cùng lý do |
| `ticks` (bid/ask) | chỉ **6 tuần** | ❌ để huấn luyện; ✅ cho live sau này |

Ghi lại để lần sau không phải mừng hụt: **những cột nghe hấp dẫn nhất — dòng tiền ngoại,
basis, sổ lệnh — đều không đủ lịch sử để huấn luyện.**

### 3.1 Open interest: đã đo, quyết định là chưa dùng

Bảng 2×2 kinh điển của phái sinh (giá tăng/giảm × OI tăng/giảm), lợi nhuận ngày hôm sau
tính bằng điểm cơ bản (1 bp = 0,01%):

| | | TRAIN (n=1.634) | | VALID (n=237) | |
|---|---|---:|---:|---:|---:|
| | | bp | sigma | bp | sigma |
| giá GIẢM | OI tăng | **+32,7** | **4,3** | +0,4 | 0,0 |
| giá GIẢM | OI giảm | −10,0 | −1,2 | +15,5 | 1,1 |
| giá TĂNG | OI tăng | +2,7 | 0,4 | −6,1 | −0,4 |
| giá TĂNG | OI giảm | −1,8 | −0,3 | +4,4 | 0,3 |

Ô "giá giảm + OI tăng" cho 4,3 sigma trên train — nghe rất mạnh, và có cách giải thích
kinh tế hợp lý (phe bán mới vào dồn dập → rủi ro bị siết). Nhưng:

- **Valid không xác nhận được**: n chỉ 45 cho ô đó, sai số chuẩn ~19 bp, nên khoảng tin
  cậy trùm cả +39 lẫn −38. Nó **không bác bỏ** kết quả train, chỉ là không nói được gì.
- **Đa kiểm định**: tôi nhìn cả 4 ô rồi mới thấy ô này. 4,3 sigma của ô tốt nhất trong 4
  ô không phải 4,3 sigma của một giả thuyết nêu trước.
- **Nhịp sai**: OI là dữ liệu **ngày**, mô hình quyết định mỗi **5 phút**. Một cột đứng
  yên suốt 51 bar đóng góp rất ít ở nhịp quyết định.
- **Trễ thêm một ngày**: OI ngày `d` công bố sau khi đóng cửa, nên ở mọi bar của ngày `d`
  chỉ dùng được OI tới ngày `d−1`.
- **Nhiễu do đảo hợp đồng**: `|ΔOI|` ngày sau đáo hạn là **33,2%** so với 9,3% ngày
  thường — gấp 3,6 lần, cùng loại nhiễu như gap giá khi đảo hợp đồng.
- **12 phiên có OI = 0**, đều rơi vào ngày đáo hạn nhưng chỉ 12/108 ngày đáo hạn, nên là
  lỗi dữ liệu chứ không phải quy ước.

Quyết định: **chưa thêm vào bộ đặc trưng.** Ghi lại số liệu ở đây để sau này không phải
đo lại. Xem xét lại nếu (a) chuyển sang mô hình có nhịp ngày, hoặc (b) valid tích luỹ đủ
mẫu để xác nhận hay bác bỏ ô đó.

## 4. Lập luận nhân quả

Snapshot là một lát cắt cố định của quá khứ; không có cửa sổ trượt, không có tham số ước
lượng, không có gì nhìn tới tương lai. `loader.py` đọc file y như đọc CSV.

Rủi ro nhân quả thật nằm ở chỗ khác và phải nói rõ: **`bars_1m` có cột `updated_at` và cờ
`is_final`**, nghĩa là một bar có thể được sửa lại sau khi phát. Snapshot phải chỉ lấy
`is_final = true` và ghi lại `max(updated_at)` để biết bản chụp phản ánh trạng thái nào.

## 5. Bất biến

**Bất biến mới #15 — `loader.py` không bao giờ mở kết nối mạng.** Đây là thứ giữ cho toàn
bộ đường huấn luyện tái lập được và chạy được khi mất mạng. Kiểm tra bằng cách chặn
`socket.socket` trong lúc gọi `load_ohlcv()`.

## 6. Bài test làm spec này thất bại

```
tests/test_fetch.py::test_snapshot_reproduces_the_csv_exactly
tests/test_fetch.py::test_snapshot_name_is_content_addressed
tests/test_fetch.py::test_snapshot_metadata_records_provenance
tests/test_fetch.py::test_fetch_refuses_to_run_without_credentials
tests/test_invariants.py::test_loader_never_opens_a_network_connection
```

- **reproduces the csv** — bài quan trọng nhất. Snapshot `bars_1m` cho VN30F1M phải khớp
  **từng dòng** với `ohlc_export.csv` trên mọi cột dùng chung. Sai múi giờ, sai kiểu
  `numeric`, hay quên lọc `is_final` là đỏ ngay. Đây là cách duy nhất chứng minh đường DB
  và đường CSV cho ra cùng một thứ.
- **content addressed** — fetch hai lần cùng khoảng phải ra cùng tên file
- **provenance** — thiếu bất kỳ trường nào trong số: truy vấn, số dòng, khoảng thời gian,
  hash, thời điểm lấy → đỏ
- **refuses without credentials** — nếu ai đó nhúng DSN mặc định vào code thì đỏ
- **loader never opens a network connection** — bất biến #15

Bốn bài đầu cần DB nên đánh dấu `@pytest.mark.db` và tự bỏ qua khi không có `PG_DSN`
hoặc không nối được — suite phải chạy được cả khi ngoại tuyến.

## 7. Tiêu chí chấp nhận

Thay đổi kỹ thuật, không có giả thuyết thị trường. Tập test: **đã nhìn 1 lần**, ghi trong
[SO-LAN-NHIN-TAP-TEST.md](SO-LAN-NHIN-TAP-TEST.md).

- Snapshot VN30F1M 2017-11-06 → 2026-09-04 có **đúng 533.344 dòng** và khớp CSV trên mọi
  cột dùng chung
- 50 test hiện có vẫn xanh; suite chạy được khi không có DB
- Không có DSN hay mật khẩu nào trong repo
- `loader.py` không import gì liên quan tới mạng

---

## Kết quả

**Chấp nhận**, và bài test đối chiếu đã bắt được **hai lỗi thật** — đúng như mục đích.

Đã làm: `laplace/fetch.py` (`SnapshotSpec`, `fetch_snapshot`, `load_snapshot`, CLI),
`tests/test_fetch.py` 6 bài, bất biến #15. **57/57 test xanh.**

| Tiêu chí | Kết quả |
|---|---|
| Snapshot VN30F1M có đúng 533.344 dòng | **đạt** — khớp chính xác |
| Khớp CSV trên mọi cột dùng chung | **không đạt — vì CSV sai, xem dưới** |
| 50 test cũ vẫn xanh, suite chạy khi ngoại tuyến | **đạt** — 57/57, các bài cần DB tự bỏ qua |
| Không có DSN hay mật khẩu trong repo | **đạt** — chỉ đọc `PG_DSN` |
| `loader.py` không chạm mạng | **đạt** — bất biến #15 chặn `socket.socket` |

### Lỗi 1: lệch múi giờ (đã sửa)

`ts` là `timestamptz` lưu theo UTC. Bỏ mũi giờ trực tiếp làm bar 14:27 thành 07:27, lệch
cả phiên 7 tiếng. Phải đổi sang `Asia/Ho_Chi_Minh` **trước** khi bỏ. Test bắt ngay lần
chạy đầu.

### Lỗi 2: file CSV gán nhầm nhãn BUY và SELL

Sau khi sửa múi giờ, số dòng và OHLCV khớp gần như hoàn hảo (open 0, high 1, low 0,
close 2, volume 20 dòng lệch trên 533.344 — đúng là bar đã đính chính). Nhưng bốn cột
order flow lệch ở **99,5% số dòng**, và lý do là chúng **bị hoán đổi**:

```
db.buy_vol  == csv.SELL_VOL   ở 99,996% số dòng
db.sell_vol == csv.BUY_VOL    ở 99,997% số dòng
```

Hai kiểm chứng độc lập cho biết **DB đúng, CSV sai**:

| Kiểm chứng | Nhãn của DB | Nhãn của CSV |
|---|---:|---:|
| Giá TB bên mua − bên bán (phải **dương** = spread) | **+0,586 điểm**, dương ở 94,7% bar | −0,0002 điểm, dương ở 39,1% bar |
| corr(mất cân bằng mua-bán, return trong bar) — phải **dương** | **+0,34** | −0,34 |

Người mua chủ động trả giá chào bán nên giá trung bình của họ phải cao hơn; và áp lực mua
phải đẩy giá lên. Nhãn của CSV vi phạm cả hai.

**Hệ quả: toàn bộ 22 đặc trưng nhóm `flow` hiện đang bị lật dấu.** Mạng có thể hấp thụ
một phép đổi dấu bằng trọng số âm, nên nó không phá việc học — nhưng ba chuyện thật sự
nguy hiểm:

1. `flow__px_spread` = `buy_px_edge − sell_px_edge` lẽ ra luôn dương (spread), nay luôn
   âm. Đây không phải đổi dấu vô hại mà là một giá trị vô nghĩa.
2. Mọi diễn giải đều ngược. Nhận xét tôi từng đưa ra ở spec 001 rằng *"`flow__ofi` nay
   sạch hơn"* là nói trên dữ liệu đã lật dấu.
3. **Nguy hiểm nhất**: khi chuyển sang DB cho paper trading, mọi đặc trưng `flow` sẽ
   **lặng lẽ đổi dấu**, và mô hình huấn luyện trên CSV sẽ làm ngược lại đúng những gì nó
   học. Đây chính là kịch bản mà bài test đối chiếu sinh ra để chặn.

### Đã sửa

`loader.py` đổi lại hai cột khi đọc CSV (`SELL_VOL → buy_vol`, `BUY_VOL → sell_vol`, và
tương tự cho `_VAL`), kèm chú thích đầy đủ bằng chứng ngay tại chỗ. Kiểm chứng sau khi sửa:

```
corr(flow__ofi, return trong bar)   trước: −0,3032    sau: +0,3032
```

Thêm **bất biến #16** để chuyện này không tái diễn: mất cân bằng mua-bán phải cùng dấu với
return trong bar. Sai nhãn thì tương quan **đổi dấu** chứ không về 0, nên rất dễ thấy.

### Và một phát hiện thứ ba: cột `value` của CSV không mang giá riêng từng bên

Bài kiểm tra "giá TB bên mua > bên bán" **không chạy được trên đường CSV** — không phải
vì nhãn sai mà vì thông tin đó không tồn tại:

| | Tỷ lệ bar có giá suy ra từ hai bên **bằng hệt nhau** |
|---|---:|
| CSV | **52,6%** |
| DB | 0,6% |

CSV dùng **một giá chung (VWAP)** cho cả `BUY_VAL` lẫn `SELL_VAL`; DB có giá riêng từng
bên. Đây cũng chính là lời giải cho sai lệch ~0,024% ở cột `value` mà tôi chưa giải thích
được lúc đầu.

**Hệ quả**: ba đặc trưng `flow__buy_px_edge`, `flow__sell_px_edge`, `flow__px_spread` gần
như **không mang thông tin gì trên đường CSV** (std lần lượt 0,00068 / 0,00068 / 0,00030).
Sau RobustScaler chúng bị khuếch đại lên thang đơn vị — nhiễu thuần đội lốt đặc trưng.
Chúng sẽ có nghĩa thật khi chuyển sang DB. Cần quyết: bỏ bây giờ hay giữ.

Bài kiểm tra giá đã chuyển sang `tests/test_fetch.py::test_db_buy_side_pays_more_than_sell_side`,
nơi nó áp dụng được.

### Còn một điều tôi chưa giải thích được

~~Sai lệch ~0,024% ở cột `value`~~ — **đã giải thích**: CSV dùng một giá chung cho cả hai
bên, xem mục trên. Test vẫn chốt ngưỡng 0,1% để nếu nó lớn lên thì có báo.
