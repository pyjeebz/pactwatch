"""Diff engine — structurally compare two OpenAPI specs and emit Change objects."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


@dataclass
class Change:
    """A single structural change detected between two OpenAPI specs."""

    change_type: str
    """One of: 'added', 'removed', 'modified'."""

    location: str
    """Top-level area: 'paths', 'schemas', 'security', 'parameters', 'responses'."""

    path: str
    """API path context, e.g. 'GET /users/{id}'."""

    field: str | None = None
    """Specific field affected, e.g. 'name', 'email'."""

    detail: dict = dc_field(default_factory=dict)
    """Extra context — old/new values, types, metadata."""


def diff_specs(old: dict, new: dict) -> list[Change]:
    """Compare two fully-resolved OpenAPI specs and return a list of Changes."""
    changes: list[Change] = []
    _diff_paths(old, new, changes)
    _diff_security(old, new, changes)
    return changes


def _diff_paths(old: dict, new: dict, changes: list[Change]) -> None:
    old_paths = old.get("paths", {})
    new_paths = new.get("paths", {})
    all_path_keys = set(old_paths.keys()) | set(new_paths.keys())

    for path_key in sorted(all_path_keys):
        old_path_item = old_paths.get(path_key, {})
        new_path_item = new_paths.get(path_key, {})
        old_methods = {m for m in old_path_item if m in HTTP_METHODS}
        new_methods = {m for m in new_path_item if m in HTTP_METHODS}

        for method in sorted(old_methods - new_methods):
            changes.append(Change(
                change_type="removed", location="paths",
                path=f"{method.upper()} {path_key}",
                detail={"operation": old_path_item[method]},
            ))

        for method in sorted(new_methods - old_methods):
            changes.append(Change(
                change_type="added", location="paths",
                path=f"{method.upper()} {path_key}",
                detail={"operation": new_path_item[method]},
            ))

        for method in sorted(old_methods & new_methods):
            endpoint = f"{method.upper()} {path_key}"
            _diff_operation(endpoint, old_path_item[method], new_path_item[method], changes)


def _diff_operation(endpoint: str, old_op: dict, new_op: dict, changes: list[Change]) -> None:
    _diff_parameters(endpoint, old_op, new_op, changes)
    _diff_request_body(endpoint, old_op, new_op, changes)
    _diff_responses(endpoint, old_op, new_op, changes)
    _diff_description(endpoint, old_op, new_op, changes)
    _diff_operation_security(endpoint, old_op, new_op, changes)


def _params_by_key(op: dict) -> dict[str, dict]:
    params = op.get("parameters", [])
    return {(p["name"], p.get("in", "query")): p for p in params}


def _diff_parameters(endpoint: str, old_op: dict, new_op: dict, changes: list[Change]) -> None:
    old_params = _params_by_key(old_op)
    new_params = _params_by_key(new_op)

    for key in sorted(set(old_params) | set(new_params)):
        name, location = key
        if key not in new_params:
            changes.append(Change(change_type="removed", location="parameters",
                                  path=endpoint, field=name, detail={"parameter": old_params[key]}))
        elif key not in old_params:
            changes.append(Change(change_type="added", location="parameters",
                                  path=endpoint, field=name, detail={"parameter": new_params[key]}))
        else:
            old_p, new_p = old_params[key], new_params[key]
            old_type = _schema_type(old_p.get("schema", {}))
            new_type = _schema_type(new_p.get("schema", {}))
            if old_type != new_type:
                changes.append(Change(change_type="modified", location="parameters",
                                      path=endpoint, field=name,
                                      detail={"old_type": old_type, "new_type": new_type}))
            old_req = old_p.get("required", False)
            new_req = new_p.get("required", False)
            if old_req != new_req:
                changes.append(Change(change_type="modified", location="parameters",
                                      path=endpoint, field=name,
                                      detail={"attribute": "required", "old_value": old_req, "new_value": new_req}))


def _diff_request_body(endpoint: str, old_op: dict, new_op: dict, changes: list[Change]) -> None:
    old_schema = _extract_json_schema(old_op.get("requestBody", {}))
    new_schema = _extract_json_schema(new_op.get("requestBody", {}))
    if old_schema or new_schema:
        _diff_schema(endpoint, old_schema or {}, new_schema or {}, changes, context="request")


def _diff_responses(endpoint: str, old_op: dict, new_op: dict, changes: list[Change]) -> None:
    old_responses = old_op.get("responses", {})
    new_responses = new_op.get("responses", {})
    all_codes = set(old_responses.keys()) | set(new_responses.keys())

    for code in sorted(all_codes):
        if code not in new_responses:
            changes.append(Change(change_type="removed", location="responses",
                                  path=endpoint, field=str(code),
                                  detail={"status_code": code, "response": old_responses[code]}))
        elif code not in old_responses:
            changes.append(Change(change_type="added", location="responses",
                                  path=endpoint, field=str(code),
                                  detail={"status_code": code, "response": new_responses[code]}))
        else:
            old_resp_schema = _extract_json_schema(old_responses[code])
            new_resp_schema = _extract_json_schema(new_responses[code])
            if old_resp_schema or new_resp_schema:
                _diff_schema(endpoint, old_resp_schema or {}, new_resp_schema or {},
                             changes, context="response", status_code=code)


def _diff_schema(endpoint: str, old_schema: dict, new_schema: dict,
                 changes: list[Change], context: str = "response",
                 status_code: str | None = None, parent_field: str | None = None) -> None:
    old_props = old_schema.get("properties", {})
    new_props = new_schema.get("properties", {})
    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))
    all_fields = set(old_props.keys()) | set(new_props.keys())

    for field_name in sorted(all_fields):
        full_field = f"{parent_field}.{field_name}" if parent_field else field_name
        base_detail = {"context": context, "status_code": status_code}

        if field_name not in new_props:
            changes.append(Change(change_type="removed", location="schemas", path=endpoint,
                                  field=full_field, detail={**base_detail, "was_required": field_name in old_required,
                                                            "old_schema": old_props[field_name]}))
        elif field_name not in old_props:
            changes.append(Change(change_type="added", location="schemas", path=endpoint,
                                  field=full_field, detail={**base_detail, "is_required": field_name in new_required,
                                                            "new_schema": new_props[field_name]}))
        else:
            old_fs, new_fs = old_props[field_name], new_props[field_name]
            old_type, new_type = _schema_type(old_fs), _schema_type(new_fs)
            if old_type != new_type:
                changes.append(Change(change_type="modified", location="schemas", path=endpoint,
                                      field=full_field, detail={**base_detail, "attribute": "type",
                                                                 "old_value": old_type, "new_value": new_type}))
            old_nullable = old_fs.get("nullable", False)
            new_nullable = new_fs.get("nullable", False)
            if old_nullable != new_nullable:
                changes.append(Change(change_type="modified", location="schemas", path=endpoint,
                                      field=full_field, detail={**base_detail, "attribute": "nullable",
                                                                 "old_value": old_nullable, "new_value": new_nullable}))
            old_enum, new_enum = set(old_fs.get("enum", [])), set(new_fs.get("enum", []))
            if old_enum != new_enum:
                removed_vals = old_enum - new_enum
                added_vals = new_enum - old_enum
                if removed_vals:
                    changes.append(Change(change_type="modified", location="schemas", path=endpoint,
                                          field=full_field, detail={**base_detail, "attribute": "enum_removed",
                                                                     "removed_values": sorted(removed_vals),
                                                                     "remaining_values": sorted(new_enum)}))
                if added_vals:
                    changes.append(Change(change_type="modified", location="schemas", path=endpoint,
                                          field=full_field, detail={**base_detail, "attribute": "enum_added",
                                                                     "added_values": sorted(added_vals),
                                                                     "all_values": sorted(new_enum)}))
            old_default = old_fs.get("default")
            new_default = new_fs.get("default")
            if old_default != new_default and ("default" in old_fs or "default" in new_fs):
                changes.append(Change(change_type="modified", location="schemas", path=endpoint,
                                      field=full_field, detail={**base_detail, "attribute": "default",
                                                                 "old_value": old_default, "new_value": new_default}))
            if old_fs.get("type") == "object" and new_fs.get("type") == "object":
                _diff_schema(endpoint, old_fs, new_fs, changes, context=context,
                             status_code=status_code, parent_field=full_field)

    # Required-status changes for shared fields
    for field_name in sorted(old_props.keys() & new_props.keys()):
        full_field = f"{parent_field}.{field_name}" if parent_field else field_name
        was_required = field_name in old_required
        is_required = field_name in new_required
        if was_required != is_required:
            changes.append(Change(change_type="modified", location="schemas", path=endpoint,
                                  field=full_field, detail={"context": context, "status_code": status_code,
                                                            "attribute": "required",
                                                            "old_value": was_required, "new_value": is_required}))


def _diff_security(old: dict, new: dict, changes: list[Change]) -> None:
    old_schemes = (old.get("components", {}) or {}).get("securitySchemes", {}) or {}
    new_schemes = (new.get("components", {}) or {}).get("securitySchemes", {}) or {}

    for name in sorted(set(old_schemes) | set(new_schemes)):
        if name not in new_schemes:
            changes.append(Change(change_type="removed", location="security", path="securitySchemes",
                                  field=name, detail={"old_scheme": old_schemes[name]}))
        elif name not in old_schemes:
            changes.append(Change(change_type="added", location="security", path="securitySchemes",
                                  field=name, detail={"new_scheme": new_schemes[name]}))
        elif old_schemes[name] != new_schemes[name]:
            changes.append(Change(change_type="modified", location="security", path="securitySchemes",
                                  field=name, detail={"old_scheme": old_schemes[name], "new_scheme": new_schemes[name]}))

    old_sec = old.get("security", [])
    new_sec = new.get("security", [])
    if old_sec != new_sec:
        changes.append(Change(change_type="modified", location="security", path="security",
                              detail={"old_value": old_sec, "new_value": new_sec}))


def _diff_operation_security(endpoint: str, old_op: dict, new_op: dict, changes: list[Change]) -> None:
    old_sec = old_op.get("security")
    new_sec = new_op.get("security")
    if old_sec is not None and new_sec is not None and old_sec != new_sec:
        changes.append(Change(change_type="modified", location="security", path=endpoint,
                              detail={"old_value": old_sec, "new_value": new_sec}))
    elif old_sec is not None and new_sec is None:
        changes.append(Change(change_type="removed", location="security", path=endpoint,
                              detail={"old_value": old_sec}))
    elif old_sec is None and new_sec is not None:
        changes.append(Change(change_type="added", location="security", path=endpoint,
                              detail={"new_value": new_sec}))


def _diff_description(endpoint: str, old_op: dict, new_op: dict, changes: list[Change]) -> None:
    for attr in ("description", "summary"):
        old_val = old_op.get(attr)
        new_val = new_op.get(attr)
        if old_val != new_val:
            changes.append(Change(change_type="modified", location="paths", path=endpoint,
                                  field=attr, detail={"old_value": old_val, "new_value": new_val}))


def _schema_type(schema: dict) -> str:
    return schema.get("type", "object")


def _extract_json_schema(container: dict) -> dict | None:
    content = container.get("content", {})
    json_content = content.get("application/json", {})
    return json_content.get("schema")
