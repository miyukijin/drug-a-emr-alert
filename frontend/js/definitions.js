/** Shared field definitions (exercise workbook + model_table spec). */
import { h } from "./dom.js";

export const TOOLTIP = {
  conditions:
    "Count of distinct qualifying high-risk conditions (0–4) recorded on or before the first Disease X diagnosis. Counts diabetes, heart disease, immunocompromised, and obesity (each at most once). Hypertension and mental health are not included in this count.",
  p_treated:
    "P(treated): model-estimated probability the patient will receive Drug A in the sample, from features at diagnosis. It reflects historical prescribing patterns, not clinical appropriateness. Alerts use eligible AND P(treated) below the threshold.",
  eligible:
    "Label-based eligibility for Drug A: age > 12 and (age ≥ 65 or ≥ 1 qualifying high-risk condition in the Conditions count).",
};

const TERMS = [
  {
    term: "Conditions (count)",
    body: [
      "The number shown is ",
      h("code", {}, "NUM_CONDITIONS"),
      ": how many ",
      h("strong", {}, "different"),
      " qualifying high-risk condition ",
      h("strong", {}, "types"),
      " appear in the record on or before the first Disease X diagnosis date.",
    ],
    bullets: [
      "Range 0–4 (each type counted at most once).",
      "Included types: diabetes, heart disease (cardiovascular), immunocompromised, obesity — aligned with the exercise Instructions high-risk list and model_table.",
      "Built from ",
      h("code", {}, "CONDITIONS"),
      " transactions in the sample, point-in-time (nothing after the diagnosis date is used).",
      "Not included in this count: hypertension and mental health (recorded separately in the pipeline but excluded from ",
      h("code", {}, "NUM_CONDITIONS"),
      " per the submission’s eligibility assumption).",
      "Contributes to eligibility when age < 65: you need Conditions ≥ 1 (or age ≥ 65).",
    ],
  },
  {
    term: "P(treated)",
    body: [
      h("strong", {}, "P(treated)"),
      " is the ",
      h("strong", {}, "probability the model assigns"),
      " to “this patient receives Drug A” (",
      h("code", {}, "TARGET = 1"),
      " in the sample), using age, gender, Conditions count, physician specialty/state, and care setting at diagnosis.",
    ],
    bullets: [
      "Shown as a percentage in the UI (e.g. 8% means P(treated) = 0.08).",
      "It estimates ",
      h("strong", {}, "observed prescribing behaviour"),
      " in the exercise data — useful to ",
      h("strong", {}, "prioritise"),
      " patients, not to decide clinical appropriateness.",
      "An ",
      h("strong", {}, "alert"),
      " fires when the patient is ",
      h("strong", {}, "eligible"),
      " and ",
      h("code", {}, "P(treated)"),
      " is below the alert threshold (default 15%).",
      "Likelihood tiers (Low / Medium / High) are derived from ",
      h("code", {}, "P(treated)"),
      " relative to that threshold.",
    ],
  },
  {
    term: "Eligible for Drug A alert",
    body: [
      "Matches the exercise label rule: age > 12 and (age ≥ 65 or ≥ 1 condition in the Conditions count above).",
    ],
    bullets: [
      "Eligibility is rule-based (transparent). The model only ranks treatment likelihood among eligible patients.",
      "Patients who are not eligible never receive an alert, regardless of ",
      h("code", {}, "P(treated)"),
      ".",
    ],
  },
];

function termBlock({ term, body, bullets }) {
  return h("div", { class: "def-term" },
    h("h3", {}, term),
    h("p", {}, ...body),
    h("ul", {}, ...bullets.map((b) => h("li", {}, ...(Array.isArray(b) ? b : [b])))));
}

/** Always-visible summary on the worklist (not collapsed). */
export function definitionsCallout() {
  const row = (term, text) =>
    h("div", { class: "defs-callout-row" },
      h("div", { class: "defs-callout-term" }, term),
      h("div", { class: "defs-callout-desc" }, text));
  return h("section", { class: "defs-callout", id: "field-definitions", "aria-labelledby": "defs-callout-title" },
    h("h2", { class: "defs-callout-title", id: "defs-callout-title" }, "Field definitions"),
    h("p", { class: "defs-callout-lead" }, "English wording for the columns in the worklist and patient cards."),
    row("Conditions", TOOLTIP.conditions),
    row("P(treated)", TOOLTIP.p_treated),
    row("Eligible", TOOLTIP.eligible),
    h("p", { class: "note" }, "More detail: ",
      h("a", { href: "#about", onclick: (e) => { e.preventDefault(); location.hash = "about"; } }, "About the model"),
      " tab."));
}

/** Full definitions block for About (and optional expandable worklist). */
export function definitionsPanel({ compact = false } = {}) {
  const inner = h("div", { class: "defs-body" }, ...TERMS.map(termBlock));
  if (compact) {
    return h("details", { class: "defs compact", open: true },
      h("summary", {}, "Extended definitions (optional)"),
      inner);
  }
  return h("div", { class: "card defs" },
    h("h2", { style: "margin:0 0 12px;font-size:18px" }, "Field definitions"),
    h("p", { class: "note", style: "margin-top:0" }, "How to read the worklist and patient cards. Wording follows the exercise workbook and ",
      h("code", {}, "docs/data_dictionary_model_table.md"),
      "."),
    inner);
}