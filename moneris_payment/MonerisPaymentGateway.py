from __future__ import unicode_literals
import frappe
import frappe.utils
import urllib2
import xml.sax
import socket
from frappe import _

PaymentSettings=frappe.get_doc('Moneris Settings','Moneris Settings')
country=PaymentSettings.country

class mpgHttpsPost:

	# __url = {'protocol' : 'https', 'port' : '443', 'file' : get }
	__agent = "Python API 1.6.1"
	__timeout = 40
	__requestData = ""
	__Response = None	 
	
	def __init__ (self, trxn):
		self.__trxn = trxn
		self.__status_check = False
		self.__storeId = PaymentSettings.store_id
		self.__apiToken = PaymentSettings.api_token
		self.__url = self._getUrl()
		self.__data = self.__toXml()
	
	def postRequest (self):	 
		# requestUrl = self.__url["protocol"] + "://" + self.__url["host"] + ":" + self.__url["port"] + "/" + self.__url["file"]
		requestUrl = self.__url
		try:
			#print ("Request URL is: [" + requestUrl + "]") 
			#print ("Data to send : " + self.__data)
			requestObj = urllib2.Request(requestUrl, self.__data)
			socket.setdefaulttimeout(self.__timeout)
			requestObj.add_header("USER-AGENT", self.__agent)
			responsePacket = urllib2.urlopen(requestObj)
			response = responsePacket.read()

			#print ("******\n Got response of: " + response + "\n******")
		except urllib2.HTTPError, e:
			response = self.__GlobalError(e)
		except urllib2.URLError, e:		     
			response = self.__GlobalError(e)
			
		self.__Response = mpgResponse(response)


	def postStatus (self):	
		self.__status_check = True
		self.__data = self.__toXml()
		self.postRequest()

	def getResponse(self):
		return self.__Response

	def __statusCheckXml(self):
		if self.__status_check == True:
			return "<status_check>true</status_check>"
		else:
			return ""

	def __toXml(self):
		request = "<request>" + "<store_id>" + self.__storeId + "</store_id>" + "<api_token>" + self.__apiToken + "</api_token>" + self.__statusCheckXml() + self.__trxn.toXml() + "</request>"
		print(request)
		return request

	def __GlobalError(self, error):
		if isinstance (error, urllib2.HTTPError):
			errorNumber = error.code
			errorMessage = "HttpError - " + str(errorNumber) 
		elif isinstance (error, urllib2.URLError):
			errorNumber, errorMessage = error.reason
			
		errorResponse = '<?xml version="1.0" standalone="yes"?><response><receipt><ReceiptId>Global Error Receipt</ReceiptId><ReferenceNum>null</ReferenceNum><ResponseCode>null</ResponseCode><AuthCode>null</AuthCode><TransTime>null</TransTime><TransDate>null</TransDate><TransType>null</TransType><Complete>false</Complete><Message>' + '[' + str(errorNumber) + '] ' + errorMessage + '</Message><TransAmount>null</TransAmount><CardType>null</CardType><TransID>null</TransID><TimedOut>null</TimedOut><BankTotals>null</BankTotals><Ticket>null</Ticket><CorporateCard>false</CorporateCard></receipt></response>'
		return errorResponse

	def _getUrl(self):
		if PaymentSettings.country=="Canada" and PaymentSettings.test_mode==1:
			return "https://esqa.moneris.com:443/gateway2/servlet/MpgRequest"
		elif PaymentSettings.country=="Canada"and PaymentSettings.test_mode==0:
			return "https://www3.moneris.com:443/gateway2/servlet/MpgRequest"
		elif PaymentSettings.country=="United States" and PaymentSettings.test_mode==1:
			return "https://esplusqa.moneris.com:443/gateway_us/servlet/MpgRequest"
		elif PaymentSettings.country=="United States" and PaymentSettings.test_mode==0:
			return "https://esplus.moneris.com:443/gateway_us/servlet/MpgRequest"
		return "" 


class mpgResponse (xml.sax.handler.ContentHandler):
	__rawResponse = ""
	
	def __init__(self, xmlResponse):
		self.__rawResponse = xmlResponse
		handler = self.__xmlResponseHandler()
		xml.sax.parseString(xmlResponse, handler)
		self.__map = handler.getMap()
		self.__ECRs = handler.getECRs()
		
	def getRawResponse(self):
		return self.__rawResponse
	
	class __xmlResponseHandler (xml.sax.handler.ContentHandler):
		__currTag = ""
		__map = None
		__buffer = ""
		__ECRs = None

		def __init__ (self):
			self.__currTag = ""
			self.__buffer = ""
			self.__map = {}
			self.__ECRs = {}
			self.__isBankTotal = False
			self.__inECR = False
	
		def startElement(self, name, attributes):			 
			self.__currTag = name   
			
			if name == 'BankTotals':
				self.__ECRs = {}
			
			if self.__inECR == True:
				if name == "Card":				
					self.__inECRCard = True
					self.__currECRCard = {}
				elif name != "Amount" and name != "Count" :
					self.__currTransType = name
						
			if name == "BankTotals":
				self.__isBankTotal = True
			elif name == "ECR":
				self.__inECR = True
				self.__inECRCard = False
				self.__currECR = {}
				self.__currECR["CardTypes"] = []
				self.__currECR["Cards"] = {}
		
		def characters (self,ch):
			self.__buffer = self.__buffer + ch
			
		
		def endElement(self, name):	
				
			if name == self.__currTag:
				if self.__inECR :
					if self.__inECRCard :									   
						if name == "CardType" : 
							self.__currECR["CardTypes"].append(self.__buffer)
							self.__currECRCard[name] = self.__buffer
							self.__currECRCardType = self.__buffer
						else : 
							self.__currECRCard[self.__currTransType + name] = self.__buffer

					else:	   
						self.__currECR[name] = self.__buffer
				else:
					self.__map[name] = self.__buffer
					
			if name == "BankTotals":			
				self.__isBankTotal = False
			elif name == "ECR":
				self.__inECR = False
				self.__ECRs[self.__currECR["term_id"]] = self.__currECR
			else:
				if name == "Card" :														     
					self.__currECR["Cards"][self.__currECRCardType] = self.__currECRCard
					self.__inECRCard = False
					
			self.__buffer = ""
					
		def getMap(self):
			return self.__map
		
		def getECRs(self):
			return self.__ECRs
	
	def __getGenericProp(self, mapping, prop):
		propVal = ""
		try:
			propVal = mapping[prop]
		except:
			propVal = ""
		return propVal

	def __getProp(self, prop):
		return self.__getGenericProp(self.__map, prop)

	def __getECRProp(self, ecr, prop):
		return self.__getGenericProp(self.__ECRs[ecr], prop)

	def __getCardTypeProp(self, ecr, cardType, prop):
		return self.__ECRs[ecr]["Cards"][cardType][prop]

	def getReceiptId (self):
		return self.__getProp("ReceiptId")

	def getReferenceNum (self):
		return self.__getProp("ReferenceNum")

	def getResponseCode (self):
		return self.__getProp("ResponseCode")

	def getAuthCode (self):
		return self.__getProp("AuthCode")

	def getTransTime (self):
		return self.__getProp("TransTime")

	def getTransDate (self):
		return self.__getProp("TransDate")

	def getTransType (self):
		return self.__getProp("TransType")

	def getComplete (self):
		return self.__getProp("Complete")

	def getMessage (self):
		return self.__getProp("Message")

	def getTransAmount (self):
		return self.__getProp("TransAmount")

	def getCardType (self):
		return self.__getProp("CardType")

	def getTransID (self):
		return self.__getProp("TransID")

	def getTimedOut (self):
		return self.__getProp("TimedOut")

	def getBankTotals (self):
		return self.__getProp("BankTotals")

	def getTicket (self):
		return self.__getProp("Ticket")
		
	def getMaskedPan (self):
		return self.__getProp("MaskedPan")

	def getCorporateCard (self):
		return self.__getProp("CorporateCard")
		
	def getAvsResultCode (self):
		return self.__getProp("AvsResultCode")
		
	def getCvdResultCode (self):
		return self.__getProp("CvdResultCode")

	def getCavvResultCode (self):
		return self.__getProp("CavvResultCode")

	def getStatusCode (self):
		return self.__getProp("status_code")

	def getStatusMessage (self):
		return self.__getProp("status_message")

	def getRecurSuccess (self):
		return self.__getProp("RecurSuccess")

	def getRecurUpdateSuccess (self):
		return self.__getProp("RecurUpdateSuccess")

	def getNextRecurDate (self):
		return self.__getProp("NextRecurDate")

	def getRecurEndDate (self):
		return self.__getProp("RecurEndDate")
		
	def getECRs (self):
		return self.__ECRs
	
	def getCardTypes (self, ecr):
		return self.__getECRProp(ecr, "CardTypes")
		
	def getPurchaseCount (self, ecr, cardType):
		return self.__getCardTypeProp(ecr, cardType, "PurchaseCount")
		
	def getPurchaseAmount (self, ecr, cardType):
		return self.__getCardTypeProp(ecr, cardType, "PurchaseAmount")

	def getRefundCount (self, ecr, cardType):
		return self.__getCardTypeProp(ecr, cardType, "RefundCount")
		
	def getRefundAmount (self, ecr, cardType):
		return self.__getCardTypeProp(ecr, cardType, "RefundAmount")

	def getCorrectionCount (self, ecr, cardType):
		return self.__getCardTypeProp(ecr, cardType, "CorrectionCount")
		
	def getCorrectionAmount (self, ecr, cardType):
		return self.__getCardTypeProp(ecr, cardType, "CorrectionAmount")

class mpgTransaction:
	def __init__(self):
		self._Request = ""
		self._tags = {}
		self._order
	
	def toXml(self):
		requestXml = "<" + self._Request + ">"
		for index, tag in enumerate(self._order):
			value = self._tags[tag]		 
			if isinstance(value, basestring):
				requestXml = requestXml + "<" + tag + ">" + value + "</" + tag + ">"
			elif isinstance(value, mpgTransaction):
				requestXml = requestXml + value.toXml()
			elif isinstance(value, list):
				for item in value:				
					requestXml = requestXml + item.toXml()
			
		requestXml = requestXml + "</" + self._Request + ">"

		return requestXml

class Purchase(mpgTransaction):
	def __init__(self, order_id, amount, pan, expdate, crypt_type):
		if country=="Canada":
			self._Request = "purchase"
		else:
			self._Request = "us_purchase"
		self._tags = {"order_id" : order_id, "amount" : amount, "pan" : pan, "expdate" : expdate, "crypt_type" : crypt_type, "cvd": None, "avs": None}
		self._order = ["order_id", "amount", "pan", "expdate", "crypt_type"]	    

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")
	
	def setCvdInfo (self, cvdInfo):
		self._tags["cvd"] = cvdInfo
		self._order.append("cvd")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setCustInfo (self, custInfo):
		self._tags["CustInfo"] = custInfo
		self._order.append("CustInfo")

	def setRecur (self, recur):
		self._tags["recur"] = recur
		self._order.append("recur")

	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class Preauth(mpgTransaction):
	def __init__(self, order_id, amount, pan, expdate, crypt_type):
		if country=="Canada":
			self._Request = "preauth"
		else:
			self._Request = "us_preauth"
		self._tags = {"order_id" : order_id, "amount" : amount, "pan" : pan, "expdate" : expdate, "crypt_type" : crypt_type, "cvd": None, "avs": None}
		self._order = ["order_id", "amount", "pan", "expdate", "crypt_type"]

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")
	
	def setCvdInfo (self, cvdInfo):
		self._tags["cvd"] = cvdInfo
		self._order.append("cvd")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setCustInfo (self, custInfo):
		self._tags["CustInfo"] = custInfo
		self._order.append("CustInfo")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class PurchaseCorrection(mpgTransaction):
	def __init__(self, order_id, txn_number, crypt_type):
		if country=="Canada":
			self._Request = "purchasecorrection"
		else:
			self._Request = "us_purchasecorrection"
		self._tags = {"order_id" : order_id, "txn_number" : txn_number, "crypt_type" : crypt_type}
		self._order = ["order_id", "txn_number", "crypt_type"]

class Reauth(mpgTransaction):
	def __init__(self, order_id, amount, orig_order_id, txn_number, crypt_type):
		if country=="Canada":
			self._Request = "reauth"
		else:
			self._Request = "us_reauth"
		self._tags = {"order_id" : order_id, "amount" : amount, "orig_order_id" : orig_order_id, "txn_number" : txn_number, "crypt_type" : crypt_type}
		self._order = ["order_id", "amount", "orig_order_id", "txn_number", "crypt_type"]

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")
		
class Completion(mpgTransaction):
	def __init__(self, order_id, comp_amount, txn_number, crypt_type):
		if country=="Canada":
			self._Request = "completion"
		else:
			self._Request = "us_completion"
		self._tags = {"order_id" : order_id, "comp_amount" : comp_amount, "txn_number" : txn_number, "crypt_type" : crypt_type}
		self._order = ["order_id", "comp_amount", "txn_number", "crypt_type"]

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")
		
	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class Refund(mpgTransaction):
	def __init__(self, order_id, amount, txn_number, crypt_type):
		if country=="Canada":
			self._Request = "refund"
		else:
			self._Request = "us_refund"
		self._tags = {"order_id" : order_id, "amount" : amount, "txn_number" : txn_number, "crypt_type" : crypt_type}
		self._order = ["order_id", "amount", "txn_number", "crypt_type"]

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class IndependentRefund(mpgTransaction):
	def __init__(self, order_id, amount, pan, expdate, crypt_type):
		if country=="Canada":
			self._Request = "ind_refund"
		else:
			self._Request = "us_ind_refund"
		self._tags = {"order_id" : order_id, "amount" : amount, "pan" : pan, "expdate" : expdate, "crypt_type" : crypt_type}
		self._order = ["order_id", "amount", "pan", "expdate", "crypt_type"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class CardVerification(mpgTransaction):
	def __init__(self, order_id, pan, expdate):
		if country=="Canada":
			self._Request = "card_verification"
		else:
			self._Request = "us_card_verification"
		self._tags = {"order_id" : order_id, "pan" : pan, "expdate" : expdate,"cvd_info": None, "avs_info" : None}
		self._order = ["order_id", "pan", "expdate", "cvd_info", "avs_info"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

	def setCvdInfo (self, cvdInfo):
		self._tags["cvd"] = cvdInfo
		self._order.append("cvd")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")


#Track 2 Transactions
class Track2Purchase(mpgTransaction):
	def __init__(self, order_id, amount, track2, pan, expdate, pos_code):
		if country=="Canada":
			self._Request = "track2_purchase"
		else:
			self._Request = "us_track2_purchase"
		self._tags = {"order_id" : order_id, "amount" : amount, "track2" : track2, "pan" : pan, "expdate" : expdate, "pos_code" : pos_code, "avs" : None}
		self._order = ["order_id", "amount", "track2", "pan", "expdate", "pos_code"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class Track2Preauth(mpgTransaction):
	def __init__(self, order_id, amount, track2, pan, expdate, pos_code):
		if country=="Canada":
			self._Request = "track2_preauth"
		else:
			self._Request = "us_track2_preauth"
		self._tags = {"order_id" : order_id, "amount" : amount, "track2" : track2, "pan" : pan, "expdate" : expdate, "pos_code" : pos_code, "avs" : None}
		self._order = ["order_id", "amount", "track2", "pan", "expdate", "pos_code"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class Track2Completion(mpgTransaction):
	def __init__(self, order_id, comp_amount, txn_number, pos_code):
		if country=="Canada":
			self._Request = "track2_completion"
		else:
			self._Request = "us_track2_completion"
		self._tags = {"order_id" : order_id, "comp_amount" : comp_amount, "txn_number" : txn_number, "pos_code" : pos_code}
		self._order = ["order_id", "comp_amount", "txn_number", "pos_code"]
		
	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")
		
class Track2PurchaseCorrection(mpgTransaction):
	def __init__(self, order_id, txn_number):
		self._Request = "us_track2_purchasecorrection"
		self._tags = {"order_id" : order_id, "txn_number" : txn_number}
		self._order = ["order_id", "txn_number"]
		
class Track2Forcepost(mpgTransaction):
	def __init__(self, order_id, amount, track2, pan, expdate, pos_code, auth_code):
		self._Request = "us_track2_forcepost"
		self._tags = {"order_id" : order_id, "amount" : amount, "track2" : track2, "pan" : pan, "expdate" : expdate, "pos_code" : pos_code, "auth_code" : auth_code}
		self._order = ["order_id", "amount", "track2", "pan", "expdate", "pos_code", "auth_code"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class Track2Refund(mpgTransaction):
	def __init__(self, order_id, amount, txn_number):
		self._Request = "us_track2_refund"
		self._tags = {"order_id" : order_id, "amount": amount, "txn_number" : txn_number}
		self._order = ["order_id", "amount", "txn_number"]
		
	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")		
		
class Track2IndependentRefund(mpgTransaction):
	def __init__(self, order_id, amount, track2, pan, expdate, pos_code):
		self._Request = "us_track2_ind_refund"
		self._tags = {"order_id" : order_id, "amount" : amount, "track2" : track2, "pan" : pan, "expdate" : expdate, "pos_code" : pos_code}
		self._order = ["order_id", "amount", "track2", "pan", "expdate", "pos_code", ]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

#Cavv Transactions
class CavvPurchase(mpgTransaction):
	def __init__(self, order_id, amount, pan, expdate, cavv):
		self._Request = "us_cavv_purchase"
		self._tags = {"order_id" : order_id, "amount" : amount, "pan" : pan, "expdate" : expdate, "cavv" : cavv, "cvd": None, "avs": None}
		self._order = ["order_id", "amount", "pan", "expdate", "cavv"]	    

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")
	
	def setCvdInfo (self, cvdInfo):
		self._tags["cvd"] = cvdInfo
		self._order.append("cvd")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setCustInfo (self, custInfo):
		self._tags["CustInfo"] = custInfo
		self._order.append("CustInfo")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class CavvPreauth(mpgTransaction):
	def __init__(self, order_id, amount, pan, expdate, cavv):
		self._Request = "us_cavv_preauth"
		self._tags = {"order_id" : order_id, "amount" : amount, "pan" : pan, "expdate" : expdate, "cavv" : cavv, "cvd": None, "avs": None}
		self._order = ["order_id", "amount", "pan", "expdate", "cavv"]	    

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")
	
	def setCvdInfo (self, cvdInfo):
		self._tags["cvd"] = cvdInfo
		self._order.append("cvd")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setCustInfo (self, custInfo):
		self._tags["CustInfo"] = custInfo
		self._order.append("CustInfo")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

#ACH transactions
class ACHDebit(mpgTransaction):
	def __init__(self, order_id, amount, ach_info):
		self._Request = "us_ach_debit"
		self._tags = {"order_id" : order_id, "amount" : amount, "cust_info" : None, "ach_info" : ach_info}
		self._order = ["order_id", "amount", "cust_info", "ach_info"]

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")
		
	def setCustInfo (self, cust_info):
		self._tags["cust_info"] = cust_info
		self._order.append("cust_info")

	def setRecur (self, recur):
		self._tags["recur"] = recur
		self._order.append("recur")

class ACHReversal(mpgTransaction):
	def __init__(self, order_id, txn_number):
		self._Request = "us_ach_reversal"
		self._tags = {"order_id" : order_id, "txn_number" : txn_number}
		self._order = ["order_id", "txn_number"]

class ACHCredit(mpgTransaction):
	def __init__(self, order_id, amount, ach_info):
		self._Request = "us_ach_credit"
		self._tags = {"order_id" : order_id, "amount" : amount, "ach_info" : ach_info}
		self._order = ["order_id", "amount", "ach_info"]

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

class ACHFiEnquiry(mpgTransaction):
	def __init__(self, routing_num):
		self._Request = "us_ach_fi_enquiry"
		self._tags = {"routing_num" : routing_num}
		self._order = ["routing_num"]

class ACHInfo(mpgTransaction):
	__checkFromReader = False
	def __init__(self, *vargs):
		self._Request = "ach_info"
		if len(list(vargs)) == 4: 
			self.__checkFromReader = False	
			self._tags = {"sec" : vargs[0], "routing_num" : vargs[1], "account_num" : vargs[2], "account_type" : vargs[3]}
			self._order = ["sec", "routing_num", "account_num", "account_type"]
		elif len(list(vargs)) == 6:
			self.__checkFromReader = True	
			self._tags = {"sec" : vargs[0], "micr" : vargs[1], "dl_num" : vargs[2], "magstripe" : vargs[3], "image_front" : vargs[4], "image_back" : vargs[5]}
			self._order = ["sec", "micr", "dl_num", "magstripe", "image_front", "image_back"]
		else:
			self.tags = {}
			self._order = []

	def setCustFirstName(self, cust_first_name):
		self._tags["cust_first_name"] = cust_first_name
		self._order.append("cust_first_name")

	def setCustLastName(self, cust_last_name):
		self._tags["cust_last_name"] = cust_last_name
		self._order.append("cust_last_name")

	def setCustAddress1(self, cust_address1):
		self._tags["cust_address1"] = cust_address1
		self._order.append("cust_address1")

	def setCustAddress2(self, cust_address2):
		self._tags["cust_address2"] = cust_address2
		self._order.append("cust_address2")

	def setCustCity(self, cust_city):
		self._tags["cust_city"] = cust_city
		self._order.append("cust_city")

	def setCustState(self, cust_state):
		self._tags["cust_state"] = cust_state
		self._order.append("cust_state")

	def setCustZip(self, cust_zip):
		self._tags["cust_zip"] = cust_zip
		self._order.append("cust_zip")

	def setCheckNum(self, check_num):
		self._tags["check_num"] = check_num
		self._order.append("check_num")

	def setMicr(self, micr):
		self._tags["micr"] = micr
		self._order.append("micr")
		
#Contactless 
class ContactlessPurchase(mpgTransaction):
	def __init__(self, order_id, amount, track2, pan, expdate, pos_code):
		self._Request = "us_contactless_purchase"
		self._tags = {"order_id" : order_id, "amount" : amount, "track2" : track2, "pan" : pan, "expdate" : expdate, "pos_code" : pos_code}
		self._order = ["order_id", "amount", "track2", "pan", "expdate", "pos_code"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class ContactlessRefund(mpgTransaction):
	def __init__(self, order_id, amount, track2, pos_code, txn_number):
		self._Request = "us_contactless_refund"
		self._tags = {"order_id" : order_id, "amount" : amount, "track2" : track2, "pos_code" : pos_code, "txn_number" : txn_number}
		self._order = ["order_id", "amount", "track2", "pos_code", "txn_number"]

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")
		
class ContactlessPurchaseCorrection(mpgTransaction):
	def __init__(self, order_id, txn_number):
		self._Request = "us_contactless_purchasecorrection"
		self._tags = {"order_id" : order_id, "txn_number" : txn_number}
		self._order = ["order_id", "txn_number"]

#Encrypted Track2
class EncTrack2Purchase(mpgTransaction):
	def __init__(self, order_id, amount, enc_track2, pos_code, device_type):
		self._Request = "us_enc_track2_purchase"
		self._tags = {"order_id" : order_id, "amount" : amount, "enc_track2" : enc_track2, "pos_code" : pos_code, "device_type" : device_type, "avs": None}
		self._order = ["order_id", "amount", "enc_track2", "pos_code", "device_type"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")
		
	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")
		
class EncTrack2Preauth(mpgTransaction):
	def __init__(self, order_id, amount, enc_track2, pos_code, device_type):
		self._Request = "us_enc_track2_preauth"
		self._tags = {"order_id" : order_id, "amount" : amount, "enc_track2" : enc_track2, "pos_code" : pos_code, "device_type" : device_type, "avs": None}
		self._order = ["order_id", "amount", "enc_track2", "pos_code", "device_type"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")
		
	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")
		
	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")
		
class EncTrack2IndependentRefund(mpgTransaction):
	def __init__(self, order_id, amount, enc_track2, pos_code, device_type):
		self._Request = "us_enc_track2_ind_refund"
		self._tags = {"order_id" : order_id, "amount" : amount, "enc_track2" : enc_track2, "pos_code" : pos_code, "device_type" : device_type}
		self._order = ["order_id", "amount", "enc_track2", "pos_code", "device_type"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")
		
class EncTrack2Forcepost(mpgTransaction):
	def __init__(self, order_id, amount, enc_track2, pos_code, device_type, auth_code):
		self._Request = "us_enc_track2_forcepost"
		self._tags = {"order_id" : order_id, "amount" : amount, "enc_track2" : enc_track2, "pos_code" : pos_code, "device_type" : device_type, "auth_code" : auth_code}
		self._order = ["order_id", "amount", "enc_track2", "pos_code", "device_type", "auth_code"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")
		
#Encrypted Non eCom
class EncPurchase(mpgTransaction):
	def __init__(self, order_id, amount, enc_track2, crypt_type, device_type):
		self._Request = "us_enc_purchase"
		self._tags = {"order_id" : order_id, "amount" : amount, "enc_track2" : enc_track2, "crypt_type" : crypt_type, "device_type" : device_type}
		self._order = ["order_id", "amount", "enc_track2", "crypt_type", "device_type"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setCvdInfo (self, cvdInfo):
		self._tags["cvd"] = cvdInfo
		self._order.append("cvd")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setCustInfo (self, custInfo):
		self._tags["CustInfo"] = custInfo
		self._order.append("CustInfo")

	def setRecur (self, recur):
		self._tags["recur"] = recur
		self._order.append("recur")

	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class EncPreauth(mpgTransaction):
	def __init__(self, order_id, amount, enc_track2, crypt_type, device_type):
		self._Request = "us_enc_preauth"
		self._tags = {"order_id" : order_id, "amount" : amount, "enc_track2" : enc_track2, "crypt_type" : crypt_type, "device_type" : device_type}
		self._order = ["order_id", "amount", "enc_track2", "crypt_type", "device_type"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setCvdInfo (self, cvdInfo):
		self._tags["cvd"] = cvdInfo
		self._order.append("cvd")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

	def setCustInfo (self, custInfo):
		self._tags["CustInfo"] = custInfo
		self._order.append("CustInfo")

	def setCommcardInvoice (self, commcard_invoice):
		self._tags["commcard_invoice"] = commcard_invoice
		self._order.append("commcard_invoice")

	def setCommcardTaxAmount (self, commcard_tax_amount):
		self._tags["commcard_tax_amount"] = commcard_tax_amount
		self._order.append("commcard_tax_amount")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class EncIndRefund(mpgTransaction):
	def __init__(self, order_id, amount, enc_track2, crypt_type, device_type):
		self._Request = "us_enc_ind_refund"
		self._tags = {"order_id" : order_id, "amount" : amount, "enc_track2" : enc_track2, "crypt_type" : crypt_type, "device_type" : device_type}
		self._order = ["order_id", "amount", "enc_track2", "crypt_type", "device_type"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class EncForcePost(mpgTransaction):
	def __init__(self, order_id, amount, enc_track2, auth_code, crypt_type, device_type):
		self._Request = "us_enc_forcepost"
		self._tags = {"order_id" : order_id, "amount" : amount, "enc_track2" : enc_track2, "auth_code" : auth_code, "crypt_type" : crypt_type, "device_type" : device_type}
		self._order = ["order_id", "amount", "enc_track2", "auth_code", "crypt_type", "device_type"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

class EncCardVerification(mpgTransaction):
	def __init__(self, order_id, enc_track2, device_type, avs):
		self._Request = "us_enc_card_verification"
		self._tags = {"order_id" : order_id, "enc_track2" : enc_track2, "device_type" : device_type, "avs_info" : avs}
		self._order = ["order_id", "enc_track2", "device_type", "avs_info"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setDynamicDescriptor (self, dynamic_descriptor):
		self._tags["dynamic_descriptor"] = dynamic_descriptor
		self._order.append("dynamic_descriptor")

	def setCvdInfo (self, cvdInfo):
		self._tags["cvd"] = cvdInfo
		self._order.append("cvd")

	def setAvsInfo (self, avsInfo):
		self._tags["avs"] = avsInfo
		self._order.append("avs")

#Pinless Debit Transactions
class PinlessDebitPurchase(mpgTransaction):
	def __init__(self, order_id, amount, pan, expdate, presentation_type, intended_use, p_account_number):
		self._Request = "us_pinless_debit_purchase"
		self._tags = {"order_id" : order_id, "amount" : amount, "pan" : pan, "expdate" : expdate, "presentation_type" : presentation_type, "intended_use" : intended_use, "p_account_number" : p_account_number}
		self._order = ["order_id", "amount", "pan", "expdate", "presentation_type", "intended_use", "p_account_number"]
		
	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setCustInfo (self, custInfo):
		self._tags["CustInfo"] = custInfo
		self._order.append("CustInfo")

	def setRecur (self, recur):
		self._tags["recur"] = recur
		self._order.append("recur")

class PinlessDebitRefund(mpgTransaction):
	def __init__(self, order_id, amount, txn_number):
		if country=="Canada":
			self._Request = "pinless_debit_refund"
		else:
			self._Request = "us_pinless_debit_refund"
		self._tags = {"order_id" : order_id, "amount" : amount, "txn_number" : txn_number}
		self._order = ["order_id", "amount", "txn_number"]

#Administrative Transactions
class OpenTotals(mpgTransaction):
	def __init__(self, ecr_number):
		if country=="Canada":
			self._Request = "opentotals"
		else:
			self._Request = "us_opentotals"
		self._tags = {"ecr_number" : ecr_number } 
		self._order = ["ecr_number"]

class BatchClose(mpgTransaction):
	def __init__(self, ecr_number):
		if country=="Canada":
			self._Request = "batchclose"
		else:
			self._Request = "us_batchclose"
		self._tags = {"ecr_number" : ecr_number } 
		self._order = ["ecr_number"]

#Recuring Transactions
class Recur(mpgTransaction):
	def __init__(self, recur_unit, start_now, start_date, num_recurs, period, recur_amount):
		self._Request = "recur"
		self._tags = {"recur_unit" : recur_unit, "start_now" : start_now, "start_date" : start_date, "num_recurs" : num_recurs, "period" : period, "recur_amount" : recur_amount}
		self._order = ["recur_unit", "start_now", "start_date", "num_recurs", "period", "recur_amount"]
	
class RecurUpdate(mpgTransaction):
	def __init__(self, order_id):
		if country=="Canada":
			self._Request = "recur_update"
		else:
			self._Request = "us_recur_update"
		self._tags = {"order_id" : order_id } 
		self._order = ["order_id"]

	def setCustId (self, cust_id):
		self._tags["cust_id"] = cust_id
		self._order.append("cust_id")

	def setRecurAmount (self, recur_amount):
		self._tags["recur_amount"] = recur_amount
		self._order.append("recur_amount")

	def setPan (self, pan):
		self._tags["pan"] = pan
		self._order.append("pan")

	def setExpDate (self, expdate):
		self._tags["expdate"] = expdate
		self._order.append("expdate")

	def setAddNumRecurs (self, add_num_recurs):
		self._tags["add_num_recurs"] = add_num_recurs
		self._order.append("add_num_recurs")

	def setTotalNumRecurs (self, total_num_recurs):
		self._tags["total_num_recurs"] = total_num_recurs
		self._order.append("total_num_recurs")

	def setHold (self, hold):
		self._tags["hold"] = hold
		self._order.append("hold")
		
	def setTerminate (self, terminate):
		self._tags["terminate"] = terminate
		self._order.append("terminate")
	
	def setAvsStreetNumber(self, avs_street_number):
		self._tags["avs_street_num"] = avs_street_number
		self._order.append("avs_street_num")
		
	def setAvsStreetName(self, avs_street_name):
		self._tags["avs_street_name"] = avs_street_name
		self._order.append("avs_street_name")
	
	def setAvsZipcode(self, avs_zipcode):
		self._tags["avs_zipcode"] = avs_zipcode
		self._order.append("avs_zipcode")
		
	def setPAccountNumber (self, p_account_number):
		self._tags["p_account_number"] = p_account_number
		self._order.append("p_account_number")
	
	def setPresentationType (self, presentation_type):
		self._tags["presentation_type"] = presentation_type
		self._order.append("presentation_type")

#EFraud
class CvdInfo(mpgTransaction):
	def __init__(self, cvd_indicator, cvd_value):
		self._Request = "cvd_info"
		self._tags = {"cvd_indicator" : cvd_indicator, "cvd_value" : cvd_value}
		self._order = ["cvd_indicator", "cvd_value"]

class AvsInfo(mpgTransaction):
	def __init__(self, avs_street_number, avs_street_name, avs_zipcode) :
		self._Request = "avs_info"
		self._tags = {"avs_street_number" : avs_street_number, "avs_street_name" : avs_street_name, "avs_zipcode" : avs_zipcode}
		self._order = ["avs_street_number", "avs_street_name", "avs_zipcode"]

#Cust Info		
class CustInfo(mpgTransaction):
	def __init__(self) :
		self._Request = "cust_info"
		self._tags = {"billing" : None, "shipping" : None, "email" : "", "instructions": "", "item" : []}
		self._order = []

	def setBilling(self, billingInfo):
		self._tags["billing"] = billingInfo
		self._order.append("billing")

	def setShipping(self, shippingInfo):
		self._tags["shipping"] = shippingInfo	   
		self._order.append("shipping")
		
	def setEmail(self, email):
		self._tags["email"] = email
		self._order.append("email")
		
	def setInstruction(self, instructions):
		self._tags["instructions"] = instructions
		self._order.append("instructions")
	
	def addItem(self, item):
		itm = self._tags["item"]
		itm.append(item)
		self._tags["item"] = itm
		if "item" not in self._order:
			self._order.append("item")
		
class BillingInfo(mpgTransaction):
	def __init__(self, first_name, last_name, company_name, address, city, province, postal_code, country, phone_number, fax, tax1, tax2, tax3, shipping_cost):
		self._Request = "billing"
		self._tags = {}
		self._tags["first_name"] = first_name
		self._tags["last_name"] = last_name
		self._tags["company_name"] = company_name
		self._tags["address"] = address
		self._tags["city"] = city
		self._tags["province"] = province
		self._tags["postal_code"] = postal_code
		self._tags["country"] = country
		self._tags["phone_number"] = phone_number
		self._tags["fax"] = fax
		self._tags["tax1"] = tax1
		self._tags["tax2"] = tax2
		self._tags["tax3"] = tax3
		self._tags["shipping_cost"] = shipping_cost
		self._order = ["first_name", "last_name", "company_name", "address", "city", "province", "postal_code", "country", "phone_number", "fax", "tax1", "tax2", "tax3", "shipping_cost"]

	def setFirstName (self, first_name):
		self._tags["first_name"] = first_name

	def setLastName (self, last_name):
		self._tags["last_name"] = last_name

	def setCompanyName (self, company_name):
		self._tags["company_name"] = company_name

	def setAddress (self, address):
		self._tags["address"] = address

	def setCity (self, city):
		self._tags["city"] = city

	def setProvince (self, province):
		self._tags["province"] = province

	def setPostalCode (self, postal_code):
		self._tags["postal_code"] = postal_code

	def setCountry (self, country):
		self._tags["country"] = country

	def setPhoneNumber (self, phone_number):
		self._tags["phone_number"] = phone_number

	def setFax (self, fax):
		self._tags["fax"] = fax

	def setTax1 (self, tax1):
		self._tags["tax1"] = tax1

	def setTax2 (self, tax2):
		self._tags["tax2"] = tax2

	def setTax3 (self, tax3):
		self._tags["tax3"] = tax3

	def setShippingCost (self, shipping_cost):
		self._tags["shipping_cost"] = shipping_cost

class ShippingInfo(mpgTransaction):
	def __init__(self, first_name, last_name, company_name, address, city, province, postal_code, country, phone_number, fax, tax1, tax2, tax3, shipping_cost):
		self._Request = "shipping"
		self._tags = {}	 
		self._tags["first_name"] = first_name
		self._tags["last_name"] = last_name
		self._tags["company_name"] = company_name
		self._tags["address"] = address
		self._tags["city"] = city
		self._tags["province"] = province
		self._tags["postal_code"] = postal_code
		self._tags["country"] = country
		self._tags["phone_number"] = phone_number
		self._tags["fax"] = fax
		self._tags["tax1"] = tax1
		self._tags["tax2"] = tax2
		self._tags["tax3"] = tax3
		self._tags["shipping_cost"] = shipping_cost
		self._order = ["first_name", "last_name", "company_name", "address", "city", "province", "postal_code", "country", "phone_number", "fax", "tax1", "tax2", "tax3", "shipping_cost"]

	def setFirstName (self, first_name):
		self._tags["first_name"] = first_name

	def setLastName (self, last_name):
		self._tags["last_name"] = last_name

	def setCompanyName (self, company_name):
		self._tags["company_name"] = company_name

	def setAddress (self, address):
		self._tags["address"] = address

	def setCity (self, city):
		self._tags["city"] = city

	def setProvince (self, province):
		self._tags["province"] = province

	def setPostalCode (self, postal_code):
		self._tags["postal_code"] = postal_code

	def setCountry (self, country):
		self._tags["country"] = country

	def setPhoneNumber (self, phone_number):
		self._tags["phone_number"] = phone_number

	def setFax (self, fax):
		self._tags["fax"] = fax

	def setTax1 (self, tax1):
		self._tags["tax1"] = tax1

	def setTax2 (self, tax2):
		self._tags["tax2"] = tax2

	def setTax3 (self, tax3):
		self._tags["tax3"] = tax3

	def setShippingCost (self, shipping_cost):
		self._tags["shipping_cost"] = shipping_cost

		
class Item(mpgTransaction):
	def __init__(self, itemName, quantity, product_code, extended_amount) :
		self._Request = "item"
		self._tags = {"name" : itemName, "quantity" : quantity, "product_code" : product_code, "extended_amount" : extended_amount}
		self._order = ["name", "quantity", "product_code", "extended_amount"]

	def setitemName (self, itemName):
		self._tags["itemName"] = itemName

	def setquantity (self, quantity):
		self._tags["quantity"] = quantity

	def setproduct_code (self, product_code):
		self._tags["product_code"] = product_code

	def setextended_amount (self, extended_amount):
		self._tags["extended_amount"] = extended_amount