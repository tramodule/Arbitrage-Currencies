from curl_cffi import requests
from concurrent.futures import ThreadPoolExecutor
import math
from tabulate import tabulate
from copy import deepcopy


class Currency:
    all_currencies = {
        "AUD": "Australian Dollar",
        "BGN": "Bulgarian Lev",
        "BRL": "Brazilian Real",
        "CAD": "Canadian Dollar",
        "CHF": "Swiss Franc",
        "CNY": "Chinese Renminbi Yuan",
        "CZK": "Czech Koruna",
        "DKK": "Danish Krone",
        "EUR": "Euro",
        "GBP": "British Pound",
        "HKD": "Hong Kong Dollar",
        "HUF": "Hungarian Forint",
        "IDR": "Indonesian Rupiah",
        "ILS": "Israeli New Sheqel",
        "INR": "Indian Rupee",
        "ISK": "Icelandic Króna",
        "JPY": "Japanese Yen",
        "KRW": "South Korean Won",
        "MXN": "Mexican Peso",
        "MYR": "Malaysian Ringgit",
        "NOK": "Norwegian Krone",
        "NZD": "New Zealand Dollar",
        "PHP": "Philippine Peso",
        "PLN": "Polish Złoty",
        "RON": "Romanian Leu",
        "SEK": "Swedish Krona",
        "SGD": "Singapore Dollar",
        "THB": "Thai Baht",
        "TRY": "Turkish Lira",
        "USD": "United States Dollar",
        "ZAR": "South African Rand"
    }

    def __init__(self):
        self.currencies = list(Currency.all_currencies.keys())
        self.num_currencies = len(self.currencies)

        self.rates = [[float('inf')] * self.num_currencies for _ in range(self.num_currencies)]
        self.graph = [[float('inf')] * self.num_currencies for _ in range(self.num_currencies)]
        for i in range(self.num_currencies):
            # Distance from node i to itself is 0 in normal shortest-path terms
            self.graph[i][i] = 0.0

    def __get_live_rate(self, from_currency, to_currency) -> float:
        """Fetch live exchange rate using Frankfurter API."""
        try:
            response = requests.get(
                f"https://api.frankfurter.dev/v1/latest?base={from_currency}&symbols={to_currency}",
                timeout=25
            ).json()
            rate = float(list(response["rates"].values())[0])
            return rate
        except Exception as e:
            print(e)
            return float('inf')

    def __fetch_rate(self, args):
        """Helper method for parallel fetching of exchange rates."""
        i, j, c1, c2 = args
        rate = self.__get_live_rate(c1, c2)
        if rate != float('inf'):
            # Store -log(rate) to detect negative cycles
            self.graph[i][j] = -math.log(rate)
            self.rates[i][j] = rate



    def create_graph(self):
        """Populate the adjacency matrix in parallel."""
        tasks = []
        for i, c1 in enumerate(self.currencies):
            for j, c2 in enumerate(self.currencies):
                if i != j:
                    tasks.append((i, j, c1, c2))

        with ThreadPoolExecutor() as executor:
            executor.map(self.__fetch_rate, tasks)



    def __reconstruct_cycle(self, predecessor, start):
        """
        Once a negative cycle is detected by Bellman–Ford, trace back
        through predecessors to reconstruct the cycle.
        """
        for _ in range(self.num_currencies):
            start = predecessor[start]

        # Now collect the cycle
        cycle = []
        cycle_start = start
        while True:
            cycle.append(start)
            start = predecessor[start]
            if start == cycle_start:
                cycle.append(start)
                break

        cycle.reverse()
        return [self.currencies[idx] for idx in cycle]

    def has_arbitrage(self):
        """
        Bellman-Ford from each currency to detect negative cycles.
        Return the cycle if found; else None.
        """
        profits = []
        edges = []
        for i in range(self.num_currencies):
            for j in range(self.num_currencies):
                if i != j and self.graph[i][j] < float('inf'):
                    edges.append((i, j, self.graph[i][j]))

        for source in range(self.num_currencies):
            dist = [float('inf')] * self.num_currencies
            dist[source] = 0.0
            predecessor = [-1] * self.num_currencies

            # Relax edges (n-1) times
            for _ in range(self.num_currencies - 1):
                for u, v, w in edges:
                    if dist[u] + w < dist[v]:
                        dist[v] = dist[u] + w
                        predecessor[v] = u

            for u, v, w in edges:
                if dist[u] + w < dist[v]:
                    # Negative cycle found, reconstruct
                    profits.append(self.__reconstruct_cycle(predecessor, v))


        return profits

if __name__ == '__main__':
    cur = Currency()
    cur.create_graph()
    cycle = cur.has_arbitrage()
    if cycle:
        print("Arbitrage opportunity detected!")
        max_length = max(list(map(len, cycle)))
        cycle_same_size = list(map(lambda x : x + ([""] * (max_length - len(x))), cycle))

        no_dup_cycle = []
        for items in cycle_same_size:
            if items not in no_dup_cycle:
                no_dup_cycle.append(items)

        new_data = []
        for currencies in no_dup_cycle:
            new_cycle = [currencies[0]]
            for currency in currencies[1:]:
                # TODO: Fix the conversion rate between the currencies
                new_cycle.append((currency, cur.rates[cur.currencies.index(currencies[0])][cur.currencies.index(currency)]))

            new_data.append(new_cycle)


        headers = ["Currency Start"] + ["Col" + str(i) for i in range(1, max_length)]

        # Print a table in pretty format
        print(tabulate(new_data, headers=headers, tablefmt="pretty"))
    else:
        print("No arbitrage opportunities.")
