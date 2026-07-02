# -*- coding: utf-8 -*-
from markupsafe import Markup, escape
from odoo import fields, models, _
from odoo.exceptions import UserError


class CostEstimateDiscountWizard(models.TransientModel):
    """Apply a justified discount to an estimate's final price.

    A discount can never be applied silently: a reason is always mandatory and
    at least one of a reference or an official supporting document must be
    provided. The justification is written onto the estimate and posted to the
    chatter (with the attachments) for a permanent audit trail.
    """

    _name = "cost.estimate.discount.wizard"
    _description = "Apply Discount"

    estimate_id = fields.Many2one(
        "cost.estimate", string="Estimate", required=True
    )
    currency_id = fields.Many2one(
        related="estimate_id.currency_id", readonly=True
    )
    price_before = fields.Monetary(
        related="estimate_id.consolidated_total", string="Price Before Discount",
        currency_field="currency_id", readonly=True,
    )

    discount_type = fields.Selection(
        [("percent", "Percentage (%)"), ("fixed", "Fixed Amount")],
        string="Discount Type", default="percent", required=True,
    )
    discount_value = fields.Float(string="Discount Value", required=True)

    reason = fields.Text(
        string="Reason / Justification", required=True,
        help="Why is this discount being granted? This is mandatory.",
    )
    reference = fields.Char(
        string="Reference",
        help="Approval memo number, contract clause, ticket, etc.",
    )
    attachment_ids = fields.Many2many(
        "ir.attachment", string="Official Document(s)",
        help="Scan or PDF of the approval / authorising document.",
    )

    def action_apply(self):
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            raise UserError(_("A reason is required to apply a discount."))
        if not self.reference and not self.attachment_ids:
            raise UserError(_(
                "Provide a reference or attach an official document to justify "
                "the discount."
            ))
        if self.discount_value <= 0:
            raise UserError(_("The discount value must be greater than zero."))
        if self.discount_type == "percent" and self.discount_value > 100:
            raise UserError(_("A percentage discount cannot exceed 100%."))
        if self.discount_type == "fixed" and self.discount_value > self.price_before:
            raise UserError(_(
                "A fixed discount cannot exceed the price before discount "
                "(%(price)s).", price=self.price_before,
            ))

        est = self.estimate_id
        # Re-bind the uploaded attachments onto the estimate for permanence.
        if self.attachment_ids:
            self.attachment_ids.write({
                "res_model": "cost.estimate",
                "res_id": est.id,
            })
        est.write({
            "discount_type": self.discount_type,
            "discount_value": self.discount_value,
            "discount_reason": self.reason,
            "discount_reference": self.reference,
            "discount_attachment_ids": [(6, 0, self.attachment_ids.ids)],
            "discount_user_id": self.env.user.id,
            "discount_date": fields.Date.context_today(self),
        })
        if self.discount_type == "percent":
            shown = _("%(v).2f%%", v=self.discount_value)
        else:
            shown = "%s %s" % (self.discount_value, est.currency_id.symbol or "")
        est.message_post(
            body=Markup(
                "<b>Discount applied:</b> {shown} "
                "(amount {amt}).<br/>"
                "<b>Reason:</b> {reason}<br/>"
                "<b>Reference:</b> {ref}"
            ).format(
                shown=shown,
                amt=est.discount_amount,
                reason=escape(self.reason),
                ref=escape(self.reference) if self.reference else _("(document attached)"),
            ),
            attachment_ids=self.attachment_ids.ids,
        )
        return {"type": "ir.actions.act_window_close"}