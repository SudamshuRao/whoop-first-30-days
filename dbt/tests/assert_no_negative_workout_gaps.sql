-- Workouts are ordered by start time, so a gap can never be negative.
select * from {{ ref('int_endomondo__workout_gaps') }}
where days_since_prev < 0
