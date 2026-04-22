class Amplifier:
    def amplify(self, winners):
        scaled = []

        for winner in winners or []:
            amplified = dict(winner)
            amplified["budget"] = float(winner.get("budget", 0)) * 2
            scaled.append(amplified)

        return scaled
