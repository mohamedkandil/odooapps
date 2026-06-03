from odoo import models, fields, api
from datetime import date, timedelta

class PharmacyBatch(models.Model):
    _name = 'pharmacy.batch'
    _description = 'Pharmacy Batch/Lot'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    product_id = fields.Many2one('pharmacy.product', required=True, ondelete='cascade', tracking=True)
    lot_number = fields.Char(required=True, tracking=True)
    expiry_date = fields.Date(required=True, tracking=True)
    manufacturing_date = fields.Date(tracking=True)
    quantity = fields.Float(tracking=True)
    branch_id = fields.Many2one('pharmacy.branch', string='Branch', tracking=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    is_expired = fields.Boolean(compute='_compute_is_expired', store=True)
    is_near_expiry = fields.Boolean(compute='_compute_is_near_expiry', store=True)
    days_to_expiry = fields.Integer(compute='_compute_days_to_expiry', store=True)

    @api.depends('expiry_date')
    def _compute_is_expired(self):
        today = date.today()
        for rec in self:
            rec.is_expired = rec.expiry_date and rec.expiry_date < today

    @api.depends('expiry_date')
    def _compute_is_near_expiry(self):
        today = date.today()
        for rec in self:
            if rec.expiry_date:
                days_left = (rec.expiry_date - today).days
                rec.is_near_expiry = 0 <= days_left <= 90
            else:
                rec.is_near_expiry = False

    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        today = date.today()
        for rec in self:
            rec.days_to_expiry = (rec.expiry_date - today).days if rec.expiry_date else 0

    def action_create_expiry_notifications(self):
        logs = self.env['pharmacy.notification.log']
        for batch in self.filtered(lambda b: b.is_near_expiry or b.is_expired):
            state_label = 'expired' if batch.is_expired else 'near expiry'
            logs.create({
                'name': '%s - %s' % (batch.name, state_label),
                'notification_type': 'expiry',
                'branch_id': batch.branch_id.id,
                'product_id': batch.product_id.id,
                'batch_id': batch.id,
                'message': '%s batch %s is %s (%s days).' % (
                    batch.product_id.display_name,
                    batch.lot_number,
                    state_label,
                    batch.days_to_expiry,
                ),
            })

    @api.model
    def cron_expiry_alerts(self):
        batches = self.search([('expiry_date', '!=', False)])
        batches._compute_is_expired()
        batches._compute_is_near_expiry()
        batches.filtered(lambda batch: batch.is_expired or batch.is_near_expiry).action_create_expiry_notifications()
