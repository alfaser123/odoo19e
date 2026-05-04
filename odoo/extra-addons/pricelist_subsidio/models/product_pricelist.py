from odoo import fields, models


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    codigo_cat_subsidio = fields.Char(string="Cód Categ Subsidio")
