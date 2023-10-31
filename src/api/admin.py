from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("DELETE FROM ml_ledger"))
        result = connection.execute(sqlalchemy.text("SELECT amount FROM gold_ledger"))
        gold = 0
        for row in result:
            gold += row.amount

        diff = 100 - gold
        if diff != 0:
            connection.execute(
                    sqlalchemy.text("""INSERT INTO gold_ledger (amount, shop_name, description)
                                    VALUES (:amount, :shop_name, :description)"""),
                    {"amount": diff, "shop_name": "reset", "description": "reset"}
                )

        result = connection.execute(
                sqlalchemy.text("""SELECT amount, potion_id FROM potion_ledger
                                ORDER BY potion_ledger.created_at"""))
        potion_tots = []
        for row in result:
            flag = False
            for item in potion_tots:
                if item['potion_id'] == row.potion_id:
                    flag = True
                    item['amount'] += row.amount

            if flag == False:
                potion_tots.append({
                    "amount": row.amount,
                    "potion_id": row.potion_id,
                })

        for item in potion_tots:
            connection.execute(
                sqlalchemy.text("""INSERT INTO potion_ledger (amount, shop_name, description, potion_id)
                                    VALUES (:amount, :shop_name, :description, :potion_id)"""),
                    {"amount": item['amount'] * -1, "shop_name": "reset", "description": "reset",
                     "potion_id": item['potion_id']}
                )

    return "OK"


@router.get("/shop_info/")
def get_shop_info():
    """ """

    # TODO: Change me!
    return {
        "shop_name": "Potion Shop",
        "shop_owner": "Potion Seller",
    }

