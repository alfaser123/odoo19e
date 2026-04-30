{
    'name': 'Costos ABC Odoo 19',
    'version': '19.0.1.0.0',
    'summary': 'Distribución contable ABC basada en distribución analítica',
    'category': 'Accounting/Accounting',
    'author': 'Tu Empresa',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'analytic',
    ],
    'data': [
        'views/analytic_distribution_model_views.xml',
        'views/account_move_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/costos_distribuciones/static/src/js/analytic_distribution_abc_patch.js',
            '/costos_distribuciones/static/src/xml/analytic_distribution_abc.xml',
        ],
    },
    'installable': True,
    'application': False,
}