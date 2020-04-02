import logging
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework.exceptions import NotFound
from rest_framework.views import exception_handler
from typing import List, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

NON_CLONEABLE_MODELS: List[str] = [
    'User',
]


@transaction.atomic
def clone_instance(instance: T) -> T:
    """
    Clone any django model instance and its related instances recursively
    Ignore many-to-many or one-to-many relationship (reverse foreign key)
    Also ignore user model

    ref:
        https://docs.djangoproject.com/en/2.2/ref/models/fields/#attributes-for-fields-with-relations
        https://github.com/jackton1/django-clone/blob/master/model_clone/mixins/clone.py
    """
    # initialize a new instance
    cloned_instance = instance.__class__()

    fields = instance._meta.get_fields()
    for field in fields:
        # only clone one-to-one or forward foreign key relationship
        # ignore many-to-many or reverse foreign key relationship
        if field.one_to_one or field.many_to_one:
            _related = getattr(instance, field.name)

            # skip if related instance is None
            if _related is None:
                continue

            # use the same reference for non-cloneable related models
            if field.related_model.__name__ in NON_CLONEABLE_MODELS:
                setattr(cloned_instance, field.name, _related)
            else:
                _cloned_related = clone_instance(_related)
                setattr(cloned_instance, field.name, _cloned_related)

        # simply copy the value for those non-relation fields
        if not field.is_relation:
            _value = getattr(instance, field.name)
            setattr(cloned_instance, field.name, _value)

    # set primary key as None to save a new record in DB
    cloned_instance.pk = None
    cloned_instance.save()
    return cloned_instance


def exception_logging_handler(exc: Exception, context: dict):
    """
    Intercept DRF error handler to log the error message

    Update the REST_FRAMEWORK setting in settings.py to use this handler

    REST_FRAMEWORK = {
        'EXCEPTION_HANDLER': 'core.exception_logging_handler',
    }
    """
    logger.warning(exc)

    # translate uncaught Django ObjectDoesNotExist exception to NotFound
    if isinstance(exc, ObjectDoesNotExist):
        logger.error(f'uncaught ObjectDoesNotExist error: {exc} - {context}')
        exc = NotFound(str(exc))

    # follow DRF default exception handler
    response = exception_handler(exc, context)
    return response
