from __future__ import annotations
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import SessionLocal, Location, Item, Placement

def _norm(s: str) -> str:
    return " ".join(s.strip().lower().split())

def resolve_location_path(path_text: str) -> Dict[str, Any]:
    """
    path_text: "garage/placard jaune/haut"
    Crée les segments manquants.
    """
    parts = [p.strip() for p in path_text.replace(">", "/").split("/") if p.strip()]
    if not parts:
        return {"error": "empty_path"}

    db: Session = SessionLocal()
    try:
        parent_id = None
        resolved: List[Dict[str, Any]] = []

        for raw in parts:
            name = raw.strip()
            # chercher sous parent_id
            stmt = select(Location).where(Location.parent_id == parent_id, Location.name == name)
            loc = db.execute(stmt).scalar_one_or_none()
            if loc is None:
                loc = Location(name=name, parent_id=parent_id)
                db.add(loc)
                db.commit()
                db.refresh(loc)
                action = "created"
            else:
                action = "found"

            resolved.append({"id": loc.id, "name": loc.name, "action": action})
            parent_id = loc.id

        return {
            "location_id": parent_id,
            "path": resolved
        }
    finally:
        db.close()

def get_or_create_item(name: str) -> Dict[str, Any]:
    n = name.strip()
    if not n:
        return {"error": "empty_name"}

    db: Session = SessionLocal()
    try:
        stmt = select(Item).where(Item.name == n)
        item = db.execute(stmt).scalar_one_or_none()
        if item is None:
            item = Item(name=n)
            db.add(item)
            db.commit()
            db.refresh(item)
            return {"item_id": item.id, "name": item.name, "action": "created"}
        return {"item_id": item.id, "name": item.name, "action": "found"}
    finally:
        db.close()

def put_item(item_id: int, location_id: int, quantity: int = 1) -> Dict[str, Any]:
    if quantity <= 0:
        quantity = 1

    db: Session = SessionLocal()
    try:
        pl = db.get(Placement, {"item_id": item_id, "location_id": location_id})
        if pl is None:
            pl = Placement(item_id=item_id, location_id=location_id, quantity=quantity)
            db.add(pl)
            action = "created"
        else:
            pl.quantity += quantity
            action = "incremented"

        db.commit()
        return {"status": "ok", "action": action, "item_id": item_id, "location_id": location_id, "quantity_added": quantity}
    finally:
        db.close()
