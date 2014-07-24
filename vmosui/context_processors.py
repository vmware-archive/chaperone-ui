def Vmosui(request):
    """ VMOS UI context processor.

    Adds data needed by all templates to the context.
    """
    context = {
        'user': request.user,
    }
    return context
