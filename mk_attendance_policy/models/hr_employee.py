from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    attendance_policy_id = fields.Many2one(
        'mk.attendance.policy',
        string='Attendance Policy',
        default=lambda self: self.env['mk.attendance.policy'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1),
    )
