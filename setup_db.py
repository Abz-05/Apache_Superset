#!/usr/bin/env python3
"""
Database Setup Script
Creates database, loads DDL schema, and optionally loads data
"""

import json
import argparse
import logging
import subprocess
import sys

import psycopg2
from psycopg2 import sql

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_database(db_config: dict):
    """Create database if it doesn't exist"""
    db_name = db_config['database']
    
    # Connect to default postgres database
    conn_config = db_config.copy()
    conn_config['database'] = 'postgres'
    
    try:
        conn = psycopg2.connect(**conn_config)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            logger.info(f"Creating database '{db_name}'...")
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                sql.Identifier(db_name)
            ))
            logger.info(f"✓ Database '{db_name}' created")
        else:
            logger.info(f"Database '{db_name}' already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Error creating database: {e}")
        return False


def load_ddl(db_config: dict, ddl_file: str = 'sql.sql'):
    """Load DDL schema"""
    try:
        logger.info(f"Loading DDL from {ddl_file}...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        with open(ddl_file, 'r') as f:
            ddl_sql = f.read()
        
        cursor.execute(ddl_sql)
        conn.commit()
        
        cursor.close()
        conn.close()
        logger.info("✓ DDL schema loaded successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error loading DDL: {e}")
        return False


def load_csv_data(db_config: dict, product_csv: str = None, 
                 store_csv: str = None, transaction_csv: str = None):
    """Load CSV data using COPY command"""
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        if product_csv:
            logger.info(f"Loading products from {product_csv}...")
            with open(product_csv, 'r', encoding='utf-8') as f:
                cursor.copy_expert(
                    """COPY products (product_id, category, sub_category, brand, sub_brand, 
                       psku, psku_code, sku, sku_code, weight_value, weight_unit, 
                       count_value, unit_price) 
                       FROM STDIN WITH CSV HEADER""",
                    f
                )
            logger.info("✓ Products loaded")
        
        if store_csv:
            logger.info(f"Loading stores from {store_csv}...")
            with open(store_csv, 'r', encoding='utf-8') as f:
                cursor.copy_expert(
                    """COPY stores (store_id, store_type, cycle_days, avg_sales_multiplier,
                       city, region, state, pin_code, area_type, established_date)
                       FROM STDIN WITH CSV HEADER""",
                    f
                )
            logger.info("✓ Stores loaded")
        
        if transaction_csv:
            logger.info(f"Loading transactions from {transaction_csv}...")
            with open(transaction_csv, 'r', encoding='utf-8') as f:
                cursor.copy_expert(
                    "COPY transactions FROM STDIN WITH CSV HEADER",
                    f
                )
            logger.info("✓ Transactions loaded")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error loading CSV data: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Setup FMCG database')
    parser.add_argument('--db-config', default='db_config.json',
                       help='Database configuration file')
    parser.add_argument('--create-db', action='store_true',
                       help='Create database')
    parser.add_argument('--load-ddl', action='store_true',
                       help='Load DDL schema')
    parser.add_argument('--ddl-file', default='sql.sql',
                       help='DDL file to load')
    parser.add_argument('--load-products', help='Product CSV file to load')
    parser.add_argument('--load-stores', help='Store CSV file to load')
    parser.add_argument('--load-transactions', help='Transaction CSV file to load')
    
    args = parser.parse_args()
    
    # Load database config
    try:
        with open(args.db_config, 'r') as f:
            db_config = json.load(f)
        logger.info(f"Loaded database config from {args.db_config}")
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)
    
    # Create database
    if args.create_db:
        if not create_database(db_config):
            sys.exit(1)
    
    # Load DDL
    if args.load_ddl:
        if not load_ddl(db_config, args.ddl_file):
            sys.exit(1)
    
    # Load CSV data
    if args.load_products or args.load_stores or args.load_transactions:
        if not load_csv_data(db_config, args.load_products, 
                           args.load_stores, args.load_transactions):
            sys.exit(1)
    
    logger.info("✓ Database setup complete!")


if __name__ == '__main__':
    main()