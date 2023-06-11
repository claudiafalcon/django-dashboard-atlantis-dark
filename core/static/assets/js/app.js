
$( function() {
    var collection = $(".cust-form-date");
    collection.each( function (){
        if (this.type != "date"){ //if browser doesn't support input type="date", initialize date picker widget:
            $(this).datepicker({ dateFormat: 'dd/mm/yy' });
        }    
    });

   
    $("h4.currency").formatCurrency();
  

    $('#add-row').DataTable({
        "pageLength": 5,
    });

    $('#add-row-comp').DataTable({
        "pageLength": 15,
        buttons: [
            'excelHtml5'
        ]
    });

    var action = '<td> <div class="form-button-action"> <button type="button" data-toggle="tooltip" title="" class="btn btn-link btn-primary btn-lg" data-original-title="Edit Task"> <i class="fa fa-edit"></i> </button> <button type="button" data-toggle="tooltip" title="" class="btn btn-link btn-danger" data-original-title="Remove"> <i class="fa fa-times"></i> </button> </div> </td>';

    $('#addRowButton').click(function() {
        $("#errorLabel").text("");
        var serializedData = $("#createNewCFDIRequest").serialize();
        console.log(serializedData)
        $.ajax({
            url:$("#createNewCFDIRequest").data('url'),
            data: serializedData,
            type: 'post',
            success: function (response){
                requests = response.descarga
                for (i in requests ){
                    json = requests[i];
                    var estado='';
                    switch(json.status){
                        case 1:
                            estado = 'Enviada';
                            break;
                        case 2:
                            estado = 'En Proceso';
                            break;
                        case 3:
                            estado = 'Descargada';
                            break;
                        case 5:
                            estado  = 'Sin CFDIs';
                            break;
                        default:
                            estado = 'ERROR';              
                    }
                    const options = { year: 'numeric', month: 'long', day: 'numeric' }
                    fromDate = new Date(json.fromDate);
                    timediff = fromDate.getTimezoneOffset()*60000;
                    fromDate = new Date(fromDate.valueOf()+timediff);
                    toDate = new Date(json.toDate);
                    timediff = toDate.getTimezoneOffset()*60000;
                    toDate = new Date(toDate.valueOf()+timediff);
                    $('#add-row').dataTable().fnAddData([
                        json.idSolicitud,
                        estado,
                        fromDate.toLocaleDateString('es-MX', options),
                        toDate.toLocaleDateString('es-MX', options),
                        json.num_cfdis,
                        json.rfc_solicitante,
                        action
                        ]);
                    $('#addRowModal').modal('hide');
                }
            },
            error: function(response){
                json = response.responseJSON
                $("#errorLabel").text(json.error);
            }
        })

    });

 //$( "#fromDate" ).datepicker();
 } );

 function CurrencyFormatted(amount) {
	var i = parseFloat(amount);
	if(isNaN(i)) { i = 0.00; }
	var minus = '';
	if(i < 0) { minus = '-'; }
	i = Math.abs(i);
	i = parseInt((i + .005) * 100);
	i = i / 100;
	s = new String(i);
	if(s.indexOf('.') < 0) { s += '.00'; }
	if(s.indexOf('.') == (s.length - 2)) { s += '0'; }
	s = minus + s;
	return s;
};