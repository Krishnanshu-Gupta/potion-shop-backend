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
                (1, 0, 0, 0): "red",
                (0, 1, 0, 0): "green",
                (0, 0, 1, 0): "blue",
                (0, 0, 0, 1): "dark",
            }
            color = color_mapping.get(tuple(barrel.potion_type), "other")
            if color != "other":
                result = connection.execute(
                    sqlalchemy.text(f"UPDATE global_inventory SET num_{color}_ml = num_{color}_ml + (:ml * :quantity), gold = gold - (:price * :quantity)"),
                    {"ml": barrel.ml_per_barrel, "quantity": barrel.quantity, "price": barrel.price}
                )

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #current logic: buy potions to have at least 30 of each color (in ml and potions)
    #this means that if nearly all of the potions have been sold, then we can get a deal by buying the larger sized barrels
    wanted_potions = 30
    print(wholesale_catalog)
    sql = "SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, gold FROM global_inventory"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))

    sql = "SELECT potion_type, quantity FROM potion_inventory"
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text(sql))

    colors = ["red", "green", "blue", "dark"]
    row_global = result.first()
    mls = [getattr(row_global, f"num_{color}_ml") for color in colors]
    gold = row_global.gold
    final_ml = []

    for potion_type, quantity in potions:
        num = max(wanted_potions - quantity, 0)
        final_ml = [x + (y * num) for x, y in zip(mls, potion_type)]

    lst = []
    for potion, ml, color in zip(potions, final_ml, colors):
        res, gold_new = barrels_logic(wholesale_catalog, color, ml, gold)
        if res is not []:
            lst.extend(res)
        gold = gold_new

    return lst

def barrels_logic(catalog, color, ml, gold):
    sorted_catalog = sorted(catalog, key = lambda x: x.ml_per_barrel, reverse=True)
    purchase = []
    for barrel in sorted_catalog:
        if barrel.potion_type == [1 if c == color else 0 for c in ["red", "green", "blue", "dark"]]:
            ml_per_barrel = barrel.ml_per_barrel
            quantity_needed = ml // ml_per_barrel
            quantity = min(quantity_needed, barrel.quantity)
            if quantity > 0 and gold >= (quantity * barrel.price):
                purchase.append({
                    "sku": barrel.sku,
                    "quantity": quantity
                })
                gold -= (barrel.quantity * barrel.price)
                ml -= quantity * ml_per_barrel
    return purchase, gold