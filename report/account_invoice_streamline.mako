<style type="text/css">
${css}
</style>
%for i, order in enumerate(objects):
<%page expression_filter="entity"/>
<% setLang(order.partner_id.lang) %>
<%!
        def formatText(text):
            return '<br />'.join(text.splitlines())
%>
<div class="address">
    <div class="addressright">
        <table class="recipient">
            %if invoice_type == 'normal':
    %if order.type == 'in_refund':
	       <tr><th class="addresstitle">FOURNISSEUR :</th></tr>
    %endif
    %if order.type == 'out_refund':
	       <tr><th class="addresstitle">CLIENT :</th></tr>
    %endif
    %if order.type == 'in_invoice':
            <tr><th class="addresstitle">FOURNISSEUR :</th></tr>
    %endif
    %if order.type == 'out_invoice':
            <tr><th class="addresstitle">CLIENT :</th></tr>
    %endif
%endif
            %if order.partner_id:
            <tr><td class="name">${order.partner_id.parent_id.name or ''}</td></tr>
            <tr><td class="name">${order.partner_id.title and order.partner_id.title.name or ''} ${order.partner_id.name }</td></tr>
            <tr><td> ${order.partner_id.street or ''} </td></tr>
            <tr><td> ${order.partner_id.street2 or ''} </td></tr>
            <tr><td> ${order.partner_id.zip or ''} ${order.partner_id.city or ''}</td></tr>
            %endif
        </table>

        <div class="date">
            <p>Fait &agrave; Paris, le  ${ order.date_invoice}</p>
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
    %if invoice_type == 'normal':
    %if order.type == 'in_refund':
	       <h1 class="text">Avoir fournisseur</h1>
    %endif
    %if order.type == 'out_refund':
	       <h1 class="text">Avoir client</h1>
    %endif
	%if order.type == 'in_invoice':
	       <h1 class="text">Facture Fournisseur</h1>
	%endif
	%if order.type == 'out_invoice':
	       <h1 class="text">Facture client</h1>
	%endif
%endif
</div>

<div class="basic_table">
    <center>
    <table class="basic_table">
    <thead>
        <tr>
%if invoice_type == 'normal':
    %if order.type == 'in_refund':
        <th>Num&eacute;ro d'avoir</th>
        <th>Date d'avoir</th>
        <th>Fournisseur</th>
    %endif
    %if order.type == 'out_refund':
        <th>Num&eacute;ro d'avoir</th>
        <th>Date d'avoir</th>
        <th>Client</th>
    %endif
    %if order.type == 'in_invoice':
        <th>Num&eacute;ro de facture</th>
        <th>Date de Facturation</th>
        <th>Fournisseur</th>

	%endif
	%if order.type == 'out_invoice':
	    <th>Num&eacute;ro de facture</th>
        <th>Date de facturation</th>
        <th>Client</th>
	%endif
%endif
        </tr>
        <tr>
%if invoice_type == 'normal':
    %if order.type == 'in_refund':
        <td>${order.number or ''}</td>
        <td>${order.date_invoice or ''}</td>
        <td>${order.partner_id.name }</td>
    %endif
    %if order.type == 'out_refund':
        <td>${order.number or ''}</td>
        <td>${order.date_invoice or ''}</td>
        <td>${order.partner_id.name }</td>
    %endif
    %if order.type == 'in_invoice':
        <td>${order.supplier_invoice_number or ''}</td>
        <td>${order.date_invoice or ''}</td>
        <td>${order.partner_id.name }</td>

	%endif
	%if order.type == 'out_invoice':
	    <td>${order.number or ''}</td>
        <td>${order.date_invoice or ''}</td>
        <td>${order.partner_id.name }</td>
	%endif
%endif
        </tr>
    </thead>
    </table>
    </center>
</div>
<table class="list_table">
    <thead>
        <tr>
            <th>Produit</th>
            <th>Description</th>
            <th class="amount">Quantit&eacute;</th>
            <th class="amount">Prix Unitaire</th>
            <th class="amount">Montant HT</th>
        </tr>
    </thead>
    <tbody>
    %for line in order.invoice_line:
        <tr class="line">
            <td>${ line.product_id.name or ''}</td>
            <td style="text-align:center">${ line.name or '' }</td>
            <td class="amount" width="8%" style="text-align:center">${ line.quantity or '' }</td>
            <td class="amount" width="12%" style="text-align:center">${ formatLang(line.price_unit, currency_obj=order.currency_id or '') }</td>
            <td class="amount" width="14%" style="text-align:center">${ formatLang(line.price_subtotal, currency_obj=order.currency_id or '') }</td>
        </tr>
    %endfor
    </tbody>
    </table>
    <p>&nbsp;</p>
    <table class="totaux">
    <tfoot class="totals">
        <tr>
            <td colspan="4"/>
            <td><b>Total HT :</b></td>
            <td class="amount" style="white-space:nowrap">${ formatLang(order.amount_untaxed, currency_obj=order.currency_id or '') }</td>
        </tr>
        <tr>
            <td colspan="4"/>
            <td><b>Total TVA :</b></td>
            <td class="amount" style="white-space:nowrap">${ formatLang(order.amount_tax, currency_obj=order.currency_id or '') }</td>
        </tr>
        <tr>
            <td colspan="4"/>
            <td><b>Total TTC :</b></td>
            <td class="amount" style="white-space:nowrap">${ formatLang(order.amount_total, currency_obj=order.currency_id or '') }</td>
        </tr>
    </tfoot>
    </table>
     <p>&nbsp;</p>
    <table>
    %if order.comment:
        <tr>
            <p class="descriptif"><u>Informations compl&eacute;mentaires</u></p>
            <p class="comment">${order.comment|formatText or ''} </p>
        </tr>
        %endif
    </table>


<!--FIXME Resolve multi footer -->
%if i < len(objects) - 1:
    <div style="page-break-after:always"></div>
%endif
%endfor
