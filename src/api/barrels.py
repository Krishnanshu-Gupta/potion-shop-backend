from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    print(barrels_delivered)
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            color_mapping = {
                (100, 0, 0, 0): "red",
                (0, 100, 0, 0): "green",
                (0, 0, 100, 0): "blue",
            }
            color = color_mapping.get(tuple(barrel.potion_type), "other")
            if color is not "other":
                result = connection.execute(
                    sqlalchemy.text(f"UPDATE global_inventory SET num_{color}_ml = num_{color}_ml + (:ml * :quantity), gold = gold - (:price * :quantity)"),
                    {"ml": barrel.ml_per_barrel, "quantity": barrel.quantity, "price": barrel.price}
                )

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #current logic: buy potions to have at least 15 of each color (in ml and potions)
    print(wholesale_catalog)
    sql = """SELECT num_red_potions, num_green_potions, num_blue_potions
            ,num_red_ml, num_green_ml, num_blue_ml FROM global_inventory"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))

    row = result.first()
    colors = ["red", "green", "blue"]
    potions = [getattr(row, f"num_{color}_potions") for color in colors]
    mls = [getattr(row, f"num_{color}_ml") for color in colors]

    lst = []
    for potion, ml, color in zip(potions, mls, colors):
        maxAmt = 15 * 100
        buy_ml = maxAmt - (potion * 100) - ml
        res = barrels_logic(wholesale_catalog, color, buy_ml)
        if res is not []:
            lst.extend(res)

    return lst

def barrels_logic(catalog, color, ml):
    purchase = []
    for barrel in catalog:
        if barrel.potion_type == [100 if c == color else 0 for c in ["red", "green", "blue", "dark"]]:
            ml_per_barrel = barrel.ml_per_barrel
            quantity_needed = ml // ml_per_barrel
            quantity = min(quantity_needed, barrel.quantity)
            if quantity > 0:
                purchase.append({
                    "sku": barrel.sku,
                    "quantity": quantity
                })
                ml -= quantity * ml_per_barrel
    return purchase