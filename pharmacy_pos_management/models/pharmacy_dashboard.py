from odoo import models, fields, api

class PharmacyDashboard(models.Model):
    _name = 'pharmacy.dashboard'
    _description = 'Pharmacy Dashboard'

    name = fields.Char(required=True)
    dashboard_type = fields.Selection([
        ('sales', 'Sales'),
        ('inventory', 'Inventory'),
        ('purchase', 'Purchase'),
        ('finance', 'Finance'),
        ('performance', 'Performance')
    ], required=True)
    data = fields.Json()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    branch_id = fields.Many2one('pharmacy.branch')
