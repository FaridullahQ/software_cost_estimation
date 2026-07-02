# Software Cost Estimation — Calculation Manual

A short reference to **how every computed amount is derived**. Amounts recompute
live as you type; nothing is entered by hand except the inputs in **bold**.

---

## 1. Line-level amounts

### Labour line (Pre-Development tab)
Inputs: **Persons**, **Working Days**, **Hours/Day**, **Hourly Rate** (the rate
auto-fills from the chosen Role).

```
Person-Hours = Persons × Working Days × Hours/Day
Labour Cost  = Person-Hours × Hourly Rate
```

Head-count is applied **once** (inside Person-Hours). Example: 2 × 30 × 8 = 480
person-hours; 480 × $15 = **$7,200**.

### Development driver line (Development Drivers tab)
The **Method** decides the formula:

| Method | Formula | You enter |
|---|---|---|
| Count × Complexity × Rate | `Count × Complexity × Unit Rate` | Count, Complexity (1–10), Unit Rate |
| Count × Unit Price (flat) | `Count × Unit Rate` | Count, Unit Rate |
| Toggle | `Unit Rate` if **Included** ticked, else `0` | Included, Unit Rate |

Examples: 15 × 8 × $10 = **$1,200**; 4 × $1,000 = **$4,000**; SSO ticked at
$1,000 = **$1,000**.

### Markup line (Markups & Maintenance tab)
Inputs: **Percent**, **Applied On** (base), **Recurring** flag.

```
Base Amount = TDC, or Development Catalog, or Labour   (per "Applied On")
Markup Amount = Base Amount × Percent ÷ 100
```

Example: PM 25% on a TDC of $52,060 = **$13,015**.

---

## 2. Flat factors (from project parameters)

These come from the selection fields and the values set in
**Configuration → Settings** (defaults shown):

```
Scope Cost        = Small 2,000 | Medium 4,000 | Large 8,000
Duration Cost     = Duration (months) × Cost-per-Month (1,000)
Tech Variance Cost= Level One 2,000 | Level Two 4,000 | Level Three 6,000
Architecture Cost = Monolith 500 | Hybrid 750 | Micro Services 1,000
License Cost      = entered manually
```

---

## 3. Roll-up (totals footer)

```
Labour Cost        = Σ Labour line amounts
Development Catalog = Σ Development line amounts

Stack Adjustment   = (Labour Cost + Development Catalog) × (Productivity Factor − 1)
                     (0 when no stack is selected; factor defaults to 1.0)

TDC (Total Development Cost)
    = Labour Cost
    + Development Catalog
    + Stack Adjustment
    + Tech Variance Cost
    + License Cost
    + Architecture Cost

One-time Markups   = Σ markup amounts where Recurring = No
Annual Maintenance = Σ markup amounts where Recurring = Yes

One-time Subtotal  = TDC + Scope Cost + Duration Cost + One-time Markups
Contingency Amount = One-time Subtotal × Contingency % ÷ 100
One-time Total (CapEx) = One-time Subtotal + Contingency Amount

Grand Total (Year 1) = roundup( One-time Total + Annual Maintenance )
```

**TDC is the base for percentage markups, and it excludes Scope, Duration,
markups and contingency** — so there is no circular reference. Maintenance is
reported separately as a recurring annual (OpEx) figure, but its first year is
included in the Year-1 Grand Total. Rounding uses the increment in Settings
(default 1, i.e. round up to the whole currency unit).

---

## 4. Risk band (Risk & Negotiation tab)

```
Optimistic   = Grand Total × (1 − Optimistic % ÷ 100)
Pessimistic  = Grand Total × (1 + Pessimistic % ÷ 100)
Expected (PERT) = (Optimistic + 4 × Grand Total + Pessimistic) ÷ 6
```

The PERT figure weights the most-likely value heavily but is pulled toward the
worst case — a more defensible number to budget against.

```
Variance = Grand Total − Approved/Negotiated Amount
```

---

## 5. Worked example (the "Afghan Telecom — Inventory" demo)

| Component | Amount |
|---|---:|
| Labour Cost | 25,800 |
| Development Catalog | 23,760 |
| Tech Variance (Level One) | 2,000 |
| Architecture (Monolith) | 500 |
| License | 0 |
| **TDC** | **52,060** |
| Scope (Medium) | 4,000 |
| Duration (12 × 1,000) | 12,000 |
| One-time Markups (PM 25 + Test 15 + Train 10 + Docs 10 = 60% of TDC) | 31,236 |
| One-time Subtotal | 99,296 |
| Contingency (10%) | 9,930 |
| **One-time Total (CapEx)** | **109,226** |
| Annual Maintenance (30% of TDC, recurring) | 15,618 |
| **Grand Total (Year 1)** | **124,844** |

Risk band: Optimistic **112,360** / Expected (PERT) **127,965** /
Pessimistic **156,055**.

---

## 6. Evaluation order (for reference)

Line amounts → Labour & Catalog subtotals + Flat factors → **TDC** →
Markups (depend on TDC) → One-time Subtotal → Contingency → One-time Total →
Grand Total → Risk band & Variance. Each step depends only on earlier ones.

---

## 7. Technology stack (productivity calibration)

Each stack carries a **Productivity Factor** (Configuration → Technology Stacks).
It scales the build effort only:

```
Stack Adjustment = (Labour Cost + Development Catalog) × (Factor − 1)
```

Factor 1.0 is the baseline (hand-built backend + SPA). Below 1.0 = more
productive stack (Odoo ≈ 0.60); above 1.0 = more effort for the same scope
(bespoke micro-services ≈ 1.20). The same functional size therefore yields a
different TDC per stack, and markups — which sit on TDC — follow automatically.

---

## 8. Sub-module roll-up (consolidation)

A main estimate can roll in any number of standalone **sub-module** estimates,
each at an allocation percentage (use < 100% for a shared component). Amounts
are converted to the main's currency at the estimate date.

```
Allocated CapEx (per sub) = convert(Sub One-time Total) × Allocation% ÷ 100
Allocated OpEx  (per sub) = convert(Sub Annual Maintenance) × Allocation% ÷ 100

Consolidated CapEx = Main One-time Total + Σ Allocated CapEx
Consolidated OpEx  = Main Annual Maintenance + Σ Allocated OpEx
Consolidated Total (Year 1) = roundup(Consolidated CapEx + Consolidated OpEx)
```

Sub-modules are summed **fully-loaded** — the main's markups and contingency
are NOT re-applied on top, because each sub-module is already a complete
estimate. Circular roll-ups are blocked. When there are no sub-modules,
Consolidated Total equals the Grand Total.

---

## 9. Discount (justified)

A manager applies a discount to the consolidated total. It can never be applied
without a reason plus a reference and/or an official supporting document; the
justification is recorded in the chatter.

```
Discount Amount = Consolidated Total × Value ÷ 100        (percentage)
                = Value                                    (fixed amount)
                  capped to never exceed the Consolidated Total
Final Price     = Consolidated Total − Discount Amount
```

The PERT risk band is computed on the **pre-discount** consolidated total
(it expresses cost uncertainty, not a commercial decision). The negotiation
**Variance** compares the Approved/Negotiated amount against the **Final Price**.
