
frappe.ui.form.on("Purchase Receipt", {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button("Sales Invoice", () => {
                frappe.model.open_mapped_doc({
                    method: "ezmera_app.events.sales_invoice.create_sales_invoice",
                    source_name: frm.doc.name
                });
            },);
        }
    }
});
