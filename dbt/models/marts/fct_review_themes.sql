-- One row per review and theme it mentions, matched with the keyword rules in seeds/review_themes.csv.
-- Rules are deliberately simple and transparent; their accuracy is measured on a hand-labelled sample.
select
    r.review_id,
    t.theme
from {{ ref('stg_reviews__google_play') }} r
join {{ ref('review_themes') }} t
    on regexp_matches(lower(r.content), t.pattern)
