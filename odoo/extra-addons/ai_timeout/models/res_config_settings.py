from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ai_request_timeout_seconds = fields.Integer(
        string="AI request timeout (seconds)",
        config_parameter="ai.request_timeout_seconds",
        default=90,
        help="Default timeout for Odoo AI HTTP calls when the caller does not set one explicitly.",
    )
