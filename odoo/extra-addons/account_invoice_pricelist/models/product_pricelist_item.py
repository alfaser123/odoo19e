# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    base = fields.Selection(
        selection_add=[
            ("list_price_taxincl", "Precio base Tiene impuestos incluidos"),
        ],
        ondelete={"list_price_taxincl": "set default"},
    )
    taxes_id = fields.Many2many(
        comodel_name="account.tax",
        relation="product_pricelist_item_tax_rel",
        column1="pricelist_item_id",
        column2="tax_id",
        string="Imp ya incluidos en precio de vta",
        domain="[('type_tax_use', '=', 'sale'), ('company_id', 'parent_of', company_id)]",
        check_company=True,
    )

    def _get_price_label_base_str(self):
        self.ensure_one()
        if self.base == "list_price_taxincl":
            return _("Precio base Tiene impuestos incluidos")
        return super()._get_price_label_base_str()

    def _compute_base_price(self, product, quantity, uom, date, currency, **kwargs):
        if self.base != "list_price_taxincl":
            return super()._compute_base_price(
                product, quantity, uom, date, currency, **kwargs
            )

        self.ensure_one()
        product.ensure_one()
        uom.ensure_one()
        currency.ensure_one()

        src_currency = product.currency_id
        price = product._price_compute("list_price", uom=uom, date=date)[product.id]
        taxes = self.taxes_id
        if taxes:
            price = taxes.with_context(force_price_include=True).compute_all(
                price,
                currency=src_currency,
                quantity=1.0,
                product=product,
                handle_price_include=True,
            )["total_excluded"]

        if src_currency != currency:
            price = src_currency._convert(
                price, currency, self.env.company, date, round=False
            )

        return price

    def _onchange_base(self):
        res = super()._onchange_base()
        for item in self:
            if item.base != "list_price_taxincl":
                item.taxes_id = False
        return res

    def _onchange_compute_price(self):
        res = super()._onchange_compute_price()
        for item in self:
            if item.compute_price != "formula":
                item.taxes_id = False
        return res
