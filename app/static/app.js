"use strict";

const NS = "http://www.w3.org/2000/svg";
const ICONS = {
  shield: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"],
  shieldcheck: ["M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z", "M9 12l2 2 4-4"],
  files: ["M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z", "M14 2v6h6", "M16 13H8", "M16 17H8", "M10 9H8"],
  upload: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "M17 8l-5-5-5 5", "M12 3v12"],
  download: ["M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4", "M7 10l5 5 5-5", "M12 15V3"],
  activity: ["M22 12h-4l-3 9L9 3l-3 9H2"],
  bell: ["M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9", "M13.73 21a2 2 0 0 1-3.46 0"],
  users: ["M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2", "M9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z", "M23 21v-2a4 4 0 0 0-3-3.87", "M16 3.13a4 4 0 0 1 0 7.75"],
  userplus: ["M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2", "M8.5 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8z", "M20 8v6", "M23 11h-6"],
  pencil: ["M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"],
  refresh: ["M21 2v6h-6", "M3 12a9 9 0 0 1 15-6.7L21 8", "M3 22v-6h6", "M21 12a9 9 0 0 1-15 6.7L3 16"],
  trash: ["M3 6h18", "M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6", "M10 11v6", "M14 11v6", "M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"],
  logout: ["M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4", "M16 17l5-5-5-5", "M21 12H9"],
  search: ["M11 3a8 8 0 1 0 0 16 8 8 0 0 0 0-16z", "M21 21l-4.35-4.35"],
  moon: ["M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"],
  sun: ["M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z", "M12 1v2", "M12 21v2", "M4.22 4.22l1.42 1.42", "M18.36 18.36l1.42 1.42", "M1 12h2", "M21 12h2", "M4.22 19.78l1.42-1.42", "M18.36 5.64l1.42-1.42"],
  lock: ["M5 11h14a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2z", "M7 11V7a5 5 0 0 1 10 0v4"],
  zap: ["M13 2L3 14h9l-1 8 10-12h-9l1-8z"],
  eye: ["M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z", "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"],
  x: ["M18 6L6 18", "M6 6l12 12"],
  check: ["M22 11.08V12a10 10 0 1 1-5.93-9.14", "M22 4L12 14.01l-3-3"],
  alert: ["M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z", "M12 9v4", "M12 17h.01"],
};

const NAV = {
  owner: [
    ["documents", "Documents", "files", "Documents you own or that were shared with you"],
    ["catalogue", "Document Catalogue", "search", "Find documents and request access"],
    ["upload", "Upload", "upload", "Add a new document"],
    ["myRequests", "My Requests", "clock", "Track your access requests"],
    ["incomingRequests", "Incoming Requests", "users", "Review requests for your documents"],
  ],
  viewer: [
    ["documents", "Shared with me", "files", "Documents other people have shared with you"],
    ["catalogue", "Document Catalogue", "search", "Find documents and request access"],
    ["myRequests", "My Requests", "clock", "Track your access requests"],
  ],
  admin: [
    ["catalogue", "Document Catalogue", "search", "Find documents and request access"],
    ["myRequests", "My Requests", "clock", "Track your access requests"],
    ["activity", "Activity", "activity", "Every action, including refused attempts"],
    ["alerts", "Alerts", "bell", "Unusual behaviour worth a look"],
    ["users", "Users", "users", "Accounts and their access"],
    ["integrity", "Integrity", "shieldcheck", "Proof that the audit log was not altered"],
  ],
};

const DEMO = [["Admin", "admin@trustvault.test"], ["Owner", "owner1@trustvault.test"],
              ["Second owner", "owner2@trustvault.test"], ["Viewer", "viewer@trustvault.test"]];

const state = { token: sessionStorage.getItem("tv_token"), me: null, tab: null, filters: {}, alerts: 0 };
const $ = (id) => document.getElementById(id);

/* ---------- helpers ---------- */

function icon(name) {
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  for (const d of ICONS[name]) {
    const path = document.createElementNS(NS, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

/* Build elements safely: text is always added as text, never as HTML. */
function el(tag, attrs, ...kids) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (value !== false && value != null) node.setAttribute(key, value);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    node.append(kid instanceof Node ? kid : String(kid));
  }
  return node;
}

const qs = (obj) => { const s = new URLSearchParams(obj).toString(); return s ? "?" + s : ""; };
const size = (n) => (n < 1024 ? n + " B" : n < 1048576 ? (n / 1024).toFixed(1) + " KB" : (n / 1048576).toFixed(1) + " MB");
const full = (iso) => new Date(iso).toLocaleString();
const pill = (text, kind) => el("span", { class: "pill " + (kind || text) }, text);

function ago(iso) {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + " min ago";
  if (s < 86400) return Math.floor(s / 3600) + " h ago";
  if (s < 604800) return Math.floor(s / 86400) + " d ago";
  return new Date(iso).toLocaleDateString();
}

function initials(email) {
  const parts = String(email || "?").split("@")[0].split(/[._-]+/).filter(Boolean);
  return ((parts[0] || "?")[0] + ((parts[1] || "")[0] || "")).toUpperCase();
}
const avatarClass = (email) => "av" + ([...String(email)].reduce((a, c) => a + c.charCodeAt(0), 0) % 6);

function person(email, label) {
  return el("div", { class: "person" },
    el("span", { class: "avatar " + avatarClass(email) }, initials(email)),
    el("span", {}, label || email));
}

function friendly(err) {
  return err.status === 404 && err.message === "Not found" ? "Not found, or you do not have access." : err.message;
}

function toast(text, kind) {
  const t = el("div", { class: "toast " + (kind || ""), role: kind === "error" ? "alert" : "status" },
    icon(kind === "error" ? "alert" : "check"), el("span", {}, text));
  t.addEventListener("click", () => t.remove());
  $("toasts").append(t);
  setTimeout(() => t.remove(), kind === "error" ? 7000 : 4000);
}

function busy(btn, on, label) {
  btn.disabled = on;
  btn.replaceChildren(...(on ? [el("span", { class: "spinner" }), "Working"] : [label]));
}

function field(name, label, type, value, required) {
  return el("label", {}, label,
    el("input", { name, type: type || "text", value: value || "", required: required ? "required" : false }));
}

function table(headers, rows) {
  return el("div", { class: "table-wrap" }, el("table", {},
    el("thead", {}, el("tr", {}, headers.map((h) => el("th", {}, h)))),
    el("tbody", {}, rows)));
}

function emptyState(iconName, title, text, action) {
  return el("div", { class: "empty" }, icon(iconName), el("strong", {}, title), text ? el("p", {}, text) : null, action || null);
}

const skeleton = () => el("div", {}, el("div", { class: "skeleton" }), el("div", { class: "skeleton" }), el("div", { class: "skeleton" }));
const iconBtn = (name, label, onclick, kind) =>
  el("button", { class: "icon-btn " + (kind || ""), title: label, "aria-label": label, onclick }, icon(name));

/* ---------- confirmation dialog ---------- */

function ask(title, text, okLabel, danger) {
  return new Promise((resolve) => {
    const d = $("dialog");
    const done = (v) => { d.close(); resolve(v); };
    d.addEventListener("close", () => resolve(false), { once: true });
    d.replaceChildren(el("h3", {}, title), el("p", { class: "muted" }, text),
      el("div", { class: "dialog-actions" },
        el("button", { class: "btn ghost", onclick: () => done(false) }, "Cancel"),
        el("button", { class: "btn " + (danger ? "danger-solid" : ""), onclick: () => done(true) }, okLabel)));
    d.showModal();
  });
}

/* ---------- API ---------- */

async function api(path, options = {}) {
  const headers = {};
  if (state.token) headers["Authorization"] = "Bearer " + state.token;
  let body;
  if (options.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.json);
  } else if (options.form) {
    body = options.form;
  }
  const res = await fetch(path, { method: options.method || "GET", headers, body });
  if (res.status === 401 && state.token) {
    signOut("Your session has ended. Please sign in again.");
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    let detail = res.statusText || "Request failed";
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : "Please check the form and try again.";
    } catch (_) { /* not JSON */ }
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return options.blob ? res.blob() : res.json();
}

/* ---------- theme, shell, sign in/out ---------- */

function applyTheme(theme) {
  if (theme) document.documentElement.dataset.theme = theme;
  else delete document.documentElement.dataset.theme;
}
applyTheme(localStorage.getItem("tv_theme"));
const isDark = () => document.documentElement.dataset.theme === "dark" ||
  (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);

function renderFooter() {
  const dark = isDark();
  $("side-foot").replaceChildren(
    el("div", { class: "me" }, el("span", { class: "avatar " + avatarClass(state.me.email) }, initials(state.me.email)),
      el("div", { class: "me-text" }, el("div", { class: "me-email" }, state.me.email), pill(state.me.role))),
    el("button", { class: "nav-item", onclick: () => {
      localStorage.setItem("tv_theme", dark ? "light" : "dark");
      applyTheme(dark ? "light" : "dark");
      renderFooter();
    } }, icon(dark ? "sun" : "moon"), dark ? "Light mode" : "Dark mode"),
    el("button", { class: "nav-item", onclick: async () => {
      try { await api("/auth/logout", { method: "POST" }); } catch (_) { /* already signed out */ }
      signOut("");
    } }, icon("logout"), "Sign out"));
}

function renderNav() {
  $("nav").replaceChildren(
    el("div", { class: "nav-label" }, state.me.role === "admin" ? "Administration" : "Workspace"),
    ...NAV[state.me.role].map(([key, label, iconName]) =>
      el("button", { class: "nav-item" + (key === state.tab ? " active" : ""), onclick: () => show(key) },
        icon(iconName), label,
        key === "alerts" && state.alerts > 0 ? el("span", { class: "badge" }, state.alerts) : null)));
}

function signOut(message) {
  state.token = null;
  state.me = null;
  sessionStorage.removeItem("tv_token");
  if ($("dialog").open) $("dialog").close();
  $("shell").classList.add("hidden");
  $("login-screen").classList.remove("hidden");
  $("login-msg").textContent = message || "";
}

async function start() {
  try { state.me = await api("/me"); } catch (_) { return; }
  $("login-screen").classList.add("hidden");
  $("shell").classList.remove("hidden");
  renderFooter();
  if (state.me.role === "admin") {
    try { state.alerts = (await api("/admin/alerts")).length; } catch (_) { state.alerts = 0; }
  }
  show(NAV[state.me.role][0][0]);
}

async function show(tab, note) {
  state.tab = tab;
  const meta = NAV[state.me.role].find(([key]) => key === tab);
  $("page-title").textContent = meta[1];
  $("page-sub").textContent = meta[3];
  $("page-actions").replaceChildren();
  renderNav();
  const view = $("view");
  view.replaceChildren(skeleton());
  if (note) toast(note, "ok");
  try {
    await VIEWS[tab](view);
  } catch (err) {
    if (err.message !== "unauthorized") {
      toast(friendly(err), "error");
      view.replaceChildren(emptyState("alert", "Something went wrong", friendly(err)));
    }
  }
}

/* ---------- documents ---------- */

async function download(d) {
  try {
    const blob = await api("/documents/" + d.id + "/download", { blob: true });
    const url = URL.createObjectURL(blob);
    const link = el("a", { href: url, download: d.name });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (err) { toast(friendly(err), "error"); }
}

function replaceContent(d) {
  const input = el("input", { type: "file", accept: "." + d.name.split(".").pop().toLowerCase() });
  input.addEventListener("change", async () => {
    const file = input.files[0];
    if (!file) return;
    if (!(await ask("Replace file contents",
      "The contents of \"" + d.name + "\" will be overwritten with \"" + file.name + "\". The name stays the same.",
      "Replace", true))) return;
    const data = new FormData();
    data.append("file", file);
    try {
      await api("/documents/" + d.id + "/content", { method: "PUT", form: data });
      show("documents", "File contents replaced.");
    } catch (err) { toast(friendly(err), "error"); }
  });
  input.click();
}

function editDetails(d) {
  const dlg = $("dialog");
  const form = el("form", {}, el("h3", {}, "Edit details"),
    field("name", "Name", "text", d.name, true), field("category", "Category", "text", d.category || ""),
    el("div", { class: "dialog-actions" },
      el("button", { type: "button", class: "btn ghost", onclick: () => dlg.close() }, "Cancel"),
      el("button", { type: "submit", class: "btn" }, "Save")));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(form);
    try {
      await api("/documents/" + d.id, { method: "PATCH",
        json: { name: data.get("name").trim(), category: data.get("category").trim() } });
      dlg.close();
      show("documents", "Details saved.");
    } catch (err) { toast(friendly(err), "error"); }
  });
  dlg.replaceChildren(form);
  dlg.showModal();
}

async function remove(d) {
  if (!(await ask("Delete document", "\"" + d.name + "\" will no longer open for anyone, including you.", "Delete", true))) return;
  try {
    await api("/documents/" + d.id, { method: "DELETE" });
    show("documents", "Deleted.");
  } catch (err) { toast(friendly(err), "error"); }
}

async function openShare(d) {
  const dlg = $("dialog");
  const render = async () => {
    const grants = await api("/documents/" + d.id + "/grants");
    const list = grants.length
      ? el("ul", { class: "people" }, grants.map((g) => el("li", {},
          person(g.email), pill(g.permission), el("span", { class: "muted small" }, ago(g.granted_at)),
          el("button", { class: "btn danger sm", onclick: async () => {
            try {
              await api("/documents/" + d.id + "/grants/" + g.user_id, { method: "DELETE" });
              toast("Access taken back. It stops working immediately.", "ok");
              await render();
            } catch (err) { toast(friendly(err), "error"); }
          } }, "Take back"))))
      : el("p", { class: "muted" }, "Not shared with anyone yet.");
    const form = el("form", { class: "add-row" },
      field("email", "Person's email", "email", "", true),
      el("label", {}, "Access", el("select", { name: "permission" },
        el("option", { value: "read" }, "Read only"), el("option", { value: "edit" }, "Read and edit"))),
      el("button", { type: "submit", class: "btn" }, "Give access"));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const data = new FormData(form);
      try {
        await api("/documents/" + d.id + "/grants",
          { method: "POST", json: { email: data.get("email"), permission: data.get("permission") } });
        toast("Access given.", "ok");
        await render();
      } catch (err) { toast(friendly(err), "error"); }
    });
    dlg.replaceChildren(
      el("div", { class: "dialog-head" }, el("h3", {}, "Share document"),
        el("button", { class: "icon-btn", "aria-label": "Close", onclick: () => dlg.close() }, icon("x"))),
      el("p", { class: "muted" }, d.name), list, form);
  };
  try { await render(); dlg.showModal(); } catch (err) { toast(friendly(err), "error"); }
}

function docActions(d) {
  const acts = [iconBtn("download", "Download", () => download(d))];
  if (d.my_permission === "owner" || d.my_permission === "edit") {
    acts.push(iconBtn("refresh", "Replace file contents", () => replaceContent(d)));
    acts.push(iconBtn("pencil", "Edit name and category", () => editDetails(d)));
  }
  if (d.my_permission === "owner") {
    acts.push(iconBtn("userplus", "Share", () => openShare(d)));
    acts.push(iconBtn("trash", "Delete", () => remove(d), "danger"));
  }
  return acts;
}

function fileCell(d) {
  const ext = (d.name.split(".").pop() || "").toLowerCase();
  const kind = { pdf: "pdf", png: "img", jpg: "img", jpeg: "img", txt: "txt" }[ext] || "txt";
  return el("div", { class: "file-cell" },
    el("span", { class: "ft ft-" + kind }, ext.toUpperCase().slice(0, 4)),
    el("div", {}, el("div", { class: "file-name" }, d.name), d.category ? el("span", { class: "chip" }, d.category) : null));
}

const stat = (label, value) => el("div", { class: "stat" }, el("div", { class: "stat-label" }, label), el("div", { class: "stat-value" }, value));

async function renderDocuments(view) {
  const f = state.filters;
  const isOwner = state.me.role === "owner";
  const hasFilters = Object.keys(f).length > 0;
  if (isOwner) {
    $("page-actions").replaceChildren(el("button", { class: "btn", onclick: () => show("upload") }, icon("upload"), "Upload"));
  }
  const form = el("form", { class: "toolbar" },
    el("label", { class: "search" }, icon("search"),
      el("input", { name: "q", type: "search", placeholder: "Search by name", value: f.q || "", "aria-label": "Search by name" })),
    el("details", { class: "more", open: f.owner || f.category || f.created_from || f.created_to ? "open" : false },
      el("summary", { class: "btn ghost" }, "Filters"),
      el("div", { class: "more-body" },
        field("owner", "Owner email", "text", f.owner), field("category", "Category", "text", f.category),
        field("created_from", "Added from", "date", f.created_from), field("created_to", "Added to", "date", f.created_to))),
    el("button", { class: "btn", type: "submit" }, "Search"),
    hasFilters ? el("button", { type: "button", class: "btn ghost", onclick: () => { state.filters = {}; show("documents"); } }, "Clear") : null);
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    state.filters = Object.fromEntries([...new FormData(form).entries()].filter(([, v]) => v));
    show("documents");
  });

  const docs = await api("/documents" + qs(state.filters));
  const mine = docs.filter((d) => d.my_permission === "owner").length;
  const stats = el("div", { class: "stats" },
    stat(hasFilters ? "Matching" : "Documents", docs.length),
    isOwner ? stat("Yours", mine) : null,
    stat("Shared with you", docs.length - mine));
  const body = docs.length
    ? table(["Document", "Owner", "Your access", "Size", "Added", ""], docs.map((d) => el("tr", {},
        el("td", {}, fileCell(d)),
        el("td", {}, d.owner_id === state.me.id ? person(state.me.email, "You") : person(d.owner_email || "unknown")),
        el("td", {}, pill(d.my_permission)),
        el("td", {}, size(d.size)),
        el("td", { title: full(d.created_at) }, ago(d.created_at)),
        el("td", { class: "actions" }, docActions(d)))))
    : emptyState("files", hasFilters ? "No documents match" : "No documents yet",
        hasFilters ? "Try different filters." : isOwner ? "Upload your first document to get started." : "Nothing has been shared with you yet.",
        isOwner && !hasFilters ? el("button", { class: "btn", onclick: () => show("upload") }, icon("upload"), "Upload a document") : null);
  view.replaceChildren(stats, form, body);
}

async function renderUpload(view) {
  const input = el("input", { type: "file", name: "file", accept: ".pdf,.png,.jpg,.jpeg,.txt", class: "sr-only" });
  const picked = el("div", { class: "picked muted" }, "No file selected");
  const showPicked = () => {
    const file = input.files[0];
    picked.textContent = file ? file.name + " (" + size(file.size) + ")" : "No file selected";
  };
  const zone = el("label", { class: "dropzone" }, icon("upload"),
    el("strong", {}, "Drop a file here or click to browse"),
    el("span", { class: "muted small" }, "PDF, PNG, JPG or TXT, up to 5 MB"), input);
  ["dragenter", "dragover"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add("over"); }));
  ["dragleave", "drop"].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove("over"); }));
  zone.addEventListener("drop", (e) => {
    if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; showPicked(); }
  });
  input.addEventListener("change", showPicked);

  const submit = el("button", { type: "submit", class: "btn" }, "Upload document");
  const form = el("form", { class: "card upload" }, zone, picked, field("category", "Category (optional)"), submit);
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const file = input.files[0];
    if (!file) return toast("Choose a file first.", "error");
    if (file.size > 5 * 1024 * 1024) return toast("That file is larger than 5 MB.", "error");
    const category = new FormData(form).get("category");
    const data = new FormData();
    data.append("file", file);
    busy(submit, true);
    try {
      await api("/documents" + qs(category ? { category } : {}), { method: "POST", form: data });
      show("documents", "Uploaded.");
    } catch (err) {
      busy(submit, false, "Upload document");
      toast(friendly(err), "error");
    }
  });
  view.replaceChildren(form);
}

/* ---------- activity (admin) ---------- */

const ACTIONS = {
  login: ["Signed in", "lock"],
  login_locked: ["Sign-in blocked", "alert"],
  upload: ["Uploaded", "upload"],
  download: ["Downloaded", "download"],
  view: ["Viewed details", "eye"],
  update: ["Edited details", "pencil"],
  replace: ["Replaced contents", "refresh"],
  delete: ["Deleted", "trash"],
  grant: ["Gave access", "userplus"],
  revoke: ["Took back access", "x"],
  list_grants: ["Viewed who has access", "users"],
  deactivate_user: ["Disabled account", "x"],
  activate_user: ["Enabled account", "check"],
};

const CATEGORIES = [
  ["all", "All", () => true],
  ["denied", "Refused", (r) => r.outcome === "denied"],
  ["documents", "Documents", (r) => ["upload", "download", "view", "update", "replace", "delete", "list_grants"].includes(r.action)],
  ["permissions", "Permission changes", (r) => ["grant", "revoke", "deactivate_user", "activate_user"].includes(r.action)],
  ["signins", "Sign-ins", (r) => r.action === "login" || r.action === "login_locked"],
];

const act = { rows: [], cat: "all", q: "", action: "", shown: [] };

function actionLabel(r) {
  if (r.action === "login" && r.outcome === "denied") return "Failed sign-in";
  return (ACTIONS[r.action] || [r.action])[0];
}
const actionIcon = (r) => (ACTIONS[r.action] || [null, "activity"])[1];

function dayLabel(iso) {
  const d = new Date(iso);
  const start = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((start(new Date()) - start(d)) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long", year: "numeric" });
}

function matchesText(r) {
  if (act.action && r.action !== act.action) return false;
  const q = act.q.trim().toLowerCase();
  if (!q) return true;
  const hay = [r.actor, r.target, r.action, actionLabel(r),
    r.document_id ? "#" + r.document_id : "", r.detail && r.detail.name].join(" ").toLowerCase();
  return hay.includes(q);
}

function openEvent(r) {
  const dlg = $("dialog");
  const row = (k, v) => [el("dt", {}, k), el("dd", {}, v)];
  dlg.replaceChildren(
    el("div", { class: "dialog-head" }, el("h3", {}, "Event #" + r.id),
      el("button", { class: "icon-btn", "aria-label": "Close", onclick: () => dlg.close() }, icon("x"))),
    el("dl", { class: "kv" },
      ...row("When", full(r.time)),
      ...row("Who", r.actor || "Unknown or not signed in"),
      ...row("Action", actionLabel(r) + " (" + r.action + ")"),
      ...row("Result", pill(r.outcome === "denied" ? "refused" : "allowed", r.outcome)),
      ...row("Document", r.document_id ? "#" + r.document_id : "None"),
      ...row("Target person", r.target || "None"),
      ...row("Details", r.detail ? el("pre", { class: "detail" }, JSON.stringify(r.detail, null, 2)) : "None")));
  dlg.showModal();
}

function eventRow(r) {
  const open = () => openEvent(r);
  const tr = el("tr", { class: "event" + (r.outcome === "denied" ? " refused" : ""), tabindex: "0", onclick: open },
    el("td", { title: full(r.time) }, new Date(r.time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })),
    el("td", {}, r.actor ? person(r.actor) : el("span", { class: "muted" }, "Not signed in")),
    el("td", {}, el("div", { class: "act" }, icon(actionIcon(r)), actionLabel(r))),
    el("td", {}, pill(r.outcome === "denied" ? "refused" : "allowed", r.outcome)),
    el("td", {}, r.document_id ? el("span", { class: "chip" }, "#" + r.document_id) : "-",
      r.detail && r.detail.name ? " " + r.detail.name : ""),
    el("td", {}, r.target || "-"));
  tr.addEventListener("keydown", (e) => { if (e.key === "Enter") open(); });
  return tr;
}

/* A cell starting with = + - or @ could run as a formula in a spreadsheet, so it is defused. */
function csvCell(v) {
  let s = v === null || v === undefined ? "" : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return '"' + s.replaceAll('"', '""') + '"';
}

function exportCsv(rows) {
  const head = ["id", "time", "actor", "action", "result", "document_id", "target", "detail"];
  const lines = [head.join(",")].concat(rows.map((r) =>
    [r.id, r.time, r.actor, r.action, r.outcome, r.document_id, r.target, r.detail ? JSON.stringify(r.detail) : ""]
      .map(csvCell).join(",")));
  const url = URL.createObjectURL(new Blob([lines.join("\r\n")], { type: "text/csv" }));
  const link = el("a", { href: url, download: "trustvault-activity.csv" });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function paintActivity(parts) {
  const { statsBox, catsBox, bodyBox } = parts;
  const rows = act.rows;
  const refused = rows.filter((r) => r.outcome === "denied").length;
  const downloads = rows.filter((r) => r.action === "download" && r.outcome === "allowed").length;
  const people = new Set(rows.map((r) => r.actor).filter(Boolean)).size;
  const card = (label, value, hint, warn) => el("div", { class: "stat" + (warn ? " warn" : "") },
    el("div", { class: "stat-label" }, label), el("div", { class: "stat-value" }, value),
    hint ? el("div", { class: "stat-hint" }, hint) : null);
  statsBox.replaceChildren(
    card("Events", rows.length, rows.length >= 500 ? "Newest 500 shown" : "In the audit log"),
    card("Refused", refused, rows.length ? Math.round((refused / rows.length) * 100) + "% of events" : "", refused > 0),
    card("Downloads", downloads, "Files opened"),
    card("People", people, "Active accounts"));

  const base = rows.filter(matchesText);
  catsBox.replaceChildren(...CATEGORIES.map(([key, label, test]) =>
    el("button", { class: "seg-btn" + (act.cat === key ? " on" : ""),
        onclick: () => { act.cat = key; paintActivity(parts); } },
      label, el("span", { class: "count" }, base.filter(test).length))));

  const test = CATEGORIES.find(([key]) => key === act.cat)[2];
  act.shown = base.filter(test);
  if (!act.shown.length) {
    bodyBox.replaceChildren(emptyState("activity", "No events match", "Try another category or clear the search."));
    return;
  }
  let lastDay = "";
  const trs = [];
  for (const r of act.shown) {
    const day = dayLabel(r.time);
    if (day !== lastDay) {
      trs.push(el("tr", { class: "day-row" }, el("td", { colspan: "6" }, day)));
      lastDay = day;
    }
    trs.push(eventRow(r));
  }
  bodyBox.replaceChildren(
    table(["Time", "Who", "Action", "Result", "Document", "Target"], trs),
    el("p", { class: "muted small note" }, "Select a row for the full details of an event."));
}

async function renderActivity(view) {
  act.rows = await api("/admin/audit?limit=500");
  const parts = { statsBox: el("div", { class: "stats" }), catsBox: el("div", { class: "seg" }), bodyBox: el("div", {}) };
  const search = el("input", { type: "search", value: act.q, "aria-label": "Search activity",
    placeholder: "Search by person, action or #document" });
  search.addEventListener("input", () => { act.q = search.value; paintActivity(parts); });
  const select = el("select", { "aria-label": "Filter by action" },
    el("option", { value: "" }, "All actions"),
    ...Object.entries(ACTIONS).map(([key, [label]]) =>
      el("option", { value: key, selected: key === act.action ? "selected" : false }, label)));
  select.addEventListener("change", () => { act.action = select.value; paintActivity(parts); });
  $("page-actions").replaceChildren(
    el("button", { class: "btn ghost", onclick: () => show("activity") }, icon("refresh"), "Refresh"),
    el("button", { class: "btn ghost", onclick: () => exportCsv(act.shown) }, icon("download"), "Export CSV"));
  view.replaceChildren(parts.statsBox, parts.catsBox,
    el("div", { class: "toolbar" }, el("label", { class: "search" }, icon("search"), search), select),
    parts.bodyBox);
  paintActivity(parts);
}

/* ---------- alerts, users, integrity (admin) ---------- */

async function renderAlerts(view) {
  const list = await api("/admin/alerts");
  state.alerts = list.length;
  renderNav();
  view.replaceChildren(list.length
    ? el("div", { class: "alerts" }, list.map((a) => el("div", { class: "alert-card" }, icon("alert"),
        el("div", {}, el("strong", {}, a.kind.replaceAll("_", " ")),
          el("div", { class: "muted" }, (a.actor || "unknown account") + ": " + a.count + " in the last " + a.window)))))
    : emptyState("shieldcheck", "All quiet", "Nothing unusual in recent activity."));
}

async function toggleUser(u) {
  if (u.is_active && !(await ask("Disable account", u.email + " will be signed out and refused on their next request.", "Disable account", true))) return;
  try {
    await api("/admin/users/" + u.id + "/" + (u.is_active ? "deactivate" : "activate"), { method: "POST" });
    show("users", u.is_active ? "Account disabled." : "Account enabled.");
  } catch (err) { toast(friendly(err), "error"); }
}

async function renderUsers(view) {
  const users = await api("/admin/users");
  view.replaceChildren(table(["User", "Role", "Status", ""], users.map((u) => el("tr", {},
    el("td", {}, person(u.email)), el("td", {}, pill(u.role)),
    el("td", {}, pill(u.is_active ? "active" : "disabled")),
    el("td", { class: "actions" }, u.id === state.me.id ? "" :
      el("button", { class: "btn sm " + (u.is_active ? "danger" : "ghost"), onclick: () => toggleUser(u) },
        u.is_active ? "Disable account" : "Enable account"))))));
}

async function renderIntegrity(view) {
  const card = el("div", { class: "card integrity" });
  const run = async () => {
    card.className = "card integrity";
    card.replaceChildren(el("span", { class: "spinner big" }), el("p", { class: "muted" }, "Checking every entry"));
    try {
      const r = await api("/admin/audit/verify");
      card.className = "card integrity " + (r.ok ? "good" : "bad");
      card.replaceChildren(
        el("div", { class: "big-icon" }, icon(r.ok ? "shieldcheck" : "alert")),
        el("h2", {}, r.ok ? "Audit log is intact" : "Tampering detected"),
        el("p", { class: "muted" }, r.ok
          ? "All " + r.checked + " entries match their hashes and chain together."
          : "Entry " + r.first_bad_id + " does not match. " + r.checked + " earlier entries were fine."),
        r.ok && r.head ? el("code", { class: "hash" }, "Latest hash " + r.head.slice(0, 24)) : null,
        el("button", { class: "btn ghost", onclick: run }, "Check again"));
    } catch (err) { if (err.message !== "unauthorized") toast(friendly(err), "error"); }
  };
  view.replaceChildren(card, el("p", { class: "muted note" },
    "Every entry stores a hash of the entry before it. Editing or removing any past entry breaks the chain, and this check shows where."));
  run();
}


/* ---------- document catalogue ---------- */

async function renderCatalogue(view) {
  const search = el("input", {
    type: "search",
    placeholder: "Search documents...",
    "aria-label": "Search documents"
  });
  const category = el("input", {
    type: "text",
    placeholder: "Filter by category",
    "aria-label": "Filter by category"
  });
  const results = el("div", {});
  const status = el("p", { class: "muted small" }, "");

  async function load() {
    results.replaceChildren(el("p", { class: "muted" }, "Loading documents..."));
    try {
      const params = new URLSearchParams();
      if (search.value.trim()) params.set("q", search.value.trim());
      if (category.value.trim()) params.set("category", category.value.trim());

      const docs = await api("/documents/catalogue?" + params.toString());
      const items = Array.isArray(docs) ? docs : (docs.items || []);
      status.textContent = items.length + " document(s) found";

      if (!items.length) {
        results.replaceChildren(
          emptyState("search", "No documents found", "Try another search or category.")
        );
        return;
      }

      results.replaceChildren(table(
        ["Document", "Category", "Owner", "Permission", "Request access"],
        items.map((d) => {
          const name = d.name || d.title || d.filename || ("Document #" + d.id);
          const permission = d.my_permission || "none";
          const canRequest = d.can_request_access === true;

          return el("tr", {},
            el("td", {}, name),
            el("td", {}, d.category || "-"),
            el("td", {}, d.owner_email || "-"),
            el("td", {}, pill(permission.replaceAll("_", " "))),
            el("td", { class: "actions" },
              canRequest
                ? el("div", { class: "actions" },
                    el("button", {
                      class: "btn sm",
                      onclick: () => requestAccess(d.id, "read")
                    }, "Request read"),
                    el("button", {
                      class: "btn sm ghost",
                      onclick: () => requestAccess(d.id, "edit")
                    }, "Request edit"))
                : el("span", { class: "muted small" },
                    permission === "owner" ? "Your document" :
                    permission === "edit" ? "Already has edit access" :
                    permission === "read" ? "Already has read access" :
                    "Unavailable"))
          );
        })
      ));
    } catch (err) {
      results.replaceChildren(
        emptyState("alert", "Catalogue unavailable", friendly(err))
      );
    }
  }

  async function requestAccess(docId, permission) {
    if (!(await ask(
      "Request " + permission + " access",
      "Send a request for " + permission + " access to document #" + docId + "?",
      "Send request"
    ))) return;

    try {
      await api("/documents/" + docId + "/access-requests", {
        method: "POST",
        json: { permission }
      });
      toast("Access request submitted.", "success");
      await load();
    } catch (err) {
      toast(friendly(err), "error");
    }
  }

  const searchButton = el("button", {
    class: "btn",
    onclick: load
  }, "Search");

  search.addEventListener("keydown", (e) => {
    if (e.key === "Enter") load();
  });
  category.addEventListener("keydown", (e) => {
    if (e.key === "Enter") load();
  });

  $("page-actions").replaceChildren(
    el("button", {
      class: "btn ghost",
      onclick: () => show("myRequests")
    }, "My Requests")
  );

  view.replaceChildren(
    el("div", { class: "toolbar" },
      el("label", { class: "search" }, icon("search"), search),
      category,
      searchButton
    ),
    status,
    results
  );

  await load();
}

/* ---------- my access requests ---------- */

async function renderMyRequests(view) {
  const items = await api("/access-requests/mine");

  if (!items.length) {
    view.replaceChildren(
      emptyState("clock", "No access requests yet",
        "Find documents in the catalogue and request access.")
    );
    return;
  }

  view.replaceChildren(table(
    ["Request", "Document", "Permission", "Status", "Submitted", "Decision"],
    items.map((r) => el("tr", {},
      el("td", {}, "#" + r.id),
      el("td", {}, "#" + r.document_id),
      el("td", {}, r.permission),
      el("td", {}, pill(r.status)),
      el("td", {}, r.created_at
        ? new Date(r.created_at).toLocaleString()
        : "-"),
      el("td", {}, r.decided_at
        ? new Date(r.decided_at).toLocaleString()
        : "-")
    ))
  ));

  $("page-actions").replaceChildren(
    el("button", {
      class: "btn ghost",
      onclick: () => show("catalogue")
    }, "Browse Catalogue")
  );
}

/* ---------- incoming requests for owned documents ---------- */

async function renderIncomingRequests(view) {
  const docs = await api("/documents");
  const owned = (Array.isArray(docs) ? docs : (docs.items || []))
    .filter((d) => d.owner_id === state.me.id);

  const results = await Promise.all(
    owned.map(async (d) => {
      try {
        const requests = await api("/documents/" + d.id + "/access-requests");
        return requests.map((r) => ({
          ...r,
          document_name: d.name || d.title || d.filename || ("Document #" + d.id)
        }));
      } catch (err) {
        console.error("Could not load requests for document", d.id, err);
        return [];
      }
    })
  );

  const items = results.flat();

  if (!items.length) {
    view.replaceChildren(
      emptyState("users", "No incoming requests",
        "Requests for your documents will appear here.")
    );
    return;
  }

  view.replaceChildren(table(
    ["Document", "Requester ID", "Permission", "Status", "Submitted", "Actions"],
    items.map((r) => el("tr", {},
      el("td", {}, r.document_name),
      el("td", {}, "#" + r.requester_id),
      el("td", {}, r.permission),
      el("td", {}, pill(r.status)),
      el("td", {}, r.created_at
        ? new Date(r.created_at).toLocaleString()
        : "-"),
      el("td", { class: "actions" },
        r.status === "pending"
          ? el("div", { class: "actions" },
              el("button", {
                class: "btn sm",
                onclick: () => decideRequest(r.id, "approve")
              }, "Approve"),
              el("button", {
                class: "btn sm danger",
                onclick: () => decideRequest(r.id, "reject")
              }, "Reject"))
          : "-")
    ))
  ));
}

async function decideRequest(requestId, decision) {
  const confirmed = await ask(
    decision === "approve" ? "Approve access" : "Reject access",
    "Are you sure you want to " + decision + " this request?",
    decision === "approve" ? "Approve" : "Reject",
    decision === "reject"
  );

  if (!confirmed) return;

  try {
    await api("/access-requests/" + requestId + "/decision", {
      method: "POST",
      json: { decision }
    });
    toast("Request " + decision + "d.", "success");
    show("incomingRequests");
  } catch (err) {
    toast(friendly(err), "error");
  }
}

const VIEWS = {
  documents: renderDocuments,
  catalogue: renderCatalogue,
  upload: renderUpload,
  myRequests: renderMyRequests,
  incomingRequests: renderIncomingRequests,
  activity: renderActivity,
  alerts: renderAlerts,
  users: renderUsers,
  integrity: renderIntegrity,
};

/* ---------- start-up ---------- */

document.querySelectorAll("[data-icon]").forEach((node) => node.prepend(icon(node.dataset.icon)));
$("pw-toggle").append(icon("eye"));
$("pw-toggle").addEventListener("click", () => {
  const input = $("password");
  const reveal = input.type === "password";
  input.type = reveal ? "text" : "password";
  $("pw-toggle").setAttribute("aria-label", reveal ? "Hide password" : "Show password");
});
$("demo-chips").replaceChildren(...DEMO.map(([label, email]) =>
  el("button", { type: "button", class: "chip", title: email, onclick: () => { $("email").value = email; $("password").focus(); } }, label)));

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = $("login-btn");
  $("login-msg").textContent = "";
  if (!$("email").value || !$("password").value) {
    $("login-msg").textContent = "Enter your email and password.";
    return;
  }
  busy(btn, true);
  try {
    const data = await api("/auth/login", { method: "POST", json: { email: $("email").value, password: $("password").value } });
    state.token = data.access_token;
    sessionStorage.setItem("tv_token", state.token);
    $("password").value = "";
    await start();
  } catch (err) {
    $("login-msg").textContent = friendly(err);
  }
  busy(btn, false, "Sign in");
});

if (state.token) start();