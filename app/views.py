# -*- encoding: utf-8 -*-

import base64
import datetime
import json
import codecs
import zlib
import io
import zipfile
import pprint
import sqlite3
import shutil
import os
import xml.etree.ElementTree as ET

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Max, Min, Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.template import loader
from django.http import HttpResponse
from django import template
from cfdiclient import Autenticacion
from cfdiclient import Validacion
from cfdiclient import Fiel
from django.conf import settings
from cfdiclient import SolicitaDescarga
from cfdiclient import VerificaSolicitudDescarga
from cfdiclient import DescargaMasiva
from django.contrib.auth.models import User
from .models import Satuser
from .models import DescargaCFDI
from .models import ComprobanteCFDI
from .models import Paquete
from .forms import SolicitiduCFDIForm, ReporteCFDIForm, SimulacionAcumulado
from .models import UsoCFDI
from .models import ImpuestosCDFI
from .models import ClaveServicioConTopeCFDI
from .models import ImpuestosConceptoCFDI, ComplementoConceptoCDFI
from .models import ConceptoCDFI
from .models import TablasDeISR
from .models import PagosEfecturados
from django.views.generic.edit import CreateView
from dateutil.parser import parse
from datetime import date
from django.db.models import Q, When, Case


from django.http import JsonResponse
from django.forms.models import model_to_dict


from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA
from OpenSSL import crypto


class SimuladoView(CreateView):
     def post(self, request):

        form = SimulacionAcumulado(request.POST)
        if form.is_valid():
            month = form.cleaned_data.get("month")
            year = form.cleaned_data.get("year")
            ingresosAdicionales = form.cleaned_data.get("ingresosAdicionales")
            gastosAdicionales = form.cleaned_data.get("gastosAdicionales")

            acumuladosSimulados = getAcumuladosSimulados(year, month,ingresosAdicionales, gastosAdicionales)
                  
            return JsonResponse({"status":"ok","acumuladosSimulados": acumuladosSimulados}, status = 200)
        else:
            return JsonResponse({"status":"ko", "errors": form.errors})

class ReportCFDIView(CreateView):

    def post(self, request):
        form = ReporteCFDIForm(request.POST)
        user = User.objects.last()
        rfc = user.satuser.rfc
        tipoDeclaracion = 'M'
        usos = {'Emitidos': False,
                'Personales': False,
                'Empresariales': False
                }

        mes = date.today().month
        anno = date.today().year
        if form.is_valid():
            tipoDeclaracion = form.cleaned_data.get("tipo")
            anno = form.cleaned_data.get("lyears")
            mes = form.cleaned_data.get("months")
            selects = form.cleaned_data.get("types")
            for sel in selects:
                usos[sel] = True
        context = getResponseContext(tipoDeclaracion, usos, anno, mes)
        context["form"] = form
        formSimulado = SimulacionAcumulado(initial={
                               'year': anno, 'month': mes, 'ingresosAdicionales': 0.0 ,'gastosAdicionales': 0.0  })
        formSimulado.fields['year'].widget.attrs['readonly'] = True
        formSimulado.fields['month'].widget.attrs['readonly'] = True

        context["formSimulado"] = formSimulado
      
        
        html_template = loader.get_template('reportecfdi.html')
        return HttpResponse(html_template.render(context, request))

    def get(self, request):
        user = User.objects.last()
        rfc = user.satuser.rfc
        tipoDeclaracion = 'M'
        usos = {'Emitidos': True,
                'Personales': False,
                'Empresariales': True
                }

        mes = date.today().month
        anno = date.today().year
        context = getResponseContext(tipoDeclaracion, usos, anno, mes)
     
        form = ReporteCFDIForm(initial={
                               'rfc': user.satuser.rfc, 'years': anno, 'months': mes, 'types': ('Emitidos', 'Personales')})
        form.fields['rfc'].widget.attrs['readonly'] = True

        context["form"] = form

        formSimulado = SimulacionAcumulado(initial={
                               'year': anno, 'month': mes, 'ingresosAdicionales': 0.0 ,'gastosAdicionales': 0.0  })
        formSimulado.fields['year'].widget.attrs['readonly'] = True
        formSimulado.fields['month'].widget.attrs['readonly'] = True

        context["formSimulado"] = formSimulado


        html_template = loader.get_template('reportecfdi.html')
        return HttpResponse(html_template.render(context, request))


class DownloadCFDIView(CreateView):

    def get(self, request):
        user = User.objects.last()
       # createProfile()

        fielKey = user.satuser.fielKey
        fielCer = user.satuser.fielCer
        cer_der = open(settings.SAT_DIR[0] + fielCer, 'rb').read()
        key_der = open(settings.SAT_DIR[0] + fielKey, 'rb').read()
        fielPas = user.satuser.fielPas
        rfc = user.satuser.rfc
        cfdisToBeValidate = DescargaCFDI.objects.filter(
            rfc_solicitante=rfc).filter(Q(status=1) | Q(status=2))
        fiel = Fiel(cer_der, key_der, fielPas)
        auth = Autenticacion(fiel)
        token = auth.obtener_token()
        for cfdi in cfdisToBeValidate:
            v_descarga = VerificaSolicitudDescarga(fiel)
            result = v_descarga.verificar_descarga(
                token, rfc, cfdi.idSolicitud)
            if result['cod_estatus'] == '5000':
                if result['estado_solicitud'] == '3':
                    cfdi.status = 4
                    cfdi.num_cfdis = result['numero_cfdis']
                    cfdi.save()
                    for paquete in result['paquetes']:
                        paq = Paquete()
                        paq.solicitud = cfdi
                        paq.idPaquete = paquete
                        paq.save()
                elif result['estado_solicitud'] == '5' and result['codigo_estado_solicitud'] == '5004':
                    cfdi.status = 5
                    cfdi.num_cfdis = result['numero_cfdis']
                    cfdi.save()
                elif result['estado_solicitud'] == '2':
                    cfdi.status = 2
                    cfdi.save()
                elif result['estado_solicitud'] == '1':
                    cfdi.status = 1
                    cfdi.save()
                else:
                    cfdi.status = 0
                    cfdi.save()

        cfdisToBeDownload = DescargaCFDI.objects.filter(
            rfc_solicitante=rfc).filter(status=4)
        for cfdi in cfdisToBeDownload:
            paquetes = Paquete.objects.filter(solicitud=cfdi)
            for paq in paquetes:
                descarga = DescargaMasiva(fiel)
                result = descarga.descargar_paquete(token, rfc, paq.idPaquete)
                if result['cod_estatus'] == '5000':
                    cfdi.status = 3
                    data = result['paquete_b64']
                    convert(data, paq.idPaquete)
                    cfdi.save()
                else:
                    cfdi.status = 0
                    cfdi.save()
        cargaCFDIs()

        #{'cod_estatus': '5000', 'estado_solicitud': '5', 'codigo_estado_solicitud': '5004', 'numero_cfdis': '0', 'mensaje': 'Solicitud Aceptada', 'paquetes': []}
        #{'cod_estatus': '5000', 'estado_solicitud': '3', 'codigo_estado_solicitud': '5000', 'numero_cfdis': '6', 'mensaje': 'Solicitud Aceptada', 'paquetes': ['3035DDD5-0093-48AE-ADC4-62111BCF147E_01']}

        cfdis = DescargaCFDI.objects.filter(rfc_solicitante=rfc)
        context = {'descargas': cfdis}
        html_template = loader.get_template('downloadcfdi.html')
        return HttpResponse(html_template.render(context, request))

    def post(self, request):

        form = SolicitiduCFDIForm(request.POST)

        if form.is_valid():
            cfdis = []

            user = User.objects.last()
            fielKey = user.satuser.fielKey
            fielCer = user.satuser.fielCer
            cer_der = open(settings.SAT_DIR[0] + fielCer, 'rb').read()
            key_der = open(settings.SAT_DIR[0] + fielKey, 'rb').read()
            fielPas = user.satuser.fielPas
            rfc = user.satuser.rfc
            fiel = Fiel(cer_der, key_der, fielPas)
            auth = Autenticacion(fiel)
            token = auth.obtener_token()
            descarga = SolicitaDescarga(fiel)

            requests = form.cleaned_data.get("types")

            for req in requests:  # El request es para el emisor
                if req == '1':
                    #result = {'id_solicitud': '05f2b4f6-0a58-43b9-9367-ce2621567b63', 'cod_estatus': '5000', 'mensaje': 'Solicitud Aceptada'}
                    result = descarga.solicitar_descarga(token, rfc, form.cleaned_data.get(
                        "fromDate"), form.cleaned_data.get("toDate"), rfc_emisor=rfc)
                else:
                    #result = {'id_solicitud': '3035ddd5-0093-48ae-adc4-62111bcf147e', 'cod_estatus': '5000', 'mensaje': 'Solicitud Aceptada'}
                    result = descarga.solicitar_descarga(token, rfc, form.cleaned_data.get(
                        "fromDate"), form.cleaned_data.get("toDate"), rfc_receptor=rfc)
                if result['cod_estatus'] == '5000' and DescargaCFDI.objects.filter(idSolicitud=result['id_solicitud']).exists() == False:
                    newCFDI = DescargaCFDI()
                    newCFDI.fromDate = form.cleaned_data.get("fromDate")
                    newCFDI.toDate = form.cleaned_data.get("toDate")
                    newCFDI.idSolicitud = result['id_solicitud']
                    newCFDI.status = 1
                    newCFDI.rfc_solicitante = rfc
                    newCFDI.num_cfdis = 0
                    newCFDI.save()
                    cfdis.append(model_to_dict(newCFDI))
                else:
                    return JsonResponse({'error': 'La solicitud no fue exitosa. Intente mas tarde'}, status=400)

            return JsonResponse({'descarga': cfdis}, status=200)
        else:
            er = ''
            for key, value in form.errors.items():
                er = er + str(key) + '-' + str(value[0])

def getAcumuladosSimulados(year,month, ingresosAdicionales, gastosAdicionales):
    user = User.objects.last()
    rfc = user.satuser.rfc
    cfdis = ComprobanteCFDI.objects.filter(
        Q(emisorRFC=rfc) | Q(receptorRFC=rfc))
    cfdis = cfdis.filter(fecha__year=year)
    cfdis = cfdis.filter(Q(fecha__month__lte=month))
    cfdis = cfdis.exclude(uso__isPartial='N', receptorRFC=rfc)
 
    qsIngresos = cfdis.filter(emisorRFC=rfc).filter(
        tipoComprobante='I').filter(status='Vigente') | cfdis.filter(emisorRFC=rfc).filter(
        tipoComprobante='I').filter(status='No Encontrado')
    ingresos = getNumFloat(
        next(iter(qsIngresos.aggregate(Sum('subtotal')).values()))) + getNumFloat(ingresosAdicionales)
    isrRetenido = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='001') & Q(impuestoscdfi__idTipo='RET'))).values())))
    ivaRetenido = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='RET'))).values())))
    iva = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values())))
    

    qsGastosI = cfdis.filter(receptorRFC=rfc).filter(
        tipoComprobante='I').filter(status='Vigente')
    qsGastosE = cfdis.filter(receptorRFC=rfc).filter(
        tipoComprobante='E').filter(status='Vigente')


   
    gastos = getNumFloat(next(iter(qsGastosI.aggregate(Sum('totalDeducible')).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(Sum('totalDeducible')).values()))) + getNumFloat(gastosAdicionales)
    ivaAcreditable = getNumFloat(next(iter(qsGastosI.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values())))

    base = ingresos - gastos

    rangoQS = TablasDeISR.objects.filter(month=month) & TablasDeISR.objects.filter(year=year) & TablasDeISR.objects.filter(limiteInferior__lte = base)  & (TablasDeISR.objects.filter(limiteSuperior__gt = base))
    if not rangoQS:
        rango = TablasDeISR.objects.filter(month=month) & TablasDeISR.objects.filter(year=year) & TablasDeISR.objects.filter(limiteInferior__lte = base) & (TablasDeISR.objects.filter(limiteSuperior__isnull =True))  
    rango = rangoQS.first()
    isrCausado = rango.cuotaFija + ((base - rango.limiteInferior) * rango.porcentajeExcedente/100)
    pagosQS = PagosEfecturados.objects.filter(Q(year=year) & Q(month__lte=month))
    isrPagado = getNumFloat(next(iter(pagosQS.aggregate(isrPagado=Sum('total', filter=Q(impuesto='001') & Q(tipo='P'))).values())))
    isrAcreditado = getNumFloat(next(iter(pagosQS.aggregate(isrAcreditado=Sum('total', filter=Q(impuesto='001') & Q(tipo='A'))).values())))
    ivaPagado = getNumFloat(next(iter(pagosQS.aggregate(ivaPagado=Sum('total', filter=Q(impuesto='002') & Q(tipo='P'))).values())))
    ivaAcreditado = getNumFloat(next(iter(pagosQS.aggregate(ivaAcreditado=Sum('total', filter=Q(impuesto='002') & Q(tipo='A'))).values())))

    isrPorPagar = isrCausado - isrRetenido - isrPagado -isrAcreditado
    ivaPorPagar = iva - ivaRetenido - ivaAcreditable -ivaPagado -ivaAcreditado


    acumuladosSimulados = { 'ingresos': ingresos, 'gastos': gastos, 'base': base, 'isrCausado': isrCausado, 'isrRetenido': isrRetenido, 'isrPagado': isrPagado, 'isrAcreditado':isrAcreditado, 'isrPorPagar': isrPorPagar,
                  'ivaCausado': iva, 'ivaRetenido': ivaRetenido, 'ivaAcreditable': ivaAcreditable, 'ivaPagado': ivaPagado,'ivaAcreditado':ivaAcreditado, 'ivaPorPagar': ivaPorPagar}
    return acumuladosSimulados
                
def getAcumulados(year,month):
    user = User.objects.last()
    rfc = user.satuser.rfc
    cfdis = ComprobanteCFDI.objects.filter(
        Q(emisorRFC=rfc) | Q(receptorRFC=rfc))
    cfdis = cfdis.filter(fecha__year=year)
    cfdis = cfdis.filter(Q(fecha__month__lte=month))
    cfdis = cfdis.exclude(uso__isPartial='N', receptorRFC=rfc)
    topes = ClaveServicioConTopeCFDI.objects.all()
    topeDeclara = {}
    for tope in topes:
        topeDeclara[tope.claveProducto] = getNumFloat(tope.tope)
        toBeUpdated = cfdis.filter(
            Q(conceptocdfi__claveProducto=tope.claveProducto))
        for cfdi in toBeUpdated:
            cfdi.totalDeducible = cfdi.subtotal
            cfdi.totalImpuestosTrasDeducible = cfdi.totalImpuestosTras
            month_cfdi = cfdi.fecha.month
            if tope.isPatial == 'Y':
                key = str(tope.claveProducto) +'|' + str(month_cfdi)
                topeDeclara[key] = topeDeclara[tope.claveProducto]
            else:
                key = tope.claveProducto
            for conc in cfdi.conceptocdfi_set.filter(Q(claveProducto=tope.claveProducto)):
                if(conc.importe > topeDeclara[key]):
                    cfdi.totalDeducible = cfdi.totalDeducible - \
                        (conc.importe - topeDeclara[key])
                    
                    impuestos = conc.impuestosconceptocfdi_set.filter(Q(idImpuesto ='002') & Q(idTipo='TRA') & Q(tipoFactor='Tasa'))        
                    for impuesto in impuestos:
                        quantituToSubstract = impuesto.importe - impuesto.tasaOCuota * topeDeclara[key]
                        ivaToModified =cfdi.impuestoscdfi_set.filter(Q(idImpuesto ='002') & Q(idTipo='TRA')).first()
                        ivaToModified.importeDeducible = ivaToModified.importe - quantituToSubstract
                        cfdi.totalImpuestosTrasDeducible = cfdi.totalImpuestosTras - quantituToSubstract
                        ivaToModified.save()
                    topeDeclara[key] = 0
                else:
                    topeDeclara[key] = topeDeclara[key] - conc.importe
                
            cfdi.save()
 
    qsIngresos = cfdis.filter(emisorRFC=rfc).filter(
        tipoComprobante='I').filter(status='Vigente') | cfdis.filter(emisorRFC=rfc).filter(
        tipoComprobante='I').filter(status='No Encontrado')
    ingresos = getNumFloat(
        next(iter(qsIngresos.aggregate(Sum('subtotal')).values())))
    isrRetenido = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='001') & Q(impuestoscdfi__idTipo='RET'))).values())))
    ivaRetenido = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='RET'))).values())))
    iva = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values())))
    

    qsGastosI = cfdis.filter(receptorRFC=rfc).filter(
        tipoComprobante='I').filter(status='Vigente')
    qsGastosE = cfdis.filter(receptorRFC=rfc).filter(
        tipoComprobante='E').filter(status='Vigente')


   
    gastos = getNumFloat(next(iter(qsGastosI.aggregate(Sum('totalDeducible')).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(Sum('totalDeducible')).values())))
    ivaAcreditable = getNumFloat(next(iter(qsGastosI.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values())))

    base = ingresos - gastos

    rangoQS = TablasDeISR.objects.filter(month=month) & TablasDeISR.objects.filter(year=year) & TablasDeISR.objects.filter(limiteInferior__lte = base)  & (TablasDeISR.objects.filter(limiteSuperior__gt = base))
    if not rangoQS:
        rango = TablasDeISR.objects.filter(month=month) & TablasDeISR.objects.filter(year=year) & TablasDeISR.objects.filter(limiteInferior__lte = base) & (TablasDeISR.objects.filter(limiteSuperior__isnull =True))  
    rango = rangoQS.first()
    isrCausado = rango.cuotaFija + ((base - rango.limiteInferior) * rango.porcentajeExcedente/100)
    pagosQS = PagosEfecturados.objects.filter(Q(year=year) & Q(month__lte=month))
    isrPagado = getNumFloat(next(iter(pagosQS.aggregate(isrPagado=Sum('total', filter=Q(impuesto='001') & Q(tipo='P'))).values())))
    isrAcreditado = getNumFloat(next(iter(pagosQS.aggregate(isrAcreditado=Sum('total', filter=Q(impuesto='001') & Q(tipo='A'))).values())))
    ivaPagado = getNumFloat(next(iter(pagosQS.aggregate(ivaPagado=Sum('total', filter=Q(impuesto='002') & Q(tipo='P'))).values())))
    ivaAcreditado = getNumFloat(next(iter(pagosQS.aggregate(ivaAcreditado=Sum('total', filter=Q(impuesto='002') & Q(tipo='A'))).values())))

    isrPorPagar = isrCausado - isrRetenido - isrPagado -isrAcreditado
    ivaPorPagar = iva - ivaRetenido - ivaAcreditable -ivaPagado -ivaAcreditado


    acumulados = { 'ingresos': ingresos, 'gastos': gastos, 'base': base, 'isrCausado': isrCausado, 'isrRetenido': isrRetenido, 'isrPagado': isrPagado, 'isrAcreditado':isrAcreditado, 'isrPorPagar': isrPorPagar,
                  'ivaCausado': iva, 'ivaRetenido': ivaRetenido, 'ivaAcreditable': ivaAcreditable, 'ivaPagado': ivaPagado,'ivaAcreditado':ivaAcreditado, 'ivaPorPagar': ivaPorPagar}
    return acumulados




def getResponseContext(tipoReporte, usos, year, month):
    user = User.objects.last()
    rfc = user.satuser.rfc
    cfdis = ComprobanteCFDI.objects.filter(
        Q(emisorRFC=rfc) | Q(receptorRFC=rfc))
    cfdis = cfdis.filter(fecha__year=year)
    if tipoReporte == 'Y':
         month = date.today().month
    if tipoReporte == 'M':
        if month is None or month == '':
            month = date.today().month
        cfdis = cfdis.filter(Q(fecha__month=month))

    if usos['Emitidos'] == False:
        cfdis = cfdis.exclude(Q(emisorRFC=rfc))
    if usos['Personales'] == False:
        cfdis = cfdis.exclude(uso__isPartial='N', receptorRFC=rfc)
    if usos['Empresariales'] == False:
        cfdis = cfdis.exclude(uso__isPartial='Y', receptorRFC=rfc)

    '''
        for cfdi in cfdis:
            validacion = Validacion()
            estado = validacion.obtener_estado(cfdi.emisorRFC , cfdi.receptorRFC, str(cfdi.total), cfdi.uuid)
            cfdi.status = estado['estado']
            cfdi.save()
        '''
    '''if tipoReporte == 'M':
        topes = ClaveServicioConTopeCFDI.objects.filter(Q(isPatial='Y'))
    else:
        topes = ClaveServicioConTopeCFDI.objects.all()

    topeDeclara = {}
    for tope in topes:
        if tipoReporte == 'Y' and tope.isPatial == 'Y':
            topeDeclara[tope.claveProducto] = getNumFloat(tope.tope)*12
        elif tipoReporte == 'M' and tope.isPatial == 'N':
            topeDeclara[tope.claveProducto] = getNumFloat(tope.tope)/12
        else:
            topeDeclara[tope.claveProducto] = getNumFloat(tope.tope)
        toBeUpdated = cfdis.filter(
            Q(conceptocdfi__claveProducto=tope.claveProducto))
        for cfdi in toBeUpdated:
            cfdi.totalDeducible = cfdi.subtotal
            for conc in cfdi.conceptocdfi_set.filter(Q(claveProducto=tope.claveProducto)):
                if(conc.importe > topeDeclara[tope.claveProducto]):
                    cfdi.totalDeducible = cfdi.totalDeducible - \
                        (conc.importe - topeDeclara[tope.claveProducto])
                    impuestos = conc.impuestosconceptocfdi_set.filter(Q(idImpuesto ='002') & Q(idTipo='TRA') & Q(tipoFactor='Tasa'))        
                    for impuesto in impuestos:
                        quantituToSubstract = impuesto.importe - impuesto.tasaOCuota * topeDeclara[tope.claveProducto]
                        ivaToModified =cfdi.impuestoscdfi_set.filter(Q(idImpuesto ='002') & Q(idTipo='TRA')).first()
                        ivaToModified.importeDeducible = ivaToModified.importe - quantituToSubstract
                        ivaToModified.save()
                    topeDeclara[tope.claveProducto] = 0
                else:
                    topeDeclara[tope.claveProducto] = topeDeclara[tope.claveProducto] - conc.importe
            cfdi.save()'''

    cfdisIngresos = cfdis.filter(emisorRFC=rfc).filter(
        tipoComprobante='I').filter(status='Vigente') | cfdis.filter(emisorRFC=rfc).filter(
        tipoComprobante='I').filter(status='No Encontrado')
    
    for cfdi in cfdisIngresos:
        updateStatus(cfdi)

    qsIngresos = cfdis.filter(emisorRFC=rfc).filter(
        tipoComprobante='I').filter(status='Vigente') | cfdis.filter(emisorRFC=rfc).filter(
        tipoComprobante='I').filter(status='No Encontrado')
    totalIngreso = getNumFloat(
        next(iter(qsIngresos.aggregate(Sum('total')).values())))
    subtotalIngreso = getNumFloat(
        next(iter(qsIngresos.aggregate(Sum('subtotal')).values())))
    imptrasladadosIngreso = getNumFloat(
        next(iter(qsIngresos.aggregate(Sum('totalImpuestosTras')).values())))
    impretenidosIngreso = getNumFloat(
        next(iter(qsIngresos.aggregate(Sum('totalImpuestosRet')).values())))

    isrRetenidoIngreso = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='001') & Q(impuestoscdfi__idTipo='RET'))).values())))
    ivaRetenidoIngreso = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='RET'))).values())))
    ivaTrasladadoIngreso = getNumFloat(next(iter(qsIngresos.aggregate(isrRetenido=Sum(
        'impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values())))

    qsGastosI = cfdis.filter(receptorRFC=rfc).filter(
        tipoComprobante='I').filter(status='Vigente')
    qsGastosE = cfdis.filter(receptorRFC=rfc).filter(
        tipoComprobante='E').filter(status='Vigente')

    totalGastos = getNumFloat(next(iter(qsGastosI.aggregate(Sum('total')).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(Sum('total')).values())))
    subtotalGastos = getNumFloat(next(iter(qsGastosI.aggregate(Sum('subtotal')).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(Sum('subtotal')).values())))
    deducibleGastos = getNumFloat(next(iter(qsGastosI.aggregate(Sum('totalDeducible')).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(Sum('totalDeducible')).values())))
    imptrasladadosGastos = getNumFloat(next(iter(qsGastosI.aggregate(Sum('totalImpuestosTras')).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(Sum('totalImpuestosTras')).values())))
    impretenidosGastos = getNumFloat(next(iter(qsGastosI.aggregate(Sum('totalImpuestosRet')).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(Sum('totalImpuestosRet')).values())))
    isrRetenidoGastos = getNumFloat(next(iter(qsGastosI.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='001') & Q(impuestoscdfi__idTipo='RET'))).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='001') & Q(impuestoscdfi__idTipo='RET'))).values())))
    ivaRetenidoGastos = getNumFloat(next(iter(qsGastosI.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='RET'))).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='RET'))).values())))
    ivaTrasladadoGastos = getNumFloat(next(iter(qsGastosI.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values(
    )))) - getNumFloat(next(iter(qsGastosE.aggregate(isrRetenido=Sum('impuestoscdfi__importeDeducible', filter=Q(impuestoscdfi__idImpuesto='002') & Q(impuestoscdfi__idTipo='TRA'))).values())))

    ingresos = {'totalIngreso': totalIngreso, 'subtotalIngreso': subtotalIngreso, 'imptrasladadosIngreso': imptrasladadosIngreso, 'impretenidosIngreso': impretenidosIngreso,
                'isrRetenidoIngreso': isrRetenidoIngreso, 'ivaRetenidoIngreso': ivaRetenidoIngreso, 'ivaTrasladadoIngreso': ivaTrasladadoIngreso}
    gastos = {'totalGastos': totalGastos, 'subtotalGastos': subtotalGastos, 'deducibleGastos': deducibleGastos, 'imptrasladadosGastos': imptrasladadosGastos,
              'impretenidosGastos': impretenidosGastos, 'isrRetenidoGastos': isrRetenidoGastos, 'ivaRetenidoGastos': ivaRetenidoGastos, 'ivaTrasladadoGastos': ivaTrasladadoGastos}
    acumulados = getAcumulados(year, month)
    context = {'cfdis': cfdis, 'ingresos': ingresos, 'gastos': gastos, 'acumulados' : acumulados}

    return context


def createProfile():
    user = User.objects.get(username='boofalcon')
    profile = Satuser.objects.create(user=user, fielKey='Claveprivada_FIEL_FAMC8401278B9_20200619_130735.key',
                                     fielCer='famc8401278b9.cer', fielPas='Nimrod17', rfc='FAMC8401278B9')
    profile.save()


def getNumFloat(s):
    if s is None:
        return 0
    try:
        return float(s)
    except:
        return 0


def loadCatalog():
    connection = sqlite3.connect(":memory:")
    cursor = connection.cursor()

    sqlfile = open(settings.SAT_DIR[0] + "init.sql")
    sql_as_string = sqlfile.read()
    cursor.executescript(sql_as_string)

    for row in cursor.execute("SELECT * FROM app_usocfdi"):
        print(row)

def updateStatus(cfdi):
    validacion = Validacion()
    estado = validacion.obtener_estado(
    cfdi.emisorRFC, cfdi.receptorRFC, str(getNumFloat(cfdi.total)/getNumFloat(cfdi.tipoCambio)), cfdi.uuid)
    #      print(estado)
    cfdi.status = estado['estado']
    cfdi.save()

def loadComprobante(tree, file):
    folder = None
    cfdiTag = 'cfdi'
    root = tree.getroot()
    namespaces = {'cfdi': 'http://www.sat.gob.mx/cfd/3','cfdi4': 'http://www.sat.gob.mx/cfd/4',
                  'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital', 'iedu': 'http://www.sat.gob.mx/iedu'}
    # response uses a default namespace, and tags don't mention it
    # create a new ns map using an identifier of our choice
    try:
        uuid = root.find('cfdi:Complemento', namespaces).find(
        'tfd:TimbreFiscalDigital', namespaces).attrib['UUID']
    except Exception as e:
        uuid = root.find('cfdi4:Complemento', namespaces).find(
        'tfd:TimbreFiscalDigital', namespaces).attrib['UUID']
        cfdiTag = 'cfdi4'
    try:
        if ComprobanteCFDI.objects.filter(uuid=uuid).filter(tipoComprobante=root.attrib['TipoDeComprobante']).exists() == False:
            folder = root.attrib['Fecha'].replace('-', '')[0:6]
            cfdi = ComprobanteCFDI()
            cfdi.uuid = uuid
            cfdi.fileName = folder + '/' + file
            if 'MetodoPago' in root.attrib:
                cfdi.metodoPago = root.attrib['MetodoPago']
            cfdi.tipoComprobante = root.attrib['TipoDeComprobante']
            if 'TipoCambio' in root.attrib:
                cfdi.tipoCambio = root.attrib['TipoCambio']
            else:
                cfdi.tipoCambio = 1.0
            cfdi.total = getNumFloat(root.attrib['Total']) * getNumFloat(cfdi.tipoCambio)
            cfdi.subtotal = getNumFloat(root.attrib['SubTotal']) * getNumFloat(cfdi.tipoCambio)
            cfdi.totalDeducible = getNumFloat(root.attrib['SubTotal']) * getNumFloat(cfdi.tipoCambio)
            cfdi.certificado = root.attrib['NoCertificado']
            cfdi.moneda = root.attrib['Moneda']
            cfdi.fecha = parse(root.attrib['Fecha'])
            emisor = root.find(cfdiTag +':Emisor', namespaces)

            if 'CondicionesDePago' in root.attrib:
                cfdi.condiciones = root.attrib['CondicionesDePago']

            if emisor is not None:
                cfdi.emisorName = emisor.attrib['Nombre']
                cfdi.emisorRegimen = emisor.attrib['RegimenFiscal']
                cfdi.emisorRFC = emisor.attrib['Rfc']
            receptor = root.find(cfdiTag +':Receptor', namespaces)
            if receptor is not None:
                if 'Nombre' in receptor.attrib:
                    cfdi.receptorName = receptor.attrib['Nombre']
                cfdi.receptorRFC = receptor.attrib['Rfc']
                if UsoCFDI.objects.filter(
                    clave=receptor.attrib['UsoCFDI']).count() > 0 :
                        uso = UsoCFDI.objects.filter(
                        clave=receptor.attrib['UsoCFDI'])[0]
                        cfdi.uso = uso
            impuestos = root.find(cfdiTag +':Impuestos', namespaces)
            if impuestos is not None:
                if 'TotalImpuestosRetenidos' in impuestos.attrib:
                    cfdi.totalImpuestosRet = getNumFloat(
                        impuestos.attrib['TotalImpuestosRetenidos']) * getNumFloat(cfdi.tipoCambio)
                if 'TotalImpuestosTrasladados' in impuestos.attrib:
                    cfdi.totalImpuestosTras = getNumFloat(
                        impuestos.attrib['TotalImpuestosTrasladados']) * getNumFloat(cfdi.tipoCambio)
                    cfdi.totalImpuestosTrasDeducible = cfdi.totalImpuestosTras
            validacion = Validacion()
            estado = validacion.obtener_estado(
                cfdi.emisorRFC, cfdi.receptorRFC, getNumFloat(cfdi.total)/getNumFloat(cfdi.tipoCambio), cfdi.uuid)
    #      print(estado)
            cfdi.status = estado['estado']
            cfdi.save()

            if impuestos is not None:
                trasladados = impuestos.find(cfdiTag +':Traslados', namespaces)
                if trasladados is not None:
                    for child in trasladados:
                        impuesto = ImpuestosCDFI()
                        impuesto.comprobante = cfdi
                        impuesto.idImpuesto = child.attrib['Impuesto']
                        impuesto.idTipo = 'TRA'
                        if 'TipoFactor' in child.attrib:
                            impuesto.tipoFactor = child.attrib['TipoFactor']
                        if 'TasaOCuota' in child.attrib:
                            impuesto.tasaOCuota = getNumFloat(
                                child.attrib['TasaOCuota']) 
                        impuesto.importe = 0.0
                        if impuesto.tipoFactor != 'Exento':
                            impuesto.importe = getNumFloat(child.attrib['Importe']) * getNumFloat(cfdi.tipoCambio)
                            impuesto.importeDeducible = impuesto.importe
                        impuesto.save()
                retenciones = impuestos.find(cfdiTag +':Retenciones', namespaces)
                if retenciones is not None:
                    for child in retenciones:
                        impuesto = ImpuestosCDFI()
                        impuesto.comprobante = cfdi
                        impuesto.idImpuesto = child.attrib['Impuesto']
                        impuesto.idTipo = 'RET'
                        if 'TipoFactor' in child.attrib:
                            impuesto.tipoFactor = child.attrib['TipoFactor']
                        if 'TasaOCuota' in child.attrib:
                            impuesto.tasaOCuota = getNumFloat(
                                child.attrib['TasaOCuota'])
                        impuesto.importe = getNumFloat(child.attrib['Importe']) * getNumFloat(cfdi.tipoCambio)
                        impuesto.importeDeducible = impuesto.importe
                        impuesto.save()
            conceptos = root.find(cfdiTag +':Conceptos', namespaces)
            if conceptos is not None:
                for concepto in conceptos:
                    con = ConceptoCDFI()
                    con.comprobante = cfdi
                    con.claveProducto = concepto.attrib['ClaveProdServ']
                    con.cantidad = getNumFloat(concepto.attrib['Cantidad'])
                    con.unidad = concepto.attrib['ClaveUnidad']
                    con.des = concepto.attrib['Descripcion']
                    if 'Unidad' in concepto.attrib:
                        con.des = concepto.attrib['Descripcion'] + \
                            '-'+concepto.attrib['Unidad']
                    con.valorUnitario = getNumFloat(
                        concepto.attrib['ValorUnitario'])
                    con.importe = getNumFloat(concepto.attrib['Importe']) * getNumFloat(cfdi.tipoCambio)
                    con.save()
                    impuestos = concepto.find(cfdiTag +':Impuestos', namespaces)
                    if impuestos is not None:
                        trasladados = impuestos.find(
                            cfdiTag +':Traslados', namespaces)
                        if trasladados is not None:
                            for child in trasladados:
                                impuesto = ImpuestosConceptoCFDI()
                                impuesto.concepto = con
                                impuesto.idImpuesto = child.attrib['Impuesto']
                                impuesto.idTipo = 'TRA'
                                if 'TipoFactor' in child.attrib:
                                    impuesto.tipoFactor = child.attrib['TipoFactor']
                                if 'TasaOCuota' in child.attrib:
                                    impuesto.tasaOCuota = getNumFloat(
                                        child.attrib['TasaOCuota'])
                                if 'Base' in child.attrib:
                                    impuesto.base = getNumFloat(
                                        child.attrib['Base']) * getNumFloat(cfdi.tipoCambio)
                                if 'Importe' in child.attrib:
                                    impuesto.importe = getNumFloat(
                                        child.attrib['Importe']) * getNumFloat(cfdi.tipoCambio)
                                impuesto.save()
                        retenciones = impuestos.find(
                            cfdiTag +':Retenciones', namespaces)
                        if retenciones is not None:
                            for child in retenciones:
                                impuesto = ImpuestosConceptoCFDI()
                                impuesto.concepto = con
                                impuesto.idImpuesto = child.attrib['Impuesto']
                                impuesto.idTipo = 'RET'
                                impuesto.tipoFactor = child.attrib['TipoFactor']
                                if 'TipoFactor' in child.attrib:
                                    impuesto.tipoFactor = child.attrib['TipoFactor']
                                if 'TasaOCuota' in child.attrib:
                                    impuesto.tasaOCuota = getNumFloat(
                                        child.attrib['TasaOCuota'])
                                if 'Base' in child.attrib:
                                    impuesto.base = getNumFloat(
                                        child.attrib['Base']) * getNumFloat(cfdi.tipoCambio)
                                impuesto.importe = getNumFloat(
                                    child.attrib['Importe']) * getNumFloat(cfdi.tipoCambio)

                                impuesto.save()
                    complemento = concepto.find(
                        cfdiTag +":ComplementoConcepto", namespaces)
                    if complemento is not None:
                        colegiatura = complemento.find(
                            "iedu:instEducativas", namespaces)
                        if colegiatura is not None:
                            comp = ComplementoConceptoCDFI()
                            comp.concepto = con
                            comp.KeyName = 'CURP'
                            comp.KeyValue = colegiatura.attrib['CURP']
                            comp.save()

        else:
            folder = 'Duplicados'
    except Exception as e:
        print("*****ERROR****** " + str(e))
        folder = 'Error'
    return folder


def cargaCFDIs():
    files = os.listdir(settings.SAT_DIR[0] + 'TempFiles')
    for f in files:

        try:

            tree = ET.parse(settings.SAT_DIR[0] + 'TempFiles/'+f)
            print("Archivo CFDI:: " + f)
            res = loadComprobante(tree, f)
            if res is not None:
                try:
                    os.stat(settings.SAT_DIR[0] + res)
                except:
                    os.mkdir(settings.SAT_DIR[0] + res)
                with open(settings.SAT_DIR[0] + 'TempFiles/'+f, 'rb') as forigen:
                    with open(settings.SAT_DIR[0] + res + '/'+f, 'wb') as fdestino:
                        shutil.copyfileobj(forigen, fdestino)
                        if os.path.isfile(settings.SAT_DIR[0] + 'TempFiles/'+f):
                            os.remove(settings.SAT_DIR[0] + 'TempFiles/'+f)
        except:
            print("Warning: Archivo No es CFDI:: " + f)


def convert(d, name):
    with open(settings.SAT_DIR[0] + name + '.zip', 'wb') as result:
        result.write(base64.b64decode(d))
    zip_ref = zipfile.ZipFile(settings.SAT_DIR[0] + name + ".zip", 'r')
    zip_ref.extractall(settings.SAT_DIR[0] + 'TempFiles')
    zip_ref.close()


        



@login_required(login_url="/login/")
def index(request):
    return render(request, "index.html")


@login_required(login_url="/login/")
def pages(request):
    context = {}
    # All resource paths end in .html.
    # Pick out the html file name from the url. And load that template.
    try:

        load_template = request.path.split('/')[-1]
        html_template = loader.get_template(load_template)
        return HttpResponse(html_template.render(context, request))

    except template.TemplateDoesNotExist:

        html_template = loader.get_template('error-404.html')
        return HttpResponse(html_template.render(context, request))

    except:

        html_template = loader.get_template('error-500.html')
        return HttpResponse(html_template.render(context, request))
