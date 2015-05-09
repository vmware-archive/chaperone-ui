from django.conf import settings


def SuperVIO(request):
    """ SuperVIO UI context processor.

    Adds data needed by all templates to the context.
    """
    context = {
        'user': request.user,
        'settings': settings,
    }
    return context
