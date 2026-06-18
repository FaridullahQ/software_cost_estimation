# -*- coding: utf-8 -*-
from odoo import api, fields, models
from .cost_estimation_markup_template import MARKUP_BASE_SELECTION


class CostEstimateMarkup(models.Model):
    _name = "cost.estimate.markup"
    _description = "Estimate Markup Line"
    _order = "sequence, id"

    estimate_id = fields.Many2one(
        "cost.estimate", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    percent = fields.Float(string="Percent (%)", required=True)
    base = fields.Selection(
        MARKUP_BASE_SELECTION, string="Applied On", required=True, default="tdc",
        help="Which estimate pool this percentage applies to in Automatic "
        "mode. Ignored when the estimate's Markup Base Mode is Manual.",
    )
    is_recurring = fields.Boolean(string="Recurring (Annual OpEx)")

    # Mirror of the parent's mode so the view can drive readonly per row.
    base_mode = fields.Selection(
        related="estimate_id.markup_base_mode", string="Base Mode",
        readonly=True,
    )

    base_amount = fields.Monetary(
        string="Base",
        compute="_compute_base_amount",
        inverse="_inverse_base_amount",
        store=True,
        readonly=False,
        currency_field="currency_id",
        help="Automatic mode: derived from the selected pool. "
        "Manual mode: the single base typed on the estimate (editable here "
        "too - typing it on any line updates the shared base for all lines).",
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

    @api.depends(
        "base",
        "estimate_id.markup_base_mode",
        "estimate_id.manual_markup_base",
        "estimate_id.tdc",
        "estimate_id.dev_catalog_cost",
        "estimate_id.labor_cost",
    )
    def _compute_base_amount(self):
        for line in self:
            est = line.estimate_id
            if est.markup_base_mode == "manual":
                line.base_amount = est.manual_markup_base
            else:
                base_map = {
                    "tdc": est.tdc,
                    "dev": est.dev_catalog_cost,
                    "labor": est.labor_cost,
                }
                line.base_amount = base_map.get(line.base, 0.0)

    def _inverse_base_amount(self):
        """In Manual mode, typing a base on any line becomes the single shared
        base on the estimate, which then propagates back to every line."""
        for line in self:
            if line.estimate_id.markup_base_mode == "manual":
                line.estimate_id.manual_markup_base = line.base_amount

    @api.depends("percent", "base_amount")
    def _compute_amount(self):
        for line in self:
            line.amount = line.base_amount * (line.percent / 100.0)
