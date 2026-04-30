import json
from odoo import models, fields, api

class AnalyticMixin(models.AbstractModel):
    _inherit = 'analytic.mixin'

    # Campo paralelo que guarda el mapeo { 'analytic_account_id': account.account.id }
    # Odoo espera que analytic_distribution tenga puros floats.
    analytic_distribution_accounts = fields.Json(string="Cuentas Contables Mapeadas")
    