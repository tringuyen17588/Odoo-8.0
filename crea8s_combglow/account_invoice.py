# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013 Camptocamp
#    Copyright 2009-2013 Akretion,
#    Author: Emmanuel Samyn, Raphaël Valyi, Sébastien Beau,
#            Benoît Guillot, Joel Grand-Guillaume
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
from openerp.osv import fields, orm
from datetime import datetime, timedelta
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
from openerp import workflow
from openerp import netsvc
from openerp.tools.translate import _


class sale_order_line_discount(osv.osv_memory):
    _name = "sale.order.line.discount"
    _columns = {
        'name': fields.many2one('sale.order', 'Sale Order'),
        'sale_line': fields.many2many('sale.order.line', 'crea8s_sale_line_discount', 'discount_id', 'sale_line_id', 'Sale Order Lines'),
        'discount': fields.float('Discount(%)'),
    }    
    def get_order(self, cr, uid, context={}):
        if context.get('sale_order_id', False):
            return context['sale_order_id']
        return 0
    _defaults = {
        'name':get_order, 
    }
    def confirm_discount(self, cr, uid, ids, context={}):
        sale_line_obj = self.pool.get('sale.order.line')
        discount = self.browse(cr, uid, ids[0]).discount or 0
        sl_ids = [x.id for x in self.browse(cr, uid, ids[0]).sale_line]
        if sl_ids:
            sale_line_obj.write(cr, uid, sl_ids, {'discount': discount})
        return 1
    
sale_order_line_discount()

class sale_order(osv.osv):
    _inherit = "sale.order"
    
    def setup_discount(self, cr, uid, ids, context={}):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Setup Discount',
            'res_model': 'sale.order.line.discount',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {'sale_order_id': ids[0]},
            'nodestroy': True,
        }
sale_order()

class account_invoice(osv.osv):
    _inherit = "account.invoice"
    _columns = {
        'po_no': fields.char('PO NO.', size=256),
        'ref_no': fields.many2one('res.users', 'Reference'),
    }
account_invoice()

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    _columns = {
        'inv_qty': fields.float('Invoiced Qty', digits_compute= dp.get_precision('Product UoS')),
    }

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           sales order line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        res = {}
        if 1<2:#not line.invoiced:
            if not account_id:
                if line.product_id:
                    account_id = line.product_id.property_account_income.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ.id
                    if not account_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please define income account for this product: "%s" (id:%d).') % \
                                    (line.product_id.name, line.product_id.id,))
                else:
                    prop = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                    account_id = prop and prop.id or False
            uosqty = self._get_line_qty(cr, uid, line, context=context)
            uos_id = self._get_line_uom(cr, uid, line, context=context)
            pu = 0.0
            if uosqty:
                pu = round(line.price_unit * line.product_uom_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
            if context.get('saleline', []):
                if line.id in context['saleline']:
                    temp = line.inv_qty or 0
                    index =  context['saleline'].index(line.id)
                    self.write(cr, uid, [line.id], {'inv_qty': temp + context['change_qty'][index]})
                    uosqty = context['change_qty'][index]
                    
            fpos = line.order_id.fiscal_position or False
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
            if not account_id:
                raise osv.except_osv(_('Error!'),
                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
            res = {
                'name': line.name,
                'sequence': line.sequence,
                'origin': line.order_id.name,
                'account_id': account_id,
                'price_unit': pu,
                'quantity': uosqty,
                'discount': line.discount,
                'uos_id': uos_id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
            }

        return res
    
    def invoice_line_create(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        create_ids = []
        sales = set()
        for line in self.browse(cr, uid, ids, context=context):
            vals = self._prepare_order_line_invoice_line(cr, uid, line, False, context)
            if vals:
                inv_id = self.pool.get('account.invoice.line').create(cr, uid, vals, context=context)
                self.write(cr, uid, [line.id], {'invoice_lines': [(4, inv_id)]}, context=context)
                sales.add(line.order_id.id)
                create_ids.append(inv_id)
        # Trigger workflow events
        wf_service = netsvc.LocalService("workflow")
        for sale_id in sales:
            wf_service.trg_write(uid, 'sale.order', sale_id, cr)
        return create_ids

sale_order_line()

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
        'sale_line_id': fields.many2one('sale.order.line', 'Sale Order Line'),
    }
        
account_invoice_line()

class sale_order_line_invoice_partial(osv.osv_memory):
    _name = 'sale.order.line.invoice.partial'
    _columns = {
        'name': fields.many2one('sale.order.line', 'Order Line'),
        'qty': fields.float('Qty', digits_compute= dp.get_precision('Product UoS')),
        'parent': fields.many2one('sale.order.line.make.invoice', 'Parent'),
    }
    
sale_order_line_invoice_partial()

class sale_advance_payment_inv(osv.osv_memory):
    _inherit = "sale.advance.payment.inv"
    
    def create_invoices(self, cr, uid, ids, context=None):
        """ create invoices for the active sales orders """
        sale_obj = self.pool.get('sale.order')
        act_window = self.pool.get('ir.actions.act_window')
        wizard = self.browse(cr, uid, ids[0], context)
        sale_ids = context.get('active_ids', [])
        if wizard.advance_payment_method == 'all':
            # create the final invoices of the active sales orders
            res = sale_obj.manual_invoice(cr, uid, sale_ids, context)
            if context.get('open_invoices', False):
                return res
            return {'type': 'ir.actions.act_window_close'}

        if wizard.advance_payment_method == 'lines':
            # open the list view of sales order lines to invoice
            res = act_window.for_xml_id(cr, uid, 'sale', 'action_order_line_tree2', context)
            res['context'] = {
                'search_default_order_id': sale_ids and sale_ids[0] or False,
            }
            return res
        assert wizard.advance_payment_method in ('fixed', 'percentage')

        inv_ids = []
        for sale_id, inv_values in self._prepare_advance_invoice_vals(cr, uid, ids, context=context):
            inv_ids.append(self._create_invoices(cr, uid, inv_values, sale_id, context=context))

        if context.get('open_invoices', False):
            return self.open_invoices( cr, uid, ids, inv_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}
sale_advance_payment_inv()

class sale_order_line_make_invoice(osv.osv_memory):
    _inherit = "sale.order.line.make.invoice"
    _description = "Sale OrderLine Make_invoice"
    
    _columns = {
        'inv_line': fields.one2many('sale.order.line.invoice.partial', 'parent', 'Lines'),
    }
    
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        a = order.partner_id.property_account_receivable.id
        if order.partner_id and order.partner_id.property_payment_term.id:
            pay_term = order.partner_id.property_payment_term.id
        else:
            pay_term = False
#         raise osv.except_osv('warning!', str(lines))
        return {
            'name': order.client_order_ref or '',
            'origin': order.name,
            'type': 'out_invoice',
            'reference': "P%dSO%d" % (order.partner_id.id, order.id),
            'account_id': a,
            'partner_id': order.partner_invoice_id.id,
            'invoice_line': [(6, 0, lines)],
            'currency_id' : order.pricelist_id.currency_id.id,
            'comment': order.note,
            'payment_term': pay_term,
            'fiscal_position': order.fiscal_position.id or order.partner_id.property_account_position.id,
            'user_id': order.user_id and order.user_id.id or False,
            'company_id': order.company_id and order.company_id.id or False,
            'date_invoice': fields.date.today(),
            'section_id': order.section_id.id,
        }

    
    def get_line_ids(self, cr, uid, context={}):
        temp = []
        sale_order_line_obj = self.pool.get('sale.order.line')
        if context.get('active_ids', []):
            for x in context.get('active_ids', []):
                br = sale_order_line_obj.browse(cr, uid, x)
                temp.append({'name': x,
                             'qty': br.product_uom_qty and br.product_uom_qty - br.inv_qty or br.product_uos_qty})
        return temp
    
    _defaults = {
        'inv_line': get_line_ids, 
    }
    
    def make_invoices(self, cr, uid, ids, context=None):
        """
             To make invoices.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs
             @param context: A standard dictionary

             @return: A dictionary which of fields with values.

        """
        if context is None: context = {}
        res = False
        invoices = {}

    #TODO: merge with sale.py/make_invoice
        def make_invoice(order, lines):
            """
                 To make invoices.

                 @param order:
                 @param lines:

                 @return:

            """
            inv = self._prepare_invoice(cr, uid, order, lines)
            inv_id = self.pool.get('account.invoice').create(cr, uid, inv)
            return inv_id

        sales_order_line_obj = self.pool.get('sale.order.line')
        sales_order_obj = self.pool.get('sale.order')
        for line in sales_order_line_obj.browse(cr, uid, context.get('active_ids', []), context=context):
            if (line.inv_qty < line.product_uos_qty or line.inv_qty < line.product_uom_qty) and (line.state not in ('draft', 'cancel')):
                if not line.order_id in invoices:
                    invoices[line.order_id] = []
                line_id = sales_order_line_obj.invoice_line_create(cr, uid, [line.id], {'saleline': [x.name.id for x in self.browse(cr, uid, ids[0]).inv_line],
                                                                                        'change_qty': [x.qty for x in self.browse(cr, uid, ids[0]).inv_line]})
                for lid in line_id:
                    invoices[line.order_id].append(lid)
            else:
                raise osv.except_osv('Error !', 'You can not create invoice with quantity greater than required quantity. \n Please check your sale order again !')
        for order, il in invoices.items():
            res = make_invoice(order, il)
            cr.execute('INSERT INTO sale_order_invoice_rel \
                    (order_id,invoice_id) values (%s,%s)', (order.id, res))
            sales_order_obj.invalidate_cache(cr, uid, ['invoice_ids'], [order.id], context=context)
            flag = True
            sales_order_obj.message_post(cr, uid, [order.id], body=_("Invoice created"), context=context)
            data_sale = sales_order_obj.browse(cr, uid, order.id, context=context)
            for line in data_sale.order_line:
                if not line.invoiced:
                    flag = False
                    break
            if flag:
                line.order_id.write({'state': 'progress'})
                workflow.trg_validate(uid, 'sale.order', order.id, 'all_lines', cr)

#        if not invoices:
#            raise osv.except_osv(_('Warning!'), _('Invoice cannot be created for this Sales Order Line due to one of the following reasons:\n1.The state of this sales order line is either "draft" or "cancel"!\n2.The Sales Order Line is Invoiced!'))
        if context.get('open_invoices', False):
            return self.open_invoices(cr, uid, ids, res, context=context)
        return {'type': 'ir.actions.act_window_close'}

    def open_invoices(self, cr, uid, ids, invoice_ids, context=None):
        """ open a view on one of the given invoice_ids """
        ir_model_data = self.pool.get('ir.model.data')
        form_res = ir_model_data.get_object_reference(cr, uid, 'account', 'invoice_form')
        form_id = form_res and form_res[1] or False
        tree_res = ir_model_data.get_object_reference(cr, uid, 'account', 'invoice_tree')
        tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Invoice'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.invoice',
            'res_id': invoice_ids,
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': {'type': 'out_invoice'},
            'type': 'ir.actions.act_window',
        }
