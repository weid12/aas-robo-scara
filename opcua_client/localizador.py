import asyncio
import json
import csv
import re
from collections import deque
from pathlib import Path

from asyncua import Client, ua
from asyncua.common.node import Node

SERVER_URL = "opc.tcp://192.168.0.120:4880"   # ajuste para seu servidor
OUTPUT_DIR = Path("opcua_nodes")
OUTPUT_DIR.mkdir(exist_ok=True)

INDEX_JSONL = OUTPUT_DIR / "all_nodes.jsonl"
INDEX_CSV = OUTPUT_DIR / "all_nodes.csv"

def to_nodeid_str(n: Node) -> str:
    s = n.nodeid.to_string()
    return s if s.startswith("ns=") else f"ns={n.nodeid.NamespaceIndex};{s}"

async def browse_all(client: Client, max_depth=50, max_nodes=200000):
    root = client.get_root_node()
    objects = client.get_objects_node()
    q = deque([(objects, ["Objects"], 0)])
    visited = set()
    total = 0

    jf = INDEX_JSONL.open("w", encoding="utf-8")
    cf = INDEX_CSV.open("w", encoding="utf-8", newline="")
    writer = csv.writer(cf)
    writer.writerow(["NodeId", "BrowseName", "DisplayName", "NodeClass", "Path"])

    while q and total < max_nodes:
        node, path, depth = q.popleft()
        if node.nodeid in visited:
            continue
        visited.add(node.nodeid)

        try:
            bn = await node.read_browse_name()
            dn = await node.read_display_name()
            nc = await node.read_node_class()
            rec = {
                "NodeId": to_nodeid_str(node),
                "BrowseName": bn.Name,
                "DisplayName": dn.Text,
                "NodeClass": ua.NodeClass(nc).name,
                "Path": "/".join(path+[bn.Name])
            }
            jf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            writer.writerow([rec[k] for k in ["NodeId","BrowseName","DisplayName","NodeClass","Path"]])

            if depth < max_depth:
                try:
                    for c in await node.get_children():
                        q.append((c, path+[bn.Name], depth+1))
                except Exception:
                    pass
            total += 1
        except Exception:
            continue

    jf.close()
    cf.close()
    print(f"Indexação concluída. {total} nós salvos em {INDEX_JSONL} e {INDEX_CSV}")

def load_index() -> list:
    recs = []
    with INDEX_JSONL.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                recs.append(json.loads(line))
            except Exception:
                continue
    return recs

def search(records, query: str, regex=False, max_show=20):
    if regex:
        rx = re.compile(query, re.IGNORECASE)
        hits = [r for r in records if rx.search(json.dumps(r, ensure_ascii=False))]
    else:
        q = query.lower()
        hits = [r for r in records if q in json.dumps(r, ensure_ascii=False).lower()]
    print(f"Encontrados {len(hits)} resultados.")
    for r in hits[:max_show]:
        print(f"{r['NodeId']}\t{r['BrowseName']}\t{r['DisplayName']}\t{r['NodeClass']}\t{r['Path']}")

async def main():
    async with Client(url=SERVER_URL) as client:
        await browse_all(client)

    records = load_index()
    print("Digite palavras para buscar, 'regex <expr>' para regex, 'quit' para sair.")
    while True:
        cmd = input("> ").strip()
        if cmd.lower() == "quit":
            break
        if cmd.startswith("regex "):
            search(records, cmd[6:], regex=True)
        else:
            search(records, cmd)

if __name__ == "__main__":
    asyncio.run(main())