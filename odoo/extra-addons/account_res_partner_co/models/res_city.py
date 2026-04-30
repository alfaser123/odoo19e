# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

# _logger = logging.getLogger(__name__)

class ResCity(models.Model):
    _name = 'res.city'

    code = fields.Char(string='Code')
    name = fields.Char(string='Name')
    state_id = fields.Many2one('res.country.state', string='State', required=True)
