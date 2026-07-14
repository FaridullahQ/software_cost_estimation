# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

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
    _rec_name = "title"

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
    is_sample = fields.Boolean(
        string="Sample Estimate", default=False, copy=False, index=True,
        help="Marks records created by the built-in sample data loader.",
    )

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
            ("layered", "Layered (N-Tier)"),
            ("client_server", "Client-Server"),
            ("hybrid", "Modular Monolith (Hybrid)"),
            ("microkernel", "Microkernel / Plug-in"),
            ("soa", "Service-Oriented (SOA)"),
            ("event_driven", "Event-Driven"),
            ("serverless", "Serverless (FaaS)"),
            ("microservices", "Micro Services"),
            ("space_based", "Space-Based"),
        ],
        string="System Architecture", default="monolith",
        help="Deployment / structuring style. Higher operational complexity "
             "carries a higher fixed cost; tune each style's amount in Settings.\n"
             "- Monolith: one deployable unit; simplest to build and run (e.g. a "
             "standard Odoo web app).\n"
             "- Layered (N-Tier): presentation / business / data tiers; the classic "
             "enterprise default.\n"
             "- Client-Server: a central server with thin/native clients.\n"
             "- Modular Monolith (Hybrid): one deployable, internally split into "
             "independent modules with clear boundaries - modularity without the "
             "overhead of micro services.\n"
             "- Microkernel / Plug-in: a minimal core extended by plug-ins (e.g. an "
             "IDE or a rules engine).\n"
             "- Service-Oriented (SOA): coarse-grained shared services over an "
             "enterprise bus.\n"
             "- Event-Driven: asynchronous producers/consumers over a broker; "
             "scalable and decoupled.\n"
             "- Serverless (FaaS): functions on managed infrastructure; little ops "
             "but cold-start and vendor constraints.\n"
             "- Micro Services: independently deployable, scalable services for "
             "parallel teams; high operational complexity.\n"
             "- Space-Based: in-memory data grid for extreme, elastic scale.",
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
    stack_id = fields.Many2one(
        "cost.estimation.stack", string="Technology Stack", tracking=True,
        help="The build technology (Odoo, Spring Boot, ASP.NET Core, Django, "
             "...). Its productivity factor scales Labour + Development Catalog, so "
             "the same functional size costs differently per stack. Leave empty for "
             "a stack-neutral estimate (factor 1.0).",
    )
    stack_factor = fields.Float(
        string="Productivity Factor", compute="_compute_stack_factor",
        store=True, default=1.0, recursive=True,
        help="Mirror of the selected stack's factor (1.0 when no stack set).",
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

    # ------------------------------------------------------- Sub-module roll-up
    component_ids = fields.One2many(
        "cost.estimate.component", "main_estimate_id",
        string="Sub-Modules",
        help="Standalone sub-module estimates rolled into this one.",
    )
    parent_component_ids = fields.One2many(
        "cost.estimate.component", "sub_estimate_id",
        string="Used In",
        help="Main estimates that roll this estimate in as a sub-module.",
    )
    has_components = fields.Boolean(
        string="Has Sub-Modules", compute="_compute_has_components", store=True
    )
    component_count = fields.Integer(
        string="Sub-Module Count", compute="_compute_has_components", store=True
    )
    parent_count = fields.Integer(
        string="Used-In Count", compute="_compute_parent_count"
    )
    components_capex = fields.Monetary(
        string="Sub-Modules CapEx", compute="_compute_consolidation",
        store=True, currency_field="currency_id",
    )
    components_opex = fields.Monetary(
        string="Sub-Modules OpEx (Annual)", compute="_compute_consolidation",
        store=True, currency_field="currency_id",
    )
    consolidated_capex = fields.Monetary(
        string="Consolidated CapEx", compute="_compute_consolidation",
        store=True, currency_field="currency_id",
        help="This estimate's own one-time cost plus the allocated CapEx of "
             "every rolled-in sub-module.",
    )
    consolidated_opex = fields.Monetary(
        string="Consolidated Annual Maintenance", compute="_compute_consolidation",
        store=True, currency_field="currency_id",
    )
    consolidated_total = fields.Monetary(
        string="Consolidated Total (Year 1)", compute="_compute_consolidation",
        store=True, currency_field="currency_id",
        help="Headline price including main + sub-modules, before any discount. "
             "Equals the Grand Total when there are no sub-modules.",
    )

    # ============================================== Parent / Sub-module linkage
    # A "sub-module" estimate carries ONLY its incremental build effort
    # (Labour + Development + stack-scaled adjustment). All shared one-time
    # costs - scope, duration, architecture, technology variance, technology
    # stack, license, markups, contingency, risk band and discount - belong to
    # the parent project and are paid there ONCE, so they are neither entered
    # nor calculated on the sub-module. The sub-module's build effort folds into
    # the parent's TDC *before* the parent applies its markups and contingency.
    estimate_type = fields.Selection(
        [
            ("independent", "Independent Project"),
            ("sub_module", "Sub-Module of a Project"),
        ],
        string="Estimate Type", default="independent", required=True,
        tracking=True,
        help="Independent Project: a complete, self-contained estimate that "
             "carries all of its own costs.\n"
             "Sub-Module of a Project: a partial estimate that belongs to a parent "
             "project. It holds only its own build effort (Labour + Development); the "
             "shared costs (scope, duration, architecture, technology, stack, "
             "license, markups, contingency, discount) are defined and charged once "
             "on the parent, so they are hidden here to avoid double counting.",
    )
    parent_estimate_id = fields.Many2one(
        "cost.estimate", string="Parent Project", tracking=True,
        ondelete="restrict", index=True,
        domain="[('estimate_type', '=', 'independent')]",
        help="The independent project this sub-module rolls up into. Its "
             "technology-stack productivity factor is inherited so this sub-module's "
             "effort is calibrated consistently with the parent.",
    )
    child_estimate_ids = fields.One2many(
        "cost.estimate", "parent_estimate_id", string="Linked Sub-Modules",
        help="Partial sub-module estimates whose build effort rolls into this "
             "project before markups and contingency are applied.",
    )
    child_count = fields.Integer(
        string="Linked Sub-Module Count", compute="_compute_child_rollup", store=True
    )
    child_build_total = fields.Monetary(
        string="Sub-Modules Build Effort", compute="_compute_child_rollup",
        store=True, currency_field="currency_id",
        help="Sum of every linked sub-module's build effort, folded into this "
             "project's TDC.",
    )
    # Inherited mirrors, shown read-only on a sub-module so the estimator can
    # see what is defined on the parent (and which productivity factor applies).
    # Computed (not related) with an explicit comodel so the comodel is always
    # resolved - a bare related Many2one can leave the comodel as '_unknown'
    # and break onchange reads.
    parent_stack_factor = fields.Float(
        string="Inherited Productivity Factor",
        compute="_compute_parent_mirror",
    )
    parent_stack_id = fields.Many2one(
        "cost.estimation.stack", string="Inherited Technology Stack",
        compute="_compute_parent_mirror",
    )

    @api.depends("parent_estimate_id.stack_id",
                 "parent_estimate_id.stack_factor")
    def _compute_parent_mirror(self):
        for est in self:
            est.parent_stack_id = est.parent_estimate_id.stack_id
            est.parent_stack_factor = est.parent_estimate_id.stack_factor or 1.0

    # ----------------------------------------------------------------- Discount
    discount_type = fields.Selection(
        [("percent", "Percentage (%)"), ("fixed", "Fixed Amount")],
        string="Discount Type", readonly=True, copy=False,
    )
    discount_value = fields.Float(string="Discount Value", readonly=True, copy=False)
    discount_reason = fields.Text(string="Discount Reason", readonly=True, copy=False)
    discount_reference = fields.Char(
        string="Discount Reference", readonly=True, copy=False
    )
    discount_attachment_ids = fields.Many2many(
        "ir.attachment", "cost_estimate_discount_attachment_rel",
        "estimate_id", "attachment_id",
        string="Discount Documents", readonly=True, copy=False,
    )
    discount_user_id = fields.Many2one(
        "res.users", string="Discount Approved By", readonly=True, copy=False
    )
    discount_date = fields.Date(string="Discount Date", readonly=True, copy=False)
    discount_amount = fields.Monetary(
        string="Discount Amount", compute="_compute_discount", store=True,
        currency_field="currency_id",
    )
    final_price = fields.Monetary(
        string="Final Price", compute="_compute_discount", store=True,
        currency_field="currency_id",
        help="Consolidated total minus the approved discount. This is the "
             "headline price presented to the client.",
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
        string="Labour (Pre-Development)", compute="_compute_build_effort",
        store=True, currency_field="currency_id",
    )
    dev_catalog_cost = fields.Monetary(
        string="Development Catalog", compute="_compute_build_effort",
        store=True, currency_field="currency_id",
    )
    stack_adjustment = fields.Monetary(
        string="Stack Productivity Adjustment", compute="_compute_build_effort",
        store=True, currency_field="currency_id",
        help="(Labour + Dev Catalog) x (Productivity Factor - 1). Negative for "
             "a more productive stack, positive for a more effort-heavy one. On a "
             "sub-module the factor is inherited from the parent project.",
    )
    build_effort = fields.Monetary(
        string="Build Effort", compute="_compute_build_effort", store=True,
        currency_field="currency_id",
        help="Labour + Development Catalog + Stack Productivity Adjustment. "
             "This is the incremental figure a sub-module contributes to its parent.",
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
    @api.depends("scope", "duration_months", "tech_variance", "architecture",
                 "estimate_type")
    def _compute_flat_factors(self):
        ICP = self.env["ir.config_parameter"].sudo()
        scope_map = {
            "small": _f(ICP.get_param("%s.scope_small" % PARAM, 1000)),
            "medium": _f(ICP.get_param("%s.scope_medium" % PARAM, 2500)),
            "large": _f(ICP.get_param("%s.scope_large" % PARAM, 5000)),
        }
        tv_map = {
            "level1": _f(ICP.get_param("%s.tech_level1" % PARAM, 1000)),
            "level2": _f(ICP.get_param("%s.tech_level2" % PARAM, 2500)),
            "level3": _f(ICP.get_param("%s.tech_level3" % PARAM, 4500)),
        }
        arch_map = {
            "monolith": _f(ICP.get_param("%s.arch_monolith" % PARAM, 200)),
            "layered": _f(ICP.get_param("%s.arch_layered" % PARAM, 300)),
            "client_server": _f(ICP.get_param("%s.arch_client_server" % PARAM, 350)),
            "hybrid": _f(ICP.get_param("%s.arch_hybrid" % PARAM, 500)),
            "microkernel": _f(ICP.get_param("%s.arch_microkernel" % PARAM, 600)),
            "soa": _f(ICP.get_param("%s.arch_soa" % PARAM, 700)),
            "event_driven": _f(ICP.get_param("%s.arch_event_driven" % PARAM, 800)),
            "serverless": _f(ICP.get_param("%s.arch_serverless" % PARAM, 900)),
            "microservices": _f(ICP.get_param("%s.arch_microservices" % PARAM, 1000)),
            "space_based": _f(ICP.get_param("%s.arch_space_based" % PARAM, 1200)),
        }
        monthly_rate = _f(ICP.get_param("%s.monthly_rate" % PARAM, 800))
        for est in self:
            # A sub-module never carries the shared one-time flat costs; they
            # are accounted on the parent project.
            if est.estimate_type == "sub_module":
                est.scope_cost = 0.0
                est.duration_cost = 0.0
                est.tech_variance_cost = 0.0
                est.architecture_cost = 0.0
                continue
            est.scope_cost = scope_map.get(est.scope, 0.0)
            est.duration_cost = est.duration_months * monthly_rate
            est.tech_variance_cost = tv_map.get(est.tech_variance, 0.0)
            est.architecture_cost = arch_map.get(est.architecture, 0.0)

    @api.depends("stack_id", "stack_id.productivity_factor", "estimate_type",
                 "parent_estimate_id.stack_factor")
    def _compute_stack_factor(self):
        for est in self:
            # A sub-module inherits its parent's productivity factor so its
            # effort is calibrated identically to the rest of the project, even
            # though the Technology Stack field itself is hidden on the child.
            if est.estimate_type == "sub_module" and est.parent_estimate_id:
                est.stack_factor = est.parent_estimate_id.stack_factor or 1.0
            else:
                est.stack_factor = est.stack_id.productivity_factor or 1.0

    @api.depends("labor_line_ids.amount", "dev_line_ids.amount", "stack_factor")
    def _compute_build_effort(self):
        for est in self:
            labor = sum(est.labor_line_ids.mapped("amount"))
            dev = sum(est.dev_line_ids.mapped("amount"))
            factor = est.stack_factor or 1.0
            est.labor_cost = labor
            est.dev_catalog_cost = dev
            # Stack productivity scales the build effort (Labour + Dev Catalog).
            est.stack_adjustment = (labor + dev) * (factor - 1.0)
            est.build_effort = labor + dev + est.stack_adjustment

    @api.depends("child_estimate_ids.build_effort")
    def _compute_child_rollup(self):
        for est in self:
            kids = est.child_estimate_ids
            est.child_count = len(kids)
            est.child_build_total = sum(kids.mapped("build_effort"))

    @api.depends("component_ids")
    def _compute_has_components(self):
        for est in self:
            est.component_count = len(est.component_ids)
            est.has_components = bool(est.component_ids)

    def _compute_parent_count(self):
        for est in self:
            est.parent_count = len(est.parent_component_ids)

    @api.depends(
        "build_effort",
        "child_build_total",
        "markup_line_ids.amount",
        "markup_line_ids.is_recurring",
        "tech_variance_cost",
        "architecture_cost",
        "license_cost",
        "scope_cost",
        "duration_cost",
        "contingency_percent",
        "estimate_type",
    )
    def _compute_totals(self):
        ICP = self.env["ir.config_parameter"].sudo()
        rounding = _f(ICP.get_param("%s.rounding" % PARAM, 100)) or 100.0
        for est in self:
            is_sub = est.estimate_type == "sub_module"
            # On a sub-module the shared one-time costs are nil; only the build
            # effort counts and it rolls up into the parent.
            if is_sub:
                est.tdc = est.build_effort
                est.markup_one_time = 0.0
                est.maintenance_annual = 0.0
                est.subtotal_one_time = est.build_effort
                est.contingency_amount = 0.0
                est.total_one_time = est.build_effort
                est.grand_total = math.ceil(est.build_effort / rounding) * rounding
                continue
            # Independent project: its own build effort PLUS every linked
            # sub-module's build effort feed the TDC, so the markups (which sit
            # on TDC) and the contingency are applied ONCE over the consolidated
            # build - never re-charged per sub-module.
            est.tdc = (
                    est.build_effort
                    + est.child_build_total
                    + est.tech_variance_cost
                    + est.license_cost
                    + est.architecture_cost
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

    @api.depends(
        "total_one_time",
        "maintenance_annual",
        "component_ids.allocated_capex",
        "component_ids.allocated_opex",
    )
    def _compute_consolidation(self):
        ICP = self.env["ir.config_parameter"].sudo()
        rounding = _f(ICP.get_param("%s.rounding" % PARAM, 100)) or 100.0
        for est in self:
            est.components_capex = sum(est.component_ids.mapped("allocated_capex"))
            est.components_opex = sum(est.component_ids.mapped("allocated_opex"))
            est.consolidated_capex = est.total_one_time + est.components_capex
            est.consolidated_opex = est.maintenance_annual + est.components_opex
            raw = est.consolidated_capex + est.consolidated_opex
            est.consolidated_total = math.ceil(raw / rounding) * rounding

    @api.depends(
        "consolidated_total", "discount_type", "discount_value"
    )
    def _compute_discount(self):
        for est in self:
            base = est.consolidated_total
            if est.discount_type == "percent":
                amount = base * (est.discount_value / 100.0)
            elif est.discount_type == "fixed":
                amount = est.discount_value
            else:
                amount = 0.0
            amount = max(0.0, min(amount, base))
            est.discount_amount = amount
            est.final_price = base - amount

    @api.depends("consolidated_total", "optimistic_pct", "pessimistic_pct")
    def _compute_risk_band(self):
        for est in self:
            likely = est.consolidated_total
            est.optimistic_total = likely * (1 - est.optimistic_pct / 100.0)
            est.pessimistic_total = likely * (1 + est.pessimistic_pct / 100.0)
            est.expected_total = (
                                         est.optimistic_total + 4 * likely + est.pessimistic_total
                                 ) / 6.0

    @api.depends("final_price", "approved_amount")
    def _compute_variance(self):
        for est in self:
            est.variance = est.final_price - est.approved_amount

    # ================================================== Parent / child guards
    @api.constrains("estimate_type", "parent_estimate_id", "child_estimate_ids")
    def _check_parent_link(self):
        for est in self:
            if est.estimate_type == "sub_module":
                if not est.parent_estimate_id:
                    raise ValidationError(_(
                        "Choose the Parent Project for '%s'. A sub-module must "
                        "belong to an independent project.", est.display_name))
                if est.parent_estimate_id == est:
                    raise ValidationError(_(
                        "An estimate cannot be a sub-module of itself."))
                if est.parent_estimate_id.estimate_type == "sub_module":
                    raise ValidationError(_(
                        "'%(parent)s' is itself a sub-module. Only one level of "
                        "nesting is allowed - a sub-module's parent must be an "
                        "independent project.",
                        parent=est.parent_estimate_id.display_name))
                if est.child_estimate_ids:
                    raise ValidationError(_(
                        "'%s' already has its own sub-modules, so it cannot "
                        "itself become a sub-module.", est.display_name))
            elif est.parent_estimate_id:
                raise ValidationError(_(
                    "An independent project cannot have a Parent Project. Set "
                    "the Estimate Type to 'Sub-Module of a Project' first, or "
                    "clear the parent."))

    @api.onchange("estimate_type")
    def _onchange_estimate_type(self):
        if self.estimate_type == "independent":
            self.parent_estimate_id = False

    def action_view_children(self):
        """Open the sub-module estimates linked to this project."""
        self.ensure_one()
        return {
            "name": _("Linked Sub-Modules"),
            "type": "ir.actions.act_window",
            "res_model": "cost.estimate",
            "view_mode": "tree,form",
            "domain": [("parent_estimate_id", "=", self.id)],
            "context": {
                "default_estimate_type": "sub_module",
                "default_parent_estimate_id": self.id,
                "default_partner_id": self.partner_id.id,
            },
        }

    def action_open_parent(self):
        """Open the parent project of this sub-module."""
        self.ensure_one()
        return {
            "name": _("Parent Project"),
            "type": "ir.actions.act_window",
            "res_model": "cost.estimate",
            "view_mode": "form",
            "res_id": self.parent_estimate_id.id,
        }

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
                est.approved_amount = est.final_price
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
        baseline instead of a blank sheet.

        Guarded against double-loading: if both the Labour (Pre-Development)
        and Development Drivers sections already contain at least one line,
        the estimator must clear them first before loading again. This keeps
        a single click idempotent and protects any manual edits the user may
        have already made on top of a previously loaded template.
        """
        self.ensure_one()
        if self.state != "draft":
            raise UserError(_("Templates can only be loaded on a draft estimate."))
        if self.labor_line_ids and self.dev_line_ids:
            raise UserError(_(
                "The standard template has already been loaded on this "
                "estimate: both the Labour (Pre-Development) and "
                "Development Drivers sections already contain lines.\n\n"
                "To load it again, first delete all existing lines in both "
                "sections, then click 'Load Standard Template' again."
            ))
        self._load_standard_labor()
        self._load_catalog_lines()
        if not self.markup_line_ids:
            self.markup_line_ids = self._default_markup_commands()
        return True

    def _load_standard_labor(self):
        """(Re)build the standard labour phases. Always replaces any
        existing labour lines instead of appending, so this method is
        idempotent no matter how many times it is invoked."""
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
        # (5, 0, 0) clears any existing labour lines before the fresh set is
        # created, so this can never silently pile up duplicates.
        commands = [(5, 0, 0)]
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
        """(Re)build the development-driver lines from the catalog. Always
        replaces any existing dev lines instead of appending, so this method
        is idempotent no matter how many times it is invoked."""
        # (5, 0, 0) clears any existing dev-driver lines before the fresh
        # set is created, so this can never silently pile up duplicates.
        commands = [(5, 0, 0)]
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

    def action_open_discount_wizard(self):
        """Launch the discount wizard so a justified discount can be applied."""
        self.ensure_one()
        return {
            "name": _("Apply Discount"),
            "type": "ir.actions.act_window",
            "res_model": "cost.estimate.discount.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_estimate_id": self.id,
                "default_discount_type": self.discount_type or "percent",
                "default_discount_value": self.discount_value or 0.0,
            },
        }

    def action_remove_discount(self):
        """Clear an applied discount (audited in chatter)."""
        self.ensure_one()
        if not self.discount_amount and not self.discount_type:
            return
        self.message_post(body=_(
            "<b>Discount removed.</b> Previous discount amount: %(amt)s."
        ) % {"amt": self.discount_amount})
        self.write({
            "discount_type": False,
            "discount_value": 0.0,
            "discount_reason": False,
            "discount_reference": False,
            "discount_attachment_ids": [(5, 0, 0)],
            "discount_user_id": False,
            "discount_date": False,
        })

    def _all_sub_estimates(self):
        """Return every estimate reachable as a (transitive) sub-module of
        these records, used to guard against circular roll-ups."""
        seen = self.env["cost.estimate"]
        frontier = self.mapped("component_ids.sub_estimate_id")
        while frontier:
            new = frontier - seen
            seen |= new
            frontier = new.mapped("component_ids.sub_estimate_id")
        return seen

    def action_view_parents(self):
        """Open the main estimates that roll this one in as a sub-module."""
        self.ensure_one()
        mains = self.parent_component_ids.mapped("main_estimate_id")
        return {
            "name": _("Used In"),
            "type": "ir.actions.act_window",
            "res_model": "cost.estimate",
            "view_mode": "tree,form",
            "domain": [("id", "in", mains.ids)],
        }

    # ----------------------------------------------------- Sample data loader
    # Curated from OdooMates' free Odoo 17 modules (github.com/odoomates/odooapps).
    _ODOOMATES_SAMPLES = [
        ("Full Accounting Kit (om_account_accountant)", "Full Accounting Kit", "large"),
        ("Accounting PDF Reports (accounting_pdf_reports)", "Accounting PDF Reports", "medium"),
        ("Assets Management (om_account_asset)", "Assets Management", "medium"),
        ("Bank Statement Import (om_account_bank_statement_import)", "Bank Statement Import", "medium"),
        ("Budget Management (om_account_budget)", "Budget Management", "medium"),
        ("Accounting Daily Reports (om_account_daily_reports)", "Accounting Daily Reports", "small"),
        ("Payment Follow-up Management (om_account_followup)", "Payment Follow-up", "small"),
        ("Data Remove (om_data_remove)", "Data Remove Tool", "small"),
        ("Fiscal Year (om_fiscal_year)", "Fiscal Year", "small"),
        ("Odoo Payroll (om_hr_payroll)", "Payroll", "large"),
        ("Payroll Accounting (om_hr_payroll_account)", "Payroll Accounting", "medium"),
        ("Recurring Payments (om_recurring_payments)", "Recurring Payments", "small"),
    ]

    @api.model
    def _sample_profile(self, tier, rate):
        ccr, flat, tog = "count_complexity_rate", "flat", "toggle"
        if tier == "small":
            params = dict(scope="small", duration_months=2.0,
                          tech_variance="level1", contingency_percent=5.0)
            labor = [("Requirement & Analysis", 1, 6, rate)]
            dev = [
                ("Transactional Tables", ccr, 4, 4, 10, False),
                ("Processes & Logic", ccr, 4, 4, 10, False),
                ("UI Screens / Views", ccr, 5, 3, 15, False),
                ("QWeb / PDF Reports", flat, 2, 0, 300, False),
            ]
        elif tier == "large":
            params = dict(scope="large", duration_months=7.0,
                          tech_variance="level2", contingency_percent=12.0)
            labor = [("Requirement & Analysis", 2, 18, rate),
                     ("Design", 1, 10, rate)]
            dev = [
                ("Transactional Tables", ccr, 16, 6, 10, False),
                ("Processes & Logic", ccr, 14, 6, 10, False),
                ("UI Screens / Views", ccr, 22, 6, 15, False),
                ("Reports & Analytics", ccr, 12, 5, 100, False),
                ("Accounting / HR Integration", flat, 3, 0, 1000, False),
                ("RBAC Security", tog, 0, 0, 750, True),
            ]
        else:  # medium
            params = dict(scope="medium", duration_months=4.0,
                          tech_variance="level1", contingency_percent=10.0)
            labor = [("Requirement & Analysis", 1, 12, rate),
                     ("Design", 1, 6, rate)]
            dev = [
                ("Transactional Tables", ccr, 8, 5, 10, False),
                ("Processes & Logic", ccr, 8, 5, 10, False),
                ("UI Screens / Views", ccr, 12, 5, 15, False),
                ("Reports & Analytics", ccr, 6, 4, 100, False),
                ("Accounting Integration", flat, 2, 0, 1000, False),
            ]
        return params, labor, dev

    @api.model
    def action_load_odoomates_samples(self):
        """Create one cost estimate per OdooMates free Odoo 17 module.

        Idempotent: modules already present (matched by title) are skipped, so
        the action can be re-run safely.
        """
        Rate = self.env["cost.estimation.rate"]
        re_role = Rate.search([("code", "=", "RE")], limit=1) or Rate.search([], limit=1)
        rate = re_role.hourly_rate if re_role else 15.0
        stack = self.env.ref(
            "software_cost_estimation.stack_odoo", raise_if_not_found=False
        )
        partner = self.env["res.partner"].search(
            [("name", "=", "OdooMates")], limit=1
        )
        if not partner:
            partner = self.env["res.partner"].create({
                "name": "OdooMates", "comment": "Free Odoo modules publisher",
            })
        created = self.env["cost.estimate"]
        for title, system_name, tier in self._ODOOMATES_SAMPLES:
            if self.search_count([("title", "=", title), ("is_sample", "=", True)]):
                continue
            params, labor, dev = self._sample_profile(tier, rate)
            labor_cmds = [
                (0, 0, {
                    "sequence": (i + 1) * 10, "name": name,
                    "role_id": re_role.id if re_role else False,
                    "responsible": re_role.name if re_role else "",
                    "persons": persons, "working_days": days,
                    "hours_per_day": 8.0, "hourly_rate": r,
                })
                for i, (name, persons, days, r) in enumerate(labor)
            ]
            dev_cmds = [
                (0, 0, {
                    "sequence": (i + 1) * 10, "name": name, "calc_method": method,
                    "count": count, "complexity": complexity or 1.0,
                    "unit_rate": rate_, "included": included,
                })
                for i, (name, method, count, complexity, rate_, included)
                in enumerate(dev)
            ]
            vals = dict(
                params,
                title=title, system_name=system_name, is_sample=True,
                partner_id=partner.id,
                stack_id=stack.id if stack else False,
                labor_line_ids=labor_cmds, dev_line_ids=dev_cmds,
            )
            created |= self.create(vals)
        return created

    def action_print_report(self):
        return self.env.ref(
            "software_cost_estimation.action_report_cost_estimate"
        ).report_action(self)
