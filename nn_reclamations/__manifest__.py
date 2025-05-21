# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'reclamation',
    'category': 'course',
    'summary': 'Gestion des reclamation',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['base', 'crm', 'contacts', ],
    'data': [

        'views/reclamation.xml',
        'security/ir.model.access.csv',
        'views/menu_type_reclamation.xml',

    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'application': True,

}
