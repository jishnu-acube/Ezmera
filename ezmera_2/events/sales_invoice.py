import frappe
from frappe.model.mapper import get_mapped_doc

@frappe.whitelist()
def create_sales_invoice(source_name, target_doc=None):
    doc = get_mapped_doc(
        "Purchase Receipt",
        source_name,
        {
            "Purchase Receipt": {
                "doctype": "Sales Invoice",
                "field_map": {
                    "posting_date": "posting_date"
                }
            },
            "Purchase Receipt Item": {
                "doctype": "Sales Invoice Item",
                "field_map": {
                    "rate": "rate",
                    "amount": "amount"
                }
            }
        },
        target_doc
    )

    return doc
