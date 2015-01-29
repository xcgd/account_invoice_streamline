import time

from openerp import fields, models, api, _
from openerp.addons.analytic_structure.MetaAnalytic import MetaAnalytic
from openerp.exceptions import except_orm

from lxml import etree


class account_invoice_line_analytic(models.Model):
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



class account_invoice_streamline(models.Model):
    _name = "account.invoice"
    _inherit = "account.invoice"

    @staticmethod
    def _delete_sheet(res):
        """Delete the 'sheet' element
        but preserve its content.
        """
        tree = etree.XML(res['arch'])
        sheets = tree.xpath('//sheet')
        if sheets:
            etree.strip_tags(tree, 'sheet')
        res['arch'] = etree.tostring(tree)
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """ Display analysis code in account move lines trees
        """
        res = super(account_invoice_streamline, self).fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )
        ans_obj = self.env['analytic.structure']

        line_id_field = res['fields'].get('invoice_line')
        ans_obj.analytic_fields_subview_get(
            'account_invoice_line', line_id_field
        )
        res = self._delete_sheet(res)
        return res

    @api.model
    def line_get_convert(self, line, part, date):
        res = super(account_invoice_streamline, self).line_get_convert(line, part, date)
        res.update(self.env['analytic.structure'].extract_values(
            line, 'account_invoice_line',
            dest_model='account_move_line',
            context=self._context
        ))
        return res

    @staticmethod
    def _get_object_reference(invoice):
        """ Set the move object reference to account_invoice
        """
        return 'account.invoice,%s' % invoice.id

    @api.multi
    def action_move_create(self):
        """ Creates invoice related analytics and financial move lines

            Add reference to the invoice on the move
        """

        account_invoice_tax = self.env['account.invoice.tax']
        account_move = self.env['account.move']

        for inv in self:
            if not inv.journal_id.sequence_id:
                raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            ctx = dict(self._context, lang=inv.partner_id.lang)

            if not inv.date_invoice:
                inv.with_context(ctx).write({'date_invoice': fields.Date.context_today(self)})
            date_invoice = inv.date_invoice

            company_currency = inv.company_id.currency_id
            # create the analytical lines, one move line per invoice line
            iml = inv._get_analytic_lines()
            # check if taxes are all computed
            compute_taxes = account_invoice_tax.compute(inv)
            inv.check_tax_lines(compute_taxes)

            # I disabled the check_total feature
            if self.env['res.users'].has_group('account.group_supplier_inv_check_total'):
                if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding / 2.0):
                    raise except_orm(_('Bad Total!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise except_orm(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # one move line per tax line
            iml += account_invoice_tax.move_line_get(inv.id)

            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
            else:
                ref = inv.number

            diff_currency = inv.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)

            name = inv.name or inv.supplier_invoice_number or '/'
            totlines = []
            if inv.payment_term:
                totlines = inv.with_context(ctx).payment_term.compute(total, date_invoice)[0]
            if totlines:
                res_amount_currency = total_currency
                ctx['date'] = date_invoice
                for i, t in enumerate(totlines):
                    if inv.currency_id != company_currency:
                        amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                    else:
                        amount_currency = False

                    # last line: add the diff
                    res_amount_currency -= amount_currency or 0
                    if i + 1 == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': inv.account_id.id,
                        'date_maturity': t[0],
                        'amount_currency': diff_currency and amount_currency,
                        'currency_id': diff_currency and inv.currency_id.id,
                        'ref': ref,
                        })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': inv.account_id.id,
                    'date_maturity': inv.date_due,
                    'amount_currency': diff_currency and total_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref
                })

            date = date_invoice

            part = self.env['res.partner']._find_accounting_partner(inv.partner_id)

            line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
            line = inv.group_lines(iml, line)

            journal = inv.journal_id.with_context(ctx)
            if journal.centralisation:
                raise except_orm(_('User Error!'),
                                 _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = inv.finalize_invoice_move_lines(line)

            if (
                inv.type in ('in_invoice', 'in_refund') and
                inv.supplier_invoice_number
            ):
                # Use the reference of this invoice as the reference of generated account_move_object
                move_ref = inv.supplier_invoice_number
            else:
                move_ref = inv.reference or inv.name

            move_vals = {
                'ref': move_ref,
                'line_id': line,
                'journal_id': journal.id,
                'date': inv.date_invoice,
                'narration': inv.comment,
                'company_id': inv.company_id.id,
                'object_reference': self._get_object_reference(inv),
            }
            ctx['company_id'] = inv.company_id.id
            period = inv.period_id
            if not period:
                period = period.with_context(ctx).find(date_invoice)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id

            ctx['invoice'] = inv
            move = account_move.with_context(ctx).create(move_vals)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
                }
            inv.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
        self._log_event()
        return True

    @api.model
    def wizard_invoice_cancel(self):
        invoices = self

        context = self._context.copy()

        context['active_ids'] = []

        for invoice in invoices:
            # Filter the journal type
            if invoice.journal_id.type == 'situation':
                raise except_orm(
                    _(u"Error"),
                    _(u"You can't reverse a move from a 'situation' journal")
                )
            if invoice.journal_id.is_not_reversable:
                raise except_orm(
                    _(u"Error"),
                    _(u"Reversal is not allowed in this journal.")
                )

            # Only reverse move from 'open' invoices
            if invoice.state != 'open':
                self._workflow_signal('invoice_cancel')
                continue
            context['active_ids'].append(invoice.move_id.id)

        if not context['active_ids']:
            return True

        # Change the state so we are sure not to trigger another transition
        self._workflow_signal('invoice_canceling')

        # The wizard will call context['post_function'] if it exists,
        # with 'cr' as first parameters. other parameters will be interpreted
        context['post_function_obj'] = 'account.invoice'
        context['post_function_name'] = '_workflow_signal'
        context['post_function_args'] = [self.ids, 'invoice_cancel']
        # Same here but this function will be called if there is an error
        context['post_err_function_obj'] = 'account.invoice'
        context['post_err_function_name'] = '_workflow_signal'
        context['post_err_function_args'] = [self.ids, 'cancel_cancel']
        return {
            'name': 'Create Move Reversals',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.reversal.create',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context
        }

    @api.multi
    def action_cancel(self):
        state = self.read(['state'])[0]['state']
        if state == 'draft':
            return super(account_invoice_streamline, self).action_cancel()
        return True

    @api.multi
    def action_cancel_draft(self):
        invoices = self
        for invoice in invoices:
            if not invoice.move_id:
                continue
            for line in invoice.move_id.line_id:
                if line.reconcile_id or line.reconcile_partial_id:
                    raise except_orm(
                        _(u"Operation not Permitted"),
                        _(u"Some move lines linked to "
                          u"this invoice are reconciled.")
                    )
        return super(account_invoice_streamline, self).action_cancel_draft()
