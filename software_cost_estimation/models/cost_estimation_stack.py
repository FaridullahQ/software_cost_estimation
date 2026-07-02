# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CostEstimationStack(models.Model):
    """Technology stack catalog.

    Each stack carries a *productivity factor* that scales the build effort
    (Labour + Development Catalog) so the same functional size maps to a
    different cost per technology. A factor below 1.0 means the stack is more
    productive than the baseline (less hand-written code); above 1.0 means it
    needs more effort for the same scope.

    Calibration guidance (baseline = 1.0, hand-built backend + SPA):
        * Odoo / low-code ERP ............... 0.55 - 0.65
        * Django / Rails / Laravel .......... 0.75 - 0.85
        * ASP.NET Core / Spring Boot + UI ... 0.90 - 1.00
        * Bespoke micro-services / native ... 1.10 - 1.30
    These are starting points; tune them from your own delivery history.
    """

    _name = "cost.estimation.stack"
    _description = "Technology Stack (Productivity Calibration)"
    _order = "sequence, name"

    name = fields.Char(string="Technology Stack", required=True, translate=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(default=10)
    productivity_factor = fields.Float(
        string="Productivity Factor",
        default=1.0,
        required=True,
        help="Multiplier applied to Labour + Development Catalog. "
        "1.0 = baseline. Below 1.0 = more productive stack (e.g. Odoo 0.6); "
        "above 1.0 = more effort for the same scope (e.g. bespoke 1.2).",
    )
    active = fields.Boolean(default=True)
    note = fields.Char(string="Guidance")

    @api.depends("name", "productivity_factor")
    def _compute_display_name(self):
        for rec in self:
            if rec.productivity_factor and rec.productivity_factor != 1.0:
                rec.display_name = "%s (x%.2f)" % (rec.name, rec.productivity_factor)
            else:
                rec.display_name = rec.name
