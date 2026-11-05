import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class PortalOrderActions extends Interaction {
    static selector = ".o_portal_orders_order";
    dynamicContent = {
        ".o_portal_orders_action": { "t-on-click": this.locked(this.onActionClick, true) },
    };

    async onActionClick(ev) {
        const orderId = this.el.dataset.orderId;
        const action = ev.currentTarget.dataset.action;
        await this.waitFor(rpc(`/my/portal_orders/${orderId}/${action}`));
        window.location = "/my/portal_orders";
    }
}

registry.category("public.interactions").add("portal_orders.order_actions", PortalOrderActions);
