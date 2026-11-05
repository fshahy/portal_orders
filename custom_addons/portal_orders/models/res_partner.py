from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    portal_order_limit = fields.Selection(
        [("1", "1"), ("2", "2"), ("3", "3")],
        string="Portal Order Limit",
        default="1",
        help="Number of products a portal user can request",
    )
    allowed_product_category_ids = fields.Many2many(
        "product.category",
        relation="product_category_partner_rel",
        string="Allowed Product Categories",
    )
    portal_orders_tax_rate = fields.Integer(
        string="Portal Orders Tax Rate (%)",
        default=0,
        help="Tax rate applied to this user's portal orders instead of the global one",
    )
