from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

# Highest quantity any employee may request; the per-partner
# `portal_order_limit` can only lower it.
MAX_PORTAL_ORDER_AMOUNT = 3

GLOBAL_PURCHASE_TAX_XMLID = "portal_orders.global_purchase_tax"
GLOBAL_PURCHASE_TAX_RATE = 66


class PortalOrder(models.Model):
    _name = "portal.order"
    _description = "Portal Order"
    _inherit = ["mail.thread"]
    _order = "name desc"

    name = fields.Char(string="Order Number", required=True, index=True, default="New", copy=False)
    product_id = fields.Many2one("product.product", string="Product", required=True)
    amount = fields.Integer(string="Amount", required=True)
    tax = fields.Integer(string="Tax", required=True)
    supplierinfo_id = fields.Many2one("product.supplierinfo", string="Supplier Info")
    gross_price = fields.Float(string="Gross Price", digits=(6, 2), compute="_compute_gross_price")
    taxed_price = fields.Float(string="Taxed Price", digits=(6, 2), compute="_compute_taxed_price")
    user_id = fields.Many2one(
        "res.users",
        string="Requested By",
        readonly=True,
        index=True,
        default=lambda self: self.env.user,
    )
    # sudo-computed related: lets a portal manager display the requester's
    # contact details without being granted read access on res.users
    partner_id = fields.Many2one(related="user_id.partner_id", string="Requester")
    date_created = fields.Datetime(
        string="Creation Date",
        required=True,
        readonly=True,
        index=True,
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
    attachments_count = fields.Integer(string="Number of Attachments", compute="_compute_attachments_count")
    purchase_order_id = fields.Many2one("purchase.order", string="Purchase Order", readonly=True, copy=False)
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
        copy=False,
        default="draft",
        tracking=True,
    )

    @api.depends("amount", "supplierinfo_id.price")
    def _compute_gross_price(self):
        for order in self:
            order.gross_price = order.amount * order.supplierinfo_id.price

    @api.depends("gross_price", "tax")
    def _compute_taxed_price(self):
        for order in self:
            order.taxed_price = order.gross_price * (1 + order.tax / 100)

    @api.depends("attachment_ids")
    def _compute_attachments_count(self):
        # portal users have no access to ir.attachment, which would make the
        # count 0; counting the order's own attachments discloses nothing
        for order in self:
            order.attachments_count = len(order.sudo().attachment_ids)

    @api.constrains("amount")
    def _check_amount(self):
        for order in self:
            if not 1 <= order.amount <= MAX_PORTAL_ORDER_AMOUNT:
                raise ValidationError(self.env._(
                    "The amount must be between 1 and %(max)s.", max=MAX_PORTAL_ORDER_AMOUNT,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                # portal users have no read access on ir.sequence
                vals["name"] = self.env["ir.sequence"].sudo().next_by_code("portal.order") or "/"
        orders = super().create(vals_list)
        orders._post_template("portal_orders.email_template_portal_order_created")
        return orders

    def action_approve(self):
        self._check_portal_manager()
        self._set_state_from("draft", "approved", "portal_orders.email_template_portal_order_approved")

    def action_reject(self):
        self._check_portal_manager()
        self._set_state_from("draft", "rejected", "portal_orders.email_template_portal_order_rejected")

    def action_buy(self):
        self._set_state_from("approved", "in_progress")
        # employees may not create purchase orders themselves; the values
        # below come from the approved order only, never from the request
        for order in self.sudo():
            order.purchase_order_id = order.env["purchase.order"].create({
                "partner_id": order.supplierinfo_id.partner_id.id,
                "order_line": [fields.Command.create({
                    "name": order.name,
                    "product_id": order.product_id.id,
                    "product_qty": order.amount,
                    "price_unit": order.supplierinfo_id.price,
                    "tax_ids": [fields.Command.set(order._get_global_purchase_tax().ids)],
                })],
            })

    def action_done(self):
        for order in self:
            if order.state != "ready_to_pick":
                raise UserError(self.env._("Order %s is not ready to be picked up.", order.name))
            if not order.picking_date:
                raise ValidationError(self.env._("Set a picking date before finishing order %s.", order.name))
        self.state = "done"

    def _set_picking_date(self, picking_date):
        self.picking_date = picking_date
        self._set_state_from("in_progress", "ready_to_pick", "portal_orders.email_template_portal_order_ready")

    @api.model
    def _get_global_purchase_tax(self):
        """ Return the Global Purchase Tax, creating it on first use.

        It is not shipped as XML data: an account.tax requires a country,
        taken from the company, and a fresh database may not have one yet.
        """
        tax = self.env.ref(GLOBAL_PURCHASE_TAX_XMLID, raise_if_not_found=False)
        if tax:
            return tax
        # portal users have no access to account.tax creation nor ir.model.data
        company = self.env.company.sudo()
        if not (company.account_fiscal_country_id or company.country_id):
            raise UserError(self.env._(
                "The Global Purchase Tax cannot be created: set a country on company %s first.",
                company.name,
            ))
        country = company.account_fiscal_country_id or company.country_id
        TaxGroup = self.env["account.tax.group"].sudo()
        # without a chart of accounts no tax group exists, and a tax needs one
        tax_group = TaxGroup.search([
            *TaxGroup._check_company_domain(company),
            ("country_id", "in", (country.id, False)),
        ], limit=1) or TaxGroup.create({
            "name": "Portal Orders",
            "company_id": company.id,
            "country_id": country.id,
        })
        tax = self.env["account.tax"].sudo().create({
            "tax_group_id": tax_group.id,
            "country_id": country.id,
            "name": "Global Purchase Tax",
            "amount_type": "percent",
            "type_tax_use": "purchase",
            "amount": GLOBAL_PURCHASE_TAX_RATE,
            "company_id": company.id,
        })
        self.env["ir.model.data"].sudo()._update_xmlids([{
            "xml_id": GLOBAL_PURCHASE_TAX_XMLID,
            "record": tax,
            "noupdate": True,
        }])
        return tax.with_env(self.env)

    def _check_portal_manager(self):
        if not self.env.user.has_group("portal_orders.group_portal_manager"):
            raise AccessError(self.env._("Only portal order managers can approve or reject orders."))

    def _set_state_from(self, from_state, to_state, template_xmlid=None):
        wrong_state = self.filtered(lambda order: order.state != from_state)
        if wrong_state:
            raise UserError(self.env._(
                "Orders %(names)s are not in state %(state)s.",
                names=wrong_state.mapped("name"),
                state=dict(self._fields["state"]._description_selection(self.env))[from_state],
            ))
        self.state = to_state
        if template_xmlid:
            self._post_template(template_xmlid)

    def _post_template(self, template_xmlid):
        # portal users have no access to mail.template nor the composer; the
        # template is a fixed data record, so rendering it as superuser is safe
        for order in self.sudo():
            order.message_post_with_source(template_xmlid)
