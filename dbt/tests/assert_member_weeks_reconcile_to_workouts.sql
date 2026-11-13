-- Every workout must land in exactly one member-week: totals must match.
select
    (select sum(n_workouts) from {{ ref('fct_member_weeks') }}) as weekly_total,
    (select count(*) from {{ ref('fct_workouts') }})            as workout_total
where (select sum(n_workouts) from {{ ref('fct_member_weeks') }})
   <> (select count(*) from {{ ref('fct_workouts') }})
