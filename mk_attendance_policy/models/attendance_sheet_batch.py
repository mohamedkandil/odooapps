from odoo import fields, models
from odoo.exceptions import UserError, ValidationError


class MkAttendanceSheetBatch(models.TransientModel):
    _name = 'mk.attendance.sheet.batch'
    _description = 'Batch Attendance Sheets'

    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    department_id = fields.Many2one(
        'hr.department',
        domain="[('company_id', 'in', [False, company_id])]",
    )
    attendance_policy_id = fields.Many2one(
        'mk.attendance.policy',
        domain="[('company_id', '=', company_id), ('active', '=', True)]",
        help='Leave empty to use the employee policy, then the active company policy.',
    )
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    skip_existing = fields.Boolean(default=True)

    def _get_employees(self):
        self.ensure_one()
        domain = [
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ]
        if self.department_id:
            domain.append(('department_id', 'child_of', self.department_id.id))
        return self.env['hr.employee'].search(domain, order='name')

    def _get_employee_policy(self, employee):
        self.ensure_one()
        if self.attendance_policy_id:
            return self.attendance_policy_id
        if employee.attendance_policy_id:
            return employee.attendance_policy_id
        return self.env['mk.attendance.policy'].search([
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ], limit=1)

    def action_generate_sheets(self):
        self.ensure_one()
        if self.date_to < self.date_from:
            raise ValidationError("End date must be later than or equal to start date.")

        employees = self._get_employees()
        if not employees:
            raise UserError("No active employees found for the selected company or department.")

        sheet_model = self.env['mk.attendance.sheet']
        created_sheets = sheet_model
        skipped = 0

        for employee in employees:
            if self.skip_existing:
                existing = sheet_model.search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '=', self.date_from),
                    ('date_to', '=', self.date_to),
                ], limit=1)
                if existing:
                    skipped += 1
                    continue

            policy = self._get_employee_policy(employee)
            if not policy:
                skipped += 1
                continue

            sheet = sheet_model.create({
                'employee_id': employee.id,
                'attendance_policy_id': policy.id,
                'company_id': self.company_id.id,
                'date_from': self.date_from,
                'date_to': self.date_to,
            })
            sheet.action_generate()
            created_sheets |= sheet

        if not created_sheets:
            raise UserError("No sheets were created. They may already exist, or no attendance policy was found.")

        action = self.env.ref('mk_attendance_policy.action_mk_attendance_sheet').read()[0]
        action['domain'] = [('id', 'in', created_sheets.ids)]
        action['context'] = {
            'default_company_id': self.company_id.id,
            'search_default_group_by_employee': 1,
        }
        if skipped:
            action['display_name'] = "Attendance Sheets (%s created, %s skipped)" % (
                len(created_sheets),
                skipped,
            )
        return action
