# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A single **Odoo 20.0** addon, `custom_addons/portal_orders`, that lets employees place purchase requests from the website portal. A portal manager approves or rejects them. Backend (internal) users then follow the generated `purchase.order`s, set a pick-up date and close them. See README.md for the business rules and the demo logins (alice/bob = employees, john = manager, ingrid = internal user; password = first name).

Branches: `14.0` holds the original Odoo 14 module and `20.0` the port. `enterprise/` holds **Odoo 14** Enterprise addons. Git does not track it, it cannot load on Odoo 20, and it is not mounted. Never edit it. `skills/` holds Odoo's agent skills (odoo-guidelines, odoo-web-guidelines, odoo-security, odoo-review, odoo-git). Read the matching ones before writing or reviewing code.

## Running

Everything runs through docker-compose (Odoo 20 + Postgres 16 + pgAdmin on :8888):

```bash
docker-compose up -d                      # Odoo at http://localhost:8069, master password "admin"
docker-compose restart web                # pick up Python changes
```

`config/odoo.conf` is mounted at `/etc/odoo`. Addons path is `/mnt/custom_addons`. DB credentials are odoo/odoo, host `db`. Odoo 20 requires PostgreSQL >= 16.

Install or upgrade, and run the tests (the tests `env.ref` the demo records, so the database needs demo data):

```bash
docker-compose exec web odoo -c /etc/odoo/odoo.conf -d <db> -u portal_orders --stop-after-init --no-http
docker-compose exec web odoo -c /etc/odoo/odoo.conf -d <db> -u portal_orders --test-enable --test-tags /portal_orders --stop-after-init --no-http
# single test:
docker-compose exec web odoo -c /etc/odoo/odoo.conf -d <db> --test-tags /portal_orders:TestPortalOrder.test_full_flow --stop-after-init --no-http
```

`TestPortalOrderRoutes.test_tours` runs browser tours. It needs Chrome and the `websocket-client` Python package in the Odoo container, which the stock `odoo:20.0` image lacks, so without them it is skipped.

## Architecture

**Order lifecycle** (`portal.order.state`): `draft` → `approved` | `rejected` → `in_progress` → `ready_to_pick` → `done`. The model owns every transition: `action_approve`/`action_reject` (portal manager only), `action_buy` (creates the `purchase.order` with the `global_purchase_tax`, as sudo), `_set_picking_date` (called by the wizard) and `action_done`. `_set_state_from` validates the source state and posts the matching `mail.template` from `data/order_mail_template.xml` via `message_post_with_source`, as sudo.

**Controllers** (`controllers/portal.py`): `/my/portal_orders` (list) and `/my/portal_orders/<id>` (detail) are http routes. `products`, `product_suppliers`, `tax_rate`, `save` and `<id>/approve|reject|buy` are `jsonrpc` routes. `save` validates product, vendor, quantity limit and PDF on the server, then stores the signature as an `ir.attachment` via sudo. `<id>/attachment/<att_id>` streams an order's attachment after checking order access. The portal home card is a `portal.entry` record (`data/portal_entry_data.xml`). Its counter is `_prepare_portal_counter_values`.

**Frontend**: the QWeb pages are in `views/order_templates.xml` (Bootstrap 5). The JS is made of Odoo 20 `Interaction`s in `static/src/interactions/`: `new_order_form.js` (the new-order modal: computes prices on the client, 5MB limit) and `order_actions.js` (approve/reject/buy buttons). They load through the manifest `assets` key. Tours live in `static/tests/tours/`.

**Per-user configuration** is stored on `res.partner`: `portal_order_limit` (max quantity), `allowed_product_category_ids` (product visibility, enforced in the controller) and `portal_orders_tax_rate`, which overrides the global tax when non-zero. `MAX_PORTAL_ORDER_AMOUNT` (3) in `models/portal_order.py` is the hard cap, enforced by a constraint.

**Security** (Odoo 20 unified `ir.access`, no `ir.model.access`/`ir.rule`):
- `security/portal_orders_security.xml`: privilege plus two groups, `group_portal_employee` and `group_portal_manager`. Both imply `base.group_portal`.
- `security/ir.access.csv` (`id,name,model_id,group_id/id,operation,domain`): employees `cru` their own orders (`user_id = user`), managers `ru` all, internal users `ru` all, plus read rows for the product/partner/tax models the portal pages read. Mail, sequence, purchase and attachment writes go through narrow, commented `sudo()` calls instead of extra rows.
- `portal.order.partner_id` is a related field (sudo-computed), so managers can show requester details without access to `res.users`.
