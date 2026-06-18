# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CostEstimationRate(models.Model):
    _name = "cost.estimation.rate"
    _description = "Estimation Rate Card (Role / Hourly Rate)"
    _order = "sequence, name"

    name = fields.Char(string="Role", required=True, translate=True)
    code = fields.Char(string="Code")
    sequence = fields.Integer(default=10)
    hourly_rate = fields.Monetary(
        string="Hourly Rate", required=True, currency_field="currency_id"
    )
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )
    active = fields.Boolean(default=True)
    note = fields.Char(string="Note")

    def name_get(self):
        result = []
        for rec in self:
            label = rec.name
            if rec.hourly_rate:
                label = "%s (%s/h)" % (rec.name, rec.hourly_rate)
            result.append((rec.id, label))
        return result
