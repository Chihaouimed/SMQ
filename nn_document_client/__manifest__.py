
# Fichier: document_client/__manifest__.py
{
    'name': 'Document Client',
    'version': '1.0',
    'category': 'Documents',
    'summary': 'Gestion des documents clients',
    'description': """
Module pour gérer les documents clients
======================================
Ce module permet de gérer les documents associés aux clients.
    """,
    'author': 'Votre Nom',
    'website': 'https://www.votresite.com',
    'depends': ['base', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/document_client_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}