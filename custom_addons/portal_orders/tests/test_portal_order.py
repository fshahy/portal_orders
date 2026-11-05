import base64

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import HttpCase, TransactionCase, tagged
from odoo.tools import file_open, mute_logger


class PortalOrderCommon(TransactionCase):
    # Relies on the module's demo data (users, products, vendors).

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice = cls.env.ref("portal_orders.portal_employee_1")
        cls.bob = cls.env.ref("portal_orders.portal_employee_2")
        cls.john = cls.env.ref("portal_orders.portal_manager")
        cls.ingrid = cls.env.ref("portal_orders.internal_user_1")
        cls.product = cls.env.ref("portal_orders.product_template_product_1").product_variant_ids[:1]
        cls.supplierinfo = cls.env.ref("portal_orders.supplier_info_1")

    def _create_order(self, user=None, amount=1, tax=10):
        return self.env["portal.order"].with_user(user or self.alice).create({
            "product_id": self.product.id,
            "supplierinfo_id": self.supplierinfo.id,
            "amount": amount,
            "tax": tax,
        }).with_env(self.env)


@tagged("post_install", "-at_install")
class TestPortalOrder(PortalOrderCommon):

    def test_prices(self):
        order = self._create_order(amount=2)
        self.assertEqual(order.gross_price, 20)
        self.assertAlmostEqual(order.taxed_price, 22)

    def test_prices_multi_record(self):
        orders = self._create_order(amount=1) | self._create_order(amount=2)
        self.assertEqual(orders.mapped("gross_price"), [10, 20])

    def test_invalid_amount(self):
        with self.assertRaises(ValidationError):
            self._create_order(amount=4)
        order = self._create_order()
        with self.assertRaises(ValidationError):
            order.amount = 0

    def test_sequence_and_notification(self):
        order = self._create_order()
        self.assertTrue(order.name.startswith("PPO"))
        created = order.message_ids[:1]
        self.assertIn("Please check the order", created.body)
        self.assertEqual(created.partner_ids, self.john.partner_id, "managers are notified, not the requester")
        order.with_user(self.john).action_approve()
        self.assertEqual(order.message_ids[:1].partner_ids, self.alice.partner_id)

    def test_record_rules(self):
        order = self._create_order(user=self.alice)
        self.assertFalse(self.env["portal.order"].with_user(self.bob).search([("id", "=", order.id)]))
        self.assertTrue(self.env["portal.order"].with_user(self.john).search([("id", "=", order.id)]))
        with self.assertRaises(AccessError):
            order.with_user(self.bob).action_buy()

    def test_full_flow(self):
        order = self._create_order()
        with self.assertRaises(AccessError):
            order.with_user(self.alice).action_approve()
        order.with_user(self.john).action_approve()
        self.assertEqual(order.state, "approved")
        with self.assertRaises(UserError):
            order.with_user(self.john).action_reject()

        order.with_user(self.alice).action_buy()
        self.assertEqual(order.state, "in_progress")
        purchase = order.purchase_order_id
        self.assertEqual(purchase.partner_id, self.supplierinfo.partner_id)
        self.assertEqual(purchase.order_line.product_qty, 1)
        self.assertEqual(purchase.order_line.tax_ids, self.env.ref("portal_orders.global_purchase_tax"))

        with self.assertRaises(UserError):
            order.with_user(self.ingrid).action_done()
        wizard = self.env["portal.order.picking.date.wizard"].with_user(self.ingrid).with_context(
            active_id=order.id,
        ).create({"picking_date": "2026-12-01"})
        wizard.action_set_picking_date()
        self.assertEqual(order.state, "ready_to_pick")
        self.assertIn("is ready", order.message_ids[:1].body)

        order.with_user(self.ingrid).action_done()
        self.assertEqual(order.state, "done")

    def test_global_tax_created_on_demand(self):
        # like a fresh database: no tax yet, and a company with neither a
        # country nor a tax group (no chart of accounts)
        self.env.ref("portal_orders.global_purchase_tax").unlink()
        company = self.env["res.company"].create({"name": "Fresh Company"})
        PortalOrder = self.env["portal.order"].with_company(company)
        with self.assertRaises(UserError):
            PortalOrder._get_global_purchase_tax()

        company.country_id = self.env.ref("base.be")
        tax = PortalOrder._get_global_purchase_tax()
        self.assertEqual((tax.amount, tax.type_tax_use, tax.company_id), (66, "purchase", company))
        self.assertEqual(tax.tax_group_id.company_id, company)
        self.assertEqual(self.env.ref("portal_orders.global_purchase_tax"), tax)
        self.assertEqual(PortalOrder._get_global_purchase_tax(), tax, "created only once")

    def test_done_requires_picking_date(self):
        order = self._create_order()
        order.state = "ready_to_pick"
        with self.assertRaises(ValidationError):
            order.action_done()


@tagged("post_install", "-at_install")
class TestPortalOrderRoutes(HttpCase, PortalOrderCommon):

    def _signature(self):
        with file_open("portal_orders/demo/attach_1.pdf", "rb") as f:
            return "data:application/pdf;base64," + base64.b64encode(f.read()).decode()

    def test_employee_routes(self):
        self.authenticate("alice@example.com", "alice")
        products = self.make_jsonrpc_request("/my/portal_orders/products")
        self.assertIn(self.product.id, [p["id"] for p in products])
        self.assertNotIn(
            self.env.ref("portal_orders.product_template_product_2").product_variant_ids[:1].id,
            [p["id"] for p in products],
            "Alice may only see products of her allowed categories",
        )
        suppliers = self.make_jsonrpc_request(
            "/my/portal_orders/product_suppliers", {"product_id": self.product.id},
        )
        self.assertEqual(len(suppliers), 2)
        self.assertEqual(
            self.make_jsonrpc_request("/my/portal_orders/tax_rate"),
            {"tax_rate": 20, "is_user_rate": True, "max_amount": 2},
        )

        result = self.make_jsonrpc_request("/my/portal_orders/save", {
            "product_id": self.product.id,
            "supplierinfo_id": self.supplierinfo.id,
            "amount": 2,
            "file": self._signature(),
        })
        order = self.env["portal.order"].browse(result["id"])
        self.assertEqual(order.user_id, self.alice)
        self.assertEqual(order.tax, 20)
        self.assertEqual(order.attachment_ids.mimetype, "application/pdf")
        self.assertEqual(order.with_user(self.alice).attachments_count, 1)
        self.assertEqual(order.with_user(self.john).attachments_count, 1)

        list_page = self.url_open("/my/portal_orders").text
        self.assertEqual(list_page.count("o_portal_submenu"), 1, "breadcrumb rendered once")

        response = self.url_open(f"/my/portal_orders/{order.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(order.name, response.text)
        self.assertNotIn("Purchase Orders", response.text, "no purchase breadcrumb on a portal order")
        response = self.url_open(f"/my/portal_orders/{order.id}/attachment/{order.attachment_ids.id}")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertEqual(self.url_open("/my/portal_orders").status_code, 200)
        self.assertEqual(self.url_open("/my/home").status_code, 200)

    def test_employee_limits(self):
        self.authenticate("alice@example.com", "alice")
        with mute_logger("odoo.http"), self.assertRaises(Exception, msg="above Alice's limit of 2"):
            self.make_jsonrpc_request("/my/portal_orders/save", {
                "product_id": self.product.id,
                "supplierinfo_id": self.supplierinfo.id,
                "amount": 3,
                "file": self._signature(),
            })
        other_product = self.env.ref("portal_orders.product_template_product_2").product_variant_ids[:1]
        with mute_logger("odoo.http"), self.assertRaises(Exception, msg="product outside her categories"):
            self.make_jsonrpc_request("/my/portal_orders/save", {
                "product_id": other_product.id,
                "supplierinfo_id": self.env.ref("portal_orders.supplier_info_3").id,
                "amount": 1,
                "file": self._signature(),
            })

    def test_portal_card_visible_without_orders(self):
        entry = self.env.ref("portal_orders.portal_entry_portal_orders")
        self.assertFalse(self.env["portal.order"].with_user(self.bob).search_count([]))
        self.assertIn(entry, entry.with_user(self.bob)._filter_visible_portal_cards(), "employee")
        self.assertIn(entry, entry.with_user(self.john)._filter_visible_portal_cards(), "manager")
        customer = self.env["res.users"].create({
            "name": "Customer", "login": "customer", "group_ids": [Command.set(self.env.ref("base.group_portal").ids)],
        })
        self.assertNotIn(entry, entry.with_user(customer)._filter_visible_portal_cards(), "other portal user")

    def test_other_employee_order_hidden(self):
        order = self._create_order(user=self.alice)
        self.authenticate("bob@example.com", "bob")
        response = self.url_open(f"/my/portal_orders/{order.id}", allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        response = self.url_open(f"/my/portal_orders/{order.id}/attachment/1")
        self.assertEqual(response.status_code, 404)

    def test_tours(self):
        # start_tour logs in with the login as password
        for user in (self.alice, self.john):
            user.password = user.login
        self.start_tour("/my/portal_orders", "portal_orders_employee_new_order", login=self.alice.login)
        order = self.env["portal.order"].search([("user_id", "=", self.alice.id)], limit=1)
        self.assertEqual((order.amount, order.tax, order.state), (2, 20, "draft"))
        self.assertEqual(order.attachment_ids.mimetype, "application/pdf")

        self.start_tour(f"/my/portal_orders/{order.id}", "portal_orders_manager_approve", login=self.john.login)
        self.assertEqual(order.state, "approved")

    def test_manager_routes(self):
        order = self._create_order(user=self.alice)
        self.authenticate("john@example.com", "john")
        response = self.url_open(f"/my/portal_orders/{order.id}")
        self.assertIn("Approve", response.text)
        self.make_jsonrpc_request(f"/my/portal_orders/{order.id}/approve")
        self.assertEqual(order.state, "approved")
