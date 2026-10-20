{{ config(enabled=var('enable_jev_udf_models', false)) }}

-- Article screenshot query: marketing actions materialized by the dbt UDF model.
-- Prerequisite: make build-jev-udf

select
    customer_id,
    next_best_offer,
    round(next_best_offer_confidence, 2) as next_best_offer_confidence,
    round(likely_to_redeem_promo, 2) as likely_to_redeem_promo,
    round(campaign_priority, 2) as campaign_priority,
    round(campaign_priority_confidence, 2) as campaign_priority_confidence
from {{ ref('int_customer_marketing_actions') }}
order by campaign_priority desc, customer_id
