# pulumi-component-tree

A Python framework for building tree-structured Pulumi components that facilitate clear organization and dependency management of cloud infrastructure resources. The tree structure naturally maps to how cloud resources are typically organized - for example, VPCs containing subnets, or Kubernetes clusters containing node pools.

## Features

- Type-safe properties using TypedDict for each component type
- Automatic parent-child dependency management
- Property inheritance from parent to child components 
- Fluent API for building resource trees using the `<<` operator
- Context manager support for automatic construction
- Full type hints and mypy compatibility
- Python 3.8+ support

## Requirements

- Python 3.8 or higher
- Pulumi 3.0.0 or higher
- typing-extensions 4.0.0 or higher

## Installation

```bash
pip install pulumi-component-tree
```

## Basic Usage

Here's a simple example that demonstrates the core functionality:

```python
from typing import TypedDict
from pulumi_component_tree import ComponentTree

class NetworkProps(TypedDict, total=False):
    cidr: str
    name: str

class NetworkResource(ComponentTree[NetworkProps]):
    """Network resource that could create a VPC"""
    
    def _construct(self) -> None:
        # In a real implementation, this would create actual cloud resources
        # For example using pulumi_aws.ec2.Vpc etc.
        self.network_name = self.props["name"]
        self.network_cidr = self.props["cidr"]

class SubnetProps(TypedDict, total=False):
    cidr: str
    zone: str

class SubnetResource(ComponentTree[SubnetProps]):
    """Subnet resource within a network"""
    
    def _construct(self) -> None:
        # Would create actual subnet resources in real implementation
        self.subnet_cidr = self.props["cidr"]
        self.availability_zone = self.props["zone"]

# Create network resource and add subnets as children
# Construction happens automatically when the context exits
network = NetworkResource("example-vpc", "main", {
    "name": "example-vpc",
    "cidr": "10.0.0.0/16"
})

with network as net:
    # Using << operator to add children
    net << SubnetResource("subnet", "subnet-a", {
        "cidr": "10.0.1.0/24",
        "zone": "us-west-2a"
    }) << SubnetResource("subnet", "subnet-b", {
        "cidr": "10.0.2.0/24", 
        "zone": "us-west-2b"
    })
```

## API Documentation

### ComponentTree

The base class for creating tree-structured Pulumi components:

```python
class ComponentTree[P](ComponentResource, Generic[P]):
    def __init__(self, 
                 t: str,
                 name: str, 
                 props: Optional[P] = None,
                 opts: Optional[ResourceOptions] = None,
                 remote: bool = False,
                 package_ref: Optional[Any] = None) -> None:
```

#### Key Methods

- `_construct(self) -> None`: Abstract method that subclasses must implement to create their resources
- `add(self, child: ChildComponent) -> Optional[ComponentTree[Any]]`: Add a child component or resource
- `extend(self, resource_type: Type[ComponentTree[Any]], props: ComponentTreeProps) -> None`: Set default properties for child types
- `construct(self) -> None`: Manually trigger resource construction (automatic with context manager)

#### Properties

- `props`: Get effective properties (defaults + instance props)
- `defaults`: Get/set default properties
- `opts`: Get/set Pulumi resource options
- `children`: List of constructed child resources

### Context Manager Support

The class supports the context manager protocol for automatic construction:

```python
with NetworkResource("vpc", "main") as vpc:
    vpc << SubnetResource("subnet", "a")  # Construction happens on context exit
```

Without the context manager, you must call `.construct()` explicitly:

```python
vpc = NetworkResource("vpc", "main")
vpc.add(SubnetResource("subnet", "a"))
vpc.construct()  # Must call explicitly!
```

### Property Inheritance

Child components can inherit properties from their parents:

```python
# Set defaults for all subnet children
vpc.extend(SubnetResource, {
    "vpc_id": vpc.id,
    "map_public_ip": True
})
```

### Resource Trees

The tree structure ensures:

1. Children are created after parents (proper dependency ordering)
2. Children inherit resource options from parents (e.g. provider, protection)
3. Resources are organized in a logical, maintainable way

## Advanced Usage

### Custom Resource Options

```python
from pulumi import ResourceOptions

# Apply options to specific components
subnet = SubnetResource("subnet", "private", {
    "cidr": "10.0.3.0/24"
}, opts=ResourceOptions(
    protect=True,  # Protect from accidental deletion
    depends_on=[some_other_resource]
))

# Options are inherited by children
with NetworkResource("vpc", "main", opts=ResourceOptions(
    provider=aws_provider,  # Use specific provider
    tags={"env": "prod"}  # Add tags to all child resources
)) as vpc:
    vpc << subnet
```

### Resource Creation Functions

Besides component classes, you can also add resource creation functions:

```python
vpc << (lambda props, opts: ec2.SecurityGroup(
    "sg",
    vpc_id=vpc.id,
    tags={"Name": f"{props['name']}-sg"},
    opts=opts
))
```

## License

Copyright (c) 2025, Schuyler Erle
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
