$(document).ready(function() {
	
	var privacyBubble = $('<span id="privateBubble" title="Datasets are private and not visible to the public until a moderator has reviewed and approved them." class="info-block info-inline" style="cursor:pointer"> ' +
	        	'<i class="icon-question-sign"></i>' +
	        	'Why is my dataset private?</span>');

    var updatePrivacyDropdown = function() {
		if ($('#field-organizations > option:selected').text() === 'iutah') {
	    	if ($('#field-private option:selected').val() === "True"){
                $('#field-private option[value="False"]').attr('disabled', true);
                $('#field-private option[value="True"]').attr('disabled', false);
                privacyBubble.insertAfter($('#field-private'));
            } else {
                $('#field-private option[value="False"]').attr('disabled', false);
                $('#field-private option[value="True"]').attr('disabled', true);
                privacyBubble.remove();
	        }
        }
	};

	updatePrivacyDropdown();
	$('#field-organizations').change(updatePrivacyDropdown);
	
	
	$('.additional-info .nav-tabs a').click(function(e){
		e.preventDefault();
		$(this).tab('show');
	});
	
	
});


