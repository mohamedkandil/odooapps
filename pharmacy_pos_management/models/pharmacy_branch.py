from odoo import models, fields, api

class PharmacyBranch(models.Model):
    _name = 'pharmacy.branch'
    _description = 'Pharmacy Branch'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    profile_id = fields.Many2one('pharmacy.profile', string='Pharmacy Profile')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    manager_id = fields.Many2one('res.users', string='Branch Manager')
    user_ids = fields.Many2many('res.users', 'pharmacy_branch_user_rel', 'branch_id', 'user_id', string='Allowed Users')
    cashbox_ids = fields.One2many('pharmacy.cashbox', 'branch_id', string='Cashboxes')
    phone = fields.Char()
    address = fields.Text()
    active = fields.Boolean(default=True)
