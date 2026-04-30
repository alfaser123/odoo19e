from odoo import models, fields

class AccountAnalyticDistributionModel(models.Model):
    _inherit = 'account.analytic.distribution.model'

    account_account_id = fields.Many2one('account.account', string='Cuenta Contable')
    driver_distribution_id = fields.Many2one('driver.distribution', string='Driver de Distribución')
