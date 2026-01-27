from odoo import models, fields, api
from odoo.exceptions import UserError


class VehicleTrip(models.Model):
    _name = 'vehicle.trip'
    _description = 'Vehicle Trip'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True)
    driver_id = fields.Many2one('res.partner', string='Driver')

    start_odometer = fields.Float('Start Odometer', required=True)
    end_odometer = fields.Float('End Odometer', required=True)
    trip_km = fields.Float(
        'Trip KM',
        compute='_compute_km',
        store=True,
        readonly=True
    )

    start_time = fields.Datetime('Start Time', required=True)
    end_time = fields.Datetime('End Time', required=True)
    trip_hours = fields.Float(
        'Trip Hours',
        compute='_compute_hours',
        store=True,
        readonly=True
    )

    config_id = fields.Many2one(
        'vehicle.trip.config',
        string='Vehicle Type',
        required=True
    )

    trip_cost = fields.Float(
        'Trip Cost',
        compute='_compute_cost',
        store=True,
        readonly=True
    )

    account_move_id = fields.Many2one(
        'account.move',
        string='Expense Entry',
        readonly=True
    )

    # ===================== COMPUTES =====================

    @api.depends('start_odometer', 'end_odometer')
    def _compute_km(self):
        for rec in self:
            rec.trip_km = max(rec.end_odometer - rec.start_odometer, 0)

    @api.depends('start_time', 'end_time')
    def _compute_hours(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                delta = rec.end_time - rec.start_time
                rec.trip_hours = delta.total_seconds() / 3600
            else:
                rec.trip_hours = 0

    @api.depends('trip_km', 'trip_hours', 'config_id')
    def _compute_cost(self):
        threshold = float(
            self.env['ir.config_parameter']
            .sudo()
            .get_param('vehicle_trip.hour_threshold', default=5)
        )

        for rec in self:
            if not rec.config_id:
                rec.trip_cost = 0
                continue

            if rec.trip_hours > threshold:
                rec.trip_cost = rec.trip_hours * rec.config_id.cost_per_hour
            else:
                rec.trip_cost = rec.trip_km * rec.config_id.cost_per_km

    # ===================== ACCOUNTING =====================

    def action_create_expense(self):
        for rec in self:
            if rec.account_move_id:
                raise UserError('Expense already created for this trip.')

            account = self.env['account.account'].search(
                [('account_type', '=', 'expense')],
                limit=1
            )

            if not account:
                raise UserError(
                    'Please configure an Expense account before creating expense entries.'
                )

            move_vals = {
                'move_type': 'entry',
                'line_ids': [(0, 0, {
                    'name': f'Trip Cost: {rec.vehicle_id.name}',
                    'account_id': account.id,
                    'debit': rec.trip_cost,
                    'credit': 0,
                })],
            }

            move = self.env['account.move'].create(move_vals)
            rec.account_move_id = move.id
