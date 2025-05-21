# -*- coding: utf-8 -*-
{
    'name': "Suggestions Client",
    'summary': """
        Gestion des suggestions et retours clients
    """,
    'description': """
        Ce module permet de recueillir, suivre et traiter les suggestions
        et retours des clients afin d'améliorer vos produits et services.

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
    'depends': ['base', 'mail', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/suggestion_client.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}