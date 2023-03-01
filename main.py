# Import modules
from selenium import webdriver
from selenium.webdriver.common.by import By
import smtplib
import time

# Set product URL and desired price
product_url = "https://pt.aliexpress.com/item/1005004767710064.html"
desired_price = 3000

# Set email address and password
sender_email = "maheidem@gmail.com"
sender_password = "uteqsnifmnuxbcwd"

# Create webdriver object
driver = webdriver.Chrome()

# Define function to check price
def check_price():
    # Load product page
    driver.get(product_url)

    # Find price element
    price_element = driver.find_element(By.CLASS_NAME, 'product-price-value')

    # Get price text and convert to float
    price_text = price_element.text.replace("R$ ", "").replace('.', '').replace(',', '.')
    price = float(price_text)

    # Return price
    return price

# Define function to send email alert
def send_email_alert(price):
    # Create email message
    message = f"Subject: Price Alert\n\nThe product you are tracking is now R$ {price}.\n{product_url}"

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
        current_price = check_price()
        if current_price < desired_price:
            send_email_alert(current_price)
        
        # time.sleep(60) # Wait for an hour

# Run main function        
if __name__ == "__main__":
   main()