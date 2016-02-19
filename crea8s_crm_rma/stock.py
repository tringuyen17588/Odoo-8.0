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
from openerp import tools
from openerp.addons.decimal_precision import decimal_precision as dp

class stock_picking(orm.Model):
    _inherit = "stock.picking"

    _columns = {
        'claim_id': fields.many2one('crm.claim', 'Claim'),
    }

#     def create(self, cr, uid, vals, context=None):
#         if ('name' not in vals) or (vals.get('name') == '/'):
#             sequence_obj = self.pool.get('ir.sequence')
#             if vals['type'] == 'internal':
#                 seq_obj_name = self._name
#             else:
#                 seq_obj_name = 'stock.picking.' + vals['type']
#             vals['name'] = sequence_obj.get(cr, uid, seq_obj_name,
#                                             context=context)
#         new_id = super(stock_picking, self).create(cr, uid, vals,
#                                                    context=context)
#         return new_id


class stock_picking_out(orm.Model):

    _inherit = "stock.picking.out"

    _columns = {
        'claim_id': fields.many2one('crm.claim', 'Claim'),
    }


class stock_picking_in(orm.Model):

    _inherit = "stock.picking.in"

    _columns = {
        'claim_id': fields.many2one('crm.claim', 'Claim'),
    }


# This part concern the case of a wrong picking out. We need to create a new
# stock_move in a picking already open.
# In order to don't have to confirm the stock_move we override the create and
# confirm it at the creation only for this case
class stock_move(orm.Model):

    _inherit = "stock.move"
    _columns = {
        'brand_id': fields.many2one('crea8s.product.brand', 'Brand'),
    }
    
    def create(self, cr, uid, vals, context=None):
        move_id = super(stock_move, self
                        ).create(cr, uid, vals, context=context)
        if vals.get('picking_id'):
            picking_obj = self.pool.get('stock.picking')
            picking = picking_obj.browse(cr, uid, vals['picking_id'],
                                         context=context)
            if picking.claim_id and picking.type == u'in':
                self.write(cr, uid, move_id, {'state': 'confirmed'},
                           context=context)
        return move_id

class stock_location(orm.Model):
    _inherit = "stock.location"
    _columns = {
        'is_defect': fields.boolean('Defective Location'),
}

#    Report For Defective Warehouse

class stock_inventory(orm.Model):
    _inherit = "stock.inventory"
    
    def action_view_refund(self, cr, uid, ids, context=None):
        mod_obj = self.pool.get('ir.model.data')
        inv_obj = self.pool.get('account.invoice')
        idd = inv_obj.search(cr, uid, [('type', '=', 'in_refund'),
                                       ('inventory_id', '=', ids[0])])
        idd = idd and idd[0] or 0
        view_ref = mod_obj.get_object_reference(cr, uid, 'crm_claim_rma', 'crea8s_account_invoice_supplier_form')
        view_id = view_ref and view_ref[1] or False,
        line = [x.id for x in self.browse(cr, uid, ids[0]).move_ids]
        return {
            'type': 'ir.actions.act_window',
            'name': 'Supplier Refunds',
            'res_model': 'account.invoice',
            'res_id': idd,
            'domain': '''[('type', '=', 'in_refund')]''',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'context': "{'claims_ids': %s, 'crea8s_inventory_line': %s, 'default_type': 'in_refund', 'type': 'in_refund', 'journal_type': 'purchase_refund'}"%(ids[0], line),
            'nodestroy': True,
        }
        
stock_inventory()

class report_stock_defective_inventory(orm.Model):
    _name = "report.stock.defective.inventory"
    _description = "Stock Defective Warehouse"
    _auto = False
    _columns = {
        'date': fields.datetime('Date', readonly=True),
        'year': fields.char('Year', size=4, readonly=True),
        'month':fields.selection([('01','January'), ('02','February'), ('03','March'), ('04','April'),
            ('05','May'), ('06','June'), ('07','July'), ('08','August'), ('09','September'),
            ('10','October'), ('11','November'), ('12','December')], 'Month', readonly=True),
        'partner_id':fields.many2one('res.partner', 'Partner', readonly=True),
        'product_id':fields.many2one('product.product', 'Product', readonly=True),
        'product_categ_id':fields.many2one('product.category', 'Product Category', readonly=True),
        'location_id': fields.many2one('stock.location', 'Location', readonly=True),
        'brand_id': fields.many2one('crea8s.product.brand', 'Brand', readonly=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'product_qty':fields.float('Quantity',  digits_compute=dp.get_precision('Product Unit of Measure'), readonly=True),
        'value' : fields.float('Total Value',  digits_compute=dp.get_precision('Account'), required=True),
        'state': fields.selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('confirmed', 'Confirmed'), ('assigned', 'Available'), ('done', 'Done'), ('cancel', 'Cancelled')], 'Status', readonly=True, select=True,
              help='When the stock move is created it is in the \'Draft\' state.\n After that it is set to \'Confirmed\' state.\n If stock is available state is set to \'Avaiable\'.\n When the picking it done the state is \'Done\'.\
              \nThe state is \'Waiting\' if the move is waiting for another one.'),
        'location_type': fields.selection([('supplier', 'Supplier Location'), ('view', 'View'), ('internal', 'Internal Location'), ('customer', 'Customer Location'), ('inventory', 'Inventory'), ('procurement', 'Procurement'), ('production', 'Production'), ('transit', 'Transit Location for Inter-Companies Transfers')], 'Location Type', required=True),
        'scrap_location': fields.boolean('scrap'),
    }
    def init(self, cr):
        tools.drop_view_if_exists(cr, 'report_stock_defective_inventory')
        cr.execute("""
CREATE OR REPLACE view report_stock_defective_inventory AS (
    (SELECT
        min(m.id) as id, m.date as date,
        to_char(m.date, 'YYYY') as year,
        to_char(m.date, 'MM') as month,
        m.partner_id as partner_id, m.location_id as location_id,
        m.product_id as product_id, pt.categ_id as product_categ_id, l.usage as location_type, l.scrap_location as scrap_location,
        m.company_id,
        m.brand_id,
        m.state as state, m.prodlot_id as prodlot_id,

        coalesce(sum(-pt.standard_price * m.product_qty * pu.factor / pu2.factor)::decimal, 0.0) as value,
        coalesce(sum(-m.product_qty * pu.factor / pu2.factor)::decimal, 0.0) as product_qty
    FROM
        stock_move m
            LEFT JOIN stock_picking p ON (m.picking_id=p.id)
            LEFT JOIN product_product pp ON (m.product_id=pp.id)
                LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                LEFT JOIN product_uom pu ON (pt.uom_id=pu.id)
                LEFT JOIN product_uom pu2 ON (m.product_uom=pu2.id)
            LEFT JOIN product_uom u ON (m.product_uom=u.id)
            LEFT JOIN stock_location l ON (m.location_id=l.id)
            WHERE m.state != 'cancel'
    GROUP BY
        m.id, m.product_id, m.product_uom, pt.categ_id, m.partner_id, m.location_id,  m.location_dest_id, m.brand_id, 
        m.prodlot_id, m.date, m.state, l.usage, l.scrap_location, m.company_id, pt.uom_id, to_char(m.date, 'YYYY'), to_char(m.date, 'MM')
) UNION ALL (
    SELECT
        -m.id as id, m.date as date,
        to_char(m.date, 'YYYY') as year,
        to_char(m.date, 'MM') as month,
        m.partner_id as partner_id, m.location_dest_id as location_id,
        m.product_id as product_id, pt.categ_id as product_categ_id, l.usage as location_type, l.scrap_location as scrap_location,
        m.company_id,
        m.brand_id,
        m.state as state, m.prodlot_id as prodlot_id,
        coalesce(sum(pt.standard_price * m.product_qty * pu.factor / pu2.factor)::decimal, 0.0) as value,
        coalesce(sum(m.product_qty * pu.factor / pu2.factor)::decimal, 0.0) as product_qty
    FROM
        stock_move m
            LEFT JOIN stock_picking p ON (m.picking_id=p.id)
            LEFT JOIN product_product pp ON (m.product_id=pp.id)
                LEFT JOIN product_template pt ON (pp.product_tmpl_id=pt.id)
                LEFT JOIN product_uom pu ON (pt.uom_id=pu.id)
                LEFT JOIN product_uom pu2 ON (m.product_uom=pu2.id)
            LEFT JOIN product_uom u ON (m.product_uom=u.id)
            LEFT JOIN stock_location l ON (m.location_dest_id=l.id)
            WHERE m.state != 'cancel'
    GROUP BY
        m.id, m.product_id, m.product_uom, pt.categ_id, m.partner_id, m.location_id, m.location_dest_id, m.brand_id,
        m.prodlot_id, m.date, m.state, l.usage, l.scrap_location, m.company_id, pt.uom_id, to_char(m.date, 'YYYY'), to_char(m.date, 'MM')
    )
);
        """)
report_stock_defective_inventory()
    