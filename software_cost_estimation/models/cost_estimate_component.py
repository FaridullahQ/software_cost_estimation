# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CostEstimateComponent(models.Model):
    """Roll-up link: a standalone sub-module estimate consumed by a main one.

    Each line attaches an existing *sub-module* estimate to a *main* estimate
    at a configurable allocation percentage (default 100%). This lets a shared
    component be split across several mains (e.g. 50% here, 50% elsewhere).

    The sub-module's fully-loaded CapEx and OpEx are converted to the main's
    currency and scaled by the allocation. The main does NOT re-apply its own
    markups/contingency on top of these, because each sub-module is already a
    complete, self-contained estimate.
    """

    _name = "cost.estimate.component"
    _description = "Estimate Sub-Module Roll-up"
    _order = "sequence, id"

    main_estimate_id = fields.Many2one(
        "cost.estimate", string="Main Estimate", required=True,
        ondelete="cascade", index=True,
    )
    sub_estimate_id = fields.Many2one(
        "cost.estimate", string="Sub-Module Estimate", required=True,
        ondelete="restrict",
        help="An existing standalone estimate to roll into the main one.",
    )
    sequence = fields.Integer(default=10)
    allocation_percent = fields.Float(
        string="Allocation %", default=100.0, required=True,
        help="Portion of this sub-module's cost charged to this main estimate. "
        "Use < 100% when the component is shared across several mains.",
    )

    # ---- mirror of the sub-module for display ----
    sub_system_name = fields.Char(
        related="sub_estimate_id.system_name", string="System / Product",
        readonly=True,
    )
    sub_title = fields.Char(
        related="sub_estimate_id.title", string="Sub Title", readonly=True
    )
    sub_state = fields.Selection(
        related="sub_estimate_id.state", string="Sub Status", readonly=True
    )
    # FIX: store=True is required on related Many2one fields. Without it, Odoo
    # 17's onchange snapshot diff calls convert_to_read() on a field whose
    # comodel resolves as '_unknown', causing:
    #   AttributeError: '_unknown' object has no attribute 'id'
    sub_partner_id = fields.Many2one(
        related="sub_estimate_id.partner_id", string="Sub Client",
        readonly=True, store=True,
    )
    sub_grand_total = fields.Monetary(
        related="sub_estimate_id.grand_total", string="Sub Grand Total",
        currency_field="sub_currency_id", readonly=True,
    )
    sub_currency_id = fields.Many2one(
        related="sub_estimate_id.currency_id", string="Sub Currency",
        readonly=True, store=True,
    )

    # ---- allocated, converted to the MAIN currency ----
    allocated_capex = fields.Monetary(
        string="Allocated CapEx", compute="_compute_allocated", store=True,
        currency_field="currency_id",
    )
    allocated_opex = fields.Monetary(
        string="Allocated OpEx (Annual)", compute="_compute_allocated",
        store=True, currency_field="currency_id",
    )
    allocated_total = fields.Monetary(
        string="Allocated Year-1", compute="_compute_allocated", store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="main_estimate_id.currency_id", store=True, readonly=True
    )

    @api.depends(
        "allocation_percent",
        "sub_estimate_id.total_one_time",
        "sub_estimate_id.maintenance_annual",
        "sub_estimate_id.currency_id",
        "main_estimate_id.currency_id",
        "main_estimate_id.estimate_date",
    )
    def _compute_allocated(self):
        for line in self:
            sub = line.sub_estimate_id
            main = line.main_estimate_id
            factor = (line.allocation_percent or 0.0) / 100.0
            capex = sub.total_one_time
            opex = sub.maintenance_annual
            if sub and main and sub.currency_id and main.currency_id \
                    and sub.currency_id != main.currency_id:
                date = main.estimate_date or fields.Date.context_today(line)
                company = main.company_id or self.env.company
                capex = sub.currency_id._convert(
                    capex, main.currency_id, company, date
                )
                opex = sub.currency_id._convert(
                    opex, main.currency_id, company, date
                )
            line.allocated_capex = capex * factor
            line.allocated_opex = opex * factor
            line.allocated_total = (capex + opex) * factor

    @api.constrains("main_estimate_id", "sub_estimate_id", "allocation_percent")
    def _check_link(self):
        for line in self:
            if line.allocation_percent < 0 or line.allocation_percent > 100:
                raise ValidationError(
                    _("Allocation percentage must be between 0 and 100.")
                )
            if line.sub_estimate_id == line.main_estimate_id:
                raise ValidationError(
                    _("An estimate cannot be a sub-module of itself.")
                )
            # walk the sub's own component tree; the main must not appear,
            # otherwise we'd create a circular roll-up.
            if line.main_estimate_id in line.sub_estimate_id._all_sub_estimates():
                raise ValidationError(_(
                    "Circular roll-up detected: '%(sub)s' already includes "
                    "'%(main)s' (directly or indirectly).",
                    sub=line.sub_estimate_id.display_name,
                    main=line.main_estimate_id.display_name,
                ))