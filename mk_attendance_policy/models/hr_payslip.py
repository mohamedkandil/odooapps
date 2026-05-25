from odoo import fields, models

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    attendance_sheet_id = fields.Many2one('mk.attendance.sheet', readonly=True)

    def _get_attendance_sheet(self):
        self.ensure_one()
        if self.attendance_sheet_id:
            return self.attendance_sheet_id
        return self.env['mk.attendance.sheet'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', 'in', ['approved', 'paid']),
        ], order='date_from desc', limit=1)

    def _load_attendance_inputs(self):
        for slip in self:
            sheet = slip._get_attendance_sheet()
            if not sheet:
                continue
            contract = slip.contract_id or sheet._get_contract()
            old_inputs = slip.input_line_ids.filtered(lambda line: line.attendance_sheet_id == sheet)
            old_inputs.unlink()
            commands = sheet._get_payslip_input_commands(contract)
            if commands:
                slip.write({
                    'attendance_sheet_id': sheet.id,
                    'input_line_ids': commands,
                })

    def compute_sheet(self):
        self._load_attendance_inputs()
        return super().compute_sheet()
