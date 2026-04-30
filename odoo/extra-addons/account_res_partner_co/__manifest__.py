# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'account_res_partner_co',
    'version': '1.1',
    'summary': 'PIIG - res_partner Colombia  num_id and names',
    'sequence': 30,
    "author": "PIIG SAS",
    'description': """ incluye lso 4 componentes latinoamericasnos para Nombre, calcula Digito de verificacion y aporta 
    consulta en linea a aportes y subs para importar data """,
    'category': 'Accounting',
    "license": "LGPL-3",
    'website': 'https://www.pi-ig.com',
    'images' : [],
    'depends' : ['base','l10n_co_dian','l10n_co_dian_tech_menu_complete'],
    'data': [
        'views/res_partner_view.xml',
        'views/l10n_latam_identification_type_views.xml',
     ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}


