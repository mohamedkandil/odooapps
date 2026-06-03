from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PharmacyInventory(models.Model):
    _name = 'pharmacy.inventory'
    _description = 'Pharmacy Inventory'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    product_id = fields.Many2one('pharmacy.product', required=True, tracking=True)
    branch_id = fields.Many2one('pharmacy.branch', required=True, tracking=True)
    batch_id = fields.Many2one('pharmacy.batch', tracking=True)
    quantity = fields.Float(tracking=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    lot_number = fields.Char(related='batch_id.lot_number', store=True)
    expiry_date = fields.Date(related='batch_id.expiry_date', store=True)
    min_stock = fields.Float('Minimum Stock', default=0.0)
    reorder_qty = fields.Float('Reorder Quantity', default=0.0)
    last_inventory_date = fields.Date()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    stock_state = fields.Selection([
        ('ok', 'Available'),
        ('low', 'Low Stock'),
        ('out', 'Out of Stock'),
    ], compute='_compute_stock_state', store=True)

    @api.depends('quantity', 'min_stock')
    def _compute_stock_state(self):
        for rec in self:
            if rec.quantity <= 0:
                rec.stock_state = 'out'
            elif rec.quantity <= rec.min_stock:
                rec.stock_state = 'low'
            else:
                rec.stock_state = 'ok'

    @api.model
    def cron_min_stock_alerts(self):
        logs = self.env['pharmacy.notification.log']
        for rec in self.search([('stock_state', 'in', ['low', 'out'])]):
            logs.create({
                'name': 'Stock alert - %s' % rec.product_id.display_name,
                'notification_type': 'stock',
                'branch_id': rec.branch_id.id,
                'product_id': rec.product_id.id,
                'batch_id': rec.batch_id.id,
                'message': '%s stock is %s in %s.' % (
                    rec.product_id.display_name,
                    rec.stock_state,
                    rec.branch_id.display_name,
                ),
            })


class PharmacyInventoryAdjustment(models.Model):
    _name = 'pharmacy.inventory.adjustment'
    _description = 'Pharmacy Inventory Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, default='New', tracking=True)
    branch_id = fields.Many2one('pharmacy.branch', required=True, tracking=True)
    product_id = fields.Many2one('pharmacy.product', required=True, tracking=True)
    batch_id = fields.Many2one('pharmacy.batch', tracking=True)
    quantity = fields.Float(required=True, tracking=True)
    reason = fields.Text()
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    def action_done(self):
        inventory = self.env['pharmacy.inventory']
        for adjustment in self:
            line = inventory.search([
                ('branch_id', '=', adjustment.branch_id.id),
                ('product_id', '=', adjustment.product_id.id),
                ('batch_id', '=', adjustment.batch_id.id),
            ], limit=1)
            if line:
                line.quantity += adjustment.quantity
            else:
                inventory.create({
                    'branch_id': adjustment.branch_id.id,
                    'product_id': adjustment.product_id.id,
                    'batch_id': adjustment.batch_id.id,
                    'quantity': adjustment.quantity,
                })
            adjustment.state = 'done'


class PharmacyStockTransfer(models.Model):
    _name = 'pharmacy.stock.transfer'
    _description = 'Pharmacy Branch Stock Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, default='New', tracking=True)
    source_branch_id = fields.Many2one('pharmacy.branch', required=True, tracking=True)
    dest_branch_id = fields.Many2one('pharmacy.branch', required=True, tracking=True)
    product_id = fields.Many2one('pharmacy.product', required=True, tracking=True)
    batch_id = fields.Many2one('pharmacy.batch', tracking=True)
    quantity = fields.Float(required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], default='draft', tracking=True)

    def action_done(self):
        inventory = self.env['pharmacy.inventory']
        for transfer in self:
            source = inventory.search([
                ('branch_id', '=', transfer.source_branch_id.id),
                ('product_id', '=', transfer.product_id.id),
                ('batch_id', '=', transfer.batch_id.id),
            ], limit=1)
            if not source or source.quantity < transfer.quantity:
                raise UserError(_('Not enough stock for this transfer.'))
            dest = inventory.search([
                ('branch_id', '=', transfer.dest_branch_id.id),
                ('product_id', '=', transfer.product_id.id),
                ('batch_id', '=', transfer.batch_id.id),
            ], limit=1)
            source.quantity -= transfer.quantity
            if dest:
                dest.quantity += transfer.quantity
            else:
                inventory.create({
                    'branch_id': transfer.dest_branch_id.id,
                    'product_id': transfer.product_id.id,
                    'batch_id': transfer.batch_id.id,
                    'quantity': transfer.quantity,
                })
            transfer.state = 'done'
