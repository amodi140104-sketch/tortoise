from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.exceptions import AirflowSkipException
from datetime import datetime, timedelta
import json
import re
import os
import logging

logger = logging.getLogger(__name__)

# Configuration
SCRAPY_PROJECT_PATH = "/mnt/c/Users/Animesh Modi/Desktop/Apache_Kafka/FDP/tortoise"
OUTPUT_FILE = f"{SCRAPY_PROJECT_PATH}/mobiles.json"
SPIDER_NAME = "flipkart_search"
SEARCH_QUERY = "mobile phones"  # ← ADD: Search query parameter

def clean_and_enrich_data(**context):
    """Clean and enrich scraped mobile data"""
    filepath = OUTPUT_FILE
    
    # Check if file exists
    if not os.path.exists(filepath):
        logger.error(f"{filepath} not found. Scraping may have failed.")
        raise FileNotFoundError(f"{filepath} not found. Check scrape_mobiles logs.")

    # Check file size
    file_size = os.path.getsize(filepath)
    logger.info(f"Found {filepath}, size: {file_size} bytes")
    
    if file_size == 0:
        logger.error(f"{filepath} is empty")
        raise ValueError(f"{filepath} is empty. Scraping may have failed.")

    # Read and parse JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        with open(filepath, 'r') as f:
            logger.error(f"File contents (first 500 chars): {f.read(500)}")
        raise RuntimeError(f"Invalid JSON in {filepath}: {e}")

    # Validate data structure
    if not isinstance(raw_data, list):
        logger.warning(f"Expected list but got {type(raw_data).__name__}")
        raw_data = [raw_data] if isinstance(raw_data, dict) else []

    if not raw_data:
        logger.warning("No data scraped. Check if Flipkart changed their HTML structure.")
        raise AirflowSkipException("No data scraped.")

    logger.info(f"Processing {len(raw_data)} items")

    # Clean and enrich data
    cleaned = []
    for idx, item in enumerate(raw_data):
        try:
            # Extract price
            price_str = item.get('price', '0')
            price = int(re.sub(r'[^\d]', '', str(price_str))) if price_str else 0

            # Extract rating and reviews
            rating = float(item.get('rating', 0) or 0)
            reviews = int(item.get('reviews', 0) or 0)
            
            # Calculate value score
            value_score = (rating * reviews) / price if price > 0 else 0

            cleaned.append({
                **item,
                'price_numeric': price,
                'value_score': value_score,
                'scraped_at': datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Error processing item {idx}: {e}")
            continue

    logger.info(f"Successfully cleaned {len(cleaned)} items")
    
    # Save cleaned data
    cleaned_file = f'{SCRAPY_PROJECT_PATH}/mobiles_cleaned.json'
    with open(cleaned_file, 'w') as f:
        json.dump(cleaned, f, indent=2)
    logger.info(f"Cleaned data saved to {cleaned_file}")
    
    return cleaned


def find_best_deals(**context):
    """Find and display best value mobile phones"""
    data = context['ti'].xcom_pull(task_ids='clean_data')
    
    if not data:
        logger.info("No data received from clean_data")
        raise AirflowSkipException("No data to analyze.")

    logger.info(f"Analyzing {len(data)} products")

    try:
        # Sort by value score
        best_deals = sorted(
            data, 
            key=lambda x: x.get('value_score', 0), 
            reverse=True
        )[:10]
    except Exception as e:
        logger.error(f"Error sorting data: {e}")
        raise

    # Display results
    print("\n" + "="*80)
    print("TOP 10 BEST VALUE PHONES")
    print("="*80)
    
    for idx, phone in enumerate(best_deals, 1):
        name = phone.get('name', 'Unknown')
        price = phone.get('price_numeric', 0)
        rating = phone.get('rating', 0)
        reviews = phone.get('reviews', 0)
        value_score = phone.get('value_score', 0)
        
        print(f"\n{idx}. {name}")
        print(f"   Price: ₹{price:,}")
        print(f"   Rating: {rating} ⭐ ({reviews} reviews)")
        print(f"   Value Score: {value_score:.2f}")
    
    print("\n" + "="*80 + "\n")
    
    # Save results
    results_file = f'{SCRAPY_PROJECT_PATH}/best_deals.json'
    with open(results_file, 'w') as f:
        json.dump(best_deals, f, indent=2)
    logger.info(f"Best deals saved to {results_file}")


# DAG Default Arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Define DAG
with DAG(
    dag_id='mobile_deal_finder',
    default_args=default_args,
    description='Scrape Flipkart mobiles and find best deals',
    schedule_interval='0 9,21 * * *',  # 9 AM and 9 PM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['scrapy', 'etl', 'mobiles', 'flipkart']
) as dag:

    # Task 1: Scrape mobile data from Flipkart
    scrape = BashOperator(
        task_id='scrape_mobiles',
        bash_command=f"""
        set -euo pipefail
        
        echo "=========================================="
        echo "Starting Mobile Scraper"
        echo "Time: $(date)"
        echo "Query: {SEARCH_QUERY}"
        echo "=========================================="
        
        # Check scrapy availability
        if ! command -v scrapy >/dev/null 2>&1; then
            echo "ERROR: scrapy not found"
            exit 1
        fi
        
        echo "✓ Scrapy found: $(scrapy version)"
        
        # Navigate to project
        cd "{SCRAPY_PROJECT_PATH}" || exit 1
        echo "✓ Project directory: {SCRAPY_PROJECT_PATH}"
        
        # Verify scrapy.cfg
        if [ ! -f "scrapy.cfg" ]; then
            echo "ERROR: Not a valid Scrapy project"
            exit 1
        fi
        
        # Remove old output
        rm -f "{OUTPUT_FILE}"
        echo "✓ Cleaned old output"
        
        # Run the spider with query parameter
        echo "Running spider: {SPIDER_NAME}"
        echo "Command: scrapy crawl {SPIDER_NAME} -a query='{SEARCH_QUERY}' -O {OUTPUT_FILE}"
        echo ""
        
        scrapy crawl {SPIDER_NAME} -a query="{SEARCH_QUERY}" -O "{OUTPUT_FILE}"
        
        # Verify output
        if [ ! -f "{OUTPUT_FILE}" ]; then
            echo "ERROR: Output file not created"
            exit 1
        fi
        
        FILE_SIZE=$(wc -c < "{OUTPUT_FILE}")
        ITEM_COUNT=$(grep -o '{{' "{OUTPUT_FILE}" | wc -l)
        
        echo ""
        echo "=========================================="
        echo "✓ Scraping completed!"
        echo "Output: {OUTPUT_FILE}"
        echo "Size: $FILE_SIZE bytes"
        echo "Items scraped: ~$ITEM_COUNT"
        echo "=========================================="
        """,
        execution_timeout=timedelta(minutes=30),
    )

    # Task 2: Clean and enrich data
    clean = PythonOperator(
        task_id='clean_data',
        python_callable=clean_and_enrich_data,
    )

    # Task 3: Find best deals
    analyze = PythonOperator(
        task_id='find_deals',
        python_callable=find_best_deals,
    )

    # Define task dependencies
    scrape >> clean >> analyze