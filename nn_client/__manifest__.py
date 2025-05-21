# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Client',
    'category': 'course',
    'summary': 'Gestion des fournisseur',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['base', 'crm', 'contacts', 'nn_document_client'],
    'data': [

        'views/client.xml',
        'security/ir.model.access.csv',
        'views/menu_type_client.xml',
        'views/menu_categorie.xml',

    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'application': True,

}
