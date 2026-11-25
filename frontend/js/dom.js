export function h(tag, attrs = {}, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return el;
}

export const pct = (p, d = 1) => `${(p * 100).toFixed(d)}%`;
export const titleCase = (s) => String(s).toLowerCase().replace(/(^|[\s/(-])\w/g, (m) => m.toUpperCase());
export const tierTag = (t) => h("span", { class: `tag ${t}` }, { LOW: "Low", MEDIUM: "Medium", HIGH: "High" }[t] || t);
export const likelihoodBar = (p) => h("div", { class: "bar", title: pct(p) }, h("i", { style: `width:${Math.max(2, p * 100)}%` }));
export const errorBox = (e) =>
  h("div", { class: "err", role: "alert" }, e.message, e.requestId ? h("div", { class: "note" }, `request id: ${e.requestId}`) : null);
