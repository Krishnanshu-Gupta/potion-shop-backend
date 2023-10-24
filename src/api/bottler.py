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
            connection.execute(
                sqlalchemy.text("""INSERT INTO potion_ledger (amount, potion_id, shop_name, description)
                                VALUES (:amount, (SELECT id FROM potion_inventory WHERE potion_type = :potion_type),
                                :shop_name, :description)"""),
                {"amount": potion.quantity, "potion_type": potion.potion_type, "shop_name": "bottler",
                 "description": "Converting: " + str(potion.potion_type)}
            )
            i = 0
            for ml in potion.potion_type:
                lst = [0, 0, 0, 0]
                lst[i] += 1
                i += 1
                if(ml > 0):
                    connection.execute(
                        sqlalchemy.text("""INSERT INTO ml_ledger (amount, type, description)
                                        VALUES (:amount, :type, :description)"""),
                        {"amount": ml * potion.quantity * -1, "type": lst,
                        "description": "Converting: " + str(potion.potion_type) + ", how many: " + str(potion.quantity)}
                    )
    return "OK"

# Gets called 4 times a day
@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """
    sql = "SELECT id, amount, type FROM ml_ledger"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))

    colors = ["red", "green", "blue", "dark"]
    mls = [0, 0, 0, 0]
    for row in result:
        potion_type = row.type
        amount = row.amount
        for i, color in enumerate(colors):
            mls[i] += potion_type[i] * amount


    sql = """SELECT amount, potion_type
            FROM potion_ledger
            JOIN potion_inventory ON potion_ledger.potion_id = potion_inventory.id
            ORDER BY potion_ledger.created_at"""
    with db.engine.begin() as connection:
        potions = connection.execute(sqlalchemy.text(sql))

    potion_tots = []
    for row in potions:
        flag = False
        for item in potion_tots:
            if item['potion_type'] == row.potion_type:
                flag = True
                item['amount'] += row.amount

        if flag == False:
            potion_tots.append({
                "amount": row.amount,
                "potion_type": row.potion_type,
            })

    wanted_potions = 30
    lst = []
    for item in potion_tots:
        potion_type = item['potion_type']
        quantity = item['amount']
        num = max(wanted_potions - quantity, 0)
        max_potions_made = wanted_potions
        for ml_have, ml_potion in zip(mls, potion_type):
            if ml_potion != 0:
                num_potions = ml_have // ml_potion
                max_potions_made = min(max_potions_made, min(num_potions, num))
        if max_potions_made > 0:
            lst.append({
                "potion_type": potion_type,
                "quantity": max_potions_made
            })
            mls = [ml - (potion_type[idx] * max_potions_made) if potion_type[idx] != 0 else ml for idx, ml in enumerate(mls)]
    return lst

