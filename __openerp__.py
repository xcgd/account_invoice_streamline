# -*- coding: utf-8 -*-
##############################################################################
#
##############################################################################
{
    "name": "Account Invoice Streamline",
    "version": "1.5.1",
    "author": "XCG Consulting",
    "category": 'Accounting',
    "description": """Enhancements to the account
    invoice module to streamline its usage.
    """,
    'website': 'http://www.openerp-experts.com',
    'init_xml': [],
    "depends": [
        'base',
        'account_streamline',
        'analytic_structure',
        'account_move_reversal',
    ],
    "data": [
        'views/account_invoice.xml',
        'workflow/account_invoice.xml',
    ],
    #'demo_xml': [],
    'test': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
