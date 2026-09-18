"""Values shared between the read path and the gather.

`JOB_STATS_CACHE_KEY` lives here rather than on the view so the runner can
invalidate it without importing the view layer.
"""

JOB_STATS_CACHE_KEY = 'jobs:stats:v1'
JOB_STATS_CACHE_SECONDS = 300

# How long a filtered result count stays good for. Short: a delete or a finished
# gather should correct the total quickly, and the count is only ever used for
# the page indicator.
COUNT_CACHE_SECONDS = 60
