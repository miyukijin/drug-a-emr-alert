import { api } from "../api.js";
import { h, titleCase, errorBox } from "../dom.js";
import { predictionPanel, emrPreview } from "./patient_card.js";

export async function lookup(root, nav, arg) {
  const out = h("div", { style: "margin-top:16px" });
  const input = h("input", { type: "number", min: 1, placeholder: "e.g. 2069", value: arg ?? "", "aria-label": "Patient ID", required: true });
  const form = h("form", { class: "toolbar", onsubmit: (e) => { e.preventDefault(); nav("lookup", input.value); } },
    h("label", { class: "f" }, "Patient ID", input), h("button", { class: "btn", type: "submit" }, "Look up"));
  root.replaceChildren(h("h1", {}, "Patient lookup"), h("p", { class: "sub" }, "Enter a patient ID to see the treatment likelihood, alert status and the reasons behind it."),
    h("div", { class: "card" }, form), out);

  async function show(id) {
    out.replaceChildren(h("div", { class: "loading" }, "Loading..."));
    try {
      const p = await api.patient(id);
      const f = p.features;
      out.replaceChildren(h("div", { class: "grid g2" },
        h("div", { class: "grid", style: "align-content:start" },
          h("div", { class: "card" }, h("h2", { style: "margin:0 0 10px;font-size:18px" }, `Patient #${p.patient_id}`),
            h("dl", { class: "kv" },
              h("dt", {}, "Disease X diagnosed"), h("dd", {}, p.diagnosis_date),
              h("dt", {}, "Age / gender"), h("dd", {}, `${f.patient_age} / ${f.patient_gender}`),
              h("dt", {}, "High-risk conditions"), h("dd", {}, f.num_conditions),
              h("dt", {}, "Diagnosed by"), h("dd", {}, titleCase(f.physician_type)),
              h("dt", {}, "Physician state"), h("dd", {}, f.physician_state),
              h("dt", {}, "Care setting"), h("dd", {}, titleCase(f.location_type)))),
          h("div", { class: "card" }, h("strong", {}, "Clinical context"), h("dl", { class: "kv", style: "margin-top:8px" },
            Object.entries(p.context).flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, String(v))]))),
          h("div", { class: "card muted" }, `Back-test only: this patient ${p.recorded_outcome_received_drug_a ? "did" : "did not"} receive Drug A in the sample data.`),
          emrPreview(p.prediction, p.context)),
        predictionPanel(p.prediction)));
    } catch (e) {
      out.replaceChildren(e.status === 404 ? h("div", { class: "empty" }, `No patient with ID ${id}. Try one from the alert worklist.`) : errorBox(e));
    }
  }
  if (arg) show(arg);
}
