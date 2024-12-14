import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import pandas as pd
from playwright.sync_api import sync_playwright
import json
from urllib.parse import urlparse, urlunparse


# Function to fetch products from Silpo website

def get_silpo_products(url):
    product_names = {}
    current_page = 1
    last_page = False

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
        page_product_names = {}
        
        for product_card in soup.find_all('div', class_='ng-star-inserted'):
            # Extract the product name from the aria-label
            product_name = product_card.get('aria-label')
            if product_name:
                # Extract the link (href) to the product page
                product_link = product_card.find('a', class_='product-card')
                if product_link:
                    product_url = product_link.get('href')
                    if product_url:
                        # Full URL might need to be constructed if it's relative
                        full_url = f"https://silpo.ua{product_url}"
                        page_product_names[product_name] = full_url
        
        # If no products are found on the current page, we are done
        if not page_product_names:
            print(f"No products found on page {current_page}. Stopping.")
            break
        
        # Add the products from the current page to the overall list
        product_names.update(page_product_names)
        
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
            # print(price_tag)
            # print("\n\n\n\n")
            # Try to get the special price (current price)
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
                print("Clicking 'Load More' button to fetch more products...")
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


def find_best_match(my_products, products):
    matches = {}

    for index, row in my_products.iterrows():
        best_match = None
        found_url = None
        highest_score = 70

        for product, url in products.items():
            score = fuzz.ratio(row['Назва Товару'], product)
            
            if score > highest_score:
                highest_score = score
                best_match = product
                found_url = url

        if best_match:
            my_products.loc[index, 'silpo_url'] = found_url
            my_products.loc[index, 'silpo_price'] = best_match.split(';')[1]

    return my_products

    

def main ():


    file_path = "test-19.xlsx"
    df_porducts = pd.read_excel(file_path)
    df_porducts['silpo_price'] = None
    df_porducts['silpo_url'] = None
    df_porducts['varus_price'] = None
    df_porducts['varus_url'] = None

    # Fetch the product names from the Silpo website
    silpo_url = "https://silpo.ua/category/dlia-tvaryn-653"
    varus_url = "https://varus.ua/tovari-dlya-tvarin"


    silpo_products = get_silpo_products(silpo_url)
    varus_products = get_varus_products(varus_url)

    # Find the best matches
    matches = find_best_match(df_porducts, silpo_products)

    output_file = 'output.csv'
    matches.to_csv(output_file, index=False)


main()