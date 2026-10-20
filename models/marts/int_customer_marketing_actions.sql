{{
    config(
        materialized='table',
        enabled=var('enable_jev_udf_models', false) and target.type == 'duckdb'
    )
}}

{% set customer_limit = var('jev_customer_limit', 20) | int %}
{% set recent_order_limit = var('jev_recent_orders', 10) | int %}

with

sample as (

    select
        customer_id,
        count_lifetime_orders,
        first_ordered_at,
        last_ordered_at,
        lifetime_spend,
        customer_type
    from {{ ref('customers') }}
    where count_lifetime_orders > 0
    order by count_lifetime_orders desc, customer_id
    limit {{ customer_limit }}

),

recent_orders as (

    select
        o.customer_id,
        o.order_id,
        o.ordered_at
    from sample as s
    inner join {{ ref('orders') }} as o
        on o.customer_id = s.customer_id
    qualify dense_rank() over (
        partition by o.customer_id
        order by o.ordered_at desc
    ) <= {{ recent_order_limit }}

),

recent_order_items as (

    select
        ro.customer_id,
        ro.order_id,
        ro.ordered_at,
        oi.product_name,
        p.product_type
    from recent_orders as ro
    inner join {{ ref('order_items') }} as oi
        on oi.order_id = ro.order_id
    inner join {{ ref('products') }} as p
        on p.product_id = oi.product_id

),

orders_json as (

    select
        customer_id,
        order_id,
        ordered_at,
        json_group_array(
            json_object(
                'product_name', product_name,
                'product_type', product_type
            )
        ) as items
    from recent_order_items
    group by customer_id, order_id, ordered_at

),

orders_by_customer as (

    select
        customer_id,
        json_group_array(
            json_object(
                'order_id', order_id,
                'ordered_at', ordered_at,
                'items', items
            )
        ) as recent_orders
    from orders_json
    group by customer_id

),

customer_state as (

    select
        s.customer_id,
        json_object(
            'profile', json_object(
                'customer_id', s.customer_id,
                'count_lifetime_orders', s.count_lifetime_orders,
                'first_ordered_at', s.first_ordered_at,
                'last_ordered_at', s.last_ordered_at,
                'lifetime_spend', s.lifetime_spend,
                'customer_type', s.customer_type
            ),
            'recent_orders', coalesce(obc.recent_orders, json('[]'))
        )::varchar as customer_state
    from sample as s
    left join orders_by_customer as obc
        on obc.customer_id = s.customer_id

),

labeled as (

    select
        customer_id,
        jev_market_customer(customer_state) as marketing_json
    from customer_state

)

select
    customer_id,
    json_extract_string(marketing_json, '$.next_best_offer') as next_best_offer,
    json_extract(marketing_json, '$.next_best_offer_confidence')::double
        as next_best_offer_confidence,
    json_extract(marketing_json, '$.likely_to_redeem_promo')::double
        as likely_to_redeem_promo,
    json_extract(marketing_json, '$.campaign_priority')::double as campaign_priority,
    json_extract(marketing_json, '$.campaign_priority_confidence')::double
        as campaign_priority_confidence
from labeled
