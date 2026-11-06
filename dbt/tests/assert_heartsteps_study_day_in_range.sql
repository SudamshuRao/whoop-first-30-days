-- The trial ran about six weeks, but travel pauses stretch some calendars
-- (participant 31 spans 62 days around a holiday trip). Beyond 70 days means a date bug.
select * from {{ ref('int_heartsteps__decision_points') }}
where study_day < 0 or study_day > 70
