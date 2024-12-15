import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import pandas as pd
from playwright.sync_api import sync_playwright
import json
from urllib.parse import urlparse, urlunparse
from playwright_stealth import stealth_sync

def best_match_helper(my_products, store_products, index, row, store_name):
    best_match = None
    found_url = None
    found_price = None
    highest_score = 70
    if store_name == 'atb':
        highest_score = 55

    words = row['Назва Товару'].split()
    brand = words[1] if len(words) > 1 else None

    for product, price_and_url in store_products.items():

        if brand and brand.lower() not in product.lower():
            continue
        
        score = fuzz.ratio(row['Назва Товару'], product)
        
        if score > highest_score:
            highest_score = score
            best_match = product
            found_url = price_and_url['url']
            found_price = price_and_url['price']

    if best_match:
        my_products.loc[index, f'{store_name}_url'] = found_url
        my_products.loc[index, f'{store_name}_price'] = found_price


def find_best_match(my_products, atb_products = {}, silpo_products = {}, varus_products = {}):
    
    for index, row in my_products.iterrows():

        best_match_helper(my_products, silpo_products, index, row, "silpo")
        best_match_helper(my_products, atb_products, index, row, "atb")
        best_match_helper(my_products, varus_products, index, row, "varus")
        

    return my_products


# Function to fetch products from Silpo website

def get_silpo_products(url):
    product_names = {}
    current_page = 1
    last_page = False
    product_names = {}

    while not last_page:
        page_url = f"{url}?page={current_page}"
        response = requests.get(page_url)
        
        if response.status_code != 200:
            print(f"Failed to retrieve page {current_page}")
            break  # If we can't fetch the page, stop the loop
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check if the "Показати ще" button is disabled (indicating the last page)
        load_more_button = soup.find('button', class_='pagination__more')
        if load_more_button and 'disabled' in load_more_button.attrs:
            print(f"Reached the last page: {current_page}")
            last_page = True  # Stop when the button is disabled, indicating the last page
        
        # Extract product names and links
        
        for product_card in soup.find_all('div', class_='ng-star-inserted'):
            # Extract the product name from the aria-label
            
            product_name = product_card.get('aria-label')
            if product_name:
                product_name_split = product_name.split(';')
                product_name = product_name_split[0] + product_name_split[2]
                product_price = product_name_split[1]
                product_link = product_card.find('a', class_='product-card')
                if product_link:
                    product_url = product_link.get('href')
                    if product_url:
                        # Full URL might need to be constructed if it's relative
                        full_url = f"https://silpo.ua{product_url}"
                        product_names[product_name] = {"url":full_url, "price":product_price}
        
        # If no products are found on the current page, we are done
        if not product_card:
            print(f"No products found on page {current_page}. Stopping.")
            break
        
        # # Add the products from the current page to the overall list
        # product_names.update(page_product_names)
        
        # Move to the next page
        current_page += 1

    return product_names


def scrap_varus_products_from_page(soup, product_dict):
        
    product_cards = soup.find_all('div', class_='sf-product-card__wrapper')
    
    for product_card in product_cards:
        # Get the product name
        product_name_tag = product_card.find('h2', class_='sf-product-card__title')
        if product_name_tag:
            product_name = product_name_tag.get_text(strip=True)

        # Get the product URL
        product_link_tag = product_card.find('a', class_='sf-link sf-product-card__link')
        if product_link_tag:
            product_url = product_link_tag.get('href')
            if product_url:
                product_url = f"https://varus.ua{product_url}"  # Construct full URL

        # Get the current price
        price_tag = product_card.find('div', class_='sf-price')
        if price_tag:
            special_price_tag = price_tag.find('ins', class_='sf-price__special')
            if special_price_tag:
                special_price = special_price_tag.get_text(strip=True)
            else:
                # If no special price, get the regular price
                regular_price_tag = price_tag.find('span', class_='sf-price__regular')
                if regular_price_tag:
                    special_price = regular_price_tag.get_text(strip=True)
                else:
                    special_price = None  # If no price is found, mark it as N/A


        # Save product info in dictionary (only the name, URL, and current price)
        product_dict[product_name] = {
            'url': product_url,
            'price': special_price
        }
        product_url = None
        special_price = None


def get_varus_products(url):
    product_dict = {}
    with sync_playwright() as p:
        # Launch a browser instance (headless by default)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()


        page.goto(url)
        page.wait_for_load_state('networkidle')
        
        # Loop to handle pagination
        while True:
            # Get the HTML content of the current page
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            scrap_varus_products_from_page(soup, product_dict)

            # Find the "Load More" button
            load_more_button = page.query_selector('button.sf-button.load-more')
            if load_more_button:
                # Click the button to load more products
                load_more_button.click()
                page.wait_for_load_state('networkidle')  # Wait for the new content to load
            else:
                # If the button is not found, we've reached the last page
                print("No more 'Load More' button found. Stopping pagination.")
                break

        # Process last page
        html_content = page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        scrap_varus_products_from_page(soup, product_dict)

    return product_dict

def scrap_atb_products_from_page(soup, product_dict):

     # Find all product containers in the HTML
        products = soup.find_all('article', class_='catalog-item')

        # Iterate through each product and extract the required information
        for product in products:
            # Extract product name
            name = product.find('div', class_='catalog-item__title')
            if name:
                name = name.get_text(strip=True)
            
            # Extract product URL
            product_url = product.find('a', class_='catalog-item__photo-link')
            if product_url:
                product_url = product_url.get('href')
            
            # Extract product price
            price = product.find('div', class_='catalog-item__product-price')
            if price:
                price_tag = price.find('data', class_='product-price__top')
                if price_tag:
                    price = price_tag.get_text(strip=True)
                else:
                    price = None
            
            # Store the extracted data in the dictionary
            if name:
                product_dict[name] = {
                    "url": f"https://www.atbmarket.com{product_url}",
                    "price": price.replace("/шт", "")
                }



def get_atb_products(url):

    product_dict = {}

    with sync_playwright() as p:

        product_dict = {}
        current_page = 1
        while True:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            page_url = f"{url}?page={current_page}"
            
            page.goto(page_url)
            page.wait_for_load_state('networkidle')  # Ensure page is fully loaded

            # Scrape content
            html_content = page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract data and check if new products are added
            products_len = len(product_dict)
            scrap_atb_products_from_page(soup, product_dict)

            if products_len == len(product_dict):
                print("No new products found. Stopping.")
                break

            current_page += 1
            browser.close()
       
    return product_dict


def get_and_match_masterzoo_products(url, products_df):
    with sync_playwright() as p:
        # Launch a browser instance (headless by default)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        page.wait_for_load_state('networkidle')

        for index, row in products_df.iterrows():
            product_name = row['Назва Товару']
            input_selector = 'input#q'  # CSS selector for the input element
            page.fill(input_selector, product_name) 
            page.wait_for_timeout(1000)
            html_content = page.content()

            soup = BeautifulSoup(html_content, 'html.parser')
            item = soup.find('div', class_='multi-item')
            if item:
                product_url = item.find('a')['href']
                price = item.find('span', class_='multi-price').text.strip()
                row['masterzoo_price'] = price
                row['masterzoo_url'] = product_url
                products_df.loc[index, 'masterzoo_url'] = product_url
                products_df.loc[index, 'masterzoo_price'] = price
                



def main ():


    file_path = "test-19.xlsx"
    df_porducts = pd.read_excel(file_path)
    df_porducts['silpo_price'] = None
    df_porducts['silpo_url'] = None
    df_porducts['varus_price'] = None
    df_porducts['varus_url'] = None
    df_porducts['atb_price'] = None
    df_porducts['atb_url'] = None
    df_porducts['masterzoo_price'] = None
    df_porducts['masterzoo_url'] = None

    # Fetch the product names from the Silpo website
    silpo_url = "https://silpo.ua/category/dlia-tvaryn-653"
    varus_url = "https://varus.ua/tovari-dlya-tvarin"
    atb_url = "https://www.atbmarket.com/catalog/436-tovari-dlya-tvarin"
    masterzoo_url = "https://masterzoo.ua/ua/zoomarketi/#/search/"

    # get_and_match_masterzoo_products(masterzoo_url, df_porducts)

    # atb_products = get_atb_products(atb_url)
    silpo_products = get_silpo_products(silpo_url)
    #varus_products = get_varus_products(varus_url)
    # Find the best matches

    # matches = find_best_match(df_porducts, atb_products=atb_products,silpo_products=silpo_products,varus_products=varus_products)
    
    matches = find_best_match(df_porducts, silpo_products=silpo_products)

    output_file = 'output.csv'
    matches.to_csv(output_file, index=False)


main()