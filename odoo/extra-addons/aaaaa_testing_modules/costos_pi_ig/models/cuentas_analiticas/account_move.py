import json
import logging
from odoo import models, api, fields
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = []
        for vals in vals_list:
            dist = vals.get('analytic_distribution')
            mapping = vals.get('analytic_distribution_accounts') or '{}'
            
            # Solo particionar si la lÃnea tiene distribuciÃ³n y es de un tipo que queramos separar (normalmente product o la ausencia de uno explÃcito)
            is_product = vals.get('display_type', 'product') == 'product'
            
            if is_product and dist:
                if isinstance(dist, str):
                    try:
                        dist = json.loads(dist)
                    except Exception:
                        pass
                
                if isinstance(mapping, str):
                    try:
                        mapping = json.loads(mapping)
                    except Exception:
                        mapping = {}

                # Si logramos interpretar la distribuciÃ³n y mapping
                if isinstance(dist, dict) and mapping and len(dist) >= 1:
                    _logger.info('Interceptando lÃnea para partir. Mapeo: %s, DistribuciÃ³n: %s', mapping, dist)
                    price_unit = vals.get('price_unit', 0.0)
                    
                    for dict_key, percentage in dist.items():
                        mapped_acc_id = mapping.get(str(dict_key)) or mapping.get(dict_key)
                        
                        ratio = float(percentage) / 100.0
                        split_vals = dict(vals)
                        
                        # Escalar los valores econÃ³micos al porcentaje (ratio) de esta lÃnea
                        for val_key in ['price_unit', 'debit', 'credit', 'amount_currency', 'balance']:
                            if val_key in split_vals and split_vals[val_key]:
                                split_vals[val_key] = split_vals[val_key] * ratio
                                
                        if mapped_acc_id:
                            acc_id_val = mapped_acc_id['id'] if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id else mapped_acc_id
                            split_vals['account_id'] = int(acc_id_val)
                            
                        # Limitar la distribuciÃ³n de esta lÃnea hija a un 100% de esta cuenta
                        split_vals['analytic_distribution'] = {str(dict_key): 100.0}
                        
                        # Limpiar el text mapping para evitar iteraciones si hubiera recursividad
                        split_vals['analytic_distribution_accounts'] = json.dumps({str(dict_key): mapped_acc_id}) if mapped_acc_id else False
                        
                        _logger.info('   -> Generando sub-lÃnea para cuenta contable %s, valor: %s', split_vals.get('account_id'), split_vals.get('price_unit'))
                        new_vals_list.append(split_vals)
                    continue # Saltar a la siguiente lÃnea del loop original, pues esta ha sido convertida en varias nuevas

            # En cualquier otro caso no se afecta (fallback)
            new_vals_list.append(vals)
            
        return super(AccountMoveLine, self).create(new_vals_list)

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _sync_dynamic_lines(self, container):
        res = super()._sync_dynamic_lines(container)
        
        # Interceptar el sincronizador que crea las lineas de los apuntes contables ON THE FLY
        for line in self.line_ids:
            # Solo evaluamos lÃneas editables de producto con distribuciÃ³n
            dist = getattr(line, 'analytic_distribution', False)
            mapping = getattr(line, 'analytic_distribution_accounts', False)
            
            if line.display_type == 'product' and dist and mapping and not self._context.get('skip_dynamic_analytic_split'):
                if isinstance(mapping, str):
                    try:
                        mapping = json.loads(mapping)
                    except Exception:
                        mapping = {}
                
                # Si en memoria la distribuciÃ³n tiene varias llaves y existe el mapping para ellas
                if len(dist) >= 1 and isinstance(mapping, dict):
                    # Evitar loop si es 100% y ya estÃ¡ en la cuenta correcta
                    if len(dist) == 1:
                        dict_key = list(dist.keys())[0]
                        mapped_acc_id = mapping.get(str(dict_key)) or mapping.get(dict_key)
                        fin_acc_id_mapped = mapped_acc_id['id'] if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id else mapped_acc_id
                        if fin_acc_id_mapped and int(fin_acc_id_mapped) == line.account_id.id and float(dist[dict_key]) == 100.0:
                            continue

                    _logger.warning("INTERCEPTANDO lÃnea en memoria (dinÃ¡mica) para [%s], Dist: %s", line.name, dist)
                    # Tomar datos originales de la lÃnea a dividir
                    price_unit = line.price_unit
                    original_id = line.id
                    
                    split_commands = []
                    
                    # Preparar nuevos reemplazos
                    for dict_key, percentage in dist.items():
                        mapped_acc_id = mapping.get(str(dict_key)) or mapping.get(dict_key)
                        ratio = float(percentage) / 100.0
                        
                        if mapped_acc_id:
                            fin_account_id = mapped_acc_id['id'] if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id else mapped_acc_id
                        else:
                            fin_account_id = line.account_id.id
                        
                        copy_vals = {
                            'product_id': line.product_id.id,
                            'name': line.name,
                            'quantity': line.quantity,
                            'price_unit': price_unit * ratio,
                            'account_id': fin_account_id,
                            'display_type': 'product',
                            'analytic_distribution': {str(dict_key): 100.0},
                            'analytic_distribution_accounts': json.dumps({str(dict_key): mapped_acc_id}) if mapped_acc_id else False,
                            'tax_ids': [(6, 0, line.tax_ids.ids)],
                        }
                        
                        split_commands.append((0, 0, copy_vals))
                    
                    if split_commands:
                        # Remover la original de la sesiÃ³n actual de memoria y meter las divididas
                        self.with_context(skip_dynamic_analytic_split=True, check_move_validity=False).update({
                            'line_ids': [(2, original_id, 0)] + split_commands
                        })
        return res

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
        _logger.warning('Entrando a write de account.move y fragmentando lÃneas si es necesario')
        
        # Interceptar el diccionario antes de que Odoo ejecute el write real en DB
        if 'invoice_line_ids' in vals or 'line_ids' in vals:
            for field_name in ['invoice_line_ids', 'line_ids']:
                if field_name not in vals:
                    continue
                
                new_commands = []
                for cmd in vals[field_name]:
                    # Si es un comando CREATE(0) o UPDATE(1) y tiene distribution
                    if cmd[0] in (0, 1) and isinstance(cmd[2], dict) and 'analytic_distribution' in cmd[2]:
                        dist = cmd[2].get('analytic_distribution')
                        mapping = cmd[2].get('analytic_distribution_accounts') or '{}'
                        
                        if isinstance(dist, str):
                            try: dist = json.loads(dist)
                            except: pass
                            
                        if isinstance(mapping, str):
                            try: mapping = json.loads(mapping)
                            except: mapping = {}
                            
                        if isinstance(dist, dict) and mapping and len(dist) >= 1:
                            
                            # Evitar interceptar si es 100% y ya estÃ¡ en la cuenta correcta (para evitar borrar y recrear la lÃnea)
                            if len(dist) == 1:
                                dict_key = list(dist.keys())[0]
                                mapped_acc_id = mapping.get(str(dict_key)) or mapping.get(dict_key)
                                fin_acc_id_mapped = mapped_acc_id['id'] if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id else mapped_acc_id
                                
                                if cmd[0] == 1:
                                    line_record = self.env['account.move.line'].browse(cmd[1])
                                    if fin_acc_id_mapped and int(fin_acc_id_mapped) == line_record.account_id.id and float(dist[dict_key]) == 100.0:
                                        new_commands.append(cmd)
                                        continue
                                elif cmd[0] == 0:
                                    original_acc = cmd[2].get('account_id')
                                    if fin_acc_id_mapped and original_acc and int(fin_acc_id_mapped) == int(original_acc) and float(dist[dict_key]) == 100.0:
                                        new_commands.append(cmd)
                                        continue

                            _logger.warning(f"Interceptando comando {cmd[0]} - Desdoblando distribuciÃ³n: {dist}")
                            
                            # Para updates (1), necesitamos recuperar valores base de la BD porque el dist trae solo los cambios
                            if cmd[0] == 1:
                                line_record = self.env['account.move.line'].browse(cmd[1])
                                price_unit = cmd[2].get('price_unit', line_record.price_unit)
                                debit = cmd[2].get('debit', line_record.debit)
                                credit = cmd[2].get('credit', line_record.credit)
                                original_acc = cmd[2].get('account_id', line_record.account_id.id)
                            else: # CREATE(0)
                                price_unit = cmd[2].get('price_unit', 0.0)
                                debit = cmd[2].get('debit', 0.0)
                                credit = cmd[2].get('credit', 0.0)
                                original_acc = cmd[2].get('account_id')
                            
                            # Marcamos la lÃnea base para borrarla o vaciarla si existÃa
                            if cmd[0] == 1:
                                new_commands.append((2, cmd[1], 0))  # Delete the original from db
                                
                            # Creamos los hijos
                            for dict_key, percentage in dist.items():
                                mapped_acc_id = mapping.get(str(dict_key)) or mapping.get(dict_key)
                                ratio = float(percentage) / 100.0
                                
                                split_vals = dict(cmd[2])
                                # Llenar los valores faltantes del update
                                if cmd[0] == 1:
                                    if 'product_id' not in split_vals: split_vals['product_id'] = line_record.product_id.id
                                    if 'name' not in split_vals: split_vals['name'] = line_record.name
                                    if 'quantity' not in split_vals: split_vals['quantity'] = line_record.quantity
                                    
                                split_vals['price_unit'] = price_unit * ratio
                                if debit: split_vals['debit'] = debit * ratio
                                if credit: split_vals['credit'] = credit * ratio
                                
                                if mapped_acc_id:
                                    acc_id_val = mapped_acc_id['id'] if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id else mapped_acc_id
                                    split_vals['account_id'] = int(acc_id_val)
                                elif original_acc:
                                    split_vals['account_id'] = original_acc
                                    
                                split_vals['analytic_distribution'] = {str(dict_key): 100.0}
                                split_vals['analytic_distribution_accounts'] = json.dumps({str(dict_key): mapped_acc_id}) if mapped_acc_id else False
                                
                                new_commands.append((0, 0, split_vals))
                            
                            continue # Saltar este comando y usar los desdoblados
                            
                    # Si no pasÃ³ por el filtro anterior, dejarlo igual
                    new_commands.append(cmd)
                
                # Reemplazar el paquete completo
                vals[field_name] = new_commands

        res = super(AccountMove, self).write(vals)
        # Refuerza la validación: si se modifican líneas o campos relacionados, siempre valida
        self._validate_analytic_percentages()
        return res
