
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
from moneris_payment.MonerisPaymentGateway import *



@frappe.whitelist(allow_guest=True)
def make_payment():
	try:
		# Order Info

		order_id = "test_python-vls-"+datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
		amount = "10.00"
		pan = "4242424242424242"
		expiry_date = "1611"
		crypt = "7"

		customer=CustInfo()

		#Customer Billing Info and Shipping Info

		first_name="kartheek"
		last_name="periyasami"
		company_name="valiant"
		address="No:100,Lake View Estate Kundrathur main road , Porur"
		city="Chennai"
		state_province="Tamilnadu"
		postal_code="600116"
		country="Canada"
		phone_number="1234567890"
		fax=""
		tax1=""
		tax2=""
		tax3=""
		shipping_cost="1.00"
		billing_info=BillingInfo(first_name, last_name, company_name, address, city, state_province, postal_code, country, phone_number, fax, tax1, tax2, tax3, shipping_cost)
		shpping_info=ShippingInfo(first_name, last_name, company_name, address, city, state_province, postal_code, country, phone_number, fax, tax1, tax2, tax3, shipping_cost)
		customer.setBilling(billing_info)
		customer.setShipping(shpping_info)
		customer.setEmail("kartheek@valiantsystems.com")
		customer.setInstruction("Testing Payment Gateway")
		
		# Product Items

		
		customer.addItem(Item("Item1","1","IT-001","3.00"))
		customer.addItem(Item("Item2","1","IT-002","3.00"))
		customer.addItem(Item("Item3","1","IT-003","3.00"))

		#Purchase 

		purchase = Purchase(order_id, amount , pan, expiry_date, crypt)
		purchase.setCustInfo(customer)
		MSGObject=mpgHttpsPost(purchase)
		MSGObject.postRequest()
		
		#Response
		resp = MSGObject.getResponse()
		return {"ReceiptId" : resp.getReceiptId(),
				"ReferenceNum" :resp.getReferenceNum(),
				"ResponseCod" : resp.getResponseCode(),
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
	