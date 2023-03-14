# Import modules
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
import smtplib
import time
import configparser
import pandas as pd
import uuid
from datetime import datetime, timedelta
import json
import os, sys
from multiprocessing import Pool, cpu_count

from loguru import logger

# Filter out logs with severity lower than ERROR
logger.add(sys.stderr, level="ERROR")

#defining path for files
conf_email_credential_path = 'data/config.cfg'
parquet_history_path = 'data/prices.parquet'
product_list_json_path = 'data/products.json'

# Read email username and password from configuration file
def load_global_conf_vars():
    config = configparser.ConfigParser()
    config.read(conf_email_credential_path)
    global sender_email
    sender_email = config.get('Email', 'username')
    global sender_password
    sender_password = config.get('Email', 'password')
    global run_interval
    run_interval = int(config.get('Interval','interval'))
    global n_cpus
    n_cpus = int(config.get('Multiprocessing','cpus'))


def set_chrome_options() -> None:
    """Sets chrome options for Selenium.
    Chrome options for headless browser is enabled.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_prefs = {}
    chrome_options.experimental_options["prefs"] = chrome_prefs
    chrome_prefs["profile.default_content_settings"] = {"images": 2}
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-setuid-sandbox")
    chrome_options.add_argument("--disable-accelerated-2d-canvas")
    chrome_options.add_argument("--disable-accelerated-jpeg-decoding")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-zygote")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu-sandbox")
    return chrome_options

# Define function to check price for a single product URL
def check_single_price(args):
    product, url, loop_id = args
    prices = pd.DataFrame(columns=['id', 'loop_id', 'product', 'url', 'price', 'datetime'])
    driver = webdriver.Chrome(options=set_chrome_options())
    try:
        # Load product page
        driver.get(url)
        logger.debug(f"PID:{os.getpid()} - Checking price for {product} at {url}")
        # Find price element
        try:
            price_element = driver.find_element(By.CLASS_NAME, 'uniform-banner-box-price')
        except:
            price_element = driver.find_element(By.CLASS_NAME, 'product-price-value')
        # Get price text and convert to float
        price_text = price_element.text.replace("R$ ", "").replace('.', '').replace(',', '.')
        price = float(price_text)
        # Add price and datetime to DataFrame
        now = datetime.now()
        prices = pd.concat([prices, pd.DataFrame({'id': [str(uuid.uuid4())], 'loop_id': [loop_id], 'product': [product], 'url': [url], 'price': [price], 'datetime': [now]})], ignore_index=True)
    except:
        logger.error(f'PID:{os.getpid()} - The URL - {url} gave an error')
    driver.quit()
    return prices

# Define function to check price for multiple products and URLs using multiprocessing
def check_price(products):
    prices = pd.DataFrame(columns=['id', 'loop_id', 'product', 'url', 'price', 'datetime'])
    loop_id = str(uuid.uuid4())
    args_list = []
    for product in products:
        urls = products[product]["urls"]
        for url in urls:
            args_list.append((product, url, loop_id))
    with Pool(n_cpus) as p:
        results = p.map(check_single_price, args_list)
    prices = pd.concat(results, ignore_index=True)
    # Write prices
    
    # Write prices to parquet file
    file_path = parquet_history_path
    # Extract year, month, and day as new columns
    if prices.shape[0] == 0:
        return prices
    else:    
        prices['year'] = prices['datetime'].dt.year
        prices['month'] = prices['datetime'].dt.month
        prices['day'] = prices['datetime'].dt.day
        if not os.path.isdir(file_path):
            prices.to_parquet(file_path, engine='fastparquet', compression='gzip', partition_cols=['product', 'year', 'month', 'day'])
        else:
            prices.to_parquet(file_path, engine='fastparquet', compression='gzip', partition_cols=['product', 'year', 'month', 'day'], append=True)
        
        # Return DataFrame of prices
        return prices

def check_previous_price(product,current_loop_id):
    # Read previous prices from parquet file
    file_path = parquet_history_path
    # Get current year, month and day
    now = datetime.now() - timedelta(days=1)
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')

    # Define the filters
    filters = [('product', '==', product), ('year', '==', year), ('month', '==', month), ('day', '>=', day), ('loop_id', '!=', current_loop_id)]

    if os.path.isdir(file_path):
        previous_prices = pd.read_parquet(file_path, engine='fastparquet', filters=filters)
        previous_prices = previous_prices[previous_prices['loop_id'] != current_loop_id]
    else:
        return None
    # Find previous lowest price for product
    previous_lowest_price = previous_prices.loc[previous_prices['loop_id'] == previous_prices.tail(1)['loop_id'].values[0]].nsmallest(n=1, columns=['price'])
    if previous_lowest_price.empty:
        return None
    else:
        urls = previous_lowest_price['url']
        price = previous_lowest_price['price']
        return {'product': product, 'urls': urls, 'price': price}

def clean_historical_data(path):
    df = pd.read_parquet(path)
    df['prev_price'] = df.groupby(['product', 'url'])['price'].shift(1)
    df['price_diff'] = df['price'] - df['prev_price']
    df = df[df["price_diff"] != 0]
    df.to_parquet(path)

def send_email_alert(prices):
    message = "Subject: Price Alert\n\n"
    for product, group in prices.groupby('product'):
        lowest_price = group.nsmallest(n=1, columns=['price'])
        previous_price = check_previous_price(product,lowest_price['loop_id'].values[0])
        logger.info(f"Product: {lowest_price['product'].values[0]} - Lowest Current Price: {lowest_price['price'].values[0]} | Previous Lowest Price: {previous_price['price'].values[0]}")
        if previous_price is None or lowest_price['price'].values[0] < previous_price['price'].values[0]:
            message += f"The {product} you are tracking is now R$ {lowest_price['price'].values[0]}.\n{lowest_price['url'].values[0]}\n\n"
    if "you are tracking is" not in message:
        return
    logger.info("Sending email alert...")
    # Create SMTP object
    server = smtplib.SMTP("smtp.gmail.com", 587)
    # Start TLS encryption
    server.starttls()
    # Login to email account
    server.login(sender_email, sender_password)
    # Send email message
    server.sendmail(sender_email, sender_email, message)
    # Quit SMTP object
    server.quit()

# Define main function
def main():
    # Read products from JSON file
    with open(product_list_json_path, 'r') as f:
        products = json.load(f)
    # Check price every hour and send email alert if below desired price 

    while True:
        load_global_conf_vars()
        current_prices = check_price(products)
        if current_prices.shape[0] == 0:
            logger.error('Unable to read prices in this loop')
        else:
            send_email_alert(current_prices)
            logger.info(f"Waiting for {run_interval} seconds before checking prices again...")
        time.sleep(run_interval) # Wait for an hour

# Run main function        
if __name__ == "__main__":
    main()