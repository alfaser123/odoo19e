from odoo import models, api, fields, Command
from odoo.tools import frozendict
import json
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_zero_financial_impact = fields.Boolean(
        string='Sin Impacto Financiero',
        default=False,
        help="Si es verdadero, fuerza a que el Débito, Crédito, Balance y Monto en Divisa sean 0."
    )
    costos_uso_id = fields.Many2one('costos.uso', string='Uso de Costo')
    allowed_costos_uso_ids = fields.Many2many('costos.uso', compute='_compute_allowed_costos_uso_ids')

    @api.depends('product_id', 'partner_id', 'company_id', 'account_id')
    def _compute_allowed_costos_uso_ids(self):
        for line in self:
            if line.display_type == 'product' or not line.move_id.is_invoice(include_receipts=True):
                model_env = self.env['account.analytic.distribution.model']
                # Generar los mismos argumentos base de Odoo
                args = line._get_analytic_distribution_arguments({})
                search_vals = model_env._get_default_search_domain_vals()
                search_vals.update(args)

                # Eliminamos la búsqueda por costos_uso_id para que no filtre
                # obligatoriamente los que no tienen uso
                if 'costos_uso_id' in search_vals:
                    del search_vals['costos_uso_id']
                if 'related_root_plan_ids' in search_vals:
                    del search_vals['related_root_plan_ids']

                # Construimos el dominio exacto sin el uso de costo
                domain = []
                for fname, value in search_vals.items():
                    domain += model_env._create_domain(fname, value)

                # Obtenemos TODOS los modelos aplicables para esta linea (productos, partners, global...)
                applicable_models = model_env.search(domain)

                # Extraemos y asignamos solo los usos que correspondan a esos modelos
                valid_usos = applicable_models.mapped('costos_uso_id')
                line.allowed_costos_uso_ids = valid_usos.ids
            else:
                line.allowed_costos_uso_ids = False

    @api.depends('is_zero_financial_impact')
    def _compute_balance(self):
        super()._compute_balance()
        for line in self:
            if getattr(line, 'is_zero_financial_impact', False):
                line.balance = 0.0

    @api.depends('is_zero_financial_impact')
    def _compute_debit_credit(self):
        super()._compute_debit_credit()
        for line in self:
            if getattr(line, 'is_zero_financial_impact', False):
                line.debit = 0.0
                line.credit = 0.0

    @api.depends('is_zero_financial_impact')
    def _compute_amount_currency(self):
        super()._compute_amount_currency()
        for line in self:
            if getattr(line, 'is_zero_financial_impact', False):
                line.amount_currency = 0.0

    @api.depends('account_id', 'partner_id', 'product_id', 'costos_uso_id')
    def _compute_analytic_distribution(self):
        super()._compute_analytic_distribution()

        # Después de que Odoo calcule 'analytic_distribution', calculamos nosotros 'analytic_distribution_accounts'
        # basándonos en los mismos modelos que aplicaron.
        cache = {}
        for line in self:
            if line.display_type == 'product' or not line.move_id.is_invoice(include_receipts=True):
                related_distribution = line._related_analytic_distribution()
                root_plans = self.env['account.analytic.account'].browse(
                    list({int(account_id) for ids in related_distribution for account_id in ids.split(',') if account_id.strip()})
                ).exists().root_plan_id

                arguments = frozendict(line._get_analytic_distribution_arguments(root_plans))

                # Buscamos los modelos aplicables con los mismos argumentos
                if arguments not in cache:
                    applicable_models = self.env['account.analytic.distribution.model']._get_applicable_models(
                        {k: v for k, v in arguments.items() if k != 'related_root_plan_ids'}
                    )
                    cache[arguments] = applicable_models

                applicable_models = cache[arguments]

                res_accounts = {}
                applied_plans = self.env['account.analytic.plan'] # Start fresh, don't inherit related_plans strictly for accounts mapping if we want to allow different accounts? Or wait...
                for model in applicable_models:
                    # Misma logica que _get_distribution nativo
                    if not applied_plans & model.distribution_analytic_account_ids.root_plan_id:
                        if model.analytic_distribution_accounts: # si tiene mapeo configurado
                            mapping = model.analytic_distribution_accounts
                            if isinstance(mapping, str):
                                try:
                                    mapping = json.loads(mapping)
                                except Exception:
                                    mapping = {}

                            if isinstance(mapping, list):
                                # Si viene como lista de detalles, usar clave -> dict completo
                                # o extraer account_id
                                new_map = {}
                                for item in mapping:
                                    k = item.get('analytic_account_ids')
                                    if k:
                                        new_map[k] = item
                                res_accounts.update(new_map)
                            elif isinstance(mapping, dict):
                                res_accounts.update(mapping)
                        applied_plans += model.distribution_analytic_account_ids.root_plan_id

                # Asignamos el mapeo de cuentas resultante
                if res_accounts:
                    final_list = []
                    for k, v in res_accounts.items():
                        if isinstance(v, dict) and 'analytic_account_ids' in v:
                            final_list.append(v)
                        else:
                            final_list.append({'analytic_account_ids': str(k), 'account_id': v, 'percentage': 100.0})
                    line.analytic_distribution_accounts = json.dumps(final_list)
                elif not res_accounts and line.analytic_distribution_accounts:
                    # Si no hay un nuevo modelo, conservamos el manual que ya tenga
                    pass

    def _get_analytic_distribution_arguments(self, root_plans):
        res = super()._get_analytic_distribution_arguments(root_plans)
        res['costos_uso_id'] = self.costos_uso_id.id or False
        return res

class AccountMove(models.Model):
    _inherit = 'account.move'

    filtered_line_ids = fields.One2many(
        'account.move.line', 'move_id',
        string='Apuntes Contables',
        domain=['&', ('display_type', 'not in', ('line_section', 'line_note')), '|', ('display_type', '!=', 'product'), ('is_analytic_split', '=', True)],
    )

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

            # 0. Restaurar las líneas originales antes de recalcular
            lines_to_reset = move.line_ids.filtered('is_zero_financial_impact')
            if lines_to_reset:
                # Quitamos la bandera. Esto debe reactivar los computes nativos
                # asumiendo que no rompimos el compute manualmente escribiendo 0.
                lines_to_reset.write({'is_zero_financial_impact': False})
                # Forzamos re-cálculo para que line.balance y line.amount_currency vuelvan a existir
                move.env.flush_all()

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
                            if hasattr(m, 'costos_uso_id') and m.costos_uso_id and line.costos_uso_id:
                                if m.costos_uso_id.id != line.costos_uso_id.id:
                                    continue
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

                if isinstance(accounts_mapping, dict) and len(distribution) == 1:
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

                    # 1. PREPARACIÓN CONTABLE: Guardamos los saldos originales antes de anularlos
                    original_balance = line.balance
                    original_amount_currency = line.amount_currency

                    # Extraemos la data base para las sub-líneas
                    base_copy_vals = line.copy_data()[0]
                    if 'tax_ids' in base_copy_vals:
                        base_copy_vals['tax_ids'] = False

                    # 2. SUB-LINEAS CONTABLES DE LA DISTRIBUCION (Se crean con los saldos originales)
                    if isinstance(accounts_mapping, list) and accounts_mapping:
                        # Usar el array detallado que viene del widget
                        for detail in accounts_mapping:
                            dict_key = detail.get('analytic_account_ids')
                            percentage = detail.get('percentage', 0.0)
                            fin_account_id = detail.get('account_id')
                            if isinstance(fin_account_id, list):
                                fin_account_id = fin_account_id[0]
                            if not fin_account_id:
                                fin_account_id = line.account_id.id

                            ratio = float(percentage) / 100.0
                            new_mapping = [detail] # Guardamos el detalle igual por si acaso

                            cur_balance = company_curr.round(original_balance * ratio)
                            cur_amount_curr = line_curr.round(original_amount_currency * ratio)

                            copy_vals = dict(base_copy_vals)
                            copy_vals.update({
                                'name': line.name,
                                'quantity': line.quantity,
                                'price_unit': line.price_unit * ratio,
                                'account_id': int(fin_account_id),
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
                    else:
                        # Fallback a diccionario clásico de Odoo si accounts_mapping es dict vacío
                        for dict_key, percentage in distribution.items():
                            mapped_acc_id = accounts_mapping.get(dict_key) if isinstance(accounts_mapping, dict) else False

                            if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id:
                                fin_account_id = int(mapped_acc_id['id'])
                            elif mapped_acc_id:
                                fin_account_id = int(mapped_acc_id)
                            else:
                                fin_account_id = line.account_id.id

                            ratio = float(percentage) / 100.0

                            new_mapping = {dict_key: mapped_acc_id} if mapped_acc_id else {}

                            cur_balance = company_curr.round(original_balance * ratio)
                            cur_amount_curr = line_curr.round(original_amount_currency * ratio)

                            copy_vals = dict(base_copy_vals)
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

                    # 3. ANULACIÓN DE IMPACTO FINANCIERO EN LA LÍNEA ORIGINAL
                    # Dejamos de forzar balance: 0.0 en BD y permitimos que la bandera
                    # ejecute los computes nativos de _compute_balance, _compute_debit_credit...
                    line.with_context(
                        check_move_validity=False,
                        skip_account_move_synchronization=True
                    ).write({
                        'is_zero_financial_impact': True,
                    })

            if commands:
                move.with_context(skip_analytic_split=True, check_move_validity=False).write({
                    'line_ids': commands
                })
