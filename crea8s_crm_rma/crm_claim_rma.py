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

from openerp.osv import fields, orm, osv
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import netsvc
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta
import time


class crea8s_crm_claim_exchange(orm.Model):
    _name = 'crea8s.crm.claim.exchange'
    
    def get_claim_name(self, cr, uid, context={}):
        if context.get('claim_name', False):
            return context['claim_name']
        return ''
    
    _columns = {
        'name': fields.char('Name', size=256),
        'product_id': fields.many2one('product.product', 'Fault Product'),
        'ex_product_id': fields.many2one('product.product', 'Exchange Product'),
        'fa_qty': fields.float('Quantity'),
        'ex_qty': fields.float('Quantity'),
        'claim_id': fields.many2one('crm.claim', 'Claim'),
    }
    
    _defaults = {
        'name': get_claim_name, 
    }
    
crea8s_crm_claim_exchange()

class stock_picking(orm.Model):
    _inherit = 'stock.picking'
    _columns = {
        'claim_id': fields.many2one('crm.claim', 'Claim'),
    }
stock_picking()

class crm_claim(orm.Model):
    _inherit = 'crm.claim'
    _columns = {
        'product_id': fields.many2one('product.product', 'Fault Product'),
        'ex_prod_ids': fields.one2many('crea8s.crm.claim.exchange', 'claim_id', 'Exchange Information'),
        'ex_product_id': fields.many2one('product.product', 'Exchange Product'),
        'qty': fields.float('Quantity'),
        'ttype': fields.selection(
            [('ccredit', 'Customer Credit Note'),
             ('scredit', 'Supplier Credit Note'),
             ('cnew', 'Exchange With Customer'),
             ('snew', 'Exchange With Supplier')
             ], string='Option'),
        'def_lot_id': fields.many2one('stock.location', 'Defective Warehouse'),
        'suplier_id': fields.many2one('res.partner', 'Supplier'),
        'lot_id': fields.many2one('stock.location', 'Main Warehouse'),
#        'invoice_ids': fields.one2many('account.invoice', 'claim_id', 'Refunds'),
        'picking_ids': fields.one2many('stock.picking', 'claim_id', 'Picking List'),
    }
    
    def create_picking_list(self, cr, uid, ids, common_dest_loc_id, common_from_loc_id, p_type, partner_id, prod_id, context=None):
        if context is None:
            context = {}

        picking_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')
        wf_service = netsvc.LocalService("workflow")
        for record in self.browse(cr, uid, ids): 
            picking_id = picking_obj.create(
                cr, uid,
                {'origin': record.number,
                 'type': p_type,
                 'move_type': 'one',  # direct
                 'state': 'draft',
                 'auto_picking': 1,
                 'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                 'partner_id': partner_id,
                 'invoice_state': "none",
                 'company_id': record.company_id.id,
                 'location_id': common_from_loc_id,
                 'location_dest_id': common_dest_loc_id,
                 'claim_id': record.id,
                 }, context=context)
        # Create picking lines
            product_id = 0
            if prod_id:
                prod_obj = self.pool.get('product.product')
                for idd in prod_id:
                    product_id = prod_obj.browse(cr, uid, idd[0])
                    move_id = move_obj.create(cr, uid,
                    {'name': product_id.name_template,
                     'priority': '0',
                     'date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                     'date_expected': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                     'product_id': product_id.id,
                     'product_qty': idd[1] and idd[1] or 0,
                     'product_uom': product_id.uom_id.id,
                     'partner_id': partner_id,
                     'picking_id': picking_id,
                     'state': 'draft',
                     'price_unit': product_id.list_price and product_id.list_price or 0,
                     'company_id': record.company_id.id,
                     'location_id': common_from_loc_id,
                     'location_dest_id': common_dest_loc_id, 
                     }, context=context)
                    self.pool.get('stock.move').force_assign(cr, uid, [move_id])
        
        if picking_id:
            wf_service.trg_write(uid, 'stock.picking', picking_id, cr)
            wf_service.trg_validate(uid, 'stock.picking',
                                    picking_id, 'button_confirm', cr)
        return picking_id
    
    # If "Create" button pressed
    def action_create_picking(self, cr, uid, ids, context=None):
        inv_obj = self.pool.get('account.invoice')
        journal_obj = self.pool.get('account.journal')
        location_obj = self.pool.get('stock.location')
        cus_lot_id = location_obj.search(cr, uid, [('usage', '=', 'customer')])
        cus_lot_id = cus_lot_id and cus_lot_id[0] or 0
        sup_lot_id = location_obj.search(cr, uid, [('usage', '=', 'supplier')])
        sup_lot_id = sup_lot_id and sup_lot_id[0] or 0
        if context is None:
            context = {}
        for record in self.browse(cr, uid, ids):
            if record.ttype == 'cnew':
                partner_id = record.partner_id and record.partner_id.id or 0
                # Get fault product from customer
                self.create_picking_list(cr, uid, ids, record.def_lot_id.id, cus_lot_id, 'in', partner_id, [[fprod.product_id.id, fprod.fa_qty] for fprod in record.ex_prod_ids], context)
                # exchange new product to customer
                self.create_picking_list(cr, uid, ids, cus_lot_id, record.lot_id.id, 'out', partner_id, [[fprod.ex_product_id and fprod.ex_product_id.id or fprod.product_id.id, fprod.ex_qty] for fprod in record.ex_prod_ids], context)
            elif record.ttype == 'snew':
                partner_id = record.suplier_id and record.suplier_id.id or 0
            #    Exchange fault product into supplier
                self.create_picking_list(cr, uid, ids, sup_lot_id, record.def_lot_id.id, 'out', partner_id, [[fprod.product_id.id, fprod.fa_qty] for fprod in record.ex_prod_ids], context)
            #    Get new product from supplier
                self.create_picking_list(cr, uid, ids, record.lot_id.id, sup_lot_id, 'in', partner_id, [[fprod.ex_product_id and fprod.ex_product_id.id or fprod.product_id.id, fprod.ex_qty] for fprod in record.ex_prod_ids], context)
            elif record.ttype == 'scredit':
                journal_id = journal_obj.search(cr, uid, [('type', '=', 'purchase_refund')])
                order = self.browse(cr, uid, ids[0])
                partner_id = record.suplier_id and record.suplier_id.id or 0
                self.create_picking_list(cr, uid, ids, sup_lot_id, record.def_lot_id.id, 'out', partner_id, [[fprod1.product_id.id, fprod1.fa_qty] for fprod1 in record.ex_prod_ids], context)
                invoice_vals = {
                    'name': order.name or '',
                    'origin': order.number,
                    'type': 'in_refund',
                    'account_id': order.suplier_id and order.suplier_id.property_account_payable.id or 0,
                    'partner_id': order.suplier_id and order.suplier_id.id or 0,
                    'journal_id': journal_id and journal_id[0] or 0,
                    'currency_id': order.suplier_id and order.suplier_id.property_product_pricelist_purchase.currency_id.id,
                    'claim_id': ids[0],
                    'date_invoice': order.date,
                    'company_id': order.company_id.id,
                    }
                inv_id = inv_obj.create(cr, uid, invoice_vals)
                for fprod2 in record.ex_prod_ids:
                    inv_line = {
                        'name': fprod2.product_id and fprod2.product_id.name_template or '',
                        'origin': order.number,
                        'account_id': fprod2.product_id and fprod2.product_id.property_account_expense.id or 0,
                        'price_unit': fprod2.product_id and fprod2.product_id.price or 0,
                        'quantity': fprod2.fa_qty and fprod2.fa_qty or 0,
                        'discount': 0,
                        'invoice_id': inv_id,
                        'uos_id': fprod2.product_id and fprod2.product_id.uom_id.id or 0,
                        'product_id': fprod2.product_id.id or False,
                    }
                    self.pool.get('account.invoice.line').create(cr, uid, inv_line)
            elif record.ttype == 'ccredit':
                journal_id = journal_obj.search(cr, uid, [('type', '=', 'sale_refund')])
                order = self.browse(cr, uid, ids[0])
                partner_id = record.partner_id and record.partner_id.id or 0
                self.create_picking_list(cr, uid, ids, record.def_lot_id.id, cus_lot_id, 'in', partner_id, [[fprod.product_id.id, fprod.fa_qty] for fprod in record.ex_prod_ids], context)
                invoice_vals = {
                    'name': order.name or '',
                    'origin': order.number,
                    'type': 'out_refund',
                    'account_id': order.partner_id and order.partner_id.property_account_receivable.id or 0,
                    'partner_id': order.partner_id and order.partner_id.id or 0,
                    'journal_id': journal_id and journal_id[0] or 0,
                    'currency_id': order.partner_id.property_product_pricelist.currency_id.id,
                    'claim_id': ids[0],
                    'date_invoice': order.date,
                    'company_id': order.company_id.id,
            }            
                inv_id = inv_obj.create(cr, uid, invoice_vals)
                for fprod3 in record.ex_prod_ids:
                    
                    inv_line = {
                        'name': fprod3.product_id and fprod3.product_id.name_template or '',
                        'origin': order.number,
                        'account_id': fprod3.product_id and fprod3.product_id.property_account_income.id or 0,
                        'price_unit': fprod3.product_id and fprod3.product_id.price or 0,
                        'quantity': fprod3.fa_qty and fprod3.fa_qty or 0,
                        'discount': 0,
                        'invoice_id': inv_id,
                        'uos_id': fprod3.product_id and fprod3.product_id.uom_id.id or 0,
                        'product_id': fprod3.product_id.id or False,
                    }
                    self.pool.get('account.invoice.line').create(cr, uid, inv_line)
        stage_id = self.pool.get('crm.claim.stage').search(cr, uid, [('state', '=', 'done')])
        stage_id = stage_id and stage_id[0] or 0
        return self.write(cr, uid, ids, {'state': 'done', 'stage_id': stage_id})
        
    def get_stage_id(self, cr, uid, context={}):
        stage_id = self.pool.get('crm.claim.stage').search(cr, uid, [('state', '=', 'open')])
        stage_id = stage_id and stage_id[0] or 0
        return stage_id
    
    def btn_confirm(self, cr, uid, ids ,context={}):
        self.action_create_picking(cr, uid, ids)
        stage_id = self.pool.get('crm.claim.stage').search(cr, uid, [('name', '=', 'Settled')])
        stage_id = stage_id and stage_id[0] or 0
        return self.write(cr, uid, ids, {'state': 'done', 'stage_id': stage_id})

#    _defaults = {
#        'state': 'open',
#        'stage_id': get_stage_id,
#    }
     
crm_claim()

class product_claim(osv.osv_memory):
    _name = 'product.claim'

    _columns = {
        'name': fields.many2one('product.product', 'Product'),
        'qty': fields.float('Quantity'),
        'partner_id': fields.many2one('res.partner', 'Partner'),
        'stock_id': fields.many2one('stock.location', 'Warehouse'),
        'type': fields.selection(
            [('customer', 'Customer'),
             ('supplier', 'Supplier')], string='Type'),
        'cus_opt': fields.selection(
            [('ccredit', 'Customer Credit Note'),
             ('cnew', 'Exchange With Customer')], string='Option'),
        'sup_opt': fields.selection(
            [('scredit', 'Supplier Credit Note'),
             ('snew', 'Exchange With Supplier')], string='Option'),
    }

    def get_invoice(self,cr,uid,context={}):
        if context.get('active_id'):
            return context['active_id']
        return 0

    _defaults = {
        'name': get_invoice,
        'qty': 1,
    }
    def create_claim(self, cr, uid, ids, context=None):
        context = {}
        claim_obj = self.pool.get('crm.claim')
        for record in self.browse(cr, uid, ids):
            claim_id = claim_obj.create(cr, uid, {
                    'name': 'Issue for product %s'%(record.name.name_template and record.name.name_template or ''),
                    'claim_type': record.type,
                    'ttype': record.type == 'customer' and record.cus_opt or record.sup_opt,
                    'date': datetime.now(),
                    'warehouse_id':claim_obj._get_default_warehouse(cr, uid,context),
                    'partner_id': record.partner_id and record.partner_id.id or 0,
                    'delivery_address_id': record.partner_id and record.partner_id.id or 0,
                    'product_id': record.name and record.name.id or 0,
                    'qty': record.qty and record.qty or 0, 
                })
        return {
        'view_type':'form',
        'view_mode':'tree,form',
        'res_model':'crm.claim',
        'view_id':False,
        'type':'ir.actions.act_window',
        'domain':[('id', '=', claim_id)],
        'context':{},
      }

product_claim()