from odoo import models, fields, api

class journal_provision(models.Model):
    _inherit = 'account.journal'

    provision = fields.Boolean(string='Diario de Provision', default=False)
