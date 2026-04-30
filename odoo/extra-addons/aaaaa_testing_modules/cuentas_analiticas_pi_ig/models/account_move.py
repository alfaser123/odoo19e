from odoo import models, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _validate_analytic_percentages(self):
        _logger.warning('Entrando a _validate_analytic_percentages')
        for move in self:
            for line in move.line_ids:
                _logger.warning('Revisando línea: %s', line.name)
                if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                    total_percent = sum(line.analytic_distribution.values())
                    _logger.warning('Total porcentaje analítico: %s', total_percent)
                    if total_percent > 100:
                        _logger.error('Porcentaje supera 100%% en línea: %s', line.name)
                        raise ValidationError(
                            'La suma de los porcentajes asignados a cuentas analíticas en la línea "%s" supera el 100%%.' % (line.name or '')
                        )

    @api.constrains('line_ids')
    def _check_analytic_percentages(self):
        _logger.info('Entrando a constraint _check_analytic_percentages')
        self._validate_analytic_percentages()

    def create(self, vals):
        _logger.info('Entrando a create de account.move')
        record = super(AccountMove, self).create(vals)
        record._validate_analytic_percentages()
        return record

    def write(self, vals):
        _logger.warning('Entrando a write de account.move')
        res = super(AccountMove, self).write(vals)
        # Refuerza la validación: si se modifican líneas o campos relacionados, siempre valida
        self._validate_analytic_percentages()
        return res
