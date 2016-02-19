# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright 2013 Camptocamp
#    Copyright 2009-2013 Akretion,
#    Author: Emmanuel Samyn, Rapha�l Valyi, S�bastien Beau,
#            Beno�t Guillot, Joel Grand-Guillaume
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


class account_invoice_register(osv.osv_memory):
    _name = 'account.invoice.register'
    _columns = {
        'date_order': fields.date('Date'),
    }
    def invoice_confirm(self, cr, uid, ids, context={}):
        invoice_obj = self.pool.get('account.invoice')
        voucher_obj = self.pool.get('account.voucher')
        journal_obj = self.pool.get('account.journal')
        journal_id = journal_obj.search(cr, uid, [('type', '=', 'bank')])

        journal_id = journal_id and journal_id[0] or 0
        for record in self.browse(cr, uid, ids):
            for invoice in context.get('active_ids', False):
                print 'journal_id  day  ===   ', journal_id
                inv = invoice_obj.browse(cr, uid, invoice)
                ctx = {
                    'payment_expected_currency': inv.currency_id.id,
                    'default_partner_id': self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id,
                    'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                    'default_reference': inv.name,
                    'close_after_process': True,
                    'invoice_type': inv.type,
                    'invoice_id': inv.id,
                    'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                    'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'}
                journal_pool = self.pool.get('account.journal')
                journal = journal_pool.browse(cr, uid, journal_id, context=ctx)
                account_id = journal.default_credit_account_id or journal.default_debit_account_id
                tax_id = False
                if account_id and account_id.tax_ids:
                    tax_id = account_id.tax_ids[0].id
                partner_id = self.pool.get('res.partner')._find_accounting_partner(inv.partner_id).id
                line_cr_ids = voucher_obj.recompute_voucher_lines(cr, uid, ids, partner_id, \
                            journal_id, inv.residual, inv.currency_id.id, 'sale', record.date_order, ctx)['value']['line_cr_ids'] 
                temp_vals = voucher_obj.onchange_partner_id(cr, uid, [invoice], partner_id, \
                            journal_id, inv.residual, inv.currency_id.id, 'sale', record.date_order, context=ctx)['value']
                temp_vals.update({'partner_id': partner_id,
                                  'date': record.date_order,
                                  'journal_id': journal_id, 
                                  'company_id': inv.company_id.id,
                                  'tax_id': tax_id,
                                  'type': 'receipt',
                                  'currency_id': inv.currency_id.id})
                a = voucher_obj.create(cr, uid, temp_vals, ctx)
                for x in line_cr_ids:
                    x.update({'voucher_id': a})
                    self.pool.get('account.voucher.line').create(cr, uid, x)
                voucher_obj.button_proforma_voucher(cr, uid, [a], ctx)
        return 1
account_invoice_register()

class crea8s_shipping_method(osv.osv):
    _name = 'crea8s.shipping.method'
    _columns = {
        'name': fields.char('Name', size=256)
}
crea8s_shipping_method()

class crea8s_delivery_company(osv.osv):
    _name = 'crea8s.delivery.company'
    _columns = {
        'name': fields.char('Name', size=256)
}
crea8s_delivery_company()

class sale_order(osv.osv):
    _inherit = 'sale.order'

    _columns = {
        'tracking_no': fields.char('Tracking No.', size=128),
        'ship_method': fields.many2one('crea8s.shipping.method', 'Shipping Method'),
        'deli_com': fields.many2one('crea8s.delivery.company', 'Delivery Company'),
}
    
    def get_date_current(self, cr, uid, date_cur, context={}):
        if date_cur:
            date = datetime(int(date_cur[:4]), int(date_cur[5:7]), int(date_cur[8:10]), int(date_cur[11:13]), int(date_cur[14:16]))
        return date - timedelta(hours = 7)
    
    def import_data(self, cr, uid, fields, data, mode='init', current_module='', noupdate=False, context=None, filename=None):
        print 'ham import  ==   ', fields, '\n', data
        return super(sale_order, self).import_data(cr, uid, fields, data, mode, current_module, noupdate, context, filename)
    
    def create(self, cr, uid, vals, context=None):
        print vals
        sale_line_obj = self.pool.get('sale.order.line')
        partner_obj = self.pool.get('res.partner')
        temp = self.search(cr, uid, [('name', '=', vals.get('name', False))])
        # partner
        temp1 = partner_obj.search(cr, uid, ['name', '=', vals['partner_id']])
        if not temp1:
             vals['partner_id'] = 7
             #partner_obj.create(cr, uid, vals[''])
        if temp:
            if vals.has_key('order_line'):
                if vals.get('order_line', False):
                    valls = vals['order_line'][0][2]
                    valls.update({'order_id': temp[0]})
                    if not sale_line_obj.search(cr, uid, [('order_no', '=', valls['order_no'])]):
                        sale_line_obj.create(cr, uid, valls)
            return temp[0]
        if vals.has_key('date_order'):
            vals['date_order'] = self.get_date_current(cr, uid, vals['date_order'])
        result = super(sale_order, self).create(cr, uid, vals, context=context)
        return result

sale_order()