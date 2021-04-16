# -*- coding: utf-8 -*-
from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    portal_order_limit = fields.Selection(
        [("1", 1), ("2", 2), ("3", 3)],
        help="number of products a portal user can request",
        default="1",
    )
    allowed_product_category_ids = fields.Many2many(
        string="Allowed Product Categories",
        comodel_name="product.category",
        relation="product_category_partner_rel",
    )
    portal_orders_tax_rate = fields.Integer(
        string="Portal Orders Tax Rate (%)",
        default=0,
        help="specialized tax rate for portal orders",
    )

    def get_portal_allowed_products(self, user_id):
        # self is not loaded
        user = self.env["res.users"].browse(user_id)

        categ_ids = [categ.id for categ in user.allowed_product_category_ids]
        products = self.env["product.product"].search_read(
            [("categ_id", "in", categ_ids)]
        )

        return products
