# Portal Orders

An Odoo 20.0 addon (`custom_addons/portal_orders`) that lets employees request
products to buy from the **website portal**, without giving them a backend
account.

A manager approves or rejects each request, also from the portal. An approved
request becomes a real Odoo **purchase order** for the vendor the employee
chose. Once the goods arrive, the back office sets a pick-up date and the
employee collects them at the office.

Only the back-office team (purchasing, accounting) needs internal Odoo users.
Employees and managers are portal users.

## Who does what

| Role | Odoo user type | What they do |
| --- | --- | --- |
| **Employee** | Portal (group *Portal Orders / Employee*) | Creates requests, sees only their own, clicks *Buy Product* once a request is approved |
| **Manager** | Portal (group *Portal Orders / Manager*) | Sees every request, approves or rejects drafts |
| **Internal user** | Internal | Follows requests being purchased, sets the pick-up date, closes them |

## How a request flows

```
Draft --(manager approves)--> Approved --(employee: Buy Product)--> Purchase in progress
  |                                                                         |
  +--(manager rejects)--> Rejected                    (internal user sets pick-up date)
                                                                            v
                                     Done <--(internal user: Done)-- Ready to pick-up
```

1. **Create.** On `/my/portal_orders` the employee clicks *Create New* and:
   - picks a product (only products from the categories they are allowed to
     see, including variants such as color and size);
   - enters a quantity (at most their personal limit, never more than 3);
   - picks one of the product's vendors and their price;
   - attaches the signed request as a PDF of at most 5MB.

   The form shows the gross and taxed totals before confirming. The request
   gets a number (`PPO0001`, ...) and the managers receive an email.
2. **Approve or reject.** A manager opens the request on the portal and approves
   or rejects it. The employee receives an email either way.
3. **Buy.** On an approved request the employee clicks *Buy Product*. This
   creates a draft purchase order for the chosen vendor, with the product,
   quantity, vendor price and the global purchase tax. The request moves to
   *Purchase in progress*.
4. **Pick-up date.** In the backend menu *Portal Orders*, an internal user sees
   the requests that are in progress or ready. Once the goods are in, they use
   *Set Picking Date*. The request moves to *Ready to pick-up* and the employee
   receives an email with the date.
5. **Done.** After the employee collects the goods, the internal user clicks
   *Done*.

Every step is logged in the request's chatter.

## Configuration

Per-employee settings are on the contact form, in the *Purchase* section:

- **Portal Order Limit**: highest quantity the employee may request (1 to 3).
- **Allowed Product Categories**: the product categories the employee can
  order from.
- **Portal Orders Tax Rate (%)**: a personal tax rate. Leave it at 0 to use
  the global one.

The global tax is the *Global Purchase Tax* (66% by default), in
*Accounting > Configuration > Taxes*. It is also the tax put on the generated
purchase orders.

Outgoing emails go through the *localhost* mail server (`127.0.0.1:1025`,
meant for a local MailHog). Change it in *Settings > Technical > Outgoing Mail
Servers* for real use.

## Demo data

Installing with demo data creates two products with variants, four vendors,
one sample request and these users (the password is the first name):

| Login | Password | Role |
| --- | --- | --- |
| `alice@example.com` | `alice` | Employee: limit 2, own tax rate 20%, *Product Category 1* |
| `bob@example.com` | `bob` | Employee: limit 3, global tax, *Product Category 2* |
| `john@example.com` | `john` | Manager |
| `ingrid@example.com` | `ingrid` | Internal user (Purchase user) |

## Running

```bash
docker-compose up -d    # Odoo 20 on http://localhost:8069 (master password "admin"), Postgres 16
```

Create a database with demo data, then install *Portal Orders* from the Apps
menu. Upgrade after code changes:

```bash
docker-compose exec web odoo -c /etc/odoo/odoo.conf -d <db> -u portal_orders --stop-after-init --no-http
```

Run the tests (they need the demo data):

```bash
docker-compose exec web odoo -c /etc/odoo/odoo.conf -d <db> -u portal_orders --test-enable --test-tags /portal_orders --stop-after-init --no-http
```

The browser tour test (`test_tours`) needs Chrome and the `websocket-client`
Python package in the Odoo container. The stock `odoo:20.0` image has neither,
so it is skipped there.
