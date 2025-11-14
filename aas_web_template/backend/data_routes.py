"""
Rotas de API para acesso aos dados do robô SCARA armazenados no SQLite.

Endpoints disponíveis:
- GET /api/data/paths - Lista todos os caminhos de métricas disponíveis
- GET /api/data/timeseries - Retorna série temporal de uma métrica específica
- GET /api/data/snapshots - Retorna snapshots normalizados de um submodelo
- GET /api/data/stats - Retorna estatísticas agregadas dos dados
- GET /api/data/latest - Retorna os valores mais recentes de todas as métricas
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone

# Caminho do banco de dados (relativo à raiz do repositório)
REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "aas_history.sqlite3"

data_bp = Blueprint("data", __name__, url_prefix="/api/data")


def _db_connect() -> Optional[sqlite3.Connection]:
    """
    Estabelece conexão com o banco de dados SQLite.
    
    Returns:
        Conexão SQLite ou None se o banco não existir
    """
    if not DB_PATH.exists():
        current_app.logger.warning(f"Database not found at {DB_PATH}")
        return None
    
    try:
        con = sqlite3.connect(str(DB_PATH))
        con.row_factory = sqlite3.Row
        return con
    except sqlite3.Error as e:
        current_app.logger.error(f"Database connection error: {e}")
        return None


@data_bp.get("/paths")
def get_paths():
    """
    Lista todos os caminhos de métricas disponíveis no banco de dados.
    
    Returns:
        JSON: {
            "paths": [
                {"submodel": "OperationalData", "path": "OperationalData.JointPosition1"},
                ...
            ]
        }
    """
    con = _db_connect()
    if con is None:
        return jsonify({"paths": [], "error": "Database not available"}), 503
    
    try:
        cur = con.cursor()
        cur.execute("""
            SELECT DISTINCT submodel_name, element_path 
            FROM timeseries 
            ORDER BY submodel_name, element_path 
            LIMIT 1000
        """)
        
        paths = [
            {"submodel": row["submodel_name"], "path": row["element_path"]}
            for row in cur.fetchall()
        ]
        
        return jsonify({"paths": paths, "count": len(paths)})
    
    except sqlite3.Error as e:
        current_app.logger.error(f"Error fetching paths: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    finally:
        con.close()


@data_bp.get("/timeseries")
def get_timeseries():
    """
    Retorna série temporal de uma métrica específica.
    
    Query params:
        - submodel: Nome do submodelo (ex: "OperationalData")
        - path: Caminho do elemento (ex: "OperationalData.JointPosition1")
        - limit: Número máximo de pontos (padrão: 200, máx: 2000)
    
    Returns:
        JSON: {
            "rows": [
                {"t": "2024-01-01T12:00:00Z", "v": 123.45},
                ...
            ],
            "submodel": "OperationalData",
            "path": "OperationalData.JointPosition1",
            "count": 200
        }
    """
    submodel = request.args.get("submodel", "").strip()
    path = request.args.get("path", "").strip()
    
    try:
        limit = min(int(request.args.get("limit", "200")), 2000)
    except ValueError:
        limit = 200

    start = request.args.get("start", "").strip()
    end = request.args.get("end", "").strip()

    if not submodel or not path:
        return jsonify({"error": "Parameters 'submodel' and 'path' are required"}), 400
    
    con = _db_connect()
    if con is None:
        return jsonify({"rows": [], "error": "Database not available"}), 503
    
    try:
        cur = con.cursor()
        base_sql = (
            "SELECT value, created_at FROM timeseries "
            "WHERE submodel_name = ? AND element_path = ?"
        )
        params = [submodel, path]

        if start:
            base_sql += " AND created_at >= ?"
            params.append(start)
        if end:
            base_sql += " AND created_at <= ?"
            params.append(end)

        base_sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cur.execute(base_sql, tuple(params))
        
        rows = cur.fetchall()
        # Reverter para ordem cronológica (mais antigo primeiro)
        rows = list(reversed(rows))
        
        data = [
            {"t": row["created_at"], "v": row["value"]}
            for row in rows
        ]
        
        return jsonify({
            "rows": data,
            "submodel": submodel,
            "path": path,
            "count": len(data)
        })
    
    except sqlite3.Error as e:
        current_app.logger.error(f"Error fetching timeseries: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    finally:
        con.close()


@data_bp.get("/snapshots")
def get_snapshots():
    """
    Retorna snapshots normalizados de um submodelo.
    
    Query params:
        - submodel: Nome do submodelo (ex: "OperationalData")
        - limit: Número máximo de timestamps (padrão: 10)
    
    Returns:
        JSON: {
            "snapshots": [
                {
                    "created_at": "2024-01-01T12:00:00Z",
                    "values": [
                        {"idshort": "OperationalData.Status", "value": "Running"},
                        ...
                    ]
                },
                ...
            ]
        }
    """
    submodel = request.args.get("submodel", "").strip()
    
    try:
        limit = min(int(request.args.get("limit", "10")), 100)
    except ValueError:
        limit = 10
    
    if not submodel:
        return jsonify({"error": "Parameter 'submodel' is required"}), 400
    
    con = _db_connect()
    if con is None:
        return jsonify({"snapshots": [], "error": "Database not available"}), 503
    
    try:
        cur = con.cursor()
        
        # Buscar timestamps únicos mais recentes
        cur.execute("""
            SELECT DISTINCT created_at
            FROM submodel_snapshots
            WHERE submodel_name = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (submodel, limit))
        
        timestamps = [row["created_at"] for row in cur.fetchall()]
        
        snapshots = []
        for ts in timestamps:
            cur.execute("""
                SELECT idshort, value_text, value_num, value_bool
                FROM submodel_snapshots
                WHERE submodel_name = ? AND created_at = ?
                ORDER BY idshort
            """, (submodel, ts))
            
            values = []
            for row in cur.fetchall():
                # Determinar qual coluna tem o valor
                if row["value_bool"] is not None:
                    value = bool(row["value_bool"])
                elif row["value_num"] is not None:
                    value = row["value_num"]
                else:
                    value = row["value_text"]
                
                values.append({
                    "idshort": row["idshort"],
                    "value": value
                })
            
            snapshots.append({
                "created_at": ts,
                "values": values
            })
        
        return jsonify({
            "snapshots": snapshots,
            "submodel": submodel,
            "count": len(snapshots)
        })
    
    except sqlite3.Error as e:
        current_app.logger.error(f"Error fetching snapshots: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    finally:
        con.close()


@data_bp.get("/stats")
def get_stats():
    """
    Retorna estatísticas agregadas dos dados.
    
    Returns:
        JSON: {
            "total_records": 12345,
            "submodels": ["OperationalData", "RuntimeDiagnostics", ...],
            "date_range": {
                "first": "2024-01-01T00:00:00Z",
                "last": "2024-01-02T12:00:00Z"
            },
            "metrics_count": 42
        }
    """
    con = _db_connect()
    if con is None:
        return jsonify({"error": "Database not available"}), 503
    
    try:
        cur = con.cursor()
        
        # Total de registros
        cur.execute("SELECT COUNT(*) as count FROM timeseries")
        total_records = cur.fetchone()["count"]
        
        # Submodelos únicos
        cur.execute("SELECT DISTINCT submodel_name FROM timeseries ORDER BY submodel_name")
        submodels = [row["submodel_name"] for row in cur.fetchall()]
        
        # Range de datas
        cur.execute("""
            SELECT 
                MIN(created_at) as first_date,
                MAX(created_at) as last_date
            FROM timeseries
        """)
        date_row = cur.fetchone()
        
        # Contagem de métricas únicas
        cur.execute("SELECT COUNT(DISTINCT element_path) as count FROM timeseries")
        metrics_count = cur.fetchone()["count"]
        
        # Tamanho do arquivo do banco de dados (bytes)
        try:
            db_size_bytes = DB_PATH.stat().st_size if DB_PATH.exists() else None
        except Exception as _e:
            db_size_bytes = None

        # Ultima modificacao do arquivo (ISO 8601 UTC)
        try:
            if DB_PATH.exists():
                mtime = DB_PATH.stat().st_mtime
                db_mtime = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            else:
                db_mtime = None
        except Exception as _e:
            db_mtime = None

        return jsonify({
            "total_records": total_records,
            "submodels": submodels,
            "date_range": {
                "first": date_row["first_date"],
                "last": date_row["last_date"]
            } if date_row["first_date"] else None,
            "metrics_count": metrics_count,
            "db_size_bytes": db_size_bytes,
            "db_mtime": db_mtime,
            "db_path": str(DB_PATH)
        })
    
    except sqlite3.Error as e:
        current_app.logger.error(f"Error fetching stats: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    finally:
        con.close()


@data_bp.get("/latest")
def get_latest():
    """
    Retorna os valores mais recentes de todas as métricas.
    
    Returns:
        JSON: {
            "metrics": [
                {
                    "submodel": "OperationalData",
                    "path": "OperationalData.JointPosition1",
                    "value": 123.45,
                    "timestamp": "2024-01-01T12:00:00Z"
                },
                ...
            ]
        }
    """
    con = _db_connect()
    if con is None:
        return jsonify({"metrics": [], "error": "Database not available"}), 503
    
    try:
        cur = con.cursor()
        
        # Buscar último valor de cada métrica
        cur.execute("""
            SELECT 
                t1.submodel_name,
                t1.element_path,
                t1.value,
                t1.created_at
            FROM timeseries t1
            INNER JOIN (
                SELECT element_path, MAX(created_at) as max_date
                FROM timeseries
                GROUP BY element_path
            ) t2 ON t1.element_path = t2.element_path 
                AND t1.created_at = t2.max_date
            ORDER BY t1.submodel_name, t1.element_path
            LIMIT 500
        """)
        
        metrics = [
            {
                "submodel": row["submodel_name"],
                "path": row["element_path"],
                "value": row["value"],
                "timestamp": row["created_at"]
            }
            for row in cur.fetchall()
        ]
        
        return jsonify({
            "metrics": metrics,
            "count": len(metrics)
        })
    
    except sqlite3.Error as e:
        current_app.logger.error(f"Error fetching latest values: {e}")
        return jsonify({"error": "Database query failed"}), 500
    
    finally:
        con.close()
