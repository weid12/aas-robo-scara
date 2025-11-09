# opcua_client/opcua_to_json_mapper.py
import datetime
from typing import Any, Dict, List, Optional, Tuple
from asyncua import ua

def _to_builtin(x: Any):
    if x is None:
        return None
    if isinstance(x, (str, int, float, bool)):
        return x
    if isinstance(x, bytes):
        return x.decode(errors="ignore")
    if isinstance(x, (list, tuple)):
        return [_to_builtin(i) for i in x]
    if isinstance(x, dict):
        return {str(k): _to_builtin(v) for k, v in x.items()}
    if isinstance(x, datetime.datetime):
        return x.isoformat()
    if isinstance(x, datetime.date):
        return x.isoformat()
    try:
        if isinstance(x, ua.NodeId):
            return x.to_string()
        if isinstance(x, ua.uatypes.LocalizedText):
            return x.Text
        if isinstance(x, ua.uatypes.QualifiedName):
            return x.Name
        if isinstance(x, ua.uatypes.ExtensionObject):
            return _to_builtin(getattr(x, "Body", None))
        d = getattr(x, "__dict__", None)
        if isinstance(d, dict) and d:
            return {k: _to_builtin(v) for k, v in d.items()}
    except Exception:
        pass
    return str(x)

def _is_nodeid(s: Any) -> bool:
    return isinstance(s, str) and s.startswith("ns=") and ";" in s

async def _get_access_info(node) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    try:
        acl = await node.read_access_level()
    except Exception:
        acl = None
    try:
        uacl = await node.read_user_access_level()
    except Exception:
        uacl = None
    try:
        nc = await node.read_node_class()
        nclass = ua.NodeClass(nc).name
    except Exception:
        nclass = None
    return acl, uacl, nclass

def _has_read(access_level: Optional[int], user_access_level: Optional[int]) -> bool:
    mask = ua.AccessLevelType.CurrentRead
    ok_acl = True if access_level is None else bool(access_level & mask)
    ok_uacl = True if user_access_level is None else bool(user_access_level & mask)
    return ok_acl and ok_uacl

async def _read_value_safe(client, nodeid: str):
    node = client.get_node(nodeid)
    acl, uacl, nclass = await _get_access_info(node)
    meta = {"nodeClass": nclass, "accessLevel": acl, "userAccessLevel": uacl}

    if nclass == "Variable" and _has_read(acl, uacl):
        try:
            val = await node.read_value()
            return _to_builtin(val), "self", meta
        except Exception as e:
            meta["error"] = type(e).__name__

    try:
        for c in await node.get_children():
            try:
                nc = await c.read_node_class()
                if ua.NodeClass(nc).name != "Variable":
                    continue
                c_acl, c_uacl, _ = await _get_access_info(c)
                if not _has_read(c_acl, c_uacl):
                    continue
                try:
                    val = await c.read_value()
                    bn = await c.read_browse_name()
                    return _to_builtin(val), f"child:{bn.Name}", meta
                except Exception:
                    continue
            except Exception:
                continue
    except Exception:
        pass
    return None, "none", meta

def _coerce(value: Any, to_type: Optional[str]) -> Any:
    if to_type is None:
        return value
    try:
        if to_type == "float":
            return float(value)
        if to_type == "int":
            return int(value)
        if to_type == "str":
            return str(value)
        if to_type == "bool":
            return bool(value)
        return value
    except Exception:
        return value

async def _resolve_leaf(client, spec: Any) -> Any:
    if isinstance(spec, dict) and ("manual" in spec or "nodeId" in spec or "policy" in spec or "transform" in spec):
        nodeid = spec.get("nodeId")
        manual = spec.get("manual", None)
        policy = spec.get("policy", "prefer-opcua")
        transform = spec.get("transform")

        if policy == "manual-only":
            return _coerce(manual, transform)

        if policy == "opcua-only":
            if nodeid:
                v, _, _ = await _read_value_safe(client, nodeid)
                return _coerce(v, transform)
            return None

        if policy == "prefer-manual":
            if manual is not None:
                return _coerce(manual, transform)
            if nodeid:
                v, _, _ = await _read_value_safe(client, nodeid)
                return _coerce(v, transform)
            return None

        if nodeid:
            v, _, _ = await _read_value_safe(client, nodeid)
            if v is not None:
                return _coerce(v, transform)
        return _coerce(manual, transform)

    if _is_nodeid(spec):
        v, _, _ = await _read_value_safe(client, spec)
        return v

    return _to_builtin(spec)

async def _walk(client, node: Any) -> Any:
    if isinstance(node, dict):
        out: Dict[str, Any] = {}
        for k, v in node.items():
            out[k] = await _walk(client, v)
        return out
    if isinstance(node, list):
        return [await _walk(client, i) for i in node]
    return await _resolve_leaf(client, node)

async def map_opcua_to_submodels(client, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aceita:
      1 literal simples para valor manual
      2 string NodeId OPC UA, por exemplo ns=1;s=Robot:Controller:System:...
      3 objeto com chaves nodeId, manual, policy, transform
         policy, prefer-opcua padrão, manual-only, opcua-only, prefer-manual
         transform opcional, float, int, str, bool
    """
    return await _walk(client, config)
