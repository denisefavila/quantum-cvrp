
import neal
import numpy as np

from dataclasses import dataclass

from dimod import SampleSet
from dwave_qbsolv import QBSolv

from src.quantumrouting.types import CVRPProblem, CVRPSolution


@dataclass
class QBSolvParams:
    constraint_const: int = 10 ** 7
    """Constraint multiplier for qubo."""
    cost_const: int = 1
    """Cost Function multiplier for qubo."""


def solve(problem: CVRPProblem, params: QBSolvParams) -> CVRPSolution:
    from src.quantumrouting.wrappers.qubo import wrap_qubo_problem
    solver = QBSolv()

    # Get qubo formulation problem
    vrp_qubo = wrap_qubo_problem(problem=problem, params=params)

    # Solve qubo
    response = solver.sample_qubo(vrp_qubo, solver=neal.SimulatedAnnealingSampler())

    return _unwrap_qbsolv_solution(problem=problem, result=response)


def _unwrap_qbsolv_solution(problem: CVRPProblem, result: SampleSet) -> CVRPSolution:

    sample = list(result)[0]

    all_vehicles_results = []
    vehicle_result = []

    vehicle = 0
    step = 0

    # Decoding solution from qubo sample.
    for (s, dest) in sample:
        if sample[(s, dest)] == 1:
            if dest != 0:
                vehicle_result.append(dest)
            step += 1
            if problem.max_deliveries == step:
                # Add depot at begginning
                vehicle_result.insert(0, problem.depot_idx)
                # Add depot at ending
                vehicle_result.append(problem.depot_idx)
                all_vehicles_results.append(vehicle_result)
                step = 0
                vehicle += 1
                vehicle_result = []
                if problem.num_vehicles <= vehicle:
                    break

    # Calculate Cost and total capacity occupied in each vehicle
    cost = 0
    total_demands_size = []
    for vehicle_route in all_vehicles_results:
        demands_size = 0
        if vehicle_route == []:
            continue
        prev = vehicle_route[0]
        for dest in vehicle_route[1:]:
            cost += problem.costs[prev][dest]
            demands_size += problem.demands[dest]
            prev = dest
        total_demands_size.append(demands_size)
        cost += problem.costs[prev][problem.depot_idx]

    return CVRPSolution(
        problem_identifier=problem.problem_identifier,
        routes=np.array(all_vehicles_results),
        cost=cost,
        total_demands=np.array(total_demands_size)
    )