(() => {
  const ID = /\bVT-[A-Z0-9]+-\d+\b/;
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

  function fail(code, message) {
    const error = new Error(message);
    error.code = code;
    return error;
  }

  function getColumn(node) {
    for (let parent = node.parentElement; parent && parent !== document.body; parent = parent.parentElement) {
      const lines = (parent.innerText || "").split("\n").map(value => value.trim());
      const matches = ["Ready for QA", "Verifying"].filter(value => lines.includes(value));
      if (matches.length === 1) return matches[0];
    }
    return null;
  }

  function candidates() {
    const found = new Map();
    for (const node of document.querySelectorAll("button,[role=button],[data-card-id]")) {
      const text = (node.innerText || "").trim();
      const id = node.getAttribute("data-card-id") || text.match(ID)?.[0];
      if (!id || !ID.test(id)) continue;
      const status = getColumn(node);
      if (!status) continue;
      if (!found.has(id)) found.set(id, {node, id, status, visibleText: text});
    }
    return [...found.values()];
  }

  async function revealBoard() {
    const initialY = window.scrollY || 0;
    let previousCount = -1, stableRounds = 0;
    for (let round = 0; round < 16 && stableRounds < 2; round++) {
      const scrollables = [...document.querySelectorAll("*")].filter(element =>
        element.clientWidth > 0 && element.scrollWidth > element.clientWidth + 8
      );
      for (const element of scrollables) {
        const original = element.scrollLeft || 0;
        const step = Math.max(200, element.clientWidth || 300);
        for (let x = 0; x < element.scrollWidth; x += step) {
          element.scrollLeft = Math.min(x, element.scrollWidth);
          await wait(50);
        }
        element.scrollLeft = original;
      }

      const vertical = [...document.querySelectorAll("*")].filter(element =>
        element.clientHeight > 0 && element.scrollHeight > element.clientHeight + 8
      );
      for (const element of vertical) {
        const original = element.scrollTop || 0;
        const step = Math.max(200, element.clientHeight || 300);
        for (let y = 0; y < element.scrollHeight; y += step) {
          element.scrollTop = Math.min(y, element.scrollHeight);
          await wait(75);
        }
        element.scrollTop = original;
      }

      window.scrollTo(0, document.body.scrollHeight);
      await wait(150);
      const count = candidates().length;
      stableRounds = count === previousCount ? stableRounds + 1 : 0;
      previousCount = count;
    }
    window.scrollTo(0, initialY);
  }

  function detailText(titleNode) {
    for (let parent = titleNode; parent && parent !== document.body; parent = parent.parentElement) {
      const text = parent.innerText || "";
      if (/\bDESCRIPTION\b/i.test(text) || /(?:^|\n)QA\s*:?/im.test(text)) return text;
    }
    return "";
  }

  function readQa(text, taskId) {
    const lines = text.split("\n").map(value => value.trim());
    const values = [];
    for (let index = 0; index < lines.length; index++) {
      const inline = lines[index].match(/^QA\s*:\s*(.+)$/i);
      if (inline) values.push(inline[1].trim());
      else if (/^QA\s*:?$/i.test(lines[index])) {
        const value = lines[index + 1];
        if (value) values.push(value.trim());
      }
    }
    if (values.length !== 1) throw fail("QA_FIELD_UNREADABLE", `${taskId}: không đọc được duy nhất một trường QA.`);
    return values[0];
  }

  function section(text, name, stops) {
    const lines = text.split("\n");
    const start = lines.findIndex(line => line.trim().toLocaleLowerCase() === name.toLocaleLowerCase());
    if (start < 0) return "";
    const end = lines.findIndex((line, index) => index > start && stops.some(stop => line.trim().toLocaleLowerCase() === stop.toLocaleLowerCase()));
    return lines.slice(start + 1, end < 0 ? undefined : end).map(line => line.trim()).filter(Boolean).join("\n");
  }

  async function readBoard() {
    if (location.hostname !== "product-hub.vuatho.com" || !location.pathname.startsWith("/board")) {
      throw fail("BOARD_UNREADABLE", "Tab hiện tại không phải Product Hub board.");
    }
    const visibleText = document.body?.innerText || "";
    const columns = ["Ready for QA", "Verifying"].filter(name =>
      new RegExp(`^\\s*${name}\\s*$`, "mi").test(visibleText)
    );
    if (columns.length !== 2) throw fail("BOARD_UNREADABLE", "Không xác minh được cả hai cột Ready for QA và Verifying.");

    await revealBoard();
    const cardsFound = candidates();
    if (!cardsFound.length) throw fail("CARD_UNREADABLE", "Đã thấy hai cột nhưng không đọc được card nào để xác định QA; không thể kết luận là 0 card QA Chin.");

    const cards = [];
    for (const item of cardsFound) {
      const title = item.visibleText.split("\n").map(value => value.trim()).find(value => value && value !== item.id) || item.id;
      try {
        item.node.click(); // Read-only open of a card detail panel; no edit, status, or comment action.
        let titleNode = null;
        for (let attempt = 0; attempt < 12; attempt++) {
          titleNode = document.querySelector("#sheet-title");
          if (titleNode?.innerText?.trim()) break;
          await wait(100);
        }
        if (!titleNode?.innerText?.trim()) throw fail("DETAIL_UNREADABLE", `${item.id}: không mở/đọc được chi tiết card.`);
        const text = detailText(titleNode);
        if (!text) throw fail("DETAIL_UNREADABLE", `${item.id}: panel chi tiết không có nội dung đọc được.`);
        const qa = readQa(text, item.id);
        if (qa === "Chin") {
          const pane = titleNode.parentElement;
          const links = [...(pane?.querySelectorAll("a[href]") || [])]
            .filter(link => link.hostname === location.hostname)
            .map(link => ({name: (link.innerText || link.getAttribute("aria-label") || link.href).trim(), url: link.href}));
          const criteria = section(text, "ACCEPTANCE CRITERIA", ["REFERENCES", "EVIDENCE", "IMPLEMENTATION", "ACTIVITY", "PEOPLE", "COMMENTS"])
            .split("\n").map(value => value.replace(/^\d+[.)]\s*/, "").trim()).filter(Boolean);
          const comments = section(text, "COMMENTS", ["DESCRIPTION", "ACCEPTANCE CRITERIA", "REFERENCES"])
            .split("\n").filter(value => value && value.toLocaleLowerCase() !== "comment");
          cards.push({id: item.id, title, url: location.href, status: item.status, qa,
            visible_text: item.visibleText,
            description: section(text, "DESCRIPTION", ["ACCEPTANCE CRITERIA", "REFERENCES", "EVIDENCE", "IMPLEMENTATION", "ACTIVITY", "PEOPLE", "COMMENTS"]),
            acceptance_criteria: criteria, comments, documents: links,
            capture_scope: "visible card detail and same-origin document links; linked files are not downloaded"});
        }
      } catch (error) {
        if (error?.code) throw error;
        throw fail("CARD_UNREADABLE", `${item.id}: lỗi khi đọc card (${error?.name || "Error"}).`);
      } finally {
        const close = [...document.querySelectorAll("button")].find(button =>
          ["Đóng", "Close"].includes((button.getAttribute("aria-label") || button.innerText || "").trim())
        );
        if (close) close.click();
        else item.node.click();
        await wait(75);
      }
    }

    return {schema_version: 1, source: "VuaTho QA Chrome Extension", generated_at: new Date().toISOString(),
      board_url: location.href, columns, cards_scanned: cardsFound.length, cards};
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message?.type !== "VUA_THO_READ_BOARD") return false;
    readBoard()
      .then(data => sendResponse({ok: true, data}))
      .catch(error => sendResponse({ok: false, code: error?.code || "BOARD_UNREADABLE", error: error?.message || "Không đọc được Product Hub board."}));
    return true; // Keep the Chrome message channel open until the Promise resolves.
  });
})();
