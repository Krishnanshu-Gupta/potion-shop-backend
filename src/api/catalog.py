from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    sql = """SELECT amount, sku, potion_type, price, name
            FROM potion_ledger
            JOIN potion_inventory ON potion_ledger.potion_id = potion_inventory.id
            ORDER BY potion_ledger.created_at"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql))

    ledger_tots = []
    for row in result:
        flag = False
        for item in ledger_tots:
            if item['sku'] == row.sku:
                flag = True
                item['quantity'] += row.amount

        if flag == False:
            ledger_tots.append({
                "quantity": row.amount,
                "name": row.name,
                "sku": row.sku,
                "potion_type": row.potion_type,
                "price": row.price
            })

    ledger_tots.sort(key=lambda item: item['quantity'] * item['price'], reverse = True)
    top6 = ledger_tots[:6]
    return [item for item in top6 if item['quantity'] > 0]