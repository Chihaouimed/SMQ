{
    'name': "Gestion des Réunions",
    'summary': """
        Module pour gérer et organiser les réunions en entreprise
    """,
    'description': """
        Ce module permet de:
        - Planifier des réunions
        - Définir un ordre du jour
        - Inviter des participants
        - Suivre les statuts des réunions
        - Produire des comptes rendus
    """,
    'author': "Votre Entreprise",
    'website': "https://www.votreentreprise.com",
    'category': 'Human Resources',
    'version': '1.0',
    'depends': ['base', 'hr', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/reunion_views.xml',
    ],

    'application': True,
    'sequence': 150,
    'license': 'LGPL-3',
}