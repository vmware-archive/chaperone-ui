from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from execute import views
from vmosui.decorators import login_required_ajax


urlpatterns = patterns('',
    url(r'^$', login_required_ajax(views.index), name='index'),
    url(r'^run$', login_required_ajax(views.run_commands), name='run'),
    url(r'^tail$', login_required_ajax(views.tail_log), name='tail'),
)
