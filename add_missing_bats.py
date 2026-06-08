import json
import os

BATS_TO_ADD = [
    {
        "model": "WWSCA",
        "manufacturer": "Worth",
        "name": "WWSCA",
        "status": "BANNED"
    },
    {
        "model": "XEST9X",
        "manufacturer": "Worth",
        "name": "XEST9X",
        "status": "BANNED"
    },
    {
        "model": "XGold",
        "manufacturer": "Worth",
        "name": "XGold",
        "status": "BANNED"
    },
    {
        "model": "XPST4",
        "manufacturer": "Worth",
        "name": "XPST4",
        "status": "BANNED"
    },
    {
        "model": "XRed",
        "manufacturer": "Worth",
        "name": "XRed",
        "status": "BANNED"
    },
    {
        "model": "XWICKX",
        "manufacturer": "Worth",
        "name": "Wicked (SP Only)",
        "status": "BANNED"
    }
]

def add_bats():
    with open('bats.json', 'r') as f:
        bats_data = json.load(f)

    # Add them if they don't exist
    for bat_to_add in BATS_TO_ADD:
        found = False
        for bat in bats_data:
            if bat.get('model') == bat_to_add['model'] and bat.get('manufacturer') == bat_to_add['manufacturer']:
                # Update status just in case
                bat['status'] = "BANNED"
                found = True
                break
        if not found:
            # Add to the list (let's insert right after the other BANNED ones, e.g., index 50, or just insert at index 1)
            bats_data.insert(1, bat_to_add)

    with open('bats.json', 'w') as f:
        json.dump(bats_data, f, indent=4)
        
    print("Added missing bats.")

if __name__ == "__main__":
    add_bats()
