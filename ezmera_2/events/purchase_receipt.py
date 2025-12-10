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

    # Get default company and cost center from supplier's linked companies
    allowed_company = ""
    cost_center = ""
    if supplier.companies:
        for comp in supplier.companies:
            allowed_company = comp.company
            company = frappe.get_doc("Company", comp.company)
            cost_center = company.cost_center
            break  # take first company

    # Get default warehouse for the company
    default_wh = None
    try:
        settings = frappe.get_doc("Company Warehouse Settings", "Company Warehouse Settings")
        for w in settings.warehouses:
            if w.company == allowed_company:
                default_wh = w.default_warehouse
                break
    except:
        default_wh = None

    def update_items(source_doc, target_doc):
        # Set general fields
        target_doc.supplier = master.default_internal_supplier
        target_doc.company = allowed_company
        target_doc.set_warehouse = default_wh or ""

        # Clear taxes
        target_doc.taxes_and_charges = ""
        target_doc.taxes = []
        target_doc.ignore_default_taxes = 1

        # Clear addresses
        target_doc.supplier_address = None
        target_doc.contact_person = None
        target_doc.billing_address = None
        target_doc.shipping_address = None

        # Update each item explicitly
        for item in target_doc.items:
            # Force overwrite warehouse & cost center
            item.warehouse = default_wh or ""
            item.cost_center = cost_center or ""

            # Update rate by 1%
            if item.rate:
                item.rate = item.rate * 1.01
                item.amount = item.rate * item.qty

            # Clear item tax template
            item.item_tax_template = None

        # Recompute any missing values (optional)
        target_doc.run_method("set_missing_values")

    # Map the PR to a new PR
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
