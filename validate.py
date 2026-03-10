#!/usr/bin/env python3
"""
FMCG Data Validation Script
Comprehensive data quality checks for billion-scale dataset
"""

import json
import argparse
import logging
from typing import Dict
from datetime import date

import psycopg2

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataValidator:
    """Comprehensive validation for FMCG synthetic dataset"""
    
    def __init__(self, db_config: Dict, brand_mapping_file: str):
        self.db_config = db_config
        with open(brand_mapping_file, 'r') as f:
            data = json.load(f)
            self.brand_mappings = data['brand_category_mappings']
        
        self.conn = None
        self.cursor = None
        self.errors = []
    
    def connect(self):
        """Connect to database"""
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        logger.info("✓ Database connected")
    
    def validate_row_counts(self):
        """Validate table row counts"""
        logger.info("\n=== Row Count Validation ===")
        
        tables = ['products', 'stores', 'orders', 'transactions']
        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            logger.info(f"  {table}: {count:,} rows")
            
            if table == 'products' and count < 100000:
                self.errors.append(f"Products count {count:,} below expected 100K+")
            elif table == 'orders' and count < 900000000:
                self.errors.append(f"Orders count {count:,} below target ~1 billion")
    
    def validate_referential_integrity(self):
        """Check foreign key relationships"""
        logger.info("\n=== Referential Integrity Validation ===")
        
        # Orders -> Stores
        self.cursor.execute("""
            SELECT COUNT(*) FROM orders o 
            LEFT JOIN stores s ON o.store_id = s.store_id 
            WHERE s.store_id IS NULL
        """)
        orphaned = self.cursor.fetchone()[0]
        if orphaned > 0:
            self.errors.append(f"Found {orphaned:,} orders with invalid store_id")
        else:
            logger.info("  ✓ All orders have valid store_id")
        
        # Transactions -> Orders
        self.cursor.execute("""
            SELECT COUNT(*) FROM transactions t
            LEFT JOIN orders o ON t.order_id = o.order_id
            WHERE o.order_id IS NULL
        """)
        orphaned = self.cursor.fetchone()[0]
        if orphaned > 0:
            self.errors.append(f"Found {orphaned:,} transactions with invalid order_id")
        else:
            logger.info("  ✓ All transactions have valid order_id")
    
    def validate_date_range(self):
        """Validate date coverage"""
        logger.info("\n=== Date Range Validation ===")
        
        self.cursor.execute("SELECT MIN(order_date), MAX(order_date) FROM orders")
        min_date, max_date = self.cursor.fetchone()
        
        expected_start = date(2023, 6, 1)
        expected_end = date(2025, 12, 31)
        
        logger.info(f"  Orders date range: {min_date} to {max_date}")
        
        if min_date != expected_start:
            self.errors.append(f"Min date {min_date} != expected {expected_start}")
        if max_date != expected_end:
            self.errors.append(f"Max date {max_date} != expected {expected_end}")
        
        if not self.errors:
            logger.info("  ✓ Date range correct")
    
    def validate_brand_category_mappings(self):
        """Validate brand-category ownership"""
        logger.info("\n=== Brand-Category Mapping Validation ===")
        
        violations = []
        for brand, allowed_categories in self.brand_mappings.items():
            self.cursor.execute("""
                SELECT DISTINCT category 
                FROM products 
                WHERE brand = %s
            """, (brand,))
            
            actual_categories = [row[0] for row in self.cursor.fetchall()]
            
            for cat in actual_categories:
                if cat not in allowed_categories:
                    violations.append(f"Brand '{brand}' in unauthorized category '{cat}'")
        
        if violations:
            self.errors.extend(violations[:10])
            logger.error(f"  ✗ Found {len(violations)} violations")
        else:
            logger.info("  ✓ All brand-category mappings valid")
    
    def validate_mobile_vs_supermarket(self):
        """Critical validation: Mobile stores should have lower avg order value"""
        logger.info("\n=== Mobile vs Supermarket Validation ===")
        
        self.cursor.execute("""
            SELECT s.store_type, AVG(o.total_value) as avg_value
            FROM orders o
            JOIN stores s ON o.store_id = s.store_id
            WHERE s.store_type IN ('Mobile', 'Supermarket')
            GROUP BY s.store_type
        """)
        
        results = {row[0]: row[1] for row in self.cursor.fetchall()}
        
        if 'Mobile' in results and 'Supermarket' in results:
            mobile_avg = results['Mobile']
            supermarket_avg = results['Supermarket']
            ratio = mobile_avg / supermarket_avg
            
            logger.info(f"  Mobile avg: ₹{mobile_avg:.2f}")
            logger.info(f"  Supermarket avg: ₹{supermarket_avg:.2f}")
            logger.info(f"  Ratio: {ratio:.2f}")
            
            if ratio > 0.50:
                self.errors.append(
                    f"Mobile/Supermarket ratio {ratio:.2f} exceeds 0.50 threshold"
                )
            else:
                logger.info("  ✓ Mobile stores have appropriately lower order values")
    
    def validate_psku_hierarchy(self):
        """Validate PSKU-SKU structure"""
        logger.info("\n=== PSKU-SKU Hierarchy Validation ===")
        
        # Count PSKUs
        self.cursor.execute("SELECT COUNT(DISTINCT psku_code) FROM products")
        psku_count = self.cursor.fetchone()[0]
        logger.info(f"  Total PSKUs: {psku_count:,}")
        
        if psku_count < 5000:
            self.errors.append(f"PSKU count {psku_count:,} below target 5,000")
        
        # Check SKUs per PSKU
        self.cursor.execute("""
            SELECT psku_code, COUNT(*) as sku_count
            FROM products
            GROUP BY psku_code
            HAVING COUNT(*) < 2
        """)
        
        invalid_pskus = self.cursor.fetchall()
        if invalid_pskus:
            self.errors.append(f"Found {len(invalid_pskus)} PSKUs with < 2 SKUs")
        else:
            logger.info("  ✓ All PSKUs have minimum 2 SKUs")
        
        # Average SKUs per PSKU
        self.cursor.execute("""
            SELECT AVG(sku_count) 
            FROM (
                SELECT COUNT(*) as sku_count 
                FROM products 
                GROUP BY psku_code
            ) sub
        """)
        avg_skus = self.cursor.fetchone()[0]
        logger.info(f"  Avg SKUs per PSKU: {avg_skus:.1f}")
    
    def validate_data_quality(self):
        """Check for NULL values and invalid data"""
        logger.info("\n=== Data Quality Validation ===")
        
        # Check for NULLs in products
        self.cursor.execute("""
            SELECT COUNT(*) FROM products
            WHERE product_id IS NULL OR category IS NULL 
               OR brand IS NULL OR psku IS NULL OR sku IS NULL
               OR unit_price IS NULL
        """)
        null_count = self.cursor.fetchone()[0]
        if null_count > 0:
            self.errors.append(f"Found {null_count:,} products with NULL required fields")
        
        # Check for invalid quantities
        self.cursor.execute("SELECT COUNT(*) FROM orders WHERE quantity < 1")
        invalid = self.cursor.fetchone()[0]
        if invalid > 0:
            self.errors.append(f"Found {invalid:,} orders with quantity < 1")
        
        # Check for invalid prices
        self.cursor.execute("SELECT COUNT(*) FROM orders WHERE total_value <= 0")
        invalid = self.cursor.fetchone()[0]
        if invalid > 0:
            self.errors.append(f"Found {invalid:,} orders with total_value <= 0")
        
        if not self.errors:
            logger.info("  ✓ No data quality issues found")
    
    def generate_summary_report(self):
        """Generate validation summary"""
        logger.info("\n=== Validation Summary ===")
        
        if not self.errors:
            logger.info("✓✓✓ ALL VALIDATIONS PASSED ✓✓✓")
            return True
        else:
            logger.error(f"✗✗✗ FOUND {len(self.errors)} ERRORS ✗✗✗")
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  {i}. {error}")
            return False
    
    def run_all_validations(self):
        """Execute all validation checks"""
        logger.info("Starting comprehensive validation...")
        
        self.validate_row_counts()
        self.validate_referential_integrity()
        self.validate_date_range()
        self.validate_brand_category_mappings()
        self.validate_mobile_vs_supermarket()
        self.validate_psku_hierarchy()
        self.validate_data_quality()
        
        return self.generate_summary_report()
    
    def close(self):
        """Close connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Validate FMCG synthetic dataset')
    parser.add_argument('--db-config', default='db_config.json')
    parser.add_argument('--brand-mapping', default='brand_category_mapping.json')
    
    args = parser.parse_args()
    
    with open(args.db_config, 'r') as f:
        db_config = json.load(f)
    
    validator = DataValidator(db_config, args.brand_mapping)
    
    try:
        validator.connect()
        success = validator.run_all_validations()
        exit_code = 0 if success else 1
    finally:
        validator.close()
    
    exit(exit_code)


if __name__ == '__main__':
    main()