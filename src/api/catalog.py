from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    sql = "SELECT sku, quantity, price, name, potion_type FROM potion_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))

    catalog = []
    for sku, quantity, price, name, potion_type in result:
        if quantity > 0:
            catalog.append({
                "sku": sku,
                "name": name,
                "quantity": quantity,
                "price": price,
                "potion_type": potion_type
            })
    return catalog
