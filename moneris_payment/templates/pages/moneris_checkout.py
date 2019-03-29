
from __future__ import unicode_literals
# import frappe
# from _future_ import unicode_literals
import frappe
import frappe.utils
import moneris_payment
import json
import datetime
from frappe import _
from frappe.utils import getdate,nowdate
from datetime import date
from moneris_payment.moneris_payment.doctype.moneris_settings.moneris_settings import get_gateway_controller
from moneris_payment.MonerisPaymentGateway import *

no_cache = 1
no_sitemap = 1

expected_keys = ('amount', 'title', 'description', 'reference_doctype', 'reference_docname',
	'payer_name', 'payer_email', 'order_id', 'currency')
def get_context(context):
	context.no_cache = 1

	# all these keys exist in form_dict
	if not (set(expected_keys) - set(list(frappe.form_dict))):
		for key in expected_keys:
			context[key] = frappe.form_dict[key]
		if frappe.form_dict['payer_email']:
			if frappe.form_dict['payer_email']!=frappe.session.user:
				frappe.throw(_("Not permitted"), frappe.PermissionError)
		else:
			frappe.redirect_to_message(_('Some information is missing'),
			_('Looks like someone sent you to an incomplete URL. Please ask them to look into it.'))
			frappe.local.flags.redirect_location = frappe.local.response.location
			raise frappe.Redirect
		context.reference_docname=frappe.form_dict['order_id']
		context.customercards=frappe.db.get_all("Moneris Vault",fields={'*'},filters={"user_id":frappe.session.user},order_by="creation desc")
		gateway_controller = get_gateway_controller(context.reference_doctype, context.reference_docname)
		context.publishable_key = get_api_key(context.reference_docname, gateway_controller)
		context.image = get_header_image(context.reference_docname, gateway_controller)

		context['amount'] = fmt_money(amount=context['amount'], currency=context['currency'])

		if frappe.db.get_value(context.reference_doctype, context.reference_docname, "is_a_subscription"):
			payment_plan = frappe.db.get_value(context.reference_doctype, context.reference_docname, "payment_plan")
			recurrence = frappe.db.get_value("Payment Plan", payment_plan, "recurrence")

			context['amount'] = context['amount'] + " " + _(recurrence)



	else:
		frappe.redirect_to_message(_('Some information is missing'),
			_('Looks like someone sent you to an incomplete URL. Please ask them to look into it.'))
		frappe.local.flags.redirect_location = frappe.local.response.location
		raise frappe.Redirect


# @frappe.whitelist(allow_guest=True)
# def make_payment(payment_request_id,payment_amount,card_number,card_expire,card_cvv,reference_doctype,reference_docname):
# 	try:
# 		# Order Info
# 		payment_request=frappe.get_doc("Payment Request", payment_request_id)
# 		sale_order=frappe.get_doc("Sales Order", payment_request.reference_name)
# 		billing_info=frappe.get_doc("Address", sale_order.customer_address)
# 		shipping_info=frappe.get_doc("Address", sale_order.shipping_address_name)
# 		# customer_info=frappe.get_doc("Customer", sale_order.customer)
		
# 		sale_order_items=frappe.db.get_all("Sales Order Item",  fields=['item_code,item_name,rate,qty'], filters={'parent':sale_order.name},limit_page_length=1000)
# 		order_id = payment_request.reference_name+"-"+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
# 		amount = payment_amount
# 		pan =card_number.replace(' ', '')
# 		expiry_date = card_expire
# 		crypt = card_cvv
# 		customer=CustInfo()

# 		#Customer Billing Info and Shipping Info

# 		first_name=sale_order.contact_display
# 		last_name=" "
# 		company_name=""
# 		# Billing Info
# 		billing_full_address=billing_info.address_line1
# 		if billing_info.address_line2:
# 			billing_full_address=billing_full_address+","+billing_info.address_line2
# 		if len(billing_full_address)>70:
# 			billing_full_address=billing_full_address[:70]
# 		billing_address=billing_full_address
# 		billing_city=billing_info.city
# 		billing_state_province=billing_info.state
# 		billing_postal_code=billing_info.pincode
# 		billing_country=billing_info.country
# 		billing_phone_number=billing_info.phone
# 		billing_fax=""
# 		billing_tax1=""
# 		if sale_order.total_taxes_and_charges:
# 			billing_tax1=str(sale_order.total_taxes_and_charges)
# 		billing_tax2=""
# 		billing_tax3=""
# 		shipping_cost="0.00"

# 		# # Shipping Info
# 		shipping_full_address=shipping_info.address_line1
# 		if shipping_info.address_line2:
# 			shipping_full_address=shipping_full_address+","+shipping_info.address_line2
# 		if len(shipping_full_address)>70:
# 			shipping_full_address=shipping_full_address[:70]
# 		shipping_address=shipping_full_address
# 		shipping_city=shipping_info.city
# 		shipping_state_province=shipping_info.state
# 		shipping_postal_code=shipping_info.pincode
# 		shipping_country=shipping_info.country
# 		shipping_phone_number=shipping_info.phone
# 		shipping_fax=""
# 		shipping_tax1=""
# 		if sale_order.total_taxes_and_charges:
# 			shipping_tax1=str(sale_order.total_taxes_and_charges)
# 		shipping_tax2=""
# 		shipping_tax3=""
# 		shipping_cost="0.00"
# 		billing_obj=BillingInfo(first_name, last_name, company_name, billing_address, billing_city, billing_state_province, billing_postal_code, billing_country, billing_phone_number, billing_fax, billing_tax1, billing_tax2, billing_tax3, shipping_cost)
# 		shpping_obj=ShippingInfo(first_name, last_name, company_name, shipping_address, shipping_city, shipping_state_province, shipping_postal_code, shipping_country, shipping_phone_number, shipping_fax, shipping_tax1, shipping_tax2, shipping_tax3, shipping_cost)
# 		customer.setBilling(billing_obj)
# 		customer.setShipping(shpping_obj)
# 		customer.setEmail(frappe.session.user)
# 		customer.setInstruction(" ")
		
# 		# Product Items

# 		for item in sale_order_items:
# 			customer.addItem(Item(item.item_name[:45],str(item.qty),item.item_code.split(':')[0],str(item.rate)))


# 		#Purchase 

# 		purchase = Purchase(order_id, amount , pan, expiry_date, crypt)
# 		purchase.setCustInfo(customer)
# 		MSGObject=mpgHttpsPost(purchase)
# 		MSGObject.postRequest()
		
# 		#Response
# 		resp = MSGObject.getResponse()
# 		if resp.getComplete()=="true":
# 			gateway_controller = get_gateway_controller(reference_doctype,reference_docname)
# 			if frappe.db.get_value(reference_doctype, reference_docname, 'is_a_subscription'):
# 				reference = frappe.get_doc(reference_doctype, reference_docname)
# 				data =  reference.create_subscription("Moneris", gateway_controller, data)
# 			else:
# 				data =  frappe.get_doc("Moneris Settings", gateway_controller).create_request(data)

# 			frappe.db.commit()
# 			return data

# 		else:
# 			return {"ReceiptId" : resp.getReceiptId(),
# 					"ReferenceNum" :resp.getReferenceNum(),
# 					"ResponseCod" : resp.getResponseCode(),
# 					"AuthCode" : resp.getAuthCode(),
# 					"TransTime" : resp.getTransTime(),
# 					"TransDate" : resp.getTransDate(),
# 					"TransType" : resp.getTransType(),
# 					"Complete" : resp.getComplete(),
# 					"Message" : resp.getMessage(),
# 					"TransAmount" : resp.getTransAmount(),
# 					"CardType" : resp.getCardType(),
# 					"TransID" : resp.getTransID(),
# 					"TimedOut" : resp.getTimedOut(),
# 					"BankTotals" : resp.getBankTotals(),
# 					"Ticket" : resp.getTicket()}
# 	except Exception,e:
# 		print(e)
# 		return e

@frappe.whitelist(allow_guest=True)
def make_payment(data,reference_doctype,reference_docname):
	try:
		gateway_controller = get_gateway_controller(reference_doctype,reference_docname)
		data =  frappe.get_doc("Moneris Settings", gateway_controller).create_request(data)
		frappe.db.commit()
		return data
	except Exception as e:
		print(e)
		return e

@frappe.whitelist(allow_guest=True)
def refund_payment():
	# Refund
	refund=Refund("test_python-vls-2019-01-24-13-36-16","10.00","82990-0_12","7")
	MSGObject=mpgHttpsPost(refund)
	MSGObject.postRequest()
	resp = MSGObject.getResponse()
	return {"ReceiptId" : resp.getReceiptId(), 
	 		"ReferenceNum" : resp.getReferenceNum(), 
	 		"ResponseCode" : resp.getResponseCode(), 
	 		"AuthCode" : resp.getAuthCode(), 
	 		"TransTime" : resp.getTransTime(), 
	 		"TransDate" : resp.getTransDate(), 
	 		"TransType" : resp.getTransType(), 
	 		"Complete" : resp.getComplete(), 
	 		"Message" : resp.getMessage(), 
	 		"TransAmount" : resp.getTransAmount(), 
	 		"CardType" : resp.getCardType(), 
	 		"TransID" : resp.getTransID(), 
	 		"TimedOut" : resp.getTimedOut(), 
	 		"BankTotals" : resp.getBankTotals(), 
	 		"Ticket" : resp.getTicket()}
	