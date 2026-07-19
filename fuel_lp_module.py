import pulp


class FuelDistributionLP:
    """
    ماژول برنامه‌ریزی خطی (LP) برای ارسال بنزین از پالایشگاه‌ها
    به انبارهای نفت استانی از طریق خط لوله و ریل.
    """

    def __init__(self, refineries, depots):
        self.refineries = refineries      # لیست اسم پالایشگاه‌ها
        self.depots = depots              # لیست اسم انبارهای استانی
        self.supply = {}                  # {refinery: ظرفیت عرضه}
        self.demand = {}                  # {depot: تقاضا}
        self.cost = {}                    # {(refinery, depot, mode): هزینه هر واحد}
        self.capacity = {}                # {(refinery, depot, mode): سقف ظرفیت مسیر}
        self.model = None
        self.x = {}
        self.result = None

    def set_supply(self, supply_dict):
        self.supply = supply_dict

    def set_demand(self, demand_dict):
        self.demand = demand_dict

    def set_cost(self, cost_dict):
        # فقط مسیرهایی که اینجا هزینه‌شون تعریف بشه، در مدل مجاز خواهند بود
        self.cost = cost_dict

    def set_capacity(self, capacity_dict):
        self.capacity = capacity_dict

    def build_model(self):
        self.model = pulp.LpProblem("Fuel_Distribution", pulp.LpMinimize)
        routes = list(self.cost.keys())

        # یک متغیر تصمیم پیوسته برای هر مسیر مجاز
        self.x = {
            (i, j, m): pulp.LpVariable(f"x_{i}_{j}_{m}", lowBound=0)
            for (i, j, m) in routes
        }

        # تابع هدف: کمینه‌سازی هزینه کل حمل‌ونقل
        self.model += pulp.lpSum(
            self.cost[(i, j, m)] * self.x[(i, j, m)] for (i, j, m) in routes
        )

        # قید سقف عرضه هر پالایشگاه
        for i in self.refineries:
            self.model += (
                pulp.lpSum(self.x[(a, b, c)] for (a, b, c) in routes if a == i)
                <= self.supply[i],
                f"Supply_{i}",
            )

        # قید تأمین حداقل تقاضای هر انبار
        for j in self.depots:
            self.model += (
                pulp.lpSum(self.x[(a, b, c)] for (a, b, c) in routes if b == j)
                >= self.demand[j],
                f"Demand_{j}",
            )

        # قید سقف ظرفیت هر مسیر (در صورت تعریف)
        for (i, j, m) in routes:
            cap = self.capacity.get((i, j, m))
            if cap is not None:
                self.model += (self.x[(i, j, m)] <= cap, f"Cap_{i}_{j}_{m}")

    def solve(self):
        self.model.solve()
        self.result = {
            "status": pulp.LpStatus[self.model.status],
            "objective": pulp.value(self.model.objective),
            "shipments": {
                k: v.varValue for k, v in self.x.items() if v.varValue and v.varValue > 0
            },
            # ارزش سایه‌ای هر قید = مقدار دوگان آن (برای تحلیل حساسیت)
            "shadow_prices": {name: c.pi for name, c in self.model.constraints.items()},
        }
        return self.result

    def print_results(self):
        print("وضعیت حل:", self.result["status"])
        print("هزینه کل بهینه:", self.result["objective"])
        print("\nمقادیر ارسالی:")
        for (i, j, m), val in self.result["shipments"].items():
            print(f"  {i} -> {j} ({m}): {val}")
        print("\nارزش‌های سایه‌ای:")
        for name, val in self.result["shadow_prices"].items():
            print(f"  {name}: {val}")
