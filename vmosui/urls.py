from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required

from vmosui import views


admin.autodiscover()


urlpatterns = patterns('',
    url(r'^$', login_required(views.index), name='index'),
    url(r'^login$', views.login, name='login'),
    url(r'^logout$', views.logout, name='logout'),
    url(r'^prepare/', include('prepare.urls', namespace='prepare')),
    url(r'^deploy/', include('deploy.urls', namespace='deploy')),
    url(r'^configure/', include('configure.urls', namespace='configure')),
)
