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

from openerp.osv import fields, osv
from openerp import tools

class crea8s_event_number(osv.Model):
    _name = "crea8s.event.number"
    _columns = {
        'name': fields.char('Number', size=10),
    }
#    Modified by NHT

class crea8s_image_url(osv.osv_memory):
    _name = 'crea8s.image.url'
    _columns ={
        'name': fields.char('URL', size=256),
        'event_id': fields.many2one('event.event', 'Event'),
    }    
    def get_event(self, cr, uid, context={}):
        if context.get('active_id', False):
            return context['active_id']
        return 0
    
    _defaults ={
        'event_id': get_event,
    }
    
    def set_img_event(self, cr, uid, ids, context={}):
        event_obj = self.pool.get('event.event')
        for record in self.browse(cr, uid, ids):
            event_obj.write(cr, uid, [record.event_id.id], {'img_banner': ''' <img src="%s"> '''%record.name})
        return 1
    
crea8s_image_url()

class event_event(osv.Model):
    _inherit = "event.event"

    def _get_image(self, cr, uid, ids, name, args, context=None):
        result = dict.fromkeys(ids, False)
        for obj in self.browse(cr, uid, ids, context=context):
            result[obj.id] = tools.image_get_resized_images(obj.image, avoid_resize_medium=True)
        return result

    def _set_image(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'image': tools.image_resize_image_big(value)}, context=context)
    
    _columns ={
        'mail_lst': fields.many2one('mail.mass_mailing.list', 'Mail List'),
        'img_banner': fields.text('Banner'),
        'is_locker': fields.boolean('Locker'),
        'image': fields.binary("Image",
            help="This field holds the image used as image for the product, limited to 1024x1024px."),
        'image_medium': fields.function(_get_image, fnct_inv=_set_image,
            string="Medium-sized image", type="binary", multi="_get_image", 
            store={
                'event.event': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Medium-sized image of the product. It is automatically "\
                 "resized as a 128x128px image, with aspect ratio preserved, "\
                 "only when the image exceeds one of those sizes. Use this field in form views or some kanban views."),
        'image_small': fields.function(_get_image, fnct_inv=_set_image,
            string="Small-sized image", type="binary", multi="_get_image",
            store={
                'event.event': (lambda self, cr, uid, ids, c={}: ids, ['image'], 10),
            },
            help="Small-sized image of the product. It is automatically "\
                 "resized as a 64x64px image, with aspect ratio preserved. "\
                 "Use this field anywhere a small image is required."),
        'name_display': fields.boolean('Name Display'),
        'gender_display': fields.boolean('Gender Display'),
        'contact_no_display': fields.boolean('Contact No. Display'),
        'dietry_req_display': fields.boolean('Dietary Requirement Display'),
        'country_club_display': fields.boolean('Country Club Display'),
        'country_club_member_display': fields.boolean('Country Club Memeber No. Display'),
        'shoe_size_display': fields.boolean('Shoe Size Display'),
        'us_shirt_size_display': fields.boolean('US Shirt Size Display'),
        'asian_size_display': fields.boolean('Asian Size Display'),
        'flexible_1_display': fields.boolean('Flexible 1 Display'),
        'flexible_2_display': fields.boolean('Flexible 2 Display'),
        'flexible_3_display': fields.boolean('Flexible 3 Display'),
        'flexible_4_display': fields.boolean('Flexible 4 Display'),
        'flexible_5_display': fields.boolean('Flexible 5 Display'),
    }
    
    def create(self, cr, user, vals, context=None):
        mass_mail_lst_obj = self.pool.get('mail.mass_mailing.list')
        mail_lst = mass_mail_lst_obj.create(cr, user, {'name': vals.get('name')})
        vals.update({'mail_lst': mail_lst})
        result = super(event_event, self).create(cr, user, vals, context) 
        return result
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('name', False):
            [x.mail_contact and self.pool.get('mail.mass_mailing.list').write(cr, uid, x.mail_contact.id, {'name': vals.get('name', False)})\
            or 0 for x in self.browse(cr, uid, ids)]
        return  super(event_event, self).write(cr, uid, ids, vals, context=context)
event_event()

class mail_mass_mailing(osv.Model):
    _inherit = 'mail.mass_mailing'
    _columns = {
                'event_id': fields.many2one('event.event', 'Event'),
    }

class mail_mass_mailing_contact(osv.Model):
    _inherit = 'mail.mass_mailing.contact'
    _columns = {
        'phone': fields.char('Phone', size=32),
    }
mail_mass_mailing_contact()
#    End of Modified

class event_registration(osv.Model):
    _inherit = "event.registration"
    _columns = {
                
        'male':fields.boolean('Male'),
        'female':fields.boolean('Female'),
        'handicap': fields.char('Handicap', size=10),
        'refer_no': fields.char('Ref no.', size=9),
        'flight_no': fields.char('Flight no.', size=10),
        'member_no': fields.char('Membership no.', size=10),
        'tee_box': fields.char('Tee Box.'),
        'tee_time': fields.char('Tee Time', size=128),
        'locker_no': fields.char('Locker no.', size=10),
        'rm_name': fields.char('RM Name.', size=256),
        'dietary_requirement': fields.char('Dietary Requirement', size=10),
        'country_club': fields.char('Country Club', size=10),
        'country_club_mem': fields.char('Country Club membership', size=10),
        'shoe_size': fields.char('Shoe Size', size=10),
        'us_shirt_size': fields.char('US Shirt Size'),
        'asian_size': fields.char('Asian Size'),
        'flexible_1': fields.char('Flexible 1'),
        'flexible_2': fields.char('Flexible 2'),
        'flexible_3': fields.char('Flexible 3'),
        'flexible_4': fields.char('Flexible 4'),
        'flexible_5': fields.char('Flexible 5'),
        'polo_size': fields.many2one('crea8s.event.number', 'Polo Shirt Size'),
        'sho_size': fields.many2one('crea8s.event.number', 'Shoes Size'),
        'mail_contact': fields.many2one('mail.mass_mailing.contact', 'Email Contact'),
        'note': fields.text('Note'),
    }
    
    def create(self, cr, user, vals, context=None):
        mass_mail_lst_obj = self.pool.get('mail.mass_mailing.contact')
        mass_id = 0
        if vals.get('event_id', False):
            mass_id = self.pool.get('event.event').browse(cr, user, vals.get('event_id', False)).mail_lst
            mass_id = mass_id and mass_id.id or False
        mail_contact = mass_mail_lst_obj.create(cr, user, {'name': vals.get('name', ''),
                                                       'email': vals.get('email', ''),
                                                       'phone': vals.get('phone', ''),
#                                                       'list_id': mass_id,
                                                       })
        vals.update({'mail_contact': mail_contact})
        result = super(event_registration, self).create(cr, user, vals, context) 
        return result
    
    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('name', False):
            [x.mail_contact and self.pool.get('mail.mass_mailing.contact').write(cr, uid, x.mail_contact.id, {'name': vals.get('name', False)})\
            or 0 for x in self.browse(cr, uid, ids)]
        if vals.get('email', False):
            [x.mail_contact and self.pool.get('mail.mass_mailing.contact').write(cr, uid, x.mail_contact.id, {'email': vals.get('email', False)})\
            or 0 for x in self.browse(cr, uid, ids)]
        if vals.get('phone', False):
            [x.mail_contact and self.pool.get('mail.mass_mailing.contact').write(cr, uid, x.mail_contact.id, {'phone': vals.get('phone', False)})\
            or 0 for x in self.browse(cr, uid, ids)]
        return  super(event_registration, self).write(cr, uid, ids, vals, context=context)
    
event_registration()
    
from openerp.report import report_sxw
import time
class crea8s_event_register(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(crea8s_event_register, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,

        })
report_sxw.report_sxw('report.crea8s.event.registration', 
                      'event.registration', 
                      'addons/crea8s_event/label.rml', 
                      parser=crea8s_event_register, header=False)
class res_partner(osv.Model):
    _inherit = "res.partner"
    _columns = {
        'registration': fields.one2many('event.registration', 'partner_id', 'registration'),
    }