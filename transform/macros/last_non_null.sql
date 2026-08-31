{% macro last_non_null(column_name, order_column='scraped_at') %}
(ARRAY_AGG({{ column_name }} ORDER BY {{ order_column }} DESC)
    FILTER (WHERE {{ column_name }} IS NOT NULL))[1]
{% endmacro %}
