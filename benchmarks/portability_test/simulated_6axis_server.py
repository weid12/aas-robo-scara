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
    await ident.add_variable(idx, "DOF", 6, varianttype=ua.VariantType.Int32)

    # ── Operational Data ─────────────────────────────────────
    operational = await robot.add_object(idx, "OperationalData")

    # Posições das 6 juntas (array de doubles, como o Stäubli faz)
    joint_positions = await operational.add_variable(
        idx, "JointPositions",
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        varianttype=ua.VariantType.Double
    )

    # Posição cartesiana TCP (Tool Center Point)
    tcp_x = await operational.add_variable(idx, "TCP_X_mm", 0.0, varianttype=ua.VariantType.Double)
    tcp_y = await operational.add_variable(idx, "TCP_Y_mm", 0.0, varianttype=ua.VariantType.Double)
    tcp_z = await operational.add_variable(idx, "TCP_Z_mm", 0.0, varianttype=ua.VariantType.Double)

    # Velocidade e torque
    velocity_pct = await operational.add_variable(idx, "VelocityOverride_pct", 100, varianttype=ua.VariantType.Int32)
    joint_torques = await operational.add_variable(
        idx, "JointTorques_Nm",
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        varianttype=ua.VariantType.Double
    )

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
    operation_counter = await counters.add_variable(idx, "OperationCounter", 0, varianttype=ua.VariantType.Int32)
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

            # Simula trajetória de pick-and-place (6 juntas em seno com fases diferentes)
            phase = 2 * math.pi * t / cycle_period
            joints = [
                 45.0 * math.sin(phase),                # J1: base rotation
                -30.0 + 20.0 * math.sin(phase + 0.5),  # J2: shoulder
                 60.0 + 30.0 * math.sin(phase + 1.0),  # J3: elbow
                 10.0 * math.sin(phase * 2),            # J4: wrist 1
                -15.0 + 15.0 * math.cos(phase * 2),    # J5: wrist 2
                 90.0 * math.sin(phase * 3),            # J6: flange
            ]
            await joint_positions.write_value(ua.Variant(joints, ua.VariantType.Double))

            # TCP cartesiano (aproximação simplificada)
            await tcp_x.write_value(round(1200 + 400 * math.sin(phase), 2))
            await tcp_y.write_value(round(500 * math.cos(phase), 2))
            await tcp_z.write_value(round(800 + 200 * math.sin(phase + 1), 2))

            # Torques (proporcional à velocidade angular)
            torques = [
                round(50 + 30 * abs(math.cos(phase)) + random.uniform(-2, 2), 1),
                round(80 + 40 * abs(math.cos(phase + 0.5)) + random.uniform(-3, 3), 1),
                round(40 + 20 * abs(math.cos(phase + 1.0)) + random.uniform(-2, 2), 1),
                round(15 + 10 * abs(math.cos(phase * 2)) + random.uniform(-1, 1), 1),
                round(12 + 8 * abs(math.cos(phase * 2)) + random.uniform(-1, 1), 1),
                round(5 + 3 * abs(math.cos(phase * 3)) + random.uniform(-0.5, 0.5), 1),
            ]
            await joint_torques.write_value(ua.Variant(torques, ua.VariantType.Double))

            # Temperaturas (drift + carga)
            for i, mt in enumerate(motor_temps):
                base = 30.0 + i * 2
                load_heat = abs(torques[i]) * 0.05
                await mt.write_value(round(base + load_heat + random.uniform(-0.3, 0.3), 1))
            await controller_temp.write_value(round(35.0 + 3 * math.sin(t / 120) + random.uniform(-0.2, 0.2), 1))

            # Contador de ciclos (1 ciclo = 1 período completo)
            new_cycles = int(t / cycle_period)
            if new_cycles > cycles:
                cycles = new_cycles
                await operation_counter.write_value(cycles)
                dist_accum += 2.7  # ~2.7m por ciclo (estimativa)
                await total_distance.write_value(round(dist_accum, 1))

            # Status e modo
            await status_node.write_value("running")
            await mode_node.write_value("automatic")
            await program_node.write_value("PickPlace_01")
            await cycle_time_node.write_value(round(cycle_period, 3))

            # Velocidade e power
            await velocity_pct.write_value(75)
            power_val = 800 + sum(abs(tq) for tq in torques) * 2 + random.uniform(-20, 20)
            await power_w.write_value(round(power_val, 0))

    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()
        logger.info("Robot 6-Axis Server finalizado")


if __name__ == "__main__":
    asyncio.run(main())
