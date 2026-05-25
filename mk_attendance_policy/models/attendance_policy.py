from odoo import api, fields, models
from odoo.exceptions import ValidationError

class MkAttendancePolicy(models.Model):
    _name = 'mk.attendance.policy'
    _description = 'Attendance Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    late_rate = fields.Float(default=0.0)
    overtime_rate = fields.Float(default=1.5)
    absence_rate = fields.Float(default=100.0, string='Default Absence %')

    grace_in_minutes = fields.Integer(default=0)
    late_start_hour = fields.Float(
        string='Late Start Hour',
        help='Leave zero to use the employee working schedule. Set 9.0 to calculate late minutes after 09:00.',
    )
    wage_days_per_month = fields.Float(default=30.0)
    wage_hours_per_day = fields.Float(default=8.0)

    late_rule_ids = fields.One2many(
        'mk.attendance.late.rule',
        'policy_id',
        string='Late Rules',
    )
    overtime_rule_ids = fields.One2many(
        'mk.attendance.overtime.rule',
        'policy_id',
        string='Overtime Rules',
    )
    absence_rule_ids = fields.One2many(
        'mk.attendance.absence.rule',
        'policy_id',
        string='Absence Rules',
    )

    generate_payroll_inputs = fields.Boolean(default=True)

    late_payroll_input_type = fields.Char(default='LATE')
    absence_payroll_input_type = fields.Char(default='ABSENCE')
    overtime_payroll_input_type = fields.Char(default='OVERTIME')
    salary_journal_id = fields.Many2one(
        'account.journal',
        string='Salary Journal',
        domain="[('type', '=', 'general'), ('company_id', 'in', [False, company_id])]",
        check_company=True,
    )

    @api.constrains('late_rate', 'overtime_rate', 'absence_rate')
    def _check_rates(self):
        for rec in self:
            if rec.late_rate < 0:
                raise ValidationError("Late rate must be zero or positive")
            if rec.overtime_rate < 0:
                raise ValidationError("Overtime rate must be zero or positive")
            if rec.absence_rate < 0 or rec.absence_rate > 100:
                raise ValidationError("Absence rate must be between 0 and 100")

    def _calculate_late(self, minutes):
        self.ensure_one()
        if minutes <= self.grace_in_minutes:
            return 0.0
        return minutes * self.late_rate

    def _get_hourly_wage(self, contract):
        self.ensure_one()
        if not contract or not self.wage_days_per_month or not self.wage_hours_per_day:
            return 0.0
        return contract.wage / (self.wage_days_per_month * self.wage_hours_per_day)

    def _calculate_late_amount(self, minutes, contract):
        return self._calculate_late_details(minutes, contract)[0]

    def _calculate_late_details(self, minutes, contract):
        self.ensure_one()
        chargeable_minutes = max(0.0, minutes - self.grace_in_minutes)
        if not chargeable_minutes:
            return 0.0, 0.0, self.env['mk.attendance.late.rule'], False

        hourly_wage = self._get_hourly_wage(contract)
        rules = self.late_rule_ids.sorted('sequence')
        if not rules:
            rated_hours = (chargeable_minutes / 60.0) * self.late_rate
            return rated_hours * hourly_wage, rated_hours, rules, True

        applied_rules = self.env['mk.attendance.late.rule']
        for rule in rules:
            if not rule._matches_minutes(chargeable_minutes):
                continue
            amount, rated_hours = rule._calculate_full_minutes_details(
                chargeable_minutes,
                hourly_wage,
                self.wage_hours_per_day,
            )
            applied_rules |= rule
            return amount, rated_hours, applied_rules, False
        return 0.0, 0.0, applied_rules, False

    def _calculate_overtime_amount(self, hours, contract, is_public_holiday=False, hour_from=False, hour_to=False):
        self.ensure_one()
        return self._calculate_overtime_details(hours, contract, is_public_holiday)[0]

    def _get_overtime_rules(self, is_public_holiday=False):
        self.ensure_one()
        day_type = 'holiday' if is_public_holiday else 'normal'
        return self.overtime_rule_ids.filtered(lambda rule: rule.day_type == day_type).sorted('sequence')

    def _calculate_overtime_details(self, hours, contract, is_public_holiday=False, hour_from=False, hour_to=False):
        self.ensure_one()
        if not hours:
            return 0.0, 0.0, self.env['mk.attendance.overtime.rule'], False

        hourly_wage = self._get_hourly_wage(contract)
        rules = self._get_overtime_rules(is_public_holiday)
        if not rules:
            rated_hours = hours * self.overtime_rate
            return rated_hours * hourly_wage, rated_hours, rules, True

        amount = 0.0
        rated_hours = 0.0
        applied_rules = self.env['mk.attendance.overtime.rule']
        for rule in rules:
            rule_amount, rule_rated_hours = rule._calculate_details(hours, hourly_wage)
            if rule_amount:
                amount += rule_amount
                rated_hours += rule_rated_hours
                applied_rules |= rule
        return amount, rated_hours, applied_rules, False

    def _calculate_overtime(self, hours):
        self.ensure_one()
        return hours * self.overtime_rate

    def _calculate_absence(self, days):
        self.ensure_one()
        return days * self.absence_rate

    def _get_absence_rules(self, absence_day_type='normal'):
        self.ensure_one()
        return self.absence_rule_ids.filtered(
            lambda rule: rule.day_type == absence_day_type
        ).sorted('sequence')

    def _calculate_absence_details(self, days, contract, absence_day_type='normal'):
        self.ensure_one()
        if not days:
            return 0.0, 0.0, self.env['mk.attendance.absence.rule'], False

        daily_wage = self._get_hourly_wage(contract) * self.wage_hours_per_day
        rules = self._get_absence_rules(absence_day_type)
        if not rules:
            rated_days = days * (self.absence_rate / 100.0)
            return rated_days * daily_wage, rated_days, rules, True

        rule = rules[:1]
        amount, rated_days = rule._calculate_details(days, daily_wage)
        return amount, rated_days, rule, False


class MkAttendanceLateRule(models.Model):
    _name = 'mk.attendance.late.rule'
    _description = 'Attendance Late Rule'
    _order = 'policy_id, sequence, minute_from'

    policy_id = fields.Many2one('mk.attendance.policy', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    minute_from = fields.Float(default=0.0, required=True)
    minute_to = fields.Float(help='Leave empty for no upper limit.')
    amount_type = fields.Selection([
        ('none', 'No Deduction'),
        ('day_fraction', 'Day Wage Fraction'),
        ('hourly_wage_multiplier', 'Hourly Wage Multiplier'),
        ('fixed_per_hour', 'Fixed Amount Per Hour'),
        ('fixed', 'Fixed Amount'),
    ], default='hourly_wage_multiplier', required=True)
    multiplier = fields.Float(default=1.0)
    day_fraction = fields.Float(default=0.0)
    fixed_amount = fields.Float(default=0.0)

    def _get_overlap(self, value):
        self.ensure_one()
        upper = self.minute_to or value
        return max(0.0, min(value, upper) - self.minute_from)

    def _calculate_amount(self, minutes, hourly_wage):
        self.ensure_one()
        return self._calculate_details(minutes, hourly_wage)[0]

    def _calculate_details(self, minutes, hourly_wage):
        self.ensure_one()
        overlap_minutes = self._get_overlap(minutes)
        if not overlap_minutes:
            return 0.0, 0.0
        overlap_hours = overlap_minutes / 60.0
        return self._amount_from_hours(overlap_hours, hourly_wage), self._rated_hours_from_hours(overlap_hours)

    def _calculate_full_minutes_details(self, minutes, hourly_wage, wage_hours_per_day=False):
        self.ensure_one()
        if not minutes:
            return 0.0, 0.0
        hours = minutes / 60.0
        return self._amount_from_hours(hours, hourly_wage, wage_hours_per_day), self._rated_hours_from_hours(hours, wage_hours_per_day)

    def _matches_minutes(self, minutes):
        self.ensure_one()
        upper = self.minute_to or minutes
        return self.minute_from <= minutes <= upper

    def _amount_from_hours(self, hours, hourly_wage, wage_hours_per_day=False):
        self.ensure_one()
        if self.amount_type == 'none':
            return 0.0
        if self.amount_type == 'day_fraction':
            return hourly_wage * (wage_hours_per_day or 0.0) * self.day_fraction
        if self.amount_type == 'fixed':
            return self.fixed_amount
        if self.amount_type == 'fixed_per_hour':
            return hours * self.fixed_amount
        return hours * hourly_wage * self.multiplier

    def _rated_hours_from_hours(self, hours, wage_hours_per_day=False):
        self.ensure_one()
        if self.amount_type == 'day_fraction':
            return (wage_hours_per_day or 0.0) * self.day_fraction
        if self.amount_type == 'hourly_wage_multiplier':
            return hours * self.multiplier
        return 0.0


class MkAttendanceOvertimeRule(models.Model):
    _name = 'mk.attendance.overtime.rule'
    _description = 'Attendance Overtime Rule'
    _order = 'policy_id, day_type, sequence, hour_from'

    policy_id = fields.Many2one('mk.attendance.policy', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    day_type = fields.Selection([
        ('normal', 'Normal Day'),
        ('holiday', 'Public Holiday'),
    ], default='normal', required=True)
    hour_from = fields.Float(
        default=0.0,
        required=True,
        string='Overtime Hours From',
        help='Start of the overtime tier, counted from the end of working hours.',
    )
    hour_to = fields.Float(
        string='Overtime Hours To',
        help='End of the overtime tier, counted from the end of working hours. Leave empty for no upper limit.',
    )
    amount_type = fields.Selection([
        ('hourly_wage_multiplier', 'Hourly Wage Multiplier'),
        ('fixed_per_hour', 'Fixed Amount Per Hour'),
        ('fixed', 'Fixed Amount'),
    ], default='hourly_wage_multiplier', required=True)
    multiplier = fields.Float(default=1.5)
    fixed_amount = fields.Float(default=0.0)

    def _get_overlap(self, value):
        self.ensure_one()
        upper = self.hour_to or value
        return max(0.0, min(value, upper) - self.hour_from)

    def _calculate_amount(self, hours, hourly_wage):
        self.ensure_one()
        return self._calculate_details(hours, hourly_wage)[0]

    def _calculate_details(self, hours, hourly_wage):
        self.ensure_one()
        overlap_hours = self._get_overlap(hours)
        if not overlap_hours:
            return 0.0, 0.0
        return self._amount_from_hours(overlap_hours, hourly_wage), self._rated_hours_from_hours(overlap_hours)

    def _calculate_full_hours_details(self, hours, hourly_wage):
        self.ensure_one()
        if not hours:
            return 0.0, 0.0
        return self._amount_from_hours(hours, hourly_wage), self._rated_hours_from_hours(hours)

    def _calculate_interval_amount(self, hour_from, hour_to, hourly_wage):
        self.ensure_one()
        return self._calculate_interval_details(hour_from, hour_to, hourly_wage)[0]

    def _calculate_interval_details(self, hour_from, hour_to, hourly_wage):
        self.ensure_one()
        overlap_hours = self._get_interval_overlap(hour_from, hour_to)
        if not overlap_hours:
            return 0.0, 0.0
        return self._amount_from_hours(overlap_hours, hourly_wage), self._rated_hours_from_hours(overlap_hours)

    def _matches_interval(self, hour_from, hour_to):
        self.ensure_one()
        return bool(self._get_interval_overlap(hour_from, hour_to))

    def _get_interval_overlap(self, hour_from, hour_to):
        self.ensure_one()
        if hour_to <= hour_from:
            hour_to += 24.0
        rule_from = self.hour_from
        rule_to = self.hour_to or hour_to
        if rule_to <= rule_from:
            rule_to += 24.0
        return max(0.0, min(hour_to, rule_to) - max(hour_from, rule_from))

    def _amount_from_hours(self, overlap_hours, hourly_wage):
        self.ensure_one()
        if self.amount_type == 'fixed':
            return self.fixed_amount
        if self.amount_type == 'fixed_per_hour':
            return overlap_hours * self.fixed_amount
        return overlap_hours * hourly_wage * self.multiplier

    def _rated_hours_from_hours(self, overlap_hours):
        self.ensure_one()
        if self.amount_type == 'hourly_wage_multiplier':
            return overlap_hours * self.multiplier
        return 0.0


class MkAttendanceAbsenceRule(models.Model):
    _name = 'mk.attendance.absence.rule'
    _description = 'Attendance Absence Rule'
    _order = 'policy_id, day_type, sequence'

    policy_id = fields.Many2one('mk.attendance.policy', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    day_type = fields.Selection([
        ('normal', 'Normal Day'),
        ('before_public_holiday', 'Before Public Holiday'),
        ('after_public_holiday', 'After Public Holiday'),
    ], default='normal', required=True)
    amount_type = fields.Selection([
        ('day_wage_percentage', 'Day Wage Percentage'),
        ('fixed_per_day', 'Fixed Amount Per Day'),
        ('fixed', 'Fixed Amount'),
    ], default='day_wage_percentage', required=True)
    percentage = fields.Float(default=100.0)
    fixed_amount = fields.Float(default=0.0)

    def _calculate_details(self, days, daily_wage):
        self.ensure_one()
        if not days:
            return 0.0, 0.0
        if self.amount_type == 'fixed':
            return self.fixed_amount, 0.0
        if self.amount_type == 'fixed_per_day':
            return days * self.fixed_amount, 0.0
        rated_days = days * (self.percentage / 100.0)
        return rated_days * daily_wage, rated_days
