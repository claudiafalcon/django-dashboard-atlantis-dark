from django import forms
from django.conf import settings
from django.contrib.postgres.forms import SimpleArrayField
from datetime import date

TYPE_CHOICES = (
    ("1", "Emitidas"),
    ("2", "Recibidas"),
)

REPORT_TYPE = (
    ("M", "Mensual"),
    ("Y", "Anual"),
)

DEC_TYPE = (
    ("Emitidos", "Emitidos"),
    ("Personales", "Personales"),
    ("Empresariales", "Empresariales"),
)

MONTH_CHOICES = (
    ("1", "Enero"),
    ("2", "Febrero"),
    ("3", "Marzo"),
    ("4", "Abril"),
    ("5", "Mayo"),
    ("6", "Junio"),
    ("7", "Julio"),
    ("8", "Agosto"),
    ("9", "Septiembre"),
    ("10", "Octubre"),
    ("11", "Noviembre"),
    ("12", "Diciembre"),
)


YEAR_CHOICES = (
    (str(date.today().year), str(date.today().year)),
    (str(date.today().year-1), str(date.today().year-1)),
    (str(date.today().year-2), str(date.today().year-2)),
)


class DateInput(forms.DateInput):
    input_type = 'date'


class ExampleForm (forms.Form):
    my_date_field = forms.DateField(widget=DateInput)


class SolicitiduCFDIForm(forms.Form):
    fromDate = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS)
    toDate = forms.DateField(input_formats=settings.DATE_INPUT_FORMATS)
    types = forms.MultipleChoiceField(choices=TYPE_CHOICES)

    def clean_toDate(self):
        toDate = self.cleaned_data['toDate']
        fromDate = self.cleaned_data['fromDate']

        if toDate <= fromDate:
            raise forms.ValidationError('Fecha fin mayor a fecha Inicio')
        return toDate


class ReporteCFDIForm(forms.Form):
    rfc = forms.CharField(label='RFC')
    tipo = forms.ChoiceField(choices=REPORT_TYPE, label="Tipo de Reporte:")
    lyears = forms.ChoiceField(choices=YEAR_CHOICES, label='Año')
    months = forms.ChoiceField(choices=MONTH_CHOICES, label="Mes")
    types = forms.MultipleChoiceField(choices=DEC_TYPE, label="Tipo de CFDIS")

class SimulacionAcumulado(forms.Form):
    ingresosAdicionales = forms.DecimalField(initial = 0.0, required =False, label="Ingresos Adicionales:")
    gastosAdicionales = forms.DecimalField(initial = 0.0, required =False, label="Gastos Adicionales:")
    year = forms.IntegerField(initial = date.today().year,required =True)
    year.widget = year.hidden_widget()
    month = forms.IntegerField(initial = date.today().month,required =True)
    month.widget = month.hidden_widget()
