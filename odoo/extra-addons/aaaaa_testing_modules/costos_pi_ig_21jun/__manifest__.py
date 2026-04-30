# -*- coding: utf-8 -*-
{
    'name': 'Costos PI IG',
    'version': '19.0.1.0.0',
    'summary': 'Módulo unificado: Costos y Cuentas Analíticas PI IG',
    'category': 'Accounting',
    'author': 'pi-ig leonardo rojas',
    'license': 'LGPL-3',
    'website': 'http://www.pi-ig.com',
    'depends': ['base', 'account', 'analytic'],
    'data': [
        'security/ir.model.access.csv',
        'views/costos_uso_views.xml',
        'views/driver_distribution_views.xml',
        'views/analytic_distribution_models_extend_views.xml', 
        'views/account_move_views_extend.xml',
        'views/cuentas_analiticas/account_move_line_tree_extend.xml',
    ],
    'post_load': None,
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'costos_pi_ig/static/src/components/analytic_distribution/analytic_distribution.js',
            'costos_pi_ig/static/src/components/analytic_distribution/analytic_distribution.xml',
        ],
    },
}
