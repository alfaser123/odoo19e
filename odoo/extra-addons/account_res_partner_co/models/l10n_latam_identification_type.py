
from odoo import api, fields, models
from odoo.exceptions import ValidationError

class L10nLatamIdentificationType(models.Model):
    _inherit = 'l10n_latam.identification.type'

    mysql_data_id = fields.Integer(string='MySQL Data ID', index=True)


    @api.constrains('mysql_data_id')
    def _check_mysql_data_id_unique(self):
            for rec in self:
                if rec.mysql_data_id:
                    other = self.search([
                        ('id', '!=', rec.id),
                        ('mysql_data_id', '=', rec.mysql_data_id),
                    ], limit=1)
                    if other:
                        raise ValidationError('El MySQL Data ID ya existe en otro registro.')