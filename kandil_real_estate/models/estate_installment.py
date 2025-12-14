from odoo import fields, models, api

class EstateInstallment(models.Model):
    _name = 'estate.installment'
    _description = 'Contract Installment'

    contract_id = fields.Many2one('estate.contract', string='Contract', required=True)
    due_date = fields.Date()
    # حقل العملة مربوط بعلاقة contract.currency_id (مهم لـ Monetary)
    currency_id = fields.Many2one('res.currency', related='contract_id.currency_id', store=True, readonly=True)
    amount = fields.Monetary(currency_field='currency_id')
    paid = fields.Boolean(default=False)
    payment_id = fields.Many2one('account.payment', string='Payment')

    def action_set_paid(self):
        for rec in self:
            rec.paid = True
