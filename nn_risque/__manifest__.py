{
    'name': "Gestion des Risques",
    'summary': """
        Module pour gérer les fiches de risque
    """,
    'description': """
        Ce module permet de:
        - Créer des fiches de risque
        - Évaluer les risques selon différents critères
        - Suivre l'évolution des risques identifiés
    """,
    'author': "Votre Entreprise",
    'website': "https://www.votreentreprise.com",
    'category': 'Management',
    'version': '1.0',
    'depends': ['base', 'mail','nn_action'],
    'data': [
        'security/ir.model.access.csv',
        'views/risque_view.xml',
        'views/recommandation_popup.xml'
    ],
    'application': True,
    'sequence': 10,
    'license': 'LGPL-3',
}