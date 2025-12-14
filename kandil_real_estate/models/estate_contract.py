from odoo import fields, models, api

class EstateContract(models.Model):
    _name = 'estate.contract'
    _description = 'Contract'

    name = fields.Char(string='Contract Reference', required=True, copy=False, readonly=True, default='New')
    reservation_id = fields.Many2one('estate.reservation', string='Reservation')
    unit_id = fields.Many2one('estate.unit', string='Unit', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    contract_type = fields.Selection([('sale','Sale'),('rent','Rent')], default='sale')
    start_date = fields.Date()
    end_date = fields.Date()
    # إضافة حقل العملة (ضروري لكل Monetary في نفس الموديل)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)
    total_amount = fields.Monetary(currency_field='currency_id')
    down_payment = fields.Monetary(currency_field='currency_id')
    state = fields.Selection([('draft','Draft'),('active','Active'),('closed','Closed'),('terminated','Terminated')], default='draft')
    salesperson_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    installment_ids = fields.One2many('estate.installment', 'contract_id', string='Installments')
    note = fields.Html(string='Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('estate.contract') or 'New'
        if 'currency_id' not in vals:
            vals['currency_id'] = self.env.company.currency_id.id
        rec = super().create(vals)
        return rec

    def action_activate(self):
        for rec in self:
            rec.state = 'active'
            rec.unit_id.status = 'sold' if rec.contract_type == 'sale' else 'rented'

    def action_close(self):
        for rec in self:
            rec.state = 'closed'
