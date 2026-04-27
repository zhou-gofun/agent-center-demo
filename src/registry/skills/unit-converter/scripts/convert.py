#!/usr/bin/env python3
"""
Unit Converter Script

Supports: temperature, length, weight, currency conversions.
"""

import json
import sys
import os
from typing import Dict, Any, Optional

# Conversion factors
# Length: base unit = meter
LENGTH_TO_METER = {
    "m": 1,
    "km": 1000,
    "cm": 0.01,
    "mm": 0.001,
    "in": 0.0254,
    "inch": 0.0254,
    "ft": 0.3048,
    "feet": 0.3048,
    "yd": 0.9144,
    "yard": 0.9144,
    "mi": 1609.344,
    "mile": 1609.344,
}

# Weight: base unit = kg
WEIGHT_TO_KG = {
    "kg": 1,
    "g": 0.001,
    "mg": 0.000001,
    "lb": 0.453592,
    "lbs": 0.453592,
    "pound": 0.453592,
    "oz": 0.0283495,
    "ounce": 0.0283495,
}

# Currency exchange rates (approximate, for demo)
# In production, this would fetch real-time rates
CURRENCY_RATES = {
    "USD": 1.0,
    "CNY": 7.24,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 151.50,
}


def convert_temperature(value: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """Convert temperature between Celsius, Fahrenheit, Kelvin."""
    from_u = from_unit.lower()
    to_u = to_unit.lower()

    # Convert to Celsius first
    if from_u in ("c", "°c", "celsius"):
        celsius = value
        formula_step1 = f"{value}°C"
    elif from_u in ("f", "°f", "fahrenheit"):
        celsius = (value - 32) * 5 / 9
        formula_step1 = f"({value} - 32) × 5/9"
    elif from_u in ("k", "°k", "kelvin"):
        celsius = value - 273.15
        formula_step1 = f"{value}K - 273.15"
    else:
        return None

    # Convert from Celsius to target
    if to_u in ("c", "°c", "celsius"):
        result = celsius
        result_unit = "°C"
        if from_u == to_u:
            formula = f"{value}{result_unit}"
        else:
            formula = f"°C = {formula_step1} = {round(celsius, 2)}{result_unit}"
    elif to_u in ("f", "°f", "fahrenheit"):
        result = celsius * 9 / 5 + 32
        result_unit = "°F"
        if from_u == to_u:
            formula = f"{value}{result_unit}"
        else:
            formula = f"°F = {formula_step1} × 9/5 + 32 = {round(result, 2)}{result_unit}"
    elif to_u in ("k", "°k", "kelvin"):
        result = celsius + 273.15
        result_unit = "K"
        if from_u == to_u:
            formula = f"{value}{result_unit}"
        else:
            formula = f"K = {formula_step1} + 273.15 = {round(result, 2)}{result_unit}"
    else:
        return None

    return {
        "success": True,
        "input": {"value": value, "from_unit": from_unit, "to_unit": to_unit},
        "output": {"value": round(result, 4), "unit": result_unit},
        "formula": formula
    }


def normalize_unit(unit: str, category: str) -> Optional[str]:
    """Normalize unit string."""
    unit = unit.lower().strip()

    if category == "temperature":
        unit_map = {
            "c": "c", "°c": "c", "celsius": "c",
            "f": "f", "°f": "f", "fahrenheit": "f",
            "k": "k", "°k": "k", "kelvin": "k",
        }
    elif category == "length":
        unit_map = {k: k for k in LENGTH_TO_METER.keys()}
        unit_map.update({"inches": "in", "foot": "ft"})
    elif category == "weight":
        unit_map = {k: k for k in WEIGHT_TO_KG.keys()}
        unit_map.update({"pounds": "lb"})
    elif category == "currency":
        unit_map = {k: k for k in CURRENCY_RATES.keys()}
        unit_map.update({"rmb": "cny", "yuan": "cny", "jpy": "jpy", "usd": "usd"})
    else:
        return None

    return unit_map.get(unit)


def detect_category(from_unit: str, to_unit: str) -> Optional[str]:
    """Auto-detect the conversion category."""
    f = from_unit.lower()
    t = to_unit.lower()

    if f in LENGTH_TO_METER and t in LENGTH_TO_METER:
        return "length"
    elif f in WEIGHT_TO_KG and t in WEIGHT_TO_KG:
        return "weight"
    elif f in CURRENCY_RATES and t in CURRENCY_RATES:
        return "currency"
    elif any(x in f for x in ["c", "f", "k", "°"]) or any(x in t for x in ["c", "f", "k", "°"]):
        return "temperature"
    return None


def convert_length(value: float, from_unit: str, to_unit: str) -> Optional[Dict[str, Any]]:
    """Convert length units."""
    from_u = normalize_unit(from_unit, "length")
    to_u = normalize_unit(to_unit, "length")

    if not from_u or not to_u:
        return None

    # Convert to meters first, then to target
    meters = value * LENGTH_TO_METER[from_u]
    result = meters / LENGTH_TO_METER[to_u]

    formula = f"{value} {from_u} = {meters:.6f} m = {round(result, 6)} {to_u}"

    return {
        "success": True,
        "input": {"value": value, "from_unit": from_unit, "to_unit": to_unit},
        "output": {"value": round(result, 6), "unit": to_u},
        "formula": formula
    }


def convert_weight(value: float, from_unit: str, to_unit: str) -> Optional[Dict[str, Any]]:
    """Convert weight units."""
    from_u = normalize_unit(from_unit, "weight")
    to_u = normalize_unit(to_unit, "weight")

    if not from_u or not to_u:
        return None

    # Convert to kg first, then to target
    kg = value * WEIGHT_TO_KG[from_u]
    result = kg / WEIGHT_TO_KG[to_u]

    formula = f"{value} {from_u} = {kg:.6f} kg = {round(result, 6)} {to_u}"

    return {
        "success": True,
        "input": {"value": value, "from_unit": from_unit, "to_unit": to_unit},
        "output": {"value": round(result, 6), "unit": to_u},
        "formula": formula
    }


def convert_currency(value: float, from_unit: str, to_unit: str) -> Optional[Dict[str, Any]]:
    """Convert currency units."""
    from_u = normalize_unit(from_unit, "currency")
    to_u = normalize_unit(to_unit, "currency")

    if not from_u or not to_u:
        return None

    # Convert to USD first, then to target
    usd = value / CURRENCY_RATES[from_u]
    result = usd * CURRENCY_RATES[to_u]

    formula = f"{value} {from_u} = {usd:.4f} USD × {CURRENCY_RATES[to_u]} = {round(result, 2)} {to_u}"

    return {
        "success": True,
        "input": {"value": value, "from_unit": from_unit, "to_unit": to_unit},
        "output": {"value": round(result, 2), "unit": to_u},
        "formula": formula,
        "note": "Exchange rates are approximate (demo values)"
    }


def convert(value: float, from_unit: str, to_unit: str, category: str = None) -> Dict[str, Any]:
    """
    Main conversion function.

    Args:
        value: Numeric value to convert
        from_unit: Source unit
        to_unit: Target unit
        category: Conversion category (temperature/length/weight/currency)
                 Auto-detected if not provided

    Returns:
        Conversion result dictionary
    """
    if not from_unit or not to_unit:
        return {
            "success": False,
            "error": "Missing from_unit or to_unit"
        }

    # Auto-detect category
    if not category:
        category = detect_category(from_unit, to_unit)

    if not category:
        return {
            "success": False,
            "error": f"Cannot determine conversion type for '{from_unit}' to '{to_unit}'",
            "supported": "temperature (c/f/k), length (m/km/cm/mm/in/ft/yd/mi), weight (kg/g/mg/lb/oz), currency (USD/CNY/EUR/GBP/JPY)"
        }

    # Perform conversion
    if category == "temperature":
        result = convert_temperature(value, from_unit, to_unit)
    elif category == "length":
        result = convert_length(value, from_unit, to_unit)
    elif category == "weight":
        result = convert_weight(value, from_unit, to_unit)
    elif category == "currency":
        result = convert_currency(value, from_unit, to_unit)
    else:
        return {
            "success": False,
            "error": f"Unsupported category: {category}"
        }

    if result is None:
        return {
            "success": False,
            "error": f"Invalid units for {category}: '{from_unit}' or '{to_unit}'"
        }

    return result


def main():
    """CLI entry point."""
    stdin_data = sys.stdin.read().strip()

    if stdin_data:
        try:
            input_data = json.loads(stdin_data)
            if "__entrypoint__" in input_data:
                input_data = input_data["__input__"]
            value = float(input_data.get("value", 0))
            from_unit = input_data.get("from_unit", "")
            to_unit = input_data.get("to_unit", "")
            category = input_data.get("category")
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            print(json.dumps({"success": False, "error": f"Invalid input: {e}"}))
            sys.exit(1)
    else:
        import argparse
        parser = argparse.ArgumentParser(description="Unit conversion tool")
        parser.add_argument("--value", type=float, required=True, help="Value to convert")
        parser.add_argument("--from", dest="from_unit", type=str, required=True, help="Source unit")
        parser.add_argument("--to", dest="to_unit", type=str, required=True, help="Target unit")
        parser.add_argument("--category", type=str, help="Category (temperature/length/weight/currency)")
        args = parser.parse_args()
        value = args.value
        from_unit = args.from_unit
        to_unit = args.to_unit
        category = args.category

    result = convert(value=value, from_unit=from_unit, to_unit=to_unit, category=category)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
