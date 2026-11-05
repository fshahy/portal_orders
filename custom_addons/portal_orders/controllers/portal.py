import base64
import binascii

from odoo import Command
from odoo.exceptions import UserError
from odoo.http import request, route

from odoo.addons.portal.controllers.portal import CustomerPortal

MAX_SIGNATURE_SIZE = 5 * 1024 * 1024


class PortalOrders(CustomerPortal):

    def _prepare_portal_counter_values(self, counter):
        if counter == "portal_orders_count":
            return "portal.order", [], "read"
        return super()._prepare_portal_counter_values(counter)

    def _get_portal_order_tax_rate(self):
        user_tax_rate = request.env.user.partner_id.portal_orders_tax_rate
        return user_tax_rate or request.env["portal.order"]._get_global_purchase_tax().amount

    def _get_allowed_portal_order_products(self):
        categories = request.env.user.partner_id.allowed_product_category_ids
        return request.env["product.product"].search([
            ("categ_id", "in", categories.ids),
            ("purchase_ok", "=", True),
        ])

    @route("/my/portal_orders", type="http", auth="user", website=True)
    def portal_my_orders(self, search=None, search_in="name", **kw):
        is_manager = request.env.user.has_group("portal_orders.group_portal_manager")
        searchbar_inputs = {
            "name": {"input": "name", "label": request.env._("Search by Order Number")},
            "state": {"input": "state", "label": request.env._("Search by State")},
        }
        domain = []
        if search and search_in in searchbar_inputs:
            domain = [(search_in, "ilike", search)]

        values = self._prepare_portal_layout_values()
        values.update({
            "page_name": "portal_orders",
            "default_url": "/my/portal_orders",
            "orders": request.env["portal.order"].search(domain),
            "searchbar_inputs": searchbar_inputs,
            "search_in": search_in,
            "search": search,
            "is_manager": is_manager,
        })
        return request.render("portal_orders.portal_my_orders", values)

    @route("/my/portal_orders/<int:order_id>", type="http", auth="user", website=True)
    def portal_my_order(self, order_id, **kw):
        order = request.env["portal.order"].browse(order_id).exists()
        if not order or not order.has_access("read"):
            return request.redirect("/my/portal_orders")
        values = self._prepare_portal_layout_values()
        values.update({
            "page_name": "portal_orders",
            # not "order": purchase's breadcrumbs react to that variable
            "portal_order": order,
            "is_manager": request.env.user.has_group("portal_orders.group_portal_manager"),
        })
        return request.render("portal_orders.portal_my_order", values)

    @route("/my/portal_orders/<int:order_id>/attachment/<int:attachment_id>", type="http", auth="user", website=True)
    def portal_order_attachment(self, order_id, attachment_id, **kw):
        order = request.env["portal.order"].browse(order_id).exists()
        if not order or not order.has_access("read"):
            raise request.not_found()
        # portal users have no access to ir.attachment; serve only the
        # attachments of an order the user is allowed to read
        attachment = order.sudo().attachment_ids.filtered(lambda a: a.id == attachment_id)
        if not attachment:
            raise request.not_found()
        return request.env["ir.binary"]._get_stream_from(attachment).get_response()

    @route("/my/portal_orders/products", type="jsonrpc", auth="user", website=True, readonly=True)
    def portal_order_products(self):
        return [
            {"id": product.id, "name": product.display_name}
            for product in self._get_allowed_portal_order_products()
        ]

    @route("/my/portal_orders/product_suppliers", type="jsonrpc", auth="user", website=True, readonly=True)
    def portal_order_product_suppliers(self, product_id):
        product = self._get_allowed_portal_order_products().filtered(lambda p: p.id == int(product_id))
        return [
            {
                "id": seller.id,
                "name": seller.partner_id.display_name,
                "price": seller.price,
                "currency": seller.currency_id.symbol,
            }
            for seller in product.seller_ids
        ]

    @route("/my/portal_orders/tax_rate", type="jsonrpc", auth="user", website=True, readonly=True)
    def portal_order_tax_rate(self):
        return {
            "tax_rate": self._get_portal_order_tax_rate(),
            "is_user_rate": bool(request.env.user.partner_id.portal_orders_tax_rate),
            "max_amount": int(request.env.user.partner_id.portal_order_limit or 0),
        }

    @route("/my/portal_orders/save", type="jsonrpc", auth="user", website=True)
    def portal_order_save(self, product_id, supplierinfo_id, amount, file):
        product = self._get_allowed_portal_order_products().filtered(lambda p: p.id == int(product_id))
        seller = product.seller_ids.filtered(lambda s: s.id == int(supplierinfo_id))
        if not product or not seller:
            raise UserError(request.env._("Select one of the products and vendors offered to you."))
        amount = int(amount)
        max_amount = int(request.env.user.partner_id.portal_order_limit or 0)
        if amount > max_amount:
            raise UserError(request.env._("You may request at most %s items.", max_amount))
        try:
            pdf = base64.b64decode(file.partition(",")[2] or file, validate=True)
        except (binascii.Error, ValueError):
            raise UserError(request.env._("The signed request must be a PDF file."))
        if len(pdf) > MAX_SIGNATURE_SIZE or not pdf.startswith(b"%PDF"):
            raise UserError(request.env._("The signed request must be a PDF file of at most 5MB."))

        order = request.env["portal.order"].create({
            "product_id": product.id,
            "amount": amount,
            "tax": self._get_portal_order_tax_rate(),
            "supplierinfo_id": seller.id,
        })
        # portal users cannot create attachments; the values are fixed here
        # and the attachment is bound to the order the user just created
        attachment = request.env["ir.attachment"].sudo().create({
            "name": f"Employee_Signature_{order.id}.pdf",
            "raw": pdf,
            "mimetype": "application/pdf",
            "res_model": order._name,
            "res_id": order.id,
        })
        order.sudo().attachment_ids = [Command.link(attachment.id)]
        return {"id": order.id}

    @route("/my/portal_orders/<int:order_id>/approve", type="jsonrpc", auth="user", website=True)
    def portal_order_approve(self, order_id):
        request.env["portal.order"].browse(order_id).action_approve()

    @route("/my/portal_orders/<int:order_id>/reject", type="jsonrpc", auth="user", website=True)
    def portal_order_reject(self, order_id):
        request.env["portal.order"].browse(order_id).action_reject()

    @route("/my/portal_orders/<int:order_id>/buy", type="jsonrpc", auth="user", website=True)
    def portal_order_buy(self, order_id):
        request.env["portal.order"].browse(order_id).action_buy()
