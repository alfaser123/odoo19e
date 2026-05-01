from odoo import models, fields, api

class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    costos_uso_id = fields.Many2one('costos.uso', string='Uso de Costo')
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cuenta Analítica'
    )

    @api.model
    def _get_default_search_domain_vals(self):
        vals = super()._get_default_search_domain_vals()
        vals['costos_uso_id'] = False
        return vals

    # Add any extra behavior if necessary