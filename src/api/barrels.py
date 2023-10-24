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
            connection.execute(
                sqlalchemy.text("""INSERT INTO gold_ledger (amount, shop_name, description)
                                VALUES (:price, :shop_name, :description)"""),
                {"price": barrel.price * barrel.quantity * -1, "shop_name": "barrels",
                 "description": "Buying: " + str(barrel.sku) + "(" + str(barrel.potion_type) + "), how many: " + str(barrel.quantity)}
            )
            connection.execute(
                sqlalchemy.text("""INSERT INTO ml_ledger (amount, type, description)
                                VALUES (:amount, :type, :description)"""),
                {"amount": barrel.ml_per_barrel * barrel.quantity, "type": barrel.potion_type,
                 "description": "Buying: " + str(barrel.sku) + ", how many: " + str(barrel.quantity) + ", for total: " + str(barrel.price * barrel.quantity)}
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

    sql = "SELECT amount FROM gold_ledger"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))
    gold = sum(row.amount for row in result)

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

    final_ml = []
    for item in potion_tots:
        potion_type = item['potion_type']
        quantity = item['amount']
        num = max(wanted_potions - quantity, 0)
        ml_temp = [(y * num) for y in potion_type]
        final_ml = ml_temp if not final_ml else [x + y for x, y in zip(ml_temp, final_ml)]

    final_ml = [max(x - y, 0) for x, y in zip(final_ml, mls)]
    lst = []
    for ml, color in zip(final_ml, colors):
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
                gold -= (quantity * barrel.price)
                ml -= quantity * ml_per_barrel
    return purchase, gold