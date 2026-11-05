{
    "name": "Portal Orders",
    "version": "20.0.1.0.0",
    "category": "Services",
    "summary": "Employees place purchase requests from the portal",
    "description": """
Employees place purchase requests from the portal and a portal manager
approves or rejects them. Internal users then follow the resulting purchase
orders, set a pick-up date and close them.
""",
    "depends": ["portal", "purchase", "contacts"],
    "data": [
        "security/portal_orders_security.xml",
        "security/ir.access.csv",
        "data/order_data.xml",
        "data/order_mail_template.xml",
        "data/portal_entry_data.xml",
        "wizard/set_picking_date_wizard_views.xml",
        "views/order_views.xml",
        "views/order_templates.xml",
        "views/res_partner_views.xml",
    ],
    "demo": [
        "demo/order_demo.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "portal_orders/static/src/interactions/**/*",
        ],
        "web.assets_tests": [
            "portal_orders/static/tests/tours/**/*",
        ],
    },
    "post_init_hook": "_post_init_hook",
    "author": "Farid Shahy",
    "application": True,
    "license": "LGPL-3",
}
