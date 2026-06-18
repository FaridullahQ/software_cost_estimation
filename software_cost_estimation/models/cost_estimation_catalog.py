# -*- coding: utf-8 -*-
from odoo import fields, models

CATEGORY_SELECTION = [
    ("data_model", "Data Model"),
    ("logic", "Processes & Logic"),
    ("integration", "Interfaces & Integration"),
    ("analytics", "Reporting & Analytics"),
    ("security", "Security (AuthN / AuthZ)"),
    ("localization", "Localization"),
    ("migration", "Data Migration"),
    ("other", "Other"),
]

CALC_METHOD_SELECTION = [
    ("count_complexity_rate", "Count x Complexity x Rate"),
    ("flat", "Count x Unit Price"),
    ("toggle", "Toggle (Included x Price)"),
]


class CostEstimationCatalog(models.Model):
    _name = "cost.estimation.catalog"
    _description = "Cost Driver Catalog"
    _order = "sequence, id"

    name = fields.Char(string="Cost Driver", required=True, translate=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        CATEGORY_SELECTION, string="Category", required=True, default="other"
    )
    calc_method = fields.Selection(
        CALC_METHOD_SELECTION,
        string="Calculation Method",
        required=True,
        default="count_complexity_rate",
        help="How the line amount is derived:\n"
        "- Count x Complexity x Rate: parametric driver (e.g. tables, processes).\n"
        "- Count x Unit Price: flat priced item (e.g. integration endpoints).\n"
        "- Toggle: a 0/1 switch multiplied by a fixed price (e.g. SSO, biometric).",
    )
    default_complexity = fields.Float(string="Default Complexity", default=1.0)
    default_unit_rate = fields.Monetary(
        string="Default Unit Rate", currency_field="currency_id"
    )
    currency_id = fields.Many2one(
        "res.currency", default=lambda self: self.env.company.currency_id
    )
    active = fields.Boolean(default=True)
    note = fields.Char(string="Guidance")
