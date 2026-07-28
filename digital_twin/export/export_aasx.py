# ------------------------------------------------------------------------------------------------------------------
#   Exportador de arquivos AASX.
#   Gera um pacote AASX válido contendo os submodelos AAS a partir dos arquivos JSON locais.
#
#   Estrutura AASX (OPC Open Packaging Convention):
#   ├── [Content_Types].xml        — tipos MIME de cada extensão e part especial
#   ├── _rels/
#   │   └── .rels                  — relação root → aasx-origin (item inicial do pacote)
#   ├── aasx/
#   │   ├── aasx-origin            — marcador vazio obrigatório
#   │   ├── aas.xml                — ambiente AAS serializado em XML (AAS 3.0)
#   │   └── _rels/
#   │       └── aasx-origin.rels   — relação aasx-origin → aas.xml
# ------------------------------------------------------------------------------------------------------------------

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import aas_core3.types as aas_types
import aas_core3.jsonization as aas_json
import aas_core3.xmlization as aas_xml


# ---------------------------------------------------------------------------
# Helpers de normalização dos JSONs dos submodelos
# ---------------------------------------------------------------------------

def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _infer_xs_type_from_values(values: List[Any]) -> str:
    if any(isinstance(v, float) for v in values):
        return "xs:double"
    if all(isinstance(v, int) for v in values):
        return "xs:integer"
    return "xs:double"


def _to_sme_list_from_property(prop_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Converte uma Property com value=lista em SubmodelElementList de Properties."""
    id_short = prop_obj.get("idShort") or "List"
    values = prop_obj.get("value") or []
    vt = prop_obj.get("valueType")
    if isinstance(vt, str) and vt.startswith("xs:"):
        list_vt = vt
    else:
        list_vt = _infer_xs_type_from_values(values if isinstance(values, list) else [])

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

    seq = values if isinstance(values, list) else []
    items: List[Dict[str, Any]] = []
    for i, v in enumerate(seq, start=1):
        items.append({
            "modelType": "Property",
            "idShort": f"{id_short}_{i}",
            "valueType": list_vt,
            "value": str(v) if v is not None else "",
        })
    lst["value"] = items
    return lst


def _coerce_property_value(prop_obj: Dict[str, Any]) -> None:
    """
    Garante que Property.value seja string compatível com o valueType declarado.
    Casos tratados:
    - value numérico (int/float) → stringify
    - value None → string vazia
    - value string incompatível com tipo numérico (ex: "0.004s" para xs:double) →
      tenta extrair número; se não conseguir, troca valueType para xs:string
    """
    if "value" not in prop_obj:
        return
    val = prop_obj["value"]
    vt = prop_obj.get("valueType", "xs:string")

    # Já é string — verificar compatibilidade com tipos numéricos
    if isinstance(val, str):
        numeric_types = {"xs:double", "xs:float", "xs:decimal", "xs:integer",
                         "xs:int", "xs:long", "xs:short", "xs:byte",
                         "xs:unsignedInt", "xs:unsignedLong"}
        if vt in numeric_types:
            try:
                float(val)  # tenta parse — se falhar, muda tipo para string
            except ValueError:
                # ex: "0.004s" — extrai parte numérica ou converte para xs:string
                import re
                m = re.match(r"^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)", val)
                if m:
                    prop_obj["value"] = m.group(1)
                else:
                    prop_obj["valueType"] = "xs:string"
        return

    # Valor numérico ou booleano — stringify
    if val is None:
        prop_obj["value"] = ""
    else:
        prop_obj["value"] = str(val)


def _normalize_submodel_json(obj: Any) -> Any:
    """
    Percorre o JSON recursivamente e:
    - Converte Property com value=lista em SubmodelElementList.
    - Garante que Property.value seja string compatível com valueType.
    """
    if isinstance(obj, dict):
        mt = obj.get("modelType")
        if mt == "Property":
            if "value" in obj and isinstance(obj["value"], list):
                return _to_sme_list_from_property(obj)
            _coerce_property_value(obj)
        for k, v in list(obj.items()):
            if isinstance(v, (dict, list)):
                obj[k] = _normalize_submodel_json(v)
    elif isinstance(obj, list):
        return [_normalize_submodel_json(it) for it in obj]
    return obj


# ---------------------------------------------------------------------------
# Carregamento e construção do ambiente AAS
# ---------------------------------------------------------------------------

def _load_submodels_from_dir(submodels_dir: Path) -> List[aas_types.Submodel]:
    submodels: List[aas_types.Submodel] = []
    for p in sorted(submodels_dir.glob("*.json")):
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        fixed = _normalize_submodel_json(data)
        fixed.setdefault("modelType", "Submodel")
        sm = aas_json.submodel_from_jsonable(fixed)
        submodels.append(sm)
    if not submodels:
        raise FileNotFoundError(f"Nenhum arquivo JSON de submodelo encontrado em: {submodels_dir}")
    return submodels


def _make_shell_for_submodels(
    submodels: List[aas_types.Submodel],
    shell_id: str = "urn:aas:generated:Shell:ScaraRobot",
    global_asset_id: str = "urn:aas:generated:Asset:ScaraRobot",
) -> aas_types.AssetAdministrationShell:
    refs: List[aas_types.Reference] = [
        aas_types.Reference(
            type=aas_types.ReferenceTypes.MODEL_REFERENCE,
            keys=[aas_types.Key(type=aas_types.KeyTypes.SUBMODEL, value=sm.id)],
        )
        for sm in submodels
    ]
    # globalAssetId é obrigatório na spec AAS 3.0
    asset_info = aas_types.AssetInformation(
        asset_kind=aas_types.AssetKind.INSTANCE,
        global_asset_id=global_asset_id,
    )
    shell = aas_types.AssetAdministrationShell(
        id=shell_id,
        id_short="ScaraRobotShell",
        submodels=refs,
        asset_information=asset_info,
    )
    return shell


def build_environment_from_folder(submodels_dir: Path) -> aas_types.Environment:
    submodels = _load_submodels_from_dir(submodels_dir)
    shell = _make_shell_for_submodels(submodels)
    env = aas_types.Environment(
        asset_administration_shells=[shell],
        submodels=submodels,
        concept_descriptions=[],
    )
    return env


# ---------------------------------------------------------------------------
# Serialização XML
# ---------------------------------------------------------------------------

def write_env_as_xml(env: aas_types.Environment) -> bytes:
    buf = io.StringIO()
    aas_xml.write(env, buf)
    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Empacotamento AASX (OPC Open Packaging Convention)
# ---------------------------------------------------------------------------

def write_minimal_aasx(env_xml: bytes, out_path: Path) -> Path:
    """
    Cria um pacote AASX válido segundo a especificação OPC Open Packaging:

    Arquivos gerados dentro do ZIP:
      [Content_Types].xml          — tipos MIME registrados
      _rels/.rels                  — relação root que aponta para aasx/aasx-origin
      aasx/aasx-origin             — marcador vazio (origin part)
      aasx/_rels/aasx-origin.rels  — relação origin → aas.xml
      aasx/aas.xml                 — ambiente AAS em XML (AAS 3.0)
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # -- [Content_Types].xml --------------------------------------------------
    # Registra extensões padrão + o arquivo aasx-origin (sem extensão = Override)
    content_types = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '  <Default Extension="xml" ContentType="application/xml"/>\n'
        '  <Override PartName="/aasx/aasx-origin"'
        ' ContentType="application/aas"/>\n'
        '</Types>\n'
    ).encode("utf-8")

    # -- _rels/.rels ----------------------------------------------------------
    # Relação root → aasx-origin com tipo AASX
    root_rels = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="r1" Type="http://www.admin-shell.io/aasx/relationships/aasx-origin"'
        ' Target="/aasx/aasx-origin"/>\n'
        '</Relationships>\n'
    ).encode("utf-8")

    # -- aasx/_rels/aasx-origin.rels ------------------------------------------
    # Relação origin → aas.xml com tipo AAS spec
    origin_rels = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '  <Relationship Id="r2" Type="http://www.admin-shell.io/aasx/relationships/aas-spec"'
        ' Target="/aasx/aas.xml"/>\n'
        '</Relationships>\n'
    ).encode("utf-8")

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("aasx/aasx-origin", b"")        # marcador vazio obrigatório
        zf.writestr("aasx/_rels/aasx-origin.rels", origin_rels)
        zf.writestr("aasx/aas.xml", env_xml)

    return out_path


# ---------------------------------------------------------------------------
# Ponto de entrada principal
# ---------------------------------------------------------------------------

def export_full_aasx(submodels_dir: Path, out_path: Path) -> Path:
    """
    Exporta todos os submodelos JSON em *submodels_dir* para um pacote AASX
    completo salvo em *out_path*.

    Returns:
        Caminho do arquivo AASX gerado.
    """
    env = build_environment_from_folder(submodels_dir)
    xml_bytes = write_env_as_xml(env)
    return write_minimal_aasx(xml_bytes, out_path)


# ---------------------------------------------------------------------------
# Execução direta (python export_aasx.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    base = Path(__file__).parent.parent   # digital_twin/
    submodels_dir = base / "submodels"
    out_path = base / "export" / "output.aasx"

    print(f"[export_aasx] Submodels dir : {submodels_dir}")
    print(f"[export_aasx] Output path   : {out_path}")

    try:
        result = export_full_aasx(submodels_dir, out_path)
        print(f"[export_aasx] OK AASX gerado com sucesso: {result}  ({result.stat().st_size:,} bytes)")
    except Exception as exc:
        print(f"[export_aasx] ERRO ao gerar AASX: {exc}", file=sys.stderr)
        sys.exit(1)
