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
{
    'name': 'RMA Claim Created by CREA8S',
    'version': '1.1',
    'category': 'Generic Modules/CRM & SRM',
    'description': """ 	RMA Claim created by CREA8S """,
    'author': 'CREA8S',
    'website': 'http://www.crea8s.com/',
    'depends': ['crm_claim', 'stock'],
    'data': ['crm_claim_rma_view.xml'],
    'test': [],
    'images': ['images/product_return.png',
               'images/claim.png',
               'images/return_line.png',
               'images/exchange.png',
               ],
    'installable': True,
    'auto_install': False,
}