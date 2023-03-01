# Import modules
from selenium import webdriver
from selenium.webdriver.common.by import By
import smtplib
import time
import configparser

# Set list of product URLs and desired prices
products = {
    "Product 1": {
        "url": "https://pt.aliexpress.com/item/1005003359522996.html"
    },
    "Product 2": {
        "url": "https://pt.aliexpress.com/item/1005004667422776.html"
    },
    "Product 3": {
        "url": "https://pt.aliexpress.com/item/1005004643544273.html"
    },
    "Product 4": {
        "url": "https://pt.aliexpress.com/item/1005004767710064.html"
    },
    "Product 5": {
        "url": "https://pt.aliexpress.com/item/1005003391597856.html"
    },
    "Product 6": {
        "url": "https://pt.aliexpress.com/item/1005003391612933.html"
    },
    "Product 7": {
        "url": "https://pt.aliexpress.com/item/1005003391623760.html"
    },
    "Product 8": {
        "url": "https://pt.aliexpress.com/item/1005004586709793.html"
    },
    "Product 9": {
        "url": "https://pt.aliexpress.com/item/1005004305762942.html"
    }
}

desired_price =  2700

# Create webdriver object
driver = webdriver.Chrome()

# Read email username and password from configuration file
config = configparser.ConfigParser()
config.read('config.cfg')
sender_email = config.get('Email', 'username')
sender_password = config.get('Email', 'password')

# Define function to check price
def check_price(products):
    prices = {}
    for product in products:
        # Load product page
        driver.get(products[product]["url"])

    # Find price element
        try:
            price_element = driver.find_element(By.CLASS_NAME, 'uniform-banner-box-price')
        except:
            price_element = driver.find_element(By.CLASS_NAME, 'product-price-value')

        # Get price text and convert to float
        price_text = price_element.text.replace("R$ ", "").replace('.', '').replace(',', '.')
        price = float(price_text)

        # Add price to dictionary
        prices[product] = price

    # Return dictionary of prices
    return prices

# Define function to send email alert
def send_email_alert(prices):
    for product in prices:
        if prices[product] < desired_price:
            print(f'Vou mandar um e-mail para o item {products[product]["url"]}')
            # Create email message
            message = f"Subject: Price Alert\n\nThe {product} you are tracking is now R$ {prices[product]}.\n{products[product]['url']}"
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
    # Check price every hour and send email alert if below desired price 
    while True:
        current_prices = check_price(products)
        send_email_alert(current_prices)       
        time.sleep(60) # Wait for an hour

# Run main function        
if __name__ == "__main__":
   main()
