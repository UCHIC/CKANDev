/**
 * Created by pabitra on 10/24/14.
 */
$(document).ready(function(){
    hideLinks();

});

function hideLinks(){
    $("p").find("a").each(function(){
        var linkText = $(this).text();
        $(this).before(linkText);
        $(this).remove();
    });
}