$(function() {
 
    
        $("input[type='radio'][name='paymenttype']").change(function(){
          
    if($(this).val()=="exist")
    {
    $("#existing-cards").show();
    $("#payment-form").hide();        
    }
    if($(this).val()=="new")
    {
    $("#existing-cards").hide();
    $("#payment-form").show();        
    }
  });
        $(".cardinfo").click(function(){
            $(".submit-loading").show();
            var data_key=$(this).parent().attr("data-key");
            moneris_make_payment_withvault(data_key);
        });
     
    var cardNumber = $('#card-number');
    var cardNumberField = $('#card-number-field');
    var CVV = $("#card-cvv");
    var confirmButton = $('#confirm-purchase');

    // Use the payform library to format and validate
    // the payment fields.

    cardNumber.payform('formatCardNumber');
    CVV.payform('formatCardCVC');


    cardNumber.keyup(function() {

       
        if ($.payform.validateCardNumber(cardNumber.val()) == false) {
            cardNumberField.addClass('has-error');
        } else {
            cardNumberField.removeClass('has-error');
            cardNumberField.addClass('has-success');
        }

        
    });

    confirmButton.click(function(e) {

        e.preventDefault();

        var isCardValid = $.payform.validateCardNumber(cardNumber.val());
        var isCvvValid = $.payform.validateCardCVC(CVV.val());
        var isExpValid=validate_expire();
 $(".error").html("");
        if (!isCardValid) {
           $(".error").append("<p>Invalid Card</p>")
        } if (!isCvvValid) {
           $(".error").append("<p>Invalid CVV</p>")
        } 
        if (!isExpValid) {
           $(".error").append("<p>Invalid Expire Date</p>")
        } 
        if(isCardValid && isCvvValid && isExpValid) {
            confirmButton.attr("disabled","disabled")
            moneris_make_payment();

            }
        if(!isCardValid || !isCvvValid || !isExpValid)
        {

            $(".error").show();
            setTimeout(function(){  $(".error").hide(); }, 3000);

        }
    });
  
});
  function validate_expire()
    {
        var minMonth = new Date().getMonth() + 1;
          var minYear = new Date().getFullYear();
          var month = parseInt($("#card-exp-month").val(), 10);
          var year = parseInt($("#card-exp-year option:selected").text(), 10);

            return (!month || !year || year > minYear || (year === minYear && month >= minMonth));
               
    }
    function moneris_make_payment()
    {
        $(".submit-loading").show();
        var monerisdata={
                                    payment_request_id:$("#PaymentRequestId").val(),
                                    card_number:$("#card-number").val(),
                                    card_expire:$("#card-exp-year").val()+$("#card-exp-month").val(),
                                    card_cvv:$("#card-cvv").val(),
                                    data_key:''
                                };
        frappe.call({
                       method: "moneris_payment.templates.pages.moneris_checkout.make_payment",
                        args: {
                            data:JSON.stringify(monerisdata),
                            reference_doctype: "Payment Request",
                            reference_docname: $("#PaymentRequestId").val()
                        },
                       callback: function(Response) {
                        if(Response.message.status=="Completed")
                        {
                            $('.success').show();
                            setTimeout(function() {
                                window.location.href = Response.message.redirect_to
                            }, 2000);
                        }
                        else
                        {
                             $(".error").html("<p>"+Response.message.Message+"</p>")
                              $(".error").show();
                             setTimeout(function(){  $(".error").hide(); confirmButton.removeAttr("disabled")}, 3000);
                        }
                       }
                   });
    }
    function moneris_make_payment_withvault(datakey)
    {
        $(".submit-loading").show(); 
        var monerisdata={
                                    payment_request_id:$("#PaymentRequestId").val(),
                                    card_number:$("#card-number").val(),
                                    card_expire:$("#card-exp-year").val()+$("#card-exp-month").val(),
                                    card_cvv:$("#card-cvv").val(),
                                    data_key:datakey
                                };
        frappe.call({
                       method: "moneris_payment.templates.pages.moneris_checkout.make_payment",
                        args: {
                            data:JSON.stringify(monerisdata),
                            reference_doctype: "Payment Request",
                            reference_docname: $("#PaymentRequestId").val()
                        },
                       callback: function(Response) {
                        if(Response.message.status=="Completed")
                        {
                            
                            $('.success').show();
                        $(".submit-loading").hide(); 
                            setTimeout(function() {
                                window.location.href = Response.message.redirect_to
                            }, 2000);
                        }
                        else
                        {
                             $(".error").html("<p>"+Response.message.Message+"</p>")
                              $(".error").show();
                               $(".submit-loading").hide();
                             setTimeout(function(){    $(".error").hide(); }, 3000);
                        }
                       }
                   });
    }
