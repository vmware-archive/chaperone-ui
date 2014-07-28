from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from configure import views


urlpatterns = patterns('',
    url(r'^nsx$', login_required(views.nsx_index), name='nsx'),
    url(r'^sddc$', login_required(views.sddc_index), name='sddc'),
    url(r'^hvs$', login_required(views.hypervisors_index), name='hvs'),
    url(r'^run/nsx$', login_required(views.run_nsx_commands), name='run_nsx'),
    url(r'^run/sddc$', login_required(views.run_sddc_commands),
        name='run_sddc'),
    url(r'^run/hvs$', login_required(views.run_hvs_commands), name='run_hvs'),
    url(r'^tail/nsx$', login_required(views.tail_nsx_log), name='tail_nsx'),
    url(r'^tail/sddc$', login_required(views.tail_sddc_log), name='tail_sddc'),
    url(r'^tail/hvs$', login_required(views.tail_hvs_log), name='tail_hvs'),
    url(r'^hvs/nics$', login_required(views.get_nics), name='nics'),
)
