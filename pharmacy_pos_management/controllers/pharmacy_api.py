import json

from odoo import http
from odoo.http import request


class PharmacyApiController(http.Controller):

    def _json_response(self, payload, status=200):
        return request.make_response(
            json.dumps(payload, default=str),
            headers=[('Content-Type', 'application/json')],
            status=status,
        )

    @http.route('/pharmacy/api/products', type='http', auth='user', methods=['GET'], csrf=False)
    def products(self, **kwargs):
        domain = [('active', '=', True)]
        search = kwargs.get('search')
        if search:
            domain += ['|', '|', ('name', 'ilike', search), ('barcode', 'ilike', search), ('scientific_name', 'ilike', search)]
        products = request.env['pharmacy.product'].search(domain, limit=int(kwargs.get('limit', 80)))
        return self._json_response({
            'products': [{
                'id': product.id,
                'name': product.name,
                'barcode': product.barcode,
                'scientific_name': product.scientific_name,
                'trade_name': product.trade_name,
                'list_price': product.list_price,
                'available_qty': product.available_qty,
                'prescription_required': product.prescription_required,
                'controlled_medicine': product.controlled_medicine,
            } for product in products]
        })

    @http.route('/pharmacy/api/stock', type='http', auth='user', methods=['GET'], csrf=False)
    def stock(self, **kwargs):
        domain = []
        if kwargs.get('branch_id'):
            domain.append(('branch_id', '=', int(kwargs['branch_id'])))
        if kwargs.get('product_id'):
            domain.append(('product_id', '=', int(kwargs['product_id'])))
        lines = request.env['pharmacy.inventory'].search(domain, limit=int(kwargs.get('limit', 100)))
        return self._json_response({
            'stock': [{
                'branch': line.branch_id.display_name,
                'product': line.product_id.display_name,
                'batch': line.batch_id.display_name,
                'quantity': line.quantity,
                'expiry_date': line.expiry_date,
                'state': line.stock_state,
            } for line in lines]
        })

    @http.route('/pharmacy/api/reports/summary', type='http', auth='user', methods=['GET'], csrf=False)
    def summary(self, **kwargs):
        orders = request.env['pharmacy.pos.order'].search([('state', '=', 'paid')])
        return self._json_response({
            'paid_orders': len(orders),
            'sales_total': sum(orders.mapped('total')),
            'near_expiry_batches': request.env['pharmacy.batch'].search_count([('is_near_expiry', '=', True)]),
            'expired_batches': request.env['pharmacy.batch'].search_count([('is_expired', '=', True)]),
        })
