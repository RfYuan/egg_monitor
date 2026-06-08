from typing import Optional, Dict

def calculate_basis(spot_price: float, futures_price: float) -> float:
    return spot_price - futures_price
