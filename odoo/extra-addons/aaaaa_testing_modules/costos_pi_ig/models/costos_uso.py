# -*- coding: utf-8 -*-
from odoo import models, fields

class CostosUso(models.Model):
    _name = 'costos.uso'
    _description = 'Usos Costos'

    name = fields.Char(string='Nombre', required=True)
    descripcion = fields.Char(string='Descripción')
    analytic_distribution_ids = fields.One2many('account.analytic.distribution.model', 'costos_uso_id', string='Modelos de Distribución Analítica')