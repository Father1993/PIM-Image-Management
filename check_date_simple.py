#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

PIM_API_URL = os.getenv("PIM_API_URL")
PIM_LOGIN = os.getenv("PIM_LOGIN")
PIM_PASSWORD = os.getenv("PIM_PASSWORD")

def authenticate():
    response = requests.post(
        f"{PIM_API_URL}/sign-in/",
        json={"login": PIM_LOGIN, "password": PIM_PASSWORD, "remember": True}
    )
    response.raise_for_status()
    return response.json()["data"]["access"]["token"]

def get_product(token, product_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{PIM_API_URL}/product/{product_id}", headers=headers, timeout=30)
    if response.status_code == 200:
        data = response.json()
        if data.get("success") and data.get("data"):
            return data["data"]
    return None

if __name__ == "__main__":
    product_id = int(sys.argv[1]) if len(sys.argv) > 1 else 28160
    
    print(f"Auth...")
    token = authenticate()
    
    print(f"Getting product {product_id}...")
    product = get_product(token, product_id)
    
    if product:
        print(f"\nID: {product.get('id')}")
        print(f"Name: {product.get('header', 'N/A')[:50]}")
        print(f"Articul: {product.get('articul', 'N/A')}")
        print(f"catalogId: {product.get('catalogId', 'N/A')}")
        print(f"enabled: {product.get('enabled', 'N/A')}")
        print(f"deleted: {product.get('deleted', 'N/A')}")
        print(f"\nCreatedAt: {product.get('createdAt', 'N/A')}")
        print(f"UpdatedAt: {product.get('updatedAt', 'N/A')}")
    else:
        print(f"Product {product_id} not found!")

