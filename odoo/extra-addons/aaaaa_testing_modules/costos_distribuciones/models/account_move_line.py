# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_is_zero, float_round


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    abc_distribution_account_map = fields.Json(
        string='Mapa cuentas contables ABC',
        copy=True,
    )

    abc_generated_line = fields.Boolean(
        string='Línea generada por ABC',
        default=False,
        copy=False,
    )

    abc_generated_role = fields.Selection([
        ('reverse', 'Reversa cuenta original'),
        ('target', 'Distribución cuenta destino'),
    ], string='Rol ABC', copy=False)

    abc_source_line_id = fields.Many2one(
        'account.move.line',
        string='Línea origen ABC',
        copy=False,
        index=True,
    )

    @api.constrains('analytic_distribution', 'abc_distribution_account_map')
    def _check_abc_distribution_account_map(self):
        for line in self:
            analytic_distribution = line.analytic_distribution or {}
            account_map = line.abc_distribution_account_map or {}

            invalid_keys = set(account_map.keys()) - set(analytic_distribution.keys())
            if invalid_keys:
                raise ValidationError(_(
                    "El mapa contable ABC contiene combinaciones analíticas que no existen en la distribución analítica."
                ))

    def _abc_is_invoice_product_line(self):
        self.ensure_one()
        return bool(
            self.move_id.move_type in ('out_invoice', 'in_invoice')
            and not self.display_type
            and not self.tax_line_id
            and not self.abc_generated_line
            and not self.exclude_from_invoice_tab
            and self.product_id
        )

    def _abc_prepare_distribution_model_vals(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id if self.partner_id else False
        return {
            'company_id': self.company_id.id or False,
            'partner_id': partner.id if partner else False,
            'partner_category_id': partner.category_id.ids if partner else [],
            'product_id': self.product_id.id or False,
            'account_prefix': (self.account_id.code or '')[:3] if self.account_id else False,
        }

    def _abc_autofill_account_map_from_model(self):
        """
        Rellena abc_distribution_account_map cuando la distribución analítica
        fue tomada automáticamente desde account.analytic.distribution.model.
        """
        if self.env.context.get('abc_skip_autofill'):
            return

        model_obj = self.env['account.analytic.distribution.model']
        for line in self.filtered(lambda l: l.move_id.state == 'draft' and l._abc_is_invoice_product_line()):
            payload = model_obj._abc_get_distribution_with_accounts(
                line._abc_prepare_distribution_model_vals()
            )
            model_distribution = payload.get('distribution') or {}
            model_account_map = payload.get('account_map') or {}

            if model_distribution and (line.analytic_distribution or {}) == model_distribution:
                line.with_context(abc_skip_autofill=True).write({
                    'abc_distribution_account_map': model_account_map,
                })

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._abc_autofill_account_map_from_model()
        return lines

    def write(self, vals):
        res = super().write(vals)
        trigger_fields = {
            'analytic_distribution',
            'partner_id',
            'product_id',
            'account_id',
            'company_id',
        }
        if (
            not self.env.context.get('abc_skip_autofill')
            and 'abc_distribution_account_map' not in vals
            and trigger_fields.intersection(vals.keys())
        ):
            self._abc_autofill_account_map_from_model()
        return res

    def _abc_has_valid_distribution_accounts(self):
        self.ensure_one()
        distribution = self.analytic_distribution or {}
        account_map = self.abc_distribution_account_map or {}
        return bool(distribution and account_map and any(account_map.get(k) for k in distribution.keys()))

    def _abc_get_target_slices(self):
        """
        Devuelve una lista de dicts:
        [
            {
                'distribution_key': '12,45',
                'percentage': 60.0,
                'account_id': 123,
            },
            ...
        ]
        """
        self.ensure_one()
        distribution = self.analytic_distribution or {}
        account_map = self.abc_distribution_account_map or {}

        result = []
        for key, percentage in distribution.items():
            if key == '__update__':
                continue
            account_id = account_map.get(key)
            if not account_id:
                continue
            result.append({
                'distribution_key': key,
                'percentage': percentage,
                'account_id': account_id,
            })
        return result

    def _abc_prepare_reclassification_vals(self):
        """
        Genera:
        - 1 línea reversa sobre la cuenta original del producto
        - N líneas destino distribuidas por porcentaje

        No toca impuestos, CxC, CxP.
        """
        self.ensure_one()

        if not self._abc_is_invoice_product_line():
            return []

        if not self._abc_has_valid_distribution_accounts():
            return []

        currency = self.currency_id or self.move_id.currency_id or self.company_currency_id
        company_currency = self.company_currency_id
        precision = company_currency.rounding

        if float_is_zero(self.balance, precision_rounding=precision):
            return []

        slices = self._abc_get_target_slices()
        if not slices:
            return []

        total_percentage = sum(x['percentage'] for x in slices)
        if float_is_zero(total_percentage, precision_rounding=0.0001):
            return []

        vals_list = []

        # Línea de reversa: anula el impacto de la cuenta original del producto
        reverse_vals = {
            'move_id': self.move_id.id,
            'name': _('[ABC REV] %s') % (self.name or self.product_id.display_name or '/'),
            'account_id': self.account_id.id,
            'partner_id': self.partner_id.id,
            'product_id': self.product_id.id,
            'quantity': 0.0,
            'price_unit': 0.0,
            'debit': self.credit,
            'credit': self.debit,
            'amount_currency': -self.amount_currency,
            'currency_id': currency.id if currency else False,
            'company_id': self.company_id.id,
            'exclude_from_invoice_tab': True,
            'analytic_distribution': False,
            'abc_distribution_account_map': False,
            'abc_generated_line': True,
            'abc_generated_role': 'reverse',
            'abc_source_line_id': self.id,
        }
        vals_list.append(reverse_vals)

        # Líneas destino: redistribuyen el subtotal sobre cuentas contables destino
        distributed_balance_sum = 0.0
        distributed_amount_currency_sum = 0.0

        for index, item in enumerate(slices, start=1):
            pct = item['percentage'] / 100.0
            target_account = self.env['account.account'].browse(item['account_id'])

            if index < len(slices):
                piece_balance = float_round(self.balance * pct, precision_rounding=precision)
                piece_amount_currency = currency.round(self.amount_currency * pct) if currency else 0.0
            else:
                # última línea absorbe redondeo
                piece_balance = self.balance - distributed_balance_sum
                piece_amount_currency = self.amount_currency - distributed_amount_currency_sum

            distributed_balance_sum += piece_balance
            distributed_amount_currency_sum += piece_amount_currency

            debit = piece_balance if piece_balance > 0 else 0.0
            credit = -piece_balance if piece_balance < 0 else 0.0

            vals_list.append({
                'move_id': self.move_id.id,
                'name': _('[ABC %s%%] %s') % (item['percentage'], self.name or self.product_id.display_name or '/'),
                'account_id': target_account.id,
                'partner_id': self.partner_id.id,
                'product_id': self.product_id.id,
                'quantity': 0.0,
                'price_unit': 0.0,
                'debit': debit,
                'credit': credit,
                'amount_currency': piece_amount_currency,
                'currency_id': currency.id if currency else False,
                'company_id': self.company_id.id,
                'exclude_from_invoice_tab': True,
                'analytic_distribution': False,
                'abc_distribution_account_map': False,
                'abc_generated_line': True,
                'abc_generated_role': 'target',
                'abc_source_line_id': self.id,
            })

        return vals_list