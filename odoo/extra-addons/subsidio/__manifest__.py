# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Cubic ERP - Teradata SAC (<http://cubicerp.com>).
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
{
    "name": "Subsidio",
    "version": "1.0",
    "description": """CCF""",
    "author": "OxSoft SAS",
    "website": "http://www.oxsoft.com.co",
    "category": "CCF",
    "depends": [
        "account_accountant",
        "piig_10n_account_tax_withholding",
        
        ],
    "data":[
      'views/partner_categorias_subsidio_view.xml',
      'views/account_extended.xml',
      'views/product_extended_view.xml',
      'views/tarifas_view.xml',
      'views/categorias_update.xml',
      'views/product_pricelist_ext_views.xml',
      ],
    "demo_xml": [],
    "active": False,
    "installable": True,
    "certificate" : "",
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
