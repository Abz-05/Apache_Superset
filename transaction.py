#!/usr/bin/env python3
"""
Transaction Generator - Creates 1:1 correspondence with orders table
"""

import json
import argparse
import logging
from typing import Dict

import psycopg2
from psycopg2.extras import execute_values
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[logging.FileHandler('transaction_generator.log'), 
                            logging.StreamHandler()])
logger = logging.getLogger(__name__)


class TransactionGenerator:
    """Generate transactions with 1:1 order correspondence"""
    
    def __init__(self, db_config: Dict, batch_size: int = 50000):
        self.db_config = db_config
        self.batch_size = batch_size
        self.conn = None
        self.cursor = None
    
    def connect_database(self):
        """Connect to PostgreSQL"""
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        logger.info("✓ Database connected")
    
    def disable_indexes(self):
        """Drop indexes for faster bulk insert"""
        logger.info("Dropping indexes for transactions...")
        self.cursor.execute("DROP INDEX IF EXISTS idx_transactions_order")
        self.cursor.execute("DROP INDEX IF EXISTS idx_transactions_date")
        self.cursor.execute("DROP INDEX IF EXISTS idx_transactions_store_date")
        self.conn.commit()
        logger.info("✓ Indexes dropped")
    
    def enable_indexes(self):
        """Recreate indexes after bulk insert"""
        logger.info("Recreating indexes for transactions...")
        self.cursor.execute("CREATE INDEX idx_transactions_order ON transactions(order_id)")
        self.cursor.execute("CREATE INDEX idx_transactions_date ON transactions(date)")
        self.cursor.execute("CREATE INDEX idx_transactions_store_date ON transactions(store_id, date)")
        self.conn.commit()
        logger.info("✓ Indexes recreated")
    
    def generate_transactions(self):
        """Generate transactions from orders table"""
        logger.info("Generating transactions...")
        
        # Get total order count
        self.cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = self.cursor.fetchone()[0]
        logger.info(f"Total orders to process: {total_orders:,}")
        
        # Check existing transactions to resume
        self.cursor.execute("SELECT COUNT(*) FROM transactions")
        existing_count = self.cursor.fetchone()[0]
        logger.info(f"Existing transactions: {existing_count:,}")
        
        if existing_count >= total_orders * 2:
            logger.info("All transactions already generated!")
            return
        
        # Since we generate 2 transactions per order, we need to know where we left off
        last_order_id = 0
        if existing_count > 0:
            self.cursor.execute("SELECT MAX(order_id) FROM transactions")
            last_order_id = self.cursor.fetchone()[0] or 0
            
        transaction_id = existing_count + 1
        logger.info(f"Resuming from transaction {transaction_id:,}, last order_id: {last_order_id}")
        
        with tqdm(total=total_orders, initial=existing_count // 2) as pbar:
            while True:
                # Fetch batch of orders using order_id > last_order_id
                self.cursor.execute("""
                    SELECT order_id, store_id, product_id, order_date, quantity, total_value
                    FROM orders
                    WHERE order_id > %s
                    ORDER BY order_id
                    LIMIT %s
                """, (last_order_id, self.batch_size))
                
                orders = self.cursor.fetchall()
                if not orders:
                    break
                
                # Prepare transaction records for COPY (CSV format)
                import io
                f = io.StringIO()
                for i, order in enumerate(orders):
                    unit_price = round(float(order[5]) / order[4], 2)
                    # First transaction copy
                    f.write(f"{transaction_id}\t{order[0]}\t{order[1]}\t{order[2]}\t{order[3]}\t{order[4]}\t{order[5]}\t{unit_price}\n")
                    transaction_id += 1
                    
                    # Second transaction copy
                    f.write(f"{transaction_id}\t{order[0]}\t{order[1]}\t{order[2]}\t{order[3]}\t{order[4]}\t{order[5]}\t{unit_price}\n")
                    transaction_id += 1
                
                # Bulk insert using COPY
                f.seek(0)
                self.cursor.copy_from(f, 'transactions', columns=(
                    'transaction_id', 'order_id', 'store_id', 'product_id', 
                    'date', 'quantity', 'value', 'unit_price'
                ))
                self.conn.commit()
                
                last_order_id = orders[-1][0]
                pbar.update(len(orders))
        
        logger.info(f"✓ Generated {transaction_id - 1:,} transactions")
    
    def validate_transactions(self):
        """Validate transaction generation"""
        logger.info("Validating transactions...")
        
        # Count match
        self.cursor.execute("SELECT COUNT(*) FROM transactions")
        trans_count = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = self.cursor.fetchone()[0]
        
        logger.info(f"  Transactions: {trans_count:,}")
        logger.info(f"  Orders: {order_count:,}")
        
        if trans_count == order_count * 2:
            logger.info("  ✓ Count match confirmed (2x orders)")
        else:
            logger.error(f"  ✗ Count mismatch: {trans_count} transactions vs {order_count} orders (expected 2x)")
        
        # Check for orphaned transactions
        self.cursor.execute("""
            SELECT COUNT(*) 
            FROM transactions t 
            LEFT JOIN orders o ON t.order_id = o.order_id 
            WHERE o.order_id IS NULL
        """)
        orphaned = self.cursor.fetchone()[0]
        
        if orphaned == 0:
            logger.info("  ✓ No orphaned transactions")
        else:
            logger.error(f"  ✗ Found {orphaned:,} orphaned transactions")
        
        logger.info("✓ Validation complete")
    
    def close(self):
        """Close connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    parser = argparse.ArgumentParser(description='Generate FMCG transactions')
    parser.add_argument('--db-config', default='db_config.json')
    parser.add_argument('--batch-size', type=int, default=50000)
    parser.add_argument('--disable-indexes', action='store_true')
    parser.add_argument('--enable-indexes', action='store_true')
    parser.add_argument('--validate', action='store_true')
    
    args = parser.parse_args()
    
    with open(args.db_config, 'r') as f:
        db_config = json.load(f)
    
    generator = TransactionGenerator(db_config, args.batch_size)
    
    try:
        generator.connect_database()
        
        if args.disable_indexes:
            generator.disable_indexes()
            
        generator.generate_transactions()
        
        if args.enable_indexes:
            generator.enable_indexes()
            
        if args.validate:
            generator.validate_transactions()
    finally:
        generator.close()
    
    logger.info("✓ Transaction generation complete!")


if __name__ == '__main__':
    main()