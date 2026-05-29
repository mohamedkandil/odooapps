from odoo import models, fields, api

class PharmacyPrescription(models.Model):
    _name = 'pharmacy.prescription'
    _description = 'Pharmacy Prescription'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    patient_id = fields.Many2one('pharmacy.customer', string='Patient', required=True, tracking=True)
    doctor_name = fields.Char(tracking=True)
    doctor_license = fields.Char(tracking=True)
    prescription_date = fields.Date(default=fields.Date.today, tracking=True)
    prescription_file = fields.Binary('Prescription File')
    ocr_text = fields.Text('OCR Result')
    allergy_warning = fields.Text()
    interaction_alert = fields.Text()
    refill_allowed = fields.Boolean(default=False)
    pos_order_ids = fields.One2many('pharmacy.pos.order', 'prescription_id', string='POS Orders')
    refill_parent_id = fields.Many2one('pharmacy.prescription', string='Refill Of')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('validated', 'Validated'),
        ('expired', 'Expired')
    ], default='draft', tracking=True)

    def action_validate(self):
        self.write({'state': 'validated'})

    def action_expire(self):
        self.write({'state': 'expired'})

    def action_create_refill(self):
        for prescription in self:
            prescription.copy({
                'name': '%s Refill' % prescription.name,
                'refill_parent_id': prescription.id,
                'state': 'draft',
            })
