# -*- coding: utf-8 -*-
from odoo import fields, models

MARKUP_BASE_SELECTION = [
    ("tdc", "Total Development Cost (TDC)"),
    ("dev", "Development Catalog Only"),
    ("labor", "Labour Only"),
]


class CostEstimationMarkupTemplate(models.Model):
    _name = "cost.estimation.markup.template"
    _description = "Estimation Markup Template"
    _order = "sequence, id"

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    percent = fields.Float(string="Percent (%)", required=True)
    base = fields.Selection(
        MARKUP_BASE_SELECTION, string="Applied On", required=True, default="tdc"
    )
    is_recurring = fields.Boolean(
        string="Recurring (Annual OpEx)",
        help="If set, this markup is treated as a recurring annual cost "
        "(e.g. maintenance) rather than part of the one-time build cost.",
    )
    active = fields.Boolean(default=True)
    note = fields.Char()
