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

import time
import datetime
from openerp.report import report_sxw
         
class crm_claim_rma_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context=None):
        super(crm_claim_rma_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
        })        
        
report_sxw.report_sxw('report.crm_claim_rma_report_reportname', 'crm.claim', 'addons/crm_claim_rma/report/crm_claim_rma_report.rml', parser=crm_claim_rma_report)