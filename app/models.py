# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from django.db import models
from django.contrib.auth.models import User

# Create your models here.


class Satuser(models.Model):
    user = models.OneToOneField(User, on_delete = models.CASCADE)
    fielKey = models.CharField(max_length=200)
    fielCer = models.CharField(max_length=200)
    fielPas = models.CharField(max_length=200)
    rfc =  models.CharField(max_length=20)
    

class DescargaCFDI(models.Model):
    idSolicitud = models.CharField(max_length=200)
    status = models.IntegerField()
    num_cfdis = models.IntegerField()
    fromDate = models.DateField()
    toDate = models.DateField()
    rfc_solicitante = models.CharField(max_length=20)


class Paquete(models.Model):
    solicitud = models.ForeignKey(DescargaCFDI,on_delete=models.CASCADE)
    idPaquete = models.CharField(max_length=200)

class UsoCFDI(models.Model):
    clave = models.CharField(max_length=3)
    des = models.CharField(max_length=200)
    isPartial = models.CharField(max_length=1,default='Y')

class ClaveServicioConTopeCFDI(models.Model):
    claveProducto = models.IntegerField()
    tope = models.FloatField()
    keyName = models.CharField(max_length=32,blank=True, null=True)
    keyValue = models.CharField(max_length=32,blank=True, null=True)
    isPatial = models.CharField(max_length=1,default='Y')

class ComprobanteCFDI(models.Model):
    uuid = models.CharField(max_length=256)
    fileName = models.CharField(max_length=256)
    metodoPago = models.CharField(max_length=3,blank=True, null=True)
    tipoComprobante = models.CharField(max_length=1)
    total = models.FloatField()
    subtotal = models.FloatField()
    moneda = models.CharField(max_length=3)
    certificado = models.CharField(max_length=256)
    fecha = models.DateField()
    emisorRFC = models.CharField(max_length=20)
    emisorName = models.CharField(max_length=200)
    emisorRegimen = models.CharField(max_length=3)
    receptorRFC = models.CharField(max_length=20)
    receptorName = models.CharField(max_length=200)
    uso = models.ForeignKey(UsoCFDI,on_delete=models.CASCADE)
    condiciones  = models.CharField(max_length=512,blank=True, null=True)
    tipoCambio =  models.FloatField(default=1.0, blank=True, null=True)
    totalImpuestosRet = models.FloatField(default=0.0,blank=True, null=True)
    totalImpuestosTras = models.FloatField(default=0.0, blank=True, null=True)
    totalImpuestosTrasDeducible = models.FloatField(default=0.0, blank=True, null=True)
    totalDeducible = models.FloatField(default=0.0, blank=True, null=True)
    status = models.CharField(max_length=20)
    
    class Meta:
        constraints = [
            models.UniqueConstraint (fields=['uuid', 'tipoComprobante'], name='unique_comprobante')
        ]


class ImpuestosCDFI(models.Model):
    comprobante = models.ForeignKey(ComprobanteCFDI,on_delete=models.CASCADE)
    idImpuesto = models.CharField(max_length=3)
    idTipo = models.CharField(max_length=3)
    tipoFactor = models.CharField(max_length=8,blank=True, null=True)
    tasaOCuota = models.FloatField(blank=True, null=True)
    importe = models.FloatField()
    importeDeducible = models.FloatField(default=0.0, blank=True, null=True)

class ConceptoCDFI(models.Model):
    comprobante = models.ForeignKey(ComprobanteCFDI,on_delete=models.CASCADE)
    claveProducto = models.CharField(max_length=10)
    cantidad = models.IntegerField()
    unidad = models.CharField(max_length=3)
    des = models.CharField(max_length=200)
    valorUnitario = models.FloatField()
    importe = models.FloatField()

class ComplementoConceptoCDFI(models.Model):
    concepto = models.ForeignKey(ConceptoCDFI,on_delete=models.CASCADE)
    keyName = models.CharField(max_length=32,blank=True, null=True)
    keyValue = models.CharField(max_length=32,blank=True, null=True)


class ImpuestosConceptoCFDI(models.Model):
    concepto = models.ForeignKey(ConceptoCDFI,on_delete=models.CASCADE)
    idImpuesto = models.CharField(max_length=3)
    idTipo = models.CharField(max_length=3,blank=True, null=True)
    tipoFactor = models.CharField(max_length=8,blank=True, null=True)
    tasaOCuota = models.FloatField(blank=True, null=True)
    base = models.FloatField(blank=True, null=True)
    importe = models.FloatField(blank=True, null=True)

class TablasDeISR(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    limiteInferior = models.FloatField()
    limiteSuperior = models.FloatField(blank=True, null=True)
    cuotaFija = models.FloatField()
    porcentajeExcedente = models.FloatField()

class Declaracion(models.Model):
    type = models.CharField(max_length=64)
    period = models.CharField(max_length=64)
    fecha = models.DateField()
    operationNumber = models.CharField(max_length=64)
    year = models.IntegerField()
    media =  models.CharField(max_length=64)
    isrInFavor = models.FloatField(default=0.0,blank=True, null=True)
    isrInCharge = models.FloatField(default=0.0,blank=True, null=True)
    isrToBePay = models.FloatField(default=0.0,blank=True, null=True)
    ivaInFavor = models.FloatField(default=0.0,blank=True, null=True)
    ivaInCharge = models.FloatField(default=0.0,blank=True, null=True)
    ivaToBePay = models.FloatField(default=0.0,blank=True, null=True)

class PagosEfecturados(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    impuesto = models.CharField(max_length=3)
    total =  models.FloatField()
    tipo = models.CharField(max_length=1,default='P')
    references = models.ManyToManyField(Declaracion)
    

    





