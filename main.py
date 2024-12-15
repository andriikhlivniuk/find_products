from fuzzywuzzy import fuzz
import pandas as pd
from atb import get_atb_products
from varus import get_varus_products
from silpo import get_silpo_products
from masterzoo import get_and_match_masterzoo_products


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

    get_and_match_masterzoo_products(masterzoo_url, df_porducts)

    atb_products = get_atb_products(atb_url)
    silpo_products = get_silpo_products(silpo_url)
    varus_products = get_varus_products(varus_url)
    # Find the best matches

    matches = find_best_match(df_porducts, atb_products=atb_products,silpo_products=silpo_products,varus_products=varus_products)
    
    #matches = find_best_match(df_porducts, silpo_products=silpo_products)

    output_file = 'output.csv'
    matches.to_csv(output_file, index=False)


main()