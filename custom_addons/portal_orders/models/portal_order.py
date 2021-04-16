# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PortalOrder(models.Model):
    _name = "portal.order"
    _description = "Portal Order"
    _order = "name desc"
    _inherit = [
        "mail.thread",
    ]

    name = fields.Char(string="Order Number", required=True, index=True, default="New")

    product_id = fields.Many2one("product.product", string="Product", required=True)

    amount = fields.Integer(string="Amount", required=True)
    tax = fields.Integer(string="Tax", required=True)

    supplierinfo_id = fields.Many2one("product.supplierinfo", "Supplier Info")

    gross_price = fields.Float(
        digits=(6, 2), string="Gross Price", compute="_calc_gross_price"
    )
    taxed_price = fields.Float(
        digits=(6, 2), string="Taxed Price", compute="_calc_taxed_price"
    )

    user_id = fields.Many2one(
        "res.users",
        string="Requested By",
        readonly=True,
        index=True,
        default=lambda self: self.env.user,
    )
    date_created = fields.Datetime(
        string="Creation Date",
        required=True,
        readonly=True,
        index=True,
        states={"draft": [("readonly", False)]},
        copy=False,
        default=fields.Datetime.now,
    )

    picking_date = fields.Date(string="Picking Date")

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        readonly=True,
        default=lambda self: self.env.company,
    )

    attachment_ids = fields.Many2many("ir.attachment", string="Attachments")

    attachments_count = fields.Integer(
        string="Number of Attachments", compute="_get_attachments_count"
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("in_progress", "Purchase in progress"),
            ("ready_to_pick", "Ready to pick-up"),
            ("done", "Done"),
        ],
        string="State",
        readonly=True,
        index=True,
        copy=False,
        default="draft",
        tracking=True,
    )

    @api.model
    def create(self, vals):
        if vals.get("name", "New") == "New":
            vals["name"] = self.env["ir.sequence"].next_by_code("portal.order") or "/"

        template_id = self.env.ref("portal_orders.email_template_portal_order_created")

        order = super(PortalOrder, self).create(vals)
        order.message_post_with_template(template_id.id)

        return order

    @api.depends("name")
    def name_get(self):
        result = []
        for ppo in self:
            result.append((ppo.id, ppo.name))

        return result

    def _check_amount(self):
        if self.amount < 1 or self.amount > 3:
            return False
        else:
            return True

    @api.depends("gross_price")
    def _calc_gross_price(self):
        if self._check_amount():
            self.gross_price = self.amount * self.supplierinfo_id.price
        else:
            raise ValidationError("invalid amount")

    @api.depends("gross_price", "taxed_price")
    def _calc_taxed_price(self):
        self.taxed_price = self.gross_price * (1 + (self.tax / 100))

    def _get_attachments_count(self):
        for record in self:
            record.attachments_count = len(record.attachment_ids)

    def set_done(self):
        if not self.picking_date:
            raise ValidationError("must set a picking date before finishing order")
        else:
            self.state = "done"
