{
    'name': 'L10N CO DIAN Technical Menu',
    'version': '19.0.1.0.2',
    'summary': 'Technical accounting menu for identification document types with mysql_data_id',
    'depends': ['account', 'accountant', 'l10n_latam_base'],
    'data': [
        'views/l10n_latam_identification_type_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
