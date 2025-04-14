import json
import re
from typing import Any, List, Dict, Optional, Union
from dataclasses import dataclass
from difflib import SequenceMatcher
from collections import Counter, defaultdict
import math
from mcp.server.fastmcp import FastMCP

# 1) Initialize your MCP server with a descriptive name
mcp = FastMCP("medicines-db")

# 2) Load the large JSON file once at startup
DATA_PATH = "File_Path"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    medicines: List[dict] = json.load(f)

# 3) Create multiple indices for fast lookups
name_index = {entry["Name"]: entry for entry in medicines if "Name" in entry}
manufacturer_index = defaultdict(list)
composition_index = defaultdict(list)
price_index = defaultdict(list)
prescription_index = {"Yes": [], "No": []}

# Build all indices
for entry in medicines:
    # Manufacturer index
    if "Manufacturer" in entry:
        manufacturer_index[entry["Manufacturer"]].append(entry)
    
    # Composition index (split by '+' to index individual components)
    if "Composition" in entry:
        full_comp = entry["Composition"]
        # Index the full composition
        composition_index[full_comp].append(entry)
        # Index individual components
        for component in full_comp.split("+"):
            component = component.strip()
            # Extract the active ingredient name (removing dosage info)
            match = re.search(r"([\w\s-]+)\s*\(", component)
            if match:
                ingredient = match.group(1).strip()
                composition_index[ingredient].append(entry)
    
    # Price range index (buckets of 100)
    if "MRP" in entry:
        try:
            price = float(entry["MRP"])
            bucket = math.floor(price / 100) * 100
            price_index[bucket].append(entry)
        except (ValueError, TypeError):
            pass
    
    # Prescription index
    if "Prescription" in entry:
        prescription_index[entry["Prescription"]].append(entry)

# Extract unique active ingredients for better search
all_ingredients = set()
for entry in medicines:
    if "Composition" in entry:
        components = entry["Composition"].split("+")
        for component in components:
            match = re.search(r"([\w\s-]+)\s*\(", component)
            if match:
                all_ingredients.add(match.group(1).strip())

# Helper function for similarity matching
def similarity_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

# Helper function to extract active ingredients from composition
def extract_ingredients(composition: str) -> List[str]:
    ingredients = []
    if not composition:
        return ingredients
        
    components = composition.split("+")
    for component in components:
        match = re.search(r"([\w\s-]+)\s*\(", component)
        if match:
            ingredients.append(match.group(1).strip())
        else:
            # If pattern doesn't match, use the whole component
            ingredients.append(component.strip())
    return ingredients

# Helper function to format medicine record for display
def format_medicine(medicine: Dict[str, Any]) -> Dict[str, Any]:
    """Format a medicine record for better display, adding derived fields."""
    result = medicine.copy()
    
    # Add formatted price if available
    if "MRP" in result:
        try:
            price = float(result["MRP"])
            result["Price_INR"] = f"₹{price:.2f}"
            
            # Add price category
            if price < 50:
                result["Price_Category"] = "Low"
            elif price < 200:
                result["Price_Category"] = "Medium"
            elif price < 500:
                result["Price_Category"] = "High"
            else:
                result["Price_Category"] = "Premium"
                
        except (ValueError, TypeError):
            pass
            
    # Extract and add active ingredients list
    if "Composition" in result:
        result["Active_Ingredients"] = extract_ingredients(result["Composition"])
        
        # Number of ingredients
        result["Ingredient_Count"] = len(result["Active_Ingredients"])
        
        # Check if combination medicine (more than one ingredient)
        result["Is_Combination"] = result["Ingredient_Count"] > 1
        
    # Add prescription requirement in plain language
    if "Prescription" in result:
        if result["Prescription"] == "Yes":
            result["Requires_Prescription"] = True
            result["Prescription_Type"] = "Prescription Required"
        else:
            result["Requires_Prescription"] = False
            result["Prescription_Type"] = "Over-the-Counter"
            
    return result

@mcp.tool()
def get_medicine_by_name(name: str, include_alternatives: bool = True) -> str:
    """
    Retrieve a medicine record by its exact Name, with optional cheaper alternatives.
    
    Args:
        name: The exact Name field of the medicine.
        include_alternatives: Whether to include cheaper alternatives in results.
        
    Returns:
        JSON-encoded record with alternatives, or an error message.
    """
    entry = name_index.get(name)
    if not entry:
        # Try fuzzy match if exact match fails
        best_match = None
        best_score = 0
        
        for med_name in name_index:
            score = similarity_score(name, med_name)
            if score > best_score and score >= 0.8:
                best_score = score
                best_match = med_name
                
        if best_match:
            entry = name_index[best_match]
            result = {
                "note": f"Exact medicine not found. Showing closest match: '{best_match}'",
                "medicine": format_medicine(entry)
            }
        else:
            return f"Medicine named '{name}' not found."
    else:
        result = {"medicine": format_medicine(entry)}
    
    # Automatically include cheaper alternatives if requested
    if include_alternatives and "MRP" in entry:
        try:
            med_price = float(entry["MRP"])
            ref_ingredients = []
            
            if "Composition" in entry:
                ref_ingredients = extract_ingredients(entry["Composition"])
            
            cheaper_alternatives = []
            similar_composition_alternatives = []
            
            for alt in medicines:
                if alt["Name"] == entry["Name"]:
                    continue
                    
                if "MRP" not in alt:
                    continue
                    
                try:
                    alt_price = float(alt["MRP"])
                    
                    # Check if it's cheaper
                    if alt_price < med_price:
                        formatted_alt = format_medicine(alt)
                        
                        # Check composition similarity if we have reference ingredients
                        if ref_ingredients and "Composition" in alt:
                            alt_ingredients = extract_ingredients(alt["Composition"])
                            
                            if alt_ingredients:
                                # Calculate Jaccard similarity
                                set1 = set(ref_ingredients)
                                set2 = set(alt_ingredients)
                                
                                intersection = len(set1.intersection(set2))
                                union = len(set1.union(set2))
                                
                                if union > 0:
                                    similarity = intersection / union
                                    
                                    # If similar composition and cheaper, it's a great alternative
                                    if similarity >= 0.7:
                                        cheaper_alternatives.append({
                                            "medicine": formatted_alt,
                                            "price_savings": f"₹{med_price - alt_price:.2f}",
                                            "savings_percentage": f"{((med_price - alt_price) / med_price) * 100:.1f}%",
                                            "similarity_score": f"{similarity:.2f}"
                                        })
                                    # If somewhat similar, keep track separately
                                    elif similarity >= 0.4:
                                        similar_composition_alternatives.append({
                                            "medicine": formatted_alt,
                                            "price_savings": f"₹{med_price - alt_price:.2f}",
                                            "savings_percentage": f"{((med_price - alt_price) / med_price) * 100:.1f}%",
                                            "similarity_score": f"{similarity:.2f}"
                                        })
                except (ValueError, TypeError):
                    continue
            
            # Sort alternatives by savings (highest first)
            cheaper_alternatives.sort(key=lambda x: float(x["savings_percentage"].rstrip('%')), reverse=True)
            similar_composition_alternatives.sort(key=lambda x: float(x["similarity_score"]), reverse=True)
            
            result["cheaper_alternatives"] = cheaper_alternatives[:5]  # Top 5 cheapest with similar composition
            
            # If we have few or no high-similarity alternatives, include some with lower similarity
            if len(cheaper_alternatives) < 3:
                result["similar_composition_alternatives"] = similar_composition_alternatives[:3]
                
        except (ValueError, TypeError):
            # If price parsing fails, skip alternatives
            pass
    
    return json.dumps(result, ensure_ascii=False)

@mcp.tool()
def search_medicines(query: str, max_results: int = 10) -> str:
    """
    Full-text search across all medicine fields.
    
    Args:
        query: Substring to search (case-insensitive).
        max_results: Maximum number of matching records to return.
        
    Returns:
        JSON-encoded list of matches, or a not-found message.
    """
    q = query.lower()
    results = []
    for entry in medicines:
        # flatten entry to a single string for simple search
        if q in json.dumps(entry, ensure_ascii=False).lower():
            results.append(format_medicine(entry))
        if len(results) >= max_results:
            break
    
    if not results:
        return f"No medicines found containing '{query}'."
    
    return json.dumps(results, ensure_ascii=False)

@mcp.tool()
def fuzzy_search_by_name(partial_name: str, similarity_threshold: float = 0.6, max_results: int = 10) -> str:
    """
    Search for medicines with names similar to the provided partial name using fuzzy matching.
    
    Args:
        partial_name: A partial or misspelled medicine name to search for.
        similarity_threshold: Minimum similarity score (0.0-1.0) to include in results.
        max_results: Maximum number of matching records to return.
        
    Returns:
        JSON-encoded list of matches sorted by similarity, or a not-found message.
    """
    if not partial_name or len(partial_name) < 3:
        return "Please provide at least 3 characters for fuzzy search."
        
    scored_results = []
    for med_name, entry in name_index.items():
        score = similarity_score(partial_name, med_name)
        if score >= similarity_threshold:
            scored_results.append((score, format_medicine(entry)))
    
    # Sort by similarity score (descending)
    scored_results.sort(reverse=True, key=lambda x: x[0])
    
    # Limit results
    top_results = [
        {"similarity_score": f"{score:.2f}", "medicine": entry} 
        for score, entry in scored_results[:max_results]
    ]
    
    if not top_results:
        return f"No medicines found with names similar to '{partial_name}'."
    
    return json.dumps(top_results, ensure_ascii=False)

@mcp.tool()
def search_by_composition(ingredient: str, max_results: int = 10) -> str:
    """
    Search for medicines containing a specific active ingredient.
    
    Args:
        ingredient: Name of an active ingredient to search for.
        max_results: Maximum number of matching records to return.
        
    Returns:
        JSON-encoded list of medicines containing the ingredient, or a not-found message.
    """
    results = []
    
    # Try exact match first
    if ingredient in composition_index:
        results = composition_index[ingredient][:max_results]
    else:
        # Try substring search in all compositions
        q = ingredient.lower()
        for entry in medicines:
            if "Composition" in entry and q in entry["Composition"].lower():
                results.append(entry)
            if len(results) >= max_results:
                break
    
    if not results:
        # Try fuzzy matching for ingredient names
        best_match = None
        best_score = 0
        
        for known_ingredient in all_ingredients:
            score = similarity_score(ingredient, known_ingredient)
            if score > best_score and score >= 0.7:
                best_score = score
                best_match = known_ingredient
                
        if best_match and best_match in composition_index:
            results = composition_index[best_match][:max_results]
            return json.dumps({
                "note": f"No exact match found. Showing results for similar ingredient: '{best_match}'",
                "matches": [format_medicine(r) for r in results]
            }, ensure_ascii=False)
    
    if not results:
        return f"No medicines found containing ingredient '{ingredient}'."
    
    return json.dumps([format_medicine(r) for r in results], ensure_ascii=False)

@mcp.tool()
def filter_by_price_range(min_price: float = 0, max_price: float = float('inf'), max_results: int = 20) -> str:
    """
    Filter medicines by price range.
    
    Args:
        min_price: Minimum price in INR.
        max_price: Maximum price in INR.
        max_results: Maximum number of matching records to return.
        
    Returns:
        JSON-encoded list of medicines within the price range, or a not-found message.
    """
    results = []
    
    for entry in medicines:
        if "MRP" in entry:
            try:
                price = float(entry["MRP"])
                if min_price <= price <= max_price:
                    results.append(format_medicine(entry))
                if len(results) >= max_results:
                    break
            except (ValueError, TypeError):
                continue
    
    if not results:
        return f"No medicines found in price range ₹{min_price:.2f} - ₹{max_price:.2f}."
    
    # Sort by price
    results.sort(key=lambda x: float(x["MRP"]) if "MRP" in x and x["MRP"] else float('inf'))
    
    return json.dumps(results, ensure_ascii=False)

@mcp.tool()
def filter_by_manufacturer(manufacturer: str, max_results: int = 20) -> str:
    """
    Filter medicines by manufacturer.
    
    Args:
        manufacturer: Full or partial manufacturer name.
        max_results: Maximum number of matching records to return.
        
    Returns:
        JSON-encoded list of medicines from the manufacturer, or a not-found message.
    """
    # First try exact match
    results = []
    if manufacturer in manufacturer_index:
        results = manufacturer_index[manufacturer][:max_results]
    else:
        # Try partial match
        manufacturer_lower = manufacturer.lower()
        for mfr, entries in manufacturer_index.items():
            if manufacturer_lower in mfr.lower():
                results.extend(entries)
                if len(results) >= max_results:
                    results = results[:max_results]
                    break
    
    if not results:
        return f"No medicines found from manufacturer '{manufacturer}'."
    
    return json.dumps([format_medicine(r) for r in results], ensure_ascii=False)

@mcp.tool()
def filter_by_prescription_requirement(prescription_required: bool, max_results: int = 20) -> str:
    """
    Filter medicines by prescription requirement.
    
    Args:
        prescription_required: True for prescription medicines, False for over-the-counter.
        max_results: Maximum number of matching records to return.
        
    Returns:
        JSON-encoded list of medicines with the specified prescription requirement.
    """
    key = "Yes" if prescription_required else "No"
    results = prescription_index.get(key, [])[:max_results]
    
    if not results:
        status = "prescription" if prescription_required else "non-prescription"
        return f"No {status} medicines found."
    
    return json.dumps([format_medicine(r) for r in results], ensure_ascii=False)

@mcp.tool()
def find_similar_medicines(medicine_name: str, max_results: int = 5) -> str:
    """
    Find medicines with similar composition to the specified medicine.
    
    Args:
        medicine_name: Name of the reference medicine.
        max_results: Maximum number of similar medicines to return.
        
    Returns:
        JSON-encoded list of similar medicines, or an error message.
    """
    reference = name_index.get(medicine_name)
    if not reference:
        # Try fuzzy match
        best_match = None
        best_score = 0
        
        for med_name in name_index:
            score = similarity_score(medicine_name, med_name)
            if score > best_score and score >= 0.8:
                best_score = score
                best_match = med_name
                
        if best_match:
            reference = name_index[best_match]
            medicine_name = best_match  # Update to the matched name
        else:
            return f"Medicine '{medicine_name}' not found."
    
    if "Composition" not in reference:
        return f"Cannot find similar medicines - no composition data for '{medicine_name}'."
    
    # Get the ingredients from the reference medicine
    ref_ingredients = extract_ingredients(reference["Composition"])
    if not ref_ingredients:
        return f"Cannot find similar medicines - unable to parse ingredients for '{medicine_name}'."
    
    # Score all other medicines by ingredient similarity
    similar_meds = []
    for entry in medicines:
        if entry["Name"] == medicine_name:
            continue  # Skip the reference medicine
            
        if "Composition" not in entry:
            continue
            
        entry_ingredients = extract_ingredients(entry["Composition"])
        
        # Calculate Jaccard similarity (intersection over union)
        set1 = set(ref_ingredients)
        set2 = set(entry_ingredients)
        
        if not set2:
            continue
            
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union > 0:
            similarity = intersection / union
            if similarity > 0:  # Any ingredient match
                similar_meds.append((similarity, entry))
    
    # Sort by similarity (descending)
    similar_meds.sort(reverse=True, key=lambda x: x[0])
    
    result = {
        "reference_medicine": format_medicine(reference),
        "similar_medicines": [
            {
                "similarity_score": f"{score:.2f}",
                "medicine": format_medicine(med)
            }
            for score, med in similar_meds[:max_results]
        ]
    }
    
    if not similar_meds:
        result["message"] = f"No medicines with similar composition to '{medicine_name}' found."
    
    return json.dumps(result, ensure_ascii=False)

@mcp.tool()
def get_medicine_statistics() -> str:
    """
    Get statistical overview of the medicines database.
    
    Returns:
        JSON-encoded statistics about the medicines database.
    """
    stats = {
        "total_medicines": len(medicines),
        "prescription_count": len(prescription_index.get("Yes", [])),
        "otc_count": len(prescription_index.get("No", [])),
        "unknown_prescription_status": len(medicines) - len(prescription_index.get("Yes", [])) - len(prescription_index.get("No", [])),
        "manufacturer_counts": dict(Counter(med["Manufacturer"] for med in medicines if "Manufacturer" in med).most_common(10)),
        "price_distribution": {
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "price_ranges": {}
        }
    }
    
    # Price statistics
    prices = []
    price_ranges = defaultdict(int)
    
    for entry in medicines:
        if "MRP" in entry:
            try:
                price = float(entry["MRP"])
                prices.append(price)
                
                # Price distribution in ranges of 100
                range_key = f"₹{math.floor(price/100)*100} - ₹{math.floor(price/100)*100 + 99.99}"
                price_ranges[range_key] += 1
                
            except (ValueError, TypeError):
                continue
    
    if prices:
        stats["price_distribution"]["min_price"] = f"₹{min(prices):.2f}"
        stats["price_distribution"]["max_price"] = f"₹{max(prices):.2f}"
        stats["price_distribution"]["avg_price"] = f"₹{sum(prices)/len(prices):.2f}"
        stats["price_distribution"]["price_ranges"] = dict(sorted(price_ranges.items()))
    
    # Common active ingredients
    ingredient_counter = Counter()
    for entry in medicines:
        if "Composition" in entry:
            ingredients = extract_ingredients(entry["Composition"])
            ingredient_counter.update(ingredients)
    
    stats["common_ingredients"] = dict(ingredient_counter.most_common(10))
    
    return json.dumps(stats, ensure_ascii=False)

@mcp.tool()
def paginated_search(query: str = "", page: int = 1, page_size: int = 10, 
                    manufacturer: str = "", min_price: float = 0, 
                    max_price: float = float('inf'), 
                    prescription_required: Optional[bool] = None,
                    ingredient: str = "") -> str:
    """
    Advanced search with pagination and multiple filters.
    
    Args:
        query: General search term (searches across all fields).
        page: Page number (starting from 1).
        page_size: Number of results per page.
        manufacturer: Filter by manufacturer (full or partial).
        min_price: Minimum price filter.
        max_price: Maximum price filter.
        prescription_required: Filter by prescription requirement (None for any).
        ingredient: Filter by active ingredient.
        
    Returns:
        JSON-encoded paginated results with meta information.
    """
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
    
    # Start with all medicines
    filtered_results = medicines.copy()
    
    # Apply filters one by one
    if query:
        q = query.lower()
        filtered_results = [
            entry for entry in filtered_results 
            if q in json.dumps(entry, ensure_ascii=False).lower()
        ]
    
    if manufacturer:
        manufacturer_lower = manufacturer.lower()
        filtered_results = [
            entry for entry in filtered_results
            if "Manufacturer" in entry and manufacturer_lower in entry["Manufacturer"].lower()
        ]
    
    if min_price > 0 or max_price < float('inf'):
        filtered_results = [
            entry for entry in filtered_results
            if "MRP" in entry and entry["MRP"] and min_price <= float(entry["MRP"]) <= max_price
        ]
    
    if prescription_required is not None:
        req_value = "Yes" if prescription_required else "No"
        filtered_results = [
            entry for entry in filtered_results
            if "Prescription" in entry and entry["Prescription"] == req_value
        ]
    
    if ingredient:
        ingredient_lower = ingredient.lower()
        filtered_results = [
            entry for entry in filtered_results
            if "Composition" in entry and ingredient_lower in entry["Composition"].lower()
        ]
    
    # Calculate pagination
    total_results = len(filtered_results)
    total_pages = math.ceil(total_results / page_size)
    
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    paginated_results = filtered_results[start_idx:end_idx]
    
    result = {
        "meta": {
            "total_results": total_results,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        },
        "results": [format_medicine(entry) for entry in paginated_results]
    }
    
    return json.dumps(result, ensure_ascii=False)

@mcp.tool()
def analyze_composition(composition: str) -> str:
    """
    Analyze a medicine composition string to extract and structure the ingredients.
    
    Args:
        composition: A composition string (e.g. "Ambroxol (30mg/5ml) + Levosalbutamol (1mg/5ml)").
        
    Returns:
        JSON-encoded structured analysis of the composition.
    """
    if not composition:
        return "Please provide a composition string to analyze."
    
    result = {
        "raw_composition": composition,
        "ingredients": []
    }
    
    components = composition.split("+")
    for component in components:
        component = component.strip()
        
        # Try to extract ingredient name and dosage
        name_match = re.search(r"([\w\s-]+)\s*\(", component)
        dosage_match = re.search(r"\(([\w\s\d\.\/]+)\)", component)
        
        ingredient = {
            "raw_text": component,
        }
        
        if name_match:
            ingredient["name"] = name_match.group(1).strip()
        else:
            ingredient["name"] = component
            
        if dosage_match:
            ingredient["dosage"] = dosage_match.group(1).strip()
            
            # Try to further parse the dosage
            dosage = ingredient["dosage"]
            value_match = re.search(r"(\d+(?:\.\d+)?)", dosage)
            unit_match = re.search(r"(\d+(?:\.\d+)?)\s*([a-zA-Z]+)", dosage)
            
            if value_match:
                ingredient["dosage_value"] = value_match.group(1)
                
            if unit_match:
                ingredient["dosage_unit"] = unit_match.group(2)
        
        result["ingredients"].append(ingredient)
    
    # Add similar medicines with this composition
    medicines_with_comp = []
    for entry in medicines:
        if "Composition" in entry and composition == entry["Composition"]:
            medicines_with_comp.append(format_medicine(entry))
    
    if medicines_with_comp:
        result["medicines_with_this_composition"] = medicines_with_comp[:5]
    
    return json.dumps(result, ensure_ascii=False)

@mcp.tool()
def count_medicines_by_composition(composition: str, exact_match: bool = False) -> str:
    """
    Count and list all medicines with a specific composition or containing specific ingredients.
    
    Args:
        composition: The composition or ingredient to search for.
        exact_match: If True, only find medicines with the exact composition.
                     If False, find medicines containing this ingredient.
        
    Returns:
        JSON-encoded count and list of medicines with pricing information.
    """
    results = []
    composition_lower = composition.lower()
    
    # Process exact matches first
    if exact_match:
        for entry in medicines:
            if "Composition" in entry and entry["Composition"] == composition:
                results.append(entry)
    else:
        # Process partial matches (contains the ingredient)
        for entry in medicines:
            if "Composition" in entry and composition_lower in entry["Composition"].lower():
                results.append(entry)
    
    if not results:
        if exact_match:
            return f"No medicines found with the exact composition: '{composition}'."
        else:
            return f"No medicines found containing: '{composition}'."
    
    # Group by manufacturer for better analysis
    manufacturers = defaultdict(list)
    for entry in results:
        if "Manufacturer" in entry:
            manufacturers[entry["Manufacturer"]].append(entry)
        else:
            manufacturers["Unknown"].append(entry)
    
    # Price analysis
    prices = []
    for entry in results:
        if "MRP" in entry:
            try:
                price = float(entry["MRP"])
                prices.append(price)
            except (ValueError, TypeError):
                continue
    
    price_stats = {}
    if prices:
        price_stats = {
            "min_price": f"₹{min(prices):.2f}",
            "max_price": f"₹{max(prices):.2f}",
            "avg_price": f"₹{sum(prices)/len(prices):.2f}",
            "total_medicines_with_price": len(prices)
        }
    
    # Sort medicines by price for easy comparison
    if prices:
        results.sort(key=lambda x: float(x["MRP"]) if "MRP" in x and x["MRP"] else float('inf'))
    
    response = {
        "query": composition,
        "exact_match": exact_match,
        "total_medicines_found": len(results),
        "total_manufacturers": len(manufacturers),
        "price_statistics": price_stats,
        "medicines": [format_medicine(entry) for entry in results],
        "by_manufacturer": {
            manufacturer: {
                "count": len(entries),
                "medicines": [format_medicine(entry) for entry in entries]
            }
            for manufacturer, entries in manufacturers.items()
        }
    }
    
    return json.dumps(response, ensure_ascii=False)

@mcp.tool()
def categorize_medicines(max_categories: int = 10) -> str:
    """
    Categorize medicines by active ingredients and return the most common categories.
    
    Args:
        max_categories: Maximum number of categories to return.
        
    Returns:
        JSON-encoded categories with example medicines.
    """
    # Create categories based on ingredients
    categories = defaultdict(list)
    
    for entry in medicines:
        if "Composition" in entry:
            ingredients = extract_ingredients(entry["Composition"])
            
            # Use the first ingredient as the primary category
            if ingredients:
                primary_ingredient = ingredients[0]
                categories[primary_ingredient].append(entry)
    
    # Get the most common categories
    top_categories = sorted(categories.items(), key=lambda x: len(x[1]), reverse=True)[:max_categories]
    
    result = []
    for category, entries in top_categories:
        result.append({
            "category": category,
            "medicine_count": len(entries),
            "example_medicines": [format_medicine(entry) for entry in entries[:3]]
        })
    
    return json.dumps(result, ensure_ascii=False)

@mcp.tool()
def get_all_manufacturers() -> str:
    """
    Get a list of all manufacturers in the database.
    
    Returns:
        JSON-encoded list of manufacturers with medicine counts.
    """
    result = [
        {"name": manufacturer, "medicine_count": len(entries)}
        for manufacturer, entries in manufacturer_index.items()
    ]
    
    # Sort by medicine count (descending)
    result.sort(key=lambda x: x["medicine_count"], reverse=True)
    
    return json.dumps(result, ensure_ascii=False)

@mcp.tool()
def suggest_alternatives(medicine_name: str, max_suggestions: int = 5) -> str:
    """
    Suggest alternative medicines based on composition similarity and price.
    
    Args:
        medicine_name: Name of the reference medicine.
        max_suggestions: Maximum number of alternatives to suggest.
        
    Returns:
        JSON-encoded list of alternative medicines with comparison data.
    """
    reference = name_index.get(medicine_name)
    if not reference:
        # Try fuzzy match
        best_match = None
        best_score = 0
        
        for med_name in name_index:
            score = similarity_score(medicine_name, med_name)
            if score > best_score and score >= 0.8:
                best_score = score
                best_match = med_name
                
        if best_match:
            reference = name_index[best_match]
            medicine_name = best_match  # Update to the matched name
        else:
            return f"Medicine '{medicine_name}' not found."
    
    if "Composition" not in reference:
        return f"Cannot suggest alternatives - no composition data for '{medicine_name}'."
    
    if "MRP" not in reference:
        return f"Cannot suggest alternatives - no price data for '{medicine_name}'."
    
    try:
        ref_price = float(reference["MRP"])
    except (ValueError, TypeError):
        return f"Cannot suggest alternatives - invalid price data for '{medicine_name}'."
    
    # Get medicines with similar composition
    ref_ingredients = extract_ingredients(reference["Composition"])
    if not ref_ingredients:
        return f"Cannot suggest alternatives - unable to parse ingredients for '{medicine_name}'."
    
    alternatives = []
    for entry in medicines:
        if entry["Name"] == medicine_name:
            continue  # Skip the reference medicine
            
        if "Composition" not in entry or "MRP" not in entry:
            continue
            
        try:
            entry_price = float(entry["MRP"])
        except (ValueError, TypeError):
            continue
            
        entry_ingredients = extract_ingredients(entry["Composition"])
        
        # Calculate ingredient similarity
        set1 = set(ref_ingredients)
        set2 = set(entry_ingredients)
        
        if not set2:
            continue
            
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        if union > 0:
            ingredient_similarity = intersection / union
            if ingredient_similarity >= 0.5:  # At least 50% similar ingredients
                # Calculate price difference percentage
                price_diff_pct = ((entry_price - ref_price) / ref_price) * 100
                
                alternatives.append({
                    "medicine": format_medicine(entry),
                    "ingredient_similarity": ingredient_similarity,
                    "price_difference_percentage": price_diff_pct,
                    "price_comparison": "cheaper" if price_diff_pct < 0 else "more expensive",
                    "absolute_price_difference": abs(entry_price - ref_price)
                })
    
    # Sort by similarity and then by price (cheaper first)
    alternatives.sort(key=lambda x: (-x["ingredient_similarity"], x["absolute_price_difference"]))
    
    result = {
        "reference_medicine": format_medicine(reference),
        "alternatives": alternatives[:max_suggestions]
    }
    
    if not alternatives:
        result["message"] = f"No suitable alternatives found for '{medicine_name}'."
    
    return json.dumps(result, ensure_ascii=False)

if __name__ == "__main__":
    # 4) Run over stdio so Claude Desktop can manage the process
    mcp.run(transport="stdio")