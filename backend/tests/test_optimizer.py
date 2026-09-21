from skysafe.optimizer import optimize_resource_allocation

def test_resource_optimizer():
    result = optimize_resource_allocation([], [])
    assert result["status"] == "optimized"
    assert isinstance(result["assignments"], list)
