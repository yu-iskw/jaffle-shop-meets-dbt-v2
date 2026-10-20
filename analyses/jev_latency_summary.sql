-- Article screenshot query: latency stats from the benchmark harness.
-- Prerequisite: make experiment-jev-article

with latest_run as (
    select max(run_at) as run_at
    from raw.jev_benchmark_runs
),

scoped as (
    select b.*
    from raw.jev_benchmark_runs as b
    inner join latest_run as l
        on b.run_at = l.run_at
)

select
    count(*) as call_count,
    round(sum(latency_ms), 1) as total_ms,
    round(min(latency_ms), 1) as min_ms,
    round(avg(latency_ms), 1) as mean_ms,
    round(quantile_cont(latency_ms, 0.5), 1) as p50_ms,
    round(quantile_cont(latency_ms, 0.95), 1) as p95_ms,
    round(max(latency_ms), 1) as max_ms,
    round(min(latency_ms) filter (where call_index = 0), 1) as cold_start_ms,
    round(avg(latency_ms) filter (where call_index > 0), 1) as warm_mean_ms
from scoped
