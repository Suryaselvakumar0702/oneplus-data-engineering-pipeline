import requests
import pandas as pd
import json
import time
from urllib.parse import urljoin


# ============================================================
# 1. API CONFIGURATION
# ============================================================

CATEGORY_API_URL = (
    "https://mallapi.oneplus.in/"
    "v2/api/rest/mallweb/category/config/fetch"
)

PRODUCT_API_URL = (
    "https://mallapi.oneplus.in/"
    "v2/api/rest/mallweb/category/goods/fetch"
)

BASE_URL = "https://www.oneplus.in"


HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://www.oneplus.in",
    "Referer": "https://www.oneplus.in/",
    "User-Agent": "Mozilla/5.0"
}


# ============================================================
# 2. SETTINGS
# ============================================================

STORE_VIEW_CODE = "in"

SETTLE_CHANNEL = 3

PAGE_SIZE = 12

SORT_OPTION = "LATEST"

# Safety limit to prevent infinite pagination
MAX_PAGES = 100


# ============================================================
# 3. FETCH ALL CATEGORIES
# ============================================================

def fetch_categories():

    print("\n" + "=" * 60)
    print("FETCHING ONEPLUS CATEGORIES")
    print("=" * 60)

    payload = {
        "settleChannel": SETTLE_CHANNEL,
        "storeViewCode": STORE_VIEW_CODE
    }

    try:

        response = requests.post(
            CATEGORY_API_URL,
            headers=HEADERS,
            json=payload,
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        # ----------------------------------------------------
        # Get category list
        # ----------------------------------------------------

        category_list = (
            data
            .get("data", {})
            .get("categoryList", [])
        )

        if not category_list:

            print("No categories found.")

            return []

        categories = []

        print(
            f"\nTotal categories returned by API: "
            f"{len(category_list)}"
        )

        # ----------------------------------------------------
        # Extract category information
        # ----------------------------------------------------

        for category in category_list:

            category_name = category.get(
                "categoryName"
            )

            category_code = category.get(
                "categoryCode"
            )

            url_key = category.get(
                "urlKey"
            )

            # ------------------------------------------------
            # Skip invalid categories
            # ------------------------------------------------

            if not category_code:

                continue

            # ------------------------------------------------
            # Skip "All"
            #
            # Individual categories are processed instead.
            # This avoids extracting the same products twice.
            # ------------------------------------------------

            if category_name == "All":

                continue

            categories.append({

                "category_name":
                    category_name,

                "category_code":
                    category_code,

                "url_key":
                    url_key
            })

        # ----------------------------------------------------
        # Display categories
        # ----------------------------------------------------

        print(
            f"\nCategories to process: "
            f"{len(categories)}"
        )

        print("\nCategory list:")

        for category in categories:

            print(
                f"- {category['category_name']} "
                f"| {category['category_code']} "
                f"| {category['url_key']}"
            )

        return categories

    except requests.exceptions.RequestException as e:

        print("\nCategory API request failed.")
        print("Error:", e)

        return []

    except ValueError as e:

        print("\nInvalid category API response.")
        print("Error:", e)

        return []


# ============================================================
# 4. FETCH ONE PRODUCT PAGE
# ============================================================

def fetch_product_page(
    category_code,
    page
):

    payload = {

        "settleChannel":
            SETTLE_CHANNEL,

        "storeViewCode":
            STORE_VIEW_CODE,

        "filterGroupQueryList":
            [],

        "categoryCode":
            category_code,

        "currentPage":
            page,

        "pageSize":
            PAGE_SIZE,

        "sceneType":
            1,

        "sortOption":
            SORT_OPTION
    }

    response = requests.post(
        PRODUCT_API_URL,
        headers=HEADERS,
        json=payload,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ============================================================
# 5. EXTRACT PRODUCTS FROM ONE CATEGORY
# ============================================================

def extract_category_products(category):

    category_name = category[
        "category_name"
    ]

    category_code = category[
        "category_code"
    ]

    category_url_key = category[
        "url_key"
    ]

    print("\n" + "=" * 60)

    print(
        f"CATEGORY: {category_name}"
    )

    print(
        f"CODE: {category_code}"
    )

    print("=" * 60)

    category_products = []

    page = 1

    # Used to prevent duplicate pages
    seen_product_codes = set()

    while page <= MAX_PAGES:

        print(
            f"Fetching {category_name} - "
            f"page {page}..."
        )

        try:

            # ------------------------------------------------
            # Fetch page
            # ------------------------------------------------

            data = fetch_product_page(
                category_code,
                page
            )

            # ------------------------------------------------
            # Get API data
            # ------------------------------------------------

            api_data = data.get(
                "data",
                {}
            )

            if api_data is None:

                api_data = {}

            # ------------------------------------------------
            # Get product list
            # ------------------------------------------------

            product_list = api_data.get(
                "productList"
            )

            # ------------------------------------------------
            # No productList
            # ------------------------------------------------

            if product_list is None:

                print(
                    f"No product list on page {page}."
                )

                break

            # ------------------------------------------------
            # Empty product list
            # ------------------------------------------------

            if len(product_list) == 0:

                print(
                    f"No products on page {page}."
                )

                break

            # ------------------------------------------------
            # Display count
            # ------------------------------------------------

            print(
                f"Products returned: "
                f"{len(product_list)}"
            )

            # ------------------------------------------------
            # Check for repeated products
            # ------------------------------------------------

            new_products = []

            for product in product_list:

                product_code = product.get(
                    "productCode"
                )

                # If product has a product code
                if product_code:

                    if product_code in seen_product_codes:

                        continue

                    seen_product_codes.add(
                        product_code
                    )

                new_products.append(
                    product
                )

            # ------------------------------------------------
            # If page contains nothing new
            # ------------------------------------------------

            if not new_products:

                print(
                    "No new products found."
                )

                print(
                    "Stopping pagination."
                )

                break

            # ------------------------------------------------
            # Add category information to products
            # ------------------------------------------------

            for product in new_products:

                product["_category_name"] = (
                    category_name
                )

                product["_category_code"] = (
                    category_code
                )

                product["_category_url"] = (
                    urljoin(
                        BASE_URL,
                        category_url_key
                        or ""
                    )
                )

            category_products.extend(
                new_products
            )

            print(
                f"New products added: "
                f"{len(new_products)}"
            )

            # ------------------------------------------------
            # Pagination information
            # ------------------------------------------------

            pagination = api_data.get(
                "pagination"
            )

            # ------------------------------------------------
            # If API provides pagination
            # ------------------------------------------------

            if pagination:

                current_page = pagination.get(
                    "currentPage"
                )

                total_pages = pagination.get(
                    "totalPages"
                )

                print(
                    f"Pagination: "
                    f"{current_page} / "
                    f"{total_pages}"
                )

                if (
                    current_page is not None
                    and total_pages is not None
                    and current_page >= total_pages
                ):

                    print(
                        "Last page reached."
                    )

                    break

            # ------------------------------------------------
            # If API does NOT provide pagination
            # ------------------------------------------------

            else:

                # If fewer products than PAGE_SIZE
                # are returned, this is normally
                # the last page.

                if len(product_list) < PAGE_SIZE:

                    print(
                        "Returned products are less "
                        "than PAGE_SIZE."
                    )

                    print(
                        "Last page reached."
                    )

                    break

            # ------------------------------------------------
            # Next page
            # ------------------------------------------------

            page += 1

            time.sleep(0.5)

        except requests.exceptions.RequestException as e:

            print(
                f"Request failed on page {page}."
            )

            print(
                "Error:",
                e
            )

            break

        except ValueError as e:

            print(
                f"Invalid JSON on page {page}."
            )

            print(
                "Error:",
                e
            )

            break

    print(
        f"\nTotal products extracted from "
        f"{category_name}: "
        f"{len(category_products)}"
    )

    return category_products


# ============================================================
# 6. EXTRACT ALL WEBSITE PRODUCTS
# ============================================================

def extract_all_products(categories):

    all_products = []

    print("\n" + "=" * 60)
    print("STARTING ALL-CATEGORY EXTRACTION")
    print("=" * 60)

    # --------------------------------------------------------
    # Loop through every category
    # --------------------------------------------------------

    for category in categories:

        products = extract_category_products(
            category
        )

        all_products.extend(
            products
        )

        time.sleep(1)

    print("\n" + "=" * 60)

    print(
        "ALL-CATEGORY EXTRACTION COMPLETED"
    )

    print("=" * 60)

    print(
        "Total raw product records:",
        len(all_products)
    )

    return all_products


# ============================================================
# 7. NORMALIZE PRODUCTS AND SKUs
# ============================================================

def normalize_products(products):

    rows = []

    # ========================================================
    # Loop through products
    # ========================================================

    for product in products:

        # ----------------------------------------------------
        # Product information
        # ----------------------------------------------------

        product_name = product.get(
            "productName"
        )

        product_code = product.get(
            "productCode"
        )

        # ----------------------------------------------------
        # MAIN PRODUCT URL
        #
        # Prefer productDetailUrl
        # ----------------------------------------------------

        product_url = product.get(
            "productDetailUrl"
        )

        # ----------------------------------------------------
        # Fallback URL
        # ----------------------------------------------------

        if not product_url:

            product_url = product.get(
                "productUrl"
            )

        # ----------------------------------------------------
        # Make sure URL is absolute
        # ----------------------------------------------------

        if product_url:

            product_url = urljoin(
                BASE_URL,
                product_url
            )

        # ----------------------------------------------------
        # Keep original short URL
        # ----------------------------------------------------

        product_short_url = product.get(
            "productUrl"
        )

        if product_short_url:

            product_short_url = urljoin(
                BASE_URL,
                product_short_url
            )

        # ----------------------------------------------------
        # Category
        # ----------------------------------------------------

        category_name = product.get(
            "_category_name"
        )

        category_code = product.get(
            "_category_code"
        )

        category_url = product.get(
            "_category_url"
        )

        # ----------------------------------------------------
        # Product-level fields
        # ----------------------------------------------------

        product_original_price = product.get(
            "originalPrice"
        )

        product_now_price = product.get(
            "nowPrice"
        )

        product_discount = product.get(
            "discountRate"
        )

        discount_tag = product.get(
            "discountRateTag"
        )

        product_image = product.get(
            "primeImageUrl"
        )

        product_has_stock = product.get(
            "hasStock"
        )

        product_out_stock = product.get(
            "outStock"
        )

        product_new = product.get(
            "newProduct"
        )

        product_publish_time = product.get(
            "publishTime"
        )

        # ====================================================
        # SKU LIST
        # ====================================================

        sku_list = product.get(
            "skuList"
        )

        if sku_list is None:

            sku_list = []

        # ====================================================
        # Extract every SKU
        # ====================================================

        for sku in sku_list:

            # ------------------------------------------------
            # Color
            # ------------------------------------------------

            color_data = sku.get(
                "color"
            )

            if color_data is None:

                color_data = {}

            # ------------------------------------------------
            # RAM / Storage
            # ------------------------------------------------

            rom_data = sku.get(
                "rom"
            )

            if rom_data is None:

                rom_data = {}

            # =================================================
            # CREATE ROW
            # =================================================

            row = {

                # Category
                "category_name":
                    category_name,

                "category_code":
                    category_code,

                "category_url":
                    category_url,

                # Product
                "product_name":
                    product_name,

                "product_code":
                    product_code,

                # URLs
                "product_url":
                    product_url,

                "product_short_url":
                    product_short_url,

                # SKU
                "sku_code":
                    sku.get("skuCode"),

                "sku_name":
                    sku.get("skuName"),

                # Color
                "color":
                    color_data.get("optLabel"),

                "color_code":
                    color_data.get("optCode"),

                # RAM / Storage
                "ram_storage":
                    rom_data.get("optLabel"),

                "storage_code":
                    rom_data.get("optCode"),

                # Price
                "original_price":
                    sku.get("originalPrice"),

                "sale_price":
                    sku.get("salePrice"),

                "now_price":
                    sku.get("nowPrice"),

                # Discount
                "discount_rate":
                    sku.get("discountRate"),

                "discount_tag":
                    discount_tag,

                # Stock
                "has_stock":
                    sku.get("hasStock"),

                "out_stock":
                    sku.get("outStock"),

                "low_stock":
                    sku.get("lowStock"),

                # Status
                "new_product":
                    sku.get("newProduct"),

                "sale_status":
                    sku.get("saleStatus"),

                # Other
                "publish_time":
                    sku.get("publishTime"),

                "has_gift":
                    sku.get("hasGift"),

                # Image
                "image_url":
                    sku.get("primeImageUrl"),

                "image_alt":
                    sku.get("imageAlt")
            }

            rows.append(row)

        # ====================================================
        # PRODUCT WITHOUT SKU
        # ====================================================

        if not sku_list:

            row = {

                "category_name":
                    category_name,

                "category_code":
                    category_code,

                "category_url":
                    category_url,

                "product_name":
                    product_name,

                "product_code":
                    product_code,

                "product_url":
                    product_url,

                "product_short_url":
                    product_short_url,

                "sku_code":
                    None,

                "sku_name":
                    None,

                "color":
                    None,

                "color_code":
                    None,

                "ram_storage":
                    None,

                "storage_code":
                    None,

                "original_price":
                    product_original_price,

                "sale_price":
                    None,

                "now_price":
                    product_now_price,

                "discount_rate":
                    product_discount,

                "discount_tag":
                    discount_tag,

                "has_stock":
                    product_has_stock,

                "out_stock":
                    product_out_stock,

                "low_stock":
                    None,

                "new_product":
                    product_new,

                "sale_status":
                    product.get(
                        "saleStatus"
                    ),

                "publish_time":
                    product_publish_time,

                "has_gift":
                    product.get(
                        "hasGift"
                    ),

                "image_url":
                    product_image,

                "image_alt":
                    None
            }

            rows.append(row)

    return rows


# ============================================================
# 8. REMOVE DUPLICATES
# ============================================================

def remove_duplicates(rows):

    df = pd.DataFrame(rows)

    if df.empty:

        return df

    # --------------------------------------------------------
    # Remove duplicate SKU records
    # --------------------------------------------------------

    if "sku_code" in df.columns:

        sku_exists = (
            df["sku_code"].notna()
        )

        df_with_sku = (
            df[sku_exists]
            .drop_duplicates(
                subset=["sku_code"],
                keep="first"
            )
        )

        df_without_sku = (
            df[~sku_exists]
        )

        df = pd.concat(
            [
                df_with_sku,
                df_without_sku
            ],
            ignore_index=True
        )

    # --------------------------------------------------------
    # Remove duplicate products if product code repeats
    # --------------------------------------------------------

    # Note:
    # We DO NOT remove rows based on product_code here
    # because one product can have multiple SKUs.

    return df


# ============================================================
# 9. SAVE RAW DATA
# ============================================================

def save_raw_data(products):

    with open(
        "oneplus_all_products_raw.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            products,
            file,
            ensure_ascii=False,
            indent=4
        )

    print(
        "\nRaw JSON saved:"
    )

    print(
        "oneplus_all_products_raw.json"
    )


# ============================================================
# 10. SAVE DATAFRAME
# ============================================================

def save_dataframe(df):

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    df.to_csv(
        "oneplus_all_products.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------------
    # Excel
    # --------------------------------------------------------

    df.to_excel(
        "oneplus_all_products.xlsx",
        index=False
    )

    print("\nFiles saved successfully!")

    print(
        "1. oneplus_all_products.csv"
    )

    print(
        "2. oneplus_all_products.xlsx"
    )


# ============================================================
# 11. MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "ONEPLUS ALL PRODUCT EXTRACTOR"
    )

    print("=" * 60)

    # ========================================================
    # STEP 1
    # Get categories automatically
    # ========================================================

    categories = fetch_categories()

    if not categories:

        print(
            "\nNo categories available."
        )

        return

    # ========================================================
    # STEP 2
    # Extract products from every category
    # ========================================================

    products = extract_all_products(
        categories
    )

    if not products:

        print(
            "\nNo products extracted."
        )

        return

    # ========================================================
    # STEP 3
    # Save raw JSON
    # ========================================================

    save_raw_data(
        products
    )

    # ========================================================
    # STEP 4
    # Normalize products + SKUs
    # ========================================================

    print("\n" + "=" * 60)

    print(
        "NORMALIZING PRODUCTS"
    )

    print("=" * 60)

    rows = normalize_products(
        products
    )

    # ========================================================
    # STEP 5
    # Create DataFrame
    # ========================================================

    df = remove_duplicates(
        rows
    )

    # ========================================================
    # STEP 6
    # Display results
    # ========================================================

    print("\n" + "=" * 60)

    print(
        "FINAL DATAFRAME"
    )

    print("=" * 60)

    if df.empty:

        print(
            "DataFrame is empty."
        )

        return

    # --------------------------------------------------------
    # Display first 10 rows
    # --------------------------------------------------------

    print(
        df.head(10).to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Total rows
    # --------------------------------------------------------

    print(
        "\nTotal rows:",
        len(df)
    )

    # --------------------------------------------------------
    # Total columns
    # --------------------------------------------------------

    print(
        "Total columns:",
        len(df.columns)
    )

    # ========================================================
    # STEP 7
    # Display category summary
    # ========================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "CATEGORY SUMMARY"
    )

    print(
        "=" * 60
    )

    category_summary = (
        df.groupby(
            "category_name"
        )["product_code"]
        .nunique()
        .sort_values(
            ascending=False
        )
    )

    print(
        category_summary
    )

    # ========================================================
    # STEP 8
    # Save CSV + Excel
    # ========================================================

    save_dataframe(
        df
    )

    # ========================================================
    # COMPLETE
    # ========================================================

    print(
        "\n" + "=" * 60
    )

    print(
        "ALL PRODUCT EXTRACTION COMPLETED"
    )

    print(
        "=" * 60
    )


# ============================================================
# 12. RUN PROGRAM
# ============================================================

if __name__ == "__main__":

    main()