from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _abc_is_supported_invoice(self):
        self.ensure_one()
        return self.move_type in ('out_invoice', 'in_invoice')

    def _abc_remove_old_generated_lines(self):
        for move in self:
            old_lines = move.line_ids.filtered(lambda l: l.abc_generated_line)
            if old_lines:
                old_lines.with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).unlink()

    def _abc_create_generated_lines(self):
        aml_obj = self.env['account.move.line']
        for move in self:
            if move.state != 'draft':
                continue
            if not move._abc_is_supported_invoice():
                continue

            vals_to_create = []
            base_lines = move.line_ids.filtered(lambda l: l._abc_is_invoice_product_line())
            for line in base_lines:
                vals_to_create.extend(line._abc_prepare_reclassification_vals())

            if vals_to_create:
                aml_obj.with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).create(vals_to_create)

    def _post(self, soft=True):
        candidate_moves = self.filtered(lambda m: m.state == 'draft' and m._abc_is_supported_invoice())

        # Limpiar y regenerar antes del posteo final
        candidate_moves._abc_remove_old_generated_lines()
        candidate_moves._abc_create_generated_lines()

        return super()._post(soft=soft)