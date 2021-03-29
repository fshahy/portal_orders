from collections import defaultdict
from odoo import models, api, fields, _
from odoo.exceptions import AccessError


class CustomAttachment(models.Model):
    _name = "ir.attachment.custom"
    _description = "customized attachment"
    _inherits = {"ir.attachment": "attachment_id"}

    attachment_id = fields.Many2one(
        "ir.attachment",
        "Attachment",
        required=True,
        ondelete="cascade",
        index=True,
        auto_join=True,
    )

    @api.model
    def check(self, mode, values=None):
        if self.env.user.has_group("base.group_user"):
            return True
        else:
            return super(CustomAttachment, self).check(mode, values)