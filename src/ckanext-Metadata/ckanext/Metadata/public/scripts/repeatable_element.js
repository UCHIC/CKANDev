/**
 * Created by pabitra on 4/10/14.
 */
var numberOfCreators = 0;
var numberOfContributors = 0;
var numberOfVariables = 0;
var deleteCreatorCount = 0;
var deleteVariableCount = 0;
var addCreatorCount = 0;
var addVariableCount = 0;
var originalCreatorCount = 0;
var originalVariableCount = 0;
var deleteContributorCount = 0;
var addContributorCount = 0;

$(document).ready(function(){
    numberOfCreators = $('#creator_list > div').length
    originalCreatorCount = numberOfCreators;
    numberOfContributors = $('#contributor_list > div').length
    numberOfVariables = $('#variable_list > div').length
    originalVariableCount = numberOfVariables;

    // initially we want to have one contributor element that is hidden
    // from which the first clone can be made when the user selects add contributor button
    var $contributor_div = $('#contributor_list').find('[id^=contributor_]').first();
    var hide_contributor = false;
    $contributor_div.find("input").each(function(){
        if (endsWith($(this).attr("id"), "-delete") && $(this).attr("value") == "1"){
            hide_contributor = true;
        }
    })

    if(hide_contributor){
        $contributor_div.hide();
    }

    var addCreatorButton = $('#addCreator').find('a').first();
    addCreatorButton.click(function(){
        addCreator();
     })

    var addContributorButton = $('#addContributor').find('a').first();
    addContributorButton.click(function(){
        addContributor();
     })

    var addVariableButton = $('#addVariable').find('a').first();
    addVariableButton.click(function(){
        addVariable();
     })

    $("[id$=-is_a_group]").click(function(){
        var idSplit = new String(this.id).split("-");
        checkboxToggle(idSplit[2])
    })

    $("[id^=btn_]").click(function(){
        var idSplit = new String(this.id).split("_");

        if(idSplit[3] == "creator")
        {
            deleteCreator(idSplit[1]);
        }
        else if(idSplit[3] == "contributor")
        {
            deleteContributor(idSplit[1]);
        }
        else if(idSplit[3] == "variable")
        {
            deleteVariable(idSplit[1]);
        }
    })
});

function addCreator(){

    var $clone = $('#creator_list').find('[id^=creator_]').last().clone().appendTo('#creator_list');
    $clone.attr('id', increment(numberOfCreators,'creator_0'));
    $clone.attr('style', "");
    // find all the input elements
    $clone.find("input").each(function(){
        this.id = increment(numberOfCreators, this.id);
        this.name = increment(numberOfCreators, this.name);
        if(this.type == 'checkbox'){
            this.checked = false;
            this.value = '0'
        }
        else{
            this.value ="";
        }

    });

    $("[id$=-is_a_group]").click(function(){
        //alert('you selected')
        var idSplit = new String(this.id).split("-");
        checkboxToggle(idSplit[2])
    })

     var label = $clone.find(".checkbox", 'label').first();
     var new_for = increment(numberOfCreators, label.attr('for'));
     label.attr('for', new_for);


    $clone.find("div").each(function(){
        this.id = increment(numberOfCreators, this.id);
    })
    $clone.find("a").each(function(){
        this.id = increment(numberOfCreators, this.id);
    })

    addCreatorCount++;

    $("#btn_" + numberOfCreators + "_delete_creator").click(function(){
        var idSplit = new String(this.id).split("_");
        deleteCreator(idSplit[1]);
    })
    numberOfCreators++;
}

function addContributor(){
    var $clone = $('#contributor_list').find('[id^=contributor_]').last().clone().appendTo('#contributor_list');

    $clone.attr('id', increment(numberOfContributors,'contributor_0'));
    $clone.attr('style', "");
    // find all the input elements
    $clone.find("input").each(function(){
        this.id = increment(numberOfContributors, this.id);
        this.name = increment(numberOfContributors, this.name);
        if (this.name.indexOf('__delete') > -1){
            this.value = '0'
        }
        else{
          this.value ="";
        }

    });
    $clone.find("div").each(function(){
        this.id = increment(numberOfContributors, this.id);
    })
    $clone.find("a").each(function(){
        this.id = increment(numberOfContributors, this.id);
    })

    addContributorCount++;

    $("#btn_" + numberOfContributors + "_delete_contributor").click(function(){
        var idSplit = new String(this.id).split("_");
        deleteContributor(idSplit[1]);
    })
    numberOfContributors++;
}

function addVariable(){
    var $clone = $('#variable_list').find('[id^=variable_]').last().clone().appendTo('#variable_list');

    $clone.attr('id', increment(numberOfVariables,'variable_0'));
    $clone.attr('style', "");
    // find all the input elements
    $clone.find("input").each(function(){
        this.id = increment(numberOfVariables, this.id);
        this.name = increment(numberOfVariables, this.name);
        if (this.name.indexOf('__delete') > -1){
            this.value = '0'
        }
        else{
          this.value ="";
        }

    });
    $clone.find("div").each(function(){
        this.id = increment(numberOfVariables, this.id);
    })
    $clone.find("button").each(function(){
        this.id = increment(numberOfVariables, this.id);
    })

    addVariableCount++;

    $("#btn_" + numberOfVariables + "_delete_variable").click(function(){
        var idSplit = new String(this.id).split("_");
        deleteVariable(idSplit[1]);
    })
    numberOfVariables++;
}
function deleteCreator(index){
    var displayedCount = originalCreatorCount + addCreatorCount - deleteCreatorCount;
    if(displayedCount == 1){
        alert("There has to be at least one creator.");
        return;
    }
    // set the delete field of the deleted creator to 1
    $('#field-creators-' +index + '-delete').attr('value', 1);
    $('#creator_' + index).hide();
    deleteCreatorCount++;
}

function deleteContributor(index){
    // set the delete field of the deleted creator to 1
    $('#field-contributors-' +index + '-delete').attr('value', 1);
    $('#contributor_' + index).hide();
    deleteContributorCount++;
}

function deleteVariable(index){
    var displayedCount = originalVariableCount + addVariableCount - deleteVariableCount;
    if(displayedCount == 1){
        alert("There has to be at least one variable.");
        return;
    }
    // set the delete field of the deleted creator to 1
    $('#field-variables-' +index + '-delete').attr('value', 1);
    $('#variable_' + index).hide();
    deleteVariableCount++;
}

function checkboxToggle(index){

    // set the delete field of the deleted creator to 1
    if ($('#field-creators-' +index + '-is_a_group').is(':checked')){
        $('#field-creators-' +index + '-is_a_group').attr('value', '1');
    }
    else{
        $('#field-creators-' +index + '-is_a_group').attr('value', '0');
    }
}

function increment(index, string) {
    //return (string || '').replace(/\d+/, function (index) { return 1 + parseInt(index, 10); });
    return (string || '').replace(/\d+/, index);
}

function endsWith(str, suffix) {
    return str.indexOf(suffix, str.length - suffix.length) !== -1;
}
