const status = document.getElementById("status");
const board = "https://product-hub.vuatho.com/board";
document.getElementById("connect").onclick = () => chrome.tabs.create({url: board});
async function readBoard() {
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab?.url?.startsWith(board)) throw new Error("Mở Product Hub board trong tab hiện tại trước.");
  const response = await chrome.tabs.sendMessage(tab.id, {type: "VUA_THO_READ_BOARD"});
  if (!response?.ok) throw new Error(response?.error || "Không đọc được board.");
  return response.data;
}
document.getElementById("verify").onclick = async () => {
  status.textContent = "Đang xác minh board và trường QA…";
  try { const d = await readBoard(); status.textContent = `Quét thành công · ${d.cards_scanned} card đã đọc · ${d.cards.length} card QA=Chin · ${d.columns.join(", ")}`; }
  catch (e) { status.textContent = e.message; }
};
document.getElementById("sync").onclick = async () => {
  status.textContent = "Đang đọc nội dung đang hiển thị…";
  try {
    const d = await readBoard();
    const file = new Blob([JSON.stringify(d, null, 2)], {type: "application/json"});
    const url = URL.createObjectURL(file);
    await chrome.downloads.download({url, filename: "vuatho-product-hub-qa.json", saveAs: true});
    URL.revokeObjectURL(url);
    const time = new Date().toISOString();
    await chrome.storage.local.set({lastSync: time});
    status.textContent = `Đã quét ${d.cards_scanned} card và xuất ${d.cards.length} card QA=Chin. Chọn vị trí lưu JSON.`;
    const label = document.getElementById("last-sync");
    if (label) label.textContent = `Last sync: ${time}`;
  } catch (e) { status.textContent = e.message; }
};
chrome.storage.local.get("lastSync", ({lastSync}) => {
  const label = document.getElementById("last-sync");
  if (label) label.textContent = `Last sync: ${lastSync || "chưa đồng bộ"}`;
});
