from odoo import models, fields

class AccountAnalyticDistributionLine(models.Model):
    _name = 'account.analytic.distribution.line'
    _description = 'Analytic Distribution Line (custom)'

    account_account_id = fields.Many2one('account.account', string='Account')
    # Puedes agregar aquí otros campos relacionados a la línea de distribución