# Proposed Unit Test Cases

## 1. Context Manager Construction Test
Tests that resources are properly constructed when using the context manager syntax:
```python
@pulumi.runtime.test
def test_context_manager_construction():
    with TestComponent("parent") as parent:
        child = TestComponent("child", {"code": "via-context"})
        parent << child
    # Verify child code output
```

## 4. Resource Wrapper Function Test
Tests adding a resource via wrapper function:
```python
@pulumi.runtime.test
def test_resource_wrapper():
    parent = TestComponent("parent")
    def create_resource(props, opts):
        return TestResource("wrapped", {"code": "wrapped-code"}, opts)
    # Verify wrapped resource creation and output
```