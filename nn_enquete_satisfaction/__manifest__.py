{
    'name': 'Enquête Satisfaction Client',
    'version': '1.0',
    'summary': 'Gestion des enquêtes de satisfaction client',
    'description': 'Module pour créer et envoyer des enquêtes de satisfaction aux clients',
    'author': 'TonNom',
    'depends': ['base', 'mail', 'survey',  # Ajouté pour la prédiction de risque
                ],
    'data': [
        'security/ir.model.access.csv',
        'views/enquete_satisfaction_views.xml',
        'views/wizard.xml',

    ],
    'external_dependencies': {
        'python': [
            'requests',  # Pour les appels API Hugging Face
        ],
    },
    'assets': {
        'web.assets_backend': [
            # 'nn_enquete_satisfaction/static/src/css/satisfaction_dashboard.css',
            # 'nn_enquete_satisfaction/static/src/js/satisfaction_widgets.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
