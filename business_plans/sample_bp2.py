from business_plans.bp import actualise, BP

sample_bp = BP("Sample", start=2016, end=2023)
growth_rate = 0.1
sample_bp.bp.line(name="Sales",
                  history=[25.6, 28.1, 31.0],
                  simulation=actualise(percent=growth_rate))
print(sample_bp["Sales"])
