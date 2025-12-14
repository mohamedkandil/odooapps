from odoo import fields, models, api

class EstateBuilding(models.Model):
    _name = 'estate.building'
    _description = 'Building'

    name = fields.Char(required=True)
    address = fields.Text()
    developer_id = fields.Many2one('res.partner', string='Developer')
    unit_ids = fields.One2many('estate.unit', 'building_id', string='Units')
    total_units = fields.Integer(compute='_compute_total_units')
    active = fields.Boolean(default=True)

    def _compute_total_units(self):
        for rec in self:
            rec.total_units = len(rec.unit_ids)
