# -*- coding: utf-8 -*-
from odoo import fields, models

PARAM = "software_cost_estimation"


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    sce_monthly_rate = fields.Float(
        string="Cost per Project Month",
        config_parameter="%s.monthly_rate" % PARAM, default=1000.0,
    )
    sce_rounding = fields.Float(
        string="Round Grand Total Up To",
        config_parameter="%s.rounding" % PARAM, default=1.0,
    )
    sce_scope_small = fields.Float(
        string="Scope Cost - Small",
        config_parameter="%s.scope_small" % PARAM, default=2000.0,
    )
    sce_scope_medium = fields.Float(
        string="Scope Cost - Medium",
        config_parameter="%s.scope_medium" % PARAM, default=4000.0,
    )
    sce_scope_large = fields.Float(
        string="Scope Cost - Large",
        config_parameter="%s.scope_large" % PARAM, default=8000.0,
    )
    sce_tech_level1 = fields.Float(
        string="Tech Variance - Level One",
        config_parameter="%s.tech_level1" % PARAM, default=2000.0,
    )
    sce_tech_level2 = fields.Float(
        string="Tech Variance - Level Two",
        config_parameter="%s.tech_level2" % PARAM, default=4000.0,
    )
    sce_tech_level3 = fields.Float(
        string="Tech Variance - Level Three",
        config_parameter="%s.tech_level3" % PARAM, default=6000.0,
    )
    sce_arch_monolith = fields.Float(
        string="Architecture - Monolith",
        config_parameter="%s.arch_monolith" % PARAM, default=500.0,
    )
    sce_arch_hybrid = fields.Float(
        string="Architecture - Hybrid (Monolith Modular)",
        config_parameter="%s.arch_hybrid" % PARAM, default=750.0,
    )
    sce_arch_microservices = fields.Float(
        string="Architecture - Micro Services",
        config_parameter="%s.arch_microservices" % PARAM, default=1000.0,
    )
