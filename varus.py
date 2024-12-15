from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

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


        # Save product info in dictionary
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