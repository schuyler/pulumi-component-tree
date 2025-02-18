# pulumi-component-tree

A Python package providing a tree-like structure for managing Pulumi ComponentResources and their dependencies.

## Features

- Type-safe resource tree construction
- Automatic dependency management between parent and child resources
- Property inheritance via defaults
- Structured resource organization

## Installation

```bash
pip install pulumi-component-tree
```

## Basic Usage

```python
from pulumi_component_tree import Resource, ResourceProps
from typing import TypedDict

# Define resource properties
class NetworkProps(TypedDict, total=False):
    cidr: str
    name: str

# Create a resource type
class NetworkResource(Resource[NetworkProps]):
    def _construct(self) -> None:
        # Create your Pulumi resources here
        self.network_name = self.props["name"]
        self.network_cidr = self.props["cidr"]

# Use the resource in a tree structure
network = NetworkResource("main", {
    "name": "example-vpc",
    "cidr": "10.0.0.0/16"
})

# Add child resources
subnet = network.add(SubnetResource("subnet-a", {
    "cidr": "10.0.1.0/24",
    "zone": "us-west-2a"
}))

# Construct the tree (builds resources in correct order)
network.construct()
```

## Key Concepts

### Resources

Each resource extends the base `Resource` class and implements the `_construct()` method to create its Pulumi resources:

```python
class MyResource(Resource[MyProps]):
    def _construct(self) -> None:
        # Create Pulumi resources here
        pass
```

### Props and TypedDict

Resource properties are defined using `TypedDict` for type safety:

```python
class MyProps(TypedDict, total=False):
    name: str
    count: int
```

### Tree Structure

Resources can be organized in a tree with parent-child relationships:

```python
parent = ParentResource("parent", {...})
child1 = parent.add(ChildResource("child1", {...}))
child2 = parent.add(ChildResource("child2", {...}))
```

### Property Inheritance

Child resources can inherit properties from their parents:

```python
# Set defaults for all children of a specific type
parent.extend(ChildResource, {
    "environment": "prod",
    "region": "us-west-2"
})

# Add child - will inherit the defaults
child = parent.add(ChildResource("child", {...}))
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.
