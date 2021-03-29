# Odoo Developer Test Case
When an employee needs to buy something, he/she can create and order for this
product and select from which vendor he/she wants to buy. 

The order has to be approved by the manager and the product is purchased from that vendor. 
Once the product is sent to the company, the employee can pick it up at the office.

Is also possible that the Manager rejects the order, based on the company’s decision. In
that case, the employee can create a new order only the next month (it can be for the
same product or for a different product).

For employees and managers, we want to handle this logic using portals, and only give
backend access to our accounting team to confirm the sales, purchases, invoices, etc.

## Features
* 2 new kind of users, besides the one that already exists in Odoo:
  * Portal Employee
  * Portal Manager
  * Internal Users
* Access backend through the portal
* List-view and form-view of orders.
* Each user sees only his/her own orders.
* Manager sees all orders.
* Uses product variations.
* Can search orders in list view.
* Users can only see producs from categories they are allowed to.
* Access ir.attachment model from portal.
* Use email templates for sending emails.
* Configurable global tax for portal orders.
* User specific tax which overrides the global tax.
* Global limit (currently 3) on the quantity of products to purchase for orders.
* User specific limit for quantity of products to purchase which overrides the global value of 3.
* Generates a purchase order bases on the portal order.
* Set picking date using a wizard.
* Website for validation.
* Attaching files through website has a limit of 5MB size.
* Manager can approve or reject orders.
* Include some python unit tests and demo data.

## How to use
There are 2 sample users (employees) which can be used to login to the portal and create orders:
* username alice@example.com and password `alice`
* username bob@example.com and password `bob`

also there is a sample manager with the following credentials which can approve or reject orders created by employees:
* username john@example.com and password `bob`

the internal user data is as follows:
* username ingrid@example.com and password `ingrid`

only orders in the state of `purchase_in_progress` show to the internals user. 
After receiving the product, an internal user can select a picking date for the portal order.
The employee goes to the office at that date and receives the products.
Then the internal user can close the order by pressing the done button.