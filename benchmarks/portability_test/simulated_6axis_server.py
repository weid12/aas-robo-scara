# ==================================================================================================
#   Servidor OPC UA Simulado — Robô 6 Eixos (Segundo Ativo)
#
#   Simula um robô articulado de 6 graus de liberdade (tipo KUKA/ABB/Fanuc):
#   - 6 juntas rotativas (J1..J6)
#   - Temperaturas dos motores (6 eixos)
#   - Torque por eixo
#   - Status operacional, modo, velocidade
#   - Contador de ciclos
#   - Segurança (e-stop, zonas)
#
#   Endpoint: opc.tcp://0.0.0.0:4882/Robot6Axis
#   Namespace: http://example.com/robot6axis/simulated
#
#   Uso:
#       python benchmarks/portability_test/simulated_6axis_server.py
# ==================================================================================================

import asyncio
import math
import random
import logging
from datetime import datetime, timezone

from asyncua import Server, ua

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("robot6axis_server")


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4882/Robot6Axis")
    server.set_server_name("Simulated 6-Axis Robot")

    uri = "http://example.com/robot6axis/simulated"
    idx = await server.register_namespace(uri)

    objects = server.get_objects_node()
    robot = await objects.add_object(idx, "Robot_6Axis")

    # ── Identification ───────────────────────────────────────
    ident = await robot.add_object(idx, "Identification")
    await ident.add_variable(idx, "Model", "KR-210 R2700-2")
    await ident.add_variable(idx, "Manufacturer", "SimRobot AG")
    await ident.add_variable(idx, "SerialNumber", "6AX-2024-007")
    await ident.add_variable(idx, "FirmwareVersion", "KSS 8.6.12")
    await ident.add_variable(idx, "DOF", "6")

    # ── Operational Data ─────────────────────────────────────
    operational = await robot.add_object(idx, "OperationalData")

    # Posições das 6 juntas (variáveis individuais)
    joint_nodes = []
    for i in range(1, 7):
        node = await operational.add_variable(idx, f"Joint{i}_deg", 0.0, varianttype=ua.VariantType.Double)
        joint_nodes.append(node)

    # Posição cartesiana TCP (Tool Center Point)
    tcp_x = await operational.add_variable(idx, "TCP_X_mm", 0.0, varianttype=ua.VariantType.Double)
    tcp_y = await operational.add_variable(idx, "TCP_Y_mm", 0.0, varianttype=ua.VariantType.Double)
    tcp_z = await operational.add_variable(idx, "TCP_Z_mm", 0.0, varianttype=ua.VariantType.Double)

    # Velocidade e torque
    velocity_pct = await operational.add_variable(idx, "VelocityOverride_pct", 100.0, varianttype=ua.VariantType.Double)
    # Torques por eixo
    torque_nodes = []
    for i in range(1, 7):
        node = await operational.add_variable(idx, f"Torque{i}_Nm", 0.0, varianttype=ua.VariantType.Double)
        torque_nodes.append(node)

    # Status
    status_node = await operational.add_variable(idx, "RobotStatus", "idle")
    mode_node = await operational.add_variable(idx, "WorkingMode", "T1")
    program_node = await operational.add_variable(idx, "ActiveProgram", "none")
    cycle_time_node = await operational.add_variable(idx, "CycleTime_s", 0.0, varianttype=ua.VariantType.Double)

    # ── Temperature Data (6 motores) ─────────────────────────
    temp = await robot.add_object(idx, "TemperatureData")
    motor_temps = []
    for i in range(1, 7):
        node = await temp.add_variable(idx, f"Motor{i}_temp_C", 25.0, varianttype=ua.VariantType.Double)
        motor_temps.append(node)
    controller_temp = await temp.add_variable(idx, "Controller_temp_C", 30.0, varianttype=ua.VariantType.Double)

    # ── Counter Data ─────────────────────────────────────────
    counters = await robot.add_object(idx, "CounterData")
    operation_counter = await counters.add_variable(idx, "OperationCounter", 0.0, varianttype=ua.VariantType.Double)
    total_distance = await counters.add_variable(idx, "TotalDistance_m", 0.0, varianttype=ua.VariantType.Double)

    # ── Safety ───────────────────────────────────────────────
    safety = await robot.add_object(idx, "Safety")
    estop_node = await safety.add_variable(idx, "EmergencyStop", False, varianttype=ua.VariantType.Boolean)
    safety_status = await safety.add_variable(idx, "SafetyStatus", "normal")
    zone1 = await safety.add_variable(idx, "Zone1_active", False, varianttype=ua.VariantType.Boolean)
    zone2 = await safety.add_variable(idx, "Zone2_active", False, varianttype=ua.VariantType.Boolean)

    # ── Power Data ───────────────────────────────────────────
    power = await robot.add_object(idx, "PowerData")
    power_w = await power.add_variable(idx, "PowerConsumption_W", 0.0, varianttype=ua.VariantType.Double)
    power_on_time = await power.add_variable(idx, "TotalPowerOnTime_h", 5678.9, varianttype=ua.VariantType.Double)

    await server.start()
    logger.info("Robot 6-Axis Server iniciado em opc.tcp://0.0.0.0:4882/Robot6Axis")
    logger.info("Namespace: %s (idx=%d)", uri, idx)

    # ── Simulação de dados dinâmicos ─────────────────────────
    t = 0.0
    cycles = 0
    cycle_period = 6.0  # 6 segundos por ciclo de pick-and-place
    dist_accum = 0.0

    try:
        while True:
            await asyncio.sleep(0.2)  # 5 Hz
            t += 0.2

            try:
                phase = 2 * math.pi * t / cycle_period
                joints = [
                     45.0 * math.sin(phase),
                    -30.0 + 20.0 * math.sin(phase + 0.5),
                     60.0 + 30.0 * math.sin(phase + 1.0),
                     10.0 * math.sin(phase * 2),
                    -15.0 + 15.0 * math.cos(phase * 2),
                     90.0 * math.sin(phase * 3),
                ]
                for i, jn in enumerate(joint_nodes):
                    await jn.write_value(joints[i])

                await tcp_x.write_value(1200.0 + 400.0 * math.sin(phase))
                await tcp_y.write_value(500.0 * math.cos(phase))
                await tcp_z.write_value(800.0 + 200.0 * math.sin(phase + 1))

                torques = [
                    50.0 + 30.0 * abs(math.cos(phase)) + random.uniform(-2, 2),
                    80.0 + 40.0 * abs(math.cos(phase + 0.5)) + random.uniform(-3, 3),
                    40.0 + 20.0 * abs(math.cos(phase + 1.0)) + random.uniform(-2, 2),
                    15.0 + 10.0 * abs(math.cos(phase * 2)) + random.uniform(-1, 1),
                    12.0 + 8.0 * abs(math.cos(phase * 2)) + random.uniform(-1, 1),
                    5.0 + 3.0 * abs(math.cos(phase * 3)) + random.uniform(-0.5, 0.5),
                ]
                for i, tn in enumerate(torque_nodes):
                    await tn.write_value(torques[i])

                for i, mt in enumerate(motor_temps):
                    base = 30.0 + i * 2.0
                    load_heat = abs(torques[i]) * 0.05
                    await mt.write_value(base + load_heat + random.uniform(-0.3, 0.3))
                await controller_temp.write_value(35.0 + 3.0 * math.sin(t / 120) + random.uniform(-0.2, 0.2))

                new_cycles = int(t / cycle_period)
                if new_cycles > cycles:
                    cycles = new_cycles
                    await operation_counter.write_value(float(cycles))
                    dist_accum += 2.7
                    await total_distance.write_value(dist_accum)

                await status_node.write_value("running")
                await mode_node.write_value("automatic")
                await program_node.write_value("PickPlace_01")
                await cycle_time_node.write_value(cycle_period)
                await velocity_pct.write_value(75.0)

                power_val = 800.0 + sum(abs(tq) for tq in torques) * 2.0 + random.uniform(-20, 20)
                await power_w.write_value(power_val)

            except Exception as e:
                logger.debug("Erro no loop de simulação: %s", e)

    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()
        logger.info("Robot 6-Axis Server finalizado")


if __name__ == "__main__":
    asyncio.run(main())
