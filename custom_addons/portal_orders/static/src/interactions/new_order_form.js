import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { getDataURLFromFile } from "@web/core/utils/urls";
import { _t } from "@web/core/l10n/translation";

const MAX_SIGNATURE_SIZE = 5 * 1024 * 1024;

export class PortalOrderNewOrderForm extends Interaction {
    static selector = ".o_portal_orders_new_order";
    dynamicContent = {
        _root: { "t-on-show.bs.modal": this.onShow },
        ".o_portal_orders_product": { "t-on-change": this.onProductChange },
        ".o_portal_orders_amount": { "t-on-input": this.renderTotals },
        ".o_portal_orders_suppliers": { "t-on-change": this.renderTotals },
        ".o_portal_orders_signature": { "t-on-change": this.onSignatureChange },
        "form": { "t-on-submit.prevent": this.locked(this.onSubmit, true) },
    };

    setup() {
        this.productEl = this.el.querySelector(".o_portal_orders_product");
        this.amountEl = this.el.querySelector(".o_portal_orders_amount");
        this.suppliersEl = this.el.querySelector(".o_portal_orders_suppliers");
        this.signatureEl = this.el.querySelector(".o_portal_orders_signature");
        this.taxRate = 0;
        this.maxAmount = 0;
    }

    notify(message) {
        this.services.notification.add(message, { type: "danger" });
    }

    async onShow() {
        this.el.querySelector("form").reset();
        this.suppliersEl.replaceChildren();
        this.el.querySelector(".o_portal_orders_totals").replaceChildren();
        const [products, taxInfo] = await this.waitFor(
            Promise.all([rpc("/my/portal_orders/products"), rpc("/my/portal_orders/tax_rate")])
        );
        this.taxRate = taxInfo.tax_rate;
        this.maxAmount = taxInfo.max_amount;
        this.amountEl.max = this.maxAmount;
        this.el.querySelector(".o_portal_orders_amount_help").textContent = _t(
            "You may request up to %s items.",
            this.maxAmount
        );
        this.el.querySelector(".o_portal_orders_tax_rate").textContent = taxInfo.is_user_rate
            ? _t("Applying user specific tax rate: %s%%", this.taxRate)
            : _t("Applying global tax rate: %s%%", this.taxRate);
        this.productEl.replaceChildren(
            new Option("", ""),
            ...products.map((product) => new Option(product.name, product.id))
        );
    }

    async onProductChange() {
        this.suppliersEl.replaceChildren();
        this.renderTotals();
        if (!this.productEl.value) {
            return;
        }
        const suppliers = await this.waitFor(
            rpc("/my/portal_orders/product_suppliers", { product_id: this.productEl.value })
        );
        for (const supplier of suppliers) {
            const wrapperEl = document.createElement("div");
            wrapperEl.className = "form-check";
            const inputEl = document.createElement("input");
            Object.assign(inputEl, {
                className: "form-check-input",
                type: "radio",
                name: "o_portal_orders_supplier",
                id: `o_portal_orders_supplier_${supplier.id}`,
                value: supplier.id,
                required: true,
            });
            inputEl.dataset.price = supplier.price;
            inputEl.dataset.currency = supplier.currency;
            const labelEl = document.createElement("label");
            labelEl.className = "form-check-label";
            labelEl.htmlFor = inputEl.id;
            labelEl.textContent = _t("%(vendor)s offers this product at %(currency)s%(price)s", {
                vendor: supplier.name,
                currency: supplier.currency,
                price: supplier.price,
            });
            wrapperEl.append(inputEl, labelEl);
            this.suppliersEl.append(wrapperEl);
        }
    }

    selectedSupplierEl() {
        return this.suppliersEl.querySelector("input:checked");
    }

    renderTotals() {
        const totalsEl = this.el.querySelector(".o_portal_orders_totals");
        totalsEl.replaceChildren();
        const amount = parseInt(this.amountEl.value);
        const supplierEl = this.selectedSupplierEl();
        if (!amount || !supplierEl) {
            return;
        }
        const currency = supplierEl.dataset.currency;
        const gross = amount * parseFloat(supplierEl.dataset.price);
        const taxed = gross * (1 + this.taxRate / 100);
        for (const text of [
            _t("Total gross price: %(currency)s%(total)s", { currency, total: gross.toFixed(2) }),
            _t("Total taxed price: %(currency)s%(total)s", { currency, total: taxed.toFixed(2) }),
        ]) {
            const lineEl = document.createElement("div");
            lineEl.textContent = text;
            totalsEl.append(lineEl);
        }
    }

    onSignatureChange() {
        const file = this.signatureEl.files[0];
        if (file && file.size > MAX_SIGNATURE_SIZE) {
            this.notify(_t("File too large, please select a file smaller than 5MB."));
            this.signatureEl.value = "";
        }
    }

    async onSubmit() {
        const amount = parseInt(this.amountEl.value);
        const supplierEl = this.selectedSupplierEl();
        const file = this.signatureEl.files[0];
        if (!this.productEl.value) {
            return this.notify(_t("Please select a product."));
        }
        if (!amount || amount < 1 || amount > this.maxAmount) {
            return this.notify(_t("Your allowed amount is at most %s.", this.maxAmount));
        }
        if (!supplierEl) {
            return this.notify(_t("Please select a vendor."));
        }
        if (!file) {
            return this.notify(_t("Please attach the signed request PDF file."));
        }
        const pdf = await this.waitFor(getDataURLFromFile(file));
        await this.waitFor(
            rpc("/my/portal_orders/save", {
                product_id: this.productEl.value,
                supplierinfo_id: supplierEl.value,
                amount,
                file: pdf,
            })
        );
        window.location = "/my/portal_orders";
    }
}

registry
    .category("public.interactions")
    .add("portal_orders.new_order_form", PortalOrderNewOrderForm);
