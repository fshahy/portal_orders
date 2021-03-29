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
* 3 kind of users:
  * Internal Users
  * Portal Employee
  * Portal Manager
* Access backend through the portal
* List-view and form-view of orders.
* Uses product variations.
* Access ir.attachment model from portal.
* Use email templates for sending emails.
* Configurable global tax for portal orders.
* User specific tax which overrides the global tax.
* Global limit (currently 3) on the quantity of products to purchase for orders.
* User specific limit for quantity of products to purchase which overrides the global value of 3.
* Website for validation.
* Attaching files through website has a limit of 5MB size.
* Manager can approve or reject orders.