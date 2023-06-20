import click
import typing as t
from lxml import etree as ET
from ..utils import format_docstring_as_help_str


USAGE_DESCRIPTION = format_docstring_as_help_str(
    """
    Override an entry in the project.ptx file. Entries are specified as `path` and `value`.
    Paths are `.`-separated. For example, the path of the `<c>` node in `<a><b><c>...` is
    `a.b.c`.

    Attributes can be overridden providing `path@attribute_name` and `value`. For example,
    to override the `foo` attribute in `<a><b><c foo="bar">...` use `a.b.c@foo`.

    Example, to over add/override custom xsl, you could run
    `pretext build {} targets.target.xsl custom.xsl`
"""
)


class ShadowXmlNodeType(t.TypedDict):
    name: t.Union[str, None]
    value: t.Union[str, None]
    attributes: t.List[t.Tuple[str, str]]


class XmlOverlayType(click.ParamType):
    name = "xml_overlay"

    def convert(
        self,
        value: t.Any,
        param: t.Optional[click.Parameter],
        ctx: t.Optional[click.Context],
    ) -> t.Any:
        print(
            "got",
            value,
            param,
            None if ctx is None else ctx.args,
            None if ctx is None else ctx.obj,
        )
        return value


class ShadowXmlDocument:
    def __init__(self) -> None:
        self._nodes_dict: t.Dict[str, ShadowXmlNodeType] = {}

    def upsert_node_or_attribute(self, path: str, value: str) -> "ShadowXmlDocument":
        """
        Upserts a node into the shadow document.

        @path - A string representing the path of the node/attribute. For example, `a.b.c` would be nested `<a><b><c>...` nodes.
                `a.b@c` would be an attribute named `c` on the `b` node. E.g. `<a><b c="...">...`
        @value - The (string) value of the node/attribute.
        """

        # paths of the form a.b.c@foo represent the attribute `foo` on the `c` node
        if "@" in path:
            if len(path.split("@")) > 2:
                raise Exception(
                    "Cannot have multiple `@` characters in a ShadowXmlDocument path."
                )
            path, attr_name = path.split("@")

            node = self._nodes_dict.get(
                path, {"name": None, "value": None, "attributes": []}
            )
            node["attributes"].append((attr_name, value))
            self._nodes_dict[path] = node
            # all other paths correspond to nodes and values
        else:
            node = self._nodes_dict.get(
                path, {"name": None, "value": None, "attributes": []}
            )
            node["value"] = value
            self._nodes_dict[path] = node
        return self

    def overlay_tree(self, root: ET._Element = ET.Element("root")) -> t.List[str]:
        """
        Overlay `root` with the current ShadowXmlDocument's nodes and attributes.
        A list of string messages are returned about what elements were changed.

        This function mutates `root`.
        """

        ret: t.List[str] = []

        def upsert_node(
            path: t.List[str],
            current: ET._Element = root,
            current_path: t.List[str] = [],
        ) -> t.List[ET._Element]:
            if len(path) == 0:
                return [current]
            needed_tag = path[0]
            path = path[1:]
            current_path = [*current_path, needed_tag]

            # Find all matching tags. If none are found, we create one.
            # If any are found we recurse down _every_ instance of a found tag
            matching_elms = [elm for elm in current if elm.tag == needed_tag]
            if len(matching_elms) == 0:
                # if we're here, there was no node with the correct tag name, so we add one.
                new_node = ET.Element(needed_tag)
                current.append(new_node)
                ret.append("NODE_ADDED with XML path {}".format(".".join(current_path)))
                return upsert_node(path, new_node, current_path)

            # There was one or more tags with the correct name;
            # Concatenate all target nodes that are found.
            return sum(
                (upsert_node(path, node, current_path) for node in matching_elms), []
            )

        for path, node in sorted(self._nodes_dict.items()):
            split_path = path.split(".")
            xml_nodes = upsert_node(split_path)
            for xml_node in xml_nodes:
                for attr, val in node["attributes"]:
                    old_val = xml_node.get(attr)
                    if old_val is not None:
                        if old_val != val:
                            ret.append(
                                f"ATTRIBUTE_CHANGED '{old_val}' to '{val}' at XML path '{path}'"
                            )
                    else:
                        ret.append(f"ATTRIBUTE_ADDED '{val}' at XML path '{path}'")
                    xml_node.set(attr, val)
                if node["value"] is not None:
                    if xml_node.text is not None:
                        ret.append(
                            "TEXT_CHANGED '{}' to '{}' at XML path '{}'".format(
                                repr(xml_node.text), repr(node["value"]), path
                            )
                        )
                    else:
                        ret.append(
                            "TEXT_ADDED '{}' at XML path '{}'".format(
                                repr(node["value"]), path
                            )
                        )
                    xml_node.text = node["value"]

        return ret

    def __repr__(self) -> str:
        node_repr = []
        for path, node in self._nodes_dict.items():
            attrs = " ".join(f'{key}="{val}"' for key, val in node["attributes"])
            value = "" if node["value"] is None else node["value"]
            node_repr.append(f"""<{path} {attrs}>{value}</>""")
        return "ShadowXmlDocument:" + "\n".join(sorted(node_repr))
