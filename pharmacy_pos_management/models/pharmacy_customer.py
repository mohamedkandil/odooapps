from odoo import models, fields, api

class PharmacyCustomer(models.Model):
    _name = 'pharmacy.customer'
    _description = 'Pharmacy Customer/Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    phone = fields.Char(tracking=True)
    email = fields.Char(tracking=True)
    insurance_info = fields.Char('Insurance Information')
    allergies = fields.Text()
    chronic_diseases = fields.Text()
    current_medications = fields.Text()
    loyalty_points = fields.Float(default=0.0)
    promotion_ids = fields.Many2many('pharmacy.promotion', string='Promotions')
    whatsapp_opt_in = fields.Boolean('WhatsApp Notifications', default=True)
    sms_opt_in = fields.Boolean('SMS Notifications', default=True)
    credit_limit = fields.Float(default=0.0)
    credit_balance = fields.Float(default=0.0)
    partner_id = fields.Many2one('res.partner', string='Related Partner')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    statement_line_ids = fields.One2many('pharmacy.customer.statement', 'customer_id', string='Statement')
    active = fields.Boolean(default=True)


class PharmacyCustomerStatement(models.Model):
    _name = 'pharmacy.customer.statement'
    _description = 'Pharmacy Customer Statement'
    _order = 'date desc, id desc'

    customer_id = fields.Many2one('pharmacy.customer', required=True, ondelete='cascade')
    date = fields.Date(default=fields.Date.today, required=True)
    description = fields.Char(required=True)
    debit = fields.Float()
    credit = fields.Float()
    balance = fields.Float()
