# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Audit',
    'category': 'course',
    'summary': 'Gestion des auditeurs',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['base', 'crm', 'contacts',],
    'data': [

        'views/audit.xml',
        'security/ir.model.access.csv',
        'views/menu.xml',

    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'application': True,

}
