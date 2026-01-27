from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    trip_hour_threshold = fields.Float(
        string='Trip Hour Threshold',
        default=5,
        config_parameter='vehicle_trip.hour_threshold'
    )
