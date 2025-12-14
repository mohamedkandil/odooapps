from odoo import fields, models, api

class EstateReservation(models.Model):
    _name = 'estate.reservation'
    _description = 'Reservation'

    name = fields.Char(string='Reservation Reference', required=True, copy=False, readonly=True, default='New')
    unit_id = fields.Many2one('estate.unit', string='Unit', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    date = fields.Date(default=fields.Date.context_today)
    deposit_amount = fields.Monetary('Deposit')
    currency_id = fields.Many2one('res.currency', related='unit_id.currency_id', store=True)
    status = fields.Selection([('draft','Draft'),('confirmed','Confirmed'),('cancelled','Cancelled')], default='draft')
    note = fields.Text()

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            seq = self.env['ir.sequence'].next_by_code('estate.reservation') or 'New'
            vals['name'] = seq
        return super().create(vals)

    def action_confirm(self):
        for rec in self:
            rec.status = 'confirmed'
            rec.unit_id.status = 'reserved'

    def action_cancel(self):
        for rec in self:
            rec.status = 'cancelled'
            if not self.env['estate.contract'].search([('reservation_id','=',rec.id)]):
                rec.unit_id.status = 'available'
