import { api } from "./api.js";
import { h } from "./dom.js";
import { worklist } from "./views/worklist.js";
import { lookup } from "./views/lookup.js";
import { scorer } from "./views/scorer.js";
import { about } from "./views/about.js";

const views = { worklist, lookup, scorer, about };
const root = document.getElementById("view");
const tabs = document.querySelectorAll("#tabs button");

function nav(view, arg) {
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.view === view));
  location.hash = arg ? `${view}/${arg}` : view;
}

function render() {
  const [view, arg] = (location.hash.slice(1) || "worklist").split("/");
  const fn = views[view] || worklist;
  tabs.forEach((t) => t.classList.toggle("active", t.dataset.view === (views[view] ? view : "worklist")));
  fn(root, nav, arg);
}

tabs.forEach((t) => t.addEventListener("click", () => nav(t.dataset.view)));
window.addEventListener("hashchange", render);

async function pollHealth() {
  const el = document.getElementById("status");
  try {
    const hl = await api.health();
    el.textContent = hl.status === "ok" ? "API online" : "API degraded";
    el.className = `status ${hl.status === "ok" ? "ok" : "bad"}`;
  } catch {
    el.textContent = "API offline";
    el.className = "status bad";
  }
}
pollHealth();
setInterval(pollHealth, 30000);
render();
