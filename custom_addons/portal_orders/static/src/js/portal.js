odoo.define('portal.orders', function (require) {
  'use strict';

  var publicWidget = require('web.public.widget');
  var utils = require('web.utils');

  publicWidget.registry.portalNewOrder = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.new_order_form)',
    events: {
      'show.bs.modal .modal_new_order': '_onShowDialog',
      'change .products_list': '_onSelectProduct',
      'change .amount': '_calculateTaxedPrice',
      'change .supplier_offer': '_calculateTaxedPrice',
      'click .new_order_confirm': '_onNewOrderConfirm',
      'click .cancel_order': '_clearForm',
      'change .signature': '_onSelectFile',
    },
    amount: 0,
    selected_price: 0,
    applied_tax_rate: 0,
    gross_total: 0,
    taxed_total: 0,

    _onSelectFile: function (ev) {
      const file = ev.target.files[0];
      const fileSize = ((file.size / 1024) / 1024).toFixed(4);

      if (fileSize > 5) {
        alert('file too large, please select a file smaller than 5MB');
        $('.new_order_confirm').prop('disabled', true);
      } else {
        $('.new_order_confirm').prop('disabled', false);
      }
    },

    _calculateTaxedPrice: function (ev) {
      $('.totals').empty();

      if ($('.amount').val() !== "") {
        this.amount = parseInt($('.amount').val());
      } else {
        return;
      }

      this.selected_price = parseInt($('.supplier_offer:checked').attr('data-price'));
      let currency_symbol = $('.supplier_offer:checked').attr('data-currency-symbol')
      // TODO: validate amount: 1,2,3

      if (this.amount !== "" && this.selected_price > 0 && this.applied_tax_rate > 0) {
        this.gross_total = (this.amount * this.selected_price);
        this.taxed_total = this.gross_total + (this.gross_total * (this.applied_tax_rate / 100));

        $('.totals').append(`
          <label class="total_gross_price">
            Totax gross price is: ${currency_symbol}${this.gross_total}
          </label>
          <br/>
          <label class="total_taxed_price">
            Totax taxed price is: ${currency_symbol}${this.taxed_total}
          </label>
        `);
      } else {
        $('.totals').empty();
      }
    },

    _clearForm: function () {
      $('.suppliers').empty();
      $('.totals').empty();
    },

    _createOrder: async function () {
      let files = [];

      let inputs = $('.signature');
      for (var i = 0; i < inputs.length; i++) {
        files.push(inputs.eq(i).prop("files")[0]);
      }

      console.log(files[0]);

      const pdf = await utils.getDataURLFromFile(files[0]);
      const product_id = $('.products_list').find(':selected').val();
      const supplierInfoId = $('.supplier_offer:checked').attr('id');
      const amount = $('.amount').val();

      return this._rpc({
        route: '/my/portal_orders/save',
        params: {
          "file": pdf,
          "product_id": product_id,
          "supplierinfo_id": supplierInfoId,
          "amount": amount
        }
      }).then(response => {
        window.location = "/my/portal_orders";
      });
    },

    _buttonExec: function ($btn, callback) {
      $btn.prop('disabled', true);
      return callback.call(this).guardedCatch(function () {
        $btn.prop('disabled', false);
      });
    },

    _onShowDialog: function (ev) {
      // first, clear list
      $('.products_list').empty();
      $('.amount').val("");

      console.log(this.getSession().user_id);

      this._rpc({
        model: 'res.partner',
        method: 'get_portal_allowed_products',
        args: [0, this.getSession().user_id],
      }).then(function (response) {
        $('.products_list').append(`<option value=""></option>`);
        response.forEach(product => {
          $('.products_list').append(`<option value="${product.id}">${product.display_name}</option>`);
        });
      });
    },

    _onSelectProduct: function (ev) {
      const productId = ev.target.value;

      // clear list
      $('.amount').val("");
      $('.suppliers').empty();
      $('.applied_tax_rate').empty();
      $('.totals').empty();

      if (productId === "") {
        return;
      }

      // get tax rates
      this._rpc({
        route: '/my/portal_orders/tax_rate',
        method: 'get'
      }).then(response => {
        if (response.user_tax_rate > 0) {
          this.applied_tax_rate = parseInt(response.user_tax_rate);
          $('.applied_tax_rate').append(`Applying user specific tax rate: ${this.applied_tax_rate}%`);
        } else {
          this.applied_tax_rate = parseInt(response.global_tax_rate);
          $('.applied_tax_rate').append(`Applying global taxt rate: ${this.applied_tax_rate}%`);
        }

        this._calculateTaxedPrice();
      });

      this._rpc({
        route: '/my/portal_orders/product_suppliers/',
        params: {
          product_id: productId
        }
      }).then(response => {
        response.forEach(supplier => {
          $('.suppliers').append(`
            <div class="form-check o_radio_item">
              <input class="form-check-input o_radio_input supplier_offer" type="radio" name="supplier_offer"
                  id="${supplier.id}" data-price="${supplier.price}" data-currency-symbol="${supplier.currency}" required="">
              <label class="form-check-label o_form_label" for="supplier_offer">
                <span class="text-primary">${supplier.name}</span> offers this product at price: 
                <span class="text-success">${supplier.currency}${supplier.price}</span>
              </label>
            </div>
          `)
        });
      });
    },

    _validateForm: function () {
      const amount = parseInt($('.amount').val());
      const product = $('.products_list').val();
      const signature = $('.signature');

      if (product === "") {
        alert('please select a product.');
        return Promise.resolve(false);
      }

      if (amount == "" || isNaN(amount) || amount < 1 || amount > 3) {
        alert('invalid amount');
        return Promise.resolve(false);
      }

      if ($('.supplier_offer:checked').val() === undefined) {
        alert('please select a vendor.');
        return Promise.resolve(false);
      }

      if (signature === "") {
        alert("please attach the signature PDF file.");
        return Promise.resolve(false);
      }

      return this._rpc({
        route: '/my/portal_orders/check',
        params: {
          "amount": amount,
          "user_id": this.getSession().user_id
        }
      }).then(function (response) {
        if (response.valid && amount <= response.amount) {
          return true;
        } else {
          alert(`your allowed amount is max: ${response.amount}`);
          return false;
        }
      });
    },

    _onNewOrderConfirm: async function (ev) {
      ev.preventDefault();
      ev.stopPropagation();

      this._validateForm().then(response => {
        if (response) {
          this._buttonExec($(ev.currentTarget), this._createOrder);
        }
      });
    },

  });

  publicWidget.registry.portalApproveOrder = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.approve_portal_order)',
    events: {
      'click .approve_portal_order': '_onApproveOrder',
    },

    _onApproveOrder: function (ev) {
      const order_id = $('.approve_portal_order').attr('data-id');
      this._rpc({
        route: '/my/portal_orders/approve',
        params: {
          "order_id": order_id
        },
      }).then(function (response) {
        window.location = "/my/portal_orders";
      });
    },
  });

  publicWidget.registry.portalRejectOrder = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.reject_portal_order)',
    events: {
      'click .reject_portal_order': '_onRejectOrder',
    },

    _onRejectOrder: function (ev) {
      const order_id = $('.reject_portal_order').attr('data-id');
      this._rpc({
        route: '/my/portal_orders/reject',
        params: {
          "order_id": order_id
        },
      }).then(function (response) {
        window.location = "/my/portal_orders";
      });
    },
  });

  publicWidget.registry.portalBuyOrder = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.buy_portal_order)',
    events: {
      'click .buy_portal_order': '_onBuyOrder',
    },

    _onBuyOrder: function (ev) {
      const order_id = $('.buy_portal_order').attr('data-id');
      this._rpc({
        route: '/my/portal_orders/buy',
        params: {
          "order_id": order_id
        },
      }).then(function (response) {
        window.location = "/my/portal_orders";
      });
    },
  });
});
