import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def auto_make_pr(source_pr):
    """
    Create a new Purchase Receipt from an existing PR (or any document),
    but do NOT save it. Clears taxes, sets warehouse from settings, increases rate by 1%.
    """

    source_doc = frappe.get_doc("Purchase Receipt", source_pr)
    master = frappe.get_doc("Master Settings")
    supplier = frappe.get_doc("Supplier", master.default_internal_supplier)

    def update_items(source_doc, target_doc):
        # -----------------------------
        # 1️⃣ Supplier & Company
        # -----------------------------
        target_doc.supplier = master.default_internal_supplier
        target_doc.company = supplier.represents_company

        # -----------------------------
        # 2️⃣ Fetch Company Warehouse Settings
        # -----------------------------
        default_wh = None
        try:
            settings = frappe.get_doc("Company Warehouse Settings", "Company Warehouse Settings")
            for w in settings.warehouses:
                if w.company == target_doc.company:
                    default_wh = w.default_warehouse
                    break
        except:
            default_wh = None

   
        target_doc.set_warehouse = default_wh or ""

        # -----------------------------
        # 4️⃣ Update item warehouse (if blank)
        # -----------------------------
        for item in target_doc.items:
            if not item.warehouse and default_wh:
                item.warehouse = default_wh

        # -----------------------------
        # 5️⃣ Clear taxes
        # -----------------------------
        target_doc.taxes_and_charges = ""
        target_doc.taxes = []

        for item in target_doc.items:
            item.item_tax_template = None

        target_doc.ignore_default_taxes = 1

        # -----------------------------
        # 6️⃣ Increase item rate by 1%
        # -----------------------------
        for item in target_doc.items:
            if item.rate:
                item.rate = item.rate * 1.01
                item.amount = item.rate * item.qty

        # -----------------------------
        # 7️⃣ Clear addresses
        # -----------------------------
        target_doc.supplier_address = None
        target_doc.contact_person = None
        target_doc.billing_address = None
        target_doc.shipping_address = None

        # -----------------------------
        # 8️⃣ Fill basic defaults (no taxes)
        # -----------------------------
        target_doc.run_method("set_missing_values")
      # Clear taxes table
        target_doc.taxes = []

        # Clear Purchase Taxes and Charges Template link
        target_doc.taxes_and_charges = ""

        for item in target_doc.items:
            item.item_tax_template = None

        # Prevent auto taxes
        target_doc.ignore_default_taxes = 1


    # -----------------------------
    # Create mapped doc (not saved)
    # -----------------------------
    target_doc = get_mapped_doc(
        "Purchase Receipt",
        source_pr,
        {
            "Purchase Receipt": {"doctype": "Purchase Receipt"},
            "Purchase Receipt Item": {"doctype": "Purchase Receipt Item"}
        },
        postprocess=update_items
    )

    return target_doc
