const ID = /\bVT-[A-Z0-9]+-\d+\b/;
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
function section(text, name, stops) {
  const lines = text.split("\n");
  const start = lines.findIndex(line => line.trim().toLocaleLowerCase() === name.toLocaleLowerCase());
  if (start < 0) return "";
  const end = lines.findIndex((line, i) => i > start && stops.some(stop => line.trim().toLocaleLowerCase() === stop.toLocaleLowerCase()));
  return lines.slice(start + 1, end < 0 ? undefined : end).map(x => x.trim()).filter(Boolean).join("\n");
}
async function readBoard() {
  const body = document.body?.innerText || "";
  const columns = ["Ready for QA", "Verifying"].filter(name => new RegExp(`^\\s*${name}\\s*$`, "mi").test(body));
  if (location.hostname !== "product-hub.vuatho.com" || !location.pathname.startsWith("/board")) throw Error("Trang hiện tại không phải Product Hub board.");
  if (columns.length !== 2) throw Error("Không xác minh được cả hai cột Ready for QA và Verifying.");
  const nodes = [...document.querySelectorAll("button,[role=button],[data-card-id]")];
  const seen = new Set(), cards = [];
  for (const node of nodes) {
    const text = (node.innerText || "").trim();
    const id = text.match(ID)?.[0];
    if (!id || seen.has(id)) continue;
    let column = null;
    for (let p = node.parentElement; p && p !== document.body; p = p.parentElement) {
      const t = (p.innerText || "").split("\n").map(x => x.trim());
      const matches = ["Ready for QA", "Verifying"].filter(x => t.includes(x));
      if (matches.length === 1) { column = matches[0]; break; }
    }
    if (!column) continue;
    const lines = text.split("\n").map(x => x.trim()).filter(Boolean);
    const title = lines.find(x => x !== id) || id;
    node.click(); // Open the read-only detail panel; no status or comment controls are used.
    let panel = null;
    for (let attempt = 0; attempt < 20; attempt++) {
      panel = document.querySelector("#sheet-title");
      if (panel?.innerText?.trim()) break;
      await wait(150);
    }
    let detail = "";
    if (panel) {
      for (let p = panel; p && p !== document.body; p = p.parentElement) {
        const candidate = p.innerText || "";
        if (/\nQA\n|\nQA\s*:/i.test(candidate) && /DESCRIPTION/i.test(candidate)) { detail = candidate; break; }
      }
    }
    const detailLines = detail.split("\n").map(x => x.trim());
    const qaIndex = detailLines.findIndex(x => /^QA\s*:?$/i.test(x));
    const qa = detail.match(/(?:^|\n)QA\s*:\s*([^\n]+)/i)?.[1]?.trim() || (qaIndex >= 0 ? detailLines[qaIndex + 1] : "");
    if (qa === "Chin") {
      seen.add(id);
      const detailTitle = panel?.innerText?.trim() || title;
      const links = [...(panel?.parentElement?.querySelectorAll("a[href]") || [])].filter(a => a.hostname === location.hostname).map(a => ({name: (a.innerText || a.getAttribute("aria-label") || a.href).trim(), url: a.href}));
      const commentsText = section(detail, "COMMENTS", ["DESCRIPTION", "ACCEPTANCE CRITERIA", "REFERENCES"]);
      cards.push({id, title: detailTitle, url: location.href, status: column, qa,
        visible_text: text, description: section(detail, "DESCRIPTION", ["ACCEPTANCE CRITERIA", "REFERENCES", "EVIDENCE", "IMPLEMENTATION", "ACTIVITY", "PEOPLE", "COMMENTS"]),
        comments: commentsText.split("\n").filter(x => x && x.toLocaleLowerCase() !== "comment"), documents: links,
        capture_scope: "visible detail fields and same-origin document links only"});
    }
    const close = [...document.querySelectorAll("button")].find(b => ["Đóng", "Close"].includes((b.getAttribute("aria-label") || b.innerText || "").trim()));
    if (close) close.click();
    else node.click();
    await wait(100);
  }
  if (!cards.length) throw Error("Board xác minh được nhưng không tìm thấy card có QA=Chin trong hai cột. Không tạo dữ liệu giả.");
  return {schema_version: 1, source: "VuaTho QA Chrome Extension", generated_at: new Date().toISOString(), board_url: location.href, columns, cards};
}
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "VUA_THO_READ_BOARD") return;
  try { sendResponse({ok: true, data: readBoard()}); }
  catch (error) { sendResponse({ok: false, error: error.message}); }
  return true;
});
