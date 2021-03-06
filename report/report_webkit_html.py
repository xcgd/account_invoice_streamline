# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2012 Camptocamp (<http://www.camptocamp.at>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from report import report_sxw
from report_webkit.webkit_report import WebKitParser


class report_webkit_html(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_webkit_html, self).__init__(
            cr, uid, name, context=context
        )
        self.localcontext.update({
            'cr': cr,
            'time': time,
            'uid': uid,
        })


class report_webkit_html_invoice(report_webkit_html):
    def __init__(self, cr, uid, name, context):
        super(report_webkit_html_invoice, self).__init__(
            cr, uid, name, context=context
        )
        self.localcontext.update({
            'invoice_type': 'normal',
        })

WebKitParser(
    'report.account.invoice.streamline',
    'account.invoice',
    'account_invoice_streamline/report/account_invoice_streamline.mako',
    parser=report_webkit_html_invoice
)
