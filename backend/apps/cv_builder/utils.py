from django.shortcuts import get_object_or_404

from apps.cv_builder.models import CVProfile


def get_user_cv_profile(user):
    return get_object_or_404(CVProfile, user=user)


def normalize_profile_url(value):
    if not value:
        return value
    value = value.strip()
    if value.startswith('http://') or value.startswith('https://'):
        return value
    if value.startswith('//'):
        return f'https:{value}'
    return f'https://{value}'


def reorder_owned_items(model, ordered_ids, owner_filter, id_field='id'):
    from django.db import transaction

    with transaction.atomic():
        for index, item_id in enumerate(ordered_ids):
            updated = model.objects.filter(**owner_filter, **{id_field: item_id}).update(order=index)
            if updated == 0:
                raise ValueError('Invalid or unauthorized ID in reorder list.')
