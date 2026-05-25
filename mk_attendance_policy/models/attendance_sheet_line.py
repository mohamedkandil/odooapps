from odoo import api, fields, models
from datetime import datetime

class MkAttendanceSheetLine(models.Model):
    _name = 'mk.attendance.sheet.line'
    _description = 'Attendance Sheet Line'
    _order = 'date asc'

    sheet_id = fields.Many2one('mk.attendance.sheet', ondelete='cascade', required=True)
    employee_id = fields.Many2one('hr.employee', related='sheet_id.employee_id', store=True, readonly=False)
    attendance_policy_id = fields.Many2one('mk.attendance.policy', related='sheet_id.attendance_policy_id', store=True, readonly=True)

    date = fields.Date(required=True)

    check_in = fields.Datetime(string='Check In')
    check_out = fields.Datetime(string='Check Out')
    worked_hours = fields.Float(default=0.0, string='Worked Hours')
    late_minutes = fields.Float(default=0.0, string='Late Minutes')
    late_hours = fields.Float(compute='_compute_late_hours', store=True, string='Late Hours')
    late_rated_hours = fields.Float(compute='_compute_amounts', store=True, string='Late Rated Hours')
    late_rule_names = fields.Char(compute='_compute_amounts', store=True)
    overtime_hours = fields.Float(default=0.0)
    overtime_rated_hours = fields.Float(compute='_compute_amounts', store=True, string='Overtime Rated Hours')
    hourly_wage = fields.Float(compute='_compute_amounts', store=True)
    overtime_amount = fields.Float(compute='_compute_amounts', store=True)
    overtime_rule_names = fields.Char(compute='_compute_amounts', store=True)
    is_public_holiday = fields.Boolean(default=False)
    public_holiday_id = fields.Many2one('resource.calendar.leaves', readonly=True)
    is_before_public_holiday = fields.Boolean(default=False)
    is_after_public_holiday = fields.Boolean(default=False)
    absence_day_type = fields.Selection([
        ('normal', 'Normal Day'),
        ('before_public_holiday', 'Before Public Holiday'),
        ('after_public_holiday', 'After Public Holiday'),
    ], default='normal')
    absence = fields.Float(default=0.0)

    absence_deduction_amount = fields.Float(compute='_compute_amounts', store=True)
    absence_rated_days = fields.Float(compute='_compute_amounts', store=True)
    absence_rule_names = fields.Char(compute='_compute_amounts', store=True)
    late_deduction_amount = fields.Float(compute='_compute_amounts', store=True)
    deduction_amount = fields.Float(compute='_compute_amounts', store=True)
    extra_amount = fields.Float(default=0.0)

    @api.depends('late_minutes')
    def _compute_late_hours(self):
        for rec in self:
            rec.late_hours = rec.late_minutes / 60.0

    def _recompute_late_minutes(self):
        for rec in self:
            if not rec.sheet_id or not rec.date or not rec.check_in:
                continue
            local_check_in = rec.sheet_id._to_local_datetime(rec.check_in)
            start_time = rec.sheet_id._get_work_start_time(rec.date)
            local_start = rec.sheet_id._get_tz().localize(
                datetime.combine(rec.date, start_time)
            )
            rec.late_minutes = (
                max(0.0, (local_check_in - local_start).total_seconds() / 60.0)
                if local_check_in > local_start
                else 0.0
            )

    def _recompute_overtime_hours(self):
        for rec in self:
            if not rec.sheet_id or not rec.date:
                continue
            rec.overtime_hours = rec.sheet_id._calculate_overtime_interval_hours(
                rec.date,
                rec.check_in,
                rec.check_out,
                rec.is_public_holiday,
            )

    @api.onchange('is_public_holiday', 'check_in', 'check_out', 'date')
    def _onchange_public_holiday(self):
        for rec in self:
            if rec.sheet_id and rec.date:
                rec.overtime_hours = rec.sheet_id._calculate_overtime_interval_hours(
                    rec.date,
                    rec.check_in,
                    rec.check_out,
                    rec.is_public_holiday,
                )

    @api.depends(
        'attendance_policy_id',
        'date',
        'check_in',
        'check_out',
        'late_minutes',
        'overtime_hours',
        'absence',
        'absence_day_type',
        'is_before_public_holiday',
        'is_after_public_holiday',
        'is_public_holiday',
        'sheet_id.employee_id',
        'sheet_id.date_from',
        'sheet_id.date_to',
        'attendance_policy_id.wage_days_per_month',
        'attendance_policy_id.wage_hours_per_day',
        'attendance_policy_id.late_rate',
        'attendance_policy_id.overtime_rate',
        'attendance_policy_id.grace_in_minutes',
        'attendance_policy_id.late_start_hour',
        'attendance_policy_id.late_rule_ids.minute_from',
        'attendance_policy_id.late_rule_ids.minute_to',
        'attendance_policy_id.late_rule_ids.amount_type',
        'attendance_policy_id.late_rule_ids.multiplier',
        'attendance_policy_id.late_rule_ids.day_fraction',
        'attendance_policy_id.late_rule_ids.fixed_amount',
        'attendance_policy_id.overtime_rule_ids.day_type',
        'attendance_policy_id.overtime_rule_ids.sequence',
        'attendance_policy_id.overtime_rule_ids.name',
        'attendance_policy_id.overtime_rule_ids.hour_from',
        'attendance_policy_id.overtime_rule_ids.hour_to',
        'attendance_policy_id.overtime_rule_ids.amount_type',
        'attendance_policy_id.overtime_rule_ids.multiplier',
        'attendance_policy_id.overtime_rule_ids.fixed_amount',
        'attendance_policy_id.absence_rule_ids.day_type',
        'attendance_policy_id.absence_rule_ids.sequence',
        'attendance_policy_id.absence_rule_ids.name',
        'attendance_policy_id.absence_rule_ids.amount_type',
        'attendance_policy_id.absence_rule_ids.percentage',
        'attendance_policy_id.absence_rule_ids.fixed_amount',
    )
    def _compute_amounts(self):
        for rec in self:
            policy = rec.attendance_policy_id
            if not policy:
                rec.hourly_wage = 0.0
                rec.late_deduction_amount = 0.0
                rec.late_rated_hours = 0.0
                rec.late_rule_names = False
                rec.absence_deduction_amount = 0.0
                rec.absence_rated_days = 0.0
                rec.absence_rule_names = False
                rec.deduction_amount = 0.0
                rec.overtime_amount = 0.0
                rec.overtime_rated_hours = 0.0
                rec.overtime_rule_names = False
                continue

            contract = rec.sheet_id._get_contract() if rec.sheet_id else False
            rec.hourly_wage = policy._get_hourly_wage(contract)
            late_deduction, late_rated_hours, late_rules, used_default_late_rate = policy._calculate_late_details(
                rec.late_minutes,
                contract,
            )
            absence_day_type = rec._get_absence_day_type()
            absence_deduction, absence_rated_days, absence_rules, used_default_absence_rate = policy._calculate_absence_details(
                rec.absence,
                contract,
                absence_day_type,
            )
            overtime_amount, overtime_rated_hours, overtime_rules, used_default_rate = policy._calculate_overtime_details(
                rec.overtime_hours,
                contract,
                rec.is_public_holiday,
            )
            rec.late_deduction_amount = late_deduction
            rec.late_rated_hours = late_rated_hours
            rec.late_rule_names = ', '.join(late_rules.mapped('name')) or ('Default Late Rate' if used_default_late_rate else False)
            rec.absence_deduction_amount = absence_deduction
            rec.absence_rated_days = absence_rated_days
            rec.absence_rule_names = ', '.join(absence_rules.mapped('name')) or ('Default Absence Rate' if used_default_absence_rate else False)
            rec.deduction_amount = late_deduction + absence_deduction
            rec.overtime_amount = overtime_amount
            rec.overtime_rated_hours = overtime_rated_hours
            rec.overtime_rule_names = ', '.join(overtime_rules.mapped('name')) or ('Default Overtime Rate' if used_default_rate else False)

    def _get_amount_values(self):
        self.ensure_one()
        policy = self.attendance_policy_id
        if not policy:
            return {
                'hourly_wage': 0.0,
                'late_deduction_amount': 0.0,
                'late_rated_hours': 0.0,
                'late_rule_names': False,
                'absence_deduction_amount': 0.0,
                'absence_rated_days': 0.0,
                'absence_rule_names': False,
                'deduction_amount': 0.0,
                'overtime_amount': 0.0,
                'overtime_rated_hours': 0.0,
                'overtime_rule_names': False,
            }

        contract = self.sheet_id._get_contract() if self.sheet_id else False
        hourly_wage = policy._get_hourly_wage(contract)
        late_deduction, late_rated_hours, late_rules, used_default_late_rate = policy._calculate_late_details(
            self.late_minutes,
            contract,
        )
        absence_day_type = self._get_absence_day_type()
        absence_deduction, absence_rated_days, absence_rules, used_default_absence_rate = policy._calculate_absence_details(
            self.absence,
            contract,
            absence_day_type,
        )
        overtime_amount, overtime_rated_hours, overtime_rules, used_default_rate = policy._calculate_overtime_details(
            self.overtime_hours,
            contract,
            self.is_public_holiday,
        )
        return {
            'hourly_wage': hourly_wage,
            'late_deduction_amount': late_deduction,
            'late_rated_hours': late_rated_hours,
            'late_rule_names': ', '.join(late_rules.mapped('name')) or ('Default Late Rate' if used_default_late_rate else False),
            'absence_deduction_amount': absence_deduction,
            'absence_rated_days': absence_rated_days,
            'absence_rule_names': ', '.join(absence_rules.mapped('name')) or ('Default Absence Rate' if used_default_absence_rate else False),
            'deduction_amount': late_deduction + absence_deduction,
            'overtime_amount': overtime_amount,
            'overtime_rated_hours': overtime_rated_hours,
            'overtime_rule_names': ', '.join(overtime_rules.mapped('name')) or ('Default Overtime Rate' if used_default_rate else False),
        }

    def _get_absence_day_type(self):
        self.ensure_one()
        if self.absence_day_type:
            return self.absence_day_type
        if self.is_before_public_holiday:
            return 'before_public_holiday'
        if self.is_after_public_holiday:
            return 'after_public_holiday'
        return 'normal'

    def _get_overtime_interval(self):
        self.ensure_one()
        if not self.sheet_id or not self.date or not self.check_out or not self.overtime_hours:
            return False, False

        def local_hour(value):
            local_dt = self.sheet_id._to_local_datetime(value)
            day_offset = (local_dt.date() - self.date).days if local_dt else 0
            return (
                day_offset * 24.0
                + local_dt.hour
                + local_dt.minute / 60.0
                + local_dt.second / 3600.0
            )

        overtime_to = local_hour(self.check_out)
        if self.is_public_holiday and self.check_in:
            overtime_from = local_hour(self.check_in)
        else:
            work_end = self.sheet_id._get_work_end_time(self.date)
            overtime_from = work_end.hour + work_end.minute / 60.0 + work_end.second / 3600.0

        if overtime_to <= overtime_from:
            overtime_to = overtime_from + self.overtime_hours
        return overtime_from, overtime_to

    note = fields.Text()
