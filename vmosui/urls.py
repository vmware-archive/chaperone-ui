from django.conf.urls import patterns, include, url
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', 'vmosui.views.index', name='index'),
    url(r'^prepare/', include('prepare.urls', namespace='prepare')),
    url(r'^deploy/', include('deploy.urls', namespace='deploy')),
    url(r'^configure/', include('configure.urls', namespace='configure')),
)
