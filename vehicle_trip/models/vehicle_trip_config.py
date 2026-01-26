from odoo import models, fields


class VehicleTripConfig(models.Model):
_name = 'vehicle.trip.config'
_description = 'Vehicle Trip Configuration'


name = fields.Char('Vehicle Type', required=True)
cost_per_km = fields.Float('Cost per KM', required=True)
cost_per_hour = fields.Float('Cost per Hour', required=True)