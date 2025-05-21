# -*- coding: utf-8 -*-
{
    'name': "Sous Actions",
    'summary': """
        Gestion des suggestions et retours clients
    """,
    'description': """
        

        Fonctionnalités:
        - Enregistrement des suggestions client
        - Assignation à un responsable
        - Processus de traitement et de décision
        - Suivi des actions associées
        - Validation des suggestions
    """,
    'author': "Votre Entreprise",
    'website': "https://www.votreentreprise.com",
    'category': 'Sales/CRM',
    'version': '1.0',
    'depends': ['base', 'mail', 'hr',],
    'data': [
        'security/ir.model.access.csv',
        'views/ sous_actions_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}