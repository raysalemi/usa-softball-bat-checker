import csv
import json

with open('bats.json', 'r') as f:
    bats_data = json.load(f)

# Look up by (manufacturer, model)
bats_dict = {}
for bat in bats_data:
    if "model" in bat and "manufacturer" in bat:
        key = (bat['manufacturer'].strip().lower(), bat['model'].strip().lower())
        bats_dict[key] = bat

with open('Bats/CertifiedBats.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    print("Header:", header)
    
    # Process rows
    added = 0
    updated = 0
    for row in reader:
        if len(row) < 4:
            continue
            
        manufacturer = row[1].strip()
        model = row[2].strip()
        name = row[3].strip()
        
        if not manufacturer and not model:
            continue
            
        if len(row) > 4:
            last_update = row[4].strip()
        else:
            last_update = ""
            
        key = (manufacturer.lower(), model.lower())
        
        if key in bats_dict:
            if bats_dict[key].get('status') != "APPROVED" or bats_dict[key].get('last_update') != last_update:
                bats_dict[key]['status'] = "APPROVED"
                bats_dict[key]['last_update'] = last_update
                updated += 1
        else:
            new_bat = {
                "model": model,
                "manufacturer": manufacturer,
                "name": name,
                "status": "APPROVED",
                "last_update": last_update
            }
            bats_data.append(new_bat)
            bats_dict[key] = new_bat
            added += 1

print(f"Added {added} new bats.")
print(f"Updated {updated} existing bats to APPROVED.")

with open('bats.json', 'w') as f:
    json.dump(bats_data, f, indent=4)
