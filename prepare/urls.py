from django.conf.urls import patterns, url

from prepare import views


urlpatterns = patterns('',
    url(r'^group$', views.get_group, name='group'),
    url(r'^save$', views.save_group, name='save'),
    url(r'status$', views.get_group_status, name='status'),
)
