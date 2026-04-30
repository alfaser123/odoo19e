# -*- coding: utf-8 -*-
from odoo import models, fields

class DriverDistribution(models.Model):
    _name = 'driver.distribution'
    _description = 'Controladores de Distribución'

    codigo = fields.Char(string='Código', required=True)
    valor = fields.Char(string='Valor')

    def name_get(self):
        result = []
        for record in self:
            name = record.codigo or ''
            result.append((record.id, name))
        return result