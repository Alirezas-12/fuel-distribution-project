import random


class FuelDistributionGA:
    """
    الگوریتم ژنتیک برای زمان‌بندی توزیع سوخت از انبار به جایگاه‌ها،
    با هدف کمینه‌سازی مجموع دیرکرد (tardiness) تحویل‌ها.
    """

    def __init__(self, stations, num_tankers, tanker_capacity):
        self.stations = stations              # لیست دیکشنری هر جایگاه: q, p, d, r
        self.n = len(stations)
        self.k = num_tankers
        self.capacity = tanker_capacity
        # کروموزوم = جایگشتی از ایندکس جایگاه‌ها + (k-1) ژن جداکننده منفی
        self.gene_pool = list(range(self.n)) + [-(i + 1) for i in range(self.k - 1)]

    def _decode(self, chromosome):
        # کروموزوم را بر اساس ژن‌های جداکننده به k مسیر تانکر می‌شکند
        routes = [[] for _ in range(self.k)]
        tanker = 0
        for gene in chromosome:
            if gene < 0:
                tanker += 1
            else:
                routes[tanker].append(gene)
        return routes

    def fitness(self, chromosome):
        # مجموع دیرکرد همه جایگاه‌ها + جریمه سنگین در صورت عبور از ظرفیت تانکر
        routes = self._decode(chromosome)
        total_tardiness = 0
        penalty = 0
        for route in routes:
            time = 0
            volume = 0
            for idx in route:
                st = self.stations[idx]
                start = max(time, st["r"])
                finish = start + st["p"]
                total_tardiness += max(0, finish - st["d"])
                time = finish
                volume += st["q"]
            if volume > self.capacity:
                penalty += (volume - self.capacity) * 1000
        return total_tardiness + penalty

    def _random_chromosome(self):
        genes = self.gene_pool[:]
        random.shuffle(genes)
        return genes

    def _tournament_select(self, population, fitnesses, k=3):
        contenders = random.sample(range(len(population)), k)
        best = min(contenders, key=lambda i: fitnesses[i])
        return population[best][:]

    def _order_crossover(self, parent1, parent2):
        # Order Crossover (OX): یک تکه از parent1 حفظ می‌شود، بقیه به ترتیب parent2 پر می‌شود
        size = len(parent1)
        a, b = sorted(random.sample(range(size), 2))
        child = [None] * size
        child[a:b] = parent1[a:b]
        fill_values = [g for g in parent2 if g not in child[a:b]]
        pos = 0
        for i in range(size):
            if child[i] is None:
                child[i] = fill_values[pos]
                pos += 1
        return child

    def _swap_mutation(self, chromosome, rate=0.1):
        # با احتمال rate، جای دو ژن تصادفی عوض می‌شود
        chromosome = chromosome[:]
        if random.random() < rate:
            i, j = random.sample(range(len(chromosome)), 2)
            chromosome[i], chromosome[j] = chromosome[j], chromosome[i]
        return chromosome

    def run(self, population_size=40, generations=150, mutation_rate=0.15):
        population = [self._random_chromosome() for _ in range(population_size)]
        best_chromosome, best_fitness = None, float("inf")

        for _ in range(generations):
            fitnesses = [self.fitness(ind) for ind in population]
            gen_best_idx = min(range(len(population)), key=lambda i: fitnesses[i])
            if fitnesses[gen_best_idx] < best_fitness:
                best_fitness = fitnesses[gen_best_idx]
                best_chromosome = population[gen_best_idx][:]

            new_population = [best_chromosome[:]]  # نخبه‌گرایی (elitism)
            while len(new_population) < population_size:
                p1 = self._tournament_select(population, fitnesses)
                p2 = self._tournament_select(population, fitnesses)
                child = self._order_crossover(p1, p2)
                child = self._swap_mutation(child, mutation_rate)
                new_population.append(child)
            population = new_population

        return best_chromosome, best_fitness

    def explain(self, chromosome):
        # چاپ خوانای برنامه نهایی: کدوم تانکر، کدوم جایگاه، چه زمانی
        routes = self._decode(chromosome)
        for t, route in enumerate(routes):
            time = 0
            print(f"تانکر {t + 1}:")
            for idx in route:
                st = self.stations[idx]
                start = max(time, st["r"])
                finish = start + st["p"]
                late = max(0, finish - st["d"])
                print(f"  ایستگاه {idx}: شروع={start}, پایان={finish}, "
                      f"ددلاین={st['d']}, دیرکرد={late}")
                time = finish

    def get_schedule(self, chromosome):
        # نسخه ساختاریافته (لیست دیکشنری) برای استفاده در اپ/گزارش، به‌جای چاپ مستقیم
        routes = self._decode(chromosome)
        schedule = []
        for t, route in enumerate(routes):
            time = 0
            for idx in route:
                st = self.stations[idx]
                start = max(time, st["r"])
                finish = start + st["p"]
                late = max(0, finish - st["d"])
                schedule.append({
                    "tanker": t + 1,
                    "station_index": idx,
                    "start": start,
                    "finish": finish,
                    "deadline": st["d"],
                    "tardiness": late,
                })
                time = finish
        return schedule
