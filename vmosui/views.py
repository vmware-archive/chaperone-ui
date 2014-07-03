import fcntl
import yaml

from django.conf import settings
from django.shortcuts import render


ANSWER_FILE_COOKIE = 'answerfile'


def index(request):
    filename = request.COOKIES.get(ANSWER_FILE_COOKIE)
    # TODO: Use user chosen file.
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        containers = yaml.load(fp)
        fcntl.flock(fp, fcntl.LOCK_UN)
    
    return render(request, 'vmosui/index.html', {
        'containers': containers,
    })
