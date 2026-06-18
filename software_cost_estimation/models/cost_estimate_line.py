# -*- coding: utf-8 -*-
from odoo import api, fields, models
from .cost_estimation_catalog import CATEGORY_SELECTION, CALC_METHOD_SELECTION


class CostEstimateLine(models.Model):
    _name = "cost.estimate.line"
    _description = "Estimate Development Driver Line"
    _order = "sequence, id"

    estimate_id = fields.Many2one(
        "cost.estimate", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    catalog_id = fields.Many2one("cost.estimation.catalog", string="Cost Driver")
    name = fields.Char(string="Description", required=True)
    category = fields.Selection(
        CATEGORY_SELECTION, string="Category", default="other"
    )
    calc_method = fields.Selection(
        CALC_METHOD_SELECTION,
        string="Method",
        required=True,
        default="count_complexity_rate",
        help="How this line's amount is computed:\n"
        "- Count x Complexity x Rate: parametric sizing for items that vary in "
        "difficulty (tables, processes, interfaces, reports). "
        "Example: 15 tables x complexity 8 x $10 = $1,200.\n"
        "- Count x Unit Price: flat per-unit items (integrations, users, "
        "languages). Example: 4 integrations x $1,000 = $4,000.\n"
        "- Toggle: a one-off capability that is either in or out (SSO, "
        "biometric auth, a migration step). Tick 'Included' to add its price.",
    )
    count = fields.Float(
        string="Count", default=0.0,
        help="How many of this item. Used by the 'Count x ...' methods; "
        "ignored for Toggle.",
    )
    complexity = fields.Float(
        string="Complexity (1-10)", default=1.0,
        help="Relative effort weight, only for 'Count x Complexity x Rate'. "
        "Rule of thumb: 1-3 = simple CRUD (e.g. a lookup table), "
        "4-6 = moderate logic/validation (e.g. an approval process), "
        "7-10 = heavy logic with many states or edge cases "
        "(e.g. a payroll calculation engine).",
    )
    included = fields.Boolean(
        string="Included",
        help="For the Toggle method: tick to include this capability and add "
        "its unit rate to the estimate.",
    )
    unit_rate = fields.Monetary(
        string="Unit Rate", currency_field="currency_id"
    )
    amount = fields.Monetary(
        string="Amount",
        compute="_compute_amount",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="estimate_id.currency_id", store=True, readonly=True
    )
    note = fields.Char(string="Note")

    @api.depends("calc_method", "count", "complexity", "included", "unit_rate")
    def _compute_amount(self):
        for line in self:
            if line.calc_method == "count_complexity_rate":
                line.amount = line.count * line.complexity * line.unit_rate
            elif line.calc_method == "flat":
                line.amount = line.count * line.unit_rate
            elif line.calc_method == "toggle":
                line.amount = line.unit_rate if line.included else 0.0
            else:
                line.amount = 0.0

    @api.onchange("catalog_id")
    def _onchange_catalog_id(self):
        for line in self:
            if line.catalog_id:
                line.name = line.catalog_id.name
                line.category = line.catalog_id.category
                line.calc_method = line.catalog_id.calc_method
                line.complexity = line.catalog_id.default_complexity
                line.unit_rate = line.catalog_id.default_unit_rate
