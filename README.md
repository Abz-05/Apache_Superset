# 🛒 FMCG Sales Data Pipeline & Apache Superset Dashboards

> A billion-scale synthetic FMCG (Fast-Moving Consumer Goods) data generation pipeline backed by **PostgreSQL**, visualized through **Apache Superset** dashboards for sales analytics, store performance, product insights, and transaction trends.

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Architecture](#-architecture)
- [Data Model](#-data-model)
- [Project Structure](#-project-structure)
- [Prerequisites](#-prerequisites)
- [Setup & Installation](#-setup--installation)
- [Running the Data Pipeline](#-running-the-data-pipeline)
- [Running Apache Superset](#-running-apache-superset)
- [Superset Dashboard Guide](#-superset-dashboard-guide)
- [Validation](#-validation)
- [Configuration](#-configuration)

---

## 🌐 Project Overview

This project generates a realistic **billion-scale FMCG retail dataset** spanning:

| Entity       | Scale                     |
|--------------|---------------------------|
| Products     | ~100,000–125,000 SKUs     |
| PSKUs        | ~5,000 parent SKUs        |
| Stores       | 2,000 across India        |
| Orders       | ~1 Billion records        |
| Transactions | ~2 Billion records (2× orders) |
| Date Range   | June 2023 – December 2025 |

The dataset covers **6 FMCG categories**: Food & Beverages, Personal Care, Home Care, Snacks, Baby & Childcare, Health — spread across **10 major Indian cities**.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Data Generation Layer                     │
│   product.py → store.py → order.py → transaction.py        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL Database (FMCG_DB)                  │
│   products | stores | orders | transactions                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Apache Superset (Port 8088)                    │
│   Sales Dashboards | Store Analytics | Product Insights     │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Model

```
products (100K+ SKUs)
    │
    ├── psku_code (5K PSKUs)
    └── product_id ──────────────────┐
                                     │
stores (2,000)                       │
    │                                │
    └── store_id ──── orders ────────┘
                        │
                        └── transactions (2× orders)
```

### Table Details

| Table        | Primary Key     | Key Columns                                          |
|--------------|-----------------|------------------------------------------------------|
| `products`   | `product_id`    | `category`, `brand`, `psku_code`, `sku_code`, `unit_price` |
| `stores`     | `store_id`      | `store_type`, `city`, `region`, `state`, `cycle_days` |
| `orders`     | `order_id`      | `store_id`, `product_id`, `order_date`, `quantity`, `total_value` |
| `transactions` | `transaction_id` | `order_id`, `store_id`, `product_id`, `date`, `value` |

---

## 📁 Project Structure

```
sales/
│
├── sql.sql                      # DDL — Creates all tables & indexes
├── setup_db.py                  # Database setup & CSV loader script
│
├── product.py                   # FMCG Product catalog generator (~100K SKUs)
├── product_new.py               # Enhanced product generator (latest version)
├── store.py                     # Store network generator (2,000 stores)
├── order.py                     # Order generator (~1 Billion records)
├── transaction.py               # Transaction generator (2× orders)
│
├── validate.py                  # Comprehensive data validation suite
├── analysisql.sql               # Analysis SQL queries for Superset
│
├── brand_category_mapping.json  # Brand → Category ownership mapping
├── db_config.example.json       # Example DB config (copy & rename)
├── requirements.txt             # Python dependencies
│
├── product.csv                  # Generated product data (gitignored)
└── store.csv                    # Generated store data (gitignored)
```

---

## ✅ Prerequisites

| Requirement        | Version / Notes                          |
|--------------------|------------------------------------------|
| Python             | 3.9+                                    |
| PostgreSQL         | 14+ (running locally on port 5432)      |
| Apache Superset    | Installed in a virtual environment       |
| pip                | Latest                                  |

---

## ⚙️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/Apache_Superset.git
cd Apache_Superset
```

### 2. Configure Database Credentials

Copy the example config and fill in your credentials:

```bash
copy db_config.example.json db_config.json
```

Edit `db_config.json`:

```json
{
  "host": "localhost",
  "port": 5432,
  "database": "FMCG_DB",
  "user": "postgres",
  "password": "YOUR_POSTGRES_PASSWORD"
}
```

### 3. Create Python Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the Data Pipeline

Run steps in order. Each step builds on the previous.

### Step 1 — Create Database & Load Schema

```bash
python setup_db.py --create-db --load-ddl
```

### Step 2 — Generate Products (~100K SKUs)

```bash
python product_new.py
```

This generates `product.csv`. Then load it into the database:

```bash
python setup_db.py --load-products product.csv
```

### Step 3 — Generate Stores (2,000 stores)

```bash
python store.py --stores 2000 --to-database
```

### Step 4 — Generate Orders (~1 Billion records)

> ⚠️ This is a long-running process. Use `--resume` to continue if interrupted.

```bash
# First run
python order.py --orders-per-cycle 200 --disable-indexes

# Resume if interrupted
python order.py --orders-per-cycle 200 --resume

# Recreate indexes after generation is complete
python order.py --enable-indexes
```

### Step 5 — Generate Transactions (~2 Billion records)

```bash
python transaction.py --disable-indexes --batch-size 50000
# After completion:
python transaction.py --enable-indexes
```

### Step 6 — Validate Data

```bash
python validate.py
```

---

## 🖥️ Running Apache Superset

Apache Superset is installed in a separate virtual environment. Use the following commands to start it.

### Activate Superset Environment & Start Server

```powershell
# Step 1: Activate the Superset virtual environment
C:\Users\<YourUsername>\superset_env\Scripts\activate

# Step 2: Set Flask app
$env:FLASK_APP = "superset"

# Step 3: Start the Superset server
superset run -p 8088 --with-threads --reload --debugger
```

> After running, open your browser and navigate to: **http://localhost:8088**
>
> **Default Login Credentials:**
> - Username: `admin`
> - Password: `admin` *(or as set during your installation)*

### One-liner startup (PowerShell)

```powershell
C:\Users\<YourUsername>\superset_env\Scripts\activate; $env:FLASK_APP="superset"; superset run -p 8088 --with-threads --reload --debugger
```

---

## 📈 Superset Dashboard Guide

### Connecting PostgreSQL to Superset

1. Navigate to **Settings → Database Connections → + Database**
2. Choose **PostgreSQL**
3. Enter your SQLAlchemy URI:
   ```
   postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/FMCG_DB
   ```
4. Click **Test Connection** → **Connect**

### Key Dashboards Built

| Dashboard               | Description                                                   |
|-------------------------|---------------------------------------------------------------|
| 📦 **Sales Overview**   | Total revenue, order volume, and monthly trends               |
| 🏪 **Store Performance** | Sales by store type (Hypermarket/Supermarket/Mobile/etc.)    |
| 🗺️ **Regional Analysis** | City & state-level revenue breakdown                          |
| 🏷️ **Brand & Category**  | Top brands, category mix, PSKU/SKU hierarchy view             |
| 📅 **Time Series**       | Day-over-day, month-over-month order & revenue trends         |
| 🔁 **Transaction Audit** | Transaction-to-order ratio and integrity checks               |

### Useful SQL Queries (from `analysisql.sql`)

You can import these directly into Superset's **SQL Lab**:

```sql
-- Top 10 Brands by Revenue
SELECT brand, SUM(o.total_value) AS revenue
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY brand
ORDER BY revenue DESC
LIMIT 10;

-- Monthly Sales Trend
SELECT DATE_TRUNC('month', order_date) AS month,
       COUNT(*) AS order_count,
       SUM(total_value) AS total_revenue
FROM orders
GROUP BY 1
ORDER BY 1;

-- Store Type Performance
SELECT s.store_type, COUNT(*) AS orders, SUM(o.total_value) AS revenue
FROM orders o
JOIN stores s ON o.store_id = s.store_id
GROUP BY s.store_type
ORDER BY revenue DESC;

-- Category Revenue Share
SELECT p.category, SUM(o.total_value) AS revenue,
       ROUND(100.0 * SUM(o.total_value) / SUM(SUM(o.total_value)) OVER (), 2) AS pct
FROM orders o
JOIN products p ON o.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue DESC;
```

---

## 🔍 Validation

Run the comprehensive validation suite to verify data integrity:

```bash
python validate.py --db-config db_config.json --brand-mapping brand_category_mapping.json
```

Checks performed:

| Validation                   | Expected Result                               |
|------------------------------|-----------------------------------------------|
| Row Counts                   | Products ≥ 100K, Orders ~1B                  |
| Referential Integrity        | No orphaned orders or transactions            |
| Date Range                   | June 2023 – December 2025                    |
| Brand-Category Mapping       | Each brand stays within allowed categories    |
| Mobile vs Supermarket Ratio  | Mobile avg order value < 50% of Supermarket  |
| PSKU Hierarchy               | Every PSKU has at least 2 SKUs               |
| Data Quality                 | No NULLs in required fields, no invalid prices|

---

## 🔧 Configuration

### PostgreSQL Tuning (for bulk data loading)

Add these settings to `postgresql.conf` before generating large datasets:

```ini
shared_buffers = 8GB
work_mem = 256MB
maintenance_work_mem = 2GB
effective_cache_size = 24GB
checkpoint_completion_target = 0.9
max_wal_size = 4GB
synchronous_commit = off       # During load only — re-enable after!
max_connections = 100
random_page_cost = 1.1         # For SSD storage
```

### Superset Query Timeout

To handle large analytical queries, set the timeout to 1 hour in Superset's config:

```python
# superset_config.py
SQLLAB_TIMEOUT = 3600          # 1 hour
SUPERSET_WEBSERVER_TIMEOUT = 3600
```

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

---

## 📄 License

This project is open source. Data is entirely synthetic and generated using [Faker](https://faker.readthedocs.io/).

---

*Built with 🐍 Python · 🐘 PostgreSQL · 📊 Apache Superset*
