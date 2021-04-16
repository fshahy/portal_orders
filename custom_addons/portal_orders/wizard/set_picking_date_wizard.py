# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class SePickingDate(models.TransientModel):
    _name = "portal.order.picking.date.wizard"
    _description = "Set Picking Date Wizard"

    def _default_order(self):
        return self.env["portal.order"].browse(self._context.get("active_id"))

    picking_date = fields.Date(string="Picking Date", required=True)

    order_id = fields.Many2one(
        "portal.order",
        string="Portal Order",
        required=True,
        default=_default_order,
    )

    def set_picking_date(self):
        if self.order_id.state == "in_progress":
            self.order_id.picking_date = self.picking_date
            self.order_id.state = "ready_to_pick"

            template_id = self.env.ref(
                "portal_orders.email_template_portal_order_ready"
            )
            self.order_id.message_post_with_template(template_id.id)

            return {}
        else:
            raise UserError(_("Order already has a picking date."))
