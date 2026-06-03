from odoo import models, fields, api

class PharmacyProduct(models.Model):
    _name = 'pharmacy.product'
    _description = 'Pharmacy Product'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    barcode = fields.Char(tracking=True)
    qr_code = fields.Char(tracking=True)
    sku = fields.Char(tracking=True)
    scientific_name = fields.Char(tracking=True)
    trade_name = fields.Char(tracking=True)
    active_ingredient = fields.Char(tracking=True)
    manufacturer = fields.Char(tracking=True)
    country_of_origin = fields.Char(tracking=True)
    dosage = fields.Char(tracking=True)
    drug_form = fields.Char(tracking=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    product_tmpl_id = fields.Many2one('product.template', string='Odoo Product Template')
    product_image = fields.Binary('Product Image')
    pdf_attachment = fields.Many2many('ir.attachment', string='PDF Attachments')
    alternative_ids = fields.Many2many('pharmacy.product', 'pharmacy_product_alternative_rel', 'product_id', 'alt_id', string='Alternative Medicines')
    drug_interaction_warning = fields.Text()
    controlled_medicine = fields.Boolean(default=False)
    prescription_required = fields.Boolean(default=False)
    favorite_pos = fields.Boolean('Favorite in POS', default=False)
    standard_price = fields.Float('Cost')
    list_price = fields.Float('Sales Price')
    is_otc = fields.Boolean('OTC Product', default=False)
    is_cosmetic = fields.Boolean('Cosmetic', default=False)
    is_device = fields.Boolean('Medical Device', default=False)
    is_supplement = fields.Boolean('Supplement', default=False)
    is_baby_product = fields.Boolean('Baby Product', default=False)
    batch_ids = fields.One2many('pharmacy.batch', 'product_id', string='Batches')
    available_qty = fields.Float(compute='_compute_available_qty', string='Available Quantity')
    active = fields.Boolean(default=True)

    def _compute_available_qty(self):
        inventory_model = self.env['pharmacy.inventory']
        for product in self:
            product.available_qty = sum(inventory_model.search([('product_id', '=', product.id)]).mapped('quantity'))
