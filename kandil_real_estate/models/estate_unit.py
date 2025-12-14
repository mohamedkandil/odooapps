from odoo import fields, models, api

class EstateUnit(models.Model):
    _name = 'estate.unit'
    _description = 'Real Estate Unit'
    _rec_name = 'name'

    name = fields.Char(required=True)
    building_id = fields.Many2one('estate.building', string='Building')
    unit_type = fields.Selection([('apartment','Apartment'),('villa','Villa'),('shop','Shop'),('office','Office')], default='apartment')
    area_sqm = fields.Float('Area (sqm)')
    bedrooms = fields.Integer()
    price = fields.Monetary('Price')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    status = fields.Selection([('available','Available'),('reserved','Reserved'),('sold','Sold'),('rented','Rented')], default='available')
    floor = fields.Integer()
    features = fields.Text()
    assigned_partner_id = fields.Many2one('res.partner', string='Assigned To')
    reservation_count = fields.Integer(compute='_compute_reservation_count')
    reservation_ids = fields.One2many('estate.reservation','unit_id', string='Reservations')

    def _compute_reservation_count(self):
        for rec in self:
            rec.reservation_count = self.env['estate.reservation'].search_count([('unit_id','=',rec.id)])

    def action_set_reserved(self):
        self.status = 'reserved'

    def action_set_sold(self):
        self.status = 'sold'
