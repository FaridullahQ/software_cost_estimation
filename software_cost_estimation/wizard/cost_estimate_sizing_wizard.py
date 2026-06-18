# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

SCOPE_SELECTION = [("small", "Small"), ("medium", "Medium"), ("large", "Large")]
TECH_SELECTION = [
    ("level1", "Level One"),
    ("level2", "Level Two"),
    ("level3", "Level Three"),
]
ARCH_SELECTION = [
    ("monolith", "Monolith"),
    ("hybrid", "Hybrid (Monolith Modular)"),
    ("microservices", "Micro Services"),
]


class CostEstimateSizingWizard(models.TransientModel):
    _name = "cost.estimate.sizing.wizard"
    _description = "Estimate Sizing Advisor"

    estimate_id = fields.Many2one(
        "cost.estimate", string="Estimate", required=True
    )

    # ---- size drivers ----
    num_entities = fields.Integer(
        string="Core Business Entities", default=0,
        help="Distinct transactional entities / tables. Example: a fleet system "
        "with Vehicle, Driver, Trip, Fuel Log, Maintenance Order = 5.",
    )
    num_modules = fields.Integer(
        string="Functional Modules", default=1,
        help="Distinct functional areas. Example: HR, Payroll, Recruitment = 3.",
    )
    num_integrations = fields.Integer(
        string="External Integrations", default=0,
        help="Other systems to connect to. Example: HR system + national ID "
        "API = 2.",
    )
    num_users = fields.Integer(
        string="Expected Users", default=0,
        help="Approximate number of end users.",
    )
    data_volume = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High")],
        string="Data Volume", default="low",
        help="Record scale. Low < 100k, Medium 100k-5M, High > 5M.",
    )

    # ---- risk / architecture drivers ----
    team_familiarity = fields.Selection(
        [("high", "High"), ("medium", "Medium"), ("low", "Low")],
        string="Team Familiarity With Stack", default="high",
        help="How experienced the team is with the planned technology.",
    )
    uses_emerging_tech = fields.Boolean(
        string="Uses Emerging Technology",
        help="AI/ML, blockchain, IoT, real-time streaming, etc.",
    )
    needs_independent_scaling = fields.Boolean(
        string="Needs Independent Scaling / Deployment",
        help="Parts of the system must scale or be released independently.",
    )
    multiple_teams = fields.Boolean(
        string="Multiple Teams in Parallel",
        help="Several teams will build different parts at the same time.",
    )

    # ---- recommendations ----
    size_score = fields.Integer(
        string="Size Score", compute="_compute_recommendation"
    )
    recommended_scope = fields.Selection(
        SCOPE_SELECTION, string="Recommended Scope",
        compute="_compute_recommendation",
    )
    recommended_tech_variance = fields.Selection(
        TECH_SELECTION, string="Recommended Tech Variance",
        compute="_compute_recommendation",
    )
    recommended_architecture = fields.Selection(
        ARCH_SELECTION, string="Recommended Architecture",
        compute="_compute_recommendation",
    )
    rationale = fields.Text(
        string="Why", compute="_compute_recommendation"
    )

    @api.depends(
        "num_entities", "num_modules", "num_integrations", "num_users",
        "data_volume", "team_familiarity", "uses_emerging_tech",
        "needs_independent_scaling", "multiple_teams",
    )
    def _compute_recommendation(self):
        for w in self:
            # ---- scope score ----
            score = w.num_entities + w.num_integrations * 2 + w.num_modules * 2
            if w.num_users > 500:
                score += 6
            elif w.num_users >= 50:
                score += 3
            if w.data_volume == "high":
                score += 4
            elif w.data_volume == "medium":
                score += 2
            w.size_score = score
            if score <= 8:
                scope = "small"
            elif score <= 20:
                scope = "medium"
            else:
                scope = "large"
            w.recommended_scope = scope

            # ---- technology variance ----
            if w.uses_emerging_tech or w.team_familiarity == "low":
                tech = "level3"
            elif w.team_familiarity == "medium":
                tech = "level2"
            else:
                tech = "level1"
            w.recommended_tech_variance = tech

            # ---- architecture ----
            if w.needs_independent_scaling or w.multiple_teams or scope == "large":
                arch = "microservices"
            elif scope == "medium" or w.num_modules >= 3:
                arch = "hybrid"
            else:
                arch = "monolith"
            w.recommended_architecture = arch

            scope_lbl = dict(SCOPE_SELECTION)[scope]
            tech_lbl = dict(TECH_SELECTION)[tech]
            arch_lbl = dict(ARCH_SELECTION)[arch]
            w.rationale = _(
                "Size score %(score)s -> %(scope)s scope "
                "(entities, integrations, modules and users weighted).\n"
                "%(tech)s technology variance based on team familiarity "
                "'%(fam)s'%(emerg)s.\n"
                "%(arch)s architecture %(arch_reason)s."
            ) % {
                "score": score,
                "scope": scope_lbl,
                "tech": tech_lbl,
                "fam": dict(w._fields["team_familiarity"].selection).get(
                    w.team_familiarity, ""
                ),
                "emerg": _(" with emerging tech") if w.uses_emerging_tech else "",
                "arch": arch_lbl,
                "arch_reason": (
                    _("because independent scaling / parallel teams / large "
                      "scope favour separate services")
                    if arch == "microservices"
                    else _("as a modular middle ground")
                    if arch == "hybrid"
                    else _("because a single small system needs no split")
                ),
            }

    def action_apply(self):
        self.ensure_one()
        self.estimate_id.write({
            "scope": self.recommended_scope,
            "tech_variance": self.recommended_tech_variance,
            "architecture": self.recommended_architecture,
        })
        self.estimate_id.message_post(
            body=_(
                "<b>Sizing Advisor applied</b> (size score %(score)s):"
                "<ul>"
                "<li>Scope: %(scope)s</li>"
                "<li>Technology Variance: %(tech)s</li>"
                "<li>Architecture: %(arch)s</li>"
                "</ul>"
            ) % {
                "score": self.size_score,
                "scope": dict(SCOPE_SELECTION)[self.recommended_scope],
                "tech": dict(TECH_SELECTION)[self.recommended_tech_variance],
                "arch": dict(ARCH_SELECTION)[self.recommended_architecture],
            }
        )
        return {"type": "ir.actions.act_window_close"}
