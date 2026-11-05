import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("portal_orders_employee_new_order", {
    steps: () => [
        {
            content: "Open the new order dialog",
            trigger: "button[data-bs-target='#o_portal_orders_new_order_modal']",
            run: "click",
        },
        {
            content: "Pick the first allowed product once the list is loaded",
            trigger: ".o_portal_orders_product:has(option:nth-child(2))",
            run() {
                this.anchor.selectedIndex = 1;
                this.anchor.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "Request two items",
            trigger: ".o_portal_orders_amount",
            run: "edit 2",
        },
        {
            content: "Pick the cheapest vendor",
            trigger: ".o_portal_orders_suppliers label:contains('Vendor 1')",
            run: "click",
        },
        {
            content: "Totals use Alice's own 20% tax rate",
            trigger: ".o_portal_orders_totals div:contains('24.00')",
        },
        {
            content: "Attach the signed request",
            trigger: ".o_portal_orders_signature",
            run() {
                const transfer = new DataTransfer();
                transfer.items.add(new File(["%PDF-1.4\n%%EOF\n"], "signature.pdf", { type: "application/pdf" }));
                this.anchor.files = transfer.files;
                this.anchor.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "Confirm the order",
            trigger: ".o_portal_orders_confirm",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "The new order is listed",
            trigger: ".o_portal_my_doc_table a:contains('PPO')",
        },
    ],
});

registry.category("web_tour.tours").add("portal_orders_manager_approve", {
    steps: () => [
        {
            content: "Approve the order",
            trigger: ".o_portal_orders_action[data-action='approve']",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Back on the order list, the order is approved",
            trigger: ".o_portal_my_doc_table td:contains('Approved')",
        },
    ],
});
