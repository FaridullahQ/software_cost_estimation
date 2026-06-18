# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from .cost_estimation_catalog import CATEGORY_SELECTION

STATE_LABELS = {
    "draft": "Draft",
    "review": "Under Review",
    "approved": "Approved",
    "rejected": "Rejected",
    "cancel": "Cancelled",
}
STATE_COLORS = {
    "draft": "#888780",
    "review": "#EF9F27",
    "approved": "#1D9E75",
    "rejected": "#E24B4A",
    "cancel": "#B4B2A9",
}
SCOPE_LABELS = {"small": "Small", "medium": "Medium", "large": "Large"}
ARCH_LABELS = {
    "monolith": "Monolith",
    "hybrid": "Hybrid (Monolith Modular)",
    "microservices": "Micro Services",
}


class CostEstimateDashboard(models.Model):
    _inherit = "cost.estimate"

    # ------------------------------------------------------------------ helpers
    @api.model
    def _dashboard_domain(self, filters):
        filters = filters or {}
        domain = []
        year = filters.get("year")
        if year and year != "all":
            year = int(year)
            domain += [
                ("estimate_date", ">=", date(year, 1, 1)),
                ("estimate_date", "<=", date(year, 12, 31)),
            ]
        if filters.get("partner_id"):
            domain.append(("partner_id", "=", int(filters["partner_id"])))
        if filters.get("state"):
            domain.append(("state", "=", filters["state"]))
        if filters.get("scope"):
            domain.append(("scope", "=", filters["scope"]))
        if filters.get("architecture"):
            domain.append(("architecture", "=", filters["architecture"]))
        if filters.get("user_id"):
            domain.append(("user_id", "=", int(filters["user_id"])))
        return domain

    @api.model
    def _dashboard_currency(self):
        cur = self.env.company.currency_id
        return {
            "symbol": cur.symbol or "",
            "position": cur.position or "before",
        }

    # --------------------------------------------------------------- main fetch
    @api.model
    def retrieve_dashboard_data(self, filters=None):
        filters = filters or {}
        domain = self._dashboard_domain(filters)
        estimates = self.search(domain)

        total_value = sum(estimates.mapped("grand_total"))
        count = len(estimates)
        approved = estimates.filtered(lambda e: e.state == "approved")
        approved_value = sum(
            e.approved_amount or e.grand_total for e in approved
        )
        pending = estimates.filtered(lambda e: e.state == "review")
        pending_value = sum(pending.mapped("grand_total"))
        capex = sum(estimates.mapped("total_one_time"))
        opex = sum(estimates.mapped("maintenance_annual"))
        effort = sum(estimates.mapped("labor_line_ids").mapped("person_hours"))
        avg_value = total_value / count if count else 0.0
        approval_rate = (len(approved) / count * 100.0) if count else 0.0

        kpi = {
            "total_value": total_value,
            "count": count,
            "approved_value": approved_value,
            "approved_count": len(approved),
            "pending_value": pending_value,
            "pending_count": len(pending),
            "capex": capex,
            "opex": opex,
            "avg_value": avg_value,
            "approval_rate": approval_rate,
            "effort_hours": effort,
        }

        charts = {
            "by_month": self._dashboard_by_month(estimates, filters),
            "by_state": self._dashboard_by_state(estimates),
            "cost_structure": self._dashboard_cost_structure(estimates),
            "by_category": self._dashboard_by_category(estimates),
        }

        return {
            "currency": self._dashboard_currency(),
            "kpi": kpi,
            "charts": charts,
            "top_projects": self._dashboard_top_projects(estimates),
            "recent": self._dashboard_recent(estimates),
            "estimates_list": [
                {"id": e.id, "name": "%s — %s" % (e.name, e.title or "")}
                for e in estimates.sorted(key=lambda r: r.id, reverse=True)[:100]
            ],
            "filters": self._dashboard_filter_options(),
        }

    # ------------------------------------------------------------------ charts
    @api.model
    def _dashboard_by_month(self, estimates, filters):
        year = filters.get("year")
        buckets = []
        if year and year != "all":
            year = int(year)
            months = [date(year, m, 1) for m in range(1, 13)]
        else:
            today = fields.Date.context_today(self)
            start = today.replace(day=1) - relativedelta(months=11)
            months = [start + relativedelta(months=i) for i in range(12)]
        index = {(d.year, d.month): 0.0 for d in months}
        for e in estimates:
            if not e.estimate_date:
                continue
            key = (e.estimate_date.year, e.estimate_date.month)
            if key in index:
                index[key] += e.grand_total
        labels = [d.strftime("%b %Y") for d in months]
        values = [round(index[(d.year, d.month)], 2) for d in months]
        return {"labels": labels, "values": values}

    @api.model
    def _dashboard_by_state(self, estimates):
        labels, values, counts, colors = [], [], [], []
        for state, label in STATE_LABELS.items():
            recs = estimates.filtered(lambda e: e.state == state)
            if not recs:
                continue
            labels.append(label)
            values.append(round(sum(recs.mapped("grand_total")), 2))
            counts.append(len(recs))
            colors.append(STATE_COLORS[state])
        return {"labels": labels, "values": values, "counts": counts, "colors": colors}

    @api.model
    def _dashboard_cost_structure(self, estimates):
        return {
            "labels": ["Labour", "Dev Catalog", "Markups", "Maintenance", "Contingency"],
            "values": [
                round(sum(estimates.mapped("labor_cost")), 2),
                round(sum(estimates.mapped("dev_catalog_cost")), 2),
                round(sum(estimates.mapped("markup_one_time")), 2),
                round(sum(estimates.mapped("maintenance_annual")), 2),
                round(sum(estimates.mapped("contingency_amount")), 2),
            ],
            "colors": ["#378ADD", "#1D9E75", "#EF9F27", "#7F77DD", "#B4B2A9"],
        }

    @api.model
    def _dashboard_by_category(self, estimates):
        cat_labels = dict(CATEGORY_SELECTION)
        groups = self.env["cost.estimate.line"].read_group(
            [("estimate_id", "in", estimates.ids)],
            ["amount:sum"],
            ["category"],
        )
        labels, values = [], []
        for g in groups:
            if not g.get("category") or not g.get("amount"):
                continue
            labels.append(cat_labels.get(g["category"], g["category"]))
            values.append(round(g["amount"], 2))
        return {"labels": labels, "values": values}

    @api.model
    def _dashboard_top_projects(self, estimates):
        groups = {}
        for e in estimates:
            key = e.partner_id.name if e.partner_id else "Unassigned"
            groups[key] = groups.get(key, 0.0) + e.grand_total
        ranked = sorted(groups.items(), key=lambda kv: kv[1], reverse=True)[:10]
        top = ranked[0][1] if ranked else 0.0
        return [
            {
                "name": name,
                "value": round(value, 2),
                "pct": round((value / top * 100.0) if top else 0.0, 1),
            }
            for name, value in ranked
        ]

    @api.model
    def _dashboard_recent(self, estimates):
        recent = estimates.sorted(key=lambda r: r.id, reverse=True)[:8]
        return [
            {
                "id": e.id,
                "title": e.title or e.name,
                "ref": e.name,
                "partner": e.partner_id.name or "",
                "state": e.state,
                "state_label": STATE_LABELS.get(e.state, e.state),
                "state_color": STATE_COLORS.get(e.state, "#888780"),
                "value": round(e.grand_total, 2),
            }
            for e in recent
        ]

    # ------------------------------------------------------------ filter lists
    @api.model
    def _dashboard_filter_options(self):
        all_est = self.search([])
        years = sorted(
            {e.estimate_date.year for e in all_est if e.estimate_date},
            reverse=True,
        )
        partners = all_est.mapped("partner_id")
        users = all_est.mapped("user_id")
        return {
            "years": years,
            "projects": [{"id": p.id, "name": p.name} for p in partners],
            "users": [{"id": u.id, "name": u.name} for u in users],
            "states": [{"value": k, "label": v} for k, v in STATE_LABELS.items()],
            "scopes": [{"value": k, "label": v} for k, v in SCOPE_LABELS.items()],
            "architectures": [
                {"value": k, "label": v} for k, v in ARCH_LABELS.items()
            ],
        }

    # ----------------------------------------------------------- deep dive
    @api.model
    def get_estimate_detail(self, estimate_id):
        e = self.browse(int(estimate_id))
        if not e.exists():
            return {}
        return {
            "id": e.id,
            "title": e.title or e.name,
            "ref": e.name,
            "partner": e.partner_id.name or "",
            "state_label": STATE_LABELS.get(e.state, e.state),
            "scope": SCOPE_LABELS.get(e.scope, ""),
            "architecture": ARCH_LABELS.get(e.architecture, ""),
            "tdc": round(e.tdc, 2),
            "capex": round(e.total_one_time, 2),
            "opex": round(e.maintenance_annual, 2),
            "grand_total": round(e.grand_total, 2),
            "approved_amount": round(e.approved_amount, 2),
            "variance": round(e.variance, 2),
            "optimistic": round(e.optimistic_total, 2),
            "expected": round(e.expected_total, 2),
            "pessimistic": round(e.pessimistic_total, 2),
            "effort_hours": round(
                sum(e.labor_line_ids.mapped("person_hours")), 1
            ),
            "structure": {
                "labels": ["Labour", "Dev Catalog", "Markups", "Maintenance", "Contingency"],
                "values": [
                    round(e.labor_cost, 2),
                    round(e.dev_catalog_cost, 2),
                    round(e.markup_one_time, 2),
                    round(e.maintenance_annual, 2),
                    round(e.contingency_amount, 2),
                ],
                "colors": ["#378ADD", "#1D9E75", "#EF9F27", "#7F77DD", "#B4B2A9"],
            },
        }
