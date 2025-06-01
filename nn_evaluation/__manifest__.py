# nn_evaluation/__manifest__.py
# -*- coding: utf-8 -*-
{
    'name': 'Supplier AI Analysis',
    'version': '17.0.1.0.0',
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
• Compatible avec Odoo 17
• Utilise l'API OpenAI pour les analyses (optionnel)
• Interface utilisateur intuitive
• Rapports et tableaux de bord

Configuration requise:
• Clé API OpenAI (optionnelle - mode simulation disponible)
• Modules base et mail installés
    """,
    'author': 'Votre Entreprise',
    'website': 'https://www.votreentreprise.com',
    'depends': [
        'base',
        'mail',
        'product',
        # CORRECTION: Supprimer 'nn_fournisseur' s'il n'existe pas
        # 'nn_fournisseur'
    ],
    'external_dependencies': {
        'python': ['openai']  # Suppression de 'json' car c'est natif à Python
    },
    'data': [
        'security/ir.model.access.csv',
        'data/ai_sequence.xml',
        'views/evaluation.xml',  # CORRECTION: Renommer pour cohérence
        'views/ai_analysis_views.xml',
    ],
    'demo': [],
    'assets': {
        'web.assets_backend': [
            # Ajouter des assets CSS/JS si nécessaire
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',

}