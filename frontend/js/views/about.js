import { api } from "../api.js";
import { h, pct, errorBox } from "../dom.js";
import { definitionsPanel } from "../definitions.js";

export async function about(root) {
  try {
    const m = await api.model();
    const row = (s) => h("tr", {}, h("td", {}, s.slice), h("td", {}, s.n), h("td", {}, pct(s.treated_rate)), h("td", {}, s.roc_auc.toFixed(3)), h("td", {}, s.pr_auc.toFixed(3)));
    root.replaceChildren(h("h1", {}, "About the model"),
      h("p", { class: "sub" }, "Transparent by design: what the model is, how it was checked, and what it cannot tell you."),
      definitionsPanel(),
      h("div", { class: "grid g2", style: "margin-top:16px" },
        h("div", { class: "card" }, h("dl", { class: "kv" },
          h("dt", {}, "Algorithm"), h("dd", {}, m.model_name), h("dt", {}, "Version"), h("dd", {}, m.version),
          h("dt", {}, "Features"), h("dd", {}, m.feature_set), h("dt", {}, "Trained on"), h("dd", {}, `${m.trained_rows.toLocaleString()} patients`),
          h("dt", {}, "Alert rule"), h("dd", {}, `Eligible (age >= ${m.min_eligible_age} and either age >= 65 or >= 1 high-risk condition) and P(treated) < ${pct(m.alert_threshold, 0)}`))),
        h("div", { class: "card" }, h("strong", {}, "Hold-out performance (20% of patients, not used for training)"),
          h("table", {}, h("thead", {}, h("tr", {}, ["Slice", "Patients", "Actually treated", "ROC-AUC", "PR-AUC"].map((t) => h("th", {}, t)))), h("tbody", {}, m.holdout_metrics.map(row))),
          h("div", { class: "note" }, "Discrimination is moderate: the score ranks patients usefully but is a prioritisation aid, not a verdict. Hold-out size is small; see the model report for confidence intervals."))));
  } catch (e) { root.replaceChildren(errorBox(e)); }
}
