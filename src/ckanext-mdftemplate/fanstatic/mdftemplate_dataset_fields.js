$(document).ready(function() {
	
	var privacyBubble = $('<span id="privateBubble" title="Datasets are private and not visible to the public until a moderator has reviewed and approved them." class="info-block info-inline" style="cursor:pointer"> ' +
	        	'<i class="icon-question-sign"></i>' +
	        	'Why is my dataset private?</span>');
	
	var updatePrivacyDropdown = function() {
		if ($('#field-organizations > option:selected').text() === 'iutah') {
	    	$('#field-private').val("True");
	        $('#field-private option[value="False"]').attr('disabled', true);
	        privacyBubble.insertAfter($('#field-private'));
	    } else {
	    	$('#field-private option[value="False"]').attr('disabled', false);
	    	privacyBubble.remove();
	    }
	};
	
	updatePrivacyDropdown();
	$('#field-organizations').change(updatePrivacyDropdown);
	
	
	$('.additional-info .nav-tabs a').click(function(e){
		e.preventDefault();
		$(this).tab('show');
	});
	
	
});


