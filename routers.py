from rest_framework.routers import SimpleRouter


class OptionalTrailingSlashRouter(SimpleRouter):

    def __init__(self):
        """
        SimpleRouter only strictly opt-in or opt-out trailing slash
        This custom router override URL regex to allow optional trailing slash
        """
        super().__init__()
        self.trailing_slash = '/?'

    def get_urls(self):
        """
        Thanks to the hard-code in Django REST SimpleRouter which tried to
        strip out part of the regex in the list URL

        https://github.com/encode/django-rest-framework/blob/master/rest_framework/routers.py#L273-L278

        This results in an invalid regex `^?$` (because the slash is striped)
        which cannot be complied by Django URL resolver, so we need another
        hard-code here to unwind the hard-code in the base class...
        """
        urls = super().get_urls()

        for url in urls:
            if url.pattern._regex == '^?$':
                url.pattern._regex = '^$'

        return urls
