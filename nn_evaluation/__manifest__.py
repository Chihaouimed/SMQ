# -- coding: utf-8 --
{
    'name': 'Supplier AI Analysis',
    'version': '1.0',
    'category': 'Quality/Suppliers',
    'summary': 'Intelligence artificielle pour l\'analyse des fournisseurs',
    'description': """
Module d'Intelligence Artificielle pour l'Analyse des Fournisseurs
=================================================================

Ce module ajoute des fonctionnalités d'IA au module d'évaluation des fournisseurs:

Fonctionnalités principales:
• Analyse IA avancée des performances fournisseurs
• Évaluation automatique des risques
• Recommandations intelligentes
• Chatbot IA pour assistance utilisateur
• Prédictions de tendances
• Alertes automatiques basées sur l'IA

Intégration:
• Compatible avec le module nn_evaluation
• Utilise l'API OpenAI pour les analyses
• Interface utilisateur intuitive
• Rapports et tableaux de bord

Configuration requise:
• Clé API OpenAI
• Module nn_evaluation installé
    """,
    'author': 'Votre Entreprise',
    'website': 'https://www.votreentreprise.com',
    'depends': [
        'base',
        'mail',
        'hr',
        'nn_evaluation',
        'nn_fournisseur'
    ],
    'external_dependencies': {
        'python': ['openai', 'json']
    },
    'data': [
        'security/ir.model.access.csv',
        'views/ai_analysis_views.xml',
        'data/ai_sequence.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'sequence': 100,
}