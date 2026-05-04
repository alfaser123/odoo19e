from odoo import api, fields, models, _
from odoo.tools import frozendict


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_sync_stack(self, container):
        stack, update_containers = super()._get_sync_stack(container)
        stack.append(
            (
                75,
                self._sync_dynamic_line(
                    existing_key_fname="subsidio_key",
                    needed_vals_fname="line_ids.subsidio_needed",
                    needed_dirty_fname="line_ids.subsidio_dirty",
                    line_type="subsidio",
                    container=container,
                ),
            )
        )
        return stack, update_containers


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    display_type = fields.Selection(
        selection_add=[("subsidio", "Subsidio")],
        ondelete={"subsidio": "cascade"},
    )
    subsidio_origin_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Línea origen subsidio",
        readonly=True,
        copy=False,
        index=True,
    )
    subsidio_pricelist_code = fields.Char(
        string="Cód Categ Subsidio",
        readonly=True,
        copy=False,
    )
    subsidio_key = fields.Binary(
        compute="_compute_subsidio_key",
        exportable=False,
    )
    subsidio_needed = fields.Binary(
        compute="_compute_subsidio_needed",
        exportable=False,
    )
    subsidio_dirty = fields.Boolean(compute="_compute_subsidio_needed")

    @api.depends(
        "account_id",
        "analytic_distribution",
        "currency_rate",
        "display_type",
        "move_id",
        "subsidio_origin_line_id",
        "subsidio_pricelist_code",
        "product_id",
    )
    def _compute_subsidio_key(self):
        for line in self:
            if line.display_type == "subsidio":
                line.subsidio_key = frozendict(
                    {
                        "move_id": line.move_id.id,
                        "account_id": line.account_id.id,
                        "analytic_distribution": line.analytic_distribution,
                        "currency_rate": line.currency_rate,
                        "subsidio_origin_line_id": line.subsidio_origin_line_id.id,
                        "subsidio_pricelist_code": line.subsidio_pricelist_code,
                        "product_id": line.product_id.id,
                    }
                )
            else:
                line.subsidio_key = False

    @api.depends(
        "analytic_distribution",
        "currency_rate",
        "move_id.journal_id.account_cr_subs",
        "move_id.journal_id.account_db_subs",
        "move_id.pricelist_id.codigo_cat_subsidio",
        "price_surcharge",
        "product_id",
        "quantity",
    )
    def _compute_subsidio_needed(self):
        needed_by_source = self._get_subsidio_needed_by_source_line()
        for line in self:
            line.subsidio_dirty = True
            line.subsidio_needed = needed_by_source.get(line) or False

    def _get_subsidio_needed_by_source_line(self):
        result = {}
        product_lines = self.move_id.line_ids.filtered(
            lambda line: line._use_subsidio_pricelist_accounting()
        )
        for line in product_lines:
            result[line] = line._prepare_subsidio_needed()
        return result

    def _use_subsidio_pricelist_accounting(self):
        self.ensure_one()
        journal = self.move_id.journal_id
        return (
            self.move_id.is_sale_document(include_receipts=True)
            and journal.type == "sale"
            and journal.account_db_subs
            and journal.account_cr_subs
            and self.display_type == "product"
            and not getattr(self, "is_analytic_split", False)
            and self.product_id
            and self.move_id.pricelist_id
            and self.price_surcharge < 0.0
            and self.quantity
        )

    def _prepare_subsidio_needed(self):
        self.ensure_one()
        move = self.move_id
        journal = move.journal_id
        amount = self.currency_id.round(abs(self.price_surcharge) * self.quantity)
        if not amount:
            return False

        splits = self._get_subsidio_analytic_splits(amount)
        needed = {}
        line_name = _("SUB : %s", self.product_id.display_name)
        for analytic_distribution, split_amount in splits:
            amount_currency = self.currency_id.round(split_amount)
            balance = (
                self.company_currency_id.round(amount_currency / self.currency_rate)
                if self.currency_rate
                else 0.0
            )
            for account, factor in (
                (journal.account_db_subs, 1.0),
                (journal.account_cr_subs, -1.0),
            ):
                key = frozendict(
                    {
                        "move_id": move.id,
                        "account_id": account.id,
                        "analytic_distribution": analytic_distribution,
                        "currency_rate": self.currency_rate,
                        "subsidio_origin_line_id": self.id,
                        "subsidio_pricelist_code": move.pricelist_id.codigo_cat_subsidio,
                        "product_id": self.product_id.id,
                    }
                )
                needed[key] = frozendict(
                    {
                        "name": line_name,
                        "amount_currency": amount_currency * factor,
                        "balance": balance * factor,
                        "product_id": self.product_id.id,
                    }
                )
        return needed

    def _get_subsidio_analytic_splits(self, amount):
        self.ensure_one()
        distribution = self.analytic_distribution or {}
        if not distribution:
            return [(False, amount)]

        splits = []
        distributed_amount = 0.0
        items = list(distribution.items())
        total_percentage = sum(float(value) for _account_ids, value in items) or 100.0
        for index, (account_ids, percentage) in enumerate(items):
            if index == len(items) - 1:
                split_amount = amount - distributed_amount
            else:
                split_amount = self.currency_id.round(
                    amount * float(percentage) / total_percentage
                )
                distributed_amount += split_amount
            splits.append(({account_ids: 100.0}, split_amount))
        return splits
