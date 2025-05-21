# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Action',
    'category': 'course',
    'summary': 'Gestion des Actions',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['base','crm','nn_sous_action'],
    'data': [

        'security/ir.model.access.csv',
        'views/actions.xml',
        'views/sous_actions_views.xml',

    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'application': True,

}
