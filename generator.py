import random


class GameData:

    def __init__(self, base_data):
        self.spirits = base_data.get('spirits', dict())
        self.blight_cards = base_data.get('blight-cards', 0)
        self.scenarios = base_data.get('scenarios', dict())
        self.adversaries = base_data.get('adversaries', dict())
        self.expansions = []

    def add_expansion(self, expansion_id, expansion_data):
        self.expansions.append(expansion_id)
        self.spirits.update(expansion_data.get('spirits', dict()))
        self.blight_cards += expansion_data.get('blight-cards', 0)
        self.scenarios.update(expansion_data.get('scenarios', dict()))
        self.adversaries.update(expansion_data.get('adversaries', dict()))

    def has_expansion(self, expansion_id):
        return expansion_id in self.expansions


class GamePreferences:

    def __init__(self, prefs, game_data):

        self.players = prefs.get('players', [None])
        self.balance_spirits = prefs.get('balance-spirits', True)

        self.game_data = GameData(game_data['base'])
        for expansion in prefs.get('expansions', []):
            self.game_data.add_expansion(expansion, game_data[expansion])

        self.thematic_map = prefs.get('thematic-map', False)
        self.use_blight_card = prefs.get('blight-card', True) or self.game_data.has_expansion('branch-and-claw')
        self.difficulty_level = prefs.get('difficulty-level', 2)
        
        self.randomize_scenario = not (prefs.get('scenario') or prefs.get('scenario-disabled', False))
        self.scenario = prefs.get('scenario')

        self.randomize_adversary = not (prefs.get('adversary') or prefs.get('adversary-disabled', False))
        self.adversary = prefs.get('adversary')
        self.adversary_level = prefs.get('adversary-level', None)

    def count_available_blight_cards(self):
        if self.use_blight_card:
            return self.game_data.blight_cards
        return 0

    def thematic_map_difficulty(self):
        if not self.thematic_map:
            return 0
        if self.game_data.has_expansion('branch-and-claw'):
            return 1
        return 3


def generate_invader_deck():
    return [random.sample(range(1, 5 + i), 3 + i) for i in range(3)]


def pick_boards(player_count, use_thematic_map):
    if use_thematic_map:
        return ['NW', 'NE', 'W', 'E'][:player_count]

    return random.sample(['A', 'B', 'C', 'D'], player_count)

def pick_spirit(pref, available_spirits, power_balance):
    if type(pref) == str:
        return pref

    if type(pref) == int:
        choices = [spirit_id for spirit_id in available_spirits
                   if available_spirits[spirit_id]['complexity'] <= pref]

    if type(pref) == type(None):
        choices = list(available_spirits)

    if power_balance:
        for p in power_balance.copy().reverse():
            choices = sorted(choices, key=lambda s: available_spirits[s]['powers'][p])
        return choices[0]

    return random.choice(choices)


class GameConfiguration:
    
    def __init__(self, prefs):
        self.prefs = prefs
        self.spirits = prefs.players.copy()
        self.boards = pick_boards(len(self.spirits), prefs.thematic_map)
        self.blight_card = 'default'
        self.scenario = None
        self.adversary = None
        self.adversary_level = None
        self.invader_deck = generate_invader_deck()

    def pick_blight_card(self):
        n_blight_cards = self.prefs.count_available_blight_cards()
        if n_blight_cards > 0:
            self.blight_card = random.randint(1, n_blight_cards)

    def locked_spirits(self):
        return [s for s in self.spirits if type(s) == str]

    def power_balance(self):
        powers = dict()
        for spirit_id in self.locked_spirits():
            spirit_powers = self.prefs.game_data.spirits[spirit_id]['powers']
            for p, v in spirit_powers.items():
                powers[p] = powers.get(p, 0) + v

        if powers:
            return sorted(powers, key=powers.get)
        return None

    def pick_spirits(self):
        available_spirits = self.prefs.game_data.spirits.copy()
        print(self.spirits)
        for i in range(len(self.spirits)):
            current_balance = self.power_balance() if self.prefs.balance_spirits else None
            spirit = pick_spirit(self.spirits[i], available_spirits, current_balance)
            del available_spirits[spirit]
            self.spirits[i] = spirit

    def pick_adversary(self):
        if not self.prefs.randomize_adversary:
            self.adversary = self.prefs.adversary
            self.adversary_level = self.prefs.adversary_level
            return

        max_adversary_difficulty = self.prefs.difficulty_level - self.difficulty_level()

        all_adversary_handicaps = dict()
        for spirit_id in self.locked_spirits():
            spirit_handicaps = self.prefs.game_data.spirits[spirit_id].get('adversary-handicaps', dict())
            for s, hc in spirit_handicaps.items():
                all_adversary_handicaps[s] = all_adversary_handicaps.get(s, 0) + hc

        effective_difficulties = list()
        for aid, a in self.prefs.game_data.adversaries.items():
            for level in range(len(a['difficulty'])):
                base_difficulty = a['difficulty'][level]
                handicap = all_adversary_handicaps.get(aid, 0)
                effective_difficulties.append((aid, level,  base_difficulty + handicap))

        possible_adversaries = [(a, l) for (a, l, d) in effective_difficulties
                                if d <= max_adversary_difficulty]
        
        if not possible_adversaries:
            self.adversary = None
            self.adversary_level = None
            return

        a, l = random.choice(possible_adversaries)
        self.adversary = a
        self.adversary_level = l

    def pick_scenario(self):
        if not self.prefs.randomize_scenario:
            self.scenario = self.prefs.scenario
            return

        max_scenario_difficulty = self.prefs.difficulty_level - self.difficulty_level()

        all_scenario_handicaps = dict()
        for spirit_id in self.locked_spirits():
            spirit_handicaps = self.prefs.game_data.spirits[spirit_id].get('scenario-handicaps', dict())
            for s, hc in spirit_handicaps.items():
                all_scenario_handicaps[s] = all_scenario_handicaps.get(s, 0) + hc

        effective_difficulties = {sid: s['difficulty'] + all_scenario_handicaps.get(sid, 0)
                                  for sid, s in self.prefs.game_data.scenarios.items()}

        possible_scenarios = [s for s, d in effective_difficulties.items()
                              if d <= max_scenario_difficulty]

        if not possible_scenarios:
            self.scenario = None
            return

        self.scenario = random.choice(possible_scenarios)

    def difficulty_level(self):
        difficulty = 0

        if self.adversary:
            difficulty += self.prefs.game_data.adversaries[self.adversary]['difficulty'][self.adversary_level]

        if self.scenario:
            scenario = self.prefs.game_data.scenarios[self.scenario]
            difficulty += scenario['difficulty']

            if self.adversary:
                difficulty += scenario.get('adversary-handicaps', dict()).get(self.adversary, 0)

        for spirit_id in self.locked_spirits():
            spirit = self.prefs.game_data.spirits[spirit_id]

            if self.adversary:
                difficulty += spirit.get('adversary-handicaps', dict()).get(self.adversary, 0)
            if self.scenario:
                difficulty += spirit.get('scenario-handicaps', dict()).get(self.scenario, 0)

        difficulty += self.prefs.thematic_map_difficulty()

        return difficulty
    
    def dump(self):
        return {
            'spirits': self.spirits,
            'boards': self.boards,
            'invader-deck': self.invader_deck,
            'blight-card': self.blight_card,
            'scenario': self.scenario,
            'adversary': self.adversary,
            'adversary-level': self.adversary_level,
            'thematic-map': self.prefs.thematic_map
        }

def generate_game(prefs):
    game = GameConfiguration(prefs)
    game.pick_blight_card()
    game.pick_spirits()
    game.pick_adversary()
    game.pick_scenario()
    return game
