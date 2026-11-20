"""Builds an AACT model from what is really in a workspace.

Two independent sources, as in the book's chapter 9:
  * config_model  - deploy/*.yaml: services, databases, outbound URLs;
  * import_model  - Python import graph of a modular monolith.

Unknown means failure: everything that cannot be read is reported as an issue,
and an issue fails the architecture check instead of producing a green result.
"""
import ast
import re
from pathlib import Path

import yaml

URL = re.compile(r"^(?P<scheme>[a-z][a-z0-9+.-]*)://(?P<host>[^/:]+)")
ENDPOINT_LITERAL = re.compile(r"^[a-z][a-z0-9+.-]*://")
ENDPOINT_NAME = re.compile(r"(_URL|_URI|_DSN|_HOST|_ADDR|_ENDPOINT|_BROKERS)$")
KNOWN_KEYS = {
    "service": {"name", "kind", "module", "description", "labels", "environment"},
    "database": {"name", "kind", "database", "schema", "description", "labels"},
}


def element_id(name):
    return re.sub(r"[^a-zA-Z0-9]+", "_", name)


def _element(name, kind, tags=(), external=False, label=None):
    return {
        "name": name,
        "kind": kind,
        "label": label or name,
        "tags": list(tags),
        "relations": [],
        "external": external,
    }


def _strings_outside_docstrings(tree):
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
            ):
                docstrings.add(id(node.body[0].value))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            yield node


def _imported_modules(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module


def _scan_service_code(root, issues):
    """Finds wiring that bypasses deploy/*.yaml and so would be invisible."""
    services_dir = root / "services"
    for path in sorted(services_dir.rglob("*.py")):
        relative = path.relative_to(root)
        owner = relative.parts[1]
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as error:
            issues.append(f"{relative}: cannot parse: {error}")
            continue
        for node in _strings_outside_docstrings(tree):
            if ENDPOINT_LITERAL.match(node.value):
                issues.append(f"{relative}:{node.lineno}: hard-coded endpoint {node.value!r}")
        for module in _imported_modules(tree):
            parts = module.split(".")
            if parts[0] == "services" and len(parts) > 1 and parts[1] != owner:
                issues.append(f"{relative}: imports another service: {module}")
            if parts[0] == "sqlite3":
                issues.append(f"{relative}: bypasses shared.db via sqlite3")
            if parts[0] == "importlib":
                issues.append(f"{relative}: dynamic import cannot be analysed")


def config_model(root):
    root = Path(root)
    issues, manifests = [], []
    paths = sorted((root / "deploy").glob("*"))
    if not paths:
        issues.append("deploy/: no manifests found")
    for path in paths:
        if path.suffix != ".yaml":
            issues.append(f"{path.name}: unsupported file in deploy/")
            continue
        try:
            manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            issues.append(f"{path.name}: invalid YAML: {error}")
            continue
        kind = manifest.get("kind") if isinstance(manifest, dict) else None
        if kind not in KNOWN_KEYS:
            issues.append(f"{path.name}: unknown kind {kind!r}")
            continue
        extra = set(manifest) - KNOWN_KEYS[kind]
        if extra:
            issues.append(f"{path.name}: unknown fields {sorted(extra)}")
        manifests.append(manifest)

    names = {m["name"] for m in manifests}
    elements = {}
    for manifest in manifests:
        kind = "ContainerDb" if manifest["kind"] == "database" else "Container"
        tags = (manifest.get("labels") or {}).get("architecture.tags") or []
        elements[element_id(manifest["name"])] = _element(element_id(manifest["name"]), kind, tags)

    for manifest in manifests:
        if manifest["kind"] != "service":
            continue
        source = elements[element_id(manifest["name"])]
        for variable, value in (manifest.get("environment") or {}).items():
            value = str(value)
            match = URL.match(value)
            if not match:
                if ENDPOINT_NAME.search(variable):
                    issues.append(f"{manifest['name']}: cannot parse {variable}={value!r}")
                continue
            host = match["host"]
            target = element_id(host)
            if host not in names and target not in elements:
                elements[target] = _element(target, "System", external=True, label=host)
            source["relations"].append({"to": target, "technology": match["scheme"], "tags": []})

    if (root / "services").is_dir():
        _scan_service_code(root, issues)
    return list(elements.values()), issues


def import_model(root, package, shared_modules=()):
    root = Path(root)
    issues = []
    package_dir = root / package
    if not package_dir.is_dir():
        return [], [f"{package}/: package not found"]

    def module_name(path):
        parts = list(path.relative_to(root).with_suffix("").parts)
        return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)

    modules = {module_name(path): path for path in sorted(package_dir.rglob("*.py"))}
    elements = {}
    for name in modules:
        parts = name.split(".")
        tags = []
        if len(parts) > 1 and (package_dir / parts[1]).is_dir() and parts[1] not in shared_modules:
            tags.append(f"bc:{parts[1]}")
        elements[name] = _element(element_id(name), "Component", tags)

    def resolve(target):
        parts = target.split(".")
        while parts:
            candidate = ".".join(parts)
            if candidate in modules:
                return candidate
            parts.pop()
        return None

    for name, path in modules.items():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as error:
            issues.append(f"{path.relative_to(root)}: cannot parse: {error}")
            continue
        is_package = path.name == "__init__.py"
        targets = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                targets.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    anchor = name.split(".")
                    drop = node.level - (1 if is_package else 0)
                    anchor = anchor[: len(anchor) - drop] if drop else anchor
                    base = ".".join(anchor + ([node.module] if node.module else []))
                # "from pkg import sub" may name a submodule rather than an attribute.
                targets.update(
                    f"{base}.{alias.name}" if f"{base}.{alias.name}" in modules else base
                    for alias in node.names
                )
            elif isinstance(node, ast.Call):
                called = getattr(node.func, "id", getattr(node.func, "attr", ""))
                if called in {"__import__", "import_module"}:
                    issues.append(f"{path.relative_to(root)}:{node.lineno}: dynamic import")
        source = elements[name]
        for target in sorted(filter(None, map(resolve, targets))):
            if target != name:
                source["relations"].append({"to": element_id(target), "tags": []})
    return list(elements.values()), issues


_C4_ELEMENT = re.compile(r"^(Container|ContainerDb|System_Ext|Component)\(\s*([A-Za-z0-9_]+)\s*,")
_C4_RELATION = re.compile(r"^Rel(?:_[A-Za-z]+)?\(\s*([A-Za-z0-9_]+)\s*,\s*([A-Za-z0-9_]+)\s*[,)]")
_C4_IGNORED = re.compile(
    r"^(@startuml|@enduml|!include|'|title\b|LAYOUT_|SHOW_|Person\(|\}|[A-Za-z_]*Boundary\()"
)


def puml_model(path):
    """Reads the C4-PlantUML subset used in these repositories, strictly."""
    path = Path(path)
    if not path.is_file():
        return [], [f"{path.name}: not found"]
    kinds = {
        "Container": ("Container", False),
        "ContainerDb": ("ContainerDb", False),
        "Component": ("Component", False),
        "System_Ext": ("System", True),
    }
    elements, relations, issues = {}, [], []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or _C4_IGNORED.match(line):
            continue
        if match := _C4_ELEMENT.match(line):
            kind, external = kinds[match[1]]
            elements[match[2]] = _element(match[2], kind, external=external)
        elif match := _C4_RELATION.match(line):
            relations.append((match[1], match[2]))
        else:
            issues.append(f"{path.name}:{number}: cannot parse: {line}")
    for source, target in relations:
        if source not in elements or target not in elements:
            issues.append(f"{path.name}: relation to undeclared element: {source} -> {target}")
            continue
        elements[source]["relations"].append({"to": target, "tags": []})
    return list(elements.values()), issues
