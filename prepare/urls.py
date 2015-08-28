#
#  Copyright 2015 VMware, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from prepare import views
from supervio.decorators import login_required_ajax


urlpatterns = patterns('',
    url(r'^group$', login_required_ajax(views.get_group), name='group'),
    url(r'^save$', login_required_ajax(views.save_group), name='save'),
    url(r'^status$', login_required_ajax(views.get_group_status),
        name='status'),
    url(r'^(?P<name>[^/]+)/download$', login_required(views.download_file),
        name='download'),
)
