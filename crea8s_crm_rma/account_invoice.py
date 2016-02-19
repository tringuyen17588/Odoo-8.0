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
from tools.translate import _
from datetime import datetime, timedelta
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP, float_compare

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        result = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id=account_id, context=context)
        if line.brand_id:
            result.update({'brand_id': line.brand_id and line.brand_id.id or 0,})
        return result
    
    _columns = {
        'brand_id': fields.many2one('crea8s.product.brand', 'Brand'),
    }
    
    def product_id_change(self, cr, uid, ids, pricelist, product, qty=0,
            uom=False, qty_uos=0, uos=False, name='', partner_id=False,
            lang=False, update_tax=True, date_order=False, packaging=False, fiscal_position=False, flag=False, context=None):
        result = super(sale_order_line, self).product_id_change(cr, uid, ids, pricelist, product, qty=qty, uom=uom, qty_uos=qty_uos, \
            uos=uos, name=name, partner_id=partner_id, lang=lang, update_tax=update_tax, date_order=date_order, \
            packaging=packaging, fiscal_position=fiscal_position, flag=flag, context=context)
        prod_obj = self.pool.get('product.product')
        if product:
            lst_brand = [x.brand_id and x.brand_id.id or 0 for x in prod_obj.browse(cr, uid, product).brand_id]
            result['domain'].update({'brand_id': [('id', 'in', lst_brand)]})
        return result
    
sale_order_line()

class sale_order(osv.osv):
    _inherit = "sale.order"
    _columns = {
        'claim_id': fields.many2one('crm.claim', 'Claim'),
    }    
    #    For picking list
    def _prepare_order_line_move(self, cr, uid, order, line, picking_id, date_planned, context=None):
        result = super(sale_order, self)._prepare_order_line_move(cr, uid, order, line, picking_id, date_planned, context=context)
        if line.brand_id:
            result.update({'brand_id': line.brand_id and line.brand_id.id or 0})
        return result

sale_order()

class account_invoice(orm.Model):
    _inherit = "account.invoice"
    _columns = {
        'claim_id': fields.many2one('crm.claim', 'Claim'),
        'inventory_id': fields.many2one('stock.inventory', 'Inventory'),
    }
    def get_claim_default(self, cr, uid, context={}):
        if context.get('claims_ids', False):
            return context['claims_ids']
        return 0
    
    def get_claim_info_line(self, cr, uid, context={}):
        claim_line_obj = self.pool.get('claim.line')
        inven_line_obj = self.pool.get('stock.move')
        result = []
        if context.get('crea8s_claim_line', False):
            for idd in claim_line_obj.browse(cr, uid, context['crea8s_claim_line']):
#                if idd.warranty_type =='':
                result.append({'product_id': idd.product_id and idd.product_id.id or 0, 
                               'name': idd.product_id.partner_ref,
                               'account_id': idd.product_id and (idd.product_id.property_account_expense and idd.product_id.property_account_expense.id \
                                             or  (idd.product_id.categ_id.property_account_expense_categ and idd.product_id.categ_id.property_account_expense_categ.id or 0))\
                                             or 0 ,
                               'brand_id': idd.brand_id and idd.brand_id.id or 0, 
                               'uos_id': idd.product_id and idd.product_id.uom_id.id or 0,
                               'price_unit': idd.product_id and idd.product_id.standard_price or 0, 
                               'quantity': idd.product_returned_quantity and idd.product_returned_quantity or (idd.product_qty and idd.product_qty or (idd.product_uos_qty and idd.product_uos_qty or 0)), 
                })
        elif context.get('crea8s_inventory_line', False):
            for iddm in inven_line_obj.browse(cr, uid, context['crea8s_inventory_line']):
                result.append({'product_id': iddm.product_id and iddm.product_id.id or 0, 
                               'name': iddm.product_id.partner_ref,
                               'account_id': iddm.product_id and (iddm.product_id.property_account_expense and iddm.product_id.property_account_expense.id \
                                             or  (iddm.product_id.categ_id.property_account_expense_categ and iddm.product_id.categ_id.property_account_expense_categ.id \
                                            or 0))  or 0 ,
                               'brand_id': iddm.brand_id and iddm.brand_id.id or 0, 
                               'uos_id': iddm.product_id and iddm.product_id.uom_id.id or 0,
                               'price_unit': iddm.product_id and iddm.product_id.standard_price or 0, 
                               'quantity': iddm.product_qty and iddm.product_qty or (iddm.product_uos_qty and iddm.product_uos_qty or 0), 
                })
                
#                
        return result

    
    _defaults = {
        'claim_id': get_claim_default,
        'invoice_line': get_claim_info_line,
    }

    def _refund_cleanup_lines(self, cr, uid, lines, context=None):
        """ Override when from claim to update the quantity and link to the
        claim line."""
        if context is None:
            context = {}
        new_lines = []
        inv_line_obj = self.pool.get('account.invoice.line')
        claim_line_obj = self.pool.get('claim.line')
        # check if is an invoice_line and we are from a claim
        if not (context.get('claim_line_ids') and lines and
                lines[0]._name == 'account.invoice.line'):
            return super(account_invoice, self)._refund_cleanup_lines(
                cr, uid, lines, context=None)

        for __, claim_line_id, __ in context.get('claim_line_ids'):
            line = claim_line_obj.browse(cr, uid, claim_line_id,
                                         context=context)
            if not line.refund_line_id:
                # For each lines replace quantity and add claim_line_id
                inv_line = inv_line_obj.browse(cr, uid,
                                               line.invoice_line_id.id,
                                               context=context)
                clean_line = {}
                for field_name, field in inv_line._all_columns.iteritems():
                    column_type = field.column._type
                    if column_type == 'many2one':
                        clean_line[field_name] = inv_line[field_name].id
                    elif column_type not in ('many2many', 'one2many'):
                        clean_line[field_name] = inv_line[field_name]
                    elif field_name == 'invoice_line_tax_id':
                        tax_list = []
                        for tax in inv_line[field_name]:
                            tax_list.append(tax.id)
                        clean_line[field_name] = [(6, 0, tax_list)]
                clean_line['quantity'] = line['product_returned_quantity']
                clean_line['claim_line_id'] = [claim_line_id]
                new_lines.append(clean_line)
        if not new_lines:
            # TODO use custom states to show button of this wizard or
            # not instead of raise an error
            raise orm.except_orm(
                _('Error !'),
                _('A refund has already been created for this claim !'))
        return [(0, 0, line) for line in new_lines]

    def _prepare_refund(self, cr, uid, invoice, date=None, period_id=None,
                        description=None, journal_id=None, context=None):
        if context is None:
            context = {}
        result = super(account_invoice, self)._prepare_refund(
            cr, uid, invoice,
            date=date, period_id=period_id, description=description,
            journal_id=journal_id, context=context)
        if context.get('claim_id'):
            result['claim_id'] = context['claim_id']
        return result
    
    def invoice_validate(self, cr, uid, ids, context=None):
        result = super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)
        location_obj = self.pool.get('stock.location')
        pick_obj = self.pool.get('stock.picking')
        stk_move_obj = self.pool.get('stock.move')
        for order in self.browse(cr, uid, ids):
            if order.type == 'in_refund' and order.claim_id:
                pick_name = self.pool.get('ir.sequence').get(cr, uid, 'stock.picking.out')
                picking_id = pick_obj.create(cr, uid, {
                    'name': pick_name,
                    'origin': order.name,
                    'date': datetime.now(),
                    'type': 'out',
                    'state': 'done',
                    'auto_picking':True,
                    'move_type': 'one',
                    'claim_id': order.claim_id.id,
                    'partner_id': order.partner_id.id,
                    'note': 'Fault',
                    'invoice_state': 'none',
                    'company_id': order.company_id.id})
                location_id = location_obj.search(cr, uid, [('is_defect', '=', True)])
                location_id = location_id and location_id[0] or 0
                output_id = location_obj.search(cr, uid, [('usage', '=', 'supplier')])
                output_id = output_id and output_id[0] or 0
                for line in order.invoice_line:
                    stk_move_obj.create(cr, uid, {
                        'name': line.name,
                        'picking_id': picking_id,
                        'product_id': line.product_id.id,
                        'date': datetime.now(),
                        'date_expected': datetime.now(),
                        'product_qty': line.quantity,
                        'brand_id': line.brand_id and line.brand_id.id or 0,
                        'product_uom': line.uos_id.id,
                        'product_uos_qty': line.quantity,
                        'product_uos': line.quantity,
#                        'product_packaging': line.product_packaging and line.product_packaging.id or 0,
                        'partner_id': line.partner_id.id,
                        'location_id': location_id,
                        'location_dest_id': output_id,
                        'tracking_id': False,
                        'state': 'done',
                        'company_id': order.company_id.id,
                        'price_unit': line.price_unit or 0.0})
        return result
    

account_invoice()

class account_invoice_line(orm.Model):
    _inherit = "account.invoice.line"
    _columns = {
        'brand_id': fields.many2one('crea8s.product.brand', 'Brand'),
    }
    
    def create(self, cr, uid, vals, context=None):
        claim_line_id = False
        if vals.get('claim_line_id'):
            claim_line_id = vals['claim_line_id']
            del vals['claim_line_id']
        line_id = super(account_invoice_line, self).create(
            cr, uid, vals, context=context)
        if claim_line_id:
            claim_line_obj = self.pool.get('claim.line')
            claim_line_obj.write(cr, uid, claim_line_id,
                                 {'refund_line_id': line_id},
                                 context=context)
        return line_id

    def product_id_change(self, cr, uid, ids, product, uom_id, qty=0, name='', type='out_invoice', partner_id=False, fposition_id=False, price_unit=False, currency_id=False, context=None, company_id=None):
        result = super(account_invoice_line, self).product_id_change(cr, uid, ids, product, uom_id, qty=0, name='', type=type, partner_id=partner_id, fposition_id=fposition_id, price_unit=price_unit, currency_id=currency_id, context=context, company_id=company_id)
        if result.get('domain', False):
            if product:
                lst_brand = [x.id for x in self.pool.get('product.product').browse(cr, uid, product).brand_id]
                result['domain'].update({'brand_id': [('id','in', lst_brand)]})
        return result

account_invoice_line()


