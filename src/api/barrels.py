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
            result = connection.execute(
                sqlalchemy.text("UPDATE global_inventory SET num_red_ml = num_red_ml + (:ml * :quantity), gold = gold - (:price * :quantity)"),
                {"ml": barrel.ml_per_barrel, "quantity": barrel.quantity, "price": barrel.price}
            )

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    #may need to check the wholesale_catalog first to make sure that we're actually buying
    #red potions and how much of them etc.
    print(wholesale_catalog)
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory"))

    numBuy = 1 if result.first().num_red_potions < 10 else 0
    return [
        {
            "sku": "SMALL_RED_BARREL",
            "quantity": numBuy,
        }
    ]
