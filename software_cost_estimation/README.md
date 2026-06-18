# Software Cost Estimation (Odoo 17)

A driver-based **parametric cost-estimation** application for software /
information-system projects. It re-engineers the *Systems Development
Directorate* cost-estimation workbook into a dynamic, multi-record Odoo app
with calibration data, a clean calculation engine, an approval workflow and a
PDF report.

---

## 1. Why this design

The source Excel is, in effect, a lightweight **Function-Point-style parametric
model**: it counts functional components (tables, processes, interfaces,
integrations, security features, migration steps), weights them by complexity,
multiplies by a unit rate, then layers percentage markups (PM, testing,
training, documentation, maintenance) on top.

Industry practice for this class of estimate (COCOMO II Early Design, FPA,
three-point/PERT) says to:

* separate **size/complexity drivers** from the **rate-card calibration data**;
* keep **markup factors configurable** rather than hard-coded;
* separate **one-time (CapEx)** build cost from **recurring (OpEx)** maintenance;
* express uncertainty with an **optimistic / most-likely / pessimistic** band.

The Odoo apps ecosystem (project-estimation / project-costing modules)
consistently models this as an **estimate header + categorized cost lines +
draft→approve workflow + PDF report**. This module follows both conventions.

---

## 2. How it maps to the Excel workbook

| Excel concept | Module equivalent |
|---|---|
| One sheet per project | One `cost.estimate` record per project |
| Pre-development labour (Assessment / Req. Gathering / Analysis) | `cost.estimate.labor` lines |
| Development catalog (rows 23–52) | `cost.estimate.line` driver lines + `cost.estimation.catalog` library |
| `$15/hr` flat labour rate | `cost.estimation.rate` rate card (per role) |
| Tech variance / License / Architecture flat adders | Estimate fields → `tech_variance_cost`, `license_cost`, `architecture_cost` |
| Scope (`4000`) / Initial time (`months × 1000`) | `scope_cost` / `duration_cost` (configurable in Settings) |
| TDC = `SUM(L15:L52)` | `tdc` = labour + tech variance + license + architecture + dev catalog |
| PM 25% / Testing 15% / Training 10% / Docs 10% / Maintenance 30% | `cost.estimate.markup` lines, seeded from `cost.estimation.markup.template` |
| Grand total `CEILING(L61)` | `grand_total` (one-time + first-year maintenance, rounded up) |
| Hand-written "Reduced Amount" | `approved_amount` + `variance` (negotiation fields) |

Every driver, category and unit price from the workbook is preserved as seed
data in `data/cost_estimation_catalog_data.xml`, and two of the original
projects are reproduced in `demo/` (Telecom Inventory and a differentiated
Afghan Post HRMIS).

---

## 3. What was corrected

1. **Labour double-counting (the critical bug).** In the Excel, person-hours
   already include head-count (`days × 8 × persons`), and the cost column then
   multiplied by persons **again**, so labour scaled with *persons²*. Here
   `person_hours = persons × days × hours_per_day` and
   `amount = person_hours × rate` — head-count is applied **once**. For the
   original Telecom inputs this corrects pre-development labour from a
   double-counted **40,800** down to the correct **20,400**.

2. **Configurable markups.** PM/testing/training/etc. are data-driven lines with
   a selectable base, not hard-coded formulas. Mislabeled bases ("% of
   hardware/software cost" with no hardware line) are gone.

3. **CapEx / OpEx separation.** Recurring maintenance is flagged `is_recurring`
   and reported as an annual figure, distinct from the one-time build cost
   (while still rolled into a Year-1 grand total to mirror the workbook).

4. **Normalized driver semantics.** Three explicit calculation methods replace
   the overloaded "complexity" column:
   * `count × complexity × rate` (parametric sizing — tables, processes, interfaces, reporting);
   * `count × unit price` (flat — integrations, users, data volume, localization);
   * `toggle` (binary on/off — auth methods, authorization models, migration steps).

5. **Risk handling.** Optional contingency reserve plus an optimistic / expected
   (PERT) / pessimistic band — absent from the Excel entirely.

6. **Governance.** Sequenced references, draft→review→approved workflow,
   chatter/activities, security groups, and a QWeb PDF — none of which a
   spreadsheet provides.

---

## 4. Structure

```
software_cost_estimation/
├── models/         rate card, catalog, markup template, estimate + 3 line models, settings
├── security/       groups, record rules, access rights
├── data/           sequence, rate card, driver catalog, markup templates
├── views/          form / tree / kanban / search, config menus & settings
├── report/         paperformat + QWeb PDF estimate
└── demo/           two differentiated sample estimates
```

## 5. Install

1. Copy `software_cost_estimation/` into your Odoo 17 addons path.
2. Update the apps list and install **Software Cost Estimation**.
3. Open **Cost Estimation → Estimates → New**, fill the header, then click
   **Load Standard Template** to populate the labour phases and the full driver
   catalog. Set counts / complexity / toggles, and the totals compute live.
4. Tune defaults under **Cost Estimation → Configuration → Settings** and the
   **Rate Card** / **Cost Driver Catalog** / **Markup Templates**.

Requires only `base` and `mail`. Licensed LGPL-3.

---

## 6. Dashboard (OWL)

The app opens on an interactive **Dashboard** (Cost Estimation → Dashboard), a
custom OWL client action backed by a single server method
(`cost.estimate.retrieve_dashboard_data`) that aggregates everything
server-side and respects record rules + multi-company.

It provides a filter bar (Year — defaults to the current year — Project, Status,
Scope, Architecture), KPI cards (total pipeline, approved value, average,
CapEx, annual OpEx, approval rate, total effort), and live Chart.js charts:
value by month, pipeline by status, portfolio cost structure, and driver cost by
category. Two scroll panels rank top projects by value and list recent estimates
(click to open), and a Project deep-dive shows any single estimate's cost stack,
CapEx/OpEx, variance and PERT band.

Assets load from `static/src/dashboard/` via the `web.assets_backend` bundle.

---

## Author & license

Developed and maintained by **Faridullah Qaderi & Hameed Masjedi** — **FOITECH - Digital Solutions**.
Support: faridullahqaderi54@gmail.com · https://www.linkedin.com/in/faridullah-qaderi-114405330

Released under the **LGPL-3** license (free and open source).
