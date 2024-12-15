from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


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
                