# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.report import report_sxw
import time
from datetime import datetime
from openerp.osv import fields, osv

class sale_delivery(osv.osv):
    _name = "sale.delivery"
    _columns = {
        'name': fields.char('Delivery', size=256),
    }
sale_delivery()

class sale_shiping_method(osv.osv):
    _name = "sale.shiping.method"
    _columns = {
        'name': fields.char('Shipping Method', size=256),
    }
sale_shiping_method()

class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _columns = {
        'ship_id': fields.many2one('sale.shiping.method', 'Shipping Method'),
    }
    
purchase_order()

class sale_order(osv.osv):
    _inherit = "sale.order"
    _columns = {
        'valid_date': fields.date('QUOTATION VALID TILL'),
        'ref_no': fields.char('Our Ref', size=256),
        'delivery_id': fields.many2one('sale.delivery', 'Delivery'),
    }
    
    def get_current_time(self, cr, uid, context={}):
        return datetime.now().strftime('%Y-%m-%d')

    _defaults = {
        'valid_date': get_current_time,
    }

    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        date_planned = self._get_date_planned(cr, uid, order, line, order.date_order, context=context)
        return {
            'name': line.name,
            'origin': order.name,
            'date_planned': date_planned,
            'sequence': line.sequence and line.sequence or 0,
            'product_id': line.product_id and line.product_id.id or 60,
            'product_qty': line.product_uom_qty,
            'product_uom': line.product_uom.id,
            'product_uos_qty': (line.product_uos and line.product_uos_qty) or line.product_uom_qty,
            'product_uos': (line.product_uos and line.product_uos.id) or line.product_uom.id,
            'company_id': order.company_id.id,
            'group_id': group_id,
            'invoice_state': (order.order_policy == 'picking') and '2binvoiced' or 'none',
            'sale_line_id': line.id
        }

    def action_ship_create(self, cr, uid, ids, context=None):
        """Create the required procurements to supply sales order lines, also connecting
        the procurements to appropriate stock moves in order to bring the goods to the
        sales order's requested location.

        :return: True
        """
        context = context or {}
        context['lang'] = self.pool['res.users'].browse(cr, uid, uid).lang
        procurement_obj = self.pool.get('procurement.order')
        sale_line_obj = self.pool.get('sale.order.line')
        for order in self.browse(cr, uid, ids, context=context):
            proc_ids = []
            vals = self._prepare_procurement_group(cr, uid, order, context=context)
            if not order.procurement_group_id:
                group_id = self.pool.get("procurement.group").create(cr, uid, vals, context=context)
                order.write({'procurement_group_id': group_id})

            for line in order.order_line:
                #Try to fix exception procurement (possible when after a shipping exception the user choose to recreate)
                if line.procurement_ids:
                    #first check them to see if they are in exception or not (one of the related moves is cancelled)
                    procurement_obj.check(cr, uid, [x.id for x in line.procurement_ids if x.state not in ['cancel', 'done']])
                    line.refresh()
                    #run again procurement that are in exception in order to trigger another move
                    proc_ids += [x.id for x in line.procurement_ids if x.state in ('exception', 'cancel')]
                    procurement_obj.reset_to_confirmed(cr, uid, proc_ids, context=context)
                elif sale_line_obj.need_procurement(cr, uid, [line.id], context=context):
#                    if (line.state == 'done') or not line.product_id:
#                        continue
                    vals = self._prepare_order_line_procurement(cr, uid, order, line, group_id=order.procurement_group_id.id, context=context)
                    ctx = context.copy()
                    ctx['procurement_autorun_defer'] = True
                    proc_id = procurement_obj.create(cr, uid, vals, context=ctx)
                    proc_ids.append(proc_id)
            #Confirm procurement order such that rules will be applied on it
            #note that the workflow normally ensure proc_ids isn't an empty list
            procurement_obj.run(cr, uid, proc_ids, context=context)

            #if shipping was in exception and the user choose to recreate the delivery order, write the new status of SO
            if order.state == 'shipping_except':
                val = {'state': 'progress', 'shipped': False}

                if (order.order_policy == 'manual'):
                    for line in order.order_line:
                        if (not line.invoiced) and (line.state not in ('cancel', 'draft')):
                            val['state'] = 'manual'
                            break
                order.write(val)
        return True

sale_order()

class stock_move(osv.osv):
    _inherit = "stock.move"
    _order = 'sequence, date_expected desc, id'
    _columns = {
        'sequence': fields.integer('Sequence'),
    }
stock_move()

def _get_line_no_(objLines, line):
    iNo = 0
    for item in objLines:
        if item.product_id:
            print item.product_id, '  dang kiem tra'
            if line.product_id.id != 60:
                iNo += 1
        if (item.id == line.id or line.product_id.id == 60):
            break
    return iNo

class crea8s_so_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(crea8s_so_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_line_no': _get_line_no_,
            'show_discount': self._show_discount,
            'get_do_name': self.get_do_name,
        })
    def get_do_name(self, obj):
        result = ''
        for x in obj.picking_ids:
            if len(obj.picking_ids) < 2:
                result = x.min_date 
            else:
                result += x.min_date + ' '
        return result

    def _show_discount(self, uid, context=None):
        cr = self.cr
        try: 
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'group_discount_per_so_line')[1]
        except:
            return False
        return group_id in [x.id for x in self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id]        
report_sxw.report_sxw('report.crea8s_so_report', 'sale.order', 'addons/crea8s_report_so/quotation_report.rml', parser=crea8s_so_report, header=False)

class crea8s_inv_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(crea8s_inv_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_line_no': _get_line_no_,
            'show_discount': self._show_discount,
            'get_do_so': self.get_do_so,
        })
    def _show_discount(self, uid, context=None):
        cr = self.cr
        try: 
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'group_discount_per_so_line')[1]
        except:
            return False
        return group_id in [x.id for x in self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id]

    def get_do_so(self, inv_id):
        sql = ''' select order_id from sale_order_invoice_rel where invoice_id = %s '''%inv_id
        cr = self.cr
        sale_name = ' '
        do_name = ' '
        uid = self.uid
        cr.execute(sql)
        sale_id = cr.fetchone()
        sale_id = sale_id and sale_id[0] or 0
        if sale_id:
            sale_br = self.pool.get('sale.order').browse(cr, uid, sale_id)
            sale_name = sale_br.name
            do_name = [x.name for x in sale_br.picking_ids]
            if do_name:
                do_name = len(do_name) < 2 and do_name[0] or do_name
        return [sale_name, do_name]

report_sxw.report_sxw('report.crea8s_inv_report', 'account.invoice', 'addons/crea8s_report_so/invoice_report.rml', parser=crea8s_inv_report, header=False)

class crea8s_po_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(crea8s_po_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_line_no': _get_line_no_,
            'show_discount': self._show_discount,
        })
    def _show_discount(self, uid, context=None):
        cr = self.cr
        try: 
            group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'group_discount_per_so_line')[1]
        except:
            return False
        return group_id in [x.id for x in self.pool.get('res.users').browse(cr, uid, uid, context=context).groups_id]        
report_sxw.report_sxw('report.crea8s_po_report', 'purchase.order', 'addons/crea8s_report_so/purchase_report.rml', parser=crea8s_po_report, header=False)

class crea8s_picking_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(crea8s_picking_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_line_no': _get_line_no_,
            'get_do_so': self.get_do_so,
        })

    def get_do_so(self, obj):
        cr = self.cr
        sale_name = ' '
        do_name = ' '
        uid = self.uid
        sale_id = self.pool.get('sale.order').search(cr, uid, [('procurement_group_id', '=', obj.group_id and obj.group_id.id or 0)])
        sale_id = sale_id and sale_id[0] or 0
        if sale_id:
            sale_br = self.pool.get('sale.order').browse(cr, uid, sale_id)
            pick_partner = sale_br.partner_shipping_id and sale_br.partner_shipping_id or sale_br.partner_id
            inv_partner  = sale_br.partner_invoice_id and sale_br.partner_invoice_id or sale_br.partner_id
            return [pick_partner, inv_partner]
        return [obj.partner_id,obj.partner_id]

report_sxw.report_sxw('report.crea8s_picking_report', 'stock.picking', 'addons/crea8s_report_so/picking_report.rml', parser=crea8s_picking_report, header=False)