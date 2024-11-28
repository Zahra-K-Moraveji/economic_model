import pandas as pd
import numpy as np


def calculate_economic_metrics(users, user_consumption_shares, user_pv_shares, initial_cost_share_per_user,
                               dataframe_path, capacity, building_function, inflation_rate=0.03, discount_rate=0.05,
                               period=25, degradation_rate=0.01, replacement_years=[10, 20], replacement_ratio=0.1,
                               maintenance_cost_ratio=0.01, tax_deduct=0, incentive=0):
    # Define cost per kW based on capacity
    if capacity <= 2.5:
        cost_per_kW = 4000
    elif 2.5 < capacity <= 5:
        cost_per_kW = 3000
    elif 5 < capacity <= 10:
        cost_per_kW = 2500
    elif 10 < capacity <= 15:
        cost_per_kW = 2300
    elif 15 < capacity <= 20:
        cost_per_kW = 2000
    else:
        cost_per_kW = 1449

    total_initial_cost = capacity * cost_per_kW

    # Tariff definition
    if building_function == "residential":
        grid_current_tariff = 0.06704
    elif building_function == "commercial":
        grid_current_tariff = 0.11518
    else:
        raise ValueError("Invalid building function provided.")

    # Load data
    dataframe = pd.read_csv(dataframe_path)
    building_hourly_consumption = dataframe['GRID_kWh']
    PV_hourly_generation = dataframe['PV_roofs_top_E_kWh']

    # Results container
    results = {}

    for user in users:
        user_results = {}
        discounted_generation_per_year = {}
        discounted_self_consumption_per_year = {}
        discounted_total_cost = 0
        discounted_income_per_year = {}
        total_discounted_income = 0
        total_discounted_net_metering_income = 0

        # Calculate user-specific shares
        initial_cost = total_initial_cost * initial_cost_share_per_user[user]
        replacement_cost = {
            year: total_initial_cost * replacement_ratio * ((1 + inflation_rate) ** year) / (
                        (1 + discount_rate) ** year) * user_pv_shares[user]
            for year in replacement_years
        }

        for year in range(1, period + 1):
            PV_hourly_generation_degraded = PV_hourly_generation * user_pv_shares[user] * (
                        (1 - degradation_rate) ** (year - 1))
            building_hourly_self_consumption = np.minimum(PV_hourly_generation_degraded,
                                                          building_hourly_consumption * user_consumption_shares[user])
            building_hourly_export = np.maximum(
                PV_hourly_generation_degraded - building_hourly_consumption * user_consumption_shares[user], 0)
            building_hourly_grid_purchase = np.maximum(
                building_hourly_consumption * user_consumption_shares[user] - PV_hourly_generation_degraded, 0)

            # Annual metrics
            annual_self_consumption = building_hourly_self_consumption.sum()
            annual_generation = PV_hourly_generation_degraded.sum()
            annual_PV_export = building_hourly_export.sum()
            annual_grid_purchase = building_hourly_grid_purchase.sum()

            # Discounted metrics
            discounted_generation = annual_generation / ((1 + discount_rate) ** year)
            discounted_self_consumption = annual_self_consumption / ((1 + discount_rate) ** year)

            # Add to total discounted values
            discounted_generation_per_year[year] = discounted_generation
            discounted_self_consumption_per_year[year] = discounted_self_consumption

            # Annual costs
            annual_opex = initial_cost * maintenance_cost_ratio * ((1 + inflation_rate) ** year) / (
                        (1 + discount_rate) ** year)
            annual_cost = annual_opex + replacement_cost.get(year, 0) if year > 1 else initial_cost
            discounted_total_cost += annual_cost

            # Income from self-consumption and net metering
            inflated_grid_tariff = grid_current_tariff * ((1 + inflation_rate) ** (year - 1))
            discounted_factor = ((1 + discount_rate) ** year) ** -1
            self_consumption_income = discounted_self_consumption * inflated_grid_tariff
            net_metering_income = min(annual_PV_export, annual_grid_purchase) * inflated_grid_tariff * discounted_factor
            annual_income = self_consumption_income + net_metering_income
            discounted_income_per_year[year] = annual_income
            total_discounted_income += annual_income
            total_discounted_net_metering_income += net_metering_income

        total_discounted_income += incentive
        lcoe_pv = discounted_total_cost / sum(discounted_generation_per_year.values())
        lcoe_export = (
            total_discounted_net_metering_income / sum(discounted_generation_per_year.values())
            if sum(discounted_generation_per_year.values()) > 0 else 0
        )
        npv = total_discounted_income - discounted_total_cost

        # Store user-specific results
        user_results["LCOE_PV"] = lcoe_pv
        user_results["NPV"] = npv
        user_results["Total Discounted Cost"] = discounted_total_cost
        user_results["Total Discounted Income"] = total_discounted_income
        user_results["Discounted Generation Per Year"] = discounted_generation_per_year
        user_results["Discounted Self Consumption Per Year"] = discounted_self_consumption_per_year
        results[user] = user_results

    return results

# use case example
inflation_rate = 0.03
discount_rate = 0.05
period = 25
installation_cost = 0
tax_deduct = 0
incentive = 0
capacity = 30
degradation_rate = 0.01
year_of_replacement_list = [12]
replacement_ratio = 0.1
maintenance_cost_ratio = 0.01
dataframe_path = r'C:\Users\z_keshav\CMM_PV\data\test.csv'
Building_function = "residential"

users = ['user1', 'user2', 'user3', 'user4', 'user5']
user_consumption_shares = {"user1": 0.2, "user2": 0.3, "user3": 0.15, "user4": 0.15, "user5": 0.2}
user_pv_shares = {"user1": 0.25, "user2": 0.2, "user3": 0.15, "user4": 0.2, "user5": 0.2}
# Calculate initial cost per user (equal share for simplicity)
initial_cost_Share_per_user = {"user1": 0.20, "user2": 0.20, "user3": 0.20, "user4": 0.2, "user5": 0.2}

#operating the function
results = calculate_economic_metrics(
    users=users,
    user_consumption_shares=user_consumption_shares,
    user_pv_shares=user_pv_shares,
    initial_cost_share_per_user=initial_cost_Share_per_user,
    dataframe_path=dataframe_path,
    capacity=capacity,
    building_function=Building_function
)

for user, metrics in results.items():
    print(f"--- {user} ---")
    for key, value in metrics.items():
        print(f"{key}: {value}")
    print("\n")