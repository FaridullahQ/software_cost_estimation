# -*- coding: utf-8 -*-
from odoo import fields, models, _


class CostEstimateRejectWizard(models.TransientModel):
    _name = "cost.estimate.reject.wizard"
    _description = "Reject Estimate"

    estimate_id = fields.Many2one(
        "cost.estimate", string="Estimate", required=True
    )
    reason = fields.Text(string="Rejection Reason", required=True)

    def action_reject(self):
        self.ensure_one()
        self.estimate_id.message_post(
            body=_("<b>Estimate rejected.</b><br/>Reason: %s") % self.reason
        )
        self.estimate_id.write({"state": "rejected"})
        return {"type": "ir.actions.act_window_close"}
