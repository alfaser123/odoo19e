# -*- coding: utf-8 -*-
from odoo import _, models, fields, api
from odoo.exceptions import UserError


class AccountGroup(models.Model):
    _inherit = 'account.group'

    nivel = fields.Integer(
        string='Nivel',
        compute='_compute_nivel',
        store=True
    )

    def write(self, vals):
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info('[Grupo_de_Cuentas][AccountGroup.write] Tipo de vals: %s, valor: %r', type(vals), vals)
        vals_list = vals if isinstance(vals, list) else [vals]
        for v in vals_list:
            code_prefix = v.get('code_prefix_start')
            _logger.info('[Grupo_de_Cuentas][AccountGroup.write] code_prefix: %r', code_prefix)
            if code_prefix:
                account = self.env['account.account'].search([
                    ('code', '=', code_prefix),
                    ('active', '=', True)
                ], limit=1)
                if account:
                    _logger.warning('[Grupo_de_Cuentas][AccountGroup.write] Ya existe una cuenta activa con ese código: %s', code_prefix)
                    raise UserError(_(
                        'Este prefijo de grupo pertenece a una cuenta regular del plan de cuentas, si desea crear este grupo, contacte a su administrador para hacer un traslado de saldos a otra cuenta.'))
        return super(AccountGroup, self).write(vals)

    @api.depends('code_prefix_start')
    def _compute_nivel(self):
        for group in self:
            code = group.code_prefix_start or ''
            length = len(code)
            if length == 1:
                group.nivel = 1
            elif length == 2:
                group.nivel = 2
            elif length == 4:
                group.nivel = 3
            elif length == 6:
                group.nivel = 4
            elif length == 8:
                group.nivel = 5
            elif length == 10:
                group.nivel = 6
            elif length == 12:
                group.nivel = 7
            else:
                group.nivel = 0


    @api.model_create_multi
    def create(self, vals_list):
        import logging
        _logger = logging.getLogger(__name__)

        _logger.info('[Grupo_de_Cuentas][AccountGroup.create] vals_list: %r', vals_list)

        for vals in vals_list:
            code_prefix = vals.get('code_prefix_start')
            _logger.info('[Grupo_de_Cuentas][AccountGroup.create] code_prefix: %r', code_prefix)

            if code_prefix:
                account = self.env['account.account'].search([
                    ('code', '=', code_prefix),
                    ('active', '=', True)
                ], limit=1)

                if account:
                    raise UserError(_(
                        'Este prefijo de grupo pertenece a una cuenta regular del plan de cuentas...'))

        return super().create(vals_list)