-- One row per public Google Play review of the WHOOP app that has text.
-- Reviewer names were never downloaded; dates are in the local time of the machine that ran the download.
select
    review_id,
    reviewed_at,
    cast(reviewed_at as date)                                    as reviewed_date,
    score,
    trim(content)                                                as content,
    thumbs_up,
    app_version,
    has_reply,
    case when score <= 2 then 'negative'
         when score = 3  then 'neutral'
         else 'positive' end                                     as sentiment,
    reviewed_at >= '{{ var("whoop_5_launch_date") }}'::timestamp as is_since_whoop_5
from {{ source('reviews', 'whoop_google_play') }}
where content is not null and trim(content) <> ''
