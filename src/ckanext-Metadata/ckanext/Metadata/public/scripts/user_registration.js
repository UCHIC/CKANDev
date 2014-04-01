/**
 * Created by pabitra on 3/29/14.
 */
$(document).ready(function(){

    var dataUseAgree = false;
    var dataPublishAgree = false;

    var error = $("#field-error").val();
    if (error != "{}")
    {
          if(sessionStorage.length >1)
        {
            dataUseAgree = sessionStorage.getItem('dataUseAgree');
            dataPublishAgree = sessionStorage.getItem('dataPublishAgree');
        }
        else
        {
            dataUseAgree = false;
            dataPublishAgree = false;
        }
    }

    if (dataPublishAgree && dataUseAgree){
        $('#chkDataPublishAgreement').prop('checked', true);
        $('#chkDataUseAgreement').prop('checked', true);
        $('#btnCreateAccount').attr('disabled', false);
    }
    else{
         $('#btnCreateAccount').attr('disabled', true);
         $('#chkDataPublishAgreement').prop('checked', false);
         $('#chkDataUseAgreement').prop('checked', false);
    }

    $('#btnDataPublishAgree').click(function(){
        dataPublishAgree = true;
        sessionStorage.setItem('dataPublishAgree', dataPublishAgree);
        if (dataUseAgree){
            $('#btnCreateAccount').attr('disabled', false);
        }
    });

    $('#btnDataUseAgree').click(function(){
        dataUseAgree = true;
        sessionStorage.setItem('dataUseAgree', dataUseAgree)
        if (dataPublishAgree){
            $('#btnCreateAccount').attr('disabled', false);
        }
    });

    $('#btnDataPublishDecline').click(function(){
        dataPublishAgree = false;
        $('#btnCreateAccount').attr('disabled', true);
        $('#chkDataPublishAgreement').prop('checked', false);
        sessionStorage.setItem('dataPublishAgree', dataPublishAgree);
    });

    $('#btnDataUseDecline').click(function(){
        dataUseAgree = false;
        $('#btnCreateAccount').attr('disabled', true);
        $('#chkDataUseAgreement').prop('checked', false);
        sessionStorage.setItem('dataUseAgree', dataUseAgree);
    });

    $('#chkDataPublishAgreement').click(function(){
        if($(this).is(':checked')){
            showDataPublishAgreementDialog();
        }
        else{
            $('#btnCreateAccount').attr('disabled', true);
             dataPublishAgree = false;
             sessionStorage.setItem('dataPublishAgree', dataPublishAgree);
        }

//        if($(this).is(':checked')){
//             $('#btnCreateAccount').attr('disabled', false);
//
//        }
//        else{
//              $('#btnCreateAccount').attr('disabled', true)
//        }
    });

    $('#chkDataUseAgreement').click(function(){
         if($(this).is(':checked')){
            showDataUseAgreementDialog();
         }
         else{
            $('#btnCreateAccount').attr('disabled', true);
             dataUseAgree = false;
             sessionStorage.setItem('dataUseAgree', dataUseAgree);
        }
    });
});

function showDataPublishAgreementDialog()
	{
		$('#showDataPublishModal').css('z-index', 1050);
		$('#showDataPublishModal').modal('show');
	}

function showDataUseAgreementDialog()
	{
		$('#showDataUseModal').css('z-index', 1050);
		$('#showDataUseModal').modal('show');
	}