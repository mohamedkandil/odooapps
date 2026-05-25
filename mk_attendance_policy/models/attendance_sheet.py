from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from datetime import timedelta, datetime, time
import pytz

class MkAttendanceSheet(models.Model):
    _name = 'mk.attendance.sheet'
    _description = 'Attendance Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(readonly=True, default='/')
    employee_id = fields.Many2one('hr.employee', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    attendance_policy_id = fields.Many2one(
        'mk.attendance.policy',
        default=lambda self: self.env['mk.attendance.policy'].search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1),
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and not self.attendance_policy_id:
            self.attendance_policy_id = self.employee_id.attendance_policy_id or self.env['mk.attendance.policy'].search([
                ('company_id', '=', self.env.company.id),
                ('active', '=', True)
            ], limit=1)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
    ], default='draft')

    line_ids = fields.One2many('mk.attendance.sheet.line', 'sheet_id')

    total_worked_hours = fields.Float(compute='_compute_totals', store=True)
    total_late_minutes = fields.Float(compute='_compute_totals', store=True)
    total_late_hours = fields.Float(compute='_compute_totals', store=True)
    total_overtime_hours = fields.Float(compute='_compute_totals', store=True)
    total_absence_days = fields.Float(compute='_compute_totals', store=True)
    total_overtime_amount = fields.Float(compute='_compute_totals', store=True)
    total_deduction = fields.Float(compute='_compute_totals', store=True)
    payslip_id = fields.Many2one('hr.payslip', readonly=True, copy=False)
    payslip_count = fields.Integer(compute='_compute_payslip_count')

    # ---------------- COMPUTE ----------------
    @api.depends('line_ids.worked_hours', 'line_ids.late_minutes', 'line_ids.late_hours', 'line_ids.overtime_hours', 'line_ids.absence', 'line_ids.deduction_amount', 'line_ids.overtime_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_worked_hours = sum(rec.line_ids.mapped('worked_hours'))
            rec.total_late_minutes = sum(rec.line_ids.mapped('late_minutes'))
            rec.total_late_hours = sum(rec.line_ids.mapped('late_hours'))
            rec.total_overtime_hours = sum(rec.line_ids.mapped('overtime_hours'))
            rec.total_absence_days = sum(rec.line_ids.mapped('absence'))
            rec.total_overtime_amount = sum(rec.line_ids.mapped('overtime_amount'))
            rec.total_deduction = sum(rec.line_ids.mapped('deduction_amount'))

    def _compute_payslip_count(self):
        for rec in self:
            rec.payslip_count = 1 if rec.payslip_id else 0

    @api.constrains('date_from', 'date_to')
    def _check_date_range(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_to < rec.date_from:
                raise ValidationError("End date must be later than or equal to start date")

    def _get_tz(self):
        tz_name = self.env.user.tz or self.env.company.partner_id.tz or 'UTC'
        return pytz.timezone(tz_name)

    def _to_local_datetime(self, utc_datetime):
        if not utc_datetime:
            return False
        tz = self._get_tz()
        utc_datetime = pytz.UTC.localize(utc_datetime) if utc_datetime.tzinfo is None else utc_datetime.astimezone(pytz.UTC)
        return utc_datetime.astimezone(tz)

    def _local_day_bounds_to_utc(self, day):
        tz = self._get_tz()
        local_start = tz.localize(datetime.combine(day, time.min))
        local_end = tz.localize(datetime.combine(day, time.max))
        return (
            local_start.astimezone(pytz.UTC).replace(tzinfo=None),
            local_end.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    def _get_work_start_time(self, day):
        self.ensure_one()
        if self.attendance_policy_id and self.attendance_policy_id.late_start_hour:
            hour = int(self.attendance_policy_id.late_start_hour)
            minute = int(round((self.attendance_policy_id.late_start_hour - hour) * 60))
            if minute == 60:
                hour += 1
                minute = 0
            return time(hour % 24, minute)
        calendar = self.employee_id.resource_calendar_id or self.company_id.resource_calendar_id
        if calendar:
            weekday = str(day.weekday())
            attendance = calendar.attendance_ids.filtered(lambda att: att.dayofweek == weekday).sorted('hour_from')[:1]
            if attendance:
                hour = int(attendance.hour_from)
                minute = int(round((attendance.hour_from - hour) * 60))
                return time(hour, minute)
        return time(9, 0)

    def _get_work_end_time(self, day):
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id or self.company_id.resource_calendar_id
        if calendar:
            weekday = str(day.weekday())
            attendance = calendar.attendance_ids.filtered(lambda att: att.dayofweek == weekday).sorted('hour_to', reverse=True)[:1]
            if attendance:
                hour = int(attendance.hour_to)
                minute = int(round((attendance.hour_to - hour) * 60))
                if minute == 60:
                    hour += 1
                    minute = 0
                return time(hour % 24, minute)
        work_start = self._get_work_start_time(day)
        work_hours = self._get_work_hours(day)
        end_dt = datetime.combine(day, work_start) + timedelta(hours=work_hours)
        return end_dt.time()

    def _get_local_work_start_datetime(self, day):
        self.ensure_one()
        return self._get_tz().localize(datetime.combine(day, self._get_work_start_time(day)))

    def _get_local_work_end_datetime(self, day):
        self.ensure_one()
        start_dt = self._get_local_work_start_datetime(day)
        end_time = self._get_work_end_time(day)
        end_dt = self._get_tz().localize(datetime.combine(day, end_time))
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
        return end_dt

    def _get_next_work_start_datetime(self, day):
        self.ensure_one()
        next_day = day + timedelta(days=1)
        next_start = self._get_tz().localize(datetime.combine(next_day, self._get_work_start_time(next_day)))
        work_end = self._get_local_work_end_datetime(day)
        if next_start <= work_end:
            next_start = work_end + timedelta(days=1)
        return next_start

    def _calculate_overtime_hours(self, day, attendances, is_public_holiday=False):
        self.ensure_one()
        if not attendances:
            return 0.0

        hours = 0.0
        for attendance in attendances:
            hours += self._calculate_overtime_interval_hours(
                day,
                attendance.check_in,
                attendance.check_out,
                is_public_holiday,
            )
        return hours

    def _calculate_overtime_interval_hours(self, day, check_in, check_out, is_public_holiday=False):
        self.ensure_one()
        if not check_in or not check_out:
            return 0.0
        if is_public_holiday:
            overtime_start = self._get_tz().localize(datetime.combine(day, time.min))
        else:
            overtime_start = self._get_local_work_end_datetime(day)
        overtime_end = self._get_next_work_start_datetime(day)

        local_check_in = self._to_local_datetime(check_in)
        local_check_out = self._to_local_datetime(check_out)
        overlap_start = max(local_check_in, overtime_start)
        overlap_end = min(local_check_out, overtime_end)
        if overlap_end > overlap_start:
            return (overlap_end - overlap_start).total_seconds() / 3600.0
        return 0.0

    def _get_work_hours(self, day):
        self.ensure_one()
        calendar = self.employee_id.resource_calendar_id or self.company_id.resource_calendar_id
        if calendar:
            weekday = str(day.weekday())
            attendances = calendar.attendance_ids.filtered(lambda att: att.dayofweek == weekday)
            hours = sum(att.hour_to - att.hour_from for att in attendances)
            if hours:
                return hours
        return 8.0

    def _get_contract(self):
        self.ensure_one()
        contract_model = self.env['hr.contract']
        if self.employee_id.contract_id:
            return self.employee_id.contract_id

        base_domain = [
            ('employee_id', '=', self.employee_id.id),
            '|',
            ('date_start', '=', False),
            ('date_start', '<=', self.date_to),
            '|',
            ('date_end', '=', False),
            ('date_end', '>=', self.date_from),
        ]
        contract = contract_model.search(base_domain + [('state', '=', 'open')], order='date_start desc', limit=1)
        if not contract:
            contract = contract_model.search(base_domain, order='date_start desc', limit=1)
        return contract

    def action_recompute_amounts(self):
        for rec in self:
            rec.line_ids._recompute_late_minutes()
            rec.line_ids._recompute_overtime_hours()
            rec.line_ids._compute_amounts()
            rec._compute_totals()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _get_public_holiday(self, day):
        self.ensure_one()
        day_start, day_end = self._local_day_bounds_to_utc(day)
        domain = [
            ('date_from', '<=', day_end),
            ('date_to', '>=', day_start),
            '|',
            ('resource_id', '=', False),
            ('resource_id', '=', self.employee_id.resource_id.id),
        ]
        if 'company_id' in self.env['resource.calendar.leaves']._fields:
            domain = expression.AND([
                domain,
                ['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id)],
            ])
        return self.env['resource.calendar.leaves'].search(domain, limit=1)

    def _get_payslip_input_commands(self, contract):
        self.ensure_one()
        inputs = []
        policy = self.attendance_policy_id
        if not policy or not policy.generate_payroll_inputs:
            return inputs

        def input_values(name, code, amount):
            input_fields = self.env['hr.payslip.input']._fields
            vals = {}
            if 'name' in input_fields:
                vals['name'] = name
            if 'code' in input_fields:
                vals['code'] = code
            if 'amount' in input_fields:
                vals['amount'] = amount
            if 'attendance_sheet_id' in input_fields:
                vals['attendance_sheet_id'] = self.id
            if contract and 'contract_id' in input_fields:
                vals['contract_id'] = contract.id
            return vals

        if self.total_deduction:
            inputs.append((0, 0, input_values('Attendance Deductions', policy.late_payroll_input_type, self.total_deduction)))
        if self.total_overtime_amount:
            inputs.append((0, 0, input_values('Attendance Overtime', policy.overtime_payroll_input_type, self.total_overtime_amount)))
        if self.total_absence_days:
            inputs.append((0, 0, input_values('Attendance Absence Days', policy.absence_payroll_input_type, self.total_absence_days)))
        return inputs

    def _get_payslip_journal(self, contract):
        self.ensure_one()
        journal_model = self.env['account.journal']
        candidates = []

        if self.attendance_policy_id and self.attendance_policy_id.salary_journal_id:
            return self.attendance_policy_id.salary_journal_id

        if contract and 'struct_id' in contract._fields and contract.struct_id:
            candidates.append(contract.struct_id)
            if 'type_id' in contract.struct_id._fields and contract.struct_id.type_id:
                candidates.append(contract.struct_id.type_id)

        if contract and 'structure_type_id' in contract._fields and contract.structure_type_id:
            candidates.append(contract.structure_type_id)
            if (
                'default_struct_id' in contract.structure_type_id._fields
                and contract.structure_type_id.default_struct_id
            ):
                candidates.append(contract.structure_type_id.default_struct_id)

        for candidate in candidates:
            if 'journal_id' in candidate._fields and candidate.journal_id:
                return candidate.journal_id

        return journal_model.search([
            ('company_id', 'in', [False, self.company_id.id]),
            ('type', '=', 'general'),
        ], limit=1)

    # ---------------- CREATE ----------------
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'mk.attendance.sheet'
            ) or '/'
        if vals.get('employee_id') and not vals.get('attendance_policy_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            if employee.attendance_policy_id:
                vals['attendance_policy_id'] = employee.attendance_policy_id.id
        return super().create(vals)

    # ---------------- GENERATE ----------------
    def action_generate(self):
        for rec in self:
            if not rec.employee_id:
                raise UserError("Please select an employee before generating lines.")
            if rec.date_to < rec.date_from:
                raise UserError("The end date must be later than or equal to the start date.")

            rec.line_ids.unlink()
            values = []
            current = rec.date_from
            
            # Get all attendance records for this employee and date range in UTC.
            start_datetime = rec._local_day_bounds_to_utc(rec.date_from)[0]
            end_datetime = rec._local_day_bounds_to_utc(rec.date_to)[1]
            
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', rec.employee_id.id),
                ('check_in', '>=', start_datetime),
                ('check_in', '<=', end_datetime),
            ], order='check_in asc')
            
            while current <= rec.date_to:
                # Get attendance records for this specific day
                day_start, day_end = rec._local_day_bounds_to_utc(current)
                
                day_attendances = attendances.filtered(
                    lambda a: day_start <= a.check_in <= day_end
                )
                
                check_in = None
                check_out = None
                worked_hours = 0.0
                late_minutes = 0.0
                absence = 1.0
                public_holiday = rec._get_public_holiday(current)
                is_public_holiday = bool(public_holiday)
                is_before_public_holiday = bool(rec._get_public_holiday(current + timedelta(days=1)))
                is_after_public_holiday = bool(rec._get_public_holiday(current - timedelta(days=1)))
                if is_public_holiday:
                    absence = 0.0
                
                if day_attendances:
                    absence = 0.0
                    
                    # Get first check_in of the day
                    sorted_by_checkin = day_attendances.sorted(key=lambda a: a.check_in)
                    check_in = sorted_by_checkin[0].check_in if sorted_by_checkin else None
                    
                    # Get last check_out of the day (or use the last record's check_out)
                    sorted_by_reverse = day_attendances.sorted(key=lambda a: a.check_in, reverse=True)
                    for att in sorted_by_reverse:
                        if att.check_out:
                            check_out = att.check_out
                            break
                    
                    # Calculate total worked hours for the day
                    for attendance in day_attendances:
                        if attendance.check_in and attendance.check_out:
                            delta = attendance.check_out - attendance.check_in
                            worked_hours += delta.total_seconds() / 3600.0
                    
                    # Calculate late minutes using the local timezone and working schedule.
                    if check_in:
                        local_check_in = rec._to_local_datetime(check_in)
                        start_time = rec._get_work_start_time(current)
                        local_start = rec._get_tz().localize(datetime.combine(current, start_time))
                        if local_check_in > local_start:
                            late_delta = local_check_in - local_start
                            late_minutes = late_delta.total_seconds() / 60.0

                absence_day_type = 'normal'
                if is_before_public_holiday:
                    absence_day_type = 'before_public_holiday'
                elif is_after_public_holiday:
                    absence_day_type = 'after_public_holiday'
                
                overtime_hours = rec._calculate_overtime_hours(current, day_attendances, is_public_holiday)

                values.append((0, 0, {
                    'sheet_id': rec.id,
                    'employee_id': rec.employee_id.id,
                    'date': current,
                    'check_in': check_in,
                    'check_out': check_out,
                    'worked_hours': round(worked_hours, 2),
                    'late_minutes': round(late_minutes, 2),
                    'overtime_hours': round(overtime_hours, 2),
                    'is_public_holiday': is_public_holiday,
                    'public_holiday_id': public_holiday.id if public_holiday else False,
                    'is_before_public_holiday': is_before_public_holiday,
                    'is_after_public_holiday': is_after_public_holiday,
                    'absence_day_type': absence_day_type,
                    'absence': absence,
                    'extra_amount': 0.0,
                }))
                current += timedelta(days=1)
            
            rec.line_ids = values

    # ---------------- STATES ----------------
    def action_confirm(self):
        for rec in self:
            if not rec.line_ids:
                rec.action_generate()
            rec.state = 'confirmed'

    def action_approve(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError("Only confirmed sheets can be approved.")
            rec.state = 'approved'

    def action_paid(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError("Only approved sheets can be marked as paid.")
            rec.state = 'paid'

    def action_create_payslip(self):
        for rec in self:
            if rec.payslip_id:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'hr.payslip',
                    'res_id': rec.payslip_id.id,
                    'view_mode': 'form',
                }
            contract = rec._get_contract()
            if not contract:
                raise UserError("No running contract found for this employee in the sheet period.")

            vals = {
                'name': rec.name,
                'employee_id': rec.employee_id.id,
                'date_from': rec.date_from,
                'date_to': rec.date_to,
                'input_line_ids': rec._get_payslip_input_commands(contract),
            }
            payslip_fields = self.env['hr.payslip']._fields
            if 'contract_id' in payslip_fields:
                vals['contract_id'] = contract.id
            if 'struct_id' in payslip_fields and 'struct_id' in contract._fields and contract.struct_id:
                vals['struct_id'] = contract.struct_id.id
            if 'journal_id' in payslip_fields:
                journal = rec._get_payslip_journal(contract)
                if not journal:
                    raise UserError("Please configure a Salary Journal on the salary structure or create a Miscellaneous Journal for this company.")
                vals['journal_id'] = journal.id
            payslip = self.env['hr.payslip'].create(vals)
            rec.payslip_id = payslip.id
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'hr.payslip',
                'res_id': payslip.id,
                'view_mode': 'form',
            }

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    # ---------------- DELETE SAFE ----------------
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("Cannot delete non-draft sheet")
        return super().unlink()
