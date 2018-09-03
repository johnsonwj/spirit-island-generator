
import generator
import yaml
import json

with open('data.yaml') as data_file:
    game_data = yaml.safe_load(data_file)

def handle(request):

    prefs = generator.GamePreferences(request.get_json(), game_data)
    config = generator.generate_game(prefs)

    return json.dumps(config.dump(), indent=2)
