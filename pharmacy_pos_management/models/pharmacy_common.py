from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_pharmacy_branch_ids = fields.Many2many(
        'pharmacy.branch',
        'pharmacy_branch_user_rel',
        'user_id',
        'branch_id',
        string='Allowed Pharmacy Branches',
    )
    default_pharmacy_branch_id = fields.Many2one(
        'pharmacy.branch',
        string='Default Pharmacy Branch',
        domain="[('id', 'in', allowed_pharmacy_branch_ids)]",
    )


class PharmacyProfile(models.Model):
    _name = 'pharmacy.profile'
    _description = 'Pharmacy Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
        tracking=True,
    )
    license_number = fields.Char(tracking=True)
    responsible_pharmacist_id = fields.Many2one('res.users', tracking=True)
    phone = fields.Char()
    email = fields.Char()
    website = fields.Char()
    address = fields.Text()
    branch_ids = fields.One2many('pharmacy.branch', 'profile_id', string='Branches')
    active = fields.Boolean(default=True)


class PharmacyCashbox(models.Model):
    _name = 'pharmacy.cashbox'
    _description = 'Pharmacy Branch Cashbox'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    branch_id = fields.Many2one('pharmacy.branch', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    journal_id = fields.Many2one(
        'account.journal',
        required=True,
        domain="[('type', 'in', ('cash', 'bank'))]",
        tracking=True,
    )
    cashier_ids = fields.Many2many('res.users', string='Allowed Cashiers')
    opening_balance = fields.Monetary(currency_field='currency_id', tracking=True)
    current_balance = fields.Monetary(currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True, readonly=True)
    active = fields.Boolean(default=True)


class PharmacyPromotion(models.Model):
    _name = 'pharmacy.promotion'
    _description = 'Pharmacy Promotion'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    branch_ids = fields.Many2many('pharmacy.branch', string='Branches')
    product_ids = fields.Many2many('pharmacy.product', string='Products')
    discount_percent = fields.Float(tracking=True)
    date_start = fields.Date(required=True, default=fields.Date.today)
    date_end = fields.Date(required=True)
    active = fields.Boolean(default=True)

    @api.constrains('discount_percent')
    def _check_discount_percent(self):
        for promotion in self:
            if promotion.discount_percent < 0 or promotion.discount_percent > 100:
                raise ValidationError(_('Discount must be between 0 and 100 percent.'))


class PharmacyNotificationLog(models.Model):
    _name = 'pharmacy.notification.log'
    _description = 'Pharmacy Notification Log'
    _order = 'create_date desc'

    name = fields.Char(required=True)
    notification_type = fields.Selection([
        ('expiry', 'Expiry Alert'),
        ('stock', 'Stock Alert'),
        ('whatsapp', 'WhatsApp'),
        ('sms', 'SMS'),
        ('system', 'System'),
    ], required=True, default='system')
    branch_id = fields.Many2one('pharmacy.branch')
    product_id = fields.Many2one('pharmacy.product')
    batch_id = fields.Many2one('pharmacy.batch')
    message = fields.Text(required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ], default='pending', required=True)


class PharmacyIntegrationEndpoint(models.Model):
    _name = 'pharmacy.integration.endpoint'
    _description = 'Pharmacy Integration Endpoint'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    integration_type = fields.Selection([
        ('whatsapp', 'WhatsApp API'),
        ('sms', 'SMS Gateway'),
        ('payment', 'Payment Gateway'),
        ('printer', 'Thermal Printer'),
        ('barcode', 'Barcode Device'),
        ('mobile', 'Mobile App'),
        ('third_party', 'Third Party'),
    ], required=True, tracking=True)
    base_url = fields.Char()
    api_key = fields.Char(groups='pharmacy_pos_management.group_pharmacy_admin')
    active = fields.Boolean(default=True)
    notes = fields.Text()
