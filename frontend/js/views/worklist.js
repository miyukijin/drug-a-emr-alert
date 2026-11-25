import { api } from "../api.js";
import { h, pct, titleCase, tierTag, likelihoodBar, errorBox } from "../dom.js";

export async function worklist(root, nav) {
  const state = { alerts_only: "true", tier: "", min_age: "", q: "", sort: "likelihood_asc", page: 1, page_size: 20 };
  const results = h("div");
  const kpis = h("div", { class: "grid g4", style: "margin-bottom:16px" });

  const field = (label, control) => h("label", { class: "f" }, label, control);
  const controls = {};
  const sel = (key, opts) => (controls[key] =
    h("select", { onchange: (e) => { state[key] = e.target.value; reconcile(key); state.page = 1; load(); } },
      opts.map(([v, t]) => h("option", { value: v, selected: String(state[key]) === v }, t))));
  // Alerts fire only when P(treated) < threshold, i.e. tier LOW, so MEDIUM/HIGH never coexist with "Alerts only".
  const reconcile = (changed) => {
    const nonAlertTier = state.tier === "MEDIUM" || state.tier === "HIGH";
    if (!nonAlertTier || state.alerts_only !== "true") return;
    if (changed === "tier") { state.alerts_only = ""; controls.alerts_only.value = ""; }
    else { state.tier = ""; controls.tier.value = ""; }
  };
  const search = h("input", { type: "search", placeholder: "Patient ID...", "aria-label": "Patient ID prefix",
    oninput: debounce((e) => { state.q = e.target.value; state.page = 1; load(); }) });

  root.replaceChildren(
    h("h1", {}, "Alert worklist"),
    h("p", { class: "sub" }, "Eligible Disease X patients who are unlikely to receive Drug A, lowest treatment likelihood first. Open a patient to see why."),
    kpis,
    h("div", { class: "card" },
      h("div", { class: "toolbar" },
        field("Show", sel("alerts_only", [["true", "Alerts only"], ["", "All patients"]])),
        field("Likelihood tier", sel("tier", [["", "Any"], ["LOW", "Low"], ["MEDIUM", "Medium"], ["HIGH", "High"]])),
        field("Min age", sel("min_age", [["", "Any"], ["40", "40+"], ["65", "65+"]])),
        field("Sort", sel("sort", [["likelihood_asc", "Lowest likelihood"], ["likelihood_desc", "Highest likelihood"], ["age_desc", "Oldest first"], ["id_asc", "Patient ID"]])),
        field("Search", search)),
      h("p", { class: "note" }, "Alerts are always Low tier (P(treated) below the alert threshold). Choosing Medium or High switches the view to All patients."),
      results));

  async function load() {
    results.replaceChildren(h("div", { class: "loading" }, "Loading..."));
    try {
      const params = Object.fromEntries(Object.entries(state).filter(([, v]) => v !== ""));
      params.alerts_only = state.alerts_only === "true";
      const data = await api.patients(params);
      if (!data.items.length) { results.replaceChildren(h("div", { class: "empty" }, "No patients match these filters.")); return; }
      const pages = Math.ceil(data.total / data.page_size);
      results.replaceChildren(
        h("table", {},
          h("thead", {}, h("tr", {}, ["Patient", "Diagnosed", "Age / sex", "Conditions", "Diagnosed by", "Setting", "P(treated)", "Tier", "Alert"].map((t) => h("th", {}, t)))),
          h("tbody", {}, data.items.map((p) => h("tr", { class: "row", tabindex: 0, onclick: () => nav("lookup", p.patient_id),
            onkeydown: (e) => e.key === "Enter" && nav("lookup", p.patient_id) },
            h("td", {}, `#${p.patient_id}`), h("td", {}, p.diagnosis_date), h("td", {}, `${p.patient_age} / ${p.patient_gender}`),
            h("td", {}, p.num_conditions), h("td", {}, titleCase(p.physician_type)), h("td", {}, titleCase(p.location_type)),
            h("td", {}, h("div", { style: "display:flex;gap:8px;align-items:center" }, pct(p.likelihood_treated), likelihoodBar(p.likelihood_treated))),
            h("td", {}, tierTag(p.tier)),
            h("td", {}, p.alert ? h("span", { class: "tag LOW" }, "ALERT") : h("span", { class: "tag na" }, p.eligible ? "-" : "Not eligible")))))),
        h("div", { class: "pager" },
          `${data.total.toLocaleString()} patients`,
          h("button", { class: "btn ghost", disabled: state.page <= 1, onclick: () => { state.page--; load(); } }, "Previous"),
          `Page ${state.page} / ${pages}`,
          h("button", { class: "btn ghost", disabled: state.page >= pages, onclick: () => { state.page++; load(); } }, "Next")));
    } catch (e) {
      results.replaceChildren(errorBox(e));
    }
  }

  async function renderKpis() {
    try {
      const [all, alerts, model] = await Promise.all([api.patients({ page_size: 1 }), api.patients({ alerts_only: true, page_size: 1 }), api.model()]);
      const card = (n, l) => h("div", { class: "card kpi" }, h("div", { class: "n" }, n), h("div", { class: "l" }, l));
      kpis.replaceChildren(card(all.total.toLocaleString(), "Disease X patients in sample"), card(alerts.total.toLocaleString(), "Active alerts"),
        card(pct(alerts.total / all.total, 0), "Share of patients alerted"), card(`< ${pct(model.alert_threshold, 0)}`, "Alert threshold (P treated)"));
    } catch (e) { kpis.replaceChildren(); }
  }
  renderKpis();
  load();
}

function debounce(fn, ms = 300) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
