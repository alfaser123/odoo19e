import json
import logging
from odoo import models, api, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_analytic_split = fields.Boolean(
        string="Línea de Distribución", 
        default=False, 
        help="Indica si esta línea fue creada automáticamente por distribución analítica"
    )

class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_line_ids = fields.One2many(
        'account.move.line',
        'move_id',
        string='Invoice lines',
        copy=False,
        domain=[
            ('display_type', 'in', ('product', 'line_section', 'line_subsection', 'line_note')),
            ('is_analytic_split', '=', False)
        ]
    )

    def _validate_analytic_percentages(self):
        for move in self:
            for line in move.line_ids:
                if hasattr(line, 'analytic_distribution') and line.analytic_distribution:
                    if isinstance(line.analytic_distribution, dict):
                        total_percent = sum(float(x) for x in line.analytic_distribution.values())
                        if total_percent > 100.0:
                           pass
                           # raise ValidationError('La suma de los porcentajes asignados en "%s" supera el 100%%.' % (line.name or ''))

    @api.constrains('line_ids')
    def _check_analytic_percentages(self):
        self._validate_analytic_percentages()
