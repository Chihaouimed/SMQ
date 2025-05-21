# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'documentation',
    'category': 'course',
    'summary': 'Gestion de la documentation',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['base', 'crm'],
    'data': [

        'security/ir.model.access.csv',
        'views/documentation.xml',
        'views/menu.xml',
        'views/menu_site.xml',
        'views/menu_activite.xml',
        'views/email_template.xml',
        'views/document_client_views.xml',
        'wizards/docment_rejection_wizard.xml',

    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
