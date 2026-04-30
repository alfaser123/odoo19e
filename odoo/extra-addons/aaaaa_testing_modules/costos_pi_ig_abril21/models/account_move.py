from odoo import models, api, fields, Command
import json
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        _logger.info(f"== CREATE MOVE == context: {self.env.context.get('skip_analytic_split')} == vals_list: {vals_list}")
        moves = super(AccountMove, self.with_context(skip_analytic_split=True)).create(vals_list)
        if not self.env.context.get('skip_analytic_split'):
            moves._split_analytic_financial_lines()
        return moves

    def write(self, vals):
        _logger.info(f"== WRITE MOVE == ids: {self.ids} context: {self.env.context.get('skip_analytic_split')} == vals: {vals.keys()}")
        res = super(AccountMove, self.with_context(skip_analytic_split=True)).write(vals)
        if not self.env.context.get('skip_analytic_split'):
            if 'invoice_line_ids' in vals or 'line_ids' in vals:
                self._split_analytic_financial_lines()
        return res

    def _split_analytic_financial_lines(self):
        # Cachear modelos analiticos por si hay asignacion automatica sin widget
        dist_models = self.env['account.analytic.distribution.model'].search([('analytic_distribution', '!=', False)])
        
        for move in self:
            if move.state != 'draft':
                continue
            
            commands = []
            
            # 0. Limpiar fraccionamientos anteriores para evitar duplicados al editar
            for old_line in move.line_ids.filtered(lambda l: l.is_analytic_split):
                commands.append(Command.delete(old_line.id))
            
            lines_to_remove = set()
            
            # Iteramos sobre las lineas NORMALES (is_analytic_split=False) para fraccionarlas
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product' and l.analytic_distribution and not l.is_analytic_split):
                distribution = line.analytic_distribution
                accounts_mapping = line.analytic_distribution_accounts
                
                if isinstance(accounts_mapping, str):
                    try:
                        accounts_mapping = json.loads(accounts_mapping)
                    except Exception:
                        accounts_mapping = {}
                
                if not accounts_mapping:
                    for m in dist_models:
                        if m.analytic_distribution == distribution and m.analytic_distribution_accounts:
                            accounts_mapping = m.analytic_distribution_accounts
                            if isinstance(accounts_mapping, str):
                                try:
                                    accounts_mapping = json.loads(accounts_mapping)
                                except Exception:
                                    accounts_mapping = {}
                            break
                
                if not accounts_mapping:
                    # En lugar de hacer continue, asumimos diccionario vacio
                    # para que use la misma cuenta contable original si no hay mapeo.
                    accounts_mapping = {}
                
                if len(distribution) == 1:
                    key = list(distribution.keys())[0]
                    mapped_acc_id = accounts_mapping.get(key)
                    if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id:
                        chk_id = int(mapped_acc_id['id'])
                    elif mapped_acc_id:
                        chk_id = int(mapped_acc_id)
                    else:
                        chk_id = line.account_id.id

                    if chk_id == line.account_id.id and float(distribution[key]) == 100.0:
                        continue
                
                if line.id not in lines_to_remove:
                    lines_to_remove.add(line.id)
                    company_curr = line.company_id.currency_id or move.company_id.currency_id
                    line_curr = line.currency_id or move.currency_id
                    
                    # 1. REVERSA CONTABLE: Anular impacto de la línea original en apuntes
                    # Asi la factura original cuenta el subtotal pero los apuntes se balancean a 0 con esto.
                    reverse_vals = line.copy_data()[0]
                    
                    # Limpiamos tax_ids de la reversa y de las fracciones para no duplicar impuestos en Odoo
                    if 'tax_ids' in reverse_vals:
                        reverse_vals['tax_ids'] = False
                    
                    # rev_balance = -line.balance
                    # rev_amount_curr = -line.amount_currency
                    
                    # reverse_vals.update({
                        # 'name': f"Distribución (Reversa original): {line.name}",
                        # 'account_id': line.account_id.id,
                        # 'analytic_distribution': False,
                        # 'analytic_distribution_accounts': False,
                        # 'is_analytic_split': True,
                        # 'display_type': 'product',
                        # 'quantity': -line.quantity,
                        # 'price_unit': line.price_unit,
                        # 'balance': rev_balance,
                        # 'amount_currency': rev_amount_curr,
                        # 'debit': rev_balance if rev_balance > 0 else 0.0,
                        # 'credit': -rev_balance if rev_balance < 0 else 0.0,
                    # })
                    # commands.append(Command.create(reverse_vals))
                    
                    line.update({
                        # 'name': f"Distribución (Reversa original): {line.name}",
                        # 'account_id': line.account_id.id,
                        # 'analytic_distribution': False,
                        # 'analytic_distribution_accounts': False,
                        # 'is_analytic_split': True,
                        # 'display_type': 'product',
                        # 'quantity': -line.quantity,
                        # 'price_unit': line.price_unit,
                        'balance':  0.0,
                        'debit': 0.0,
                        'credit': 0.0,
                     })
                    
                    
                    
                    
                    
                    # 2. SUB-LINEAS CONTABLES DE LA DISTRIBUCION
                    for dict_key, percentage in distribution.items():
                        mapped_acc_id = accounts_mapping.get(dict_key)
                        
                        if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id:
                            fin_account_id = int(mapped_acc_id['id'])
                        elif mapped_acc_id:
                            fin_account_id = int(mapped_acc_id)
                        else:
                            fin_account_id = line.account_id.id
                            
                        ratio = float(percentage) / 100.0
                        
                        copy_vals = line.copy_data()[0]
                        if 'tax_ids' in copy_vals:
                            copy_vals['tax_ids'] = False
                            
                        new_mapping = {dict_key: mapped_acc_id} if mapped_acc_id else {}
                        
                        cur_balance = company_curr.round(line.balance * ratio)
                        cur_amount_curr = line_curr.round(line.amount_currency * ratio)
                        
                        copy_vals.update({
                            'name': line.name,
                            'quantity': line.quantity,
                            'price_unit': line.price_unit * ratio,
                            'account_id': fin_account_id,
                            'analytic_distribution': {str(dict_key): 100.0},
                            'analytic_distribution_accounts': json.dumps(new_mapping),
                            'is_analytic_split': True,
                            'display_type': 'product',
                            'balance': cur_balance,
                            'amount_currency': cur_amount_curr,
                            'debit': cur_balance if cur_balance > 0 else 0.0,
                            'credit': -cur_balance if cur_balance < 0 else 0.0,
                        })
                        commands.append(Command.create(copy_vals))

            if commands:
                move.with_context(skip_analytic_split=True, check_move_validity=False).write({
                    'line_ids': commands
                })
