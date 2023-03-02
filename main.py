# Import modules
from selenium import webdriver
from selenium.webdriver.common.by import By
import smtplib
import time
import configparser
import pandas as pd
import uuid
from datetime import datetime
import json
import os

#defining path for files
conf_email_credential_path = 'monitor-aliexpress-product-price/config.cfg'
parquet_history_path = 'monitor-aliexpress-product-price/prices.parquet'
product_list_json_path = 'monitor-aliexpress-product-price/products.json'

# Create webdriver object
options = webdriver.ChromeOptions()
options.add_argument('headless')
driver = webdriver.Chrome(options=options)

# Read email username and password from configuration file
config = configparser.ConfigParser()
config.read(conf_email_credential_path)
sender_email = config.get('Email', 'username')
sender_password = config.get('Email', 'password')

# Define function to check price
def check_price(products):
    prices = pd.DataFrame(columns=['id', 'loop_id', 'product', 'url', 'price', 'datetime'])
    loop_id = str(uuid.uuid4())
    for product in products:
        urls = products[product]["urls"]
        desired_price = products[product]["desired_price"]
        for url in urls:
            try:
                # Load product page
                driver.get(url)
                print(f"Checking price for {product} at {url}")
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
                print(f'The URL - {url} gave an error')
    
    # Write prices to parquet file
    file_path = parquet_history_path
    if not os.path.isfile(file_path):
        prices.to_parquet(file_path, engine='fastparquet', compression='gzip')
    else:
        prices.to_parquet(file_path, engine='fastparquet', compression='gzip', append=True)
    
    # Return DataFrame of prices
    return prices

def check_previous_price(product):
    # Read previous prices from parquet file
    file_path = parquet_history_path
    if os.path.isfile(file_path):
        previous_prices = pd.read_parquet(file_path, engine='fastparquet')
        previous_prices = previous_prices[previous_prices['product'] == product]
    else:
        return None
    # Find previous lowest price for product
    previous_lowest_price = previous_prices.loc[previous_prices['loop_id'] == previous_prices.sort_values(by=['datetime'], ascending=False).head(1)['loop_id'].values[0]].nsmallest(n=1, columns=['price'])
    if previous_lowest_price.empty:
        return None
    else:
        urls = previous_lowest_price['url']
        price = previous_lowest_price['price']
        return {'product': product, 'urls': urls, 'price': price}

def send_email_alert(prices):
    message = "Subject: Price Alert\n\n"
    for product, group in prices.groupby('product'):
        lowest_price = group.nsmallest(n=1, columns=['price'])
        previous_price = check_previous_price(product)
        if previous_price is None or lowest_price['price'].values[0] < previous_price['price'].values[0]:
            message += f"The {product} you are tracking is now R$ {lowest_price['price'].values[0]}.\n{lowest_price['url'].values[0]}\n\n"
    if "you are tracking is" not in message:
        return
    print("Sending email alert...")
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
        current_prices = check_price(products)
        send_email_alert(current_prices)
        print("Waiting for an hour before checking prices again...")
        time.sleep(5) # Wait for an hour

# Run main function        
if __name__ == "__main__":
    main()