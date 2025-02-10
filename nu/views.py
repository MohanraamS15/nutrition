

import google.generativeai as genai
import os
import pandas as pd
import requests
import re
from django.conf import settings
from django.shortcuts import render

# Set Google Gemini API Key (Replace with your actual API key)
GEMINI_API_KEY = "AIzaSyDhW7eaojtomDvn8u6AjeI75I0MCkNvAJ8"

# Configure Google Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Define unit conversions for different food measures
UNIT_CONVERSIONS = {
    "cup": 236.5, "cups": 236.5,
    "oz": 28.35, "ounce": 28.35, "ounces": 28.35,
    "slice": 30, "slices": 30,
    "egg": 50, "eggs": 50,
    "tbsp": 14.3, "tsp": 4.2
}

def extract_numeric(value):
    """ Extract numeric part from a mixed string (e.g., '2 eggs' -> 2). """
    match = re.search(r"(\d+\.?\d*)", str(value))
    return float(match.group(1)) if match else 1  # Default to 1 if no number is found

def safe_float(value):
    """ Convert value to float, return 0 if conversion fails. """
    try:
        return float(value)
    except ValueError:
        return 0  # If not a number, return 0

def fetch_nutrition_from_gemini(food_name, quantity):
    """ Ask Gemini API for estimated nutritional values. """
    
    prompt = f"Give the estimated calories, protein, fiber, fat, and carbs for {quantity}g of {food_name}. Return the result in JSON format with keys: Calories, Protein, Fiber, Fat, Carbohydrates."

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)

        # Extract text response and convert to dictionary
        result = response.text
        nutrition_data = eval(result)  

        return {
            "Calories": float(nutrition_data.get("Calories", 0)),
            "Protein": float(nutrition_data.get("Protein", 0)),
            "Fiber": float(nutrition_data.get("Fiber", 0)),
            "Fat": float(nutrition_data.get("Fat", 0)),
            "Carbohydrates": float(nutrition_data.get("Carbohydrates", 0))
        }

    except Exception as e:
        print(f"Gemini API Error: {e}")
        return None  # Return None if Gemini API fails

def fetch_nutrition_from_dataset(food_name, quantity, quantity_type):
    """ Fetch nutrition data from the Kaggle dataset. """
    dataset_path = os.path.join(settings.BASE_DIR, 'nu/data/nutritional_facts.csv')

    if not os.path.exists(dataset_path):
        return None  # Return None if file is missing

    df = pd.read_csv(dataset_path)
    df.columns = df.columns.str.lower().str.strip()

    # Replace 't' and empty values with 0
    df.replace("t", 0, inplace=True)
    df.fillna(0, inplace=True)

    food_data = df[df['food'].str.lower().str.contains(food_name.lower(), na=False)]

    if not food_data.empty:
        food_info = food_data.iloc[0]
        measure_text = str(food_info.get("measure", "1"))
        measure_value = extract_numeric(measure_text)
        measure_unit = measure_text.replace(str(measure_value), "").strip().lower()
        grams = safe_float(food_info.get("grams", 100))

        if measure_unit in UNIT_CONVERSIONS:
            grams = measure_value * UNIT_CONVERSIONS[measure_unit]

        if quantity_type == "count":
            quantity = quantity * (grams / measure_value)

        return {
            "Calories": safe_float(food_info.get("calories", 0)) * (quantity / grams),
            "Protein": safe_float(food_info.get("protein", 0)) * (quantity / grams),
            "Fat": safe_float(food_info.get("fat", 0)) * (quantity / grams),
            "Fiber": safe_float(food_info.get("fiber", 0)) * (quantity / grams),
            "Carbohydrates": safe_float(food_info.get("carbs", 0)) * (quantity / grams)
        }

    return None  # If no match found

def fetch_nutrition_from_usda(food_name):
    """ Fetch nutrition data from USDA API. """
    API_KEY = "your_usda_api_key"
    USDA_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

    params = {"query": food_name, "api_key": API_KEY}
    response = requests.get(USDA_URL, params=params)
    data = response.json()

    if "foods" in data and len(data["foods"]) > 0:
        nutrients = data["foods"][0]["foodNutrients"]
        return {
            nutrient["nutrientName"]: nutrient["value"]
            for nutrient in nutrients
        }

    return None  # If no data found

def fetch_nutrition_data(food_name, quantity, quantity_type):
    """ Fetch nutrition data from Gemini API first, then Dataset, finally USDA API. """
    
    # 1️⃣ First, try Gemini API
    nutrition = fetch_nutrition_from_gemini(food_name, quantity)
    if nutrition:
        return nutrition  # ✅ Found using Gemini

    # 2️⃣ If Gemini fails, try the dataset
    nutrition = fetch_nutrition_from_dataset(food_name, quantity, quantity_type)
    if nutrition:
        return nutrition  # ✅ Found in dataset

    # 3️⃣ If still not found, use the USDA API
    return fetch_nutrition_from_usda(food_name)

def get_food_nutrition(request):
    """ Handle user request for nutrition data. """
    if request.method == "POST":
        food_name = request.POST.get("food_name")
        quantity = float(request.POST.get("quantity"))  # Grams entered by user
        quantity_type = request.POST.get("quantity_type", "grams")

        # Get nutrition data (Gemini → Dataset → USDA API)
        nutrition = fetch_nutrition_data(food_name, quantity, quantity_type)

        if nutrition:
            return render(
                request,
                "nu/nutrition_result.html",
                {"nutrition": nutrition, "food_name": food_name, "quantity": quantity, "quantity_type": quantity_type},
            )

        return render(
            request, "nu/nutrition_result.html", {"nutrition": None, "food_name": food_name}
        )  # Show error if no data found

    return render(request, "nu/food_input.html")
