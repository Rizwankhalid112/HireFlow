"""Make the location filter index-backed.

`location_raw__icontains` is the one filter on the jobs list that no btree can
serve: a leading wildcard (`%london%`) cannot use an ordinary index, so Postgres
had no choice but to scan the table. At 2,758 rows that is 23ms and invisible;
at the millions this schema is sized for it is the slowest thing in the product.

A GIN index with `gin_trgm_ops` indexes the three-character sequences of the
column, which is exactly what a substring match needs — so `%london%` becomes an
index lookup.

The raw string is what we filter on deliberately. `location_city` and
`location_country` are normalised and already indexed, but `split_location`
leaves them blank whenever it does not recognise a country, and half of real
listings land there — "Remote", "Cardiff, London or Remote (UK)". Filtering on
the normalised columns alone would silently hide rows whose location the user
can read on the card.
"""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0001_initial'),
    ]

    operations = [
        TrigramExtension(),
        migrations.AddIndex(
            model_name='job',
            index=GinIndex(
                fields=['location_raw'],
                opclasses=['gin_trgm_ops'],
                name='job_location_trgm_idx',
            ),
        ),
    ]
