# BẮT ĐẦU Ở ĐÂY — Sơ đồ các project QA Vua Thợ

> Cập nhật 18/10/2026. Tài liệu điều hướng nội bộ; không đồng nghĩa các kết nối đã hoạt động trên môi trường thực tế.
>
> **Quy tắc:** Chỉ dùng **Ngocchin/ProductHubAgent** làm điểm bắt đầu của công việc *đọc task QA Chin, theo dõi release Telegram và lập báo cáo QA*. Không tạo repo mới cho quy trình này.

## 1. Project nào làm việc gì?

| Repo private | Vai trò | Dùng khi nào |
| --- | --- | --- |
| [ProductHubAgent](https://github.com/Ngocchin/ProductHubAgent) | **Đầu mối QA Daily:** Chrome Extension đọc Product Hub, kết nối Telegram, tạo checklist và report | **Dùng ngay** khi kiểm tra Ready for QA / Verifying, QA = Chin |
| [VuaTho-Mobile-QA](https://github.com/Ngocchin/VuaTho-Mobile-QA) | Android testing: Mobile MCP, thiết bị thật / Emulator, Windows self-hosted runner, evidence | Chỉ mở khi muốn chạy automation trên app Android |
| [QA-Agent-Team](https://github.com/Ngocchin/QA-Agent-Team) | Điều phối AI QA, thiết kế test case, review và quy trình E2E web/mobile | Dùng khi cần mở rộng thành AI QA Team |
| [tester-agent-team](https://github.com/Ngocchin/tester-agent-team) | Repo chỉ có README khởi tạo ở thời điểm kiểm tra | **Không dùng** cho luồng QA Daily hiện tại |
| [VuaTho_App](https://github.com/Ngocchin/VuaTho_App) | Repo chỉ có README khởi tạo ở thời điểm kiểm tra | **Không dùng** cho luồng QA Daily hiện tại |

Các project không liên quan QA Mobile (Yuzhen, affiliate, personal workspace, bài tập) có phạm vi riêng; **không xóa, không merge, không đổi tên** khi chưa có quyết định.

## 2. Tình trạng QA Daily hiện tại

- GitHub CI và Windows Wizard build đã **PASS** trên commit `936ef5405019ed06d704cd254eb7443bb7a9a0ec`.
- Chrome Extension đã có source và kiểm thử bằng fixture DOM, **chưa xác minh đã đọc được board Product Hub thật bằng Chrome người dùng**.
- Phần Product Hub **cloud lúc PC tắt: BLOCKED** vì chưa có API/integration read-only server-side được quản trị viên cấp và kiểm chứng.
- Chrome Extension là **manual sync**: cần Chrome đang chạy và người dùng chủ động chọn Verify / Sync & Export JSON.
- Tài liệu hoặc file đính kèm chỉ được ghi link khi có thể thấy; chưa đọc được nội dung thì đánh dấu thiếu nguồn.
- Telegram cần đăng nhập MTProto và xác minh nhóm được cấp quyền; không giả định đã kết nối.
- Mọi báo cáo phải ghi rõ nguồn và thời điểm đồng bộ. Chưa test thì không được ghi PASS.

## 3. Chỉ một luồng thao tác tiếp theo (không terminal)

1. Mở [Build Windows Setup Wizard — run thành công](https://github.com/Ngocchin/ProductHubAgent/actions/runs/39123219186), ở **Artifacts** tải `VuaThoQASetup-Windows`. Giải nén và mở EXE mới.
2. Trong wizard, chọn **Install / Open Extension**. Trong Chrome mở `chrome://extensions`, bật **Developer mode**, chọn **Load unpacked**, chọn thư mục `product-hub-extension` mà wizard mở ra. Chỉ cài extension nếu được công ty cho phép truy cập dữ liệu Product Hub theo cách này.
3. Mở **https://product-hub.vuatho.com/board** trên Chrome bình thường đã đăng nhập. Mở popup extension, chọn **Verify** rồi **Sync & Export JSON**. Nếu báo lỗi thì không tự kết luận rằng không có task.
4. Quay về wizard, **Verify JSON** với file vừa xuất. Bấm **Create Local QA Report** để có bản Markdown/JSON trên máy.
5. Chỉ khi được phép đưa tài liệu nội bộ lên GitHub private, dùng **Upload Saved Report**, xác nhận và dùng token fine-grained có **Contents: Read and write** cho riêng repo này. Không gửi token/OTP/session lên chat hoặc commit.
6. Nếu muốn đọc Telegram, dùng bước **Connect Telegram → Test Telegram** trong wizard sau khi cấp phép. Không coi đăng nhập Telegram là đã thực hiện nếu chưa có kết quả xác minh thật.

## 4. Sau khi làm xong

- Báo cáo manual trong repo: [reports/manual-sync](https://github.com/Ngocchin/ProductHubAgent/tree/main/reports/manual-sync) (chỉ có dữ liệu nếu người dùng đã upload và quyền cho phép).
- Báo cáo cloud: [reports/latest.md](https://github.com/Ngocchin/ProductHubAgent/blob/main/reports/latest.md). Có thể cũ hoặc bị BLOCKED; **luôn kiểm tra ngày và blockers**.
- Chỉ khi Product Hub có API read-only được xác minh, mới chuyển sang thu thập server-side không cần bật PC.

## 5. Giao việc cho AI/Codex theo đúng repo

- “Đọc task QA Chin và Telegram, lập báo cáo” → `Ngocchin/ProductHubAgent`.
- “Mở Android Emulator / chạy test máy thật bằng Mobile MCP” → `Ngocchin/VuaTho-Mobile-QA`.
- “Thiết kế test case / multi-agent / E2E” → `Ngocchin/QA-Agent-Team`.

**Không tự tạo thêm repository hoặc thay đổi các project còn lại khi một trong ba repo này đã phù hợp.**
