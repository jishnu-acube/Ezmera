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


      
        if hasattr(target_doc, "selling_price"):
            for row in target_doc.selling_price:
               
                if row.item:
                    row.selling_price = row.selling_price 
                    row.item = row.item
                    row.price_list = row.price_list

             


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
            "Purchase Receipt Item": {"doctype": "Purchase Receipt Item"},
            "Selling Price Table": {"doctype": "Selling Price Table"}
        },
        postprocess=update_items
    )

    return target_doc

import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import today, flt


@frappe.whitelist()
def auto_make_delivery_note(source_pr):
    """
    Create Delivery Note from Purchase Receipt
    Store PR rate in custom_pr_rate
    DN rate = PR rate + 1%
    """

    source_doc = frappe.get_doc("Purchase Receipt", source_pr)

    master = frappe.get_doc("Master Settings")
    if not master.default_internal_customer:
        frappe.throw("Set Default Internal Customer in Master Settings")

    customer = master.default_internal_customer
    company = source_doc.company

    def update_items(source_doc, target_doc):

        target_doc.customer = customer
        target_doc.contact_person = ""
        target_doc.place_of_supply = ""
        target_doc.gst_category = "Unregistered"
        target_doc.address_display = ""
        target_doc.company = company
        target_doc.posting_date = today()

        target_doc.ignore_pricing_rule = 1
        target_doc.ignore_default_taxes = 1
        target_doc.taxes = []
        target_doc.taxes_and_charges = ""


        for item in target_doc.items:
            if not item.purchase_receipt_item:
                continue

            pr_item = frappe.get_doc(
                "Purchase Receipt Item", item.purchase_receipt_item
            )

            # STORE PR RATE
            item.custom_pr_rate = flt(pr_item.rate , 2)
            item.qty = pr_item.qty

        target_doc.run_method("set_missing_values")

    dn = get_mapped_doc(
        "Purchase Receipt",
        source_pr,
        {
            "Purchase Receipt": {"doctype": "Delivery Note"},
            "Purchase Receipt Item": {
                "doctype": "Delivery Note Item",
                "field_map": {
                    "name": "purchase_receipt_item",
                },
            },
        },
        postprocess=update_items,
    )

    return dn

