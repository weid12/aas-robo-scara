import asyncio
import argparse
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

from asyncua import Client


async def _find_scara_root(client: Client, object_name: str = "SCARA_TS2_80"):
    objects = client.nodes.objects
    for n in await objects.get_children():
        try:
            bn = await n.read_browse_name()
            if bn and bn.Name == object_name:
                return n
        except Exception:
            continue
    raise RuntimeError(f"Objeto '{object_name}' não encontrado sob Objects")


async def _try_read_value(node) -> Tuple[bool, Any]:
    try:
        val = await node.read_value()
        return True, val
    except Exception:
        return False, None


async def _read_tree(node, path: List[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for ch in await node.get_children():
        try:
            bn = await ch.read_browse_name()
            name = bn.Name if bn else "Unknown"
        except Exception:
            name = "Unknown"

        is_var, value = await _try_read_value(ch)
        if is_var:
            result[name] = value
        else:
            subtree = await _read_tree(ch, path + [name])
            if subtree:
                result[name] = subtree
    return result


async def run_once(endpoint: str) -> Dict[str, Any]:
    async with Client(url=endpoint) as client:
        root = await _find_scara_root(client)
        data = await _read_tree(root, ["SCARA_TS2_80"])
        return data


async def main():
    parser = argparse.ArgumentParser(
        description="Cliente simples para ler o servidor OPC UA local (server.py)"
    )
    parser.add_argument(
        "--endpoint",
        default="opc.tcp://127.0.0.1:4881/",
        help="Endpoint do servidor OPC UA",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=None,
        help="Se definido, executa em ciclo a cada N segundos",
    )
    args = parser.parse_args()

    if args.interval is None:
        data = await run_once(args.endpoint)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return

    print(f"Executando em ciclo. Intervalo: {args.interval:.2f}s (Ctrl+C para parar)")
    try:
        while True:
            t0 = datetime.utcnow().isoformat(timespec="seconds") + "Z"
            try:
                data = await run_once(args.endpoint)
                print(f"[{t0}] Snapshot:")
                print(json.dumps(data, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"[{t0}] Erro ao ler servidor: {e}")
            await asyncio.sleep(args.interval)
    except KeyboardInterrupt:
        print("Interrompido pelo usuário.")


if __name__ == "__main__":
    asyncio.run(main())
