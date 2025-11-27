#!/usr/bin/env python3
"""
CGMES RDF Schema to JSON-LD Context Converter

This tool converts CGMES RDF schema files into JSON-LD context files suitable for
hosting on a static file server. It generates:
- context.jsonld: Main entrypoint context file
- CIM/: Subfolder containing individual class context files
"""

import os
import json
from pathlib import Path
from rdflib import Graph, RDF, RDFS, Namespace, URIRef
from typing import Dict, List, Set
import argparse


class SchemaToJsonLdConverter:
    """Converts RDF schemas to JSON-LD context files."""

    def __init__(self, schema_dir: str, output_dir: str, base_uri: str = "http://iec.ch/TC57/2013/CIM-schema-cim16#",
                 context_base_url: str = None):
        """
        Initialize the converter.

        Args:
            schema_dir: Directory containing RDF schema files (.rdf, .ttl)
            output_dir: Output directory for JSON-LD context files
            base_uri: Base URI for CIM classes (default: CIM16 schema URI)
            context_base_url: Base URL where context files will be hosted (optional, uses relative URLs if not provided)
        """
        self.schema_dir = Path(schema_dir)
        self.output_dir = Path(output_dir)
        self.base_uri = base_uri
        self.context_base_url = context_base_url.rstrip('/') if context_base_url else None
        self.cim_dir = self.output_dir / "CIM"

        # Combined graph for all schemas
        self.graph = Graph()

        # Namespace definitions
        self.CIM = Namespace(base_uri)
        self.XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

        # Tracking
        self.classes: Dict[str, Dict] = {}
        self.properties: Dict[str, Dict] = {}

    def load_schemas(self):
        """Load all RDF schema files from the schema directory."""
        print(f"Loading schemas from {self.schema_dir}...")

        schema_files = list(self.schema_dir.glob("*.rdf")) + list(self.schema_dir.glob("*.ttl"))

        for schema_file in schema_files:
            print(f"  Loading {schema_file.name}...")
            try:
                if schema_file.suffix == ".rdf":
                    self.graph.parse(schema_file, format="xml")
                elif schema_file.suffix == ".ttl":
                    self.graph.parse(schema_file, format="turtle")
            except Exception as e:
                print(f"  Warning: Failed to parse {schema_file.name}: {e}")

        print(f"Loaded {len(self.graph)} triples from {len(schema_files)} files")

    def extract_classes(self):
        """Extract all classes from the RDF schema."""
        print("Extracting classes...")

        # Find all classes
        for class_uri in self.graph.subjects(RDF.type, RDFS.Class):
            class_name = self._extract_local_name(str(class_uri))

            # Get class metadata
            label = self._get_label(class_uri)
            comment = self._get_comment(class_uri)
            subclass_of = self._get_subclass_of(class_uri)

            self.classes[class_name] = {
                "@id": str(class_uri),
                "label": label or class_name,
                "comment": comment,
                "subClassOf": subclass_of,
                "properties": {}
            }

        print(f"Found {len(self.classes)} classes")

    def extract_properties(self):
        """Extract all properties and associate them with their domain classes."""
        print("Extracting properties...")

        # Find all properties (rdfs:Property)
        rdfs_property = URIRef("http://www.w3.org/2000/01/rdf-schema#Property")
        for prop_uri in self.graph.subjects(RDF.type, rdfs_property):
            prop_name = self._extract_local_name(str(prop_uri))

            # Get property metadata
            label = self._get_label(prop_uri)
            comment = self._get_comment(prop_uri)
            domain = self._get_domain(prop_uri)
            range_type = self._get_range(prop_uri)

            self.properties[prop_name] = {
                "@id": str(prop_uri),
                "label": label or prop_name,
                "comment": comment,
                "domain": domain,
                "range": range_type
            }

            # Associate property with its domain class
            if domain:
                domain_class = self._extract_local_name(domain)
                if domain_class in self.classes:
                    # Use the full property name (ClassName.propertyName)
                    self.classes[domain_class]["properties"][prop_name] = {
                        "@id": str(prop_uri),
                        "label": label,
                        "comment": comment,
                        "range": range_type
                    }

        print(f"Found {len(self.properties)} properties")

    def _get_inherited_properties(self, class_name: str, visited: Set[str] = None) -> Dict:
        """Recursively collect properties from parent classes."""
        if visited is None:
            visited = set()

        # Avoid circular references
        if class_name in visited:
            return {}
        visited.add(class_name)

        inherited = {}

        # Get the class data
        if class_name not in self.classes:
            return {}

        class_data = self.classes[class_name]

        # If this class has a parent, get its properties first
        if class_data.get("subClassOf"):
            parent_uri = class_data["subClassOf"]
            parent_name = self._extract_local_name(parent_uri)

            # Recursively get parent's properties (including its inherited ones)
            parent_props = self._get_inherited_properties(parent_name, visited)
            inherited.update(parent_props)

        # Add this class's own properties (will override parent if same name)
        inherited.update(class_data["properties"])

        return inherited

    def generate_class_contexts(self):
        """Generate individual JSON-LD context files for each class."""
        print("Generating class context files...")

        # Create CIM directory
        self.cim_dir.mkdir(parents=True, exist_ok=True)

        for class_name, class_data in self.classes.items():
            # Get all properties including inherited ones
            all_properties = self._get_inherited_properties(class_name)

            # Build context with all properties
            context = self._build_class_context(class_name, class_data, all_properties)

            # Write to file
            output_file = self.cim_dir / f"{class_name}.jsonld"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(context, f, indent=2, ensure_ascii=False)

        print(f"Generated {len(self.classes)} class context files in {self.cim_dir}")

    def generate_main_context(self):
        """Generate the main context.jsonld file."""
        print("Generating main context file...")

        # Build context with all classes
        context = {
            "@context": {
                "cim": self.base_uri,
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
            }
        }

        # Add all classes with references to their individual context files
        for class_name in sorted(self.classes.keys()):
            # Use absolute URL if context_base_url is provided, otherwise relative
            if self.context_base_url:
                context_url = f"{self.context_base_url}/CIM/{class_name}.jsonld"
            else:
                context_url = f"CIM/{class_name}.jsonld"

            context["@context"][class_name] = {
                "@id": f"cim:{class_name}",
                "@context": context_url
            }

        # Write main context file
        output_file = self.output_dir / "context.jsonld"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=2, ensure_ascii=False)

        print(f"Generated main context file: {output_file}")
        if self.context_base_url:
            print(f"Using absolute URLs with base: {self.context_base_url}")

    def _build_class_context(self, class_name: str, class_data: Dict, all_properties: Dict) -> Dict:
        """Build JSON-LD context for a single class including inherited properties."""
        context = {
            "@context": {
                "cim": self.base_uri,
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
            },
            "@id": class_data["@id"],
            "@type": "rdfs:Class",
            "rdfs:label": class_data["label"],
        }

        # Add comment if present
        if class_data.get("comment"):
            context["rdfs:comment"] = class_data["comment"]

        # Add subclass relationship if present
        if class_data.get("subClassOf"):
            subclass_name = self._extract_local_name(class_data["subClassOf"])
            context["rdfs:subClassOf"] = {
                "@id": class_data["subClassOf"],
                "@type": "@id"
            }

        # Add all properties (including inherited ones)
        # Use full qualified names with cim: prefix
        for prop_full_name, prop_data in all_properties.items():
            prop_context = {
                "@id": prop_data["@id"],
            }

            # Add type information based on range
            if prop_data.get("range"):
                range_uri = prop_data["range"]
                if "XMLSchema" in range_uri:
                    # Datatype property
                    xsd_type = self._extract_local_name(range_uri)
                    prop_context["@type"] = f"xsd:{xsd_type}"
                else:
                    # Object property
                    prop_context["@type"] = "@id"

            # Add label and comment as annotations
            if prop_data.get("label"):
                prop_context["rdfs:label"] = prop_data["label"]
            if prop_data.get("comment"):
                prop_context["rdfs:comment"] = prop_data["comment"]

            # Use the full property name with cim: prefix (e.g., cim:ACDCConverter.baseS)
            context[f"cim:{prop_full_name}"] = prop_context

        return context

    def _extract_local_name(self, uri: str) -> str:
        """Extract the local name from a URI."""
        if "#" in uri:
            return uri.split("#")[-1]
        elif "/" in uri:
            return uri.split("/")[-1]
        return uri

    def _get_label(self, subject: URIRef) -> str:
        """Get rdfs:label for a subject."""
        label = self.graph.value(subject, RDFS.label)
        return str(label) if label else None

    def _get_comment(self, subject: URIRef) -> str:
        """Get rdfs:comment for a subject."""
        comment = self.graph.value(subject, RDFS.comment)
        return str(comment) if comment else None

    def _get_subclass_of(self, subject: URIRef) -> str:
        """Get rdfs:subClassOf for a subject."""
        subclass = self.graph.value(subject, RDFS.subClassOf)
        return str(subclass) if subclass else None

    def _get_domain(self, subject: URIRef) -> str:
        """Get rdfs:domain for a property."""
        domain = self.graph.value(subject, RDFS.domain)
        return str(domain) if domain else None

    def _get_range(self, subject: URIRef) -> str:
        """Get rdfs:range for a property."""
        range_val = self.graph.value(subject, RDFS.range)
        return str(range_val) if range_val else None

    def convert(self):
        """Run the complete conversion process."""
        print("\n" + "="*60)
        print("CGMES RDF Schema to JSON-LD Context Converter")
        print("="*60 + "\n")

        self.load_schemas()
        self.extract_classes()
        self.extract_properties()
        self.generate_class_contexts()
        self.generate_main_context()

        print("\n" + "="*60)
        print("Conversion complete!")
        print(f"Output directory: {self.output_dir.absolute()}")
        print("="*60 + "\n")


def main():
    """Main entry point for the command-line tool."""
    parser = argparse.ArgumentParser(
        description="Convert CGMES RDF schemas to JSON-LD context files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert schemas from cgmes-data to output directory (with relative URLs)
  python main.py cgmes-data output

  # Generate with absolute URLs for hosting on a specific server
  python main.py cgmes-data output --context-base-url "https://example.com/contexts"

  # Specify custom base URI and context URL
  python main.py cgmes-data output --base-uri "http://example.com/cim#" --context-base-url "https://cdn.example.com/cim"
        """
    )

    parser.add_argument(
        "schema_dir",
        help="Directory containing RDF schema files (.rdf, .ttl)"
    )

    parser.add_argument(
        "output_dir",
        help="Output directory for JSON-LD context files"
    )

    parser.add_argument(
        "--base-uri",
        default="http://iec.ch/TC57/2013/CIM-schema-cim16#",
        help="Base URI for CIM classes (default: CIM16 schema URI)"
    )

    parser.add_argument(
        "--context-base-url",
        default=None,
        help="Base URL where context files will be hosted (e.g., http://example.com/contexts). If not provided, uses relative URLs."
    )

    args = parser.parse_args()

    # Create converter and run
    converter = SchemaToJsonLdConverter(
        schema_dir=args.schema_dir,
        output_dir=args.output_dir,
        base_uri=args.base_uri,
        context_base_url=args.context_base_url
    )

    converter.convert()


if __name__ == "__main__":
    main()
