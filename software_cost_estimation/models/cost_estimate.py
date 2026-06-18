# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError

PARAM = "software_cost_estimation"


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class CostEstimate(models.Model):
    _name = "cost.estimate"
    _description = "Software Cost Estimate"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    # ------------------------------------------------------------------ Header
    name = fields.Char(
        string="Reference", required=True, copy=False, readonly=True,
        index=True, default=lambda self: _("New"),
    )
    title = fields.Char(
        string="Estimate Title", required=True, tracking=True,
        help="e.g. Inventory Management System - Afghan Telecom",
    )
    system_name = fields.Char(string="System / Product")
    partner_id = fields.Many2one(
        "res.partner", string="Client / Beneficiary", tracking=True
    )
    user_id = fields.Many2one(
        "res.users", string="Estimator", default=lambda self: self.env.user,
        tracking=True,
    )
    estimate_date = fields.Date(
        string="Estimate Date", default=fields.Date.context_today, tracking=True
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "Under Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        tracking=True,
        string="Status",
    )
    note = fields.Html(string="Notes / Assumptions")

    # ------------------------------------------------------- Project parameters
    scope = fields.Selection(
        [("small", "Small"), ("medium", "Medium"), ("large", "Large")],
        string="Scope", default="medium", tracking=True,
        help="Overall functional footprint of the system. Choose by entity "
        "count, integrations and user base:\n"
        "- Small: one focused module, up to ~8 core entities, 0-1 integration, "
        "< 50 users (e.g. a leave-request app).\n"
        "- Medium: several related modules, ~8-20 entities, 2-4 integrations, "
        "50-500 users (e.g. an inventory system).\n"
        "- Large: enterprise-wide, > 20 entities, many integrations, > 500 "
        "users, multiple departments (e.g. a nationwide HRMIS).\n"
        "Tip: use the 'Sizing Advisor' button for a recommendation from "
        "concrete numbers.",
    )
    duration_months = fields.Float(
        string="Estimated Duration (months)", default=12.0,
        help="Planned calendar duration. Drives the time-based cost "
        "(months x cost-per-month from Settings). Example: 8 months x $1,000 "
        "= $8,000.",
    )
    architecture = fields.Selection(
        [
            ("monolith", "Monolith"),
            ("hybrid", "Hybrid (Monolith Modular)"),
            ("microservices", "Micro Services"),
        ],
        string="System Architecture", default="monolith",
        help="Deployment / structuring style:\n"
        "- Monolith: one deployable unit; simplest to build and run. Best for "
        "small systems and a single team (e.g. a standard Odoo web app).\n"
        "- Hybrid (Monolith Modular): one deployable, but internally split into "
        "independent modules with clear boundaries. A middle ground that gives "
        "modularity without the operational overhead of micro services (e.g. a "
        "modular ERP where HR/Finance are separate packages in one instance).\n"
        "- Micro Services: independently deployable and scalable services. "
        "Choose when parts must scale or release independently, or when several "
        "teams work in parallel (e.g. a payments service split from the portal). "
        "Highest operational complexity.",
    )
    tech_variance = fields.Selection(
        [("level1", "Level One"), ("level2", "Level Two"), ("level3", "Level Three")],
        string="Technology Variance", default="level1",
        help="Novelty / risk of the technology stack relative to the team's "
        "experience:\n"
        "- Level One: mature, well-known stack the team has shipped before "
        "(e.g. Odoo + PostgreSQL). Lowest risk.\n"
        "- Level Two: partly new - a new framework, protocol or moderate "
        "unfamiliarity (e.g. first project using a message queue or a new "
        "reporting engine).\n"
        "- Level Three: emerging / unproven technology or low team familiarity "
        "(e.g. AI/ML, blockchain, IoT, real-time streaming). Highest risk - "
        "widen the contingency reserve.",
    )
    license_cost = fields.Monetary(
        string="License Cost", currency_field="currency_id",
        help="Third-party products, libraries or tools.",
    )

    # -------------------------------------------------------------------- Lines
    labor_line_ids = fields.One2many(
        "cost.estimate.labor", "estimate_id", string="Labour"
    )
    dev_line_ids = fields.One2many(
        "cost.estimate.line", "estimate_id", string="Development Drivers"
    )
    markup_line_ids = fields.One2many(
        "cost.estimate.markup", "estimate_id", string="Markups"
    )
    markup_base_mode = fields.Selection(
        [
            ("auto", "Automatic (per line: TDC / Dev / Labour)"),
            ("manual", "Manual (single base for all markups)"),
        ],
        string="Markup Base Mode", default="auto", required=True, tracking=True,
        help="Automatic: each markup line derives its base from the selected "
        "pool (TDC, Development Catalog or Labour).\n"
        "Manual: every markup line uses one base amount you type below, "
        "regardless of the 'Applied On' pool. New lines inherit it automatically.",
    )
    manual_markup_base = fields.Monetary(
        string="Manual Markup Base", currency_field="currency_id",
        help="The single base amount applied to every markup line when "
        "Markup Base Mode is Manual.",
    )

    # ------------------------------------------------------------ Flat factors
    scope_cost = fields.Monetary(
        string="Scope Cost", compute="_compute_flat_factors", store=True,
        currency_field="currency_id",
    )
    duration_cost = fields.Monetary(
        string="Duration Cost", compute="_compute_flat_factors", store=True,
        currency_field="currency_id",
    )
    tech_variance_cost = fields.Monetary(
        string="Tech Variance Cost", compute="_compute_flat_factors", store=True,
        currency_field="currency_id",
    )
    architecture_cost = fields.Monetary(
        string="Architecture Cost", compute="_compute_flat_factors", store=True,
        currency_field="currency_id",
    )

    # --------------------------------------------------------------- Subtotals
    labor_cost = fields.Monetary(
        string="Labour (Pre-Development)", compute="_compute_totals", store=True,
        currency_field="currency_id",
    )
    dev_catalog_cost = fields.Monetary(
        string="Development Catalog", compute="_compute_totals", store=True,
        currency_field="currency_id",
    )
    tdc = fields.Monetary(
        string="Total Development Cost (TDC)", compute="_compute_totals",
        store=True, currency_field="currency_id",
        help="Labour + Tech Variance + License + Architecture + Dev Catalog. "
        "This is the base for percentage markups.",
    )
    markup_one_time = fields.Monetary(
        string="One-time Markups", compute="_compute_totals", store=True,
        currency_field="currency_id",
    )
    maintenance_annual = fields.Monetary(
        string="Annual Maintenance (OpEx)", compute="_compute_totals", store=True,
        currency_field="currency_id",
    )
    subtotal_one_time = fields.Monetary(
        string="One-time Subtotal", compute="_compute_totals", store=True,
        currency_field="currency_id",
    )
    contingency_percent = fields.Float(
        string="Contingency / Risk Reserve (%)", default=0.0,
        help="Management reserve added to the one-time build cost to absorb "
        "unknowns. Rule of thumb: ~10% for familiar Level-One work, 15-25% for "
        "Level-Three / unclear scope. Example: 15% on a $100,000 build adds "
        "$15,000.",
    )
    contingency_amount = fields.Monetary(
        string="Contingency Amount", compute="_compute_totals", store=True,
        currency_field="currency_id",
    )
    total_one_time = fields.Monetary(
        string="One-time Total (CapEx)", compute="_compute_totals", store=True,
        currency_field="currency_id",
    )
    grand_total = fields.Monetary(
        string="Grand Total (Year 1)", compute="_compute_totals", store=True,
        currency_field="currency_id",
        help="One-time build cost + first-year maintenance, rounded up.",
    )

    # ----------------------------------------------------------- Three-point band
    optimistic_pct = fields.Float(
        string="Optimistic -%", default=10.0,
        help="How much the cost could come in UNDER the grand total in the "
        "best case. Example: 10% means optimistic = grand total x 0.90.",
    )
    pessimistic_pct = fields.Float(
        string="Pessimistic +%", default=25.0,
        help="How much the cost could OVERRUN in the worst case. Example: 25% "
        "means pessimistic = grand total x 1.25.",
    )
    optimistic_total = fields.Monetary(
        string="Optimistic", compute="_compute_risk_band", store=True,
        currency_field="currency_id",
    )
    pessimistic_total = fields.Monetary(
        string="Pessimistic", compute="_compute_risk_band", store=True,
        currency_field="currency_id",
    )
    expected_total = fields.Monetary(
        string="Expected (PERT)", compute="_compute_risk_band", store=True,
        currency_field="currency_id",
        help="Risk-weighted estimate using the PERT formula "
        "(Optimistic + 4 x Most-Likely + Pessimistic) / 6. It pulls the "
        "headline figure toward the worst case to reflect that overruns are "
        "more common than savings - a more defensible number to budget against.",
    )

    # ------------------------------------------------------------- Negotiation
    approved_amount = fields.Monetary(
        string="Approved / Negotiated Amount", currency_field="currency_id",
        tracking=True,
    )
    variance = fields.Monetary(
        string="Variance vs Estimate", compute="_compute_variance",
        currency_field="currency_id",
    )

    # ===================================================================== compute
    @api.depends("scope", "duration_months", "tech_variance", "architecture")
    def _compute_flat_factors(self):
        ICP = self.env["ir.config_parameter"].sudo()
        scope_map = {
            "small": _f(ICP.get_param("%s.scope_small" % PARAM, 2000)),
            "medium": _f(ICP.get_param("%s.scope_medium" % PARAM, 4000)),
            "large": _f(ICP.get_param("%s.scope_large" % PARAM, 8000)),
        }
        tv_map = {
            "level1": _f(ICP.get_param("%s.tech_level1" % PARAM, 2000)),
            "level2": _f(ICP.get_param("%s.tech_level2" % PARAM, 4000)),
            "level3": _f(ICP.get_param("%s.tech_level3" % PARAM, 6000)),
        }
        arch_map = {
            "monolith": _f(ICP.get_param("%s.arch_monolith" % PARAM, 500)),
            "hybrid": _f(ICP.get_param("%s.arch_hybrid" % PARAM, 750)),
            "microservices": _f(ICP.get_param("%s.arch_microservices" % PARAM, 1000)),
        }
        monthly_rate = _f(ICP.get_param("%s.monthly_rate" % PARAM, 1000))
        for est in self:
            est.scope_cost = scope_map.get(est.scope, 0.0)
            est.duration_cost = est.duration_months * monthly_rate
            est.tech_variance_cost = tv_map.get(est.tech_variance, 0.0)
            est.architecture_cost = arch_map.get(est.architecture, 0.0)

    @api.depends(
        "labor_line_ids.amount",
        "dev_line_ids.amount",
        "markup_line_ids.amount",
        "markup_line_ids.is_recurring",
        "tech_variance_cost",
        "architecture_cost",
        "license_cost",
        "scope_cost",
        "duration_cost",
        "contingency_percent",
    )
    def _compute_totals(self):
        ICP = self.env["ir.config_parameter"].sudo()
        rounding = _f(ICP.get_param("%s.rounding" % PARAM, 1)) or 1.0
        for est in self:
            est.labor_cost = sum(est.labor_line_ids.mapped("amount"))
            est.dev_catalog_cost = sum(est.dev_line_ids.mapped("amount"))
            est.tdc = (
                est.labor_cost
                + est.tech_variance_cost
                + est.license_cost
                + est.architecture_cost
                + est.dev_catalog_cost
            )
            one_time_markups = est.markup_line_ids.filtered(
                lambda m: not m.is_recurring
            )
            recurring_markups = est.markup_line_ids.filtered(
                lambda m: m.is_recurring
            )
            est.markup_one_time = sum(one_time_markups.mapped("amount"))
            est.maintenance_annual = sum(recurring_markups.mapped("amount"))
            est.subtotal_one_time = (
                est.tdc + est.scope_cost + est.duration_cost + est.markup_one_time
            )
            est.contingency_amount = est.subtotal_one_time * (
                est.contingency_percent / 100.0
            )
            est.total_one_time = est.subtotal_one_time + est.contingency_amount
            raw_total = est.total_one_time + est.maintenance_annual
            est.grand_total = math.ceil(raw_total / rounding) * rounding

    @api.depends("grand_total", "optimistic_pct", "pessimistic_pct")
    def _compute_risk_band(self):
        for est in self:
            likely = est.grand_total
            est.optimistic_total = likely * (1 - est.optimistic_pct / 100.0)
            est.pessimistic_total = likely * (1 + est.pessimistic_pct / 100.0)
            est.expected_total = (
                est.optimistic_total + 4 * likely + est.pessimistic_total
            ) / 6.0

    @api.depends("grand_total", "approved_amount")
    def _compute_variance(self):
        for est in self:
            est.variance = est.grand_total - est.approved_amount

    # ===================================================================== CRUD
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "cost.estimate"
                ) or _("New")
            if not vals.get("markup_line_ids"):
                vals["markup_line_ids"] = self._default_markup_commands()
        return super().create(vals_list)

    def _default_markup_commands(self):
        commands = []
        templates = self.env["cost.estimation.markup.template"].search([])
        for tpl in templates:
            commands.append(
                (0, 0, {
                    "name": tpl.name,
                    "percent": tpl.percent,
                    "base": tpl.base,
                    "is_recurring": tpl.is_recurring,
                    "sequence": tpl.sequence,
                })
            )
        return commands

    # ================================================================== Actions
    def action_submit(self):
        for est in self:
            if not est.labor_line_ids and not est.dev_line_ids:
                raise UserError(_(
                    "Add at least one labour or development line before "
                    "submitting for review."
                ))
        self.write({"state": "review"})

    def action_approve(self):
        for est in self:
            if not est.approved_amount:
                est.approved_amount = est.grand_total
        self.write({"state": "approved"})

    def action_reset(self):
        self.write({"state": "draft"})

    def action_cancel(self):
        self.write({"state": "cancel"})

    def action_open_sizing_wizard(self):
        """Launch the Sizing Advisor, which recommends Scope, Technology
        Variance and Architecture from concrete project parameters."""
        self.ensure_one()
        return {
            "name": _("Sizing Advisor"),
            "type": "ir.actions.act_window",
            "res_model": "cost.estimate.sizing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_estimate_id": self.id},
        }

    def action_open_reject_wizard(self):
        """Launch the reject wizard so the reviewer must record a reason."""
        self.ensure_one()
        return {
            "name": _("Reject Estimate"),
            "type": "ir.actions.act_window",
            "res_model": "cost.estimate.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_estimate_id": self.id},
        }

    def action_load_template(self):
        """Populate a fresh estimate with the standard labour phases and the
        full development-driver catalog so the estimator starts from a complete
        baseline instead of a blank sheet."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Templates can only be loaded on a draft estimate."))
        self._load_standard_labor()
        self._load_catalog_lines()
        if not self.markup_line_ids:
            self.markup_line_ids = self._default_markup_commands()
        return True

    def _load_standard_labor(self):
        Rate = self.env["cost.estimation.rate"]
        re_role = Rate.search([("code", "=", "RE")], limit=1) or Rate.search([], limit=1)
        sa_role = Rate.search([("code", "=", "SA")], limit=1) or re_role
        rate_re = re_role.hourly_rate if re_role else 15.0
        rate_sa = sa_role.hourly_rate if sa_role else 15.0
        phases = [
            ("Assessment", re_role, 2, 10.0, rate_re),
            ("Requirement Gathering", re_role, 2, 30.0, rate_re),
            ("Analysis", sa_role, 3, 45.0, rate_sa),
        ]
        commands = []
        for seq, (label, role, persons, days, rate) in enumerate(phases, start=1):
            commands.append((0, 0, {
                "sequence": seq * 10,
                "name": label,
                "role_id": role.id if role else False,
                "responsible": role.name if role else "",
                "persons": persons,
                "working_days": days,
                "hours_per_day": 8.0,
                "hourly_rate": rate,
            }))
        self.labor_line_ids = commands

    def _load_catalog_lines(self):
        commands = []
        catalog = self.env["cost.estimation.catalog"].search([])
        for seq, item in enumerate(catalog, start=1):
            commands.append((0, 0, {
                "sequence": seq * 10,
                "catalog_id": item.id,
                "name": item.name,
                "category": item.category,
                "calc_method": item.calc_method,
                "complexity": item.default_complexity,
                "unit_rate": item.default_unit_rate,
                "count": 0.0,
                "included": False,
            }))
        self.dev_line_ids = commands

    def action_print_report(self):
        return self.env.ref(
            "software_cost_estimation.action_report_cost_estimate"
        ).report_action(self)
