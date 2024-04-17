# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/pylint-dev/pylint/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/pylint/blob/main/CONTRIBUTORS.txt

"""Class to generate files in mermaidjs format."""

from __future__ import annotations

from pylint.pyreverse.diagrams import Cardinality
from pylint.pyreverse.printer import EdgeType, NodeProperties, NodeType, Printer
from pylint.pyreverse.utils import get_annotation_label


class MermaidJSPrinter(Printer):
    """Printer for MermaidJS diagrams."""

    DEFAULT_COLOR = "black"

    NODES: dict[NodeType, str] = {
        NodeType.CLASS: "class",
        NodeType.PACKAGE: "class",
    }
    ARROWS: dict[EdgeType, str] = {
        EdgeType.INHERITS: "--|>",
        EdgeType.ASSOCIATION: "--*",
        EdgeType.AGGREGATION: "--o",
        EdgeType.USES: "-->",
        EdgeType.TYPE_DEPENDENCY: "..>",
    }

    CARDINALITIES: dict[Cardinality, str] = {
        Cardinality.ZERO_OR_ONE: "0..1",
        Cardinality.EXACTLY_ONE: "1",
        Cardinality.ZERO_OR_MORE: "0..*",
        Cardinality.ONE_OR_MORE: "1..*",
    }

    def _open_graph(self) -> None:
        """Emit the header lines."""
        self.emit("classDiagram")
        self._inc_indent()

    def emit_node(
        self,
        name: str,
        type_: NodeType,
        properties: NodeProperties | None = None,
    ) -> None:
        """Create a new node.

        Nodes can be classes, packages, participants etc.
        """
        # pylint: disable=duplicate-code
        if properties is None:
            properties = NodeProperties(label=name)
        nodetype = self.NODES[type_]
        body: list[str] = []
        if properties.annotations:
            body.extend(f"<<{annotation}>>" for annotation in properties.annotations)
        if properties.attrs:
            body.extend(properties.attrs)
        if properties.methods:
            for func in properties.methods:
                args = self._get_method_arguments(func)
                line = f"{func.name}({', '.join(args)})"
                line += "*" if func.is_abstract() else ""
                if func.returns:
                    line += f" {get_annotation_label(func.returns)}"
                body.append(line)
        name = name.split(".")[-1]
        self.emit(f"{nodetype} {name} {{")
        self._inc_indent()
        for line in body:
            self.emit(line)
        self._dec_indent()
        self.emit("}")

    def emit_edge(
        self,
        from_node: str,
        to_node: str,
        type_: EdgeType,
        label: str | None = None,
        from_cardinality: Cardinality | None = None,
        to_cardinality: Cardinality | None = None,
    ) -> None:
        """Create an edge from one node to another to display relationships."""
        from_node = from_node.split(".")[-1]
        to_node = to_node.split(".")[-1]
        edge = f"{from_node} "
        if from_cardinality:
            edge += f'"{self.CARDINALITIES[from_cardinality]}" '
        edge += f"{self.ARROWS[type_]} "
        if to_cardinality:
            edge += f'"{self.CARDINALITIES[to_cardinality]}" '
        edge += to_node
        if label:
            edge += f" : {label}"
        self.emit(edge)

    def _close_graph(self) -> None:
        """Emit the lines needed to properly close the graph."""
        self._dec_indent()


class ERMermaidJSPrinter(MermaidJSPrinter):
    """Printer for ER MermaidJS diagrams."""

    CARDINALITIES: dict[Cardinality, str] = {
        Cardinality.ZERO_OR_ONE: "|o",
        Cardinality.EXACTLY_ONE: "||",
        Cardinality.ZERO_OR_MORE: "}o",
        Cardinality.ONE_OR_MORE: "}|",
    }

    def _open_graph(self) -> None:
        """Emit the header lines."""
        self.emit("erDiagram")
        self._inc_indent()

    def emit_node(
        self,
        name: str,
        type_: NodeType,
        properties: NodeProperties | None = None,
    ) -> None:
        """Create a new node.

        Nodes can be classes, packages, participants etc.
        """
        # pylint: disable=duplicate-code
        if properties is None:
            properties = NodeProperties(label=name)
        body: list[str] = []
        if properties.attrs:
            for attribute in properties.attrs:
                attribute_name = attribute.split(":")[0].strip()
                attribute_type = (
                    attribute.split(":")[1].strip() if ":" in attribute else "UNKNOWN"
                )
                if "|" in attribute_type:
                    attribute_type = ", ".join(attribute_type.split("|"))
                    attribute_type = f"Union[{attribute_type}]"
                # Remove spaces from attribute type to avoid conflicts with mermaid syntax
                # https://mermaid.js.org/syntax/entityRelationshipDiagram.html#attributes
                attribute_type = attribute_type.replace(" ", "")
                # Replace commas with dashes to avoid conflicts with mermaid syntax
                # Can be removed once https://github.com/mermaid-js/mermaid/pull/5128 is merged
                attribute_type = attribute_type.replace(",", "-")
                body.append(f"{attribute_type} {attribute_name}")
        name = name.split(".")[-1]
        self.emit(f"{name} {{")
        self._inc_indent()
        for line in body:
            self.emit(line)
        self._dec_indent()
        self.emit("}")

    def emit_edge(
        self,
        from_node: str,
        to_node: str,
        type_: EdgeType,
        label: str | None = None,
        from_cardinality: Cardinality | None = None,
        to_cardinality: Cardinality | None = None,
    ) -> None:
        """Create an edge from one node to another to display relationships."""
        from_node = from_node.split(".")[-1]
        to_node = to_node.split(".")[-1]
        from_cardinality = (
            Cardinality.ZERO_OR_MORE if from_cardinality is None else from_cardinality
        )
        to_cardinality = (
            Cardinality.ZERO_OR_MORE if to_cardinality is None else to_cardinality
        )
        arrow = f"{self.CARDINALITIES[from_cardinality]}--{self._reverse_cardinality(to_cardinality)}"
        edge = f"{from_node} {arrow} {to_node}"
        if label:
            edge += f" : {label}"
        self.emit(edge)

    def _reverse_cardinality(self, cardinality: Cardinality) -> str:
        """Reverse the edge."""
        cardinality_str = self.CARDINALITIES[cardinality]
        return cardinality_str[::-1].replace("}", "{")


class HTMLMermaidJSPrinter(MermaidJSPrinter):
    """Printer for MermaidJS diagrams wrapped in a html boilerplate."""

    HTML_OPEN_BOILERPLATE = """<html>
  <body>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
      <div class="mermaid">
    """
    HTML_CLOSE_BOILERPLATE = """
       </div>
  </body>
</html>
"""
    GRAPH_INDENT_LEVEL = 4

    def _open_graph(self) -> None:
        self.emit(self.HTML_OPEN_BOILERPLATE)
        for _ in range(self.GRAPH_INDENT_LEVEL):
            self._inc_indent()
        super()._open_graph()

    def _close_graph(self) -> None:
        for _ in range(self.GRAPH_INDENT_LEVEL):
            self._dec_indent()
        self.emit(self.HTML_CLOSE_BOILERPLATE)
