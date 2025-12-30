"""
Network Validation Module

Validates that the hydrant network:
1. Is a valid tree structure (no loops)
2. Is connected from source to all nodes
3. Has exactly one source node
4. Has valid node and edge references
5. Has valid numeric values
"""

from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

try:
    from .models import Node, Edge, NodeType, NetworkInput
except ImportError:
    from models import Node, Edge, NodeType, NetworkInput


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_unique_ids(network: NetworkInput) -> List[str]:
    """
    Validate that all node and edge IDs are unique.

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    # Check node IDs
    node_ids = [n.node_id for n in network.nodes]
    if len(node_ids) != len(set(node_ids)):
        duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
        errors.append(f"Duplicate node IDs found: {set(duplicates)}")

    # Check edge IDs
    edge_ids = [e.edge_id for e in network.edges]
    if len(edge_ids) != len(set(edge_ids)):
        duplicates = [eid for eid in edge_ids if edge_ids.count(eid) > 1]
        errors.append(f"Duplicate edge IDs found: {set(duplicates)}")

    return errors


def validate_edge_references(network: NetworkInput) -> List[str]:
    """
    Validate that all edge from_node and to_node reference existing nodes.

    Returns:
        List of error messages
    """
    errors = []
    node_ids = {n.node_id for n in network.nodes}

    for edge in network.edges:
        if edge.from_node not in node_ids:
            errors.append(
                f"Edge '{edge.edge_id}' references non-existent from_node '{edge.from_node}'"
            )
        if edge.to_node not in node_ids:
            errors.append(
                f"Edge '{edge.edge_id}' references non-existent to_node '{edge.to_node}'"
            )

    return errors


def validate_single_source(network: NetworkInput) -> List[str]:
    """
    Validate that exactly one source node exists.

    Returns:
        List of error messages
    """
    errors = []
    sources = [n for n in network.nodes if n.type == NodeType.SOURCE]

    if len(sources) == 0:
        errors.append("No source node found. Network must have exactly one source.")
    elif len(sources) > 1:
        source_ids = [s.node_id for s in sources]
        errors.append(
            f"Multiple source nodes found: {source_ids}. Network must have exactly one source."
        )

    return errors


def validate_positive_values(network: NetworkInput) -> List[str]:
    """
    Validate that pipe dimensions and lengths are positive.

    Returns:
        List of error messages
    """
    errors = []

    for edge in network.edges:
        if edge.length_m <= 0:
            errors.append(
                f"Edge '{edge.edge_id}' has invalid length: {edge.length_m} m"
            )
        if edge.diameter_mm <= 0:
            errors.append(
                f"Edge '{edge.edge_id}' has invalid diameter: {edge.diameter_mm} mm"
            )

    for node in network.nodes:
        if node.demand_lpm < 0:
            errors.append(
                f"Node '{node.node_id}' has negative demand: {node.demand_lpm} L/min"
            )

    return errors


def detect_loop_dfs(
    node: str,
    parent_edge: Optional[str],
    adjacency: Dict[str, List[Tuple[str, str]]],  # node -> [(edge_id, neighbor)]
    visited: Set[str],
    rec_stack: Set[str],
    edge_visited: Set[str]
) -> Optional[str]:
    """
    DFS-based loop detection for directed graph.

    Args:
        node: Current node
        parent_edge: Edge we came from (to avoid backtracking)
        adjacency: Adjacency list
        visited: Visited nodes
        rec_stack: Recursion stack for cycle detection
        edge_visited: Visited edges

    Returns:
        Error message if loop found, None otherwise
    """
    visited.add(node)
    rec_stack.add(node)

    for edge_id, neighbor in adjacency.get(node, []):
        if edge_id in edge_visited:
            continue

        edge_visited.add(edge_id)

        if neighbor in rec_stack:
            return f"Loop detected: edge '{edge_id}' creates cycle at node '{neighbor}'"

        if neighbor not in visited:
            result = detect_loop_dfs(
                neighbor, edge_id, adjacency, visited, rec_stack, edge_visited
            )
            if result:
                return result

    rec_stack.remove(node)
    return None


def validate_no_loops(network: NetworkInput) -> List[str]:
    """
    Validate that the network contains no loops (is a tree).
    Uses DFS to detect cycles.

    Returns:
        List of error messages
    """
    errors = []

    # Build directed adjacency list
    adjacency: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for edge in network.edges:
        adjacency[edge.from_node].append((edge.edge_id, edge.to_node))

    # Also check for undirected cycles (edges going both ways)
    undirected_adj: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
    for edge in network.edges:
        undirected_adj[edge.from_node].append((edge.edge_id, edge.to_node))
        undirected_adj[edge.to_node].append((edge.edge_id, edge.from_node))

    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    edge_visited: Set[str] = set()

    # Check from each unvisited node
    for node in network.nodes:
        if node.node_id not in visited:
            result = detect_loop_dfs(
                node.node_id, None, adjacency, visited, rec_stack, edge_visited
            )
            if result:
                errors.append(result)
                break

    # Additional check: verify tree property (n nodes, n-1 edges)
    n_nodes = len(network.nodes)
    n_edges = len(network.edges)

    if n_edges != n_nodes - 1:
        # This could indicate a loop or disconnected components
        if n_edges > n_nodes - 1:
            errors.append(
                f"Network has {n_edges} edges but only {n_nodes} nodes. "
                f"A tree should have {n_nodes - 1} edges. This may indicate loops."
            )

    return errors


def validate_connected_from_source(network: NetworkInput) -> List[str]:
    """
    Validate that all nodes are reachable from the source node.
    Uses BFS from source.

    Returns:
        List of error messages
    """
    errors = []

    # Find source
    source = None
    for node in network.nodes:
        if node.type == NodeType.SOURCE:
            source = node.node_id
            break

    if not source:
        return ["Cannot validate connectivity: no source node found"]

    # Build adjacency list (directed: from_node -> to_node)
    adjacency: Dict[str, List[str]] = defaultdict(list)
    for edge in network.edges:
        adjacency[edge.from_node].append(edge.to_node)

    # BFS from source
    visited: Set[str] = set()
    queue: List[str] = [source]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        for neighbor in adjacency[current]:
            if neighbor not in visited:
                queue.append(neighbor)

    # Check which nodes are not reachable
    all_nodes = {n.node_id for n in network.nodes}
    unreachable = all_nodes - visited

    if unreachable:
        errors.append(
            f"The following nodes are not reachable from source '{source}': {unreachable}"
        )

    return errors


def validate_hydrant_demands(network: NetworkInput) -> List[str]:
    """
    Validate that at least one hydrant has positive demand when active.

    Returns:
        List of error messages
    """
    errors = []
    warnings = []

    active_hydrants = [
        n for n in network.nodes
        if n.type == NodeType.HYDRANT and n.is_active
    ]

    if not active_hydrants:
        errors.append(
            "No active hydrants found. Activate at least one hydrant with demand > 0."
        )
    else:
        total_demand = sum(h.demand_lpm for h in active_hydrants)
        if total_demand == 0:
            errors.append(
                "Total demand is zero. Set positive demand for active hydrants."
            )

    return errors


def validate_network(network: NetworkInput) -> Tuple[bool, List[str]]:
    """
    Run all validations on the network.

    Args:
        network: Network input to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    all_errors = []

    # Run all validations
    all_errors.extend(validate_unique_ids(network))
    all_errors.extend(validate_edge_references(network))
    all_errors.extend(validate_single_source(network))
    all_errors.extend(validate_positive_values(network))
    all_errors.extend(validate_no_loops(network))
    all_errors.extend(validate_connected_from_source(network))
    all_errors.extend(validate_hydrant_demands(network))

    is_valid = len(all_errors) == 0

    return is_valid, all_errors


def quick_validate(network: NetworkInput) -> bool:
    """
    Quick validation check (returns True/False only).

    Args:
        network: Network to validate

    Returns:
        True if valid, False otherwise
    """
    is_valid, _ = validate_network(network)
    return is_valid
