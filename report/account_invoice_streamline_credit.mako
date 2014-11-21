## -*- coding: utf-8 -*-
<style type="text/css">
${css}
</style>
%for i, order in enumerate(objects):
<% setLang(order.partner_id.lang) %>
<%page expression_filter="entity"/>
<%!
        def formatText(text):
            return '<br />'.join(text.splitlines())
%>

<div class="address">
    <div class="addressright">
        <table class="recipient">
        <tr><th class="addresstitle">${ _(u'CLIENT') } :</th></tr>
            %if order.partner_id:
            <tr><td class="name">${order.partner_id.parent_id.name or ''}</td></tr>
            <tr><td class="name">${order.partner_id.title and order.partner_id.title.name or ''} ${order.partner_id.name }</td></tr>
            <tr><td> ${order.partner_id.street or ''} </td></tr>
            <tr><td> ${order.partner_id.street2 or ''} </td></tr>
            <tr><td> ${order.partner_id.zip or ''} ${order.partner_id.city or ''}</td></tr>
            %endif
        </table>

       <div class="date">
        <p> Fait à Paris, le  ${ order.date_invoice}</p>
        </div>

    </div>
    <div class="addressleft">
        <table class="shipping">
            <tr><th class="addresstitle"></th></tr>
            %if order.company_id.partner_id.parent_id:
            <tr><td class="name">${order.company_id.partner_id.parent_id.name or ''}</td></tr>
            <% address_lines = order.company_id.partner_id.contact_address.split("\n")[1:] %>
            %else:
            <% address_lines = order.company_id.partner_id.contact_address.split("\n") %>
            %endif
            <tr><td class="name">${order.company_id.partner_id.title and order.company_id.partner_id.title.name or ''} ${order.company_id.partner_id.name }</td></tr>
            %for part in address_lines:
                %if part:
                <tr><td>${ part }</td></tr>
                %endif
            %endfor
       </table>
    </div>
</div>

<div class="orderinfo">
       <h1 class="text"><u>${ invoice_title }</u></h1>
</div>

<div class="basic_table">
    <center>
    <table class="basic_table">
    <thead>
        <tr>
            <th style="width:33%">${_(u"Numéro de Facture")}</th>
            <th style="width:33%">${_(u"Date de Facturation")}</th>
            <th style="width:34%">${_(u"Client")}</th>
        </tr>
        <tr>
            <td>${order.number or ''}</td>
            <td>${order.date_invoice or ''}</td>
            <td>${order.partner_id.name }</td>
        </tr>
    </thead>
    </table>
    </center>
</div>
<table class="list_table">
    <thead>
        <tr>
            <th>${ _(u"Produit") }</th>
            <th>${ _(u"Description") }</th>
            <th class="amount">${_(u"Quantité")}</th>
            <th class="amount">${_(u"Prix Unitaire")}</th>
            <th class="amount">${_(u"Montant HT ")}</th>
        </tr>
    </thead>
    <tbody>
    %for line in order.invoice_line:
        <tr class="line">
            <td>${ line.product_id.name or ''}</td>
            <td style="text-align:center">${ line.name or '' }</td>
            <td class="amount" width="8%" style="text-align:center">${ line.quantity }</td>
            <td class="amount" width="12%" style="text-align:center">${ formatLang(line.price_unit, currency_obj=order.currency_id) }</td>
            <td class="amount" width="14%" style="text-align:center">${ formatLang(line.price_subtotal, currency_obj=order.currency_id) }</td>
        </tr>
    %endfor
    </tbody>
    </table>
     <p>&nbsp;</p>
    <table class="totaux">
    <tfoot class="totals">
        <tr>
            <td colspan="4"/>
            <td><b>${_(u"Total HT ") } :</b></td>
            <td class="amount" style="white-space:nowrap">${ formatLang(order.amount_untaxed, currency_obj=order.currency_id) }</td>
        </tr>
        <tr>
            <td colspan="4"/>
            <td><b>${_(u"Total TVA")} :</b></td>
            <td class="amount" style="white-space:nowrap">${ formatLang(order.amount_tax, currency_obj=order.currency_id) }</td>
        </tr>
        <tr>
            <td colspan="4"/>
            <td><b>${_(u"Total TTC")} :</b></td>
            <td class="amount" style="white-space:nowrap">${ formatLang(order.amount_total, currency_obj=order.currency_id) }</td>
        </tr>
    </tfoot>
    </table>
    <br/><br/>
    <table>
    %if order.comment:
        <tr>
            <p class="descriptif"><u>${_(u"Informations complémentaires" or '') }</u></p>
            <p class="comment">${order.comment|formatText} </p>
        </tr>
        %endif
    </table>





</table></br></br>
%if i < len(objects) - 1:
    <div style="page-break-after:always"></div>
%endif
%endfor
