from odoo import models, api, fields, Command
from odoo.tools import frozendict
import json
import logging

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    ZERO_FINANCIAL_IMPACT_VALS = {
        'debit': 0.0,
        'credit': 0.0,
        'balance': 0.0,
        'amount_currency': 0.0,
    }

    is_zero_financial_impact = fields.Boolean(
        string='Sin Impacto Financiero',
        default=False,
        help="Si es verdadero, fuerza a que el Débito, Crédito, Balance y Monto en Divisa sean 0."
    )
    costos_uso_id = fields.Many2one('costos.uso', string='Uso de Costo')
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Cuenta Analítica',
        check_company=True,
    )
    allowed_costos_uso_ids = fields.Many2many('costos.uso', compute='_compute_allowed_costos_uso_ids')

    def _force_zero_financial_impact(self):
        def needs_zero(line):
            company_currency = line.company_currency_id or line.company_id.currency_id
            line_currency = line.currency_id or company_currency
            return (
                not company_currency.is_zero(line.debit)
                or not company_currency.is_zero(line.credit)
                or not company_currency.is_zero(line.balance)
                or not line_currency.is_zero(line.amount_currency)
            )

        lines = self.filtered(lambda line: line.is_zero_financial_impact and needs_zero(line))
        if lines:
            lines.with_context(
                skip_costos_zero_guard=True,
                check_move_validity=False,
                skip_account_move_synchronization=True,
            ).write(dict(self.ZERO_FINANCIAL_IMPACT_VALS))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_zero_financial_impact'):
                vals.update(self.ZERO_FINANCIAL_IMPACT_VALS)
        lines = super().create(vals_list)
        lines._force_zero_financial_impact()
        return lines

    def write(self, vals):
        if self.env.context.get('skip_costos_zero_guard'):
            return super().write(vals)

        vals = vals.copy()
        if vals.get('is_zero_financial_impact') is True:
            vals.update(self.ZERO_FINANCIAL_IMPACT_VALS)
            res = super().write(vals)
            self._force_zero_financial_impact()
            return res

        zero_lines = self.filtered('is_zero_financial_impact')
        normal_lines = self - zero_lines

        res = True
        if normal_lines:
            res = super(AccountMoveLine, normal_lines).write(vals) and res

        if zero_lines:
            zero_vals = vals.copy()
            if zero_vals.get('is_zero_financial_impact', True) and self.ZERO_FINANCIAL_IMPACT_VALS.keys() & zero_vals.keys():
                zero_vals.update(self.ZERO_FINANCIAL_IMPACT_VALS)
            res = super(
                AccountMoveLine,
                zero_lines.with_context(skip_costos_zero_guard=True),
            ).write(zero_vals) and res
            zero_lines._force_zero_financial_impact()

        return res

    def _validate_analytic_distribution(self):
        return super(AccountMoveLine, self.filtered(lambda line: not line.is_analytic_split))._validate_analytic_distribution()

    @api.depends('product_id', 'partner_id', 'company_id', 'account_id', 'analytic_account_id')
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

    @api.depends('move_id', 'is_zero_financial_impact')
    def _compute_balance(self):
        super()._compute_balance()
        for line in self:
            if getattr(line, 'is_zero_financial_impact', False):
                line.balance = 0.0

    @api.depends('balance', 'is_zero_financial_impact')
    def _compute_debit_credit(self):
        super()._compute_debit_credit()
        for line in self:
            if getattr(line, 'is_zero_financial_impact', False):
                line.debit = 0.0
                line.credit = 0.0

    @api.depends('currency_id', 'company_id', 'currency_rate', 'balance', 'is_zero_financial_impact')
    def _compute_amount_currency(self):
        super()._compute_amount_currency()
        for line in self:
            if getattr(line, 'is_zero_financial_impact', False):
                line.amount_currency = 0.0

    @api.depends('account_id', 'partner_id', 'product_id', 'costos_uso_id', 'analytic_account_id')
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
        res['analytic_account_id'] = self.analytic_account_id.id or False
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

    def _force_zero_financial_impact_lines(self):
        lines = self.line_ids.filtered('is_zero_financial_impact')
        lines._force_zero_financial_impact()

    @api.depends(
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'line_ids.is_analytic_split',
        'line_ids.is_zero_financial_impact',
        'invoice_line_ids.price_subtotal',
        'invoice_line_ids.price_total',
        'state',
    )
    def _compute_amount(self):
        super()._compute_amount()
        for move in self:
            if not move.is_invoice(True) or not move.line_ids.filtered(lambda line: line.is_analytic_split or line.is_zero_financial_impact):
                continue

            visible_product_lines = move.invoice_line_ids.filtered(
                lambda line: line.display_type == 'product' and not line.is_analytic_split
            )
            if not visible_product_lines:
                continue

            amount_untaxed = move.currency_id.round(sum(visible_product_lines.mapped('price_subtotal')))
            amount_total = move.currency_id.round(sum(visible_product_lines.mapped('price_total')))
            amount_tax = move.currency_id.round(amount_total - amount_untaxed)

            signed_sign = -move.direction_sign
            move.amount_untaxed = amount_untaxed
            move.amount_tax = amount_tax
            move.amount_total = amount_total
            move.amount_untaxed_signed = signed_sign * amount_untaxed
            move.amount_untaxed_in_currency_signed = signed_sign * amount_untaxed
            move.amount_tax_signed = signed_sign * amount_tax
            move.amount_total_signed = signed_sign * amount_total
            move.amount_total_in_currency_signed = signed_sign * amount_total

    def _get_rounded_base_and_tax_lines(self, round_from_tax_lines=True):
        base_lines, tax_lines = super()._get_rounded_base_and_tax_lines(round_from_tax_lines=round_from_tax_lines)
        if self.line_ids.filtered('is_analytic_split'):
            base_lines = [
                base_line
                for base_line in base_lines
                if not getattr(base_line.get('record'), 'is_analytic_split', False)
            ]
        return base_lines, tax_lines

    def _post(self, soft=True):
        draft_moves = self.filtered(lambda move: move.state == 'draft')
        draft_moves._split_analytic_financial_lines()
        draft_moves._force_zero_financial_impact_lines()
        posted_moves = super()._post(soft=soft)
        posted_moves._force_zero_financial_impact_lines()
        return posted_moves

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
                for reset_line in lines_to_reset:
                    amount_currency = (reset_line.move_id.direction_sign or 1.0) * reset_line.price_subtotal
                    balance = (
                        reset_line.company_currency_id.round(amount_currency / reset_line.currency_rate)
                        if reset_line.currency_rate
                        else amount_currency
                    )
                    reset_line.with_context(
                        skip_costos_zero_guard=True,
                        check_move_validity=False,
                        skip_account_move_synchronization=True,
                    ).write({
                        'is_zero_financial_impact': False,
                        'balance': balance,
                        'amount_currency': reset_line.currency_id.round(amount_currency),
                        'debit': balance if balance > 0 else 0.0,
                        'credit': -balance if balance < 0 else 0.0,
                    })
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
                            if m.analytic_account_id and line.analytic_account_id:
                                if m.analytic_account_id.id != line.analytic_account_id.id:
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
                        accumulated_balance = 0.0
                        accumulated_amount_currency = 0.0
                        accumulated_price_unit = 0.0
                        for index, detail in enumerate(accounts_mapping):
                            dict_key = detail.get('analytic_account_ids')
                            percentage = detail.get('percentage', 0.0)
                            fin_account_id = detail.get('account_id')
                            if isinstance(fin_account_id, list):
                                fin_account_id = fin_account_id[0]
                            if not fin_account_id:
                                fin_account_id = line.account_id.id

                            ratio = float(percentage) / 100.0
                            new_mapping = [detail] # Guardamos el detalle igual por si acaso

                            if index == len(accounts_mapping) - 1:
                                cur_balance = company_curr.round(original_balance - accumulated_balance)
                                cur_amount_curr = line_curr.round(original_amount_currency - accumulated_amount_currency)
                                cur_price_unit = line_curr.round(line.price_unit - accumulated_price_unit)
                            else:
                                cur_balance = company_curr.round(original_balance * ratio)
                                cur_amount_curr = line_curr.round(original_amount_currency * ratio)
                                cur_price_unit = line_curr.round(line.price_unit * ratio)
                                accumulated_balance += cur_balance
                                accumulated_amount_currency += cur_amount_curr
                                accumulated_price_unit += cur_price_unit

                            copy_vals = dict(base_copy_vals)
                            copy_vals.update({
                                'name': line.name,
                                'quantity': line.quantity,
                                'price_unit': cur_price_unit,
                                'account_id': int(fin_account_id),
                                'analytic_distribution': {str(dict_key): 100.0},
                                'analytic_distribution_accounts': json.dumps(new_mapping),
                                'is_analytic_split': True,
                                'is_imported': True,
                                'display_type': 'product',
                                'balance': cur_balance,
                                'amount_currency': cur_amount_curr,
                                'debit': cur_balance if cur_balance > 0 else 0.0,
                                'credit': -cur_balance if cur_balance < 0 else 0.0,
                            })
                            commands.append(Command.create(copy_vals))
                    else:
                        # Fallback a diccionario clásico de Odoo si accounts_mapping es dict vacío
                        distribution_items = list(distribution.items())
                        accumulated_balance = 0.0
                        accumulated_amount_currency = 0.0
                        accumulated_price_unit = 0.0
                        for index, (dict_key, percentage) in enumerate(distribution_items):
                            mapped_acc_id = accounts_mapping.get(dict_key) if isinstance(accounts_mapping, dict) else False

                            if isinstance(mapped_acc_id, dict) and 'id' in mapped_acc_id:
                                fin_account_id = int(mapped_acc_id['id'])
                            elif mapped_acc_id:
                                fin_account_id = int(mapped_acc_id)
                            else:
                                fin_account_id = line.account_id.id

                            ratio = float(percentage) / 100.0

                            new_mapping = {dict_key: mapped_acc_id} if mapped_acc_id else {}

                            if index == len(distribution_items) - 1:
                                cur_balance = company_curr.round(original_balance - accumulated_balance)
                                cur_amount_curr = line_curr.round(original_amount_currency - accumulated_amount_currency)
                                cur_price_unit = line_curr.round(line.price_unit - accumulated_price_unit)
                            else:
                                cur_balance = company_curr.round(original_balance * ratio)
                                cur_amount_curr = line_curr.round(original_amount_currency * ratio)
                                cur_price_unit = line_curr.round(line.price_unit * ratio)
                                accumulated_balance += cur_balance
                                accumulated_amount_currency += cur_amount_curr
                                accumulated_price_unit += cur_price_unit

                            copy_vals = dict(base_copy_vals)
                            copy_vals.update({
                                'name': line.name,
                                'quantity': line.quantity,
                                'price_unit': cur_price_unit,
                                'account_id': fin_account_id,
                                'analytic_distribution': {str(dict_key): 100.0},
                                'analytic_distribution_accounts': json.dumps(new_mapping),
                                'is_analytic_split': True,
                                'is_imported': True,
                                'display_type': 'product',
                                'balance': cur_balance,
                                'amount_currency': cur_amount_curr,
                                'debit': cur_balance if cur_balance > 0 else 0.0,
                                'credit': -cur_balance if cur_balance < 0 else 0.0,
                            })
                            commands.append(Command.create(copy_vals))

                    # 3. ANULACIÓN DE IMPACTO FINANCIERO EN LA LÍNEA ORIGINAL
                    # La bandera conserva la línea visible en factura, pero sus importes contables
                    # deben quedar blindados en cero durante recomputes y confirmación.
                    line.with_context(
                        check_move_validity=False,
                        skip_account_move_synchronization=True
                    ).write({
                        'is_zero_financial_impact': True,
                        'debit': 0.0,
                        'credit': 0.0,
                        'balance': 0.0,
                        'amount_currency': 0.0,
                    })

            if commands:
                move.with_context(skip_analytic_split=True, check_move_validity=False).write({
                    'line_ids': commands
                })
                move._force_zero_financial_impact_lines()
