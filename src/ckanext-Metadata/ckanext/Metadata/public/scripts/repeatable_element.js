/**
 * Created by pabitra on 4/10/14.
 */
var numberOfCreators = 0;
var maxNumberOfCreators = 5;
var deleteCount = 0;
var addCount = 0;
var originalCount = 0;
$(document).ready(function(){
    numberOfCreators = $('#creator_list > div').length
    originalCount = numberOfCreators;

    $('a.btn.btn-primary').click(function(){
        addCreator();
     })

    $("[id^=btn_]").click(function(){
        //$(this).
        var idSplit = new String(this.id).split("_");

        deleteCreator(idSplit[1]);
    })

});

function addCreator(){
    //var displayedCount = originalCount + addCount - deleteCount;

//    if(displayedCount == maxNumberOfCreators){
//        alert("Maximum creators allowed is " + maxNumberOfCreators + ".");
//        return;
//    }
    // check if any of the creators name is blank. If so do not add another creator
    var canAddCreator = true;
    var $creators = $('#creator_list').find('[id^=creator_]');

    $creators.each(function(){
        $(this).find("input").each(function(){
            if (endsWith($(this).attr("id"), "-name") && $(this).attr("value") == ""){
                alert("One or more creators missing name.");
                canAddCreator = false;
                return;
            }
            })
        })

    if (!canAddCreator) return;

    var $clone = $('#creator_list').find('[id^=creator_]').last().clone().appendTo('#creator_list');
    //var $clone = $('#creator_0').clone().appendTo('#creator_list');
    $clone.attr('id', increment(numberOfCreators,'creator_0'));
    $clone.attr('style', "");
    // find all the input elements
    $clone.find("input").each(function(){
        this.id = increment(numberOfCreators, this.id);
        this.name = increment(numberOfCreators, this.name);
        this.value ="";
    });
    $clone.find("div").each(function(){
        this.id = increment(numberOfCreators, this.id);
    })
    $clone.find("a").each(function(){
        this.id = increment(numberOfCreators, this.id);
    })

    addCount++;

    $("#btn_" + numberOfCreators + "_delete").click(function(){
        //$(this).
        var idSplit = new String(this.id).split("_");

        deleteCreator(idSplit[1]);
    })
    numberOfCreators++;
}
function deleteCreator(index){
    var displayedCount = originalCount + addCount - deleteCount;
    if(displayedCount == 1){
        alert("There has to be at least one creator.");
        return;
    }
    // set the delete field of the deleted creator to 1
    $('#field-creators-' +index + '-delete').attr('value', 1);
    $('#creator_' + index).hide();
    deleteCount++;
    //alert('you clicked delete' + index);
}

function increment(index, string) {
    //return (string || '').replace(/\d+/, function (index) { return 1 + parseInt(index, 10); });
    return (string || '').replace(/\d+/, index);
}

function getNumberOfDisplayedCreators()
{
    return $('#creator_list > div').length
}

function endsWith(str, suffix) {
    return str.indexOf(suffix, str.length - suffix.length) !== -1;
}
