import json

BANNED_BATS = [
    ("Bass", "Quake"),
    ("Combat", "VIRSP3 Lady Virus"),
    ("Data Driven Athletics", "314159 PI"),
    ("Easton", "SCN1"),
    ("Easton", "SCN11BH"),
    ("Easton", "SCN1B"),
    ("Easton", "SCN2B"),
    ("Easton", "SCN3"),
    ("Easton", "SCN4B"),
    ("Easton", "SCN5"),
    ("Easton", "SCN5B"),
    ("Easton", "SCN6B"),
    ("Easton", "SCN7"),
    ("Easton", "SCN7B"),
    ("Easton", "SCN8"),
    ("Easton", "SCN8B"),
    ("Easton", "SCN9"),
    ("Easton", "SCX14"),
    ("Easton", "SCX14B"),
    ("Easton", "SCX2 Synergy"),
    ("Easton", "SCX22 Synergy 2"),
    ("Easton", "SCX24B"),
    ("Easton", "SCX3"),
    ("Louisville Slugger", "FP136"),
    ("Louisville Slugger", "FP1368"),
    ("Louisville Slugger", "FP1369"),
    ("Louisville Slugger", "FPC305 Catalyst (-8)"),
    ("Louisville Slugger", "SB304"),
    ("Louisville Slugger", "SB34 Genesis"),
    ("Louisville Slugger", "SB404"),
    ("Louisville Slugger", "SB73V TPS Voltage"),
    ("Miken", "MSF Freak"),
    ("Miken", "MSU Ultra"),
    ("Miken", "MSU2 Ultra II"),
    ("Miken", "MSUM Ultra Maxload"),
    ("Nokona", "Tomahawk"),
    ("Onyx", "Battle Ground - ESBCA242"),
    ("Onyx", "First Born - ES2P21"),
    ("Pure", "SkyBolt - MFE6"),
    ("Schutt", "Red/Silver Schutt Bat"),
    ("Suncoast", "SBFPB-10"),
    ("Worth", "EST9"),
    ("Worth", "QESTFP"),
    ("Worth", "SBWK(Wicked)"),
    ("Worth", "SBWKA"),
    ("Worth", "WWSC Wicked Comp. (SP Only)"),
    ("Worth", "WWSCA"),
    ("Worth", "XEST9X"),
    ("Worth", "XGold"),
    ("Worth", "XPST4"),
    ("Worth", "XRed"),
    ("Worth", "XWICKX Wicked (SP Only)"),
]

def check_banned_bats():
    with open('bats.json', 'r') as f:
        bats_data = json.load(f)

    # create a lookup
    # Because PDF strings combine model and name in arbitrary ways, 
    # let's just check if the strings exist in either model or name
    # or if the manufacturer matches and the model/name are substrings.
    
    missing = []
    
    for mfg, fullname in BANNED_BATS:
        found = False
        for bat in bats_data:
            if "status" not in bat:
                continue
            
            # Check Manufacturer
            if bat.get("manufacturer") == mfg:
                # Check if it's BANNED
                if bat.get("status") == "BANNED":
                    # Simple heuristic: split fullname and see if it maps to model and name
                    # or if the bat model and name are contained in the fullname
                    b_model = bat.get("model", "")
                    b_name = bat.get("name", "")
                    
                    if b_model in fullname and len(b_model) > 1:
                        found = True
                        break
                    if b_name in fullname and len(b_name) > 1:
                        found = True
                        break
                        
        if not found:
            missing.append((mfg, fullname))
            
    print("Missing or not banned:")
    for m in missing:
        print(m)

if __name__ == "__main__":
    check_banned_bats()
