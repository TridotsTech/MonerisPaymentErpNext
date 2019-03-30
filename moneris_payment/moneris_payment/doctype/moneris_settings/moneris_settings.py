# -*- coding: utf-8 -*-
# Copyright (c) 2019, kartheek@valiantsystems.com and contributors
# For license information, please see license.txt
from __future__ import unicode_literals
import frappe
import json
import datetime
from frappe.model.document import Document
from frappe import _
from six.moves.urllib.parse import urlencode
from frappe.utils import get_url, call_hook_method, cint, flt
from frappe.integrations.utils import make_get_request, make_post_request, create_request_log, create_payment_gateway


class MonerisSettings(Document):
	supported_currencies = [
		 "CAD", "USD","INR"
	]
	def get_payment_url(self, **kwargs):
		return get_url("./moneris_checkout?{0}".format(urlencode(kwargs)))

	def validate_transaction_currency(self, currency):
		if currency not in self.supported_currencies:
			frappe.throw(_("Please select another payment method. Moneris does not support transactions in currency '{0}'").format(currency))
	def on_update(self):
		create_payment_gateway('Moneris')

	def create_request(self, data):
		try:
			from moneris_payment.MonerisPaymentGateway  import Vault,PurchaseWithVault,mpgHttpsPost,CustInfo,BillingInfo,ShippingInfo,Item
			self.data= json.loads(data)
			self.integration_request = create_request_log(self.data, "Host", "Moneris")
			data = json.loads(data)
			self.reference_doctype="Payment Request"
			self.reference_docname=data.get('payment_request_id')
			payment_request=frappe.get_doc("Payment Request", data.get('payment_request_id'))
			sale_order=frappe.get_doc("Sales Order",payment_request.reference_name)
			if sale_order:
				billing_info=frappe.get_doc("Address", sale_order.customer_address)
				shipping_info=frappe.get_doc("Address", sale_order.shipping_address_name)
				# customer_info=frappe.get_doc("Customer", sale_order.customer)
				sale_order_items=frappe.db.get_all("Sales Order Item",  fields=['item_code,item_name,rate,qty'], filters={'parent':sale_order.name},limit_page_length=1000)
				order_id =payment_request.reference_name
				print(sale_order.rounded_total)
				amount = str(sale_order.rounded_total)
				pan =data.get('card_number').replace(' ', '')
				expiry_date = data.get('card_expire')
				crypt = data.get('card_cvv')
				customer=CustInfo()

				#Customer Billing Info and Shipping Info

				first_name=sale_order.contact_display
				last_name=" "
				company_name=""
				# Billing Info
				billing_full_address=billing_info.address_line1
				if billing_info.address_line2:
					billing_full_address=billing_full_address+","+billing_info.address_line2
				if len(billing_full_address)>70:
					billing_full_address=billing_full_address[:70]
				billing_address=billing_full_address
				billing_city=billing_info.city
				billing_state_province=billing_info.state
				billing_postal_code=billing_info.pincode
				billing_country=billing_info.country
				billing_phone_number=billing_info.phone
				billing_fax=""
				billing_tax1=""
				if sale_order.total_taxes_and_charges:
					billing_tax1=str(sale_order.total_taxes_and_charges)
				billing_tax2=""
				billing_tax3=""
				shipping_cost="0.00"

				# # Shipping Info
				shipping_full_address=shipping_info.address_line1
				if shipping_info.address_line2:
					shipping_full_address=shipping_full_address+","+shipping_info.address_line2
				if len(shipping_full_address)>70:
					shipping_full_address=shipping_full_address[:70]
				shipping_address=shipping_full_address
				shipping_city=shipping_info.city
				shipping_state_province=shipping_info.state
				shipping_postal_code=shipping_info.pincode
				shipping_country=shipping_info.country
				shipping_phone_number=shipping_info.phone
				shipping_fax=""
				shipping_tax1=""
				if sale_order.total_taxes_and_charges:
					shipping_tax1=str(sale_order.total_taxes_and_charges)
				shipping_tax2=""
				shipping_tax3=""
				shipping_cost="0.00"
				billing_obj=BillingInfo(first_name, last_name, company_name, billing_address, billing_city, billing_state_province, billing_postal_code, billing_country, billing_phone_number, billing_fax, billing_tax1, billing_tax2, billing_tax3, shipping_cost)
				shpping_obj=ShippingInfo(first_name, last_name, company_name, shipping_address, shipping_city, shipping_state_province, shipping_postal_code, shipping_country, shipping_phone_number, shipping_fax, shipping_tax1, shipping_tax2, shipping_tax3, shipping_cost)
				customer.setBilling(billing_obj)
				customer.setShipping(shpping_obj)
				customer.setEmail(frappe.session.user)
				customer.setInstruction(" ")
				
				# Product Items

				for item in sale_order_items:
					customer.addItem(Item(item.item_name[:45],str(item.qty),item.item_code[:45].split(':')[0],str(item.rate)))

				data_key=''
				if data.get('data_key'):
					if data.get('data_key')!='':
						data_key=data.get('data_key')

				if data_key=='':
					vault = Vault(pan, expiry_date ,shipping_info.phone, frappe.session.user,frappe.session.user, "7")	
					VautObject=mpgHttpsPost(vault)
					VautObject.postRequest()
					valutResp = VautObject.getResponse()
					if valutResp.getComplete()=="true":
						data_key=valutResp.getDataKey()
						frappe.get_doc({
										"doctype":"Moneris Vault",
										"user_id":frappe.session.user,
										"data_key":valutResp.getDataKey(),
										"pan":valutResp.getResMaskedPan(),
										"expiry":valutResp.getResExpdate(),
										 "card_type":cardType(pan),
										}).insert(ignore_permissions=True)
						
				#Purchase 
				if data_key!='':
					purchase = PurchaseWithVault(data_key,order_id,amount,'1')
					purchase.setCustId(frappe.session.user)
					purchase.setCustInfo(customer)
					MSGObject=mpgHttpsPost(purchase)
					print(MSGObject)
					MSGObject.postRequest()
					# #Response
					resp = MSGObject.getResponse()
					if resp.getComplete()=="true":
						self.integration_request.db_set('status', 'Completed', update_modified=False)
						self.flags.status_changed_to = "Completed"
						return self.finalize_request(data.get('payment_request_id'),str(resp.getTransID()),str(resp.getTransDate()))
					else:
						return {"ReceiptId" : resp.getReceiptId(),
							"ReferenceNum" :resp.getReferenceNum(),
							"ResponseCod" : resp.getResponseCode(),
							"AuthCode" : resp.getAuthCode(),
							"TransTime" : resp.getTransTime(),
							"TransDate" : resp.getTransDate(),
							"TransType" : resp.getTransType(),
							"Complete" : resp.getComplete(),
							"status" : resp.getComplete(),
							"Message" : resp.getMessage(),
							"TransAmount" : resp.getTransAmount(),
							"CardType" : resp.getCardType(),
							"TransID" : resp.getTransID(),
							"TimedOut" : resp.getTimedOut(),
							"BankTotals" : resp.getBankTotals(),
							"Ticket" : resp.getTicket()}
				
				# purchase = Purchase(order_id, amount , pan, expiry_date, crypt)
				# purchase.setCustInfo(customer)
				# MSGObject=mpgHttpsPost(purchase)
				# MSGObject.postRequest()
				
				# #Response
				# resp = MSGObject.getResponse()
				# if resp.getComplete()=="true":
				# 	self.integration_request.db_set('status', 'Completed', update_modified=False)
				# 	self.flags.status_changed_to = "Completed"
				# 	return self.finalize_request(data.get('payment_request_id'),str(resp.getTransID()),str(resp.getTransDate()))
				# else:
				# 	return {"ReceiptId" : resp.getReceiptId(),
				# 		"ReferenceNum" :resp.getReferenceNum(),
				# 		"ResponseCod" : resp.getResponseCode(),
				# 		"AuthCode" : resp.getAuthCode(),
				# 		"TransTime" : resp.getTransTime(),
				# 		"TransDate" : resp.getTransDate(),
				# 		"TransType" : resp.getTransType(),
				# 		"Complete" : resp.getComplete(),
				# 		"status" : resp.getComplete(),
				# 		"Message" : resp.getMessage(),
				# 		"TransAmount" : resp.getTransAmount(),
				# 		"CardType" : resp.getCardType(),
				# 		"TransID" : resp.getTransID(),
				# 		"TimedOut" : resp.getTimedOut(),
				# 		"BankTotals" : resp.getBankTotals(),
				# 		"Ticket" : resp.getTicket()}
				# else:
				# 	return {
				# 		"redirect_to": "payment-failed",
				# 		"status": "failed"
				# 	}

			else:
				return {
						"redirect_to": "payment-failed",
						"status": "failed"
					}
		except Exception as e:
			print(e)
			return e


	

	def refund_payment(self,sales_invoice_id,total_amount):
		from moneris_payment.MonerisPaymentGateway  import Refund,CustInfo,mpgHttpsPost
		moneris_transaction=frappe.db.get_all("Moneris Transactions",  fields=['*'], filters={'sales_invoice_reference':sales_invoice_id},limit_page_length=1)
		if moneris_transaction:
			if len(moneris_transaction)>0:
				refund=Refund(moneris_transaction[0].sales_order_reference,str(total_amount),moneris_transaction[0].transaction_id,"7")
				MSGObject=mpgHttpsPost(refund)
				MSGObject.postRequest()
				resp = MSGObject.getResponse()
				respobj={"ReceiptId" : resp.getReceiptId(), 
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
				print(respobj)
	

	def finalize_request(self,payment_request_id,transactionid,transactiondate):
		redirect_to = self.data.get('redirect_to') or None
		redirect_message = self.data.get('redirect_message') or None
		status = self.integration_request.status

		if self.flags.status_changed_to == "Completed":
			if self.reference_doctype and self.reference_docname:
				custom_redirect_to = None
				try:
					custom_redirect_to = frappe.get_doc(self.reference_doctype,
						self.reference_docname).run_method("on_payment_authorized", self.flags.status_changed_to)
					sales_invoice=frappe.db.sql("""select PR.reference_name,PR.reference_doctype from `tabPayment Entry` PE inner join `tabPayment Entry Reference` PR on PE.name=PR.parent where PE.reference_no=%(payment_request_id)s""".format(),{'payment_request_id':payment_request_id}, as_dict=1)
					if sales_invoice:
						if len(sales_invoice)>0:
							payment_request=frappe.get_doc("Payment Request", payment_request_id)
							sale_order=frappe.get_doc("Sales Order",payment_request.reference_name)
							print('sales_invoice')
							print(sale_order.name)
							print(sales_invoice[0].reference_name)
							print(transactionid)
							print(transactiondate)
							frappe.get_doc({
								"doctype":"Moneris Transactions",
								"payment_request_reference":payment_request_id,
								"sales_order_reference":sale_order.name,
								"sales_invoice_reference":sales_invoice[0].reference_name,
								"transaction_id":transactionid,
								"transaction_date":transactiondate
								}).insert(ignore_permissions=True)

				except Exception as e:
					print(e)
					# frappe.log_error(frappe.get_traceback())

				if custom_redirect_to:
					redirect_to = custom_redirect_to

				redirect_url = 'payment-success'

			# if self.redirect_url:
			# 	redirect_url = self.redirect_url
			# 	redirect_to = None
		else:
			redirect_url = 'payment-failed'

		if redirect_to:
			redirect_url += '?' + urlencode({'redirect_to': redirect_to})
		if redirect_message:
			redirect_url += '&' + urlencode({'redirect_message': redirect_message})

		return {
			"redirect_to": redirect_url,
			"status": status
		}


def get_gateway_controller(doctype, docname):
	# reference_doc = frappe.get_doc(doctype, docname)
	# # gateway_controller = frappe.db.get_value("Payment Gateway", reference_doc.payment_gateway, "gateway_controller")
	# gateway_controller="moneris_settings"
	# return gateway_controller
	reference_doc = frappe.get_doc(doctype, docname)
	gateway_controller = frappe.db.get_value("Payment Gateway", reference_doc.payment_gateway, "gateway_controller")
	return gateway_controller



def cardType(number):
	number = str(number)
	cardtype = ""
	if len(number) == 15:
		if number[:2] == "34" or number[:2] == "37":
			cardtype = "American Express"
	if len(number) == 13:
		if number[:1] == "4":
			cardtype = "Visa"
	if len(number) == 16:
		if number[:4] == "6011":
			cardtype = "Discover"
		if int(number[:2]) >= 51 and int(number[:2]) <= 55:
			cardtype = "Master Card"
		if number[:1] == "4":
			cardtype = "Visa"
		if number[:4] == "3528" or number[:4] == "3529":
			cardtype = "JCB"
		if int(number[:3]) >= 353 and int(number[:3]) <= 359:
			cardtype = "JCB"
	if len(number) == 14:
		if number[:2] == "36":
			cardtype = "DINERS"
		if int(number[:3]) >= 300 and int(number[:3]) <= 305:
			cardtype = "DINERS"
	return cardtype