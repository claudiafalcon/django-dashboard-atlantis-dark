$(function() {
    //do something
    var collection = $(".cust-form-date");
    collection.each( function (){
        if (this.type != "date"){ //if browser doesn't support input type="date", initialize date picker widget:
            $(document).ready(function() {
                this.datepicker();
            }); 
        }  
    });
  });
  