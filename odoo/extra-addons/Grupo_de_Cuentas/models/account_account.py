# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json
import logging

_logger = logging.getLogger(__name__)

class AccountAccount(models.Model):
    _inherit = 'account.account'

    group_hierarchy_ids = fields.Many2many(
        'account.group',
        string='Grupo Jerárquico',
        compute='_compute_group_hierarchy',
        store=False
    )

    @api.depends('group_id')
    def _compute_group_hierarchy(self):
        for account in self:
            hierarchy = []
            group = account.group_id
            while group:
                hierarchy.insert(0, group.id)
                group = group.parent_id
            account.group_hierarchy_ids = [(6, 0, hierarchy)]

    def _get_nivel_from_length(self, length):
        if length == 1:
            return 1
        elif length == 2:
            return 2
        elif length == 4:
            return 3
        elif length == 6:
            return 4
        elif length == 8:
            return 5
        elif length == 10:
            return 6
        elif length == 12:
            return 7
        return 0

    def _check_group_exists_for_level(self, vals, is_create=True):
        _logger.info('ENTRANDO A VALIDACION CUENTA   vals  %s',vals)
        vals_list = vals if isinstance(vals, list) else [vals]
        for v in vals_list:
            company_id = v.get('company_id')
            if not company_id and not is_create:
                if hasattr(self, 'company_id') and getattr(self, 'company_id', False):
                    company_id = self.company_id.id
                elif hasattr(self, 'company_ids') and getattr(self, 'company_ids', False):
                    company_id = self.company_ids[0].id if self.company_ids else False
            code_store = v.get('code_store') or (self.code_store if not is_create else False)
            code = v.get('code') or (self.code if not is_create else False)
            group_id = v.get('group_id') or (self.group_id.id if not is_create else False)
            _logger.info('VALIDACION CUENTA: company_id=%s, code_store=%s, code=%s, group_id=%s', company_id, code_store, code, group_id)
            if not company_id or not code_store or not code or not group_id:
                _logger.warning('Faltan datos para validar grupo/cuenta')
                continue
            if isinstance(code_store, str):
                try:
                    code_store = json.loads(code_store)
                except Exception as e:
                    _logger.error('Error parseando code_store: %s', e)
                    continue
            _logger.info('DEBUG code_store valor: %r, tipo: %s', code_store, type(code_store))
            if isinstance(code_store, dict):
                code_store_val = code_store.get(str(company_id))
            else:
                code_store_val = code_store
            if not code_store_val:
                _logger.warning('No se encontró code_store para la empresa')
                continue
            nivel_cuenta = self._get_nivel_from_length(len(str(code_store_val)))
            group = self.env['account.group'].browse(group_id)
            _logger.info('Grupo encontrado: id=%s, nivel=%s, prefix=%s', group.id, group.nivel, group.code_prefix_start)
            if not group or not group.exists():
                raise ValidationError(u"Debe seleccionar un grupo válido para la cuenta")
            if group.nivel != (nivel_cuenta - 1):
                raise ValidationError(u"No existe grupo actual para la cuenta  %s y company %s, por favor cree primero el grupo" % (code, company_id)  )
            # Validar que exista grupo padre de nivel N-1 si el nivel es mayor a 1
            if nivel_cuenta > 1:
                parent_group = group.parent_id
                if not parent_group or not parent_group.exists():
                    raise ValidationError(u" Debe existir un GRUPO padre de nivel %s para crear una cuenta de nivel %s" % (nivel_cuenta-1, nivel_cuenta))
                if group.nivel != (nivel_cuenta - 1):
                    raise ValidationError(u"El grupo actual del padre es de nivel %s, debe ser de nivel %s para crear una cuenta de nivel %s" % (group.nivel,nivel_cuenta-1, nivel_cuenta))
            prefix = group.code_prefix_start or ''
            if not code.startswith(prefix):
                raise ValidationError(u"El código de la cuenta (%s) no coincide con el prefijo del grupo padre (%s)" % (code, prefix))

    # @api.model
    @api.model_create_multi
    def create(self, vals):
        _logger.info("[Grupo_de_Cuentas] Entrando al método create de account.account con vals: %s", vals)
        self._check_group_exists_for_level(vals, is_create=True)
        return super(AccountAccount, self).create(vals)

    def write(self, vals):
        _logger.info("[Grupo_de_Cuentas] Entrando al método write de account.account con vals: %s", vals)
        self._check_group_exists_for_level(vals, is_create=False)
        return super(AccountAccount, self).write(vals)
