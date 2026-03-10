#!/usr/bin/env python3
"""
FMCG Store Network Generator
Generates 1,500-5,000 stores across multiple retail formats
"""

import json
import random
import argparse
import logging
from datetime import datetime, timedelta
from typing import List, Dict

import psycopg2
from psycopg2.extras import execute_values
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('store_generator.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class StoreGenerator:
    """Generate realistic retail network with multiple store formats"""
    
    STORE_TYPES = {
        'Hypermarket': {'cycle_days': 7, 'multiplier': 2.0, 'pct': 0.10},
        'Supermarket': {'cycle_days': 6, 'multiplier': 1.5, 'pct': 0.15},
        'Large': {'cycle_days': 5, 'multiplier': 1.0, 'pct': 0.22},
        'Medium': {'cycle_days': 5, 'multiplier': 0.8, 'pct': 0.28},
        'Small': {'cycle_days': 5, 'multiplier': 0.6, 'pct': 0.18},
        'Mobile': {'cycle_days': 7, 'multiplier': 0.4, 'pct': 0.07}
    }
    
    CITIES = [
        ('Mumbai', 'West', 'Maharashtra'),
        ('Delhi', 'North', 'Delhi'),
        ('Bangalore', 'South', 'Karnataka'),
        ('Hyderabad', 'South', 'Telangana'),
        ('Chennai', 'South', 'Tamil Nadu'),
        ('Kolkata', 'East', 'West Bengal'),
        ('Pune', 'West', 'Maharashtra'),
        ('Ahmedabad', 'West', 'Gujarat'),
        ('Jaipur', 'North', 'Rajasthan'),
        ('Lucknow', 'North', 'Uttar Pradesh')
    ]
    
    def __init__(self, total_stores: int = 2000):
        self.total_stores = total_stores
        self.stores = []
        self.store_id_counter = 1
    
    def generate_stores(self) -> None:
        """Generate complete store network"""
        logger.info(f"Generating {self.total_stores} stores...")
        
        for store_type, config in self.STORE_TYPES.items():
            count = int(self.total_stores * config['pct'])
            logger.info(f"  Generating {count} {store_type} stores...")
            
            for _ in range(count):
                city, region, state = random.choice(self.CITIES)
                
                store = {
                    'store_id': self.store_id_counter,
                    'store_type': store_type,
                    'cycle_days': config['cycle_days'],
                    'avg_sales_multiplier': config['multiplier'] * random.gauss(1.0, 0.05),
                    'city': city,
                    'region': region,
                    'state': state,
                    'pin_code': random.randint(100000, 999999),
                    'area_type': 'Urban' if random.random() < 0.85 else 'Semi-Urban',
                    'established_date': (datetime(2010, 1, 1) + 
                                       timedelta(days=random.randint(0, 4700))).strftime('%Y-%m-%d')
                }
                self.stores.append(store)
                self.store_id_counter += 1
        
        logger.info(f"✓ Generated {len(self.stores)} stores")
    
    def save_to_csv(self, filename: str = 'store.csv') -> None:
        """Save stores to CSV"""
        logger.info(f"Saving to {filename}...")
        df = pd.DataFrame(self.stores)
        df.to_csv(filename, index=False)
        logger.info(f"✓ Saved {len(self.stores)} stores")
    
    def save_to_database(self, db_config: Dict) -> None:
        """Save to PostgreSQL"""
        logger.info("Saving stores to database...")
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO stores (store_id, store_type, cycle_days, avg_sales_multiplier,
                              city, region, state, pin_code, area_type, established_date)
            VALUES %s
        """
        
        values = [
            (s['store_id'], s['store_type'], s['cycle_days'], s['avg_sales_multiplier'],
             s['city'], s['region'], s['state'], s['pin_code'], s['area_type'], 
             s['established_date'])
            for s in self.stores
        ]
        
        execute_values(cursor, insert_query, values)
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("✓ Stores saved to database")


def main():
    parser = argparse.ArgumentParser(description='Generate FMCG store network')
    parser.add_argument('--stores', type=int, default=2000, help='Total number of stores')
    parser.add_argument('--output', default='store.csv', help='Output CSV file')
    parser.add_argument('--db-config', default='db_config.json')
    parser.add_argument('--to-database', action='store_true')
    
    args = parser.parse_args()
    
    generator = StoreGenerator(args.stores)
    generator.generate_stores()
    generator.save_to_csv(args.output)
    
    if args.to_database:
        with open(args.db_config, 'r') as f:
            db_config = json.load(f)
        generator.save_to_database(db_config)
    
    logger.info("✓ Store generation complete!")


if __name__ == '__main__':
    main()