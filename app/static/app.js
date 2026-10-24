"use strict";

const state = { token: sessionStorage.getItem("tv_token"), me: null, tab: null, filters: {}, auditFilters: {} };
const $ = (id) => document.getElementById(id);

const TABS = {
  owner: [["documents", "My documents"], ["upload", "Upload"]],
  viewer: [["documents", "Shared with me"]],
  admin: [["activity", "Activity"], ["alerts", "Alerts"], ["users", "Users"], ["integrity", "Integrity"]],
};

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
const when = (iso) => new Date(iso).toLocaleString();
const pill = (text, kind) => el("span", { class: "pill " + (kind || text) }, text);

function say(text, kind) {
  const box = $("msg");
  box.textContent = text || "";
  box.className = "msg " + (kind || "");
}

function friendly(err) {
  return err.status === 404 && err.message === "Not found" ? "Not found, or you do not have access." : err.message;
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

/* ---------- sign in / out ---------- */

function signOut(message) {
  state.token = null;
  state.me = null;
  sessionStorage.removeItem("tv_token");
  $("app").classList.add("hidden");
  $("who").classList.add("hidden");
  $("login").classList.remove("hidden");
  $("login-msg").textContent = message || "";
}

function renderWho() {
  const box = $("who");
  box.classList.remove("hidden");
  box.replaceChildren(pill(state.me.role), el("span", {}, state.me.email),
    el("button", {
      class: "small ghost",
      onclick: async () => {
        try { await api("/auth/logout", { method: "POST" }); } catch (_) { /* already signed out */ }
        signOut("");
      },
    }, "Sign out"));
}

function renderTabs() {
  $("tabs").replaceChildren(...TABS[state.me.role].map(([key, label]) =>
    el("button", { class: "tab" + (key === state.tab ? " active" : ""), onclick: () => show(key) }, label)));
}

async function start() {
  try { state.me = await api("/me"); } catch (_) { return; }
  $("login").classList.add("hidden");
  $("app").classList.remove("hidden");
  renderWho();
  show(TABS[state.me.role][0][0]);
}

async function show(tab, note) {
  state.tab = tab;
  say(note || "", note ? "ok" : "");
  renderTabs();
  const view = $("view");
  view.replaceChildren(el("p", { class: "muted" }, "Loading"));
  try {
    await VIEWS[tab](view);
  } catch (err) {
    if (err.message !== "unauthorized") say(friendly(err), "error");
    view.replaceChildren();
  }
}

/* ---------- documents ---------- */

function docActions(d) {
  const acts = [el("button", { class: "small", onclick: () => download(d) }, "Download")];
  if (d.my_permission === "owner" || d.my_permission === "edit")
    acts.push(el("button", { class: "small ghost", onclick: () => rename(d) }, "Rename"));
  if (d.my_permission === "owner") {
    acts.push(el("button", { class: "small ghost", onclick: () => share(d) }, "Share"));
    acts.push(el("button", { class: "small danger", onclick: () => remove(d) }, "Delete"));
  }
  return acts;
}

async function download(d) {
  try {
    const blob = await api("/documents/" + d.id + "/download", { blob: true });
    const url = URL.createObjectURL(blob);
    const link = el("a", { href: url, download: d.name });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (err) { say(friendly(err), "error"); }
}

async function rename(d) {
  const name = prompt("New name", d.name);
  if (!name || name === d.name) return;
  try {
    await api("/documents/" + d.id, { method: "PATCH", json: { name } });
    show("documents", "Renamed.");
  } catch (err) { say(friendly(err), "error"); }
}

async function remove(d) {
  if (!confirm("Delete " + d.name + "? Nobody will be able to open it.")) return;
  try {
    await api("/documents/" + d.id, { method: "DELETE" });
    show("documents", "Deleted.");
  } catch (err) { say(friendly(err), "error"); }
}

async function share(d) {
  const box = $("share");
  try {
    const grants = await api("/documents/" + d.id + "/grants");
    const list = grants.length
      ? table(["Person", "Access", "Since", ""], grants.map((g) => el("tr", {},
          el("td", {}, g.email), el("td", {}, pill(g.permission)), el("td", {}, when(g.granted_at)),
          el("td", {}, el("button", { class: "small danger", onclick: () => revoke(d, g) }, "Take back access")))))
      : el("p", { class: "empty" }, "Not shared with anyone yet.");
    const form = el("form", { class: "filters" },
      field("email", "Person's email", "email", "", true),
      el("label", {}, "Access", el("select", { name: "permission" },
        el("option", { value: "read" }, "Read only"), el("option", { value: "edit" }, "Read and edit"))),
      el("button", { type: "submit" }, "Give access"));
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const data = new FormData(form);
      try {
        await api("/documents/" + d.id + "/grants",
          { method: "POST", json: { email: data.get("email"), permission: data.get("permission") } });
        say("Access given.", "ok");
        share(d);
      } catch (err) { say(friendly(err), "error"); }
    });
    box.replaceChildren(el("h3", {}, "Sharing: " + d.name), list, form);
    box.scrollIntoView({ behavior: "smooth" });
  } catch (err) { say(friendly(err), "error"); }
}

async function revoke(d, g) {
  try {
    await api("/documents/" + d.id + "/grants/" + g.user_id, { method: "DELETE" });
    say("Access taken back. It stops working immediately.", "ok");
    share(d);
  } catch (err) { say(friendly(err), "error"); }
}

async function renderDocuments(view) {
  const f = state.filters;
  const form = el("form", { class: "filters" },
    field("q", "Name", "text", f.q), field("owner", "Owner email", "text", f.owner),
    field("category", "Category", "text", f.category),
    field("created_from", "From", "date", f.created_from), field("created_to", "To", "date", f.created_to),
    el("button", { type: "submit" }, "Search"),
    el("button", { type: "button", class: "ghost", onclick: () => { state.filters = {}; show("documents"); } }, "Clear"));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    state.filters = Object.fromEntries([...new FormData(form).entries()].filter(([, v]) => v));
    show("documents");
  });
  const docs = await api("/documents" + qs(state.filters));
  const body = docs.length
    ? table(["Name", "Category", "Owner", "Access", "Size", "Added", ""], docs.map((d) => el("tr", {},
        el("td", {}, d.name), el("td", {}, d.category || "-"),
        el("td", {}, d.owner_id === state.me.id ? "You" : d.owner_email || "-"),
        el("td", {}, pill(d.my_permission)), el("td", {}, size(d.size)), el("td", {}, when(d.created_at)),
        el("td", { class: "actions" }, docActions(d)))))
    : el("p", { class: "empty" }, "No documents found.");
  view.replaceChildren(form, body, el("div", { id: "share" }));
}

async function renderUpload(view) {
  const form = el("form", { class: "card" },
    el("h2", {}, "Upload a document"),
    el("label", {}, "File (PDF, PNG, JPG or TXT, up to 5 MB)",
      el("input", { type: "file", name: "file", required: "required", accept: ".pdf,.png,.jpg,.jpeg,.txt" })),
    field("category", "Category (optional)"),
    el("button", { type: "submit" }, "Upload"));
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = new FormData(form);
    const category = data.get("category");
    data.delete("category");
    try {
      await api("/documents" + qs(category ? { category } : {}), { method: "POST", form: data });
      show("documents", "Uploaded.");
    } catch (err) { say(friendly(err), "error"); }
  });
  view.replaceChildren(form);
}

/* ---------- admin ---------- */

function detailText(r) {
  if (!r.detail || r.action.startsWith("login")) return "-";
  const text = JSON.stringify(r.detail);
  return text.length > 80 ? text.slice(0, 80) + "..." : text;
}

async function renderActivity(view) {
  const f = state.auditFilters;
  const actions = ["", "login", "login_locked", "upload", "download", "view", "update", "delete",
    "grant", "revoke", "list_grants", "deactivate_user", "activate_user"];
  const choose = (name, label, options, current) => el("label", {}, label,
    el("select", { name }, options.map((o) =>
      el("option", { value: o, selected: o === (current || "") ? "selected" : false }, o || "any"))));
  const form = el("form", { class: "filters" },
    choose("action", "Action", actions, f.action),
    choose("outcome", "Result", ["", "allowed", "denied"], f.outcome),
    field("document_id", "Document id", "number", f.document_id),
    el("button", { type: "submit" }, "Filter"),
    el("button", { type: "button", class: "ghost", onclick: () => { state.auditFilters = { permissions: true }; show("activity"); } }, "Permission changes"),
    el("button", { type: "button", class: "ghost", onclick: () => { state.auditFilters = {}; show("activity"); } }, "All activity"));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    state.auditFilters = Object.fromEntries([...new FormData(form).entries()].filter(([, v]) => v));
    show("activity");
  });
  const { permissions, ...rest } = f;
  const rows = await api(permissions ? "/admin/permission-changes" : "/admin/audit" + qs(rest));
  const body = rows.length
    ? table(["When", "Who", "Action", "Result", "Document", "Target", "Details"], rows.map((r) => el("tr", {},
        el("td", {}, when(r.time)), el("td", {}, r.actor || "unknown"), el("td", {}, r.action),
        el("td", {}, pill(r.outcome)), el("td", {}, r.document_id || "-"), el("td", {}, r.target || "-"),
        el("td", {}, detailText(r)))))
    : el("p", { class: "empty" }, "No activity matches.");
  view.replaceChildren(el("h2", {}, permissions ? "Permission changes" : "Activity"), form, body);
}

async function renderAlerts(view) {
  const list = await api("/admin/alerts");
  view.replaceChildren(el("h2", {}, "Alerts"),
    list.length
      ? table(["What", "Who", "Count", "Window"], list.map((a) => el("tr", {},
          el("td", {}, a.kind.replaceAll("_", " ")), el("td", {}, a.actor || "unknown"),
          el("td", {}, a.count), el("td", {}, a.window))))
      : el("p", { class: "empty" }, "Nothing unusual in recent activity."));
}

async function toggleUser(u) {
  if (u.is_active && !confirm("Disable " + u.email + "? Their sessions stop working immediately.")) return;
  try {
    await api("/admin/users/" + u.id + "/" + (u.is_active ? "deactivate" : "activate"), { method: "POST" });
    show("users", u.is_active ? "Account disabled." : "Account enabled.");
  } catch (err) { say(friendly(err), "error"); }
}

async function renderUsers(view) {
  const users = await api("/admin/users");
  view.replaceChildren(el("h2", {}, "Users"),
    table(["Email", "Role", "Status", ""], users.map((u) => el("tr", {},
      el("td", {}, u.email), el("td", {}, pill(u.role)),
      el("td", {}, pill(u.is_active ? "active" : "disabled")),
      el("td", {}, u.id === state.me.id ? "" :
        el("button", { class: "small " + (u.is_active ? "danger" : "ghost"), onclick: () => toggleUser(u) },
          u.is_active ? "Disable account" : "Enable account"))))));
}

async function renderIntegrity(view) {
  const out = el("div", {});
  const check = async () => {
    try {
      const r = await api("/admin/audit/verify");
      out.replaceChildren(el("p", { class: r.ok ? "ok" : "error" }, r.ok
        ? "Intact: " + r.checked + " entries verified. Latest hash: " + (r.head ? r.head.slice(0, 16) : "none")
        : "Tampering detected near entry " + r.first_bad_id + " (" + r.checked + " entries were fine before it)."));
    } catch (err) { say(friendly(err), "error"); }
  };
  view.replaceChildren(el("h2", {}, "Audit log integrity"),
    el("p", { class: "muted" }, "Every entry is chained to the one before it with a hash. If a past entry is edited or removed, this check fails."),
    el("button", { onclick: check }, "Verify now"), out);
}

const VIEWS = {
  documents: renderDocuments, upload: renderUpload,
  activity: renderActivity, alerts: renderAlerts, users: renderUsers, integrity: renderIntegrity,
};

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  $("login-msg").textContent = "";
  try {
    const data = await api("/auth/login", { method: "POST", json: { email: $("email").value, password: $("password").value } });
    state.token = data.access_token;
    sessionStorage.setItem("tv_token", state.token);
    $("password").value = "";
    await start();
  } catch (err) { $("login-msg").textContent = friendly(err); }
});

if (state.token) start();