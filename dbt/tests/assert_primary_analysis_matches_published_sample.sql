-- Klasnja et al. (2019): 7,884 decision points outside travel, 6,331 of them available.
-- If this fails, our sample no longer matches the published analysis.
select count(*) as primary_analysis_rows
from {{ ref('fct_decision_points') }}
where is_in_primary_analysis
having count(*) <> 6331
