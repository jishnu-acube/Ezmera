frappe.ui.form.on("Purchase Receipt", {
    refresh(frm) {
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.custom_sales_status_ === "Not Sold" &&
            frm.doc.is_internal_supplier == 0 &&
            frm.doc.custom_delivery_only_items == 0
        ) {

            frm.add_custom_button("Sales Invoice", () => {

                let d = new frappe.ui.Dialog({
                    title: "Select Customer",
                    fields: [
                        {
                            fieldtype: "Link",
                            label: "Customer",
                            fieldname: "customer",
                            options: "Customer",
                            reqd: 1,
                            get_query() {
                                return {
                                    filters: {
                                        is_internal_customer: 1   // show only internal customers
                                    }
                                };
                            }
                        }
                    ],
                    primary_action_label: "Create Sales Invoice",
                    primary_action(values) {

                        d.hide();

                        frappe.call({
                            method: "ezmera_2.events.sales_invoice.make_si",
                            args: {
                                pr_name: frm.doc.name,
                                customer: values.customer
                            },
                            callback(r) {
                                frappe.model.sync(r.message);
                                frappe.set_route("Form", "Sales Invoice", r.message.name);
                            }
                        });

                    }
                });

                d.show();
            });
        }
    
     if (frm.doc.custom_delivery_only_items == 1 && frm.doc.is_internal_supplier == 0) {

            frm.add_custom_button("Create Purchase Receipt", () => {

                frappe.call({
                    method: "ezmera_2.events.purchase_receipt.auto_make_pr",
                    args: {
                        source_pr: frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            // Sync unsaved document in local cache
                            frappe.model.sync(r.message);
                            // Redirect to form view (draft)
                            frappe.set_route("Form", "Purchase Receipt", r.message.name);
                        }
                    }
                });

            });
        }
    }
});
