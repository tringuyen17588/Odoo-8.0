# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013 Camptocamp
#    Copyright 2009-2013 Akretion,
#    Author: Emmanuel Samyn, Raphaï¿½l Valyi, Sï¿½bastien Beau,
#            Benoï¿½t Guillot, Joel Grand-Guillaume
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
from datetime import timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import netsvc
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta
import time


class crea8s_project(osv.osv):
    _name = 'crea8s.project'
    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'code': fields.char('Code', size=256, required=True),
}
    _defaults = {
        'name': '/',
    }

crea8s_project()

class sale_order(osv.osv):
    _inherit = 'sale.order'

    _columns = {
        'project': fields.many2one('crea8s.project', 'Project'),
    }
    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        temp_name = temp_name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/'
        if vals.get('project', False):
            re_pro1 = self.search(cr, uid, [('project', '=', vals['project'])], order='id')
            if not re_pro1:
                temp_name = self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/'
                vals['name'] = temp_name
                self.pool.get('crea8s.project').write(cr, uid, [vals['project']], {'name': temp_name})
            else:
                cur_so = re_pro1 and self.browse(cr, uid, re_pro1[0]) or ''
                re_pro = re_pro1 and cur_so.project.code or ''
                vals['name'] = '%s%s%s'%(cur_so.name,re_pro,str(len(re_pro1)))
        else:
            if vals.get('name', '/') == '/':
                vals['name'] = temp_name
        if vals.get('partner_id') and any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id', 'fiscal_position']):
            defaults = self.onchange_partner_id(cr, uid, [], vals['partner_id'], context=context)['value']
            if not vals.get('fiscal_position') and vals.get('partner_shipping_id'):
                delivery_onchange = self.onchange_delivery_id(cr, uid, [], vals.get('company_id'), None, vals['partner_id'], vals.get('partner_shipping_id'), context=context)
                defaults.update(delivery_onchange['value'])
            vals = dict(defaults, **vals)
        ctx = dict(context or {}, mail_create_nolog=True)
        new_id = super(sale_order, self).create(cr, uid, vals, context=ctx)
        self.message_post(cr, uid, [new_id], body=_("Quotation created"), context=ctx)
        return new_id

sale_order()

import openerp.addons.decimal_precision as dp
from openerp import tools
import psycopg2

class product_template(osv.osv):
    _inherit = 'product.template'
    
    _columns = {
        'qty_hand': fields.float('Quantity On Hand', digits_compute=dp.get_precision('Product Unit of Measure')),
    }

    def change_product_qty(self, cr, uid, ids, new_quantity, product_id, context=None):
        if context is None:
            context = {}
        location_id = self.pool.get('stock.warehouse').browse(cr, uid, 1).lot_stock_id.id
        lot_id = 0
        print new_quantity, '   new_quantity'
        inventory_obj = self.pool.get('stock.inventory')
        inventory_line_obj = self.pool.get('stock.inventory.line')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context={'location':location_id, 'lot_id': 0})
        if 2>1:
            if new_quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Quantity cannot be negative.'))
            ctx = context.copy()
            ctx['location'] = location_id
            ctx['lot_id'] = 0
            
            inventory_id = inventory_obj.create(cr, uid, {
                'name': _('INV: %s') % tools.ustr(product.name),
                'product_id': product_id,
                'location_id': location_id,
                'lot_id': lot_id}, context=context)
            th_qty = product.qty_available
            line_data = {
                'inventory_id': inventory_id,
                'product_qty': new_quantity,
                'location_id': location_id,
                'product_id': product_id,
                'product_uom_id': product.uom_id.id,
                'theoretical_qty': th_qty,
                'prod_lot_id': lot_id
            }
            inventory_line_obj.create(cr , uid, line_data, context=context)
            inventory_obj.action_done(cr, uid, [inventory_id], context=context)
        return {}

    def create(self, cr, uid, vals, context=None):
        ''' Store the initial standard price in order to be able to retrieve the cost of a product template for a given date'''
        product_template_id = super(product_template, self).create(cr, uid, vals, context=context)
        if not context or "create_product_product" not in context:
            self.create_variant_ids(cr, uid, [product_template_id], context=context)
        self._set_standard_price(cr, uid, product_template_id, vals.get('standard_price', 0.0), context=context)

        # TODO: this is needed to set given values to first variant after creation
        # these fields should be moved to product as lead to confusion
        related_vals = {}
        if vals.get('ean13'):
            related_vals['ean13'] = vals['ean13']
        if vals.get('default_code'):
            related_vals['default_code'] = vals['default_code']            
        if vals.has_key('qty_hand'):
            if vals.get('qty_hand', False):
                context.update({'qty_hand': vals.get('qty_hand', False)})
                for xx in self.browse(cr, uid, product_template_id).product_variant_ids:
                    self.pool.get('product.product').change_product_qty(cr, uid, [], vals.get('qty_hand', False), xx.id, context=None)
        if related_vals:
            self.write(cr, uid, product_template_id, related_vals, context=context)
        return product_template_id

product_template()


class product_product(osv.osv):
    _inherit = 'product.product'

    _columns = {
        'att_note': fields.char('Attribute', size=256),
        'model_no': fields.char('Model No.', size=256),
        'qty_hand': fields.float('Quantity On Hand', digits_compute=dp.get_precision('Product Unit of Measure')),
        'lst_price': fields.float('Public Price', digits_compute=dp.get_precision('Product Price')),
    }

    def change_product_qty(self, cr, uid, ids, new_quantity, product_id, context=None):
        if context is None:
            context = {}
        location_id = self.pool.get('stock.warehouse').browse(cr, uid, 1).lot_stock_id.id
        lot_id = 0
        inventory_obj = self.pool.get('stock.inventory')
        inventory_line_obj = self.pool.get('stock.inventory.line')
        product = self.pool.get('product.product').browse(cr, uid, product_id, context={'location':location_id, 'lot_id': 0})
        if 2>1:#for data in self.browse(cr, uid, ids, context=context):
            if new_quantity < 0:
                raise osv.except_osv(_('Warning!'), _('Quantity cannot be negative.'))
            ctx = context.copy()
            ctx['location'] = location_id
            ctx['lot_id'] = 0
            
            inventory_id = inventory_obj.create(cr, uid, {
                'name': _('INV: %s') % tools.ustr(product.name),
                'product_id': product_id,
                'location_id': location_id,
                'lot_id': lot_id}, context=context)
            th_qty = product.qty_available
            line_data = {
                'inventory_id': inventory_id,
                'product_qty': new_quantity,
                'location_id': location_id,
                'product_id': product_id,
                'product_uom_id': product.uom_id.id,
                'theoretical_qty': th_qty,
                'prod_lot_id': lot_id
            }
            inventory_line_obj.create(cr , uid, line_data, context=context)
            inventory_obj.action_done(cr, uid, [inventory_id], context=context)
        return {}

    def create(self, cr, uid, vals, context=None):
        temp_obj = self.pool.get('product.template')
        if not vals.has_key('product_tmpl_id'):
            temp_id = temp_obj.search(cr, uid, [('name', '=', vals['name'])])
            temp_id = temp_id and temp_id[0] or temp_obj.create(cr, uid, vals)
            vals.update({'product_tmpl_id': temp_id})
        if vals.has_key('model_no'):
            vals.update({'default_code': vals['model_no']})
        if context is None:
            context = {}
        ctx = dict(context or {}, create_product_product=True)
        kq = super(product_product, self).create(cr, uid, vals, context=ctx)
        if vals.has_key('qty_hand'):
            if vals.get('qty_hand', False):
                self.pool.get('product.product').change_product_qty(cr, uid, [], vals.get('qty_hand', False), kq, context=None)
        return kq

product_product()