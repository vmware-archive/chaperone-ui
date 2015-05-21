from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required

from supervio import views
from supervio.decorators import login_required_ajax


admin.autodiscover()


urlpatterns = patterns('',
    url(r'^$', login_required(views.index), name='index'),
    url(r'^login$', views.login, name='login'),
    url(r'^logout$', views.logout, name='logout'),
    url(r'^options$', login_required(views.list_options), name='options'),
    url(r'^savevc$', login_required_ajax(views.save_vcenter), name='savevc'),
    url(r'^vcenter$', login_required(views.vcenter_settings), name='vcenter'),
    url(r'^prepare/', include('prepare.urls', namespace='prepare')),
    url(r'^execute/', include('execute.urls', namespace='execute')),
)
