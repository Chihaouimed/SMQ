# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'nn_conformite',
    'category': 'course',
    'summary': 'Gestion des nn_conformite',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['base', 'crm', 'contacts','nn_reclamations' ],
    'data': [

        'security/ir.model.access.csv',
        'views/nn_conformite.xml',
        'data/non_conformite_sequence.xml',

    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'application': True,

}
