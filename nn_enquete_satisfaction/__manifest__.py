{
    'name': 'Enquête Satisfaction Client',
    'version': '1.0',
    'summary': 'Gestion des enquêtes de satisfaction client',
    'description': 'Module pour créer et envoyer des enquêtes de satisfaction aux clients',
    'author': 'TonNom',
    'depends': ['base', 'mail', 'survey',],
    'data': [
        'security/ir.model.access.csv',
        'data/enquete_satisfaction_sequence.xml',
        'data/email_template.xml',
        'views/enquete_satisfaction_views.xml',
        'views/tree_view.xml',

    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
