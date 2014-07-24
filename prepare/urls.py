from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from prepare import views


urlpatterns = patterns('',
    url(r'^group$', login_required(views.get_group), name='group'),
    url(r'^save$', login_required(views.save_group), name='save'),
    url(r'status$', login_required(views.get_group_status), name='status'),
)
