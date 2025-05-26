# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Evaluation',
    'category': 'course',
    'summary': 'Gestion des fournisseur',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['base','crm','contacts'],
    'data': [

        'views/evaluation.xml',
        'security/ir.model.access.csv',

    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'application': True,

}
