import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import  nowdate
@frappe.whitelist()
def make_si(pr_name,customer):
    pr = frappe.get_doc("Purchase Receipt", pr_name)

    si = frappe.new_doc("Sales Invoice")
    si.due_date = nowdate()
    si.customer = customer
    # remove taxes
    si.ignore_pricing_rule = 1
    si.taxes_and_charges = ""
    # copy items manually
    for row in pr.items:
        income_account = frappe.db.get_value("Company", pr.company,"default_income_account")
        cost_center = frappe.db.get_value("Company", pr.company,"cost_center")
        if row.igst_amount:
            rate = (row.rate+row.igst_amount)
        if row.cgst_amount:
            rate = (row.rate+row.cgst_amount)

        si.append("items", {
            "item_code": row.item_code,
            "item_name": row.item_name,
            "qty": row.qty,
            "rate":  rate* 1.01,
            "uom": row.uom,
            "income_account": income_account,
            "cost_center": cost_center,            
        })
    si.save()
    return si
