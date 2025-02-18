"""Pulumi Component Tree - Hierarchical Infrastructure as Code

This module provides a framework for building tree-structured Pulumi components that
facilitate clear organization and dependency management of cloud infrastructure resources.
The tree structure naturally maps to how cloud resources are typically organized -
for example, VPCs containing subnets, or Kubernetes clusters containing node pools.

Key features:
- Type-safe properties using TypedDict for each component type
- Automatic parent-child dependency management
- Property inheritance from parent to child components
- Fluent API for building resource trees
- Context manager support for automatic construction

Example usage:

    class NetworkProps(TypedDict, total=False):
        cidr: str
        name: str

    class Network(ComponentTree[NetworkProps]):
        def _construct(self) -> None:
            # Create VPC resources...
            pass

    class SubnetProps(TypedDict, total=False):
        cidr: str
        zone: str

    class Subnet(ComponentTree[SubnetProps]):
        def _construct(self) -> None:
            # Create subnet resources...
            pass

    # Build the resource tree
    network = Network("vpc", "main", {"cidr": "10.0.0.0/16"})
    with network as net:
        net << Subnet("subnet", "a", {"cidr": "10.0.1.0/24"})
            << Subnet("subnet", "b", {"cidr": "10.0.2.0/24"})

The tree structure ensures that:
1. Children are created after parents (proper dependency ordering)
2. Children inherit resource options from parents (e.g. provider, protection)
3. Resources are organized in a logical, maintainable way

Note: If not using the `with` context manager syntax, you must explicitly call
.construct() to finalize the resource tree:

    # Without context manager
    network = Network("vpc", "main", {"cidr": "10.0.0.0/16"})
    network.add(Subnet("subnet", "a", {"cidr": "10.0.1.0/24"}))
    network.add(Subnet("subnet", "b", {"cidr": "10.0.2.0/24"}))
    network.construct()  # Must call explicitly!
"""

from typing import TypeVar, Generic, Dict, Any, TypedDict, cast, List, Optional, Type, Callable, Union

from pulumi import ComponentResource, ResourceOptions, Resource

class ComponentTreeWrapper:
    """Wrapper for lambda functions that create Pulumi resources.
    
    This class handles the delayed execution of resource creation functions
    within a ComponentTree, ensuring proper dependency ordering and property inheritance.
    """
    def __init__(self, wrapper: "ResourceWrapper", parent: "ComponentTree[Any]") -> None:
        """Initialize a wrapper for a resource creation function.

        Args:
            wrapper: A callable that takes ComponentTreeProps and ResourceOptions and returns a Resource
            parent: The parent ComponentTree instance that will own this resource
        """
        self._wrapper = wrapper
        self._parent = parent
        
    def construct(self) -> Resource:
        """Execute the wrapped function with the parent's properties and options.

        Returns:
            Resource: The Pulumi resource created by the wrapped function
        """
        opts = ResourceOptions.merge(self._parent.opts, ResourceOptions(parent=self._parent))
        return self._wrapper(self._parent.props, opts)

class ComponentTreeProps(TypedDict, total=False):
    """Base properties for all resources"""
    pass

P = TypeVar("P", bound=ComponentTreeProps)
ResourceWrapper = Callable[[ComponentTreeProps, Optional[ResourceOptions]], Resource]
ChildComponent = Union["ComponentTree[Any]", ResourceWrapper]

class ComponentTree(ComponentResource, Generic[P]):
    """Base resource class that supports tree-like structures
    
    Each concrete subclass must implement _construct() to create its resources.
    Resources can be organized in a tree structure with parent-child relationships
    that automatically handle dependencies.

    The tree is built by adding children within a context manager block.
    Construction happens automatically when the context exits.
    """
    
    _props: P
    _defaults: P
    _opts: Optional[ResourceOptions]
    _constructed: bool
    _children: List[Union["ComponentTree[Any]", Resource, ComponentTreeWrapper]]
    _child_props: Dict[Type["ComponentTree[Any]"], ComponentTreeProps]

    def __init__(self, t: str, name: str, props: Optional[P] = None, opts: Optional[ResourceOptions] = None, remote: bool = False, package_ref: Optional[Any] = None) -> None:
        """Initialize a new ComponentTree resource.

        This creates a new node in the resource tree. The node won't actually create
        its cloud resources until construct() is called, typically via the context manager.

        Args:
            t: The type token for this resource (e.g. 'pkg:index:ResourceType')
            name: Unique name for this resource instance
            props: Type-safe dictionary of resource properties
            opts: Resource options controlling aspects like dependencies and providers
            remote: Set to True if this is a remote component resource
            package_ref: Optional reference to a custom resource package

        Example:
            ```python
            vpc = NetworkResource("vpc", "main", {
                "cidr": "10.0.0.0/16",
                "name": "main-vpc"
            })
            ```
        """
        self._props = props or cast(P, {})
        self._constructed = False
        self._defaults = cast(P, {})
        self._opts = opts
        self._children = []
        self._child_props = {}
        super().__init__(t, name, props, opts, remote, package_ref)

    @property
    def props(self) -> P:
        """Get the effective properties for this resource.

        Returns a combination of the default properties and instance-specific
        properties, with instance properties taking precedence.

        Returns:
            P: The merged property dictionary
        """
        return cast(P, {**self._defaults, **self._props})

    @property
    def defaults(self) -> P:
        """Get the default properties for this resource type.

        These properties are combined with instance-specific properties,
        serving as fallback values when a property isn't specified for
        a particular instance.

        Returns:
            P: The default property dictionary
        """
        return self._defaults
    
    @defaults.setter 
    def defaults(self, value: P) -> None:
        """Set the default properties for this resource type.

        Args:
            value: The new default properties to use
        """
        self._defaults = value

    @property
    def opts(self) -> Optional[ResourceOptions]:
        """Get the Pulumi ResourceOptions for this resource.

        These options control aspects like dependencies, providers, and
        protection from deletion.

        Returns:
            Optional[ResourceOptions]: The current resource options, or None if not set
        """
        return self._opts

    @opts.setter
    def opts(self, opts: ResourceOptions) -> None:
        """Set resource options, merging with any existing options.

        When setting new options, they are merged with any existing options
        rather than replacing them completely. This ensures that important
        options like parent dependencies are preserved.

        Args:
            opts: The new resource options to merge with existing ones
        """
        self._opts = ResourceOptions.merge(self._opts, opts)

    @property
    def children(self) -> List[Resource]:
        """Get all child resources owned by this resource.

        Returns only fully constructed Pulumi Resource instances,
        filtering out any pending resource wrappers.

        Returns:
            List[Resource]: List of child resources
        """
        return [c for c in self._children if isinstance(c, (ComponentTree, Resource)) and not isinstance(c, ComponentTreeWrapper)]
    
    def extend(self, resource_type: Type["ComponentTree[Any]"], props: ComponentTreeProps) -> None:
        """Set default properties for a specific child resource type.

        This allows setting default property values that will be applied to
        all children of a specific type added to this resource.

        Args:
            resource_type: The ComponentTree subclass to set defaults for
            props: Default properties to apply to children of this type

        Example:
            ```python
            # All subnets added to this VPC will inherit these defaults
            vpc.extend(SubnetResource, {
                "vpc_id": vpc.id,
                "map_public_ip": True
            })
            ```
        """
        self._child_props[resource_type] = props
        return None

    def add(
        self,
        child: ChildComponent
    ) -> Optional["ComponentTree[Any]"]:
        """Add a child resource and configure its relationship to this parent.

        This method establishes parent-child relationships between resources,
        ensuring proper dependency ordering and property inheritance. It can
        accept either ComponentTree instances or resource creation functions.

        Args:
            child: Either a ComponentTree instance to add as a child, or a
                ResourceWrapper function that will create a resource during
                construction

        Returns:
            Optional[ComponentTree[Any]]: The added ComponentTree child if one was
            provided, or None if a ResourceWrapper function was added

        Raises:
            RuntimeError: If called after the component has been constructed

        Example:
            ```python
            # Adding a ComponentTree child
            vpc.add(SubnetResource("subnet", "main", {"cidr": "10.0.1.0/24"}))

            # Adding a resource creation function
            vpc.add(lambda props, opts: ec2.SecurityGroup("sg", {...}, opts))
            ```
        """
        if self._constructed:
            raise RuntimeError("Cannot add children after component has been constructed")
        
        if isinstance(child, ComponentTree):
            self._children.append(child)
            
            # Set dependency on parent
            child.opts = ResourceOptions.merge(child.opts, ResourceOptions(parent=self))
            
            # Apply any configured defaults for this child type
            if type(child) in self._child_props:
                child.defaults = self._child_props[type(child)]
                
            return child
        else:
            # It's a ResourceWrapper - wrap it
            wrapper = ComponentTreeWrapper(child, self)
            self._children.append(wrapper)
            return None

    def _construct(self) -> None:
        """Create the actual cloud resources for this component.

        Subclasses must implement this method to define what cloud resources
        this component creates. This is called automatically during construction
        after all children have been constructed.

        Example implementation:
            ```python
            def _construct(self) -> None:
                self.vpc = ec2.Vpc("vpc", 
                    cidr_block=self.props["cidr"],
                    tags={"Name": self.props["name"]}
                )
            ```
        """
        raise NotImplementedError("_construct method not implemented")

    def construct(self) -> None:
        """Construct this resource and all its children.

        This method orchestrates the actual creation of cloud resources:
        1. Constructs all child resources first (proper dependency ordering)
        2. Creates this component's own resources via _construct()
        3. Ensures resources are only created once

        This is typically called automatically when exiting the context manager,
        but can be called manually if needed.

        Example:
            ```python
            # Automatic construction via context manager
            with NetworkResource("vpc", "main") as vpc:
                vpc << SubnetResource("subnet", "a")

            # Manual construction
            vpc = NetworkResource("vpc", "main")
            vpc.add(SubnetResource("subnet", "a"))
            vpc.construct()
            ```
        """
        if not self._constructed:
            # Construct children first
            for i, child in enumerate(self._children):
                if isinstance(child, ComponentTree):
                    child.construct()
                elif isinstance(child, ComponentTreeWrapper):
                    self._children[i] = child.construct()
            
            # Then construct self
            self._construct()
            self._constructed = True

    def __enter__(self) -> "ComponentTree[P]":
        """Enter a context for building the resource tree.

        This enables the context manager pattern for constructing resource
        trees. The tree will be automatically constructed when exiting
        the context.

        Returns:
            ComponentTree[P]: This component instance

        Example:
            ```python
            with NetworkResource("vpc", "main") as vpc:
                vpc << SubnetResource("subnet", "a")
                vpc << SubnetResource("subnet", "b")
            ```
        """
        return self
        
    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_val: Optional[BaseException], exc_tb: Optional[Any]) -> None:
        """Exit the context and construct the resource tree.

        Called automatically when exiting a context manager block.
        This triggers construction of the entire resource tree.

        Args:
            exc_type: Type of any exception that occurred
            exc_val: Instance of any exception that occurred
            exc_tb: Traceback for any exception that occurred
        """
        self.construct()

    def __lshift__(
        self,
        child: ChildComponent
    ) -> "ComponentTree[P]":
        """Operator (<< ) alias for add().

        This enables a more fluent API for building resource trees using the
        left shift operator. The operator returns self, allowing method chaining.

        Args:
            child: The child component or resource wrapper to add

        Returns:
            ComponentTree[P]: self, enabling method chaining

        Example:
            ```python
            with NetworkResource("vpc", "main") as vpc:
                # Add multiple subnets in a chain
                vpc << subnet_a << subnet_b << subnet_c

                # Equivalent to:
                vpc.add(subnet_a)
                vpc.add(subnet_b)
                vpc.add(subnet_c)
            ```
        """
        self.add(child)
        return self
