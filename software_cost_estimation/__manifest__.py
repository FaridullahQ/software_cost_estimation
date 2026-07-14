# -*- coding: utf-8 -*-
{
    "name": "Software Cost Estimation",
    "version": "17.0.7.1.1",
    "category": "Services/Project",
    "summary": "Parametric cost estimation for information-system / software "
               "development projects (driver-based, rate-card calibrated).",
    "description": """
Software Cost Estimation
========================

A driver-based (Function-Point style) parametric estimator for software /
information-system projects, modelled on the Systems Development Directorate
cost-estimation workbook and re-engineered as a fully dynamic Odoo application.

Key capabilities
----------------
* Effort-based labour costing (persons x days x hours x rate) -- corrected so
  head-count is never double-counted.
* Reusable cost-driver catalog (transactional tables, interfaces, integration,
  authentication, authorization, migration, localization, ...) with three
  calculation methods: count x complexity x rate, flat unit price, and toggle.
* Rate card (role -> hourly rate) used as calibration data.
* Configurable factor markups (Project Management, Testing, Training,
  Documentation, Maintenance) applied to a selectable base.
* Technology-stack calibration: a productivity factor per stack (Odoo,
  Spring Boot, ASP.NET Core, Django, ...) scales build effort so the same
  functional size costs correctly across stacks.
* Sub-module roll-up: consolidate several standalone sub-module estimates
  into one main estimate at a configurable allocation %, with multi-currency
  conversion and circular-reference protection.
* Parent / sub-module projects: mark an estimate as a partial sub-module of a
  parent project. The sub-module carries only its own build effort (Labour +
  Development) and inherits the parent's productivity factor; shared one-time
  costs (scope, duration, architecture, technology, stack, license, markups,
  contingency, discount) are defined and charged once on the parent, so its
  effort folds into the parent's TDC before markups and contingency - no
  double counting.
* Justified discounts: a manager applies a percentage or fixed discount to
  the final price only with a mandatory reason plus a reference and/or an
  official supporting document, fully recorded in the chatter.
* One-click sample data: load ready-made cost estimations for OdooMates' free
  Odoo 17 modules from Settings, to explore the system with realistic figures.
* CapEx vs OpEx separation: one-time build cost vs recurring annual maintenance.
* Risk handling: contingency reserve plus optimistic / most-likely / pessimistic
  three-point (PERT) band.
* Interactive OWL dashboard (Chart.js): KPIs, pipeline, cost structure and a
  project deep-dive, filterable by year, client, status, scope, architecture,
  estimate type and estimator.
* Ten system-architecture styles (Monolith, Layered, Client-Server, Modular
  Monolith, Microkernel, SOA, Event-Driven, Serverless, Micro Services,
  Space-Based), each with a configurable fixed cost. Default flat factors and
  a round-up increment of 100 are pre-calibrated as Afghanistan-market starting
  points, all tunable in Settings.
* Draft -> Under Review -> Approved workflow with chatter and activities.
* Professional QWeb PDF estimate report.
""",
    # Author / publisher
    "author": "Faridullah Qaderi",
    "website": "https://www.linkedin.com/in/faridullah-qaderi-114405330",
    "maintainer": "FOITECH - Digital Solutions",
    # Support contact
    "support": "faridullahqaderi54@gmail.com",
    # Free & open-source license
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/cost_estimation_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "data/cost_estimation_rate_data.xml",
        "data/cost_estimation_stack_data.xml",
        "data/cost_estimation_catalog_data.xml",
        "data/cost_estimation_markup_template_data.xml",
        "views/cost_estimation_rate_views.xml",
        "views/cost_estimation_stack_views.xml",
        "views/cost_estimation_catalog_views.xml",
        "views/cost_estimate_views.xml",
        "wizard/cost_estimate_wizard_views.xml",
        "views/res_config_settings_views.xml",
        "report/cost_estimate_report.xml",
        "report/cost_estimate_report_templates.xml",
        "views/cost_estimation_menus.xml",
        "views/cost_estimate_dashboard.xml",
    ],
    "demo": [
        "demo/cost_estimate_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "software_cost_estimation/static/src/dashboard/dashboard.scss",
            "software_cost_estimation/static/src/dashboard/dashboard.js",
            "software_cost_estimation/static/src/dashboard/dashboard.xml",
        ],
    },
    "application": True,
    "installable": True,
    "images": [
        "static/description/banner.png",
        "static/description/dashboard-1.png",
        "static/description/estimate-dev-drivers.png",
        "static/description/sizing-advisor.png",
        "static/description/risk-negotiation.png",
        "static/description/print-estimate.png",
    ],
}
