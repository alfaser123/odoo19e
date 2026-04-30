# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2015 Deltatech All Rights Reserved
#                    Dorin Hongu <dhongu(@)gmail(.)com       
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

import odoo.addons.decimal_precision as dp
import logging

_logger = logging.getLogger(__name__)



class PricelistItem(models.Model):
    _inherit =  "product.pricelist.item"
 

    price_taxed_subsidiado = fields.Float('Precio subsidiado IVA incl', digits=dp.get_precision('Product Price'),
        help="Precio que se desea en la factura despues de subisidio y despues de impuesto")
    tax_id = fields.Many2one('account.tax', string='Impuesto asociado a precio tax incluido' , help="Especifica que impuesto  que estarà asociado al cálculo del valor incluido impuesto")

    
 

   
    
        