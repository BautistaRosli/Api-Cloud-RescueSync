from fastapi import APIRouter, HTTPException

from app.models import Item, ItemCreate

router = APIRouter()

fake_db: dict[int, Item] = {}
counter = 0


@router.post("/", response_model=Item)
def create_item(item: ItemCreate):
    global counter
    counter += 1
    new_item = Item(id=counter, **item.model_dump())
    fake_db[counter] = new_item
    return new_item


@router.get("/", response_model=list[Item])
def list_items():
    return list(fake_db.values())


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return fake_db[item_id]


@router.delete("/{item_id}")
def delete_item(item_id: int):
    if item_id not in fake_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del fake_db[item_id]
    return {"detail": "Item deleted"}
