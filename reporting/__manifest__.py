{
    'name': 'SMQ Reporting',
    'version': '1.0',
    'category': 'Quality',
    'summary': 'Module de reporting pour le Système de Management de la Qualité',
    'description': """
        Ce module offre des fonctionnalités de reporting pour le suivi SMQ:
        - Suivi des audits
        - Gestion des non-conformités
        - Actions correctives et préventives
        - Reporting graphique et pivot
    """,
    'author': 'Votre Nom',
    'website': 'https://www.votresite.com',
    'depends': ['base', 'mail', 'hr', 'web', 'nn_risque', 'nn_reunion', 'nn_reclamations', 'nn_evaluation',
                'nn_fournisseur', 'nn_enquete_satisfaction', 'nn_action'],
    'data': [
        'security/ir.model.access.csv',
        'views/reporting_nonconformity_views.xml',
        'views/menu.xml',

    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
