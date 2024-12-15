from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def scrap_atb_products_from_page(soup, product_dict):

    # Find all product containers in the HTML
    products = soup.find_all('article', class_='catalog-item')

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
            page.wait_for_load_state('networkidle')

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