{
    'name': 'Gestion des conformités réglementaires',
    'version': '1.0',
    'category': 'Administration',
    'summary': 'Gestion des conformités réglementaires',
    'description': """
Module de Gestion des Conformités
=================================
Ce module permet de gérer les conformités réglementaires applicables à l'entreprise.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/compliance_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}