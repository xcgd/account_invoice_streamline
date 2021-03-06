import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.addons.analytic_structure.MetaAnalytic import MetaAnalytic

from lxml import etree


class account_invoice_line_analytic(osv.Model):
    __metaclass__ = MetaAnalytic
    _name = "account.invoice.line"
    _inherit = "account.invoice.line"

    _analytic = 'account_invoice_line'

    def move_line_get_item(self, cr, uid, line, context=None):
        """Override this function to include analytic fields in generated
        move-line entries.
        """
        res = super(account_invoice_line_analytic, self).move_line_get_item(
            cr, uid, line, context
        )
        res.update(self.pool['analytic.structure'].extract_values(
            cr, uid, line, 'account_move_line', context=context
        ))
        return res


class account_invoice_streamline(osv.Model):
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

    def _links_get(self, cr, uid, context=None):
        """Gets links value for reference field"""
        obj = self.pool.get('res.request.link')
        ids = obj.search(cr, uid, [])
        res = obj.read(cr, uid, ids, ['object', 'name'], context)
        return [(r['object'], r['name']) for r in res]

    _columns = {
        'object_reference': fields.reference(
            u"Linked Object",
            selection=_links_get,
            size=128,
        )
    }

    def fields_view_get(self, cr, uid, view_id=None, view_type=False,
                        context=None, toolbar=False, submenu=False):
        '''
        Display analysis code in account move lines trees
        '''
        if context is None:
            context = {}
        res = super(account_invoice_streamline, self).fields_view_get(
            cr, uid, view_id=view_id,
            view_type=view_type, context=context,
            toolbar=toolbar, submenu=False)
        ans_obj = self.pool.get('analytic.structure')

        line_id_field = res['fields'].get('invoice_line')
        ans_obj.analytic_fields_subview_get(
            cr, uid, 'account_invoice_line', line_id_field, context=context
        )
        res = self._delete_sheet(res)
        return res

    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice_streamline, self).line_get_convert(
            cr, uid, x, part, date, context
        )
        res.update(self.pool['analytic.structure'].extract_values(
            cr, uid, x, 'account_invoice_line',
            dest_model='account_move_line',
            context=context
        ))
        return res

    def _get_object_reference(self, invoice):
        """ Set the move object reference to account_invoice
        """
        return 'account.invoice,%s' % invoice.id

    def action_move_create(self, cr, uid, ids, context=None):
        """Creates invoice related analytics and financial move lines.

        This function has been copied from account/account_invoice.py:
        - To PEP8-ify the code.
        - To use the reference of this invoice as the reference of generated
        account-move objects.
        - Not to auto-validate generated accounting entries.
        """

        ait_obj = self.pool.get('account.invoice.tax')
        cur_obj = self.pool.get('res.currency')
        period_obj = self.pool.get('account.period')
        payment_term_obj = self.pool.get('account.payment.term')
        journal_obj = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')
        if context is None:
            context = {}
        for inv in self.browse(cr, uid, ids, context=context):
            if not inv.journal_id.sequence_id:
                raise osv.except_osv(
                    _('Error!'),
                    _(
                        'Please define sequence on the journal related to '
                        'this invoice.'
                    )
                )
            if not inv.invoice_line:
                raise osv.except_osv(
                    _('No Invoice Lines!'),
                    _('Please create some invoice lines.')
                )
            if inv.move_id:
                continue

            ctx = context.copy()
            ctx.update({'lang': inv.partner_id.lang})
            if not inv.date_invoice:
                self.write(
                    cr, uid, [inv.id],
                    {'date_invoice': fields.date.context_today(
                        self, cr, uid, context=context
                    )},
                    context=ctx
                )
            company_currency = self.pool['res.company'].browse(
                cr, uid, inv.company_id.id).currency_id.id
            # create the analytical lines
            # one move line per invoice line
            iml = self._get_analytic_lines(cr, uid, inv.id, context=ctx)
            # check if taxes are all computed
            compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
            self.check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)

            # I disabled the check_total feature
            group_check_total_id = self.pool.get('ir.model.data').\
                get_object_reference(
                    cr, uid, 'account', 'group_supplier_inv_check_total'
                )[1]
            group_check_total = self.pool.get('res.groups').browse(
                cr, uid, group_check_total_id, context=context)
            if group_check_total and uid in [
                x.id for x in group_check_total.users
            ]:
                if (inv.type in ('in_invoice', 'in_refund') and (
                    abs(inv.check_total - inv.amount_total) >=
                    (inv.currency_id.rounding / 2.0)
                )):
                    raise osv.except_osv(
                        _('Bad Total!'),
                        _(
                            'Please verify the price of the invoice!\n'
                            'The encoded total does not match the computed '
                            'total.'
                        )
                    )

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise osv.except_osv(
                        _('Error!'),
                        _(
                            "Cannot create the invoice.\n"
                            "The related payment term is probably "
                            "misconfigured as it gives a computed amount "
                            "greater than the total invoiced amount. In "
                            "order to avoid rounding issues, the latest line "
                            "of your payment term must be of type 'balance'."
                        )
                    )

            # one move line per tax line
            iml += ait_obj.move_line_get(cr, uid, inv.id)

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = self._convert_ref(cr, uid, inv.number)

            diff_currency_p = inv.currency_id.id != company_currency
            # create one move line for the total and possibly adjust the other
            # lines amount
            total = 0
            total_currency = 0
            total, total_currency, iml = self.compute_invoice_totals(
                cr, uid, inv, company_currency, ref, iml, context=ctx)
            acc_id = inv.account_id.id

            name = inv['name'] or inv['supplier_invoice_number'] or '/'
            totlines = False
            if inv.payment_term:
                totlines = payment_term_obj.compute(
                    cr, uid, inv.payment_term.id, total,
                    inv.date_invoice or False, context=ctx
                )
            if totlines:
                res_amount_currency = total_currency
                i = 0
                ctx.update({'date': inv.date_invoice})
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(
                            cr, uid, company_currency, inv.currency_id.id,
                            t[1], context=ctx
                        )
                    else:
                        amount_currency = False

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': acc_id,
                        'date_maturity': t[0],
                        'amount_currency': (
                            diff_currency_p and amount_currency or False
                        ),
                        'currency_id': (
                            diff_currency_p and inv.currency_id.id or False
                        ),
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': acc_id,
                    'date_maturity': inv.date_due or False,
                    'amount_currency': (
                        diff_currency_p and total_currency or False
                    ),
                    'currency_id': (
                        diff_currency_p and inv.currency_id.id or False
                    ),
                    'ref': ref,
                })

            date = inv.date_invoice or time.strftime('%Y-%m-%d')

            part = self.pool.get("res.partner")._find_accounting_partner(
                inv.partner_id
            )

            line = map(lambda x: (0, 0, self.line_get_convert(
                cr, uid, x, part.id, date, context=ctx)), iml)

            line = self.group_lines(cr, uid, iml, line, inv)

            journal_id = inv.journal_id.id
            journal = journal_obj.browse(cr, uid, journal_id, context=ctx)
            if journal.centralisation:
                raise osv.except_osv(
                    _('User Error!'),
                    _(
                        'You cannot create an invoice on a centralized '
                        'journal. Uncheck the centralized counterpart box in '
                        'the related journal from the configuration menu.'
                    )
                )

            line = self.finalize_invoice_move_lines(cr, uid, inv, line)

            move_ref = inv.reference and inv.reference or inv.name
            if (
                inv.type in ('in_invoice', 'in_refund') and
                inv.supplier_invoice_number
            ):
                # Use the reference of this invoice as the reference of
                # generated account-move objects.
                move_ref = inv.supplier_invoice_number

            move = {
                'ref': move_ref,
                'line_id': line,
                'journal_id': journal_id,
                'date': date,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
                'object_reference': self._get_object_reference(inv)
            }
            period_id = inv.period_id and inv.period_id.id or False
            ctx.update(company_id=inv.company_id.id,
                       account_period_prefer_normal=True)
            if not period_id:
                period_ids = period_obj.find(
                    cr, uid, inv.date_invoice, context=ctx)
                period_id = period_ids and period_ids[0] or False
            if period_id:
                move['period_id'] = period_id
                for i in line:
                    i[2]['period_id'] = period_id

            ctx.update(invoice=inv)
            move_id = move_obj.create(cr, uid, move, context=ctx)
            new_move_name = move_obj.browse(cr, uid, move_id, context=ctx).name
            # make the invoice point to that move
            self.write(cr, uid, [inv.id], {
                'move_id': move_id,
                'period_id': period_id,
                'move_name': new_move_name
            }, context=ctx)
        self._log_event(cr, uid, ids)
        return True

    def wizard_invoice_cancel(self, cr, uid, ids, context=None):
        invoices = self.browse(cr, uid, ids, context=context)

        if context is None:
            context = {}

        context['active_ids'] = []

        for invoice in invoices:
            # Filter the journal type
            if invoice.journal_id.type == 'situation':
                raise osv.except_osv(
                    _(u"Error"),
                    _(u"You can't reverse a move from a 'situation' journal")
                )
            if invoice.journal_id.is_not_reversable:
                raise osv.except_osv(
                    _(u"Error"),
                    _(u"Reversal is not allowed in this journal.")
                )

            # Only reverse move from 'open' invoices
            if invoice.state != 'open':
                self._workflow_signal(cr, uid, [invoice.id], 'invoice_cancel')
                continue
            context['active_ids'].append(invoice.move_id.id)

        if not context['active_ids']:
            return True

        # Change the state so we are sure not to trigger another transition
        self._workflow_signal(cr, uid, ids, 'invoice_canceling')

        # The wizard will call context['post_function'] if it exists,
        # with 'cr' as first parameters. other parameters will be interpreted
        context['post_function_obj'] = 'account.invoice'
        context['post_function_name'] = '_workflow_signal'
        context['post_function_args'] = [ids, 'invoice_cancel']
        # Same here but this function will be called if there is an error
        context['post_err_function_obj'] = 'account.invoice'
        context['post_err_function_name'] = '_workflow_signal'
        context['post_err_function_args'] = [ids, 'cancel_cancel']
        return {
            'name': 'Create Move Reversals',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.reversal.create',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context
        }

    def action_cancel(self, cr, uid, ids, context=None):
        state = self.read(cr, uid, ids, ['state'], context=context)[0]['state']
        if state == 'draft':
            return super(account_invoice_streamline, self).action_cancel(
                cr, uid, ids, context=context
            )
        return True

    def action_cancel_draft(self, cr, uid, ids, *args):
        invoices = self.browse(cr, uid, ids)
        for invoice in invoices:
            if not invoice.move_id:
                continue
            for line in invoice.move_id.line_id:
                if line.reconcile_id or line.reconcile_partial_id:
                    raise osv.except_osv(
                        _(u"Operation not Permitted"),
                        _(u"Some move lines linked to "
                          u"this invoice are reconciled.")
                    )
        return super(account_invoice_streamline, self).action_cancel_draft(
            cr, uid, ids, *args
        )
