# ==================================================================================================
#   Servidor OPC UA Simulado — CNC Genérica (Segundo Ativo)
#
#   Simula um centro de usinagem CNC com:
#   - 3 eixos lineares (X, Y, Z)
#   - Spindle (rotação e temperatura)
#   - Status operacional
#   - Contador de peças
#
#   Endpoint: opc.tcp://0.0.0.0:4882/CNC
#   Namespace: http://example.com/cnc/simulated
#
#   Uso:
#       python benchmarks/portability_test/simulated_cnc_server.py
# ==================================================================================================

import asyncio
import math
import random
import logging
from datetime import datetime, timezone

from asyncua import Server, ua

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("cnc_server")


async def main():
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4882/CNC")
    server.set_server_name("Simulated CNC Machine")

    uri = "http://example.com/cnc/simulated"
    idx = await server.register_namespace(uri)

    objects = server.get_objects_node()
    cnc = await objects.add_object(idx, "CNC_Machine")

    # ── Identification ───────────────────────────────────────
    ident = await cnc.add_object(idx, "Identification")
    model_node = await ident.add_variable(idx, "Model", "VMC-850 3-Axis")
    manufacturer_node = await ident.add_variable(idx, "Manufacturer", "SimCNC Corp")
    serial_node = await ident.add_variable(idx, "SerialNumber", "CNC-2024-001")
    firmware_node = await ident.add_variable(idx, "FirmwareVersion", "3.5.1")

    # ── Operational Data ─────────────────────────────────────
    operational = await cnc.add_object(idx, "OperationalData")
    axis_x = await operational.add_variable(idx, "AxisX_mm", 0.0, varianttype=ua.VariantType.Double)
    axis_y = await operational.add_variable(idx, "AxisY_mm", 0.0, varianttype=ua.VariantType.Double)
    axis_z = await operational.add_variable(idx, "AxisZ_mm", 0.0, varianttype=ua.VariantType.Double)
    spindle_rpm = await operational.add_variable(idx, "SpindleRPM", 0, varianttype=ua.VariantType.Int32)
    feed_rate = await operational.add_variable(idx, "FeedRate_mmmin", 0.0, varianttype=ua.VariantType.Double)
    status_node = await operational.add_variable(idx, "MachineStatus", "idle")
    mode_node = await operational.add_variable(idx, "OperationMode", "manual")

    # ── Temperature Data ─────────────────────────────────────
    temp = await cnc.add_object(idx, "TemperatureData")
    spindle_temp = await temp.add_variable(idx, "SpindleTemp_C", 25.0, varianttype=ua.VariantType.Double)
    coolant_temp = await temp.add_variable(idx, "CoolantTemp_C", 20.0, varianttype=ua.VariantType.Double)
    ambient_temp = await temp.add_variable(idx, "AmbientTemp_C", 22.0, varianttype=ua.VariantType.Double)

    # ── Counter Data ─────────────────────────────────────────
    counters = await cnc.add_object(idx, "CounterData")
    parts_count = await counters.add_variable(idx, "PartsProduced", 0, varianttype=ua.VariantType.Int32)
    tool_changes = await counters.add_variable(idx, "ToolChanges", 0, varianttype=ua.VariantType.Int32)

    # ── Safety ───────────────────────────────────────────────
    safety = await cnc.add_object(idx, "Safety")
    estop_node = await safety.add_variable(idx, "EmergencyStop", False, varianttype=ua.VariantType.Boolean)
    door_node = await safety.add_variable(idx, "DoorClosed", True, varianttype=ua.VariantType.Boolean)

    # ── Power Data ───────────────────────────────────────────
    power = await cnc.add_object(idx, "PowerData")
    power_kw = await power.add_variable(idx, "PowerConsumption_kW", 0.0, varianttype=ua.VariantType.Double)
    runtime_h = await power.add_variable(idx, "TotalRuntime_h", 1234.5, varianttype=ua.VariantType.Double)

    await server.start()
    logger.info("CNC Server iniciado em opc.tcp://0.0.0.0:4882/CNC")
    logger.info("Namespace: %s (idx=%d)", uri, idx)

    # ── Simulação de dados dinâmicos ─────────────────────────
    t = 0
    parts = 0
    tools = 0
    cycle_time = 8.0  # segundos por peça

    try:
        while True:
            await asyncio.sleep(0.2)  # 5 Hz — mesmo que o robô SCARA
            t += 0.2

            # Simula movimento dos eixos (trajetória circular no plano XY + Z pulsante)
            x = 150.0 + 100.0 * math.sin(2 * math.pi * t / cycle_time)
            y = 150.0 + 100.0 * math.cos(2 * math.pi * t / cycle_time)
            z = -50.0 + 10.0 * math.sin(2 * math.pi * t / (cycle_time / 2))

            await axis_x.write_value(round(x, 3))
            await axis_y.write_value(round(y, 3))
            await axis_z.write_value(round(z, 3))

            # Spindle
            rpm = 8000 + int(500 * math.sin(t / 3))
            await spindle_rpm.write_value(rpm)
            await feed_rate.write_value(round(2000.0 + 200.0 * math.sin(t / 5), 1))

            # Temperaturas (drift lento)
            await spindle_temp.write_value(round(35.0 + 5.0 * math.sin(t / 60) + random.uniform(-0.2, 0.2), 1))
            await coolant_temp.write_value(round(22.0 + 2.0 * math.sin(t / 120) + random.uniform(-0.1, 0.1), 1))
            await ambient_temp.write_value(round(23.0 + random.uniform(-0.3, 0.3), 1))

            # Contador de peças (incrementa a cada ciclo)
            if t % cycle_time < 0.2:
                parts += 1
                await parts_count.write_value(parts)
                if parts % 10 == 0:
                    tools += 1
                    await tool_changes.write_value(tools)

            # Status
            await status_node.write_value("running" if rpm > 0 else "idle")
            await mode_node.write_value("auto")

            # Power
            await power_kw.write_value(round(3.5 + 1.5 * (rpm / 10000), 2))

    except asyncio.CancelledError:
        pass
    finally:
        await server.stop()
        logger.info("CNC Server finalizado")


if __name__ == "__main__":
    asyncio.run(main())
