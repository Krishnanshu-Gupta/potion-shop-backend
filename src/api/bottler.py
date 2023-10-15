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
            color_mapping = {
                (100, 0, 0, 0): "red",
                (0, 100, 0, 0): "green",
                (0, 0, 100, 0): "blue",
                (0, 0, 0, 100): "dark",
            }
            color = color_mapping.get(tuple(potion.potion_type), "other")
            if color != "other":
                result = connection.execute(
                    sqlalchemy.text(f"UPDATE global_inventory SET num_{color}_potions = num_{color}_potions + :quantity, num_{color}_ml = num_{color}_ml - (:{color} * :quantity)"),
                    {"quantity": potion.quantity, "red": potion.potion_type[0], "green": potion.potion_type[1], "blue": potion.potion_type[2]}
                )
    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    sql = """SELECT num_red_ml, num_green_ml, num_blue_ml FROM global_inventory"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))

    row = result.first()
    red_data = gen_plan("red", row.num_red_ml)
    blue_data = gen_plan("blue", row.num_blue_ml)
    green_data = gen_plan("green", row.num_green_ml)

    return red_data + green_data + blue_data

def gen_plan(color, ml):
    if ml >= 100:
        return [
            {
                "potion_type": [100 if c == color else 0 for c in ["red", "green", "blue", "dark"]],
                "quantity": ml // 100,
            }
        ]
    else:
        return []
