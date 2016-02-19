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

import datetime
import time
import math
from datetime import timedelta
from dateutil import relativedelta
from openerp import netsvc
import openerp.addons.decimal_precision as dp
from openerp import addons
import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools

class hr_payslip_line(osv.osv):
    _inherit = 'hr.payslip.line'
    
hr_payslip_line()

class hr_payslip_input(osv.osv):
    _inherit = 'hr.payslip.input'
hr_payslip_input()

class hr_payslip(osv.osv):
    _inherit = 'hr.payslip'

    def tf_psll_iputl(self, cr, uid, ids, context=None):
        input_obj = self.pool.get('hr.payslip.input')
        for record in self.browse(cr, uid, ids):
            for psll in record.line_ids:
                if psll.salary_rule_id.input_ids:
                    input_ids = input_obj.search(cr, uid, [('code', '=', psll.code), ('payslip_id', '=', record.id)])
                    input_val = {'name': psll.name,
                                 'code': psll.code,
                                 'payslip_id': record.id,
                                 'amount': psll.amount and psll.amount or 0,
                                 'pay_type': psll.pay_type and psll.pay_type or '',  
                                 'h_p_number': psll.h_p_number and psll.h_p_number or 0,
                                 'remark_pll': psll.remark_pll,
                                 'contract_id': record.contract_id.id,
                    }
                    #raise osv.except_osv('list id', record.line_ids)
                    if input_ids:
                        input_obj.write(cr, uid, input_ids, input_val)
                    else:
                        input_obj.create(cr, uid, input_val)
        return 1
            
hr_payslip()