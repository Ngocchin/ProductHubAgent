const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../../product-hub-extension/content.js"), "utf8");

function fixture(cards, options = {}) {
  let opened = null;
  let horizontalScrolled = false;
  let lazyLoaded = false;
  const titleNode = {innerText: "", parentElement: null};
  const detailPane = {innerText: "", parentElement: null, querySelectorAll: () => []};
  titleNode.parentElement = detailPane;
  const body = {innerText: options.bodyText ?? "Product Hub\nReady for QA\nVerifying"};
  const nodes = cards.map(card => {
    const lane = {innerText: `${card.status}\n${card.id}\n${card.title}`, parentElement: body};
    const node = {
      innerText: `${card.id}\n${card.title}`, parentElement: lane,
      getAttribute(name) { return name === "data-card-id" ? (card.domId || null) : null; },
      click() {
        if (opened === card) opened = null;
        else {
          opened = card;
          if (!options.noDetail) {
            titleNode.innerText = card.title;
            detailPane.innerText = card.detail ?? `${card.title}\nQA\n${card.qa}\nDESCRIPTION\n${card.description || ""}\nACCEPTANCE CRITERIA\n${(card.criteria || []).join("\n")}`;
          }
        }
      },
    };
    return node;
  });
  const scrollArea = {clientWidth: 300, scrollWidth: options.horizontal ? 700 : 300, scrollLeft: 0,
    clientHeight: 300, scrollHeight: 300, scrollTop: 0};
  Object.defineProperty(scrollArea, "scrollLeft", {get() { return this._scrollLeft || 0; }, set(value) { this._scrollLeft = value; if (value > 0) { horizontalScrolled = true; lazyLoaded = true; } }});
  const document = {
    body,
    querySelectorAll(selector) {
      if (selector === "*") return options.horizontal ? [scrollArea] : [];
      if (selector === "button,[role=button],[data-card-id]") return nodes.filter((_, index) => !cards[index].lazy || lazyLoaded);
      if (selector === "button") return [];
      return [];
    },
    querySelector(selector) { return selector === "#sheet-title" && opened && !options.noDetail ? titleNode : null; },
  };
  let listener;
  const chrome = {runtime: {onMessage: {addListener(value) { listener = value; }}}};
  const context = {document, chrome, location: {hostname: "product-hub.vuatho.com", pathname: "/board", href: "https://product-hub.vuatho.com/board"},
    window: {scrollY: 0, scrollTo() {}}, Date, Promise, Error, Set, Map, RegExp, Math, setTimeout};
  vm.runInNewContext(source, context, {filename: "content.js"});
  return {listener: (...args) => listener(...args), get horizontalScrolled() { return horizontalScrolled; }};
}

function send(harness, message = {type: "VUA_THO_READ_BOARD"}) {
  return new Promise((resolve, reject) => {
    let synchronous = true, calledSynchronously = false;
    const keepOpen = harness.listener(message, {}, result => {
      if (synchronous) calledSynchronously = true;
      resolve(result);
    });
    synchronous = false;
    if (keepOpen !== true) reject(new Error("async content handler must keep the Chrome message port open"));
    if (calledSynchronously) reject(new Error("response was sent before async board scan resolved"));
  });
}

test("async board scan resolves before responding and keeps message channel open", async () => {
  const h = fixture([{id: "VT-APP-1", title: "One", status: "Ready for QA", qa: "Chin"}]);
  const response = await send(h);
  assert.equal(response.ok, true, response.error);
  assert.equal(response.data.cards.length, 1);
  assert.equal(response.data.cards[0].qa, "Chin");
});

test("successful scan with cards but no exact QA Chin is distinct from a read failure", async () => {
  const h = fixture([
    {id: "VT-APP-1", title: "One", status: "Ready for QA", qa: "Reporter"},
    {id: "VT-APP-2", title: "Two", status: "Verifying", qa: "chin"},
  ]);
  const response = await send(h);
  assert.equal(response.ok, true);
  assert.equal(response.data.cards_scanned, 2);
  assert.deepEqual(Array.from(response.data.cards), []);
});

test("cards in both columns and lazy content are scanned after horizontal scrolling", async () => {
  const h = fixture([
    {id: "VT-APP-1", title: "One", status: "Ready for QA", qa: "Chin"},
    {id: "VT-APP-2", title: "Two", status: "Verifying", qa: "Chin", lazy: true},
  ], {horizontal: true});
  const response = await send(h);
  assert.equal(h.horizontalScrolled, true);
  assert.deepEqual(Array.from(response.data.cards, card => card.status), ["Ready for QA", "Verifying"]);
});

test("missing QA field is reported as an error and Reporter/Assignee never stand in for QA", async () => {
  const h = fixture([{id: "VT-APP-1", title: "One", status: "Ready for QA", detail: "One\nReporter\nChin\nAssignee\nChin\nDESCRIPTION\nBody"}]);
  const response = await send(h);
  assert.equal(response.ok, false);
  assert.equal(response.code, "QA_FIELD_UNREADABLE");
});

test("missing detail panel and unreadable board have separate error codes", async () => {
  const noDetail = fixture([{id: "VT-APP-1", title: "One", status: "Ready for QA", qa: "Chin"}], {noDetail: true});
  const detailError = await send(noDetail);
  assert.equal(detailError.ok, false);
  assert.equal(detailError.code, "DETAIL_UNREADABLE");
  const emptyBoard = fixture([]);
  const board = await send(emptyBoard);
  assert.equal(board.ok, false);
  assert.equal(board.code, "CARD_UNREADABLE");
  const badBoard = fixture([], {bodyText: "Product Hub"});
  const unreadable = await send(badBoard);
  assert.equal(unreadable.ok, false);
  assert.equal(unreadable.code, "BOARD_UNREADABLE");
});

test("unknown messages are ignored", () => {
  const h = fixture([]);
  assert.equal(h.listener({type: "OTHER"}, {}, () => {}), false);
});

test("popup Connect, Verify, and Sync & Export use real content message results", async () => {
  const content = fixture([{id: "VT-APP-1", title: "Payment QA", status: "Verifying", qa: "Chin", description: "Approved flow"}]);
  const elements = Object.fromEntries(["connect", "verify", "sync", "status", "last-sync"].map(id => [id, {textContent: "", onclick: null}]));
  const downloads = [], tabs = [];
  const store = {};
  const urls = new Map();
  let nextUrl = 0;
  const chrome = {
    tabs: {
      async query() { return [{id: 7, url: "https://product-hub.vuatho.com/board"}]; },
      async sendMessage(_tabId, message) { return await send(content, message); },
      async create(value) { tabs.push(value); },
    },
    downloads: {async download(value) { downloads.push(value); return 1; }},
    storage: {local: {get(_key, callback) { callback({lastSync: store.lastSync}); }, async set(value) { Object.assign(store, value); }}},
  };
  const context = {document: {getElementById(id) { return elements[id]; }}, chrome, Blob, Date, Promise, Error,
    URL: {createObjectURL(blob) { const url = `blob:${++nextUrl}`; urls.set(url, blob); return url; }, revokeObjectURL() {}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../product-hub-extension/popup.js"), "utf8"), context);
  elements.connect.onclick();
  assert.equal(tabs.length, 1);
  assert.equal(tabs[0].url, "https://product-hub.vuatho.com/board");
  await elements.verify.onclick();
  assert.match(elements.status.textContent, /Quét thành công · 1 card đã đọc · 1 card QA=Chin/);
  await elements.sync.onclick();
  assert.equal(downloads.length, 1);
  assert.equal(downloads[0].saveAs, true);
  const exported = JSON.parse(await urls.get(downloads[0].url).text());
  assert.equal(exported.cards[0].id, "VT-APP-1");
  assert.match(store.lastSync, /^\d{4}-\d\d-\d\dT/);
  assert.match(elements.status.textContent, /xuất 1 card QA=Chin/);
  assert.match(elements["last-sync"].textContent, /^Last sync: \d{4}-/);
});
