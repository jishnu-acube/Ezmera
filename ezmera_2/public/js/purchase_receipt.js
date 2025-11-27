
frappe.ui.form.on("Purchase Receipt", {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {

            frm.add_custom_button("Sales Invoice", () => {

                // Create dialog
                let d = new frappe.ui.Dialog({
                    title: "Select Customer",
                    fields: [
                        {
                            fieldtype: "Link",
                            label: "Customer",
                            fieldname: "customer",
                            options: "Customer",
                            reqd: 1
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
    }
});
