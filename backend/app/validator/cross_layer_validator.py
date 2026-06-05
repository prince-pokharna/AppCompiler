"""Cross-layer consistency checks between API, DB, UI, and Auth schemas."""

from __future__ import annotations

import logging

from app.schemas.pipeline_schemas import ErrorType, ValidationError

logger = logging.getLogger("appcompiler.validator.cross_layer")


def run_all_checks(
    ui: dict,
    api: dict,
    database: dict,
    auth: dict,
    architecture: dict,
) -> list[ValidationError]:
    """Run all 6 cross-layer consistency checks.

    Returns a list of ValidationError for any inconsistencies found.
    """
    errors: list[ValidationError] = []

    errors.extend(check_api_db_field_consistency(api, database))
    errors.extend(check_ui_api_mapping(ui, api))
    errors.extend(check_auth_roles_consistency(auth, architecture))
    errors.extend(check_db_foreign_keys(database))
    errors.extend(check_auth_api_consistency(api, auth))
    errors.extend(check_ui_auth_routes(ui, api))

    if errors:
        logger.info(
            f"Cross-layer validation found {len(errors)} inconsistency(ies)",
            extra={"error_count": len(errors)},
        )
    else:
        logger.debug("Cross-layer validation passed — all layers consistent")

    return errors


def check_api_db_field_consistency(api: dict, database: dict) -> list[ValidationError]:
    """CHECK 1: Every API endpoint's request/response fields should exist in DB schema."""
    errors: list[ValidationError] = []

    # Build a map of table_name -> set of column names
    db_columns: dict[str, set[str]] = {}
    for table in database.get("tables", []):
        table_name = table.get("name", "").lower()
        columns = {col.get("name", "").lower() for col in table.get("columns", [])}
        db_columns[table_name] = columns

    # Flatten all column names for a lenient check
    all_db_columns: set[str] = set()
    for cols in db_columns.values():
        all_db_columns.update(cols)

    # Common fields that don't need DB mapping
    meta_fields = {
        "items", "total", "page", "limit", "success", "message",
        "token", "access_token", "refresh_token", "error", "data",
        "id", "created_at", "updated_at", "password", "password_hash",
        "confirm_password", "page_size", "offset", "sort", "order",
        "search", "query", "filter", "count",
    }

    for endpoint in api.get("endpoints", []):
        path = endpoint.get("path", "")
        method = endpoint.get("method", "")

        for field_list_key in ("request_body", "response_body"):
            for field in endpoint.get(field_list_key, []):
                field_name = field.get("name", "").lower()
                if field_name in meta_fields:
                    continue
                if field_name and field_name not in all_db_columns:
                    errors.append(
                        ValidationError(
                            error_type=ErrorType.ORPHAN_REF,
                            layer="api",
                            path=f"endpoints[{method} {path}].{field_list_key}.{field_name}",
                            message=(
                                f"API field '{field_name}' in {method} {path} "
                                f"has no matching column in any database table"
                            ),
                            severity="warning",
                            auto_repairable=True,
                        )
                    )

    return errors


def check_ui_api_mapping(ui: dict, api: dict) -> list[ValidationError]:
    """CHECK 2: Every UI form/table data_source must map to an API endpoint."""
    errors: list[ValidationError] = []

    api_paths: set[str] = set()
    for endpoint in api.get("endpoints", []):
        api_paths.add(endpoint.get("path", ""))

    for page in ui.get("pages", []):
        page_name = page.get("name", "")
        for comp in page.get("components", []):
            data_source = comp.get("data_source", "")
            if not data_source:
                continue

            matched = any(
                api_path == data_source
                or api_path.startswith(data_source)
                or data_source.startswith(api_path.rstrip("/"))
                for api_path in api_paths
            )

            if not matched:
                errors.append(
                    ValidationError(
                        error_type=ErrorType.ORPHAN_REF,
                        layer="ui",
                        path=f"pages[{page_name}].components[{comp.get('name', '')}].data_source",
                        message=(
                            f"UI component '{comp.get('name', '')}' on page '{page_name}' "
                            f"references data_source '{data_source}' which has no matching API endpoint"
                        ),
                        severity="warning",
                        auto_repairable=True,
                    )
                )

    return errors


def check_auth_roles_consistency(auth: dict, architecture: dict) -> list[ValidationError]:
    """CHECK 3: Every role in auth must match roles defined in architecture."""
    errors: list[ValidationError] = []

    auth_roles = set(auth.get("roles", []))
    arch_roles = set(architecture.get("role_permissions", {}).keys())

    for role in auth_roles - arch_roles:
        errors.append(
            ValidationError(
                error_type=ErrorType.INCONSISTENCY,
                layer="auth",
                path=f"roles[{role}]",
                message=f"Auth role '{role}' is not defined in architecture role_permissions",
                severity="warning",
                auto_repairable=True,
            )
        )

    for role in arch_roles - auth_roles:
        errors.append(
            ValidationError(
                error_type=ErrorType.INCONSISTENCY,
                layer="auth",
                path=f"roles",
                message=f"Architecture role '{role}' is missing from auth roles",
                severity="error",
                auto_repairable=True,
            )
        )

    permissions = auth.get("permissions", {})
    for role in auth_roles:
        if role not in permissions:
            errors.append(
                ValidationError(
                    error_type=ErrorType.MISSING_FIELD,
                    layer="auth",
                    path=f"permissions[{role}]",
                    message=f"Auth role '{role}' has no permissions defined",
                    severity="error",
                    auto_repairable=True,
                )
            )

    return errors


def check_db_foreign_keys(database: dict) -> list[ValidationError]:
    """CHECK 4: Every DB foreign key must reference an existing table+column."""
    errors: list[ValidationError] = []

    tables: dict[str, set[str]] = {}
    for table in database.get("tables", []):
        table_name = table.get("name", "")
        columns = {col.get("name", "") for col in table.get("columns", [])}
        tables[table_name] = columns

    for table in database.get("tables", []):
        table_name = table.get("name", "")
        for fk in table.get("foreign_keys", []):
            fk_column = fk.get("column", "")
            ref_table = fk.get("references_table", "")
            ref_column = fk.get("references_column", "")

            if fk_column and fk_column not in tables.get(table_name, set()):
                errors.append(
                    ValidationError(
                        error_type=ErrorType.ORPHAN_REF,
                        layer="database",
                        path=f"tables[{table_name}].foreign_keys[{fk_column}]",
                        message=f"Foreign key column '{fk_column}' does not exist in table '{table_name}'",
                        severity="error",
                        auto_repairable=True,
                    )
                )

            if ref_table and ref_table not in tables:
                errors.append(
                    ValidationError(
                        error_type=ErrorType.ORPHAN_REF,
                        layer="database",
                        path=f"tables[{table_name}].foreign_keys[{fk_column}].references_table",
                        message=f"Foreign key in '{table_name}' references non-existent table '{ref_table}'",
                        severity="error",
                        auto_repairable=True,
                    )
                )
            elif ref_table in tables and ref_column:
                if ref_column not in tables[ref_table]:
                    errors.append(
                        ValidationError(
                            error_type=ErrorType.ORPHAN_REF,
                            layer="database",
                            path=f"tables[{table_name}].foreign_keys[{fk_column}].references_column",
                            message=f"Foreign key in '{table_name}' references non-existent column '{ref_column}' in table '{ref_table}'",
                            severity="error",
                            auto_repairable=True,
                        )
                    )

    return errors


def check_auth_api_consistency(api: dict, auth: dict) -> list[ValidationError]:
    """CHECK 5: API endpoints marked auth_required must have corresponding auth rules."""
    errors: list[ValidationError] = []

    auth_roles = set(auth.get("roles", []))

    for endpoint in api.get("endpoints", []):
        path = endpoint.get("path", "")
        method = endpoint.get("method", "")

        if endpoint.get("auth_required", False):
            roles_allowed = set(endpoint.get("roles_allowed", []))
            for role in roles_allowed:
                if role not in auth_roles:
                    errors.append(
                        ValidationError(
                            error_type=ErrorType.INCONSISTENCY,
                            layer="api",
                            path=f"endpoints[{method} {path}].roles_allowed",
                            message=f"API endpoint {method} {path} allows role '{role}' which is not defined in auth schema",
                            severity="error",
                            auto_repairable=True,
                        )
                    )

    return errors


def check_ui_auth_routes(ui: dict, api: dict) -> list[ValidationError]:
    """CHECK 6: UI pages marked auth_required should have corresponding route protection."""
    errors: list[ValidationError] = []

    auth_api_paths: set[str] = set()
    no_auth_api_paths: set[str] = set()
    for endpoint in api.get("endpoints", []):
        path = endpoint.get("path", "")
        if endpoint.get("auth_required", False):
            auth_api_paths.add(path)
        else:
            no_auth_api_paths.add(path)

    for page in ui.get("pages", []):
        page_name = page.get("name", "")
        page_auth_required = page.get("auth_required", False)

        if page_auth_required:
            for comp in page.get("components", []):
                data_source = comp.get("data_source", "")
                if not data_source:
                    continue

                if data_source in no_auth_api_paths and data_source not in auth_api_paths:
                    errors.append(
                        ValidationError(
                            error_type=ErrorType.INCONSISTENCY,
                            layer="ui",
                            path=f"pages[{page_name}].auth_required",
                            message=f"Page '{page_name}' requires auth but component '{comp.get('name', '')}' uses non-auth API endpoint '{data_source}'",
                            severity="warning",
                            auto_repairable=False,
                        )
                    )

    return errors
