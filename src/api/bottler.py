from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    """ """
    print(potions_delivered)
    with db.engine.begin() as connection:
        for potion in potions_delivered:
            result = connection.execute(
                sqlalchemy.text(f"UPDATE potion_inventory SET quantity = quantity + :quantity WHERE potion_type = :potion_type"),
                {"quantity": potion.quantity, "potion_type": potion.potion_type},
            )
            result = connection.execute(
                sqlalchemy.text(f"UPDATE global_inventory SET num_red_ml = num_red_ml - :red_ml, num_green_ml = num_green_ml - :green_ml, num_blue_ml = num_blue_ml - :blue_ml, num_dark_ml = num_dark_ml - :dark_ml"),
                {"red_ml": potion.potion_type[0] * potion.quantity, "green_ml": potion.potion_type[1] * potion.quantity,
                "blue_ml": potion.potion_type[2] * potion.quantity, "dark_ml": potion.potion_type[3] * potion.quantity},
            )
    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    sql = """SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml FROM global_inventory"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))

    sql = "SELECT potion_type, quantity FROM potion_inventory"
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text(sql))

    colors = ["red", "green", "blue", "dark"]
    row_global = result.first()
    mls = [getattr(row_global, f"num_{color}_ml") for color in colors]

    wanted_potions = 30
    lst = []
    for potion_type, quantity in potions:
        num = max(wanted_potions - quantity, 0)
        ml_res = [num * ml for ml in potion_type]
        max_potions_made = wanted_potions
        for ml_have, ml_potion in zip(mls, potion_type):
            if ml_potion != 0:
                num_potions = ml_have // ml_potion
                max_potions_made = min(max_potions_made, min(num_potions, num))

        lst.append({
            "potion_type": potion_type,
            "quantity": max_potions_made
        })

    return lst
