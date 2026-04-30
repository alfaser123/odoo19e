# -*- coding: utf-8 -*-
{
    'name': "Grupo de Cuentas, Grupo de cuentas jerárquico",
    'version': '19.0.25.12.30',
    'author': 'Leonardo Rojas',
    'category': 'Accounting',
    'website': 'https://www.pi-ig.com',
    'license': 'LGPL-3',
    'sequence': 2,
    'summary': """
    usado para agregar niveles y jerarquía a los grupos de cuentas, para mejorar la navegación y organización de las cuentas contables.
    """,
    'description': """
    Grupo de Cuentas, Grupo de cuentas jerárquico.
    se agregan niveles y jerarquía a los grupos de cuentas, para mejorar la navegación y organización de las cuentas contables.
    """,
    'price': 0.00,
    'currency': 'COP',
    'depends': [
        'account',
    ],
    'icon': 'static/description/icon.png',
    'data': [
        'views/account_views.xml',
    ],
    'demo': [
    ],
    'test': [
    ],
    'post_load': None,
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
}
