from rapidfuzz import fuzz, process
import pandas as pd
from atb import get_atb_products
from varus import get_varus_products
from silpo import get_silpo_products
from masterzoo import get_and_match_masterzoo_products

class ProductMatcher:
    def __init__(self, my_products, atb_products=None, silpo_products=None, varus_products=None):
        self.my_products = my_products
        self.atb_products = atb_products or {}
        self.silpo_products = silpo_products or {}
        self.varus_products = varus_products or {}

    def _best_match_helper(self, store_products, index, row, store_name, threshold=70):
        best_match = None
        found_url = None
        found_price = None

        words = row['Назва Товару'].split()
        brand = words[1] if len(words) > 1 else None

        for product, price_and_url in store_products.items():
            # Skip products that don’t match the brand
            if brand and brand.lower() not in product.lower():
                continue

            # Compute similarity score
            score = fuzz.ratio(row['Назва Товару'].lower(), product.lower())

            if score > threshold:
                threshold = score
                best_match = product
                found_url = price_and_url['url']
                found_price = price_and_url['price']

        # Record the best match if found
        if best_match:
            self.my_products.loc[index, f'{store_name}_url'] = found_url
            self.my_products.loc[index, f'{store_name}_price'] = found_price
 

    def find_best_match(self):
        for index, row in self.my_products.iterrows():
            self._best_match_helper(self.silpo_products, index, row, "silpo")
            self._best_match_helper(self.atb_products, index, row, "atb", threshold=55)
            self._best_match_helper(self.varus_products, index, row, "varus")
        return self.my_products

def main():
    file_path = "test-19.xlsx"
    df_products = pd.read_excel(file_path)
    df_products['silpo_price'] = None
    df_products['silpo_url'] = None
    df_products['varus_price'] = None
    df_products['varus_url'] = None
    df_products['atb_price'] = None
    df_products['atb_url'] = None
    df_products['masterzoo_price'] = None
    df_products['masterzoo_url'] = None

    silpo_url = "https://silpo.ua/category/dlia-tvaryn-653"
    varus_url = "https://varus.ua/tovari-dlya-tvarin"
    atb_url = "https://www.atbmarket.com/catalog/436-tovari-dlya-tvarin"
    masterzoo_url = "https://masterzoo.ua/ua/zoomarketi/#/search/"

    # Fetch the product names from the websites
    get_and_match_masterzoo_products(masterzoo_url, df_products)

    atb_products = get_atb_products(atb_url)
    silpo_products = get_silpo_products(silpo_url)
    varus_products = get_varus_products(varus_url)

    # Create an instance of ProductMatcher and find matches
    matcher = ProductMatcher(
        df_products,
        atb_products=atb_products,
        silpo_products=silpo_products,
        varus_products=varus_products
    )

    matches = matcher.find_best_match()

    # Save the results
    output_file = 'output.csv'
    matches.to_csv(output_file, index=False)

if __name__ == "__main__":
    main()
