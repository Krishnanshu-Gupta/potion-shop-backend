from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/inventory")
def get_inventory():
    """ """
    totalPots = 0
    totalMl = 0
    gold = 0
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml, gold FROM global_inventory")
        )
        res = result.first()
        totalMl = res.num_red_ml + res.num_green_ml + res.num_blue_ml + res.num_dark_ml
        gold = res.gold
        result = connection.execute(
            sqlalchemy.text("SELECT potion_type, quantity FROM potion_inventory")
        )
        for potion_type, quantity in result:
            totalPots += quantity

    return {"number_of_potions": totalPots, "ml_in_barrels": totalMl, "gold": gold}

class Result(BaseModel):
    gold_match: bool
    barrels_match: bool
    potions_match: bool

# Gets called once a day
@router.post("/results")
def post_audit_results(audit_explanation: Result):
    """ """
    print(audit_explanation)

    return "OK"
