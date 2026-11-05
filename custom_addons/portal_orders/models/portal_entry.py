from odoo import models


class PortalEntry(models.Model):
    _inherit = "portal.entry"

    def _filter_visible_portal_cards(self):
        # cards are hidden until their counter is > 0; an employee without
        # any order yet still needs the card to create the first one
        visible_entries = super()._filter_visible_portal_cards()
        entry = self.env.ref("portal_orders.portal_entry_portal_orders", raise_if_not_found=False)
        user = self.env.user
        if entry and entry in self and (
            user.has_group("portal_orders.group_portal_employee")
            or user.has_group("portal_orders.group_portal_manager")
        ):
            visible_entries |= entry
        return visible_entries
