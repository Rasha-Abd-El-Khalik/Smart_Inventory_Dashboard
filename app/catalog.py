from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass(frozen=True)
class TableColumn:
    label: str
    ref: Optional[str] = None

    computed: bool = False

@dataclass(frozen=True)
class WidgetDef:
    id: str
    dashboard: str
    chart_type: str
    title_fallback: str
    required_columns: List[str]
    sql: str

    title_fallback_ar: Optional[str] = None
    value_ref: Optional[str] = None
    x_ref: Optional[str] = None
    y_ref: Optional[str] = None
    time_ref: Optional[str] = None
    table_columns: Optional[List[TableColumn]] = None

WIDGETS: List[WidgetDef] = [

    WidgetDef(
        id="total_revenue",
        dashboard="sales",
        chart_type="kpi",
        title_fallback="Total Revenue",
        title_fallback_ar="إجمالي الإيرادات",
        required_columns=["order_item.extended_price", "order_item.discount"],
        sql="""
            SELECT SUM({order_item.extended_price} - {order_item.discount}) AS value
            FROM {order_item.__table__}
        """,
        value_ref=None,
    ),
    WidgetDef(
        id="total_orders",
        dashboard="sales",
        chart_type="kpi",
        title_fallback="Total Orders",
        title_fallback_ar="إجمالي الطلبات",
        required_columns=["order.order_id"],
        sql="SELECT COUNT({order.order_id}) AS value FROM {order.__table__}",
        value_ref="order.order_id",
    ),
    WidgetDef(
        id="total_items_sold",
        dashboard="sales",
        chart_type="kpi",
        title_fallback="Total Items Sold",
        title_fallback_ar="إجمالي القطع المباعة",
        required_columns=["order_item.quantity"],
        sql="SELECT SUM({order_item.quantity}) AS value FROM {order_item.__table__}",
        value_ref="order_item.quantity",
    ),
    WidgetDef(
        id="total_cost",
        dashboard="sales",
        chart_type="kpi",
        title_fallback="Total Cost",
        title_fallback_ar="إجمالي التكلفة",
        required_columns=["order_item.quantity", "order_item.product_id", "product.product_id", "product.cost"],
        sql="""
            SELECT SUM({order_item.quantity} * {product.cost}) AS value
            FROM {order_item.__table__}
            JOIN {product.__table__} ON {order_item.product_id} = {product.product_id}
        """,
        value_ref=None,
    ),
    WidgetDef(
        id="gross_margin",
        dashboard="sales",
        chart_type="kpi",
        title_fallback="Gross Margin",
        title_fallback_ar="هامش الربح الإجمالي",
        required_columns=[
            "order_item.extended_price", "order_item.discount",
            "order_item.quantity", "order_item.product_id",
            "product.product_id", "product.cost",
        ],
        sql="""
            SELECT
                SUM({order_item.extended_price} - {order_item.discount})
                - SUM({order_item.quantity} * {product.cost}) AS value
            FROM {order_item.__table__}
            JOIN {product.__table__} ON {order_item.product_id} = {product.product_id}
        """,
        value_ref=None,
    ),
    WidgetDef(
        id="margin_pct",
        dashboard="sales",
        chart_type="kpi",
        title_fallback="Margin %",
        title_fallback_ar="نسبة الهامش",
        required_columns=[
            "order_item.extended_price", "order_item.discount",
            "order_item.quantity", "order_item.product_id",
            "product.product_id", "product.cost",
        ],
        sql="""
            SELECT
                (SUM({order_item.extended_price} - {order_item.discount})
                 - SUM({order_item.quantity} * {product.cost}))
                / NULLIF(SUM({order_item.extended_price} - {order_item.discount}), 0) AS value
            FROM {order_item.__table__}
            JOIN {product.__table__} ON {order_item.product_id} = {product.product_id}
        """,
        value_ref=None,
    ),
    WidgetDef(
        id="average_order_value",
        dashboard="sales",
        chart_type="kpi",
        title_fallback="Average Order Value",
        title_fallback_ar="متوسط قيمة الطلب",
        required_columns=["order_item.extended_price", "order_item.discount", "order_item.order_id"],
        sql="""
            SELECT
                SUM({order_item.extended_price} - {order_item.discount})
                / NULLIF(COUNT(DISTINCT {order_item.order_id}), 0) AS value
            FROM {order_item.__table__}
        """,
        value_ref=None,
    ),
    WidgetDef(
        id="revenue_over_time",
        dashboard="sales",
        chart_type="line",
        title_fallback="Revenue Over Time",
        title_fallback_ar="الإيرادات عبر الزمن",
        required_columns=["order.order_id", "order.order_date", "order_item.order_id", "order_item.extended_price"],
        time_ref="order.order_date",
        y_ref=None,
        sql="""
            SELECT {bucket_expr} AS x, SUM({order_item.extended_price}) AS y
            FROM {order_item.__table__}
            JOIN {order.__table__} ON {order_item.order_id} = {order.order_id}
            WHERE 1=1 {date_filter}
            GROUP BY x
            ORDER BY x
        """,
    ),
    WidgetDef(
        id="orders_over_time",
        dashboard="sales",
        chart_type="line",
        title_fallback="Orders Over Time",
        title_fallback_ar="الطلبات عبر الزمن",
        required_columns=["order.order_id", "order.order_date"],
        time_ref="order.order_date",
        y_ref=None,
        sql="""
            SELECT {bucket_expr} AS x, COUNT({order.order_id}) AS y
            FROM {order.__table__}
            WHERE 1=1 {date_filter}
            GROUP BY x
            ORDER BY x
        """,
    ),
    WidgetDef(
        id="revenue_by_payment_type",
        dashboard="sales",
        chart_type="bar",
        title_fallback="Revenue by Payment Type",
        title_fallback_ar="الإيرادات حسب طريقة الدفع",
        required_columns=["payment.payment_type", "payment.payment_value"],
        x_ref="payment.payment_type",
        y_ref="payment.payment_value",
        sql="""
            SELECT {payment.payment_type} AS x, SUM({payment.payment_value}) AS y
            FROM {payment.__table__}
            GROUP BY {payment.payment_type}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="orders_by_status",
        dashboard="sales",
        chart_type="pie",
        title_fallback="Orders by Status",
        title_fallback_ar="الطلبات حسب الحالة",
        required_columns=["order.order_status"],
        x_ref="order.order_status",
        y_ref=None,
        sql="""
            SELECT {order.order_status} AS x, COUNT(*) AS y
            FROM {order.__table__}
            GROUP BY {order.order_status}
        """,
    ),

    WidgetDef(
        id="distribution_centers_count",
        dashboard="inventory",
        chart_type="kpi",
        title_fallback="Distribution Centers",
        title_fallback_ar="عدد مراكز التوزيع",
        required_columns=["distribution_center.distribution_center_id"],
        sql="SELECT COUNT({distribution_center.distribution_center_id}) AS value FROM {distribution_center.__table__}",
        value_ref="distribution_center.distribution_center_id",
    ),
    WidgetDef(
        id="items_in_stock",
        dashboard="inventory",
        chart_type="kpi",
        title_fallback="Items In Stock",
        title_fallback_ar="القطع المتوفرة في المخزون",
        required_columns=["inventory_item.status"],
        sql="""
            SELECT COUNT(*) AS value
            FROM {inventory_item.__table__}
            WHERE {inventory_item.status} = 'available'
        """,
        value_ref=None,
    ),
    WidgetDef(
        id="stock_by_distribution_center",
        dashboard="inventory",
        chart_type="bar",
        title_fallback="Stock by Distribution Center",
        title_fallback_ar="المخزون حسب مركز التوزيع",
        required_columns=["inventory_item.distribution_center_id", "inventory_item.status"],
        x_ref="inventory_item.distribution_center_id",
        y_ref=None,
        sql="""
            SELECT {inventory_item.distribution_center_id} AS x, COUNT(*) AS y
            FROM {inventory_item.__table__}
            GROUP BY {inventory_item.distribution_center_id}
        """,
    ),
    WidgetDef(
        id="sold_vs_available",
        dashboard="inventory",
        chart_type="pie",
        title_fallback="Sold vs Available",
        title_fallback_ar="المباع مقابل المتاح",
        required_columns=["inventory_item.status"],
        x_ref="inventory_item.status",
        y_ref=None,
        sql="""
            SELECT {inventory_item.status} AS x, COUNT(*) AS y
            FROM {inventory_item.__table__}
            GROUP BY {inventory_item.status}
        """,
    ),
    WidgetDef(
        id="stock_movements_over_time",
        dashboard="inventory",
        chart_type="line",
        title_fallback="Stock Movements Over Time",
        title_fallback_ar="حركة المخزون عبر الزمن",
        required_columns=["stock_movement.created_at", "stock_movement.quantity"],
        time_ref="stock_movement.created_at",
        y_ref="stock_movement.quantity",
        sql="""
            SELECT {bucket_expr} AS x, SUM({stock_movement.quantity}) AS y
            FROM {stock_movement.__table__}
            WHERE 1=1 {date_filter}
            GROUP BY x
            ORDER BY x
        """,
    ),
    WidgetDef(
        id="stock_movements_by_type",
        dashboard="inventory",
        chart_type="bar",
        title_fallback="Stock Movements by Type",
        title_fallback_ar="حركة المخزون حسب النوع",
        required_columns=["stock_movement.type", "stock_movement.quantity"],
        x_ref="stock_movement.type",
        y_ref="stock_movement.quantity",
        sql="""
            SELECT {stock_movement.type} AS x, SUM({stock_movement.quantity}) AS y
            FROM {stock_movement.__table__}
            GROUP BY {stock_movement.type}
        """,
    ),
    WidgetDef(
        id="low_stock_products",
        dashboard="inventory",
        chart_type="table",
        title_fallback="Low-Stock Products",
        title_fallback_ar="منتجات منخفضة المخزون",
        required_columns=["inventory_item.product_id", "inventory_item.status", "product.product_id", "product.product_name"],
        sql="""
            SELECT {product.product_name} AS product_name, COUNT(*) AS units_in_stock
            FROM {inventory_item.__table__}
            JOIN {product.__table__} ON {inventory_item.product_id} = {product.product_id}
            WHERE {inventory_item.status} = 'available'
            GROUP BY {product.product_id}, {product.product_name}
            HAVING COUNT(*) < 10
            ORDER BY units_in_stock ASC
        """,
        table_columns=[
            TableColumn(label="Product", ref="product.product_name"),
            TableColumn(label="Units In Stock", computed=True),
        ],
    ),
    WidgetDef(
        id="rental_cost_by_center",
        dashboard="inventory",
        chart_type="bar",
        title_fallback="Rental Cost by Center",
        title_fallback_ar="تكلفة الإيجار حسب المركز",
        required_columns=["distribution_center.distribution_center_name", "distribution_center.rental_cost"],
        x_ref="distribution_center.distribution_center_name",
        y_ref="distribution_center.rental_cost",
        sql="""
            SELECT {distribution_center.distribution_center_name} AS x, {distribution_center.rental_cost} AS y
            FROM {distribution_center.__table__}
            ORDER BY y DESC
        """,
    ),

    WidgetDef(
        id="total_suppliers",
        dashboard="suppliers",
        chart_type="kpi",
        title_fallback="Total Suppliers",
        title_fallback_ar="إجمالي الموردين",
        required_columns=["supplier.supplier_id"],
        sql="SELECT COUNT({supplier.supplier_id}) AS value FROM {supplier.__table__}",
        value_ref="supplier.supplier_id",
    ),
    WidgetDef(
        id="supplier_account_balances",
        dashboard="suppliers",
        chart_type="table",
        title_fallback="Supplier Account Balances",
        title_fallback_ar="أرصدة حسابات الموردين",
        required_columns=["supplier.supplier_id", "supplier.account_balance"],
        sql="""
            SELECT {supplier.supplier_id} AS supplier_id, {supplier.account_balance} AS account_balance
            FROM {supplier.__table__}
            ORDER BY account_balance DESC
        """,
        table_columns=[
            TableColumn(label="Supplier", ref="supplier.supplier_id"),
            TableColumn(label="Account Balance", ref="supplier.account_balance"),
        ],
    ),
    WidgetDef(
        id="items_supplied_per_supplier",
        dashboard="suppliers",
        chart_type="bar",
        title_fallback="Items Supplied per Supplier",
        title_fallback_ar="القطع الموردة لكل مورد",
        required_columns=["order_item.supplier_id", "order_item.quantity"],
        x_ref="order_item.supplier_id",
        y_ref="order_item.quantity",
        sql="""
            SELECT {order_item.supplier_id} AS x, SUM({order_item.quantity}) AS y
            FROM {order_item.__table__}
            GROUP BY {order_item.supplier_id}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="suppliers_by_country",
        dashboard="suppliers",
        chart_type="bar",
        title_fallback="Suppliers by Country",
        title_fallback_ar="الموردون حسب الدولة",
        required_columns=["supplier.country"],
        x_ref="supplier.country",
        y_ref=None,
        sql="""
            SELECT {supplier.country} AS x, COUNT(*) AS y
            FROM {supplier.__table__}
            GROUP BY {supplier.country}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="inventory_supplied_per_supplier",
        dashboard="suppliers",
        chart_type="bar",
        title_fallback="Inventory Supplied per Supplier",
        title_fallback_ar="المخزون المورد لكل مورد",
        required_columns=["inventory_item.supplier_id"],
        x_ref="inventory_item.supplier_id",
        y_ref=None,
        sql="""
            SELECT {inventory_item.supplier_id} AS x, COUNT(*) AS y
            FROM {inventory_item.__table__}
            GROUP BY {inventory_item.supplier_id}
            ORDER BY y DESC
        """,
    ),

    WidgetDef(
        id="total_purchase_orders",
        dashboard="purchasing",
        chart_type="kpi",
        title_fallback="Total Purchase Orders",
        title_fallback_ar="إجمالي أوامر الشراء",
        required_columns=["purchase_order.id"],
        sql="SELECT COUNT({purchase_order.id}) AS value FROM {purchase_order.__table__}",
        value_ref="purchase_order.id",
    ),
    WidgetDef(
        id="total_purchase_spend",
        dashboard="purchasing",
        chart_type="kpi",
        title_fallback="Total Purchase Spend",
        title_fallback_ar="إجمالي إنفاق الشراء",
        required_columns=["purchase_order.total_amount"],
        sql="SELECT SUM({purchase_order.total_amount}) AS value FROM {purchase_order.__table__}",
        value_ref="purchase_order.total_amount",
    ),
    WidgetDef(
        id="purchase_orders_by_status",
        dashboard="purchasing",
        chart_type="pie",
        title_fallback="Purchase Orders by Status",
        title_fallback_ar="أوامر الشراء حسب الحالة",
        required_columns=["purchase_order.status"],
        x_ref="purchase_order.status",
        y_ref=None,
        sql="""
            SELECT {purchase_order.status} AS x, COUNT(*) AS y
            FROM {purchase_order.__table__}
            GROUP BY {purchase_order.status}
        """,
    ),
    WidgetDef(
        id="purchase_spend_over_time",
        dashboard="purchasing",
        chart_type="line",
        title_fallback="Purchase Spend Over Time",
        title_fallback_ar="إنفاق الشراء عبر الزمن",
        required_columns=["purchase_order.order_date", "purchase_order.total_amount"],
        time_ref="purchase_order.order_date",
        y_ref="purchase_order.total_amount",
        sql="""
            SELECT {bucket_expr} AS x, SUM({purchase_order.total_amount}) AS y
            FROM {purchase_order.__table__}
            WHERE 1=1 {date_filter}
            GROUP BY x
            ORDER BY x
        """,
    ),
    WidgetDef(
        id="spend_by_supplier",
        dashboard="purchasing",
        chart_type="bar",
        title_fallback="Spend by Supplier",
        title_fallback_ar="الإنفاق حسب المورد",
        required_columns=["purchase_order.supplier_id", "purchase_order.total_amount"],
        x_ref="purchase_order.supplier_id",
        y_ref="purchase_order.total_amount",
        sql="""
            SELECT {purchase_order.supplier_id} AS x, SUM({purchase_order.total_amount}) AS y
            FROM {purchase_order.__table__}
            GROUP BY {purchase_order.supplier_id}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="ordered_vs_received_quantity",
        dashboard="purchasing",
        chart_type="bar",
        title_fallback="Ordered vs Received Quantity",
        title_fallback_ar="الكمية المطلوبة مقابل المستلمة",
        required_columns=["purchase_order_item.quantity_ordered", "purchase_order_item.quantity_received"],
        x_ref=None,
        y_ref=None,
        sql="""
            SELECT 'Ordered' AS x, SUM({purchase_order_item.quantity_ordered}) AS y
            FROM {purchase_order_item.__table__}
            UNION ALL
            SELECT 'Received' AS x, SUM({purchase_order_item.quantity_received}) AS y
            FROM {purchase_order_item.__table__}
        """,
    ),
    WidgetDef(
        id="average_delivery_delay",
        dashboard="purchasing",
        chart_type="kpi",
        title_fallback="Average Delivery Delay (Days)",
        title_fallback_ar="متوسط تأخير التسليم (بالأيام)",
        required_columns=["purchase_order.expected_delivery_date", "purchase_order.received_at"],
        sql="""
            SELECT AVG(DATEDIFF({purchase_order.received_at}, {purchase_order.expected_delivery_date})) AS value
            FROM {purchase_order.__table__}
            WHERE {purchase_order.received_at} IS NOT NULL
        """,
        value_ref=None,
    ),

    WidgetDef(
        id="total_products",
        dashboard="products",
        chart_type="kpi",
        title_fallback="Total Products",
        title_fallback_ar="إجمالي المنتجات",
        required_columns=["product.product_id"],
        sql="SELECT COUNT({product.product_id}) AS value FROM {product.__table__}",
        value_ref="product.product_id",
    ),
    WidgetDef(
        id="products_by_category",
        dashboard="products",
        chart_type="bar",
        title_fallback="Products by Category",
        title_fallback_ar="المنتجات حسب الفئة",
        required_columns=["product.product_id", "product.category_name"],
        x_ref="product.category_name",
        y_ref=None,
        sql="""
            SELECT {product.category_name} AS x, COUNT({product.product_id}) AS y
            FROM {product.__table__}
            GROUP BY {product.category_name}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="active_vs_discontinued",
        dashboard="products",
        chart_type="pie",
        title_fallback="Active vs Discontinued",
        title_fallback_ar="النشط مقابل الموقوف",
        required_columns=["product.discontinued"],
        x_ref="product.discontinued",
        y_ref=None,
        sql="""
            SELECT {product.discontinued} AS x, COUNT(*) AS y
            FROM {product.__table__}
            GROUP BY {product.discontinued}
        """,
    ),
    WidgetDef(
        id="average_lead_time_by_category",
        dashboard="products",
        chart_type="bar",
        title_fallback="Average Lead Time by Category",
        title_fallback_ar="متوسط مدة التوريد حسب الفئة",
        required_columns=["product.lead_time", "product.category_name"],
        x_ref="product.category_name",
        y_ref="product.lead_time",
        sql="""
            SELECT {product.category_name} AS x, AVG({product.lead_time}) AS y
            FROM {product.__table__}
            GROUP BY {product.category_name}
        """,
    ),
    WidgetDef(
        id="products_by_supplier",
        dashboard="products",
        chart_type="bar",
        title_fallback="Products by Supplier",
        title_fallback_ar="المنتجات حسب المورد",
        required_columns=["inventory_item.supplier_id", "inventory_item.product_id"],
        x_ref="inventory_item.supplier_id",
        y_ref=None,
        sql="""
            SELECT {inventory_item.supplier_id} AS x, COUNT(DISTINCT {inventory_item.product_id}) AS y
            FROM {inventory_item.__table__}
            GROUP BY {inventory_item.supplier_id}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="cost_vs_retail_price",
        dashboard="products",
        chart_type="table",
        title_fallback="Cost vs Retail Price",
        title_fallback_ar="التكلفة مقابل سعر البيع",
        required_columns=["product.product_name", "product.cost", "product.retail_price"],
        sql="""
            SELECT
                {product.product_name} AS product_name,
                {product.cost} AS cost,
                {product.retail_price} AS retail_price,
                ({product.retail_price} - {product.cost}) AS margin
            FROM {product.__table__}
            ORDER BY margin DESC
        """,
        table_columns=[
            TableColumn(label="Product", ref="product.product_name"),
            TableColumn(label="Cost", ref="product.cost"),
            TableColumn(label="Retail Price", ref="product.retail_price"),
            TableColumn(label="Margin", computed=True),
        ],
    ),

    WidgetDef(
        id="total_employees",
        dashboard="operations",
        chart_type="kpi",
        title_fallback="Total Employees",
        title_fallback_ar="إجمالي الموظفين",
        required_columns=["employee.employee_id"],
        sql="SELECT COUNT({employee.employee_id}) AS value FROM {employee.__table__}",
        value_ref="employee.employee_id",
    ),
    WidgetDef(
        id="active_employees",
        dashboard="operations",
        chart_type="kpi",
        title_fallback="Active Employees",
        title_fallback_ar="الموظفون النشطون",
        required_columns=["employee.termination_date"],
        sql="""
            SELECT COUNT(*) AS value
            FROM {employee.__table__}
            WHERE {employee.termination_date} IS NULL
        """,
        value_ref=None,
    ),
    WidgetDef(
        id="orders_handled_per_employee",
        dashboard="operations",
        chart_type="bar",
        title_fallback="Orders Handled per Employee",
        title_fallback_ar="الطلبات المنفذة لكل موظف",
        required_columns=["order.order_id", "order.employee_id", "employee.employee_id", "employee.full_name"],
        x_ref="employee.full_name",
        y_ref=None,
        sql="""
            SELECT {employee.full_name} AS x, COUNT({order.order_id}) AS y
            FROM {order.__table__}
            JOIN {employee.__table__} ON {order.employee_id} = {employee.employee_id}
            GROUP BY {employee.employee_id}, {employee.full_name}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="stock_movements_recorded_per_employee",
        dashboard="operations",
        chart_type="bar",
        title_fallback="Stock Movements per Employee",
        title_fallback_ar="حركات المخزون المسجلة لكل موظف",
        required_columns=["stock_movement.user_id", "employee.employee_id", "employee.full_name"],
        x_ref="employee.full_name",
        y_ref=None,
        sql="""
            SELECT {employee.full_name} AS x, COUNT(*) AS y
            FROM {stock_movement.__table__}
            JOIN {employee.__table__} ON {stock_movement.user_id} = {employee.employee_id}
            GROUP BY {employee.employee_id}, {employee.full_name}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="purchase_orders_created_per_employee",
        dashboard="operations",
        chart_type="bar",
        title_fallback="Purchase Orders Created per Employee",
        title_fallback_ar="أوامر الشراء المنشأة لكل موظف",
        required_columns=["purchase_order.user_id", "employee.employee_id", "employee.full_name"],
        x_ref="employee.full_name",
        y_ref=None,
        sql="""
            SELECT {employee.full_name} AS x, COUNT(*) AS y
            FROM {purchase_order.__table__}
            JOIN {employee.__table__} ON {purchase_order.user_id} = {employee.employee_id}
            GROUP BY {employee.employee_id}, {employee.full_name}
            ORDER BY y DESC
        """,
    ),
    WidgetDef(
        id="average_tenure",
        dashboard="operations",
        chart_type="kpi",
        title_fallback="Average Tenure (Days)",
        title_fallback_ar="متوسط مدة الخدمة (بالأيام)",
        required_columns=["employee.hire_date", "employee.termination_date"],
        sql="""
            SELECT AVG(DATEDIFF(COALESCE({employee.termination_date}, CURDATE()), {employee.hire_date})) AS value
            FROM {employee.__table__}
        """,
        value_ref=None,
    ),
]

DASHBOARD_IDS = ["sales", "inventory", "suppliers", "purchasing", "products", "operations"]

def widgets_for_dashboards(dashboard_ids: List[str]) -> List[WidgetDef]:
    wanted = set(dashboard_ids)
    return [w for w in WIDGETS if w.dashboard in wanted]