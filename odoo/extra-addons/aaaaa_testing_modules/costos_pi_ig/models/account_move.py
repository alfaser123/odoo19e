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
            _logger.info(f"== LLAMANDO SPLIT EN CREATE PARA MOVES: {moves.ids} ==")
            moves._split_analytic_financial_lines()
        return moves

    def write(self, vals):
        _logger.info(f"== WRITE MOVE == ids: {self.ids} context: {self.env.context.get('skip_analytic_split')} == vals: {vals.keys()}")
        res = super(AccountMove, self.with_context(skip_analytic_split=True)).write(vals)
        if not self.env.context.get('skip_analytic_split'):
            if 'invoice_line_ids' in vals or 'line_ids' in vals:
                _logger.info(f"== LLAMANDO SPLIT EN WRITE PARA MOVES: {self.ids} ==")
                self._split_analytic_financial_lines()
        return res

    def _split_analytic_financial_lines(self):
        # Cachear modelos analiticos por si hay asignacion automatica sin widget
        dist_models = self.env['account.analytic.distribution.model'].search([('analytic_distribution', '!=', False)])
        
        for move in self:
            if move.state != 'draft':
                continue
            
            commands = []
            lines_to_remove = set()
            
            for line in move.invoice_line_ids.filtered(lambda l: l.display_type == 'product' and l.analytic_distribution):
                _logger.info(f"PROCESANDO LÍNEA: {line.name} | Distribution: {line.analytic_distribution} | Mapeo cuentas: {line.analytic_distribution_accounts}")
                
                distribution = line.analytic_distribution
                accounts_mapping = line.analytic_distribution_accounts
                
                if isinstance(accounts_mapping, str):
                    try:
                        accounts_mapping = json.loads(accounts_mapping)
                    except Exception:
                        accounts_mapping = {}
                
                # Si Odoo asigno la distribucion automaticamente, buscar sus cuentas financieras en el modelo
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
                    _logger.warning(f"NO HAY MAPEO para la línea {line.id}, se deja normal.")
                    continue # No hay mapeo configurado, se deja normal
                
                # Evitar recursividad y fraccionamientos innecesarios (1 sola clave al 100% que corresponde a su propia cuenta)
                if len(distribution) == 1:
                    key = list(distribution.keys())[0]
                    mapped_acc_id = accounts_mapping.get(key)
                    if mapped_acc_id and line.account_id.id == int(mapped_acc_id) and float(distribution[key]) == 100.0:
                        _logger.info(f"DISTRIBUCIÓN 100% IGUAL: Mapeo {mapped_acc_id} coincide con línea {line.account_id.id}. Ignorando.")
                        continue
                
                if line.id not in lines_to_remove:
                    _logger.info(f"LÍNEA A REEMPLAZAR ID: {line.id}")
                    lines_to_remove.add(line.id)
                    
                    for dict_key, percentage in distribution.items():
                        mapped_acc_id = accounts_mapping.get(dict_key)
                        fin_account_id = int(mapped_acc_id) if mapped_acc_id else line.account_id.id
                        ratio = float(percentage) / 100.0
                        
                        copy_vals = line.copy_data()[0]
                        new_mapping = {dict_key: mapped_acc_id} if mapped_acc_id else {}
                        
                        copy_vals.update({
                            'name': line.name,
                            'quantity': line.quantity,
                            'price_unit': line.price_unit * ratio,
                            'account_id': fin_account_id,
                            'analytic_distribution': {str(dict_key): 100.0},
                            'analytic_distribution_accounts': json.dumps(new_mapping),
                        })
                        
                        _logger.info(f"CREANDO COMANDO NEW LINE: cuenta {fin_account_id}, price {copy_vals['price_unit']}, analítico: {copy_vals['analytic_distribution']}")
                        commands.append(Command.create(copy_vals))

            if commands:
                _logger.info(f"COMANDOS GENERADOS: {len(commands)} a crear, borrando {len(lines_to_remove)} locales")
                for line_id in lines_to_remove:
                    commands.append(Command.delete(line_id))
                
                # Inyectar el contexto de guardado seguro para no ciclar el write de nuevo recursivamente
                move.with_context(skip_analytic_split=True, check_move_validity=False).write({
                    'invoice_line_ids': commands
                })