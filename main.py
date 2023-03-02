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

# Create webdriver object
options = webdriver.ChromeOptions()
options.add_argument('headless')
driver = webdriver.Chrome(options=options)

# Read email username and password from configuration file
config = configparser.ConfigParser()
config.read('/mnt/c/Users/mahei/OneDrive/Documentos/Python/monitor-aliexpress-product-price/config.cfg')
sender_email = config.get('Email', 'username')
sender_password = config.get('Email', 'password')

# Define function to check price
def check_price(products):
    prices = pd.DataFrame(columns=['id', 'product', 'url', 'price', 'datetime'])
    for product in products:
        urls = products[product]["urls"]
        desired_price = products[product]["desired_price"]
        for url in urls:
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
            prices = pd.concat([prices, pd.DataFrame({'id': [str(uuid.uuid4())], 'product': [product], 'url': [url], 'price': [price], 'datetime': [now]})], ignore_index=True)
    
    # Write prices to parquet file
    file_path = 'monitor-aliexpress-product-price/prices.parquet'
    if not os.path.isfile(file_path):
        prices.to_parquet(file_path, engine='fastparquet')
    else:
        prices.to_parquet(file_path, engine='fastparquet', append=True)
    
    # Return DataFrame of prices
    return prices

def check_previous_price(lowest_price, product):
    # Read previous prices from parquet file
    file_path = 'monitor-aliexpress-product-price/prices.parquet'
    if os.path.isfile(file_path):
        previous_prices = pd.read_parquet(file_path, engine='fastparquet')
        previous_prices = previous_prices[previous_prices['product'] == product]
    else:
        return None
    # Find previous lowest price for product
    previous_lowest_price = previous_prices[previous_prices['price'] < lowest_price].sort_values('datetime', ascending=False).head(1)
    if previous_lowest_price.empty:
        return None
    else:
        url = previous_lowest_price['url'].iloc[0]
        price = previous_lowest_price['price'].iloc[0]
        return {'product': product, 'url': url, 'price': price}



def send_email_alert(prices, products):
    message = "Subject: Price Alert\n\n"
    for product, group in prices.groupby('product'):
        lowest_price = group['price'].min()
        previous_price = check_previous_price(lowest_price, product)
        for index, row in group.iterrows():
            price = row["price"]
            url = row["url"]
            if previous_price is None or price < previous_price['price']:
                message += f"The {product} you are tracking is now R$ {price}.\n{url}\n\n"
    if "Price Alert" not in message:
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
    with open('monitor-aliexpress-product-price/products.json', 'r') as f:
        products = json.load(f)
    # Check price every hour and send email alert if below desired price 
    while True:
        current_prices = check_price(products)
        send_email_alert(current_prices,products)
        print("Waiting for an hour before checking prices again...")
        time.sleep(5) # Wait for an hour

# Run main function        
if __name__ == "__main__":
    main()