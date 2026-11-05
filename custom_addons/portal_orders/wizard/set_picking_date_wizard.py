from odoo import fields, models


class PortalOrderPickingDateWizard(models.TransientModel):
    _name = "portal.order.picking.date.wizard"
    _description = "Set Picking Date Wizard"

    def _default_order_id(self):
        return self.env["portal.order"].browse(self.env.context.get("active_id"))

    picking_date = fields.Date(string="Picking Date", required=True)
    order_id = fields.Many2one(
        "portal.order",
        string="Portal Order",
        required=True,
        default=_default_order_id,
    )

    def action_set_picking_date(self):
        self.ensure_one()
        self.order_id._set_picking_date(self.picking_date)
