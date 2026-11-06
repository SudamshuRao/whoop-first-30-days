-- How well the keyword rules agree with hand labels, one row per split and theme.
--   dev:  the first 100 reviews, adjudicated after seeing the rules; used to improve the rules.
--   test: 60 fresh reviews labelled blind after the rules were frozen; the only figures to report.
-- Precision: of the reviews the rule tagged, the share the hand label agrees with.
-- Recall: of the reviews the hand label tagged, the share the rule also caught.
with labels as (
    select split, review_id, theme, is_mentioned = 1 as by_hand
    from {{ ref('review_hand_labels') }}
),

rules as (
    select review_id, theme, true as by_rule
    from {{ ref('fct_review_themes') }}
),

joined as (
    select l.split, l.theme, l.by_hand, coalesce(r.by_rule, false) as by_rule
    from labels l
    left join rules r using (review_id, theme)
)

select
    j.split,
    j.theme,
    t.label,
    count(*)                                              as n_reviews,
    count(*) filter (where by_hand)                       as n_by_hand,
    count(*) filter (where by_rule)                       as n_by_rule,
    count(*) filter (where by_hand and by_rule)           as true_pos,
    count(*) filter (where by_rule and not by_hand)       as false_pos,
    count(*) filter (where by_hand and not by_rule)       as false_neg,
    count(*) filter (where by_hand and by_rule)::double
        / nullif(count(*) filter (where by_rule), 0)      as precision,
    count(*) filter (where by_hand and by_rule)::double
        / nullif(count(*) filter (where by_hand), 0)      as recall
from joined j
join {{ ref('review_themes') }} t using (theme)
group by j.split, j.theme, t.label
