import json
from pprint import pprint

with open("text_files/countries.json") as file:
	countries = json.load(file)

weird = [v for k,v in countries.items() if k != v["id"]]

pprint(weird)

# with open("text_files/countries.json", "w") as file:
# 	json.dump(countries, file, indent=2)
