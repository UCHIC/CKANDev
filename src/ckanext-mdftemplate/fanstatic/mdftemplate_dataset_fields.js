ckan.module('mdftemplate_dataset_fields', function(jQuery, _) {
	return {
		initialize: function () {
			//TODO: desired javascript code goes here.
			
  			$('.nav-tabs a').click(function(e){
  				e.preventDefault()
  				$(this).tab('show')
  			});
  		
		}
	};
});
