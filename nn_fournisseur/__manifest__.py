{
    'name': "Gestion des Fournisseurs",
    'summary': """
        Module de gestion des fournisseurs avec intégration des réclamations et évaluations
    """,
    'description': """
        Module permettant de gérer les fiches fournisseurs et d'intégrer 
        les modules de réclamation et d'évaluation.
    """,
    'author': "Votre Nom",
    'website': "http://www.example.com",
    'category': 'Services',
    'version': '1.0',
    'depends': ['base', 'mail', 'nn_evaluation','nn_reclamations'],
    'data': [
        'security/ir.model.access.csv',
        'views/fournisseur.xml',
        'views/menu.xml',

    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'application': True,
}