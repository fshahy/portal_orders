# -*- coding: utf-8 -*-
{
    "name": "Portal Orders",
    "version": "1.0",
    "category": "Portal order access",
    "summary": "employees can place purchase orders from portal.",
    "description": "using the portal employees can place purchase orders and the manager can approve or reject the orders.",
    "depends": ["portal", "purchase", "contacts"],
    "data": [
        "data/order_data.xml",
        "data/order_mail_template.xml",
        "security/groups.xml",
        "security/ir.model.access.csv",
        "order_security.xml",
        "views/order_views.xml",
        "views/order_templates.xml",
        "views/res_partner_views.xml",
        "wizard/set_picking_date_wizard.xml",
    ],
    "demo": [
        "demo/order_demo.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}
