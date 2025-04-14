# INDIAN MEDICINES (MCP SERVER)

<div align="center">
  
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![FastMCP](https://img.shields.io/badge/FastMCP-gray.svg)
![JSON](https://img.shields.io/badge/JSON-gray.svg)

</div>

A comprehensive API server for medicine information lookup, alternative suggestions, and composition analysis. This server provides multiple endpoints for searching, filtering, and analyzing medicine data with advanced features like fuzzy matching and price comparison.

## 📖 Table of Contents

- [Introduction](#-introduction)
- [Features](#-features)
- [Tech Stack](#️-tech-stack)
- [Installation](#-installation)
- [Usage](#-usage)
- [API Reference](#-api-reference)
  - [Search Endpoints](#search-endpoints)
  - [Filter Endpoints](#filter-endpoints)
  - [Analysis Endpoints](#analysis-endpoints)
  - [Utility Endpoints](#utility-endpoints)
- [Data Structure](#-data-structure)
- [Performance Optimizations](#-performance-optimizations)
- [Contributing](#-contributing)
- [License](#-license)

## 📋 Introduction

MedicineDB API Server is a high-performance tool designed to provide comprehensive access to medicine information. It offers a wide range of functionalities from basic medicine lookups to advanced composition analysis and alternative medicine suggestions. This server is built to handle large datasets efficiently while providing accurate and relevant results.

## ✨ Features

- **Advanced Search Capabilities**
  - Exact and fuzzy name matching for medicines
  - Composition/ingredient-based search
  - Multi-criteria filtering with pagination
  - Manufacturer and price range filtering

- **Analysis Tools**
  - Composition string parser and analyzer
  - Statistical analysis of the database
  - Ingredient categorization

- **Medical Decision Support**
  - Alternative medicine suggestions
  - Price comparison between similar medicines
  - Prescription requirement filtering

- **Performance Optimized**
  - Multiple indexing for fast lookups
  - Efficient similarity calculations
  - Precomputed extracted ingredients

## 🛠️ Tech Stack

<div align="center">
  
| Technology | Purpose |
|------------|---------|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white) | Core programming language |
| ![FastMCP](https://img.shields.io/badge/FastMCP-000000?style=for-the-badge) | Server framework |
| ![JSON](https://img.shields.io/badge/JSON-000000?style=for-the-badge&logo=json&logoColor=white) | Data storage format |

</div>

**Libraries**:
- `difflib`: For fuzzy string matching and medicine name similarity
- `re`: For parsing composition strings and ingredient extraction
- `collections`: For optimized data structures (defaultdict, Counter)
- `math`: For price bucketing and pagination calculations
- `typing`: For type hints
- `dataclasses`: For structured data

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/medicines-db.git
cd medicines-db
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Prepare your medicine database:
```bash
# Ensure your JSON data file is at the correct path
# Default path: /Users/siddharthbajpai/Downloads/MCP_SERVER/medicines.json
# Update DATA_PATH in the code if needed
```

4. Run the server:
```bash
python medicines_server.py
```

## 📘 Usage

The server exposes multiple API endpoints through MCP (Model Context Protocol) architecture. You can interact with the server using any MCP client.

Basic example:

```python
from mcp.client import MCPClient

# Connect to the server
client = MCPClient("medicines-db")

# Search for a medicine
result = client.search_medicines("paracetamol", max_results=5)
print(result)

# Get alternatives to a specific medicine
alternatives = client.suggest_alternatives("Dolo 650")
print(alternatives)
```

## 📚 API Reference

The server provides 15 API endpoints through the MCP framework:

### Search Endpoints

#### 1. `get_medicine_by_name`
```
GET /get_medicine_by_name
```
Retrieve a medicine record by its exact Name, with optional cheaper alternatives.

**Parameters:**
- `name` (string, required): The exact Name field of the medicine
- `include_alternatives` (boolean, optional, default=true): Whether to include cheaper alternatives in results

**Response:**
```json
{
  "medicine": {
    "Name": "Dolo 650",
    "Manufacturer": "Micro Labs Ltd",
    "Composition": "Paracetamol (650mg)",
    "MRP": "30.29",
    "Prescription": "No",
    "Price_INR": "₹30.29",
    "Price_Category": "Low",
    "Active_Ingredients": ["Paracetamol"],
    "Ingredient_Count": 1,
    "Is_Combination": false,
    "Requires_Prescription": false,
    "Prescription_Type": "Over-the-Counter"
  },
  "cheaper_alternatives": [
    {
      "medicine": {...},
      "price_savings": "₹10.30",
      "savings_percentage": "34.0%",
      "similarity_score": "1.00"
    }
  ]
}
```

#### 2. `search_medicines`
```
GET /search_medicines
```
Full-text search across all medicine fields.

**Parameters:**
- `query` (string, required): Substring to search (case-insensitive)
- `max_results` (integer, optional, default=10): Maximum number of matching records to return

**Response:**
```json
[
  {
    "Name": "Dolo 650",
    "Manufacturer": "Micro Labs Ltd",
    "Composition": "Paracetamol (650mg)",
    "MRP": "30.29",
    "Price_INR": "₹30.29",
    ...
  },
  ...
]
```

#### 3. `fuzzy_search_by_name`
```
GET /fuzzy_search_by_name
```
Search for medicines with names similar to the provided partial name using fuzzy matching.

**Parameters:**
- `partial_name` (string, required): A partial or misspelled medicine name to search for
- `similarity_threshold` (number, optional, default=0.6): Minimum similarity score (0.0-1.0) to include in results
- `max_results` (integer, optional, default=10): Maximum number of matching records to return

**Response:**
```json
[
  {
    "similarity_score": "0.92",
    "medicine": {
      "Name": "Dolo 650",
      ...
    }
  },
  ...
]
```

#### 4. `search_by_composition`
```
GET /search_by_composition
```
Search for medicines containing a specific active ingredient.

**Parameters:**
- `ingredient` (string, required): Name of an active ingredient to search for
- `max_results` (integer, optional, default=10): Maximum number of matching records to return

**Response:**
```json
[
  {
    "Name": "Dolo 650",
    "Composition": "Paracetamol (650mg)",
    ...
  },
  ...
]
```

### Filter Endpoints

#### 5. `filter_by_price_range`
```
GET /filter_by_price_range
```
Filter medicines by price range.

**Parameters:**
- `min_price` (number, optional, default=0): Minimum price in INR
- `max_price` (number, optional, default=null): Maximum price in INR
- `max_results` (integer, optional, default=20): Maximum number of matching records to return

**Response:**
```json
[
  {
    "Name": "Crocin Pain Relief",
    "MRP": "49.43",
    "Price_INR": "₹49.43",
    ...
  },
  ...
]
```

#### 6. `filter_by_manufacturer`
```
GET /filter_by_manufacturer
```
Filter medicines by manufacturer.

**Parameters:**
- `manufacturer` (string, required): Full or partial manufacturer name
- `max_results` (integer, optional, default=20): Maximum number of matching records to return

**Response:**
```json
[
  {
    "Name": "Dolo 650",
    "Manufacturer": "Micro Labs Ltd",
    ...
  },
  ...
]
```

#### 7. `filter_by_prescription_requirement`
```
GET /filter_by_prescription_requirement
```
Filter medicines by prescription requirement.

**Parameters:**
- `prescription_required` (boolean, required): True for prescription medicines, False for over-the-counter
- `max_results` (integer, optional, default=20): Maximum number of matching records to return

**Response:**
```json
[
  {
    "Name": "Dolo 650",
    "Prescription": "No",
    "Requires_Prescription": false,
    "Prescription_Type": "Over-the-Counter",
    ...
  },
  ...
]
```

#### 8. `paginated_search`
```
GET /paginated_search
```
Advanced search with pagination and multiple filters.

**Parameters:**
- `query` (string, optional, default=""): General search term (searches across all fields)
- `page` (integer, optional, default=1): Page number (starting from 1)
- `page_size` (integer, optional, default=10): Number of results per page
- `manufacturer` (string, optional, default=""): Filter by manufacturer (full or partial)
- `min_price` (number, optional, default=0): Minimum price filter
- `max_price` (number, optional, default=null): Maximum price filter
- `prescription_required` (boolean or null, optional, default=null): Filter by prescription requirement (null for any)
- `ingredient` (string, optional, default=""): Filter by active ingredient

**Response:**
```json
{
  "meta": {
    "total_results": 150,
    "page": 1,
    "page_size": 10,
    "total_pages": 15
  },
  "results": [
    {
      "Name": "Dolo 650",
      ...
    },
    ...
  ]
}
```

### Analysis Endpoints

#### 9. `find_similar_medicines`
```
GET /find_similar_medicines
```
Find medicines with similar composition to the specified medicine.

**Parameters:**
- `medicine_name` (string, required): Name of the reference medicine
- `max_results` (integer, optional, default=5): Maximum number of similar medicines to return

**Response:**
```json
{
  "reference_medicine": {
    "Name": "Dolo 650",
    ...
  },
  "similar_medicines": [
    {
      "similarity_score": "1.00",
      "medicine": {
        "Name": "Crocin Pain Relief",
        ...
      }
    },
    ...
  ]
}
```

#### 10. `analyze_composition`
```
GET /analyze_composition
```
Analyze a medicine composition string to extract and structure the ingredients.

**Parameters:**
- `composition` (string, required): A composition string (e.g. "Ambroxol (30mg/5ml) + Levosalbutamol (1mg/5ml)")

**Response:**
```json
{
  "raw_composition": "Ambroxol (30mg/5ml) + Levosalbutamol (1mg/5ml)",
  "ingredients": [
    {
      "raw_text": "Ambroxol (30mg/5ml)",
      "name": "Ambroxol",
      "dosage": "30mg/5ml",
      "dosage_value": "30",
      "dosage_unit": "mg"
    },
    {
      "raw_text": "Levosalbutamol (1mg/5ml)",
      "name": "Levosalbutamol",
      "dosage": "1mg/5ml",
      "dosage_value": "1",
      "dosage_unit": "mg"
    }
  ],
  "medicines_with_this_composition": [
    {
      "Name": "Ascoril LS Syrup",
      ...
    },
    ...
  ]
}
```

#### 11. `count_medicines_by_composition`
```
GET /count_medicines_by_composition
```
Count and list all medicines with a specific composition or containing specific ingredients.

**Parameters:**
- `composition` (string, required): The composition or ingredient to search for
- `exact_match` (boolean, optional, default=false): If True, only find medicines with the exact composition. If False, find medicines containing this ingredient.

**Response:**
```json
{
  "query": "Paracetamol",
  "exact_match": false,
  "total_medicines_found": 500,
  "total_manufacturers": 25,
  "price_statistics": {
    "min_price": "₹10.50",
    "max_price": "₹150.75",
    "avg_price": "₹45.30",
    "total_medicines_with_price": 490
  },
  "medicines": [...],
  "by_manufacturer": {
    "Cipla": {
      "count": 50,
      "medicines": [...]
    },
    ...
  }
}
```

#### 12. `categorize_medicines`
```
GET /categorize_medicines
```
Categorize medicines by active ingredients and return the most common categories.

**Parameters:**
- `max_categories` (integer, optional, default=10): Maximum number of categories to return

**Response:**
```json
[
  {
    "category": "Paracetamol",
    "medicine_count": 500,
    "example_medicines": [...]
  },
  {
    "category": "Amoxicillin",
    "medicine_count": 300,
    "example_medicines": [...]
  },
  ...
]
```

### Utility Endpoints

#### 13. `get_medicine_statistics`
```
GET /get_medicine_statistics
```
Get statistical overview of the medicines database.

**Parameters:** None

**Response:**
```json
{
  "total_medicines": 15000,
  "prescription_count": 7500,
  "otc_count": 7000,
  "unknown_prescription_status": 500,
  "manufacturer_counts": {
    "Sun Pharma": 1200,
    "Cipla": 900,
    ...
  },
  "price_distribution": {
    "min_price": "₹1.50",
    "max_price": "₹2500.00",
    "avg_price": "₹125.45",
    "price_ranges": {
      "₹0 - ₹99.99": 5000,
      "₹100 - ₹199.99": 4000,
      ...
    }
  },
  "common_ingredients": {
    "Paracetamol": 500,
    "Amoxicillin": 300,
    ...
  }
}
```

#### 14. `get_all_manufacturers`
```
GET /get_all_manufacturers
```
Get a list of all manufacturers in the database.

**Parameters:** None

**Response:**
```json
[
  {
    "name": "Sun Pharma",
    "medicine_count": 1200
  },
  {
    "name": "Cipla",
    "medicine_count": 900
  },
  ...
]
```

#### 15. `suggest_alternatives`
```
GET /suggest_alternatives
```
Suggest alternative medicines based on composition similarity and price.

**Parameters:**
- `medicine_name` (string, required): Name of the reference medicine
- `max_suggestions` (integer, optional, default=5): Maximum number of alternatives to suggest

**Response:**
```json
{
  "reference_medicine": {
    "Name": "Dolo 650",
    "MRP": "30.29",
    ...
  },
  "alternatives": [
    {
      "medicine": {
        "Name": "Calpol 650",
        "MRP": "26.50",
        ...
      },
      "ingredient_similarity": 1.0,
      "price_difference_percentage": -12.5,
      "price_comparison": "cheaper",
      "absolute_price_difference": 3.79
    },
    ...
  ]
}
```

## 📊 Data Structure

The system expects a JSON array of medicine objects with the following structure:

```json
[
  {
    "Name": "Medicine Name",
    "Manufacturer": "Company Name",
    "Composition": "Ingredient1 (10mg) + Ingredient2 (20mg)",
    "MRP": "123.45",
    "Prescription": "Yes"
  },
  ...
]
```

The system enhances this data with additional computed fields:
- `Price_INR`: Formatted price with currency symbol
- `Price_Category`: Classification into Low/Medium/High/Premium
- `Active_Ingredients`: Extracted list of ingredients
- `Ingredient_Count`: Number of active ingredients
- `Is_Combination`: Whether the medicine contains multiple ingredients
- `Requires_Prescription`: Boolean for prescription requirement
- `Prescription_Type`: Human-readable prescription status

## ⚡ Performance Optimizations

The server implements several optimizations:

1. **Multiple indices** for fast lookups:
   - Name index
   - Manufacturer index
   - Composition index
   - Price index
   - Prescription index

2. **Ingredient extraction** is done once at startup to avoid repeated parsing

3. **Similarity calculations** use efficient algorithms:
   - SequenceMatcher for string similarity
   - Jaccard index for ingredient similarity

4. **Price bucketing** for faster range queries

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please make sure to update tests as appropriate.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

<div align="center">
  <p>Developed by Siddharth Bajpai</p>
  <p>For questions or support, please contact <your-email@example.com></p>
  <p>For medicines data, contact me on <a href="https://www.linkedin.com/in/siddharth-bajpai-2472b1297/">LinkedIn</a></p>
</div>
