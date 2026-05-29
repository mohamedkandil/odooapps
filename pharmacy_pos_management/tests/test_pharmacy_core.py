from odoo.tests.common import TransactionCase


class TestPharmacyCore(TransactionCase):

    def test_pos_order_total(self):
        branch = self.env['pharmacy.branch'].create({
            'name': 'Test Branch',
            'code': 'TB',
            'company_id': self.env.company.id,
        })
        product = self.env['pharmacy.product'].create({
            'name': 'Test Medicine',
            'list_price': 25.0,
        })
        session = self.env['pharmacy.pos'].create({
            'name': 'Test Session',
            'branch_id': branch.id,
            'cashier_id': self.env.user.id,
        })
        order = self.env['pharmacy.pos.order'].create({
            'pos_id': session.id,
            'order_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 2.0,
                'price_unit': 25.0,
                'discount': 10.0,
            })],
        })
        self.assertEqual(order.total, 45.0)
