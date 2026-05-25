from odoo import fields, models

class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    attendance_sheet_id = fields.Many2one(
        'mk.attendance.sheet',
        readonly=True
    )