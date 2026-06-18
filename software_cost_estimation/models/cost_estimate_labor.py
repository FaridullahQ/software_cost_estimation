# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CostEstimateLabor(models.Model):
    _name = "cost.estimate.labor"
    _description = "Estimate Labour Line"
    _order = "sequence, id"

    estimate_id = fields.Many2one(
        "cost.estimate", required=True, ondelete="cascade"
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string="Activity / Phase", required=True)
    role_id = fields.Many2one("cost.estimation.rate", string="Role")
    responsible = fields.Char(string="Responsible Individual(s)")
    persons = fields.Integer(string="Persons", default=1)
    working_days = fields.Float(string="Working Days", default=0.0)
    hours_per_day = fields.Float(string="Hours / Day", default=8.0)
    hourly_rate = fields.Monetary(
        string="Hourly Rate", currency_field="currency_id"
    )
    person_hours = fields.Float(
        string="Person-Hours",
        compute="_compute_amounts",
        store=True,
        help="Total team hours = persons x working days x hours/day. "
        "Example: 2 persons x 30 days x 8h = 480 person-hours. "
        "Cost = person-hours x rate (head-count is applied once).",
    )
    amount = fields.Monetary(
        string="Labour Cost",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        related="estimate_id.currency_id", store=True, readonly=True
    )

    @api.depends("persons", "working_days", "hours_per_day", "hourly_rate")
    def _compute_amounts(self):
        for line in self:
            # person_hours already aggregates the whole team. The rate is per
            # hour, so cost = person_hours * rate. Head-count is applied ONCE.
            line.person_hours = (
                line.persons * line.working_days * line.hours_per_day
            )
            line.amount = line.person_hours * line.hourly_rate

    @api.onchange("role_id")
    def _onchange_role_id(self):
        for line in self:
            if line.role_id:
                line.hourly_rate = line.role_id.hourly_rate
                if not line.responsible:
                    line.responsible = line.role_id.name
