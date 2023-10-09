from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    sql = "SELECT num_red_potions, num_green_potions, num_blue_potions FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))

    first_row = result.first()
    red_data = gen_catalog("red", first_row.num_red_potions)
    blue_data = gen_catalog("blue", first_row.num_blue_potions)
    green_data = gen_catalog("green", first_row.num_green_potions)

    return red_data + blue_data + green_data

def gen_catalog(color, num_potions):
    if num_potions > 0:
        return [
            {
                "sku": f"{color.upper()}_POTION_0",
                "name": f"{color} potion",
                "quantity": num_potions,
                "price": 30, #price
                "potion_type": [100 if c == color else 0 for c in ["red", "green", "blue", "dark"]],
            }
        ]
    else:
        return []
