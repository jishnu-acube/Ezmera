function apply_pr_rate(frm) {
    (frm.doc.items || []).forEach(row => {
        if (row.custom_pr_rate) {
            frm.doc.taxes =[]
            frm.doc.tax_category =""
            frm.doc.taxes_and_charges = ""
            const rate = flt(row.custom_pr_rate * 1.01, 2);

            row.rate = rate;
            row.price_list_rate = rate;
            row.base_rate = rate;

            row.discount_percentage = 0;
            row.discount_amount = 0;
            row.margin_type = "";
            row.margin_rate_or_amount = 0;

            row.amount = rate * row.qty;
            row.base_amount = row.amount;
        }
    });

    frm.refresh_field("items");
}

frappe.ui.form.on("Delivery Note", {
    refresh(frm) {
        apply_pr_rate(frm);
    },
    validate(frm) {
        apply_pr_rate(frm);
    },
    before_save(frm) {
        apply_pr_rate(frm);
    }
});
