"""
plot_topology.py
Parse topology.txt and render a directed graph of nodes and connections
using graphviz (Digraph).

Node colours
------------
RESERVOIR  : steelblue  (cylinder shape)
PSTATION   : darkorange (diamond shape)
CHANNEL    : mediumseagreen (ellipse shape)

Edge colours
------------
OVERFLOW      : dodgerblue
OUTLET_HATCH  : sienna
OUTLET_TUNNEL : slategray
DOWNLINK      : darkorange  (power station discharge)
CHANNEL       : mediumseagreen
"""

from pathlib import Path
from graphviz import Digraph

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TOPOLOGY_FILE = Path(__file__).parent / "topology.txt"
OUTPUT_FILE   = Path(__file__).parent / "output" / "topology_graph"

NODE_STYLE = {
    "RESERVOIR": dict(shape="cylinder", style="filled", fillcolor="steelblue",
                      fontcolor="white", fontname="Helvetica-Bold"),
    "PSTATION":  dict(shape="diamond",  style="filled", fillcolor="darkorange",
                      fontcolor="white", fontname="Helvetica-Bold"),
    "CHANNEL":   dict(shape="ellipse",  style="filled", fillcolor="mediumseagreen",
                      fontcolor="white", fontname="Helvetica-Bold"),
}

EDGE_STYLE = {
    "OVERFLOW":      dict(color="dodgerblue",     xlabel="overflow",      style="dashed", fontsize="10"),
    "OUTLET_HATCH":  dict(color="sienna",         xlabel="outlet hatch",  style="solid",  fontsize="10"),
    "OUTLET_TUNNEL": dict(color="slategray",      xlabel="outlet tunnel", style="solid",  fontsize="10"),
    "DOWNLINK":      dict(color="darkorange",     xlabel="discharge",     style="bold",   fontsize="10"),
    "CHANNEL":       dict(color="mediumseagreen", xlabel="channel flow",  style="solid",  fontsize="10"),
}

INVALID_IDS = {-9999, -9}   # sentinel values meaning "no connection"


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
def parse_topology(filepath: Path):
    """Return (nodes, edges).

    nodes : dict  id -> {"type": str, "name": str}
    edges : list  of (src_id, dst_id, link_type)
    """
    nodes = {}
    edges = []

    current = None

    with open(filepath) as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            tokens = line.split()
            keyword = tokens[0].upper()

            # ---- open a new node block --------------------------------
            if keyword == "NODE":
                # NODE  RESERVOIR  0  RES_A
                # NODE  CHANNEL    2  CHAN2  5   (last token = downstream id)
                nodetype = tokens[1].upper()
                node_id  = int(tokens[2])
                name     = tokens[3]
                current  = {"id": node_id, "type": nodetype, "name": name}
                nodes[node_id] = current

                # CHANNEL carries downstream id on the NODE line
                if nodetype == "CHANNEL" and len(tokens) >= 5:
                    ds = int(tokens[4])
                    if ds not in INVALID_IDS:
                        edges.append((node_id, ds, "CHANNEL"))

            elif keyword == "ENDNODE":
                current = None

            elif current is None:
                continue   # outside any node block

            # ---- connection keywords ----------------------------------
            elif keyword == "OVERFLOW_CURVE":
                # OVERFLOW_CURVE  <npts>  <downstream_id>
                ds = int(tokens[2])
                if ds not in INVALID_IDS:
                    edges.append((current["id"], ds, "OVERFLOW"))

            elif keyword == "OUTLET_HATCH":
                # OUTLET_HATCH  <downstream_id>  ...
                ds = int(tokens[1])
                if ds not in INVALID_IDS:
                    edges.append((current["id"], ds, "OUTLET_HATCH"))

            elif keyword == "OUTLET_TUNNEL":
                ds = int(tokens[1])
                if ds not in INVALID_IDS:
                    edges.append((current["id"], ds, "OUTLET_TUNNEL"))

            elif keyword == "DOWNLINK_IDNR":
                ds = int(tokens[1])
                if ds not in INVALID_IDS:
                    edges.append((current["id"], ds, "DOWNLINK"))

    return nodes, edges


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_graph(nodes, edges):
    dot = Digraph(
        name="Topology",
        comment="Hydro cascade topology",
        graph_attr={
            "rankdir": "TB",
            "splines": "curved",
            "nodesep": "0.6",
            "ranksep": "0.8",
            "fontname": "Helvetica",
        },
        node_attr={"fontsize": "12"},
        edge_attr={"fontname": "Helvetica", "fontcolor": "gray30"},
    )

    # Add nodes
    for node_id, info in sorted(nodes.items()):
        ntype = info["type"]
        label = f"{info['name']}\n(id={node_id})"
        style = NODE_STYLE.get(ntype, dict(shape="box", style="filled",
                                            fillcolor="lightgray"))
        dot.node(str(node_id), label=label, **style)

    # Add edges (deduplicate same src-dst-type)
    seen = set()
    for src, dst, etype in edges:
        key = (src, dst, etype)
        if key in seen:
            continue
        seen.add(key)
        style = EDGE_STYLE.get(etype, dict(color="black", label=etype,
                                            style="solid", fontsize="10"))
        dot.edge(str(src), str(dst), **style)

    return dot


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    nodes, edges = parse_topology(TOPOLOGY_FILE)

    print(f"Parsed {len(nodes)} nodes and {len(edges)} edges.")
    for nid, info in sorted(nodes.items()):
        print(f"  Node {nid:3d}  {info['type']:12s}  {info['name']}")
    print()
    for src, dst, etype in edges:
        print(f"  {src} --> {dst}  [{etype}]")

    dot = build_graph(nodes, edges)
    rendered = dot.render(str(OUTPUT_FILE), format="png", cleanup=True)
    print(f"\nGraph saved to: {rendered}")


if __name__ == "__main__":
    main()
