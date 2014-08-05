from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from prepare import views
from vmosui.decorators import login_required_ajax


urlpatterns = patterns('',
    url(r'^group$', login_required_ajax(views.get_group), name='group'),
    url(r'^save$', login_required_ajax(views.save_group), name='save'),
    url(r'^status$', login_required_ajax(views.get_group_status),
        name='status'),
    url(r'^(?P<name>[^/]+)/download$', login_required(views.download_file),
        name='download'),
)
