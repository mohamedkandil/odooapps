from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PharmacyPOS(models.Model):
    _name = 'pharmacy.pos'
    _description = 'Pharmacy POS Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    branch_id = fields.Many2one('pharmacy.branch', required=True, tracking=True)
    cashier_id = fields.Many2one('res.users', string='Cashier', required=True, tracking=True)
    session_date = fields.Datetime(default=fields.Datetime.now, tracking=True)
    order_ids = fields.One2many('pharmacy.pos.order', 'pos_id', string='Orders')
    cashbox_id = fields.Many2one('pharmacy.cashbox', string='Cashbox')
    state = fields.Selection([
        ('opened', 'Opened'),
        ('closed', 'Closed')
    ], default='opened', tracking=True)

class PharmacyPOSOrder(models.Model):
    _name = 'pharmacy.pos.order'
    _description = 'Pharmacy POS Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    pos_id = fields.Many2one('pharmacy.pos', required=True, ondelete='cascade')
    customer_id = fields.Many2one('pharmacy.customer', string='Customer')
    prescription_id = fields.Many2one('pharmacy.prescription', string='Prescription')
    order_line_ids = fields.One2many('pharmacy.pos.order.line', 'order_id', string='Order Lines')
    payment_ids = fields.One2many('pharmacy.pos.payment', 'order_id', string='Payments')
    total = fields.Float(compute='_compute_total', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('paid', 'Paid'),
        ('refund', 'Refund'),
        ('cancel', 'Cancelled')
    ], default='draft', tracking=True)
    date_order = fields.Datetime(default=fields.Datetime.now, tracking=True)
    name = fields.Char(required=True, default='New', tracking=True)
    branch_id = fields.Many2one(related='pos_id.branch_id', store=True, readonly=True)
    amount_paid = fields.Float(compute='_compute_payment_state', store=True)
    amount_due = fields.Float(compute='_compute_payment_state', store=True)
    is_held = fields.Boolean(default=False, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('pharmacy.pos.order') or 'New'
        return super().create(vals_list)

    @api.depends('order_line_ids.subtotal')
    def _compute_total(self):
        for order in self:
            order.total = sum(line.subtotal for line in order.order_line_ids)

    @api.depends('payment_ids.amount', 'total')
    def _compute_payment_state(self):
        for order in self:
            order.amount_paid = sum(order.payment_ids.mapped('amount'))
            order.amount_due = order.total - order.amount_paid

    def action_hold(self):
        self.write({'is_held': True})

    def action_pay(self):
        for order in self:
            if any(line.batch_id.is_expired for line in order.order_line_ids):
                raise UserError(_('Expired medicine cannot be sold.'))
            if order.amount_due > 0:
                raise UserError(_('Order still has an unpaid amount.'))
            order.write({'state': 'paid', 'is_held': False})

    def action_refund(self):
        self.write({'state': 'refund'})

class PharmacyPOSOrderLine(models.Model):
    _name = 'pharmacy.pos.order.line'
    _description = 'Pharmacy POS Order Line'

    order_id = fields.Many2one('pharmacy.pos.order', required=True, ondelete='cascade')
    product_id = fields.Many2one('pharmacy.product', required=True)
    batch_id = fields.Many2one('pharmacy.batch')
    quantity = fields.Float(required=True)
    price_unit = fields.Float(required=True)
    discount = fields.Float(default=0.0)
    subtotal = fields.Float(compute='_compute_subtotal', store=True)
    expiry_date = fields.Date(related='batch_id.expiry_date', store=True, readonly=True)
    available_qty = fields.Float(compute='_compute_available_qty')

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (line.quantity * line.price_unit) * (1 - (line.discount or 0.0) / 100)

    @api.depends('product_id', 'order_id.branch_id')
    def _compute_available_qty(self):
        inventory = self.env['pharmacy.inventory']
        for line in self:
            domain = [('product_id', '=', line.product_id.id)]
            if line.order_id.branch_id:
                domain.append(('branch_id', '=', line.order_id.branch_id.id))
            line.available_qty = sum(inventory.search(domain).mapped('quantity')) if line.product_id else 0.0

    @api.constrains('batch_id')
    def _check_not_expired(self):
        for line in self:
            if line.batch_id and line.batch_id.is_expired:
                raise ValidationError(_('Expired medicine cannot be added to POS orders.'))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.list_price
            batch = self.env['pharmacy.batch'].search([
                ('product_id', '=', self.product_id.id),
                ('is_expired', '=', False),
                ('quantity', '>', 0),
            ], order='expiry_date asc, id asc', limit=1)
            self.batch_id = batch.id

class PharmacyPOSPayment(models.Model):
    _name = 'pharmacy.pos.payment'
    _description = 'Pharmacy POS Payment'

    order_id = fields.Many2one('pharmacy.pos.order', required=True, ondelete='cascade')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('wallet', 'Wallet')
    ], required=True)
    amount = fields.Float(required=True)
    payment_date = fields.Datetime(default=fields.Datetime.now)
