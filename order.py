#!/usr/bin/env python3
"""
FMCG Order Generator - Generates ~1 billion order records
Uses cycle-based ordering with Poisson-distributed quantities
"""

import json
import argparse
import logging
import signal
import sys
from datetime import datetime, timedelta, date
from typing import Dict, List, Tuple
import random

import psycopg2
from psycopg2.extras import execute_values
import numpy as np
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('order_generator.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class OrderGenerator:
    """Generate billion-scale order records with cycle-based logic"""
    
    def __init__(self, db_config: Dict, orders_per_cycle: int = 200, limit: int = None):
        self.db_config = db_config
        self.orders_per_cycle = orders_per_cycle
        self.limit = limit
        self.start_date = date(2023, 6, 1)
        self.end_date = date(2025, 12, 31)
        self.total_days = (self.end_date - self.start_date).days + 1
        
        self.conn = None
        self.cursor = None
        self.product_ids = []
        self.product_prices = {}
        self.stores = []
        self.store_start_dates = {}
        
        self.total_orders_inserted = 0
        self.checkpoint_file = 'order_checkpoint.json'
        self.last_processed_date = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle graceful shutdown"""
        logger.warning("Received shutdown signal, saving checkpoint...")
        self._save_checkpoint()
        if self.conn:
            self.conn.commit()
            self.conn.close()
        sys.exit(0)
    
    def _save_checkpoint(self):
        """Save current progress"""
        checkpoint = {
            'last_processed_date': self.last_processed_date.isoformat() if self.last_processed_date else None,
            'total_orders_inserted': self.total_orders_inserted,
            'store_start_dates': {k: v.isoformat() for k, v in self.store_start_dates.items()}
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
        logger.info(f"Checkpoint saved: {self.total_orders_inserted:,} orders inserted")
    
    def _load_checkpoint(self) -> bool:
        """Load checkpoint if exists"""
        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)
            self.last_processed_date = date.fromisoformat(checkpoint['last_processed_date']) if checkpoint['last_processed_date'] else None
            self.total_orders_inserted = checkpoint['total_orders_inserted']
            self.store_start_dates = {int(k): date.fromisoformat(v) for k, v in checkpoint['store_start_dates'].items()}
            logger.info(f"Resuming from checkpoint: {self.total_orders_inserted:,} orders already inserted")
            return True
        except FileNotFoundError:
            return False
    
    def connect_database(self):
        """Establish database connection"""
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        logger.info("✓ Database connected")
    
    def load_products(self):
        """Load product master data"""
        logger.info("Loading product master data...")
        self.cursor.execute("SELECT product_id, unit_price FROM products")
        rows = self.cursor.fetchall()
        
        self.product_ids = [row[0] for row in rows]
        self.product_prices = {row[0]: row[1] for row in rows}
        
        logger.info(f"✓ Loaded {len(self.product_ids):,} products")
    
    def load_stores(self):
        """Load store master data"""
        logger.info("Loading store master data...")
        self.cursor.execute("""
            SELECT store_id, cycle_days, avg_sales_multiplier 
            FROM stores
        """)
        
        self.stores = []
        for row in self.cursor.fetchall():
            store = {
                'store_id': row[0],
                'cycle_days': row[1],
                'avg_sales_multiplier': float(row[2])
            }
            self.stores.append(store)
            
            # Initialize random start date for cycle staggering
            if row[0] not in self.store_start_dates:
                offset_days = random.randint(0, row[1] - 1)
                self.store_start_dates[row[0]] = self.start_date + timedelta(days=offset_days)
        
        logger.info(f"✓ Loaded {len(self.stores):,} stores")
    
    def disable_indexes(self):
        """Drop indexes before bulk insert"""
        logger.info("Dropping indexes for faster insertion...")
        self.cursor.execute("DROP INDEX IF EXISTS idx_orders_date")
        self.cursor.execute("DROP INDEX IF EXISTS idx_orders_store")
        self.cursor.execute("DROP INDEX IF EXISTS idx_orders_product")
        self.cursor.execute("DROP INDEX IF EXISTS idx_orders_store_date")
        self.conn.commit()
        logger.info("✓ Indexes dropped")
    
    def enable_indexes(self):
        """Recreate indexes after bulk insert"""
        logger.info("Recreating indexes...")
        self.cursor.execute("CREATE INDEX idx_orders_date ON orders(order_date)")
        self.cursor.execute("CREATE INDEX idx_orders_store ON orders(store_id)")
        self.cursor.execute("CREATE INDEX idx_orders_product ON orders(product_id)")
        self.cursor.execute("CREATE INDEX idx_orders_store_date ON orders(store_id, order_date)")
        self.conn.commit()
        logger.info("✓ Indexes recreated")
    
    def generate_orders(self, resume: bool = False):
        """Main order generation loop"""
        if resume:
            if self._load_checkpoint():
                start_date = self.last_processed_date + timedelta(days=1)
            else:
                logger.info("No checkpoint found, starting from beginning")
                start_date = self.start_date
        else:
            start_date = self.start_date
        
        logger.info(f"Generating orders from {start_date} to {self.end_date}")
        logger.info(f"Orders per cycle event: {self.orders_per_cycle}")
        
        current_date = start_date
        batch_orders = []
        commit_interval = 1  # Commit every 1 day for low disk space
        last_commit_date = current_date
        
        with tqdm(total=self.total_days, initial=(current_date - self.start_date).days) as pbar:
            while current_date <= self.end_date:
                date_orders = []
                
                # Check each store for cycle event
                for store in self.stores:
                    store_id = store['store_id']
                    cycle_days = store['cycle_days']
                    multiplier = store['avg_sales_multiplier']
                    
                    store_start = self.store_start_dates[store_id]
                    days_since_start = (current_date - store_start).days
                    
                    # Check if this is a cycle event day
                    if days_since_start >= 0 and days_since_start % cycle_days == 0:
                        # Generate orders for this cycle event
                        lambda_base = 8
                        effective_lambda = lambda_base * multiplier
                        
                        for _ in range(self.orders_per_cycle):
                            # Sample product
                            product_id = random.choice(self.product_ids)
                            unit_price = float(self.product_prices[product_id])
                            
                            # Sample quantity using Poisson distribution
                            quantity = max(1, int(np.random.poisson(effective_lambda)))
                            
                            # Calculate total value with price variance
                            discount_multiplier = random.uniform(0.85, 1.15)
                            total_value = round(quantity * unit_price * discount_multiplier * multiplier, 2)
                            
                            date_orders.append((
                                store_id,
                                product_id,
                                current_date,
                                quantity,
                                total_value
                            ))
                
                # Bulk insert date orders
                if date_orders:
                    insert_query = """
                        INSERT INTO orders (store_id, product_id, order_date, quantity, total_value)
                        VALUES %s
                    """
                    execute_values(self.cursor, insert_query, date_orders, page_size=10000)
                    self.total_orders_inserted += len(date_orders)
                    
                    if self.limit and self.total_orders_inserted >= self.limit:
                        logger.info(f"Reached limit of {self.limit} orders")
                        current_date = self.end_date + timedelta(days=1)
                        break
                
                # Commit periodically
                if (current_date - last_commit_date).days >= commit_interval:
                    self.conn.commit()
                    self._save_checkpoint()
                    last_commit_date = current_date
                
                self.last_processed_date = current_date
                current_date += timedelta(days=1)
                pbar.update(1)
                pbar.set_postfix({
                    'orders': f'{self.total_orders_inserted:,}',
                    'rate': f'{self.total_orders_inserted / ((current_date - start_date).days + 1):.0f}/day'
                })
        
        # Final commit
        self.conn.commit()
        self._save_checkpoint()
        logger.info(f"✓ Order generation complete: {self.total_orders_inserted:,} orders inserted")
    
    def validate_orders(self):
        """Validate generated orders"""
        logger.info("Validating orders...")
        
        # Total count
        self.cursor.execute("SELECT COUNT(*) FROM orders")
        total = self.cursor.fetchone()[0]
        logger.info(f"  Total orders: {total:,}")
        
        # Date range
        self.cursor.execute("SELECT MIN(order_date), MAX(order_date) FROM orders")
        min_date, max_date = self.cursor.fetchone()
        logger.info(f"  Date range: {min_date} to {max_date}")
        
        # Store type averages
        self.cursor.execute("""
            SELECT s.store_type, AVG(o.total_value) as avg_value
            FROM orders o
            JOIN stores s ON o.store_id = s.store_id
            GROUP BY s.store_type
            ORDER BY avg_value DESC
        """)
        logger.info("  Average order value by store type:")
        for row in self.cursor.fetchall():
            logger.info(f"    {row[0]}: ₹{row[1]:.2f}")
        
        logger.info("✓ Validation complete")
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Database connection closed")


def main():
    parser = argparse.ArgumentParser(description='Generate FMCG orders at billion scale')
    parser.add_argument('--db-config', default='db_config.json', help='Database config')
    parser.add_argument('--orders-per-cycle', type=int, default=200, 
                       help='Orders per cycle event (default: 200 for ~1B orders)')
    parser.add_argument('--disable-indexes', action='store_true',
                       help='Drop indexes before insertion')
    parser.add_argument('--enable-indexes', action='store_true',
                       help='Recreate indexes after insertion')
    parser.add_argument('--resume', action='store_true',
                       help='Resume from checkpoint')
    parser.add_argument('--limit', type=int, default=None,
                       help='Limit total number of orders generated')
    parser.add_argument('--validate', action='store_true',
                       help='Validate orders after generation')
    
    args = parser.parse_args()
    
    # Load database config
    with open(args.db_config, 'r') as f:
        db_config = json.load(f)
    
    generator = OrderGenerator(db_config, args.orders_per_cycle, args.limit)
    
    try:
        generator.connect_database()
        generator.load_products()
        generator.load_stores()
        
        if args.disable_indexes:
            generator.disable_indexes()
        
        generator.generate_orders(resume=args.resume)
        
        if args.enable_indexes:
            generator.enable_indexes()
        
        if args.validate:
            generator.validate_orders()
        
    finally:
        generator.close()
    
    logger.info("✓ All operations complete!")


if __name__ == '__main__':
    main()