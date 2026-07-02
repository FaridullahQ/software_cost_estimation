# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

PARAM = "software_cost_estimation"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sce_load_odoomates_demo = fields.Boolean(
        string="Load OdooMates Sample Project Estimations",
        config_parameter="%s.load_odoomates_demo" % PARAM,
        help="When enabled and saved, the system is populated with ready-made "
        "cost estimations for OdooMates' free Odoo 17 modules "
        "(Full Accounting Kit, Payroll, Assets, Budget, and more). Runs once; "
        "use the button to (re)load on demand.",
    )

    # Default factor amounts below are calibrated as starting points for the
    # Afghanistan software market (USD-denominated, ~$15/hr labour rate). They
    # are deliberately conservative - tune them from your own delivery history.
    sce_monthly_rate = fields.Float(
        string="Cost per Project Month",
        config_parameter="%s.monthly_rate" % PARAM, default=800.0,
    )
    sce_rounding = fields.Float(
        string="Round Grand Total Up To",
        config_parameter="%s.rounding" % PARAM, default=100.0,
    )
    sce_scope_small = fields.Float(
        string="Scope Cost - Small",
        config_parameter="%s.scope_small" % PARAM, default=1000.0,
    )
    sce_scope_medium = fields.Float(
        string="Scope Cost - Medium",
        config_parameter="%s.scope_medium" % PARAM, default=2500.0,
    )
    sce_scope_large = fields.Float(
        string="Scope Cost - Large",
        config_parameter="%s.scope_large" % PARAM, default=5000.0,
    )
    sce_tech_level1 = fields.Float(
        string="Tech Variance - Level One",
        config_parameter="%s.tech_level1" % PARAM, default=1000.0,
    )
    sce_tech_level2 = fields.Float(
        string="Tech Variance - Level Two",
        config_parameter="%s.tech_level2" % PARAM, default=2500.0,
    )
    sce_tech_level3 = fields.Float(
        string="Tech Variance - Level Three",
        config_parameter="%s.tech_level3" % PARAM, default=4500.0,
    )
    sce_arch_monolith = fields.Float(
        string="Architecture - Monolith",
        config_parameter="%s.arch_monolith" % PARAM, default=200.0,
    )
    sce_arch_layered = fields.Float(
        string="Architecture - Layered (N-Tier)",
        config_parameter="%s.arch_layered" % PARAM, default=300.0,
    )
    sce_arch_client_server = fields.Float(
        string="Architecture - Client-Server",
        config_parameter="%s.arch_client_server" % PARAM, default=350.0,
    )
    sce_arch_hybrid = fields.Float(
        string="Architecture - Modular Monolith (Hybrid)",
        config_parameter="%s.arch_hybrid" % PARAM, default=500.0,
    )
    sce_arch_microkernel = fields.Float(
        string="Architecture - Microkernel / Plug-in",
        config_parameter="%s.arch_microkernel" % PARAM, default=600.0,
    )
    sce_arch_soa = fields.Float(
        string="Architecture - Service-Oriented (SOA)",
        config_parameter="%s.arch_soa" % PARAM, default=700.0,
    )
    sce_arch_event_driven = fields.Float(
        string="Architecture - Event-Driven",
        config_parameter="%s.arch_event_driven" % PARAM, default=800.0,
    )
    sce_arch_serverless = fields.Float(
        string="Architecture - Serverless (FaaS)",
        config_parameter="%s.arch_serverless" % PARAM, default=900.0,
    )
    sce_arch_microservices = fields.Float(
        string="Architecture - Micro Services",
        config_parameter="%s.arch_microservices" % PARAM, default=1000.0,
    )
    sce_arch_space_based = fields.Float(
        string="Architecture - Space-Based",
        config_parameter="%s.arch_space_based" % PARAM, default=1200.0,
    )

    def set_values(self):
        res = super().set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        already = ICP.get_param("%s.odoomates_demo_loaded" % PARAM)
        if self.sce_load_odoomates_demo and not already:
            self.env["cost.estimate"].sudo().action_load_odoomates_samples()
            ICP.set_param("%s.odoomates_demo_loaded" % PARAM, "1")
        return res

    def action_load_odoomates_samples(self):
        """Explicit button: (re)load the OdooMates sample estimations now."""
        self.ensure_one()
        created = self.env["cost.estimate"].sudo().action_load_odoomates_samples()
        self.env["ir.config_parameter"].sudo().set_param(
            "%s.odoomates_demo_loaded" % PARAM, "1"
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": _("Sample estimations loaded"),
                "message": _("%s new OdooMates module estimation(s) added.")
                % len(created),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
