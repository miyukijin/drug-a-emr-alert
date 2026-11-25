import { h, pct, tierTag } from "../dom.js";

export function predictionPanel(pred) {
  const status = !pred.eligible ? "na" : pred.alert ? "on" : "off";
  const title = !pred.eligible ? "Not eligible for Drug A alert" : pred.alert ? "Alert: eligible but unlikely to be treated" : "No alert: treatment likelihood is adequate";
  const icon = !pred.eligible ? "i" : pred.alert ? "!" : "OK";
  return h("div", { class: "grid" },
    h("div", { class: `alert ${status}` }, h("div", { class: "ic" }, icon), h("div", {}, h("h3", {}, title),
      h("div", { class: "muted" }, pred.eligible ? `Eligible: ${pred.eligibility_reasons.join("; ")}` : pred.eligibility_reasons.join("; ")))),
    h("div", { class: "card" },
      h("div", { style: "display:flex;gap:28px;align-items:center;flex-wrap:wrap" },
        h("div", {}, h("div", { class: "muted" }, "Likelihood of receiving Drug A"), h("div", { class: "big" }, pct(pred.likelihood_treated, 1))),
        h("div", {}, h("div", { class: "muted" }, "Tier"), tierTag(pred.tier)),
        h("div", {}, h("div", { class: "muted" }, "Alert threshold"), `< ${pct(pred.alert_threshold, 0)}`)),
      pred.unseen_categories.length ? h("div", { class: "note" }, `Values not seen in training (treated as 'other'): ${pred.unseen_categories.join(", ")}`) : null),
    h("div", { class: "card" }, h("strong", {}, "What drives this score"),
      h("div", { class: "note" }, "Change in likelihood vs. a typical patient, percentage points."),
      pred.drivers.length ? pred.drivers.map(driverRow) : h("div", { class: "muted" }, "No single feature moves the score materially.")));
}

function driverRow(d) {
  const w = Math.min(50, Math.abs(d.effect) * 1.4);
  const style = d.direction === "raises" ? `left:50%;width:${w}%` : `left:${50 - w}%;width:${w}%`;
  return h("div", { class: `driver ${d.direction}` },
    h("div", { style: "width:230px" }, `${d.feature}: `, h("strong", {}, d.value)),
    h("div", { class: "b" }, h("i", { style })),
    h("div", { style: "width:70px;text-align:right" }, `${d.effect > 0 ? "+" : ""}${d.effect} pp`));
}

export function emrPreview(pred, ctx) {
  if (!pred.alert) return null;
  return h("div", { class: "emr" }, h("div", { class: "h" }, "EMR alert preview (what the prescriber would see)"),
    h("div", { class: "b" }, h("strong", {}, "Disease X patient may qualify for Drug A."),
      h("ul", {}, h("li", {}, `High-risk: ${pred.eligibility_reasons.join("; ")}`),
        h("li", {}, "Drug A must be started within 5 days of symptom onset."),
        h("li", {}, "Patients like this are rarely treated - please review eligibility and contraindications."),
        ctx && ctx["Contraindication level (0-3)"] >= 2 ? h("li", {}, "Interacting medication on file - check before prescribing.") : null)));
}
