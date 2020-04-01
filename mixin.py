import logging
from typing import Union

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models.options import Options
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


# enrich type hint for mixin and the use of self._meta
class DjangoModelMetaType:
    _meta: Options


T = Union[models.Model, DjangoModelMetaType, 'ModelUpdateMixin']


class ModelUpdateMixin:
    """
    References for accessing Django fields:
    https://docs.djangoproject.com/en/2.2/ref/models/meta/#field-access-api
    https://docs.djangoproject.com/en/2.2/ref/models/fields/#field-attribute-reference
    """

    def update(self: T, data: dict):
        # update the model instance and its related instances based on the
        # given nested dictionary `data`
        self._check_value_type(self, data, dict)

        for key, value in data.items():
            # Get the model field by field name and update field
            try:
                field = self._meta.get_field(key)
                self.update_field(field, value)

            except FieldDoesNotExist as err:
                logger.info(
                    f'[partial update] unable to retrieve field '
                    f'`{key}` in `{self}` - {err}'
                )

        self.save()

    def update_field(self: T, field: models.Field, value):
        # non-relational field can be updated
        if not field.is_relation:
            setattr(self, field.name, value)
            return

        is_updatable = issubclass(field.related_model, __class__)

        # ForeignKey (many_to_one / forward relationship) can be updated
        if field.is_relation and field.many_to_one and is_updatable:
            self._handle_many_to_one_relation(field, value)
            return

        # ForeignKey on the related model (reverse relationship)
        if field.is_relation and field.one_to_many and is_updatable:
            self._handle_one_to_many_relation(field, value)
            return

        # skip if
        #   the related instance does not have `.update()`, or
        #   the field relationship is not supported
        self._skip_update(field)

    def _handle_many_to_one_relation(self: T, field: models.Field, value):
        related_instance = getattr(self, field.name, None)

        # create new instance if not exist
        if related_instance is None:
            related_instance = field.related_model.objects.create()

        # invoke `.update()` of the related instance recursively
        related_instance.update(value)

        setattr(self, field.name, related_instance)

    def _handle_one_to_many_relation(self: T, field: models.Field, values):
        # field is `ManyToOneRel`
        related_model = field.related_model
        related_pk_name = related_model._meta.pk.attname
        related_object_manager = getattr(self, field.name)

        self._check_value_type(field, values, list)

        for value in values:
            # create mode if primary key is not given, update mode vice versa
            pk = value.get(related_pk_name)

            if pk is None:
                related_instance = related_object_manager.create()
            else:
                related_instance = related_object_manager.filter(pk=pk).first()

            # related_instance could be None if the provided pk is not a
            # child of this resource
            if related_instance:
                related_instance.update(value)

    def _check_value_type(
        self: T,
        target: Union[models.Field, T],
        value,
        expected_type: type,
    ):
        if not isinstance(value, expected_type):
            msg = f'[partial update] unable to update `{target}`. ' \
                f'Expect a `{expected_type}` but got `{type(value)}`'
            logger.exception(msg)
            raise ValidationError(msg)

    def _skip_update(self: T, field: models.Field):
        logger.warning(
            f'[partial update] unable to update field {field} in `{self}`',
            exc_info=True,
        )
