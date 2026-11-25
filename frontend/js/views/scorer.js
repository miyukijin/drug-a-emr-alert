import { api } from "../api.js";
import { h, titleCase, errorBox } from "../dom.js";
import { predictionPanel } from "./patient_card.js";

export async function scorer(root) {
  const out = h("div");
  let cats = {};
  try { cats = (await api.model()).categories; } catch (e) { root.replaceChildren(errorBox(e)); return; }
  const select = (name, values, def) => h("select", { name }, values.map((v) => h("option", { value: v, selected: v === def }, name === "physician_state" ? v : titleCase(v))));
  const field = (label, control) => h("label", { class: "f" }, label, control);
  const form = h("form", { class: "card", onsubmit: async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const body = { patient_age: Number(fd.get("patient_age")), patient_gender: fd.get("patient_gender"), num_conditions: Number(fd.get("num_conditions")),
      physician_type: fd.get("physician_type"), physician_state: fd.get("physician_state"), location_type: fd.get("location_type") };
    out.replaceChildren(h("div", { class: "loading" }, "Scoring..."));
    try { out.replaceChildren(predictionPanel(await api.predict(body))); } catch (err) {
      out.replaceChildren(errorBox(err), err.details ? h("ul", {}, err.details.map((d) => h("li", {}, `${d.field}: ${d.message}`))) : null);
    }
  } },
    h("div", { class: "grid g3" },
      field("Age at diagnosis", h("input", { name: "patient_age", type: "number", min: 0, max: 120, value: 71, required: true })),
      field("Gender", h("select", { name: "patient_gender" }, ["F", "M", "U"].map((g) => h("option", { value: g }, { F: "Female", M: "Male", U: "Unknown" }[g])))),
      field("High-risk conditions (count)", h("input", { name: "num_conditions", type: "number", min: 0, max: 10, value: 2, required: true })),
      field("Diagnosing physician specialty", select("physician_type", cats.PHYSICIAN_TYPE, "FAMILY MEDICINE")),
      field("Physician state", select("physician_state", cats.PHYSICIAN_STATE, "CA")),
      field("Care setting", select("location_type", cats.LOCATION_TYPE, "OFFICE"))),
    h("div", { style: "margin-top:14px" }, h("button", { class: "btn", type: "submit" }, "Score patient")));
  root.replaceChildren(h("h1", {}, "Score a patient"), h("p", { class: "sub" }, "What-if tool: enter the model features as the EMR would send them, and see the same result the alert API returns."), form, h("div", { style: "margin-top:16px" }, out));
}
