# BẮT ĐẦU Ở ĐÂY — VuaTho QA

> Tài liệu định hướng repository, được tạo ngày 18/10/2026. Không chứa mật khẩu, token, session hoặc dữ liệu nghiệp vụ.

## Chỉ có 1 dự án chính cho báo cáo QA mỗi ngày

**[ProductHubAgent](https://github.com/Ngocchin/ProductHubAgent)** là dự án dùng để:
- đọc card ở hai cột **Ready for QA** và **Verifying** của Product Hub;
- chỉ lấy card có **QA = Chin**;
- lấy thông báo release Telegram khi tài khoản đã được cấp quyền;
- tạo checklist và báo cáo Markdown/JSON.

Không khởi tạo project khác cho mục tiêu này.

### Những repository liên quan, không phải nơi cấu hình báo cáo hằng ngày

| Repository | Chức năng đã mô tả trong README | Khi nào dùng |
|---|---|---|
| [ProductHubAgent](https://github.com/Ngocchin/ProductHubAgent) | Trợ lý đọc task/release, tạo báo cáo | **Dùng ngay** |
| [VuaTho-Mobile-QA](https://github.com/Ngocchin/VuaTho-Mobile-QA) | Framework Mobile MCP, Windows runner, Android emulator/điện thoại | Chỉ khi cần **chạy test Android thật** |
| [QA-Agent-Team](https://github.com/Ngocchin/QA-Agent-Team) | Orchestrator và các QA agent hỗ trợ test plan/test case/E2E | Sau khi cần mở rộng **AI QA team** |
| [tester-agent-team](https://github.com/Ngocchin/tester-agent-team) | README chưa nêu chức năng đầy đủ | **Chưa dùng**, không xoá tự động |

Các repository khác có thể phục vụ mục tiêu khác; bảng này không phải danh sách tất cả dự án.

## Trạng thái thực tế

- **CI/EXE/extension:** có source, tests và Windows build; phải kiểm thử trên Chrome và Product Hub đã đăng nhập để xác nhận chạy thật.
- **Product Hub:** Google SSO không chấp nhận đăng nhập trong Chrome do Playwright mở. Phiên bản mới dùng Chrome bình thường + Chrome Extension.
- **Cloud chạy khi Windows tắt:** hiện **BLOCKED**, vì chưa có hợp đồng API/credential tích hợp server-side Product Hub được quản trị viên cấp quyền, xác minh. **Không** tự nhận rằng đã hoàn tất.
- **Telegram:** phải đăng nhập OTP/2FA bên trong wizard, xác minh đúng nhóm và đọc tin nhắn thật mới được coi là kết nối thành công.
- **Các bài test chưa chạy:** tuyệt đối không báo PASS.

## Một đường đi duy nhất, không dùng terminal

1. Mở [Build Windows setup wizard](https://github.com/Ngocchin/ProductHubAgent/actions/workflows/setup-wizard.yml), chọn run **Success** trên commit mới nhất và tải artifact `VuaThoQASetup-Windows`. Không dùng EXE cũ.
2. Giải nén ZIP bằng Windows File Explorer và mở `VuaThoQASetup.exe` từ artifact tin cậy.
3. Trong wizard chọn **Install / Open Extension**. Nó mở `chrome://extensions` và thư mục `product-hub-extension`. Bật **Developer mode** → **Load unpacked** → chọn đúng thư mục wizard vừa mở. Không cần dòng lệnh.
4. Chọn **Connect Product Hub** để mở Chrome bình thường. Tự đăng nhập Google vào `https://product-hub.vuatho.com/board` bằng tài khoản được công ty cấp quyền.
5. Tại tab Product Hub, bấm biểu tượng extension → **Verify** → **Sync & Export JSON**. Chỉ coi thành công khi extension xác nhận đọc được board và QA field thật.
6. Trong wizard chọn **Verify JSON**, chọn file JSON do extension xuất → **Create Local QA Report**. Báo cáo Markdown và JSON nằm trong thư mục mới, không ghi đè lịch sử.
7. Nếu công ty cho phép đưa nội dung card lên GitHub private và GitHub token có quyền **Contents: Read and write**, chọn **Upload Saved Report** rồi xác nhận. File được đặt dưới `reports/manual-sync/`. Nếu chưa có quyền công ty thì giữ báo cáo cục bộ.
8. Để theo dõi Telegram, trong wizard dùng **Connect Telegram** → **Test Telegram** → **Save Configuration** sau khi xác minh tài khoản/nhóm; OTP, API Hash và session không bao giờ gửi qua chat.
9. [Xem reports/manual-sync](https://github.com/Ngocchin/ProductHubAgent/tree/main/reports/manual-sync) khi đã upload. Đừng coi `reports/latest.md` được cloud tạo là báo cáo mới nhất từ Chrome Extension.

**Lưu ý**: Chế độ Extension là **đồng bộ thủ công**, chỉ hoạt động khi Chrome/PC đang chạy và người dùng thao tác. Không có bảo đảm tự đồng bộ 07:30 khi PC tắt.

## Những việc còn lại

1. Chạy thật Chrome Extension trên Product Hub và xác minh có thể đọc card QA Chin (và trường hợp thực tế có 0 card).
2. Tạo báo cáo từ JSON thực và kiểm tra các trường, expected results, link card, tài liệu chưa đọc.
3. Hoàn tất Telegram trong wizard nếu được công ty cho phép.
4. Chỉ khi admin Product Hub cung cấp tài liệu API tích hợp read-only và credentials đúng quyền mới thiết kế/kiểm thử cloud automation độc lập PC.

## Luật cho Codex

- **Dự án đang làm:** `Ngocchin/ProductHubAgent`. Trước khi sửa, luôn kiểm tra repository và branch; không chọn `VuaTho-Mobile-QA` chỉ vì tên tương tự.
- Không tạo repo mới, không xoá repo/báo cáo hoặc merge PR tùy ý.
- Báo cáo `CHƯA THỂ XÁC MINH` nếu chưa có dữ liệu thật; không tạo task hoặc release giả.
- Không yêu cầu người dùng mở terminal; ưu tiên nút GUI.
- Không gửi dữ liệu công ty sang AI/API bên ngoài nếu chưa được phép.
- Tách **test case đề xuất** khỏi **test thực thi có bằng chứng**.

## Đường dẫn nhanh

- [ProductHubAgent](https://github.com/Ngocchin/ProductHubAgent)
- [Windows Wizard Builds](https://github.com/Ngocchin/ProductHubAgent/actions/workflows/setup-wizard.yml)
- [QA Daily Workflow](https://github.com/Ngocchin/ProductHubAgent/actions/workflows/daily-qa.yml)
- [GitHub Actions Reports](https://github.com/Ngocchin/ProductHubAgent/tree/main/reports)
