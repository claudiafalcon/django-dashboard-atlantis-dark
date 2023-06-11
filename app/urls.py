# -*- encoding: utf-8 -*-
"""
License: MIT
Copyright (c) 2019 - present AppSeed.us
"""

from django.urls import path, re_path
from app import views
from .views import DownloadCFDIView
from .views import ReportCFDIView
from .views import SimuladoView
from django.contrib.auth.decorators import login_required


urlpatterns = [
    # Matches any html file 
    re_path(r'^.*\.html', views.pages, name='pages'),


    # The home page
    path('', views.index, name='home'),
    path("downloadcfdi/", login_required(DownloadCFDIView.as_view(),login_url="/login/"), name="downloadcfdi"),
    path("reportecfdi/", login_required(ReportCFDIView.as_view(),login_url="/login/"), name="reportecfdi"),
    path("simulado/",login_required(SimuladoView.as_view(),login_url="/login/"),name='simulado'),
]
