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

TDC (Total Development Cost)
    = Labour Cost
    + Tech Variance Cost
    + License Cost
    + Architecture Cost
    + Development Catalog

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
