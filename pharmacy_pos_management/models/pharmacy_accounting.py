from odoo import models, fields, api

class PharmacyAccounting(models.Model):
    _name = 'pharmacy.accounting'
    _description = 'Pharmacy Accounting Integration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    branch_id = fields.Many2one('pharmacy.branch', required=True, tracking=True)
    journal_id = fields.Many2one('account.journal', required=True, tracking=True)
    move_id = fields.Many2one('account.move', string='Journal Entry')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    cost_center_id = fields.Many2one('account.analytic.account', string='Cost Center')
    amount = fields.Float(tracking=True)
    date = fields.Date(default=fields.Date.today, tracking=True)
    company_id = fields.Many2one(related='branch_id.company_id', store=True, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], default='draft', tracking=True)

    def action_post(self):
        self.write({'state': 'posted'})

    def action_cancel(self):
        self.write({'state': 'cancel'})
