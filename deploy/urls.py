from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from deploy import views
from vmosui.decorators import login_required_ajax


urlpatterns = patterns('',
    url(r'^nsx$', login_required_ajax(views.nsx_index), name='nsx'),
    url(r'^sddc$', login_required_ajax(views.sddc_index), name='sddc'),
    url(r'^run/nsx$', login_required_ajax(views.run_nsx_commands),
        name='run_nsx'),
    url(r'^run/sddc$', login_required_ajax(views.run_sddc_commands),
        name='run_sddc'),
    url(r'^tail/nsx$', login_required_ajax(views.tail_nsx_log),
        name='tail_nsx'),
    url(r'^tail/sddc$', login_required_ajax(views.tail_sddc_log),
        name='tail_sddc'),
)
