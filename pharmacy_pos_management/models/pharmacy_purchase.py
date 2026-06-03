from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PharmacyPurchase(models.Model):
    _name = 'pharmacy.purchase'
    _description = 'Pharmacy Purchase'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    branch_id = fields.Many2one('pharmacy.branch', required=True, tracking=True)
    vendor_id = fields.Many2one('res.partner', domain="[('supplier_rank', '>', 0)]", required=True, tracking=True)
    order_line_ids = fields.One2many('pharmacy.purchase.line', 'purchase_id', string='Order Lines')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('rfq', 'RFQ'),
        ('approved', 'Approved'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], default='draft', tracking=True)
    approval_user_id = fields.Many2one('res.users', string='Approved By')
    invoice_id = fields.Many2one('account.move', string='Purchase Invoice')
    date_order = fields.Datetime(default=fields.Datetime.now, tracking=True)
    notes = fields.Text()
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    vendor_comparison = fields.Text()

    def action_submit_rfq(self):
        self.write({'state': 'rfq'})

    def action_approve(self):
        self.write({'state': 'approved', 'approval_user_id': self.env.user.id})

    def action_done(self):
        inventory = self.env['pharmacy.inventory']
        for purchase in self:
            for line in purchase.order_line_ids:
                inventory_line = inventory.search([
                    ('branch_id', '=', purchase.branch_id.id),
                    ('product_id', '=', line.product_id.id),
                ], limit=1)
                if inventory_line:
                    inventory_line.quantity += line.quantity
                else:
                    inventory.create({
                        'branch_id': purchase.branch_id.id,
                        'product_id': line.product_id.id,
                        'quantity': line.quantity,
                        'uom_id': line.product_id.uom_id.id,
                    })
            purchase.state = 'done'

    def action_cancel(self):
        self.write({'state': 'cancel'})

class PharmacyPurchaseLine(models.Model):
    _name = 'pharmacy.purchase.line'
    _description = 'Pharmacy Purchase Line'

    purchase_id = fields.Many2one('pharmacy.purchase', required=True, ondelete='cascade')
    product_id = fields.Many2one('pharmacy.product', required=True)
    quantity = fields.Float(required=True)
    price_unit = fields.Float(required=True)
    discount = fields.Float(default=0.0)
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    subtotal = fields.Float(compute='_compute_subtotal', store=True)
    tax_amount = fields.Float(compute='_compute_subtotal', store=True)
    total = fields.Float(compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'price_unit', 'discount')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (line.quantity * line.price_unit) * (1 - (line.discount or 0.0) / 100)
            taxes = line.tax_ids.compute_all(line.price_unit, quantity=line.quantity, product=False, partner=line.purchase_id.vendor_id) if line.tax_ids else {'total_included': line.subtotal}
            line.tax_amount = taxes.get('total_included', line.subtotal) - line.subtotal
            line.total = line.subtotal + line.tax_amount
