import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import  nowdate,flt
from erpnext.accounts.doctype.sales_invoice.sales_invoice import (
					get_received_items,validate_inter_company_transaction,get_inter_company_details,
					set_purchase_references,update_address,update_taxes)
@frappe.whitelist()
def make_si(pr_name,customer):
	pr = frappe.get_doc("Purchase Receipt", pr_name)

	si = frappe.new_doc("Sales Invoice")
	si.due_date = nowdate()
	si.custom_purchase_receipt = pr.name
	si.customer = customer
	# remove taxes
	si.ignore_pricing_rule = 1
	si.taxes_and_charges = ""
	# copy items manually
	for row in pr.items:
		income_account = frappe.db.get_value("Company", pr.company,"default_income_account")
		cost_center = frappe.db.get_value("Company", pr.company,"cost_center")
		rate = row.rate
		if row.igst_amount:
			rate = (row.rate+(row.igst_amount/row.qty))
		if row.cgst_amount:
			rate = (row.rate+(row.cgst_amount)*2/row.qty)

		si.append("items", {
			"item_code": row.item_code,
			"item_name": row.item_name,
			"qty": row.qty,
			"rate":  rate* 1.01,
			"uom": row.uom,
			"income_account": income_account,
			"cost_center": cost_center,
			"item_tax_template":row.item_tax_template,
			"custom_mrp":row.custom_new_mrp
		})
	si.save()
	return si




@frappe.whitelist()
def make_inter_company_purchase_invoice(source_name, target_doc=None):
	return make_inter_company_transaction("Sales Invoice", source_name, target_doc)


def make_inter_company_transaction(doctype, source_name, target_doc=None):
	if doctype in ["Sales Invoice", "Sales Order"]:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Purchase Invoice" if doctype == "Sales Invoice" else "Purchase Order"
		target_detail_field = "sales_invoice_item" if doctype == "Sales Invoice" else "sales_order_item"
		source_document_warehouse_field = "target_warehouse"
		target_document_warehouse_field = "from_warehouse"
		received_items = get_received_items(source_name, target_doctype, target_detail_field)
	else:
		source_doc = frappe.get_doc(doctype, source_name)
		target_doctype = "Sales Invoice" if doctype == "Purchase Invoice" else "Sales Order"
		source_document_warehouse_field = "from_warehouse"
		target_document_warehouse_field = "target_warehouse"
		received_items = {}

	validate_inter_company_transaction(source_doc, doctype)
	details = get_inter_company_details(source_doc, doctype)

	def set_missing_values(source, target):
		target.run_method("set_missing_values")
		set_purchase_references(target)

	def update_details(source_doc, target_doc, source_parent):
		def _validate_address_link(address, link_doctype, link_name):
			return frappe.db.get_value(
				"Dynamic Link",
				{
					"parent": address,
					"parenttype": "Address",
					"link_doctype": link_doctype,
					"link_name": link_name,
				},
				"parent",
			)

		target_doc.inter_company_invoice_reference = source_doc.name
		if target_doc.doctype in ["Purchase Invoice", "Purchase Order"]:
			currency = frappe.db.get_value("Supplier", details.get("party"), "default_currency")
			target_doc.company = details.get("company")
			target_doc.supplier = details.get("party")
			target_doc.is_internal_supplier = 1
			target_doc.ignore_pricing_rule = 1
			target_doc.buying_price_list = source_doc.selling_price_list

			# Invert Addresses
			if source_doc.company_address and _validate_address_link(
				source_doc.company_address, "Supplier", details.get("party")
			):
				update_address(target_doc, "supplier_address", "address_display", source_doc.company_address)
			if source_doc.dispatch_address_name and _validate_address_link(
				source_doc.dispatch_address_name, "Company", details.get("company")
			):
				update_address(
					target_doc,
					"dispatch_address",
					"dispatch_address_display",
					source_doc.dispatch_address_name,
				)
			if source_doc.shipping_address_name and _validate_address_link(
				source_doc.shipping_address_name, "Company", details.get("company")
			):
				update_address(
					target_doc,
					"shipping_address",
					"shipping_address_display",
					source_doc.shipping_address_name,
				)
			if source_doc.customer_address and _validate_address_link(
				source_doc.customer_address, "Company", details.get("company")
			):
				update_address(
					target_doc, "billing_address", "billing_address_display", source_doc.customer_address
				)

			if currency:
				target_doc.currency = currency

			update_taxes(
				target_doc,
				party=target_doc.supplier,
				party_type="Supplier",
				company=target_doc.company,
				doctype=target_doc.doctype,
				party_address=target_doc.supplier_address,
				company_address=target_doc.shipping_address,
			)

		else:
			currency = frappe.db.get_value("Customer", details.get("party"), "default_currency")
			target_doc.company = details.get("company")
			target_doc.customer = details.get("party")
			target_doc.selling_price_list = source_doc.buying_price_list

			if source_doc.supplier_address and _validate_address_link(
				source_doc.supplier_address, "Company", details.get("company")
			):
				update_address(
					target_doc, "company_address", "company_address_display", source_doc.supplier_address
				)
			if source_doc.shipping_address and _validate_address_link(
				source_doc.shipping_address, "Customer", details.get("party")
			):
				update_address(
					target_doc, "shipping_address_name", "shipping_address", source_doc.shipping_address
				)
			if source_doc.shipping_address and _validate_address_link(
				source_doc.shipping_address, "Customer", details.get("party")
			):
				update_address(target_doc, "customer_address", "address_display", source_doc.shipping_address)

			if currency:
				target_doc.currency = currency

			update_taxes(
				target_doc,
				party=target_doc.customer,
				party_type="Customer",
				company=target_doc.company,
				doctype=target_doc.doctype,
				party_address=target_doc.customer_address,
				company_address=target_doc.company_address,
				shipping_address_name=target_doc.shipping_address_name,
			)

	def update_item(source, target, source_parent):
		target.qty = flt(source.qty) - received_items.get(source.name, 0.0)
		if source.doctype == "Purchase Order Item" and target.doctype == "Sales Order Item":
			target.purchase_order = source.parent
			target.purchase_order_item = source.name
			target.material_request = source.material_request
			target.material_request_item = source.material_request_item

		if (
			source.get("purchase_order")
			and source.get("purchase_order_item")
			and target.doctype == "Purchase Invoice Item"
		):
			target.purchase_order = source.purchase_order
			target.po_detail = source.purchase_order_item

		if (source.get("serial_no") or source.get("batch_no")) and not source.get("serial_and_batch_bundle"):
			target.use_serial_batch_fields = 1

	item_field_map = {
		"doctype": target_doctype + " Item",
		"field_no_map": ["income_account", "expense_account", "cost_center", "warehouse"],
		"field_map": {
			"rate": "rate",
			"custom_mrp":"custom_new_mrp"
		},
		"postprocess": update_item,
		"condition": lambda doc: doc.qty > 0,
	}

	if doctype in ["Sales Invoice", "Sales Order"]:
		item_field_map["field_map"].update(
			{
				"name": target_detail_field,
			}
		)

	if source_doc.get("update_stock"):
		item_field_map["field_map"].update(
			{
				source_document_warehouse_field: target_document_warehouse_field,
				"batch_no": "batch_no",
				"serial_no": "serial_no",
			}
		)
	elif target_doctype == "Sales Order":
		item_field_map["field_map"].update(
			{
				source_document_warehouse_field: "warehouse",
			}
		)

	doclist = get_mapped_doc(
		doctype,
		source_name,
		{
			doctype: {
				"doctype": target_doctype,
				"postprocess": update_details,
				"set_target_warehouse": "set_from_warehouse",
				"field_no_map": ["taxes_and_charges", "set_warehouse", "shipping_address"],
			},
			doctype + " Item": item_field_map,
		},
		target_doc,
		set_missing_values,
	)

	return doclist
