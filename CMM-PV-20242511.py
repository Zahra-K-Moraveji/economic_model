import pandas as pd
import numpy as np
import hub.helpers.constants as cte
from hub.exports.energy_building_exports_factory import EnergyBuildingsExportsFactory
from hub.imports.geometry_factory import GeometryFactory
from hub.imports.results_factory import ResultFactory



inflation_rate = 0.03
discount_rate = 0.05
period = 25
installation_cost = 0
tax_deduct= 0
incentive= 0
capacity =30
degradation_rate = 0.01
year_of_replacement_list= [12]
replacement_ratio = 0.1
maintenance_cost_ratio =0.01
dataframe_path= r'C:\Users\z_keshav\CMM_PV\data\test.csv'
Building_function = "residential"



def calculate_pv_system_metrics(
        dataframe_path, # input from Hub
        Building_function, # input from Hub
        inflation_rate,
        discount_rate,
        period,
        capacity, # input from Hub
        degradation_rate,
        year_of_replacement_list,
        replacement_ratio,
        maintenance_cost_ratio,
        installation_cost=0,
        tax_deduct=0,
        incentive=0,
):
    # Read the data
    dataframe = pd.read_csv(dataframe_path)
    building_hourly_consumption = dataframe['GRID_kWh'] # input from Hub
    PV_hourly_generation = dataframe['PV_roofs_top_E_kWh'] # input from Hub

    # Defining tariff based on building function
    if Building_function == "residential":  # Rate D when the maximum power demand has reached 50 kW or more
        grid_current_tariff = 0.06704  # Residential tariff in $/kWh
    elif Building_function == "commercial":  # Rate G: General rate for small-power customers with demand ≤ 50 kW
        grid_current_tariff = 0.11518  # Commercial tariff in $/kWh

    # Initial Calculations for Year 1
    first_year_generation_PV = PV_hourly_generation.sum()
    first_year_self_consumption = np.minimum(PV_hourly_generation, building_hourly_consumption).sum()
    first_year_grid_purchase = np.maximum(building_hourly_consumption - PV_hourly_generation, 0).sum()
    first_year_PV_export = np.maximum(PV_hourly_generation - building_hourly_consumption, 0).sum()

    # Cost per kW determination
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
    elif 20 < capacity <= 10000:
        cost_per_kW = 1800
    else:
        cost_per_kW = 1449


    # Initial costs
    initial_cost = capacity * cost_per_kW

    # Discounted metrics initialization
    discounted_generation_per_year = {}
    discounted_self_consumption_per_year = {}
    discounted_building_export_per_year = {}
    discounted_grid_purchase_per_year = {}
    discounted_total_generation = 0
    discounted_total_self_consumption = 0
    discounted_total_building_export = 0
    discounted_total_grid_purchase = 0
    discounted_annual_cost = {}
    discounted_total_cost = 0
    discounted_income_per_year = {}
    total_discounted_income = 0
    total_discounted_net_metering_income = 0

    # Replacement costs calculation
    replacement_cost = {
        year: capacity * cost_per_kW * replacement_ratio * ((1 + inflation_rate) ** year) / (
                    (1 + discount_rate) ** year)
        for year in year_of_replacement_list
    }

    # Yearly calculations
    for year in range(1, period + 1):
        # Apply degradation to PV generation for the current year
        PV_hourly_generation_degraded = PV_hourly_generation * ((1 - degradation_rate) ** (year - 1))

        # Hourly self-consumption and export considering degraded generation
        building_hourly_self_consumption = np.minimum(PV_hourly_generation_degraded, building_hourly_consumption)
        building_hourly_export = np.maximum(PV_hourly_generation_degraded - building_hourly_consumption, 0)
        building_hourly_grid_purchase = np.maximum(building_hourly_consumption - PV_hourly_generation_degraded, 0).sum()

        # Annual values
        annual_self_consumption = building_hourly_self_consumption.sum()
        annual_generation = PV_hourly_generation_degraded.sum()
        annual_PV_export = building_hourly_export.sum()
        annual_grid_purchase = building_hourly_grid_purchase.sum()

        # Discounted values
        discounted_generation = annual_generation / ((1 + discount_rate) ** year)
        discounted_self_consumption = annual_self_consumption / ((1 + discount_rate) ** year)
        discounted_building_export = annual_PV_export / ((1 + discount_rate) ** year)
        discounted_grid_purchase = annual_grid_purchase / ((1 + discount_rate) ** year)

        # Add to total discounted values
        discounted_generation_per_year[year] = discounted_generation
        discounted_self_consumption_per_year[year] = discounted_self_consumption
        discounted_building_export_per_year[year] = discounted_building_export
        discounted_grid_purchase_per_year[year] = discounted_grid_purchase

        # Calculate total values in Life Cycle
        discounted_total_generation += discounted_generation
        discounted_total_self_consumption += discounted_self_consumption
        discounted_total_building_export += discounted_building_export
        discounted_total_grid_purchase += discounted_grid_purchase

        # Annual costs
        annual_opex = initial_cost * maintenance_cost_ratio * ((1 + inflation_rate) ** year) / (
                    (1 + discount_rate) ** year)
        annual_cost = (
            initial_cost if year == 1
            else annual_opex + replacement_cost.get(year, 0)
        )
        discounted_annual_cost[year] = annual_cost
        discounted_total_cost += annual_cost

        # Tariff adjustment for income
        inflated_grid_tariff = grid_current_tariff * ((1 + inflation_rate) ** (year - 1))
        discounted_factor = ((1 + discount_rate) ** year) ** -1

        # Income from self-consumption and net metering
        self_consumption_income = discounted_self_consumption * inflated_grid_tariff
        net_metering_income = min(annual_PV_export, first_year_grid_purchase) * inflated_grid_tariff * discounted_factor
        tax_deduction_income = (
                initial_cost * (1 + tax_deduct) * ((1 - tax_deduct) ** (year - 1)) * tax_deduct
        )

        annual_income = self_consumption_income + net_metering_income + tax_deduction_income
        discounted_income_per_year[year] = annual_income
        total_discounted_income += annual_income
        total_discounted_net_metering_income += net_metering_income

    total_discounted_income += incentive

    # LCOE calculations
    if discounted_total_generation == 0:
        raise ValueError("Discounted generation is zero, cannot calculate LCOE.")

    # To compute the LCOE for exported energy accurately,
    # you should isolate the portion of the discounted income that comes only from energy exported to the grid,
    # over the total discounted exported energy
    # Loec of purchasing from grid is same as tariff

    lcoe_pv = discounted_total_cost / discounted_total_generation

    total_transaction = (
            discounted_total_self_consumption +
            discounted_total_building_export +
            discounted_total_grid_purchase
    )

    # lcoe of exported electricity for net metering
    lcoe_export = (
        total_discounted_net_metering_income / discounted_total_building_export if discounted_total_building_export > 0 else 0)

    # lcoe of the whole system compining various transactions
    lcoe_system = (
            (discounted_total_self_consumption / total_transaction) * lcoe_pv +
            (discounted_total_grid_purchase / total_transaction) * grid_current_tariff -
            (discounted_total_building_export / total_transaction) * lcoe_export
    )

    # NPV calculation
    npv = total_discounted_income - discounted_total_cost

    return {
        'LCOE_PV': lcoe_pv,
        'LCOE_system': lcoe_system,
        'NPV': npv,
        'Annual_PV_generation': first_year_generation_PV,
        'Annual_building_self_consumption': first_year_self_consumption,
        'Annual_grid_purchase': first_year_grid_purchase,
        'Annual_PV_export': first_year_PV_export,
        'Discounted_total_cost': discounted_total_cost,
        'Total_discounted_income': total_discounted_income,
        'Discounted_generation_per_year': discounted_generation_per_year,
        'Discounted_self_consumption_per_year': discounted_self_consumption_per_year,
        'Discounted_annual_cost': discounted_annual_cost,
        'Discounted_income_per_year': discounted_income_per_year
    }

#example
