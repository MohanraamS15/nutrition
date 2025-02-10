from django.shortcuts import render
import requests


import pandas as pd
import os
import re
import requests
from django.conf import settings

# Define approximate conversions (these can be adjusted)
UNIT_CONVERSIONS = {
    "cup": 236.5,   # 1 cup = 236.5g (approx, varies by food)
    "cups": 236.5,
    "oz": 28.35,    # 1 oz = 28.35g
    "ounce": 28.35,
    "ounces": 28.35,
    "slice": 30,    # Approximate weight per slice (varies by food)
    "slices": 30,
    "egg": 50,      # 1 egg ≈ 50g
    "eggs": 50,
    "tbsp": 14.3,   # 1 tbsp ≈ 14.3g
    "tsp": 4.2      # 1 tsp ≈ 4.2g
}

def extract_numeric(value):
    """ Extract numeric part from a mixed string (e.g., '2 eggs' -> 2). """
    match = re.search(r"(\d+\.?\d*)", str(value))
    return float(match.group(1)) if match else 1  # Default to 1 if no number is found

def fetch_nutrition_from_dataset(food_name, quantity, quantity_type):
    dataset_path = os.path.join(settings.BASE_DIR, 'nu/data/nutritional_facts.csv')

    if not os.path.exists(dataset_path):
        return None  # Return None if file is missing

    # Load dataset
    df = pd.read_csv(dataset_path)

    # Convert column names to lowercase and remove spaces
    df.columns = df.columns.str.lower().str.strip()

    # Replace 't' and empty values with 0
    df.replace("t", 0, inplace=True)
    df.fillna(0, inplace=True)

    # Search for the food name in the "food" column
    food_data = df[df['food'].str.lower().str.contains(food_name.lower(), na=False)]

    if not food_data.empty:
        food_info = food_data.iloc[0]  # Take the first matching row

        # Get the measure and grams values
        measure_text = str(food_info.get("measure", "1"))  # Default to "1"
        measure_value = extract_numeric(measure_text)  # Extract numeric value
        measure_unit = measure_text.replace(str(measure_value), "").strip().lower()  # Extract unit
        grams = float(food_info.get("grams", 100))  # Default to 100g if missing

        # If measure has a unit, convert to grams
        if measure_unit in UNIT_CONVERSIONS:
            grams = measure_value * UNIT_CONVERSIONS[measure_unit]

        # If user input is in "count", convert to grams
        if quantity_type == "count":
            quantity = quantity * (grams / measure_value)  # Adjust quantity based on dataset measure

        # Convert all values to float safely
        return {
            "Calories": float(food_info.get("calories", 0)) * (quantity / grams),
            "Protein": float(food_info.get("protein", 0)) * (quantity / grams),
            "Fat": float(food_info.get("fat", 0)) * (quantity / grams),
            "Saturated Fat": float(food_info.get("sat.fat", 0)) * (quantity / grams),
            "Fiber": float(food_info.get("fiber", 0)) * (quantity / grams),
            "Carbohydrates": float(food_info.get("carbs", 0)) * (quantity / grams)
        }

    return None  # If no match found


def get_food_nutrition(request):
    if request.method == 'POST':
        food_name = request.POST.get('food_name')
        quantity = float(request.POST.get('quantity'))  # Grams entered by user
        quantity_type = request.POST.get('quantity_type', 'grams')  # Default to grams

        # 1️⃣ First, check the dataset
        nutrition = fetch_nutrition_from_dataset(food_name, quantity, quantity_type)

        # 2️⃣ If not found in dataset, use the USDA API
        if not nutrition:
            nutrition = fetch_nutrition_from_usda(food_name)

        # 3️⃣ Return results to the template
        if nutrition:
            return render(request, 'nu/nutrition_result.html', {
                'nutrition': nutrition, 'food_name': food_name, 'quantity': quantity, 'quantity_type': quantity_type
            })

        return render(request, 'nu/nutrition_result.html', {
            'nutrition': None, 'food_name': food_name
        })  # Show error if no data found

    return render(request, 'nu/food_input.html')

# Function to fetch nutrition data from the USDA API
def fetch_nutrition_from_usda(food_name):
    API_KEY = 'owhyuZkWB21o9tvLdCCgcysDDUfvRr6b0o24bH81'  # Replace with your USDA API key
    BASE_URL = 'https://api.nal.usda.gov/fdc/v1/foods/search'
    params = {'query': food_name, 'api_key': API_KEY}
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if 'foods' in data and len(data['foods']) > 0:
        nutrients = data['foods'][0]['foodNutrients']
        return {nutrient['nutrientName']: nutrient['value'] for nutrient in nutrients}
    return None



def fetch_nutrition_from_usda(food_name):
    API_KEY = 'your_usda_api_key'  # Replace with your actual API key
    BASE_URL = 'https://api.nal.usda.gov/fdc/v1/foods/search'
    
    # Convert input to singular if needed (basic handling)
    if food_name.endswith('s'):  
        food_name = food_name[:-1]  # Convert "pineapples" to "pineapple"

    params = {'query': food_name, 'api_key': API_KEY}
    response = requests.get(BASE_URL, params=params)
    data = response.json()

    if 'foods' in data and len(data['foods']) > 0:
        nutrients = data['foods'][0]['foodNutrients']
        return {nutrient['nutrientName']: nutrient['value'] for nutrient in nutrients}
    
    # If no data found, return an error message
    return None


