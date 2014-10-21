/**
 * Created by pabitra on 3/27/14.
 */
var dataUseAgree = false;

$(document).ready(function(){

    // if the data use agreement checkbox exists, then it must be a user not registered
    if ($('#chkDataUseAgreement').length){
        if(sessionStorage.length >0){
            dataUseAgree = sessionStorage.getItem('dataUseAgree');
            if(sessionStorage.getItem('dataUseAgree') == "false"){
                dataUseAgree = false;
            }
            else{
                dataUseAgree = true;
            }
            }
            else
            {
                dataUseAgree = false;
            }

        if (!dataUseAgree){
            $("a.resource-url-analytics").hide();
            $("a.btn").hide();
            $("a.heading").css({cursor:"default"});
            var element = $("a.heading")
            $("p.muted.ellipsis").hide();
            $("#datapreview").hide();

        }
        else
        {
            $("a.resource-url-analytics").show();
            $("a.btn").show();
            $("a.heading").css({cursor:"pointer"});
            $("p.muted.ellipsis").show();
            $("#datapreview").show();

        }

        if (dataUseAgree){
            $('#chkDataUseAgreement').attr('checked', true);
        }
        else{
            $('#chkDataUseAgreement').attr('checked', false);
        }

        $("a.heading").click(function(event){
            if (!dataUseAgree){
                $(this).css({cursor:"default"});
                event.preventDefault();
            }
            else
            {
                $(this).css({cursor:"pointer"});
            }
        });

        $('#btnDataUseAgree').click(function(){
            dataUseAgree = true;
            sessionStorage.setItem('dataUseAgree', dataUseAgree)
            $("a.resource-url-analytics").show();
            $("a.heading").css({cursor:"pointer"});
            $("a.btn").show();
            $("p.muted.ellipsis").show();
            $("#datapreview").show();
        });

        $('#btnDataUseDecline').click(function(){
            dataUseAgree = false;
            sessionStorage.setItem('dataUseAgree', dataUseAgree)
            $("a.resource-url-analytics").hide();
            $("a.heading").css({cursor:"default"});
            $('#chkDataUseAgreement').attr('checked', false);
            $("a.btn").hide();
            $("p.muted.ellipsis").hide();
            $("#datapreview").hide();
        });

        $('#chkDataUseAgreement').click(function(){
             if($(this).is(':checked')){
                showDataUseAgreementDialog();
             }
             else{
                dataUseAgree = false;
                sessionStorage.setItem('dataUseAgree', dataUseAgree)
                $("a.resource-url-analytics").hide();
                $("a.heading").css({cursor:"default"});
                $("a.btn").hide();
                $("p.muted.ellipsis").hide();
                $("#datapreview").hide();
            }
        });
    }
    else{
        sessionStorage.clear();
    }

});

function showDataUseAgreementDialog()
	{
		$('#showDataUseModal').css('z-index', 1050);
        $('#showDataUseModal').modal({'backdrop': 'static', 'keyboard': 'false'});
		$('#showDataUseModal').modal('show');
	}






