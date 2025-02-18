"""Basic example demonstrating pulumi-component-tree usage"""

from typing import TypedDict
from pulumi_component_tree import ComponentTree

class NetworkProps(TypedDict, total=False):
    cidr: str
    name: str

class NetworkResource(ComponentTree[NetworkProps]):
    """Example network resource"""
    
    def _construct(self) -> None:
        # In a real implementation, this would create actual cloud resources
        # For example using pulumi_aws.ec2.Vpc etc.
        self.network_name = self.props["name"]
        self.network_cidr = self.props["cidr"]

class SubnetProps(TypedDict, total=False):
    cidr: str
    zone: str

class SubnetResource(ComponentTree[SubnetProps]):
    """Example subnet resource"""
    
    def _construct(self) -> None:
        # Would create actual subnet resources in real implementation
        self.subnet_cidr = self.props["cidr"]
        self.availability_zone = self.props["zone"]

def main() -> None:
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

if __name__ == "__main__":
    main()
