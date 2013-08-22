from openerp.osv import fields, osv
from lxml import etree


class account_invoice_line_analytic(osv.Model):
    _name = "account.invoice.line"
    _inherit = "account.invoice.line"

    _columns = {
        'a1_id': fields.many2one(
            'analytic.code',
            "Analysis Code 1",
            domain=[('nd_id.ns_id.model_name', '=', 'account_invoice_line')]
        ),
        'a2_id': fields.many2one(
            'analytic.code',
            "Analysis Code 2",
            domain=[('nd_id.ns_id.model_name', '=', 'account_invoice_line')]
        ),
        'a3_id': fields.many2one(
            'analytic.code',
            "Analysis Code 3",
            domain=[('nd_id.ns_id.model_name', '=', 'account_invoice_line')]
        ),
        'a4_id': fields.many2one(
            'analytic.code',
            "Analysis Code 4",
            domain=[('nd_id.ns_id.model_name', '=', 'account_invoice_line')]
        ),
        'a5_id': fields.many2one(
            'analytic.code',
            "Analysis Code 5",
            domain=[('nd_id.ns_id.model_name', '=', 'account_invoice_line')]
        ),
    }

    def move_line_get_item(self, cr, uid, line, context=None):
        res = super(account_invoice_line_analytic, self)\
            .move_line_get_item(cr, uid, line, context=context)
        for i in range(1, 6):
            key = "a%s_id" % i
            val = getattr(line, key).id
            res[key] = val
        return res


class account_invoice_analytic(osv.Model):
    _name = "account.invoice"
    _inherit = "account.invoice"

    def _delete_sheet(self, res):
        """Delete the 'sheet' element
        but preserve its content.
        """
        tree = etree.XML(res['arch'])
        sheets = tree.xpath('//sheet')
        if sheets:
            etree.strip_tags(tree, 'sheet')
        res['arch'] = etree.tostring(tree)
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type=False,
                        context=None, toolbar=False, submenu=False):
        '''
        Display analysis code in account move lines trees
        '''
        if context is None:
            context = {}
        res = super(account_invoice_analytic, self).fields_view_get(
            cr, uid, view_id=view_id,
            view_type=view_type, context=context,
            toolbar=toolbar, submenu=False)
        ans_obj = self.pool.get('analytic.structure')

        #display analysis codes only when present on a related structure,
        #with dimension name as label
        ans_ids = ans_obj.search(cr, uid,
                                 [('model_name', '=', 'account_invoice_line')],
                                 context=context)
        ans_br = ans_obj.browse(cr, uid, ans_ids, context=context)
        ans_dict = dict()
        for ans in ans_br:
            ans_dict[ans.ordering] = ans.nd_id.name

        if 'fields' in res and 'invoice_line' in res['fields']:
            doc = etree.XML(
                res['fields']['invoice_line']['views']['tree']['arch']
            )
            line_fields = res['fields']['invoice_line'][
                'views']['tree']['fields']
            for i in range(1, 6):
                field_name = 'a%s_id' % i
                if field_name in line_fields:
                    line_fields[field_name]['string'] = \
                        ans_dict.get('%s' % i, 'A%s' % i)
                    doc.xpath("//field[@name='%s']" % field_name)[0].\
                        set('modifiers', '{"tree_invisible": %s}' %
                            (str(not '%s' % i in ans_dict).lower()))
            res['fields']['invoice_line'][
                'views']['tree']['arch'] = etree.tostring(doc)
        res = self._delete_sheet(res)
        return res

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice_analytic, self)\
            .line_get_convert(cr, uid, x, part, date, context)
        for i in range(1, 6):
            key = "a%s_id" % i
            val = x.get(key)
            res[key] = val
        return res
