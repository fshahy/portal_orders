# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import ValidationError


# @tagged("-at_install", "post_install")
class TestPortalOrder(TransactionCase):
    def setUp(self, *args, **kwargs):
        super(TestPortalOrder, self).setUp(*args, **kwargs)

        self.a_user = self.env.ref("portal_orders.portal_employee_1")
        self.a_product = self.env.ref("portal_orders.product_template_product_1")
        self.a_supplierinfo = self.env.ref("portal_orders.supplier_info_1")
        self.a_attachment = self.env.ref("portal_orders.attach_1")

        self.order = self.env["portal.order"].create(
            {
                "name": "New",
                "user_id": self.a_user.id,
                "product_id": self.a_product.id,
                "supplierinfo_id": self.a_supplierinfo.id,
                "amount": 1,
                "attachment_ids": [self.a_attachment.id],
                "tax": 10.0,
            }
        )

    def test_gross_price(self):
        self.assertEqual(self.order.gross_price, 10, "gross price must be 10")

    def test_taxed_price(self):
        self.assertEqual(self.order.taxed_price, 11, "taxed price must be 11")

    def test_invalid_amount(self):
        self.order.amount = 4
        with self.assertRaises(ValidationError):
            self.order._calc_gross_price()

    def test_picking_date(self):
        with self.assertRaises(ValidationError):
            self.order.set_done()
