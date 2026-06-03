from odoo import fields, models


class PharmacyExpiryAlertWizard(models.TransientModel):
    _name = 'pharmacy.expiry.alert.wizard'
    _description = 'Create Pharmacy Expiry Alerts'

    branch_id = fields.Many2one('pharmacy.branch')
    include_expired = fields.Boolean(default=True)
    days = fields.Selection([
        ('30', '30 Days'),
        ('60', '60 Days'),
        ('90', '90 Days'),
    ], default='90', required=True)

    def action_create_alerts(self):
        domain = [('expiry_date', '!=', False), ('days_to_expiry', '<=', int(self.days))]
        if not self.include_expired:
            domain.append(('days_to_expiry', '>=', 0))
        if self.branch_id:
            domain.append(('branch_id', '=', self.branch_id.id))
        self.env['pharmacy.batch'].search(domain).action_create_expiry_notifications()
        return {'type': 'ir.actions.act_window_close'}
