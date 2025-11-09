from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Dict, List

import aas_core3.types as aas_types
import aas_core3.jsonization as aas_json
import aas_core3.xmlization as aas_xml


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _infer_xs_type_from_values(values: List[Any]) -> str:
    # Prefer explicit double if any float; otherwise integer; fallback to double
    if any(isinstance(v, float) for v in values):
        return "xs:double"
    if all(isinstance(v, int) for v in values):
        return "xs:integer"
    return "xs:double"


def _to_sme_list_from_property(prop_obj: Dict[str, Any]) -> Dict[str, Any]:
    id_short = prop_obj.get("idShort") or "List"
    values = prop_obj.get("value") or []
    # Determine value type for list
    vt = prop_obj.get("valueType")
    if isinstance(vt, str) and vt.startswith("xs:"):
        list_vt = vt
    else:
        list_vt = _infer_xs_type_from_values(values if isinstance(values, list) else [])
    # Base for list element, carry some metadata
    lst: Dict[str, Any] = {
        "modelType": "SubmodelElementList",
        "idShort": id_short,
        "orderRelevant": True,
        "typeValueListElement": "Property",
        "valueTypeListElement": list_vt,
        "value": [],
    }
    for k in ("category", "displayName", "description", "semanticId", "qualifiers", "embeddedDataSpecifications"):
        if k in prop_obj:
            lst[k] = prop_obj[k]
    # Materialize items as Properties
    items: List[Dict[str, Any]] = []
    seq = values if isinstance(values, list) else []
    for i, v in enumerate(seq, start=1):
        items.append({
            "modelType": "Property",
            "idShort": f"{id_short}_{i}",
            "valueType": list_vt,
            "value": str(v) if v is not None else "",
        })
    lst["value"] = items
    return lst


def _normalize_submodel_json(obj: Any) -> Any:
    """
    Walk JSON and:
    - Convert Property with array value into SubmodelElementList of Properties.
    - Ensure Property.value is a string for non-array scalars.
    """
    if isinstance(obj, dict):
        mt = obj.get("modelType")
        if mt == "Property":
            if "value" in obj and isinstance(obj["value"], list):
                # transform into SubmodelElementList
                return _to_sme_list_from_property(obj)
            if "value" in obj and not isinstance(obj["value"], str):
                # scalar -> stringify
                obj["value"] = str(obj["value"]) if obj["value"] is not None else ""
        # Recurse into known collections
        for k, v in list(obj.items()):
            if isinstance(v, (dict, list)):
                obj[k] = _normalize_submodel_json(v)
    elif isinstance(obj, list):
        return [ _normalize_submodel_json(it) for it in obj ]
    return obj


def _load_submodels_from_dir(submodels_dir: Path) -> List[aas_types.Submodel]:
    submodels: List[aas_types.Submodel] = []
    for p in sorted(submodels_dir.glob("*.json")):
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        fixed = _normalize_submodel_json(data)
        # Ensure top-level modelType if missing
        fixed.setdefault("modelType", "Submodel")
        sm = aas_json.submodel_from_jsonable(fixed)
        submodels.append(sm)
    if not submodels:
        raise FileNotFoundError("no submodel JSON files found")
    return submodels


def _make_shell_for_submodels(submodels: List[aas_types.Submodel]) -> aas_types.AssetAdministrationShell:
    # Create a minimal AAS which references all submodels by ID
    refs: List[aas_types.Reference] = []
    for sm in submodels:
        refs.append(
            aas_types.Reference(
                type=aas_types.ReferenceTypes.MODEL_REFERENCE,
                keys=[aas_types.Key(type=aas_types.KeyTypes.SUBMODEL, value=sm.id)],
            )
        )
    asset_info = aas_types.AssetInformation(asset_kind=aas_types.AssetKind.INSTANCE)
    shell = aas_types.AssetAdministrationShell(
        id="urn:aas:generated:Shell:1", id_short="Shell", submodels=refs,
        asset_information=asset_info
    )
    return shell


def build_environment_from_folder(submodels_dir: Path) -> aas_types.Environment:
    submodels = _load_submodels_from_dir(submodels_dir)
    shell = _make_shell_for_submodels(submodels)
    env = aas_types.Environment(
        asset_administration_shells=[shell], submodels=submodels, concept_descriptions=[]
    )
    return env


def write_env_as_xml(env: aas_types.Environment) -> bytes:
    buf = io.StringIO()
    aas_xml.write(env, buf)
    return buf.getvalue().encode("utf-8")


def write_minimal_aasx(env_xml: bytes, out_path: Path) -> Path:
    """
    Package the XML environment into a minimal AASX ZIP:
    - [Content_Types].xml
    - aasx/aas.xml
    - aasx/aasx-origin (points to main part)
    Note: This is a minimal container and should open in common tools.
    """
    import zipfile

    out_path.parent.mkdir(parents=True, exist_ok=True)

    content_types = (
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n"
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">\n"
        "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>\n"
        "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>\n"
        "</Types>\n"
    ).encode("utf-8")

    origin_txt = b"/aasx/aas.xml\n"

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("aasx/aasx-origin", origin_txt)
        zf.writestr("aasx/aas.xml", env_xml)
    return out_path


def export_full_aasx(submodels_dir: Path, out_path: Path) -> Path:
    env = build_environment_from_folder(submodels_dir)
    xml_bytes = write_env_as_xml(env)
    return write_minimal_aasx(xml_bytes, out_path)
