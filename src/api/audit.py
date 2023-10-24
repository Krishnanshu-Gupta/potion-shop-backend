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
    ml = 0
    gold = 0

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT amount FROM ml_ledger"))
        for row in result:
            ml += row.amount

        result = connection.execute(sqlalchemy.text("SELECT amount FROM gold_ledger"))
        for row in result:
            gold += row.amount

        result = connection.execute(sqlalchemy.text("SELECT amount FROM potion_ledger"))
        for row in result:
            totalPots += row.amount

    return {"number_of_potions": totalPots, "ml_in_barrels": ml, "gold": gold}

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
