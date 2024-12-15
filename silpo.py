import requests
from bs4 import BeautifulSoup

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
        
        # Check if the button is disabled (indicating the last page)
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
                        full_url = f"https://silpo.ua{product_url}"
                        product_names[product_name] = {"url":full_url, "price":product_price}
        
        # If no products are found on the current page, we are done
        if not product_card:
            print(f"No products found on page {current_page}. Stopping.")
            break

        # Move to the next page
        current_page += 1

    return product_names