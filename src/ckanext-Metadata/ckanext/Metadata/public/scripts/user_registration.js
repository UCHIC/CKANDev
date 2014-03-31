/**
 * Created by pabitra on 3/29/14.
 */
$(document).ready(function(){

    $('#btnCreateAccount').attr('disabled', true);

    $('#chkDataPublishAgreement').click(function(){
        if($(this).is(':checked')){
             $('#btnCreateAccount').attr('disabled', false);

        }
        else{
              $('#btnCreateAccount').attr('disabled', true)
        }
    });
});

function showDataPublishAgreementDialog()
	{
		$('#showDataPublishModal').css('z-index', 1050);
		$('#showDataPublishModal').modal('show');
	}