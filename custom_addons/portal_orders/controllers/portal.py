from odoo import http
import base64
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.osv.expression import OR


class CustomerPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if "portal_orders_count" in counters:
            values["portal_orders_count"] = request.env["portal.order"].search_count([
            ])

        return values

    @http.route("/my/portal_orders", type="http", auth="user", website=True)
    def portal_my_orders(self, search=None, search_in="name", **kw):
        values = self._prepare_portal_layout_values()
        print("**", search_in)
        print("**", search)

        isManager = request.env.user.has_group(
            "portal_orders.group_portal_manager")

        searchbar_inputs = {
            "name": {
                "input": "name",
                "label": "Search by Order Number",
            },
            "date_created": {
                "input": "date_created",
                "label": "Search by Creation Date",
            },
            "state": {"input": "state", "label": "Search by States"},
        }

        PortalOrder = request.env["portal.order"]
        domain = []

        if search and search_in:
            search_domain = []
            if search_in in ("name"):
                search_domain = OR(
                    [search_domain, [("name", "ilike", search)]])
            if search_in in ("state"):
                search_domain = OR(
                    [search_domain, [("state", "ilike", search)]])
            domain += search_domain

        if not isManager:
            orders = PortalOrder.search(domain)
        else:
            orders = PortalOrder.sudo().search(domain)

        values = {
            "page_name": "portal_orders",
            "default_url": "/my/portal_orders",
            "orders": orders,
            "searchbar_inputs": searchbar_inputs,
            "search_in": search_in,
            "search": search,
            "isManager": isManager,
        }

        return request.render("portal_orders.portal_my_orders", values)

    @http.route(
        "/my/portal_orders/<int:order_id>", type="http", auth="user", website=True
    )
    def portal_my_order(self, order_id=None, access_token=None, **kw):
        isManager = request.env.user.has_group(
            "portal_orders.group_portal_manager")
        order = request.env["portal.order"].sudo().browse(order_id)

        values = {"page_name": "portal_orders",
                  "order": order, "isManager": isManager}
        return request.render("portal_orders.portal_my_order", values)

    @http.route(
        "/my/portal_orders/product_suppliers", type="json", auth="user", website=True
    )
    def get_product_suppliers(self, product_id):
        suppliers = []
        product = request.env["product.product"].browse(int(product_id))

        for seller in product.seller_ids:
            suppliers.append(
                {
                    "id": seller.id,
                    "name": seller.display_name,
                    "price": seller.price,
                    "currency": seller.currency_id.symbol,
                }
            )

        return suppliers

    @http.route("/my/portal_orders/check", type="json", aut="user", website=True)
    def check_amount(self, **kw):
        amount = kw["amount"]
        user_id = kw["user_id"]

        if user_id and amount:
            user = request.env["res.users"].browse(user_id)
            if user:
                return {"valid": True, "amount": user.partner_id.portal_order_limit}

        return {"valid": False}

    @http.route("/my/portal_orders/tax_rate", type="json", auth="user", website=True)
    def get_tax_param(self):
        global_tax_rate = request.env.ref(
            "portal_orders.global_purchase_tax").amount

        user_tax_rate = request.env.user.partner_id.portal_orders_tax_rate

        return {"global_tax_rate": global_tax_rate, "user_tax_rate": user_tax_rate}

    @http.route("/my/portal_orders/save", type="json", auth="user", website=True)
    def portal_my_order_save(self, **post):
        productId = int(post["product_id"])
        supplierInfoId = int(post["supplierinfo_id"])
        amount = int(post["amount"])

        tax = request.env.user.partner_id.portal_orders_tax_rate

        if not tax:
            tax = request.env.ref("portal_orders.global_purchase_tax").amount

        order = (
            request.env["portal.order"]
            .sudo()
            .create(
                {
                    "name": "New",
                    "product_id": productId,
                    "amount": amount,
                    "tax": tax,
                    "supplierinfo_id": supplierInfoId,
                }
            )
        )

        pdf = post["file"].lstrip("data:application/pdf;base64,")

        new_attachment = (
            request.env["ir.attachment.custom"]
            .sudo()
            .create(
                {
                    "name": "Employee_Signature.pdf",
                    "type": "binary",
                    "datas": pdf,
                    "mimetype": "application/x-pdf",
                    "public": False,
                }
            )
        )

        order.sudo().attachment_ids = [(4, new_attachment.id)]

        return order

    @http.route("/my/portal_orders/approve", type="json", auth="user", website=True)
    def approve_order(self, **kw):
        orderId = int(kw["order_id"])
        order = request.env["portal.order"].browse(orderId)
        order.write({"state": "approved"})

        template_id = request.env.ref(
            "portal_orders.email_template_portal_order_approved"
        )
        order.message_post_with_template(template_id.id)

    @http.route("/my/portal_orders/reject", type="json", auth="user", website=True)
    def reject_order(self, **kw):
        orderId = int(kw["order_id"])
        order = request.env["portal.order"].browse(orderId)
        order.write({"state": "rejected"})

        template_id = request.env.ref(
            "portal_orders.email_template_portal_order_rejected"
        )
        order.message_post_with_template(template_id.id)

    @http.route("/my/portal_orders/buy", type="json", auth="user", website=True)
    def buy_order(self, **kw):
        orderId = int(kw["order_id"])
        order = request.env["portal.order"].browse(orderId)
        order.write({"state": "in_progress"})

        PurchaseOrder = request.env["purchase.order"]
        PurchaseOrderLine = request.env["purchase.order.line"]

        tax = request.env.ref("portal_orders.global_purchase_tax")

        po = PurchaseOrder.sudo().create(
            {
                "partner_id": order.supplierinfo_id.name.id,
            }
        )

        PurchaseOrderLine.sudo().create(
            {
                "name": order.name,
                "product_id": order.product_id.id,
                "product_qty": order.amount,
                "price_unit": order.supplierinfo_id.price,
                "order_id": po.id,
                "taxes_id": [tax.id],
            }
        )
