"""Unit tests for pulumi_component_tree"""

import pulumi
from typing import TypedDict, Tuple, Union, List, Dict, Optional, Any, Callable
from pulumi_component_tree import ComponentTree

class MyMocks(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs) -> Tuple[str, Dict[str, Any]]:
        """Mock resource creation to return predictable values"""
        outputs = args.inputs
        if args.typ == "test:resource:TestResource":
            # Mock a test resource with some output values
            outputs = {
                **args.inputs,
                "output_value": "mocked-output",
            }
        return (args.name + '_id', outputs)

    def call(self, args: pulumi.runtime.MockCallArgs) -> Tuple[Dict[str, Any], Optional[List[Tuple[str, str]]]]:
        return ({}, None)

pulumi.runtime.set_mocks(MyMocks())

# Test component that creates a resource with outputs
# Create a custom Pulumi resource type for testing
class TestResource(pulumi.CustomResource):
    """A test resource with a mocked output value"""
    code: pulumi.Output[str]

    def __init__(self, name: str, props: dict, opts: Optional[pulumi.ResourceOptions] = None):
        super().__init__("test:resource:TestResource", name, props, opts)
        self.code = pulumi.Output.from_input(props["code"])

class TestProps(TypedDict, total=False):
    code: str

class TestComponent(ComponentTree[TestProps]):
    """Test component that creates a test resource"""
    def __init__(self, name: str, props: Optional[TestProps] = None, opts: Optional[pulumi.ResourceOptions] = None) -> None:
        super().__init__("pulumi-component-tree:test:TestComponent", name, props, opts)

    def _construct(self) -> None:
        self.resource = TestResource(
            "test-resource",
            props={
                "code": self.props.get("code", "default")
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

class AnotherTestProps(TypedDict, total=False):
    code: str
    code_suffix: str
    custom_value: str

class AnotherTestComponent(ComponentTree[AnotherTestProps]):
    """Another test component for testing extend functionality"""
    def __init__(self, name: str, props: Optional[AnotherTestProps] = None, opts: Optional[pulumi.ResourceOptions] = None) -> None:
        super().__init__("pulumi-component-tree:test:AnotherTestComponent", name, props, opts)

    def _construct(self) -> None:
        self.resource = TestResource(
            "another-test-resource",
            props={
                "code": f"{self.props.get('code', 'NONE')}-{self.props.get('code_suffix', 'NONE')}"
            },
            opts=pulumi.ResourceOptions(parent=self)
        )

@pulumi.runtime.test
def test_component_outputs() -> pulumi.Output[None]:
    """Test that component can handle resource outputs correctly"""
    component = TestComponent("test", {"code": "42?"})
    component.construct()
    
    def check_outputs(outputs: List[Any]) -> None:
        # pulumi.Output.all() returns a list, so we get the first (and only) value
        (code,) = outputs
        expected_code = component.props["code"]
        assert code == expected_code, f"code should be '{expected_code}', got {code}"

    return pulumi.Output.all(component.resource.code).apply(check_outputs)

@pulumi.runtime.test
def test_default_output_before_construct() -> pulumi.Output[None]:
    """Test that child component is created with default code value"""
    parent = TestComponent("parent")
    child = TestComponent("child")
    parent.add(child)
    parent.construct()
    
    def check_outputs(outputs: List[Any]) -> None:
        # pulumi.Output.all() returns a list, so we get the first (and only) value
        (code,) = outputs
        assert code == "default", f"Child code should be 'default', got {code}"

    return pulumi.Output.all(child.resource.code).apply(check_outputs)

@pulumi.runtime.test
def test_child_has_parent_in_opts() -> None:
    """Test that child's ResourceOptions correctly sets parent when added to a parent component"""
    parent = TestComponent("parent")
    child = TestComponent("child")
    parent.add(child)
    parent.construct()
    
    # After construction, verify that the child's resource has the correct parent
    assert child.opts is not None, "Child opts should not be None after adding to parent"
    assert child.opts.parent == parent, "Child resource should have parent component as its parent"

@pulumi.runtime.test
def test_child_output_after_parent_construct() -> pulumi.Output[None]:
    """Test that child component is constructed with provided value when parent constructs"""
    parent = TestComponent("parent")
    child = TestComponent("child", {"code": "child-code"})
    parent.add(child)
    parent.construct()
    
    def check_outputs(outputs: List[Any]) -> None:
        # pulumi.Output.all() returns a list, so we get the first (and only) value
        (code,) = outputs
        assert code == "child-code", f"Child code should be 'child-code', got {code}"

    return pulumi.Output.all(child.resource.code).apply(check_outputs)

@pulumi.runtime.test
def test_add_after_construct() -> None:
    """Test that adding children after construction raises error"""
    parent = TestComponent("parent")
    parent.construct()
    
    try:
        parent.add(TestComponent("child"))
        assert False, "Should have raised RuntimeError"
    except RuntimeError as e:
        assert str(e) == "Cannot add children after component has been constructed"

@pulumi.runtime.test
def test_opts_merging() -> None:
    """Test that child's ResourceOptions are preserved when added to parent"""
    parent = TestComponent(
        "parent",
        opts=pulumi.ResourceOptions(protect=True)
    )
    
    child = TestComponent(
        "child",
        opts=pulumi.ResourceOptions(delete_before_replace=True)
    )
    
    # Store original value to verify it's not lost
    assert child.opts is not None, "Child opts should not be None"
    original_delete_before_replace = child.opts.delete_before_replace
    
    parent.add(child)
    parent.construct()
    
    # Verify child retains its options and gets parent reference
    assert child.opts is not None, "Child opts should not be None after adding to parent"
    assert child.opts.delete_before_replace == original_delete_before_replace, "Child should retain its original options"
    assert child.opts.parent == parent, "Child should have parent reference"

@pulumi.runtime.test
def test_nested_components() -> pulumi.Output[None]:
    """Test that deeply nested components maintain proper dependency chains and property inheritance"""
    grandparent = TestComponent("grandparent")
    parent = TestComponent("parent", {"code": "parent-code"})
    child = TestComponent("child", {"code": "child-code"})
    
    # Build component tree
    grandparent.add(parent)
    parent.add(child)
    grandparent.construct()
    
    def check_outputs(outputs: List[Any]) -> None:
        # Check parent and child codes
        parent_code, child_code = outputs
        assert parent_code == "parent-code", f"Parent code should be 'parent-code', got {parent_code}"
        assert child_code == "child-code", f"Child code should be 'child-code', got {child_code}"
        
        # Verify dependency chain
        assert child.opts is not None, "Child opts should not be None"
        assert child.opts.parent == parent, "Child should have parent as its parent"
        assert parent.opts is not None, "Parent opts should not be None"
        assert parent.opts.parent == grandparent, "Parent should have grandparent as its parent"

    return pulumi.Output.all(parent.resource.code, child.resource.code).apply(check_outputs)

@pulumi.runtime.test
def test_extend_child_props() -> pulumi.Output[None]:
    """Test that extend() properly sets default properties for child components"""
    parent = TestComponent("parent")
    # Set defaults for AnotherTestComponent children
    parent.extend(AnotherTestComponent, AnotherTestProps(code="from-parent"))

    # Create child with some custom props that should merge with extended props
    child = AnotherTestComponent("child", {"code_suffix": "custom"})
    parent.add(child)
    parent.construct()
    
    def check_outputs(outputs: List[Any]) -> None:
        # Check that the output is properly mocked after construction
        (actual_code,) = outputs
        assert actual_code == "from-parent-custom", f"Child code should be 'from-parent-custom', got {actual_code}"

    return pulumi.Output.all(child.resource.code).apply(check_outputs)

@pulumi.runtime.test
def test_multiple_extended_properties() -> pulumi.Output[None]:
    """Test that extend() works correctly with multiple property sets"""
    parent = TestComponent("parent")
    # Set multiple default properties for AnotherTestComponent children
    parent.extend(AnotherTestComponent, AnotherTestProps(
        code="from-parent",
        code_suffix="suffix1",
        custom_value="value1"
    ))

    # Create children with different property overrides
    child1 = AnotherTestComponent("child1")  # Uses all defaults
    child2 = AnotherTestComponent("child2", {"code": "override-code"})  # Override code only
    child3 = AnotherTestComponent("child3", {
        "code_suffix": "custom-suffix",
        "custom_value": "custom-value"
    })  # Override suffix and custom value

    parent.add(child1)
    parent.add(child2)
    parent.add(child3)
    parent.construct()
    
    def check_outputs(outputs: List[Any]) -> None:
        code1, code2, code3 = outputs
        # Child1 should use all default values
        assert code1 == "from-parent-suffix1", f"Child1 code should use default values, got {code1}"
        # Child2 should use overridden code but default suffix
        assert code2 == "override-code-suffix1", f"Child2 code should use overridden code, got {code2}"
        # Child3 should use default code but overridden suffix
        assert code3 == "from-parent-custom-suffix", f"Child3 code should use custom suffix, got {code3}"

        # Verify custom_value property inheritance
        assert child1.props.get("custom_value") == "value1", "Child1 should inherit custom_value"
        assert child2.props.get("custom_value") == "value1", "Child2 should inherit custom_value"
        assert child3.props.get("custom_value") == "custom-value", "Child3 should use overridden custom_value"

    return pulumi.Output.all(
        child1.resource.code,
        child2.resource.code,
        child3.resource.code
    ).apply(check_outputs)
