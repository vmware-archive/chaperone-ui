from django.conf.urls import patterns, url

from configure import views


urlpatterns = patterns('',
    url(r'^nsx$', views.nsx_index, name='nsx'),
    url(r'^sddc$', views.sddc_index, name='sddc'),
    url(r'^run/nsx$', views.run_nsx_commands, name='run_nsx'),
    url(r'^run/sddc$', views.run_sddc_commands, name='run_sddc'),
    url(r'^tail/nsx$', views.tail_nsx_log, name='tail_nsx'),
    url(r'^tail/sddc$', views.tail_sddc_log, name='tail_sddc'),
)
